"""Verify customer isolation, signed OIDC, session/CSRF controls and discount rules using a local identity provider."""
import copy
import http.client
import json
import secrets
import sys
import tempfile
import threading
import time
import unittest
import uuid
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

# Optional, ignored local SDK installation; production installs requirements.txt.
if (Path(__file__).parent / '.local-deps').is_dir():
    sys.path.insert(0, str(Path(__file__).parent / '.local-deps'))
from joserfc import jwt
from joserfc.jwk import RSAKey, KeySet

import customer_accounts as accounts
import order_storage
import serve

DATA = json.loads(serve.CATALOG.read_text(encoding='utf-8-sig'))
PRODUCT = DATA['products'][0]


class Identity(accounts.Auth0):
    def __init__(self, config):
        super().__init__(config)
        self.key = RSAKey.generate_key(2048, parameters={'kid': 'local-test'})
        self.public = KeySet.import_key_set({'keys': [self.key.as_dict(private=False)]})
        self.user = 'alice'
        self.exchanges = 0

    def jwks(self, refresh=False):
        return self.public

    def token(self, nonce, **changes):
        claims = {'iss': self.config.issuer, 'aud': self.config.client_id, 'sub': self.user, 'nonce': nonce,
                  'iat': int(time.time()), 'exp': int(time.time()) + 120, 'email': self.user + '@example.test',
                  'name': self.user, 'email_verified': True}
        claims.update(changes)
        return jwt.encode({'alg': 'RS256', 'kid': 'local-test'}, claims, self.key)

    def exchange(self, code, nonce, verifier):
        self.exchanges += 1
        if len(verifier) != 43:
            raise ValueError('Missing PKCE verifier')
        return self.validate_token(self.token(nonce), nonce)


class Client:
    def __init__(self, server):
        self.server = server
        self.cookies = {}

    def request(self, path, data=None, csrf=None, origin=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=15)
        headers = {'Cookie': '; '.join(key + '=' + value for key, value in self.cookies.items())}
        if data is not None:
            headers['Content-Type'] = 'application/json'
            headers['Origin'] = origin or self.server.customer_accounts.config.origin
            if csrf is not None:
                headers['X-Lusar-CSRF'] = csrf
        connection.request('POST' if data is not None else 'GET', path, json.dumps(data) if data is not None else None, headers)
        response = connection.getresponse()
        raw = response.read()
        result = json.loads(raw) if raw and response.headers.get_content_type() == 'application/json' else raw.decode('utf-8')
        for key, value in response.getheaders():
            if key.lower() == 'set-cookie':
                for name, cookie in SimpleCookie(value).items():
                    if cookie['max-age'] == '0':
                        self.cookies.pop(name, None)
                    else:
                        self.cookies[name] = cookie.value
        status, headers = response.status, response.headers
        connection.close()
        return status, result, headers

    def login(self, user='alice'):
        self.server.customer_accounts.provider.user = user
        status, _, headers = self.request('/auth/start')
        assert status == 303
        parameters = parse_qs(urlsplit(headers['Location']).query)
        status, _, headers = self.request('/auth/callback?' + urlencode({'state': parameters['state'][0], 'code': 'local-code'}))
        assert status == 303 and headers['Location'] == '/account'
        return self.request('/api/account/me')[1]


class Quiet(serve.Handler):
    def log_message(self, *_):
        pass


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        previous = serve.DATABASE
        serve.DATABASE = Path(self.temp.name) / 'orders.sqlite'
        self.addCleanup(setattr, serve, 'DATABASE', previous)
        self.server = serve.ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.origin = 'http://127.0.0.1:' + str(self.server.server_port)
        config = accounts.Config('https://local-identity.example/', 'test-client', 'local-test-secret', self.origin)
        self.provider = Identity(config)
        self.server.customer_accounts = accounts.Service(serve.DATABASE, config, self.provider)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.client = Client(self.server)

    def order(self, quantity=1, mode='none', **changes):
        data = {'requestId': str(uuid.uuid4()), 'cart': {PRODUCT['id']: quantity}, 'displayedPrices': {PRODUCT['id']: PRODUCT['price']},
                'name': 'Test customer', 'phone': '+37400000000', 'email': 'alice@example.test', 'address': '', 'promo': '', 'discountMode': mode}
        data.update(changes)
        return data

    def submit(self, data, client=None):
        client = client or self.client
        me = client.request('/api/account/me')[1]
        return client.request('/api/orders', data, csrf=me.get('csrfToken'))

    def saved(self, number):
        with order_storage.connect(serve.DATABASE) as db:
            return json.loads(db.execute('SELECT payload FROM orders WHERE number = ?', (number,)).fetchone()[0])

    def test_verified_identity_and_hashed_session(self):
        me = self.client.login()
        self.assertTrue(me['authenticated'])
        self.assertEqual(me['profile']['email'], 'alice@example.test')
        token = self.client.cookies[self.server.customer_accounts.cookie_name]
        with order_storage.connect(serve.DATABASE) as db:
            stored = db.execute('SELECT token_hash FROM customer_sessions').fetchone()[0]
        self.assertEqual(stored, accounts.digest(token))
        self.assertNotEqual(stored, token)
        cookie = accounts.Service(serve.DATABASE, accounts.Config('https://id.example/', 'x', 'y', 'https://lusar.am')).cookie('__Host-lusar_session', token, 600)
        for part in ['Secure', 'HttpOnly', 'SameSite=Lax', 'Path=/']:
            self.assertIn(part, cookie)

    def test_reject_wrong_signatures_claims_and_unverified_email(self):
        for change in [{'iss': 'https://attacker.example/'}, {'aud': 'other-client'}, {'exp': int(time.time()) - 120},
                       {'iat': int(time.time()) + 120}, {'nonce': 'other'}, {'email_verified': False}, {'azp': 'other-client'}]:
            with self.assertRaises(Exception):
                self.provider.validate_token(self.provider.token('nonce', **change), 'nonce')
        other = RSAKey.generate_key(2048, parameters={'kid': 'local-test'})
        invalid = jwt.encode({'alg': 'RS256', 'kid': 'local-test'}, {'nonce': 'nonce'}, other)
        with self.assertRaises(Exception):
            self.provider.validate_token(invalid, 'nonce')

    def test_login_state_is_browser_bound_and_one_use(self):
        _, _, headers = self.client.request('/auth/start?return=https://attacker.example')
        params = parse_qs(urlsplit(headers['Location']).query)
        self.assertEqual(params['code_challenge_method'], ['S256'])
        outsider = Client(self.server)
        callback = '/auth/callback?' + urlencode({'state': params['state'][0], 'code': 'test'})
        self.assertIn('auth_error=failed', outsider.request(callback)[2]['Location'])
        self.assertEqual(self.provider.exchanges, 0)
        self.assertEqual(self.client.request(callback)[2]['Location'], '/account')
        self.assertIn('auth_error=failed', self.client.request(callback)[2]['Location'])
        self.assertEqual(self.provider.exchanges, 1)

    def test_csrf_logout_and_expiry(self):
        me = self.client.login()
        update = {'name': 'Changed', 'phone': ''}
        self.assertEqual(self.client.request('/api/account/profile', update)[0], 403)
        self.assertEqual(self.client.request('/api/account/profile', update, csrf=me['csrfToken'], origin='https://attacker.example')[0], 403)
        self.assertEqual(self.client.request('/api/account/profile', update, csrf=me['csrfToken'])[0], 200)
        self.assertEqual(self.client.request('/api/account/logout', {}, csrf=me['csrfToken'])[0], 200)
        self.assertFalse(self.client.request('/api/account/me')[1]['authenticated'])
        self.assertEqual(self.client.request('/api/orders', self.order(), csrf=me['csrfToken'])[0], 401)
        self.client.login()
        with order_storage.connect(serve.DATABASE, write=True) as db:
            db.execute('UPDATE customer_sessions SET expires = 0')
        self.assertFalse(self.client.request('/api/account/me')[1]['authenticated'])

    def test_unconfigured_provider_and_recovery_options(self):
        _, _, headers = self.client.request('/auth/start?screen=recovery&lang=hy')
        parameters = parse_qs(urlsplit(headers['Location']).query)
        self.assertEqual(parameters['prompt'], ['login'])
        self.assertEqual(parameters['ui_locales'], ['hy'])
        self.server.customer_accounts.config = accounts.Config(origin=self.origin)
        self.assertEqual(self.client.request('/api/account/me')[1], {'authenticated': False, 'available': False})
        self.assertEqual(self.client.request('/auth/start')[2]['Location'], '/account/sign-in?auth_error=unavailable')

    def test_order_ownership_does_not_use_matching_email(self):
        guest = self.order()
        self.assertEqual(self.submit(guest)[0], 201)
        alice = self.client.login()
        own = self.order()
        self.assertEqual(self.submit(own)[0], 201)
        self.assertEqual(len(self.client.request('/api/account/orders')[1]['orders']), 1)
        bob = Client(self.server)
        bob.login('bob')
        self.assertEqual(bob.request('/api/account/orders')[1]['orders'], [])
        self.assertEqual(self.submit(own, bob)[0], 409)
        self.assertEqual(self.client.request('/api/account/me')[1]['profile']['id'], alice['profile']['id'])

    def test_first_order_is_exclusive_and_reserved_until_cancelled(self):
        self.assertEqual(self.submit(self.order(mode='first'))[0], 401)
        me = self.client.login()
        self.assertTrue(me['loyalty']['firstOrderAvailable'])
        self.assertEqual(self.submit(self.order(mode='first', promo='LUSAR1000'))[0], 422)
        status, result, _ = self.submit(self.order(mode='first'))
        self.assertEqual(status, 201)
        saved = self.saved(result['number'])
        self.assertEqual(saved['firstOrderDiscount'], PRODUCT['price'] // 10)
        self.assertEqual(self.submit(self.order(mode='first'))[0], 409)
        with order_storage.connect(serve.DATABASE, write=True) as db:
            db.execute("UPDATE orders SET status = 'cancelled' WHERE number = ?", (result['number'],))
        self.assertTrue(self.client.request('/api/account/me')[1]['loyalty']['firstOrderAvailable'])
        self.assertEqual(self.submit(self.order(mode='first'))[0], 201)

    def test_loyalty_uses_settled_orders_and_recalculates_returns(self):
        self.client.login()
        _, result, _ = self.submit(self.order(quantity=8))
        number = result['number']
        order = self.saved(number)
        order['payment'] = {'method': 'store', 'amount': order['total']}
        with order_storage.connect(serve.DATABASE, write=True) as db:
            db.execute("UPDATE orders SET status = 'completed', payload = ? WHERE number = ?", (json.dumps(order), number))
        benefits = self.client.request('/api/account/me')[1]['loyalty']
        self.assertEqual(benefits['eligibleSpend'], PRODUCT['price'] * 8)
        self.assertEqual(benefits['discountPercent'], 3)
        self.assertFalse(benefits['firstOrderAvailable'])
        status, discounted, _ = self.submit(self.order(quantity=4, mode='loyalty', promo='LUSAR5000', accountPercent=100))
        self.assertEqual(status, 201)
        self.assertEqual(self.saved(discounted['number'])['accountPercent'], 3)
        self.assertEqual(self.saved(discounted['number'])['total'], 24100)
        serve.apply_adjustment(order, 'completed', 'return', PRODUCT['id'], 2)
        with order_storage.connect(serve.DATABASE, write=True) as db:
            db.execute('UPDATE orders SET payload = ? WHERE number = ?', (json.dumps(order), number))
        self.assertEqual(self.client.request('/api/account/me')[1]['loyalty']['discountPercent'], 0)

    def test_addresses_and_optimistic_cart_state_are_owner_scoped(self):
        me = self.client.login()
        csrf = me['csrfToken']
        status, updated, _ = self.client.request('/api/account/address', {'operation': 'add', 'label': 'Home', 'address': 'Test street'}, csrf)
        self.assertEqual(status, 200)
        address_id = updated['profile']['addresses'][0]['id']
        bob = Client(self.server)
        bob_me = bob.login('bob')
        self.assertEqual(bob.request('/api/account/address', {'operation': 'delete', 'id': address_id}, bob_me['csrfToken'])[0], 404)
        state = {'cart': {PRODUCT['id']: 2}, 'favorites': [PRODUCT['id']], 'version': 0}
        self.assertEqual(self.client.request('/api/account/state', state, csrf)[0], 200)
        self.assertEqual(self.client.request('/api/account/state', state, csrf)[0], 409)
        self.assertEqual(bob.request('/api/account/me')[1]['state']['cart'], {})


if __name__ == '__main__':
    unittest.main(verbosity=1)
