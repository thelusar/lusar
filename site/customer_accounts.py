"""Server-side customer sessions and Auth0 OIDC; customer passwords never enter LUSAR."""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from dataclasses import dataclass
from http.cookies import SimpleCookie
from threading import Lock
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

import order_storage
from loyalty import eligible_spend_from_saved_order, LOYALTY_TIERS

SESSION_SECONDS = 7 * 86400
DESTINATIONS = {'/account', '/account/orders', '/account/addresses', '/account/settings', '/account/loyalty',
                '/cart', '/checkout', '/manager/orders/', '/manager/access'}


class AccountError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class Config:
    issuer: str = ''
    client_id: str = ''
    secret: str = ''
    origin: str = ''

    @property
    def enabled(self):
        return bool(self.issuer and self.client_id and self.secret and self.origin)

    @property
    def secure(self):
        return self.origin.startswith('https://')

    @classmethod
    def environment(cls):
        domain = os.environ.get('LUSAR_AUTH0_DOMAIN', '').strip().removeprefix('https://').rstrip('/')
        origin = os.environ.get('LUSAR_PUBLIC_ORIGIN', os.environ.get('RENDER_EXTERNAL_URL', '')).strip().rstrip('/')
        parsed = urlsplit(origin)
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path or not parsed.hostname:
            return cls()
        if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in {'localhost', '127.0.0.1', '::1'}):
            return cls()
        if not re.fullmatch(r'[A-Za-z0-9.-]+', domain) or '.' not in domain:
            return cls(origin=origin)
        return cls('https://' + domain + '/', os.environ.get('LUSAR_AUTH0_CLIENT_ID', '').strip(),
                   os.environ.get('LUSAR_AUTH0_CLIENT_SECRET', '').strip(), origin)


class Auth0:
    def __init__(self, config):
        self.config = config
        self.keys = None
        self.keys_until = 0
        self.lock = Lock()

    def authorization(self, state, nonce, verifier, *, google=False, signup=False, recovery=False, language='ru'):
        from authlib.integrations.requests_client import OAuth2Session
        with OAuth2Session(self.config.client_id, self.config.secret, scope='openid profile email',
                           redirect_uri=self.config.origin + '/auth/callback', code_challenge_method='S256') as client:
            options = {'state': state, 'nonce': nonce, 'code_verifier': verifier, 'ui_locales': language}
            if google:
                options['connection'] = 'google-oauth2'
            if signup:
                options['screen_hint'] = 'signup'
            if recovery:
                options['prompt'] = 'login'
            return client.create_authorization_url(self.config.issuer + 'authorize', **options)[0]

    def jwks(self, refresh=False):
        with self.lock:
            if refresh or self.keys is None or self.keys_until < time.time():
                request = Request(self.config.issuer + '.well-known/jwks.json', headers={'User-Agent': 'LUSAR accounts'})
                with urlopen(request, timeout=8) as response:
                    raw = response.read(128 * 1024 + 1)
                if len(raw) > 128 * 1024:
                    raise ValueError('Oversized signing keys')
                from joserfc.jwk import KeySet
                self.keys = KeySet.import_key_set(json.loads(raw))
                self.keys_until = time.time() + 300
            return self.keys

    def validate_token(self, token, nonce):
        from joserfc import jwt
        from joserfc.errors import MissingKeyError
        try:
            result = jwt.decode(token, self.jwks(), algorithms=['RS256'])
        except MissingKeyError:
            result = jwt.decode(token, self.jwks(refresh=True), algorithms=['RS256'])
        claims = result.claims
        jwt.JWTClaimsRegistry(leeway=30, iss={'essential': True, 'value': self.config.issuer},
                              aud={'essential': True, 'value': self.config.client_id}, exp={'essential': True},
                              iat={'essential': True}, sub={'essential': True}, nonce={'essential': True, 'value': nonce}).validate(claims)
        if isinstance(claims['aud'], list) and len(claims['aud']) > 1 and claims.get('azp') != self.config.client_id:
            raise ValueError('Wrong authorized party')
        if claims.get('azp', self.config.client_id) != self.config.client_id:
            raise ValueError('Wrong authorized party')
        if claims.get('email_verified') is not True:
            raise AccountError(403, 'Подтвердите email в письме и повторите вход.')
        if not isinstance(claims['sub'], str) or not 1 <= len(claims['sub']) <= 255:
            raise ValueError('Invalid identity')
        email = claims.get('email')
        if not isinstance(email, str) or len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise ValueError('Missing verified email')
        return claims

    def exchange(self, code, nonce, verifier):
        from authlib.integrations.requests_client import OAuth2Session
        with OAuth2Session(self.config.client_id, self.config.secret, token_endpoint_auth_method='client_secret_post',
                           redirect_uri=self.config.origin + '/auth/callback', default_timeout=10) as client:
            result = client.fetch_token(self.config.issuer + 'oauth/token', grant_type='authorization_code', code=code, code_verifier=verifier)
        return self.validate_token(result['id_token'], nonce)


class Service:
    def __init__(self, database, config=None, provider=None):
        self.database = database
        self.config = config or Config.environment()
        self.provider = provider or Auth0(self.config)
        self.initialized = False
        self.lock = Lock()
        self.attempts = {}

    def ensure(self):
        with self.lock:
            if not self.initialized:
                order_storage.initialize(self.database)
                self.initialized = True

    @property
    def cookie_name(self):
        return '__Host-lusar_session' if self.config.secure else 'lusar_local_session'

    @property
    def flow_cookie(self):
        return '__Host-lusar_login' if self.config.secure else 'lusar_local_login'

    def cookie(self, name, token, seconds):
        return f'{name}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={seconds}' + ('; Secure' if self.config.secure else '')

    def read_cookie(self, handler, name):
        try:
            cookies = SimpleCookie(handler.headers.get('Cookie', ''))
            token = cookies[name].value if name in cookies else ''
            return token if re.fullmatch(r'[A-Za-z0-9_-]{43}', token) else ''
        except Exception:
            return ''

    def session(self, handler, db=None):
        token = self.read_cookie(handler, self.cookie_name)
        if not token:
            return None
        self.ensure()
        if db is None:
            with order_storage.connect(self.database) as connection:
                return self.session(handler, connection)
        row = db.execute('SELECT customer_id FROM customer_sessions WHERE token_hash = ? AND expires > ?', (digest(token), int(time.time()))).fetchone()
        if not row:
            return None
        csrf = hmac.new(token.encode(), b'lusar-csrf-v1', hashlib.sha256).hexdigest()
        return {'id': row[0], 'csrf': csrf, 'hash': digest(token)}

    def require_write(self, handler, session):
        if handler.headers.get('Origin') != self.config.origin or not secrets.compare_digest(handler.headers.get('X-Lusar-CSRF', ''), session['csrf']):
            raise AccountError(403, 'Обновите страницу и повторите действие.')

    def orders(self, db, customer_id):
        return db.execute('SELECT number, status, created, payload FROM orders WHERE customer_id = ? ORDER BY created DESC', (customer_id,)).fetchall()

    def loyalty(self, db, customer_id):
        rows = self.orders(db, customer_id)
        spent = 0
        completed = reserved = False
        for _, status, _, raw in rows:
            order = json.loads(raw)
            spent += int(eligible_spend_from_saved_order(status, order))
            completed |= status == 'completed'
            reserved |= status in {'new', 'in_progress'} and bool(order.get('firstOrderApplied') or order.get('firstOrderDiscount'))
        index = max(i for i, (threshold, _) in enumerate(LOYALTY_TIERS) if threshold <= spent)
        next_tier = LOYALTY_TIERS[index + 1] if index + 1 < len(LOYALTY_TIERS) else None
        return {'eligibleSpend': spent, 'discountPercent': LOYALTY_TIERS[index][1],
                'nextDiscountPercent': next_tier[1] if next_tier else None,
                'remainingToNext': next_tier[0] - spent if next_tier else None,
                'firstOrderAvailable': not completed and not reserved, 'firstOrderReserved': reserved}

    def me(self, handler):
        session = self.session(handler)
        if not session:
            return {'authenticated': False, 'available': self.config.enabled}
        with order_storage.connect(self.database) as db:
            row = db.execute('SELECT email, name, phone, addresses FROM customers WHERE id = ?', (session['id'],)).fetchone()
            state = db.execute('SELECT cart, favorites, version FROM customer_state WHERE customer_id = ?', (session['id'],)).fetchone()
            loyalty = self.loyalty(db, session['id'])
        addresses = json.loads(row[3])
        return {'authenticated': True, 'available': self.config.enabled, 'csrfToken': session['csrf'],
                'profile': {'id': session['id'], 'email': row[0], 'name': row[1], 'phone': row[2], 'addresses': addresses,
                            'address': addresses[0]['address'] if addresses else ''},
                'loyalty': loyalty, 'state': {'cart': json.loads(state[0]), 'favorites': json.loads(state[1]), 'version': state[2]}}

    def begin(self, handler, params):
        if not self.config.enabled:
            return self.redirect(handler, '/account/sign-in?auth_error=unavailable')
        now = int(time.time())
        address = handler.client_address[0]
        with self.lock:
            recent = [stamp for stamp in self.attempts.get(address, []) if stamp > now - 60]
            if len(recent) >= 30:
                raise AccountError(429, 'Слишком много попыток входа. Попробуйте позже.')
            if len(self.attempts) > 1000:
                self.attempts.clear()
            self.attempts[address] = [*recent, now]
        self.ensure()
        state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
        destination = params.get('return', ['/account'])[0]
        path, _, fragment = destination.partition('#')
        order_link = path == '/manager/orders/' and order_storage.ORDER_NUMBER.fullmatch(fragment)
        if destination not in DESTINATIONS and not order_link:
            destination = '/account'
        language = params.get('lang', ['ru'])[0]
        if language not in {'ru', 'hy', 'en'}:
            language = 'ru'
        with order_storage.connect(self.database, write=True) as db:
            db.execute('DELETE FROM customer_login_flows WHERE expires <= ?', (now,))
            db.execute('DELETE FROM customer_sessions WHERE expires <= ?', (now,))
            db.execute('INSERT INTO customer_login_flows (state_hash, nonce, verifier, destination, expires) VALUES (?, ?, ?, ?, ?)',
                       (digest(state), nonce, verifier, destination, now + 600))
        target = self.provider.authorization(state, nonce, verifier, google=params.get('connection') == ['google'],
                                             signup=params.get('screen') == ['signup'], recovery=params.get('screen') == ['recovery'], language=language)
        self.redirect(handler, target, [self.cookie(self.flow_cookie, state, 600)])

    def callback(self, handler, params):
        state = params.get('state', [''])[0]
        cookie = self.read_cookie(handler, self.flow_cookie)
        if not self.config.enabled or not cookie or not secrets.compare_digest(cookie, state):
            raise AccountError(400, 'Вход не подтверждён. Повторите попытку.')
        self.ensure()
        with order_storage.connect(self.database, write=True) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT nonce, verifier, destination FROM customer_login_flows WHERE state_hash = ? AND expires > ?', (digest(state), int(time.time()))).fetchone()
            db.execute('DELETE FROM customer_login_flows WHERE state_hash = ?', (digest(state),))
        if not row or 'error' in params or len(params.get('code', [''])[0]) > 4096 or not params.get('code', [''])[0]:
            raise AccountError(400, 'Вход не подтверждён. Повторите попытку.')
        claims = self.provider.exchange(params['code'][0], row[0], row[1])
        token = secrets.token_urlsafe(32)
        previous = self.read_cookie(handler, self.cookie_name)
        with order_storage.connect(self.database, write=True) as db:
            db.execute('BEGIN IMMEDIATE')
            identity = db.execute('SELECT id FROM customers WHERE issuer = ? AND subject = ?', (self.config.issuer, claims['sub'])).fetchone()
            customer_id = identity[0] if identity else str(uuid.uuid4())
            if not identity:
                name = claims.get('given_name') or claims.get('name') or ''
                db.execute('INSERT INTO customers (id, issuer, subject, email, name, created) VALUES (?, ?, ?, ?, ?, ?)',
                           (customer_id, self.config.issuer, claims['sub'], claims['email'], name[:120] if isinstance(name, str) else '', int(time.time())))
                db.execute('INSERT INTO customer_state (customer_id) VALUES (?)', (customer_id,))
            else:
                db.execute('UPDATE customers SET email = ? WHERE id = ?', (claims['email'], customer_id))
            if previous:
                db.execute('DELETE FROM customer_sessions WHERE token_hash = ?', (digest(previous),))
            db.execute('INSERT INTO customer_sessions (token_hash, customer_id, expires) VALUES (?, ?, ?)',
                       (digest(token), customer_id, int(time.time()) + SESSION_SECONDS))
        self.redirect(handler, row[2], [self.cookie(self.cookie_name, token, SESSION_SECONDS), self.cookie(self.flow_cookie, '', 0)])

    def redirect(self, handler, target, cookies=()):
        handler.send_response(303)
        handler.send_header('Location', target)
        for cookie in cookies:
            handler.send_header('Set-Cookie', cookie)
        handler.send_header('Cache-Control', 'no-store')
        handler.send_header('Content-Length', '0')
        handler.end_headers()

    def get(self, handler):
        url = urlsplit(handler.path)
        if url.path not in {'/auth/start', '/auth/callback', '/api/account/me', '/api/account/orders'}:
            return False
        try:
            if url.path == '/auth/start':
                self.begin(handler, parse_qs(url.query))
            elif url.path == '/auth/callback':
                try:
                    self.callback(handler, parse_qs(url.query))
                except Exception as error:
                    flag = 'verify-email' if isinstance(error, AccountError) and error.status == 403 else 'failed'
                    self.redirect(handler, '/account/sign-in?auth_error=' + flag, [self.cookie(self.flow_cookie, '', 0)])
            elif url.path == '/api/account/me':
                handler.reply(200, self.me(handler))
            else:
                session = self.session(handler)
                if not session:
                    raise AccountError(401, 'Войдите в личный кабинет.')
                with order_storage.connect(self.database) as db:
                    offset = int(parse_qs(url.query).get('offset', ['0'])[0])
                    if not 0 <= offset <= 1000000:
                        raise ValueError
                    all_rows = self.orders(db, session['id'])
                    rows = all_rows[offset:offset + 20]
                orders = []
                for number, status, created, raw in rows:
                    order = json.loads(raw)
                    orders.append({'number': number, 'status': status, 'created': str(created), 'total': order.get('total'),
                                   'remainingTotal': order.get('remainingAmount', order).get('total'), 'paid': bool(order.get('payment')),
                                   'items': [{key: item.get(key) for key in ('id', 'name', 'quantity', 'unitPrice', 'sku')} for item in order['items']],
                                   'returned': bool(order.get('returns'))})
                handler.reply(200, {'orders': orders, 'hasMore': len(all_rows) > offset + 20, 'nextOffset': offset + len(rows)})
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except AccountError as error:
            handler.reply(error.status, {'error': str(error)})
        except (OSError, ValueError, *order_storage.DatabaseError):
            handler.reply(503, {'error': 'Личный кабинет временно недоступен. Попробуйте позже.'})
        return True

    def post(self, handler):
        path = urlsplit(handler.path).path
        if path not in {'/api/account/profile', '/api/account/address', '/api/account/state', '/api/account/logout'}:
            return False
        try:
            session = self.session(handler)
            if not session:
                raise AccountError(401, 'Войдите в личный кабинет.')
            self.require_write(handler, session)
            length = int(handler.headers.get('Content-Length', '0'))
            if handler.headers.get_content_type() != 'application/json' or not 0 < length <= 32000:
                raise AccountError(400, 'Проверьте данные формы.')
            data = json.loads(handler.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError
            with order_storage.connect(self.database, write=True) as db:
                db.execute('BEGIN IMMEDIATE')
                if path.endswith('/logout'):
                    db.execute('DELETE FROM customer_sessions WHERE token_hash = ?', (session['hash'],))
                elif path.endswith('/profile'):
                    name, phone = data.get('name', ''), data.get('phone', '')
                    if not isinstance(name, str) or not isinstance(phone, str) or not name.strip() or len(name) > 120 or len(phone) > 40 or (phone.strip() and not 7 <= len(re.sub(r'\D', '', phone)) <= 15):
                        raise ValueError
                    db.execute('UPDATE customers SET name = ?, phone = ? WHERE id = ?', (name.strip(), phone.strip(), session['id']))
                elif path.endswith('/address'):
                    row = db.execute('SELECT addresses FROM customers WHERE id = ?', (session['id'],)).fetchone()
                    addresses = json.loads(row[0])
                    operation = data.get('operation')
                    if operation == 'add':
                        if len(addresses) >= 10:
                            raise AccountError(400, 'Можно сохранить до десяти адресов.')
                        address = {'id': str(uuid.uuid4()), 'label': data.get('label', ''), 'address': data.get('address', '')}
                        addresses.append(address)
                    else:
                        address = next((item for item in addresses if item['id'] == data.get('id')), None)
                        if not address:
                            raise AccountError(404, 'Адрес не найден.')
                        if operation == 'edit':
                            address.update(label=data.get('label', ''), address=data.get('address', ''))
                        elif operation == 'delete':
                            addresses.remove(address)
                        elif operation == 'primary':
                            addresses.remove(address)
                            addresses.insert(0, address)
                        else:
                            raise ValueError
                    for entry in addresses:
                        if not isinstance(entry['label'], str) or not isinstance(entry['address'], str) or len(entry['label']) > 50 or not entry['address'].strip() or len(entry['address']) > 300:
                            raise ValueError
                    db.execute('UPDATE customers SET addresses = ? WHERE id = ?', (json.dumps(addresses, ensure_ascii=False), session['id']))
                else:
                    cart, favorites, version = data.get('cart'), data.get('favorites'), data.get('version')
                    safe = re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}')
                    if not isinstance(cart, dict) or len(cart) > 100 or any(not safe.fullmatch(key) or type(value) is not int or not 1 <= value <= 999 for key, value in cart.items()):
                        raise ValueError
                    if not isinstance(favorites, list) or len(favorites) > 100 or any(not isinstance(key, str) or not safe.fullmatch(key) for key in favorites) or type(version) is not int:
                        raise ValueError
                    updated = db.execute('UPDATE customer_state SET cart = ?, favorites = ?, version = version + 1 WHERE customer_id = ? AND version = ?',
                                         (json.dumps(cart), json.dumps(list(dict.fromkeys(favorites))), session['id'], version))
                    if updated.rowcount != 1:
                        raise AccountError(409, 'Корзина изменилась в другом устройстве. Обновите страницу.')
            if path.endswith('/logout'):
                handler.send_response(200)
                handler.send_header('Set-Cookie', self.cookie(self.cookie_name, '', 0))
                handler.send_header('Content-Type', 'application/json')
                body = json.dumps({'ok': True, 'logoutUrl': self.config.issuer + 'v2/logout?' + urlencode({'client_id': self.config.client_id, 'returnTo': self.config.origin + '/account/sign-in'})}).encode()
                handler.send_header('Content-Length', str(len(body)))
                handler.end_headers()
                handler.wfile.write(body)
            else:
                handler.reply(200, self.me(handler))
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except AccountError as error:
            handler.reply(error.status, {'error': str(error)})
        except (OSError, ValueError, TypeError, *order_storage.DatabaseError):
            handler.reply(400, {'error': 'Не удалось сохранить изменения. Проверьте данные и повторите попытку.'})
        return True
