"""Staff access and order audit records, independent of storefront account privileges."""
import hmac
import html
import os
import uuid
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode

import order_storage

ROLE_NAMES = {'admin': 'Администратор', 'manager': 'Менеджер'}
ACTION_NAMES = {'status': 'Статус', 'payment': 'Оплата', 'return': 'Возврат', 'refund_paid': 'Выплата по возврату'}
ORDERS_PATH = '/manager/orders/'
ACCESS_PATH = '/manager/access'


def account_id(value):
    return str(uuid.UUID(value.strip()))


def owner_id():
    try:
        return account_id(os.environ.get('LUSAR_STAFF_ADMIN_ID', ''))
    except ValueError:
        return None


@dataclass(frozen=True)
class Actor:
    id: str | None
    email: str
    role: str | None
    form_key: bytes


def identity(handler, db=None):
    service = handler.customer_service()
    if not service.config.enabled or not service.read_cookie(handler, service.cookie_name):
        return None
    service.ensure()
    if db is None:
        with order_storage.connect(service.database) as connection:
            return identity(handler, connection)
    session = service.session(handler, db)
    if not session:
        return None
    row = db.execute('SELECT customers.email, staff_roles.role FROM customers '
                     'LEFT JOIN staff_roles ON staff_roles.customer_id = customers.id WHERE customers.id = ?',
                     (session['id'],)).fetchone()
    if not row:
        return None
    role = 'admin' if session['id'] == owner_id() else row[1]
    return Actor(session['id'], row[0], role, bytes.fromhex(session['csrf']))


def page(handler, status, title, content):
    body = ('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="robots" content="noindex">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><link rel="stylesheet" href="/site.css">'
            f'<main class="staff-panel"><h1>{html.escape(title)}</h1>{content}</main></html>').encode()
    handler.send_response(status)
    handler.send_header('Content-Type', 'text/html; charset=utf-8')
    handler.send_header('Cache-Control', 'no-store')
    handler.send_header('Referrer-Policy', 'no-referrer')
    handler.send_header('Content-Length', str(len(body)))
    handler.end_headers()
    if handler.command != 'HEAD':
        handler.wfile.write(body)


def sign_in_page(handler, destination, actor):
    if not handler.customer_service().config.enabled:
        return page(handler, 503, 'Панель сотрудников', '<p>Вход сотрудников временно недоступен.</p>')
    query = {'return': destination, 'screen': 'recovery'} if actor else {'return': destination}
    url = '/auth/start?' + html.escape(urlencode(query), quote=True)
    if actor:
        return page(handler, 403, 'Доступ к панели сотрудников',
                    '<p>Для этого аккаунта не выданы права сотрудника. Передайте администратору код своего аккаунта.</p>'
                    f'<p><code>{html.escape(actor.id)}</code></p><p><a href="{url}">Войти другим аккаунтом</a></p>')
    return page(handler, 401, 'Панель сотрудников', f'<p><a href="{url}">Войти в LUSAR</a></p>')


def require_origin(handler, actor):
    origin = handler.headers.get('Origin')
    same_origin_form = origin in {None, 'null'} and handler.headers.get('Sec-Fetch-Site') == 'same-origin'
    # Native form posts can omit the origin under the panel's no-referrer policy.
    # The caller still verifies a form token tied to the current staff session.
    if actor.id is None or origin == handler.customer_service().config.origin or same_origin_form:
        return True
    handler.reply(403, {'error': 'Откройте панель сотрудников и повторите действие.'})
    return False


def write_allowed(handler, actor, db, *, admin=False):
    if actor.id is None and not admin:
        return True  # Only the loopback preview can provide this identity.
    current = identity(handler, db)
    if current and current.id == actor.id and current.role and (not admin or current.role == 'admin'):
        return True
    handler.reply(403, {'error': 'Доступ сотрудника изменился. Обновите страницу.'})
    return False


def record(db, number, actor, action, detail):
    db.execute('INSERT INTO order_staff_activity (number, actor_id, actor_email, action, detail) VALUES (?, ?, ?, ?, ?)',
               (number, actor.id, actor.email, action, detail))


def history_markup(events):
    if not events:
        return ''
    items = []
    for action, detail, email, changed in events:
        changed = str(changed)
        items.append(f'<li><time>{html.escape(changed)}</time> · {html.escape(email)} · '
                     f'{html.escape(ACTION_NAMES[action])}: {html.escape(detail)}</li>')
    return '<details><summary>Журнал заказа</summary><ul>' + ''.join(items) + '</ul></details>'


def access_token(actor):
    return hmac.digest(actor.form_key, b'staff-access-v1', 'sha256').hex()


def access_page(handler, actor):
    if actor.role != 'admin':
        return page(handler, 403, 'Доступ сотрудников', '<p>Этот раздел доступен администратору.</p>')
    with order_storage.connect(handler.customer_service().database) as db:
        rows = db.execute('SELECT customers.email, staff_roles.role, staff_roles.customer_id FROM staff_roles '
                          'JOIN customers ON customers.id = staff_roles.customer_id ORDER BY customers.email').fetchall()
    token = access_token(actor)
    staff_list = []
    for email, role, user_id in rows:
        if user_id == owner_id():
            continue
        revoke = ''
        if user_id != actor.id:
            revoke = (f'<form method="post" action="{ACCESS_PATH}"><input type="hidden" name="token" value="{token}">'
                      f'<input type="hidden" name="account" value="{html.escape(user_id, quote=True)}">'
                      '<button name="role" value="remove">Отозвать доступ</button></form>')
        staff_list.append(f'<li>{html.escape(email)} · {ROLE_NAMES[role]}{revoke}</li>')
    content = (f'<nav><a href="{ORDERS_PATH}">К заказам</a></nav>'
               '<p>Сотрудник входит в LUSAR, открывает панель заказов и передаёт вам свой код аккаунта.</p>'
               f'<form method="post" action="{ACCESS_PATH}"><input type="hidden" name="token" value="{token}">'
               '<label>Код аккаунта <input name="account" required maxlength="36" autocomplete="off"></label> '
               '<label>Роль <select name="role"><option value="manager">Менеджер</option>'
               '<option value="admin">Администратор</option></select></label> '
               '<button>Сохранить доступ</button></form><h2>Назначенные сотрудники</h2>'
               + ('<ul>' + ''.join(staff_list) + '</ul>' if staff_list else '<p>Дополнительных сотрудников пока нет.</p>'))
    return page(handler, 200, 'Доступ сотрудников', content)


def update_access(handler, actor):
    if not actor or actor.role != 'admin':
        return handler.reply(403, {'error': 'Изменять доступ может только администратор.'})
    if not require_origin(handler, actor):
        return
    if handler.headers.get_content_type() != 'application/x-www-form-urlencoded':
        return handler.reply(415, {'error': 'Неверный формат формы.'})
    try:
        size = int(handler.headers.get('Content-Length', '0'))
        if not 0 < size <= 1000:
            raise ValueError
        fields = parse_qs(handler.rfile.read(size).decode(), strict_parsing=True, max_num_fields=3)
        target = account_id(fields['account'][0])
        role = fields['role'][0]
        token = fields['token'][0]
        if role not in {*ROLE_NAMES, 'remove'}:
            raise ValueError
    except (ValueError, KeyError):
        return handler.reply(400, {'error': 'Проверьте код аккаунта и роль.'})
    if not hmac.compare_digest(token.encode(), access_token(actor).encode()):
        return handler.reply(403, {'error': 'Откройте страницу доступа и повторите действие.'})
    if target in {actor.id, owner_id()}:
        return handler.reply(409, {'error': 'Нельзя менять собственные права или права основного администратора.'})
    with order_storage.connect(handler.customer_service().database, write=True) as db:
        db.execute('BEGIN IMMEDIATE')
        if not write_allowed(handler, actor, db, admin=True):
            return
        if not db.execute('SELECT 1 FROM customers WHERE id = ?', (target,)).fetchone():
            return handler.reply(404, {'error': 'Аккаунт с таким кодом не найден.'})
        if role == 'remove':
            db.execute('DELETE FROM staff_roles WHERE customer_id = ?', (target,))
        else:
            db.execute('INSERT INTO staff_roles (customer_id, role) VALUES (?, ?) '
                       'ON CONFLICT(customer_id) DO UPDATE SET role = excluded.role', (target, role))
    return handler.customer_service().redirect(handler, ACCESS_PATH)
