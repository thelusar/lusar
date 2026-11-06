"""Administrator CSV imports and exports for the order workspace."""
import csv
import hashlib
import hmac
import io
import json
import re
import secrets
import shutil
import uuid
from datetime import date, datetime, time, timedelta, timezone
from email import policy
from email.parser import BytesParser
from html import escape
from tempfile import SpooledTemporaryFile
from urllib.parse import parse_qs, urlencode, urlsplit

import order_storage
import staff
import staff_ui as ui

TITLE = 'Импорт и экспорт'
PAGE_SIZE = 50
MAX_FILE = 2 * 1024 * 1024
MAX_LINES = 5000
REQUIRED = ('number', 'name', 'phone', 'sku', 'quantity')
CONTACT_LIMITS = {'name': 120, 'phone': 40, 'email': 254, 'address': 300}
COLUMNS = ('number', 'created', 'name', 'phone', 'email', 'address', 'sku', 'quantity')
REPORT_COLUMNS = (*COLUMNS, 'product_id', 'product', 'unit_price_amd', 'status', 'total_amd', 'remaining_total_amd', 'payment', 'source_number')
SORT = {'newest': ('DESC', 'Сначала новые'), 'oldest': ('ASC', 'Сначала старые')}
TRANSFER_NAMESPACE = uuid.UUID('14ec9f0d-882e-5a4a-b7f6-43daaf23bc60')
FORMULA = re.compile(r"^'*(?:\s*[=+@\-\uff1d\uff0b\uff20\uff0d]|[\t\r\n])")


def token(actor):
    return hmac.digest(actor.form_key, b'staff-order-transfer-v1', 'sha256').hex()


def filter_fields(fields, statuses):
    criteria = {key: fields.get(key, [''])[0] for key in ('from', 'to', 'status', 'sort')}
    criteria['sort'] = criteria['sort'] or 'newest'
    if criteria['status'] not in {'', *statuses} or criteria['sort'] not in SORT:
        raise ValueError('Проверьте статус и порядок сортировки.')
    try:
        dates = [date.fromisoformat(criteria[key]) if criteria[key] else None for key in ('from', 'to')]
        if any(value and not 1900 <= value.year <= 9998 for value in dates):
            raise ValueError
    except ValueError:
        raise ValueError('Проверьте даты периода.') from None
    if dates[0] and dates[1] and dates[0] > dates[1]:
        raise ValueError('Дата начала должна быть раньше даты окончания или совпадать с ней.')
    for key, value in zip(('from', 'to'), dates):
        criteria[key] = value.isoformat() if value else ''
    return criteria


def utc_value(moment):
    utc = moment.astimezone(timezone.utc)
    # SQLite's existing CURRENT_TIMESTAMP values are UTC without an offset.
    if order_storage.DATABASE_URL:
        return utc
    return utc.replace(tzinfo=None).isoformat(sep=' ', timespec='seconds')


def query_parts(criteria, selected=()):
    terms, params = [], []
    for key, comparison, offset in (('from', '>=', 0), ('to', '<', 1)):
        if criteria[key]:
            day = date.fromisoformat(criteria[key]) + timedelta(days=offset)
            terms.append(f'created {comparison} ?')
            params.append(utc_value(datetime.combine(day, time.min, ui.YEREVAN)))
    if criteria['status']:
        terms.append('status = ?')
        params.append(criteria['status'])
    if selected:
        terms.append('number IN (' + ', '.join('?' for _ in selected) + ')')
        params.extend(selected)
    where = ' WHERE ' + ' AND '.join(terms) if terms else ''
    direction = SORT[criteria['sort']][0]
    return where, f' ORDER BY created {direction}, number {direction}', params


def query_url(criteria, index):
    return staff.TRANSFER_PATH + '?' + escape(urlencode({**criteria, 'page': index}), quote=True)


def options(choices, selected):
    return ''.join(f'<option value="{key}"{" selected" if key == selected else ""}>{escape(label)}</option>'
                   for key, label in choices)


def transfer_page(handler, actor, statuses, *, message='', error=False):
    fields = parse_qs(urlsplit(handler.path).query)
    added, skipped = (fields.get(key, [''])[0] for key in ('added', 'skipped'))
    if not message and all(re.fullmatch(r'[0-9]{1,4}', count) for count in (added, skipped)):
        message = f'Добавлено заказов: {added}. Пропущено существующих: {skipped}.'
    try:
        criteria = filter_fields(fields, statuses)
    except ValueError as problem:
        criteria = filter_fields({}, statuses)
        message, error = str(problem), True
    try:
        page = max(1, int(fields.get('page', ['1'])[0]))
    except ValueError:
        page = 1
    where, order_by, params = query_parts(criteria)
    with order_storage.connect(handler.customer_service().database) as db:
        total = db.execute('SELECT COUNT(*) FROM orders' + where, params).fetchone()[0]
        last = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(page, last)
        rows = db.execute('SELECT number, status, created, payload FROM orders' + where + order_by + ' LIMIT ? OFFSET ?',
                          (*params, PAGE_SIZE, (page - 1) * PAGE_SIZE)).fetchall()
    path = staff.TRANSFER_PATH
    csrf = f'<input type="hidden" name="token" value="{token(actor)}">'
    hidden = ''.join(f'<input type="hidden" name="{key}" value="{escape(value, quote=True)}">' for key, value in criteria.items())
    filter_form = (f'<form class="staff-transfer-filters" method="get" action="{path}">'
                   f'<label>С даты<input type="date" name="from" value="{criteria["from"]}"></label>'
                   f'<label>По дату<input type="date" name="to" value="{criteria["to"]}"></label>'
                   f'<label>Статус<select name="status">{options([("", "Все статусы"), *statuses.items()], criteria["status"])}</select></label>'
                   f'<label>Сортировка<select name="sort">{options([(key, value[1]) for key, value in SORT.items()], criteria["sort"])}</select></label>'
                   f'<button>Применить</button><a class="staff-button" href="{path}">Сбросить</a></form>')
    table_rows = []
    for number, status, created, raw in rows:
        record = json.loads(raw)
        number_attr = escape(number, quote=True)
        name = escape(record['contact'].get('name') or 'Гость')
        table_rows.append(f'<tr><td><input type="checkbox" name="number" value="{number_attr}" aria-label="Выбрать заказ {number_attr}"></td>'
                          f'<th scope="row"><a href="{staff.ORDERS_PATH}?view=orders#{number_attr}">{number_attr}</a></th>'
                          f'<td>{ui.timestamp(created)}</td><td>{name}</td>'
                          f'<td><span class="staff-status-label" data-tone="{escape(status)}">{escape(statuses[status])}</span></td>'
                          f'<td>{ui.amount(record.get("total"))}</td></tr>')
    navigation = ''
    if last > 1:
        links = []
        if page > 1:
            links.append(f'<a class="staff-button" href="{query_url(criteria, page - 1)}">Назад</a>')
        links.append(f'<span>Страница {page} из {last}</span>')
        if page < last:
            links.append(f'<a class="staff-button" href="{query_url(criteria, page + 1)}">Дальше</a>')
        navigation = f'<nav class="staff-transfer-pagination" aria-label="Страницы заказов">{"".join(links)}</nav>'
    export_form = (f'<form method="post" action="{path}/export" data-order-export>{csrf}{hidden}'
                   '<div class="staff-transfer-actions"><button class="staff-primary" name="scope" value="all">Скачать по фильтрам</button>'
                   '<button name="scope" value="selected">Скачать выбранные</button></div>'
                   '<div class="staff-transfer-scroll" tabindex="0" role="region" aria-label="Заказы для выгрузки"><table class="staff-transfer-table">'
                   '<thead><tr><th scope="col"><input type="checkbox" aria-label="Выбрать все на странице" data-select-page hidden></th>'
                   '<th scope="col">Номер</th><th scope="col">Дата · Ереван</th><th scope="col">Клиент</th>'
                   f'<th scope="col">Статус</th><th scope="col">Сумма</th></tr></thead><tbody>{"".join(table_rows)}</tbody></table></div></form>') if rows else ui.empty(
                       'Заказов нет', 'Измените даты или статус, чтобы посмотреть другие заказы.', 'orders')
    feedback = (f'<p class="staff-notice{" staff-transfer-error" if error else ""}" role="{"alert" if error else "status"}">{escape(message)}</p>'
                if message else '')
    content = (f'<div class="staff-transfer"><h1>{TITLE}</h1>{feedback}<section class="staff-surface" aria-labelledby="export-title">'
               '<div class="staff-section-head"><div><h2 id="export-title">Выгрузка заказов</h2>'
               f'<p>Найдено заказов: {total} · В файле одна строка на товар</p></div></div>'
               f'{filter_form}{export_form}{navigation}</section>'
               '<section class="staff-surface" aria-labelledby="import-title"><div class="staff-section-head">'
               '<div><h2 id="import-title">Загрузка заказов</h2><p>Создаёт новые заявки. Существующие номера пропускаются.</p></div>'
               f'<a class="staff-button" href="{path}/template" download>Скачать шаблон CSV</a></div>'
               '<p>Укажите номер из вашей системы, имя, телефон, артикул и количество. Для нескольких товаров повторите номер и контакты. '
               'В таблице задайте для телефона и артикула текстовый формат, чтобы сохранить нули в начале. Дата (ГГГГ-ММ-ДД), email и адрес необязательны. '
               'Цены берутся из каталога. Статусы, оплаты и скидки из файла не переносятся.</p>'
               f'<form method="post" action="{path}/import" enctype="multipart/form-data">{csrf}'
               '<label>Файл CSV (UTF-8, до 2 МБ)<input type="file" name="file" accept=".csv,text/csv" required></label>'
               '<button class="staff-primary">Импортировать заказы</button></form></section></div>')
    return staff.page(handler, 400 if error else 200, TITLE, content, actor=actor, active='transfer')


def download(handler, filename, rows):
    with SpooledTemporaryFile(max_size=1024 * 1024) as file:
        with io.TextIOWrapper(file, encoding='utf-8-sig', newline='') as output:
            csv.writer(output, delimiter=';').writerows(rows)
            output.flush()
            length = file.tell()
            file.seek(0)
            handler.send_response(200)
            handler.send_header('Content-Type', 'text/csv; charset=utf-8')
            handler.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            handler.send_header('Cache-Control', 'no-store')
            handler.send_header('Content-Length', str(length))
            handler.end_headers()
            if handler.command != 'HEAD':
                shutil.copyfileobj(file, handler.wfile)


def report_rows(rows, statuses, payments):
    yield REPORT_COLUMNS
    for number, status, created, raw in rows:
        order = json.loads(raw)
        contact = order['contact']
        moment = ui.local_time(created)
        for line in order['items']:
            values = (number, moment.isoformat() if moment else '', *(contact.get(key, '') for key in CONTACT_LIMITS),
                      line['sku'], line['quantity'], line['id'], line['name'], line['unitPrice'], statuses[status],
                      order.get('total'), order.get('remainingAmount', order).get('total'),
                      payments.get(order.get('payment', {}).get('method'), ''), order.get('importReference', ''))
            yield tuple("'" + value if isinstance(value, str) and FORMULA.match(value) else value for value in values)


def get(handler, actor, path, statuses):
    if actor.role != 'admin':
        return handler.reply(403, {'error': 'Импорт и экспорт доступны администратору.'})
    if path.endswith('/template'):
        return download(handler, 'lusar-orders-template.csv', [COLUMNS])
    try:
        return transfer_page(handler, actor, statuses)
    except order_storage.DatabaseError:
        return handler.reply(503, {'error': 'Список заказов временно недоступен.'})


def read_fields(handler, importing):
    try:
        size = int(handler.headers.get('Content-Length', '0'))
        if not 0 < size <= (MAX_FILE + 4096 if importing else 8192):
            raise ValueError
        content_type = handler.headers.get_content_type()
        if not importing and content_type == 'application/x-www-form-urlencoded':
            return parse_qs(handler.rfile.read(size).decode(), max_num_fields=PAGE_SIZE + 6), None
        if not importing or content_type != 'multipart/form-data':
            raise ValueError
        header = 'Content-Type: ' + handler.headers['Content-Type'] + '\r\n\r\n'
        message = BytesParser(policy=policy.default).parsebytes(header.encode() + handler.rfile.read(size))
        parts = {}
        for part in message.iter_parts():
            name = part.get_param('name', header='content-disposition')
            if name not in {'token', 'file'} or name in parts or part.is_multipart():
                raise ValueError
            parts[name] = part.get_payload(decode=True)
        if message.defects or set(parts) != {'token', 'file'} or not 0 < len(parts['file']) <= MAX_FILE:
            raise ValueError
        return {'token': [parts['token'].decode()]}, parts['file']
    except (ValueError, TypeError):
        raise ValueError('Проверьте формат формы и размер файла.') from None


def import_orders(data):
    try:
        text = data.decode('utf-8-sig')
    except UnicodeError:
        raise ValueError('Сохраните файл как CSV UTF-8 и загрузите снова.') from None
    if '\x00' in text:
        raise ValueError('Файл должен быть в формате CSV UTF-8.')
    # The template uses semicolons. Accept comma-separated spreadsheets too.
    delimiter = ';' if ';' in text.partition('\n')[0] else ','
    reader = csv.DictReader(io.StringIO(text, newline=''), delimiter=delimiter, strict=True)
    groups = {}
    try:
        headers = reader.fieldnames or []
        if not set(REQUIRED) <= set(headers) or len(headers) != len(set(headers)):
            raise ValueError('В файле не хватает обязательных столбцов или есть повторяющиеся заголовки. Используйте шаблон CSV.')
        for index, row in enumerate(reader, 1):
            line_number = reader.line_num
            if index > MAX_LINES:
                raise ValueError(f'В одном файле допускается до {MAX_LINES} строк с товарами.')
            if None in row or None in row.values():
                raise ValueError(f'Строка {line_number}: число столбцов не совпадает с заголовком.')
            row = {key: (value[1:] if value.startswith("'") and FORMULA.match(value) else value).strip()
                   for key, value in row.items()}
            number = row['number'].upper()
            if not re.fullmatch(r'[A-Z0-9][A-Z0-9._/-]{0,63}', number):
                raise ValueError(f'Строка {line_number}: в номере допустимы латиница, цифры, точка, подчёркивание, слеш и дефис. Максимум 64 символа.')
            contact = {key: row.get(key, '') for key in CONTACT_LIMITS}
            if not contact['name'] or any(len(value) > CONTACT_LIMITS[key] for key, value in contact.items()):
                raise ValueError(f'Строка {line_number}: проверьте имя и длину контактных данных.')
            if not 7 <= len(re.sub(r'\D', '', contact['phone'])) <= 15:
                raise ValueError(f'Строка {line_number}: проверьте номер телефона.')
            if contact['email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', contact['email']):
                raise ValueError(f'Строка {line_number}: проверьте email.')
            created = row.get('created', '')
            if created:
                try:
                    moment = datetime.fromisoformat(created)
                    if not 1900 <= moment.year <= 9998:
                        raise ValueError
                    created = utc_value(moment if moment.tzinfo else moment.replace(tzinfo=ui.YEREVAN))
                except ValueError:
                    raise ValueError(f'Строка {line_number}: укажите дату в формате ГГГГ-ММ-ДД.') from None
            sku, product_id = row['sku'], row.get('product_id', '')
            if not (sku or product_id) or not re.fullmatch(r'[0-9]{1,3}', row['quantity']) or int(row['quantity']) < 1:
                raise ValueError(f'Строка {line_number}: проверьте артикул и количество от 1 до 999.')
            group = groups.setdefault(number, (contact, created, {}))
            if group[:2] != (contact, created):
                raise ValueError(f'Строка {line_number}: контакты и дата одного заказа должны совпадать.')
            items = group[2]
            key = (sku, product_id)
            if key in items or len(items) >= 100:
                raise ValueError(f'Строка {line_number}: в заказе допускается до 100 разных товаров. Укажите количество в одной строке.')
            items[key] = (int(row['quantity']), line_number)
    except csv.Error:
        raise ValueError(f'Строка {reader.line_num}: проверьте формат CSV.') from None
    if not groups:
        raise ValueError('В файле нет заказов.')
    return groups


def insert_orders(handler, actor, groups, order_amount):
    catalog = {}
    products = handler.catalog_data()['products']
    by_id = {product['id']: product for product in products}
    for product in products:
        catalog.setdefault(product['sku'].strip(), []).append(product)
    added = skipped = 0
    now = utc_value(datetime.now(timezone.utc))
    with order_storage.connect(handler.customer_service().database, write=True) as db:
        db.execute('BEGIN IMMEDIATE')
        if not staff.write_allowed(handler, actor, db, admin=True):
            return None
        for number, (contact, created, items) in groups.items():
            request_id = str(uuid.uuid5(TRANSFER_NAMESPACE, number))
            if db.execute('SELECT 1 FROM orders WHERE number = ? OR request_id = ?', (number, request_id)).fetchone():
                skipped += 1
                continue
            lines = []
            seen = set()
            for (sku, product_id), (quantity, line_number) in items.items():
                matches = catalog.get(sku, [])
                product = by_id.get(product_id) if product_id else (matches[0] if len(matches) == 1 else None)
                if not product or (sku and product['sku'].strip() != sku):
                    raise ValueError(f'Строка {line_number}: артикул должен однозначно совпадать с товаром в каталоге.')
                if product['id'] in seen:
                    raise ValueError(f'Строка {line_number}: товар повторяется. Укажите количество в одной строке.')
                seen.add(product['id'])
                lines.append({'id': product['id'], 'sku': product['sku'], 'name': product['name'],
                              'quantity': quantity, 'unitPrice': product['price']})
            payload = json.dumps({'contact': contact, 'items': lines, 'promo': '', 'importReference': number,
                                  **order_amount(lines, '')}, ensure_ascii=False)
            fingerprint = hashlib.sha256(payload.encode()).hexdigest()
            for _ in range(16):
                assigned = number if order_storage.ORDER_NUMBER.fullmatch(number) else f'LS-{100000 + secrets.randbelow(900000)}'
                inserted = db.execute('INSERT INTO orders (request_id, fingerprint, number, payload, created) VALUES (?, ?, ?, ?, ?) '
                                      'ON CONFLICT (number) DO NOTHING', (request_id, fingerprint, assigned, payload, created or now))
                if inserted.rowcount:
                    break
            else:
                raise ValueError('Не удалось присвоить номер заявки. Повторите импорт.')
            added += 1
    return added, skipped


def post(handler, actor, statuses, payments, order_amount):
    if actor.role != 'admin':
        return handler.reply(403, {'error': 'Импорт и экспорт доступны администратору.'})
    if not staff.require_origin(handler, actor):
        return
    importing = handler.path.endswith('/import')
    try:
        fields, data = read_fields(handler, importing)
        if not hmac.compare_digest(fields.get('token', [''])[0].encode(), token(actor).encode()):
            return handler.reply(403, {'error': 'Откройте раздел заново и повторите действие.'})
        if importing:
            counts = insert_orders(handler, actor, import_orders(data), order_amount)
            if counts is None:
                return
            query = urlencode({'added': counts[0], 'skipped': counts[1]})
            return handler.customer_service().redirect(handler, f'{staff.TRANSFER_PATH}?{query}')
        criteria = filter_fields(fields, statuses)
        scope = fields.get('scope')
        if scope not in (['all'], ['selected']):
            raise ValueError('Выберите способ выгрузки.')
        selected = fields.get('number', []) if scope == ['selected'] else []
        if scope == ['selected'] and (not 0 < len(selected) <= PAGE_SIZE or
                                      any(not order_storage.ORDER_NUMBER.fullmatch(number) for number in selected)):
            raise ValueError('Отметьте заказы, которые нужно скачать.')
        where, order_by, params = query_parts(criteria, selected)
        with order_storage.connect(handler.customer_service().database) as db:
            rows = db.execute('SELECT number, status, created, payload FROM orders' + where + order_by, params)
            return download(handler, 'lusar-orders.csv', report_rows(rows, statuses, payments))
    except ValueError as problem:
        return transfer_page(handler, actor, statuses, message=str(problem), error=True)
    except order_storage.DatabaseError:
        return handler.reply(503, {'error': 'Операция с заказами временно недоступна. Повторите попытку позже.'})
