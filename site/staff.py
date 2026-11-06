"""Staff access and order audit records, independent of storefront account privileges."""
import hmac
import html
import os
import uuid
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode

import order_storage
import staff_ui as ui

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


def page(handler, status, title, content, *, actor=None, active=None):
    layout = ui.layout(title, content, actor=actor, active=active, role_label=ROLE_NAMES[actor.role] if actor and actor.role else '')
    body = ('<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)} · LUSAR</title><script src="/theme.js"></script>'
            '<link rel="stylesheet" href="/site.css"><link rel="stylesheet" href="/staff.css">'
            f'<script src="/staff.js" defer></script></head><body class="staff-page">{layout}</body></html>').encode()
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
                    '<p>Передайте администратору код аккаунта, чтобы получить доступ.</p>'
                    f'<p><code>{html.escape(actor.id)}</code></p><a class="staff-button" href="{url}">Войти другим аккаунтом</a>')
    return page(handler, 401, 'Панель сотрудников',
                f'<p>Войдите в рабочий аккаунт, чтобы открыть заказы.</p><a class="staff-button staff-primary" href="{url}">Войти в LUSAR</a>')


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
        items.append(f'<li><div><strong>{html.escape(ACTION_NAMES[action])}</strong><span>{ui.timestamp(changed)}</span></div>'
                     f'<p>{html.escape(detail)}</p><small>{html.escape(email)}</small></li>')
    return (f'<details class="staff-history"><summary><span>Журнал заказа <small>{len(events)}</small></span>'
            f'{ui.icon("chevron")}</summary><ol>{"".join(items)}</ol></details>')


def access_token(actor):
    return hmac.digest(actor.form_key, b'staff-access-v1', 'sha256').hex()


def form_error(handler, status, message, destination, actor):
    if 'text/html' not in handler.headers.get('Accept', ''):
        return handler.reply(status, {'error': message})
    return page(handler, status, 'Не удалось сохранить',
                ui.heading('Не удалось сохранить', message)
                + f'<a class="staff-button" href="{destination}">Вернуться к разделу</a>',
                actor=actor, active='access' if destination == ACCESS_PATH else 'orders')


def role_options(selected):
    return ''.join(f'<option value="{key}"{" selected" if key == selected else ""}>{name}</option>'
                   for key, name in ROLE_NAMES.items())


def access_page(handler, actor):
    if actor.role != 'admin':
        return page(handler, 403, 'Доступ сотрудников',
                    ui.heading('Доступ сотрудников', 'Назначать роли может администратор.'), actor=actor)
    owner = owner_id()
    with order_storage.connect(handler.customer_service().database) as db:
        rows = db.execute('SELECT customers.email, staff_roles.role, customers.id FROM customers '
                          'LEFT JOIN staff_roles ON customers.id = staff_roles.customer_id '
                          'WHERE customers.id = ? OR staff_roles.role IS NOT NULL ORDER BY customers.email', (owner,)).fetchall()
    rows.sort(key=lambda row: row[2] != owner)
    form_start = f'<form method="post" action="{ACCESS_PATH}"><input type="hidden" name="token" value="{access_token(actor)}">'
    staff_list = []
    for email, role, user_id in rows:
        label = 'Основной администратор' if user_id == owner else ROLE_NAMES[role]
        actions = ''
        if user_id not in {actor.id, owner}:
            edit_form = form_start + f'<input type="hidden" name="account" value="{html.escape(user_id, quote=True)}">'
            actions = (f'<details class="staff-role-edit"><summary>Управлять {ui.icon("chevron")}</summary>'
                       f'<div class="staff-role-actions">{edit_form}<label>Роль <select name="role">{role_options(role)}</select></label>'
                       '<button class="staff-primary">Сохранить роль</button></form>'
                       f'<details class="staff-revoke"><summary>Отозвать доступ</summary><p>Сотрудник сразу потеряет доступ к панели.</p>'
                       f'{edit_form}<button class="staff-danger" name="role" value="remove">Подтвердить отзыв</button>'
                       '</form></details></div></details>')
        marker = '<small>Ваш аккаунт</small>' if user_id == actor.id else ''
        staff_list.append(f'<li class="staff-person"><div class="staff-person-info"><span class="staff-avatar">{ui.icon("account")}</span>'
                          f'<div><strong>{html.escape(email)}</strong>{marker}</div></div>'
                          f'<span class="staff-badge">{label}</span>{actions}</li>')
    feedback = ui.notice(handler, {'access': 'Доступ сотрудника сохранён.', 'removed': 'Доступ сотрудника отозван.'})
    people = f'<ul class="staff-people">{"".join(staff_list)}</ul>'
    content = (ui.heading('Сотрудники', 'Выдавайте доступ к панели и меняйте роли сотрудников.') + feedback
               + '<div class="staff-access-grid"><section class="staff-surface staff-grant" aria-labelledby="grant-title">'
               f'<span class="staff-tile-icon">{ui.icon("team")}</span><h2 id="grant-title">Выдать доступ</h2>'
               f'<p>Сотрудник входит в LUSAR и открывает <a href="{ORDERS_PATH}">панель заказов</a>. Там он увидит свой код аккаунта.</p>'
               f'{form_start}<label>Код аккаунта<input name="account" required maxlength="36" autocomplete="off" spellcheck="false" '
               'placeholder="Вставьте код сотрудника"></label>'
               f'<label>Роль<select name="role">{role_options("manager")}</select></label>'
               '<button class="staff-primary">Выдать доступ</button></form></section>'
               '<section class="staff-surface staff-permissions" aria-labelledby="roles-title"><h2 id="roles-title">Что доступно по ролям</h2>'
               '<dl><dt>Менеджер</dt><dd>Просмотр заказов, смена статуса, отметки оплаты и возвратов.</dd>'
               '<dt>Администратор</dt><dd>Работа с заказами, выдача доступа, смена ролей и отзыв доступа.</dd></dl></section></div>'
               '<section class="staff-surface staff-team" aria-labelledby="team-title"><div class="staff-section-head">'
               f'<h2 id="team-title">Команда</h2><span class="staff-badge">{len(staff_list)}</span></div>{people}</section>')
    return page(handler, 200, 'Сотрудники', content, actor=actor, active='access')


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
        return form_error(handler, 400, 'Проверьте код аккаунта и роль.', ACCESS_PATH, actor)
    if not hmac.compare_digest(token.encode(), access_token(actor).encode()):
        return handler.reply(403, {'error': 'Откройте страницу доступа и повторите действие.'})
    if target in {actor.id, owner_id()}:
        return form_error(handler, 409, 'Менять собственную роль и роль основного администратора нельзя.', ACCESS_PATH, actor)
    with order_storage.connect(handler.customer_service().database, write=True) as db:
        db.execute('BEGIN IMMEDIATE')
        if not write_allowed(handler, actor, db, admin=True):
            return
        if not db.execute('SELECT 1 FROM customers WHERE id = ?', (target,)).fetchone():
            return form_error(handler, 404, 'Аккаунт с таким кодом не найден. Уточните код у сотрудника.', ACCESS_PATH, actor)
        if role == 'remove':
            db.execute('DELETE FROM staff_roles WHERE customer_id = ?', (target,))
        else:
            db.execute('INSERT INTO staff_roles (customer_id, role) VALUES (?, ?) '
                       'ON CONFLICT(customer_id) DO UPDATE SET role = excluded.role', (target, role))
    result = 'removed' if role == 'remove' else 'access'
    return handler.customer_service().redirect(handler, f'{ACCESS_PATH}?saved={result}')
