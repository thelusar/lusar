"""Local preview server. Order data stays outside the public directory."""
import hashlib
import base64
import html
import hmac
import json
import math
import os
import re
import secrets
import sqlite3
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from contextlib import closing
from urllib.parse import parse_qs, quote, unquote, urlsplit
import order_storage
import customer_accounts
import staff
import staff_ui as ui
from threading import Lock
from loyalty import FIRST_ORDER_PERCENT
from sync_catalog import revision
from catalog_runtime import CatalogUnavailable

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "orders.local.sqlite"
CATALOG = ROOT.parent / "storefront.json"
PROMOTIONS = json.loads((ROOT / "promotions.json").read_text(encoding="utf-8"))
BRANDS = json.loads((ROOT / "brands.json").read_text(encoding="utf-8"))
STATUS_LABELS = {"new": "Новая заявка", "in_progress": "В процессе",
                 "completed": "Выполнено", "cancelled": "Отменено"}
TRANSITIONS = {"new": ("in_progress", "cancelled"), "in_progress": ("completed", "cancelled"),
               "completed": ("cancelled",), "cancelled": ()}
MANAGER_FORM_KEY = secrets.token_bytes(32)
CUSTOMER_SERVICE_LOCK = Lock()
PAYMENT_METHODS = {"store": "В магазине", "receipt": "По чеку менеджера", "delivery": "При получении"}


def status_token(number, status, key=MANAGER_FORM_KEY):
    return hmac.new(key, f"{number}:{status}".encode(), "sha256").hexdigest()


def adjustment_token(number, status, payload, key=MANAGER_FORM_KEY):
    return status_token(number, status + ":" + hashlib.sha256(payload.encode()).hexdigest(), key)


def apply_adjustment(order, status, action, value, quantity):
    if action == "payment":
        if status not in {"in_progress", "completed"} or order.get("payment") or value not in PAYMENT_METHODS:
            raise ValueError("Оплату нельзя отметить для этого заказа.")
        if order.get("total") is None:
            raise ValueError("Сначала нужно подтвердить итоговую сумму.")
        order["payment"] = {"method": value, "amount": order["total"]}
        return status
    if action == "refund_paid":
        try:
            index = int(value)
            if index < 0:
                raise IndexError
            entry = order.get("returns", [])[index]
        except (ValueError, IndexError):
            raise ValueError("Возврат не найден.") from None
        if entry["refundDue"] <= 0 or entry.get("refundPaid"):
            raise ValueError("По этому возврату нет суммы к выплате.")
        entry["refundPaid"] = True
        return status
    if action != "return" or status != "completed" or not order.get("payment"):
        raise ValueError("Возврат доступен для оплаченного выполненного заказа.")
    remaining = [dict(line) for line in order.get("remainingItems", order["items"])]
    line = next((line for line in remaining if line["id"] == value), None)
    if line is None or not 1 <= quantity <= line["quantity"]:
        raise ValueError("Проверьте товар и количество для возврата.")
    line["quantity"] -= quantity
    remaining = [line for line in remaining if line["quantity"]]
    amount = order_amount(remaining, order.get("promo", ""), account_percent=order.get("accountPercent", 0),
                          first_order=bool(order.get("firstOrderApplied", order.get("firstOrderDiscount"))))
    previous = order.get("remainingAmount", order)
    refund = previous["total"] - amount["total"]
    order.setdefault("returns", []).append({"id": value, "quantity": quantity, "refundDue": refund})
    order["remainingItems"] = remaining
    order["remainingAmount"] = amount
    return status if remaining else "cancelled"

def order_amount(lines, promo, *, account_percent=0, first_order=False):
    # Account discounts must come from the authenticated customer's record.
    # first_order must come from a server-side eligibility check.
    if first_order and (promo or account_percent):
        raise ValueError("Скидка на первый заказ применяется отдельно.")
    if type(account_percent) is not int or not 0 <= account_percent <= 100:
        raise ValueError("Неверный размер скидки кабинета.")
    if promo and promo not in PROMOTIONS:
        raise ValueError("Промокод не найден.")
    if any(line["unitPrice"] is None for line in lines):
        if promo or account_percent or first_order:
            raise ValueError("Менеджер подтвердит цену и скидку по этой заявке.")
        return {"subtotal": None, "accountDiscount": 0, "promoDiscount": 0, "firstOrderDiscount": 0,
                "discount": 0, "total": None}
    subtotal = sum(line["unitPrice"] * line["quantity"] for line in lines)
    account_discount = int(subtotal * account_percent // 100)
    remaining = subtotal - account_discount
    nominal = PROMOTIONS.get(promo, 0)
    promo_discount = int(remaining // 10) if nominal == "10%" else min(nominal, int(remaining // 5))
    first_order_discount = int(subtotal * FIRST_ORDER_PERCENT // 100) if first_order else 0
    discount = account_discount + promo_discount + first_order_discount
    return {"subtotal": subtotal, "accountDiscount": account_discount, "promoDiscount": promo_discount,
            "firstOrderDiscount": first_order_discount, "discount": discount, "total": subtotal - discount}

class Handler(SimpleHTTPRequestHandler):
    local_manager_preview = True

    def __init__(self, *args, **kwargs):
        service = getattr(args[2], "catalog_service", None)
        if service:
            with service.acquire() as generation:
                self.catalog_generation = generation
                super().__init__(*args, directory=str(generation.directory), **kwargs)
        else:
            self.catalog_generation = None
            super().__init__(*args, directory=str(ROOT / "dist"), **kwargs)

    def customer_service(self):
        with CUSTOMER_SERVICE_LOCK:
            if not hasattr(self.server, "customer_accounts"):
                self.server.customer_accounts = customer_accounts.Service(DATABASE)
            return self.server.customer_accounts

    def log_request(self, code='-', size='-'):
        if urlsplit(getattr(self, 'path', '')).path.startswith('/auth/'):
            self.log_message('"%s %s" %s %s', self.command, urlsplit(self.path).path, code, size)
        else:
            super().log_request(code, size)

    def catalog_data(self):
        return self.catalog_generation.data if self.catalog_generation else json.loads(CATALOG.read_text(encoding="utf-8-sig"))

    def end_headers(self):
        path = urlsplit(getattr(self, "path", "")).path
        if not any(header.lower().startswith(b"cache-control:") for header in getattr(self, "_headers_buffer", [])):
            dynamic = not Path(path).suffix or path.endswith(".html") or Path(path).name in {"cart.js", "search.js", "ai-preview.js", "support.js"}
            self.send_header("Cache-Control", "no-store" if dynamic else "private, no-cache")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def reply(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def manager_actor(self, destination=staff.ORDERS_PATH):
        service = self.customer_service()
        if service.config.enabled:
            try:
                actor = staff.identity(self)
            except order_storage.DatabaseError:
                self.reply(503, {"error": "Панель сотрудников временно недоступна."})
                return None
            if actor and actor.role:
                return actor
            if self.command == "POST":
                self.reply(403, {"error": "Войдите в аккаунт с правами сотрудника."})
            else:
                staff.sign_in_page(self, destination, actor)
            return None
        password = os.environ.get("LUSAR_LOCAL_MANAGER_PASSWORD") if self.local_manager_preview else None
        if not password or self.client_address[0] not in {"127.0.0.1", "::1"}:
            staff.sign_in_page(self, destination, None)
            return None
        expected = b"Basic " + base64.b64encode(f"manager:{password}".encode())
        if not secrets.compare_digest(self.headers.get("Authorization", "").encode(), expected):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="LUSAR local preview"')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return None
        service.ensure()
        return staff.Actor(None, "Локальный просмотр", "manager", MANAGER_FORM_KEY)

    def redirect_permanently(self, location):
        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def public_redirect(self):
        service = getattr(self.server, "catalog_service", None)
        version = parse_qs(urlsplit(self.path).query).get("catalog", [None])[0]
        if service and version and urlsplit(self.path).path in {"/cart.js", "/search.js", "/ai-preview.js", "/support.js"}:
            previous = self.directory
            with service.acquire(version) as generation:
                self.directory = str(generation.directory)
                try:
                    return self.static_redirect()
                finally:
                    self.directory = previous
        return self.static_redirect()

    def static_redirect(self):
        url = urlsplit(self.path)
        if url.path == "/catalog.html":
            product_id = parse_qs(url.query).get("product", [""])[0]
            if not product_id:
                return self.redirect_permanently("/catalog")
            catalog = self.catalog_data()
            if any(item["id"] == product_id for item in catalog["products"]):
                return self.redirect_permanently("/catalog/product/" + quote(product_id, safe=""))
            return self.send_error(404, "Product unavailable")
        root = Path(self.directory).resolve()
        path = unquote(url.path)
        brand_id = path.removesuffix("/index.html").rstrip("/").removeprefix("/brands/")
        if path.startswith("/brands/") and brand_id in BRANDS:
            destination = BRANDS[brand_id]["path"]
            if (root / "brands" / destination / "index.html").is_file():
                return self.redirect_permanently("/brands/" + destination)
        target = (root / path.lstrip("/")).resolve()
        if not target.is_relative_to(root):
            return self.send_error(404)
        if path.startswith("/catalog/product/") and not target.is_file() and not (target / "index.html").is_file():
            body = (root / "catalog/unavailable/index.html").read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return
        suffix = "?" + url.query if url.query else ""
        if path.endswith("/index.html") and target.is_file():
            clean = path.removesuffix("/index.html") or "/"
            return self.redirect_permanently(quote(clean, safe="/") + suffix)
        if (target / "index.html").is_file():
            if path != "/" and path.endswith("/"):
                return self.redirect_permanently(quote(path.rstrip("/"), safe="/") + suffix)
            self.path = quote(path.rstrip("/") + "/index.html", safe="/")
        return super().do_HEAD() if self.command == "HEAD" else super().do_GET()

    def do_HEAD(self):
        if urlsplit(self.path).path.rstrip('/') in {staff.ORDERS_PATH.rstrip('/'), staff.ACCESS_PATH}:
            return self.do_GET()
        return self.public_redirect()

    def do_GET(self):
        if self.customer_service().get(self):
            return
        if urlsplit(self.path).path == "/api/catalog":
            data = self.catalog_data()
            return self.reply(200, {**data, "revision": revision(data)})
        path = urlsplit(self.path).path.rstrip('/')
        if path == staff.ACCESS_PATH:
            actor = self.manager_actor(staff.ACCESS_PATH)
            if actor:
                try:
                    return staff.access_page(self, actor)
                except order_storage.DatabaseError:
                    return self.reply(503, {"error": "Список сотрудников временно недоступен."})
            return
        if path != staff.ORDERS_PATH.rstrip('/'):
            return self.public_redirect()
        actor = self.manager_actor()
        if not actor:
            return
        self.manager_orders(actor)

    def manager_orders(self, actor):
        try:
            with order_storage.connect(DATABASE) as db:
                rows = db.execute("SELECT number, status, created, payload FROM orders ORDER BY created DESC").fetchall()
                events = db.execute("SELECT number, action, detail, actor_email, changed "
                                    "FROM order_staff_activity ORDER BY id DESC").fetchall()
        except order_storage.DatabaseError:
            return self.reply(503, {"error": "Список заказов временно недоступен."})
        history = {}
        for number, *event in events:
            history.setdefault(number, []).append(event)
        counts = dict.fromkeys(STATUS_LABELS, 0)
        cards = []
        for number, status, created, raw in rows:
            if status in counts:
                counts[status] += 1
            order = json.loads(raw)
            contact = {key: html.escape(value) for key, value in order["contact"].items() if value}
            lines = "".join(
                f'<li><div>{html.escape(line["name"])}<small>Арт. {html.escape(line["sku"])}</small></div>'
                f'<strong>{line["quantity"]} шт.</strong></li>'
                for line in order["items"]
            )
            number_attr = html.escape(number, quote=True)
            status_attr = html.escape(status, quote=True)
            total = ui.amount(order.get("total"))
            contact_fields = ''.join(f'<dt>{label}</dt><dd>{contact[key]}</dd>'
                                     for key, label in (("name", "Имя"), ("phone", "Телефон"), ("email", "Email"), ("address", "Адрес"))
                                     if key in contact)
            contact_name = contact.get("name") or "Гость"
            phone = contact.get("phone", "")
            status_label = html.escape(STATUS_LABELS.get(status, status))
            units = sum(line["quantity"] for line in order["items"])
            targets = TRANSITIONS.get(status, ())
            if order.get("payment"):
                targets = tuple(target for target in targets if target != "cancelled")
            options = "".join(f'<option value="{target}">{STATUS_LABELS[target]}</option>' for target in targets)
            controls = (f'<form class="staff-status-form" method="post" action="/manager/orders/status">'
                        f'<input type="hidden" name="number" value="{number_attr}">'
                        f'<input type="hidden" name="current" value="{status_attr}">'
                        f'<input type="hidden" name="token" value="{status_token(number, status, actor.form_key)}">'
                        '<label class="staff-status-control"><span>Статус заказа</span>'
                        f'<span class="staff-status-picker"><select name="target" required>'
                        f'<option value="" disabled selected>{status_label}</option>{options}</select>{ui.icon("chevron")}</span></label>'
                        '<button class="staff-primary">Сохранить статус</button>'
                        '<span class="staff-save-state" role="status" data-save-state hidden></span></form>') if options else (
                            f'<div class="staff-status-static"><span>Статус заказа</span><strong>{status_label}</strong></div>')
            cards.append(
                f'<details class="staff-order" id="{number_attr}" data-status="{status_attr}"><summary class="staff-order-row">'
                f'<span class="staff-order-id"><strong>{number_attr}</strong>{ui.timestamp(created)}</span>'
                f'<span class="staff-order-customer"><strong>{contact_name}</strong><small>{phone}</small></span>'
                f'<span class="staff-order-status"><span class="staff-status-label" data-tone="{status_attr}">'
                f'<span class="staff-dot"></span>{status_label}</span></span>'
                f'<span class="staff-order-amount"><strong class="staff-total">{total}</strong><small>{units} шт.</small></span>'
                f'<span class="staff-order-chevron">{ui.icon("chevron")}</span></summary>'
                f'<div class="staff-order-details"><div class="staff-detail-header">{controls}</div><div class="staff-detail-grid">'
                f'<div><section><h3 class="staff-detail-title">{ui.icon("box")}Состав заказа</h3><ul class="staff-items">{lines}</ul></section>'
                f'{staff.history_markup(history.get(number))}</div>'
                f'<div><section><h3 class="staff-detail-title">{ui.icon("account")}Контакты клиента</h3>'
                f'<dl class="staff-contact">{contact_fields}</dl></section>'
                f'<section><h3 class="staff-detail-title">{ui.icon("payment")}Оплата и возвраты</h3>'
                f'{self.adjustment_controls(number, status, raw, order, actor.form_key)}</section></div></div></div></details>')
        filters = f'<button type="button" data-filter="" aria-pressed="true">Все <strong>{len(rows)}</strong></button>'
        filters += ''.join(f'<button type="button" data-filter="{key}" aria-pressed="false"><span>{STATUS_LABELS[key]}</span>'
                           f'<strong>{count}</strong></button>' for key, count in counts.items())
        feedback = ui.notice(self, {'status': 'Статус заказа обновлён.', 'payment': 'Оплата отмечена.',
                                    'return': 'Возврат сохранён.', 'refund_paid': 'Выплата отмечена.'})
        empty = ui.empty('Заказов пока нет', 'Новые заявки с сайта появятся здесь.', 'orders')
        no_match = ui.empty('Заказы не найдены', 'Попробуйте изменить запрос или сбросить фильтр.', 'search')
        listing = ('<div class="staff-table-head" aria-hidden="true"><span>Номер · время Еревана</span><span>Клиент</span>'
                   f'<span>Статус</span><span>Сумма</span></div>{"".join(cards)}'
                   f'<div id="staff-no-match" hidden>{no_match}</div>') if cards else empty
        cancel_dialog = ('<dialog id="staff-cancel" class="staff-cancel-dialog" aria-labelledby="staff-cancel-title">'
                         '<form method="dialog"><h2 id="staff-cancel-title">Отменить заявку?</h2>'
                         '<p>После отмены заявка закроется.</p><div><button value="back" autofocus>Назад</button>'
                         '<button value="confirm" class="staff-danger">Отменить заявку</button></div></form></dialog>')
        content = (ui.heading('Заказы', 'Обрабатывайте заявки, отмечайте оплату и оформляйте возвраты.') + feedback
                   + '<p id="staff-save-feedback" class="staff-notice" role="status" hidden></p>'
                   '<section class="staff-surface staff-list" aria-labelledby="orders-title"><div class="staff-section-head">'
                   '<div><h2 id="orders-title">Список заказов</h2>'
                   f'<p id="staff-result-count" aria-live="polite">Всего заявок: {len(rows)}</p></div>'
                   '<div class="staff-filter-tools" hidden><label class="staff-search">'
                   f'{ui.icon("search")}<input type="search" id="staff-order-search" aria-label="Поиск заказов" '
                   'placeholder="Номер, имя или телефон"></label>'
                   '<button type="button" id="staff-reset" hidden>Сбросить</button></div></div>'
                   f'<div class="staff-filters" role="group" aria-label="Фильтр по статусу" hidden>{filters}</div>'
                   f'{listing}</section>{cancel_dialog}')
        return staff.page(self, 200, "Заказы LUSAR", content, actor=actor, active='orders')

    def do_POST(self):
        if self.customer_service().post(self):
            return
        if self.path == "/api/order-status":
            return self.guest_order_status()
        if self.path == "/manager/orders/adjust":
            return self.adjust_order()
        if self.path == "/manager/orders/status":
            return self.change_order_status()
        if self.path == staff.ACCESS_PATH:
            actor = self.manager_actor(staff.ACCESS_PATH)
            if actor:
                try:
                    return staff.update_access(self, actor)
                except order_storage.DatabaseError:
                    return staff.form_error(self, 503, "Повторите попытку через несколько минут.", staff.ACCESS_PATH, actor)
            return
        if self.path != "/api/orders":
            return self.reply(404, {"error": "Страница не найдена."})
        if self.headers.get_content_type() != "application/json":
            return self.reply(415, {"error": "Неверный формат заявки."})
        try:
            account_service = self.customer_service()
            session = account_service.session(self)
            if session:
                account_service.require_write(self, session)
            elif self.headers.get('X-Lusar-CSRF'):
                return self.reply(401, {"error": "Войдите в личный кабинет."})
            elif self.headers.get('Origin') and self.headers.get('Origin') != (account_service.config.origin or 'http://' + self.headers.get('Host', '')):
                return self.reply(403, {"error": "Откройте оформление заявки на сайте LUSAR."})
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16000:
                raise ValueError
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError
            request_id = str(uuid.UUID(data["requestId"]))
            discount_mode = data.get('discountMode', 'none')
            if discount_mode not in {'none', 'first', 'loyalty'}:
                raise ValueError
            if discount_mode != 'none' and not session:
                return self.reply(401, {"error": "Войдите в личный кабинет, чтобы использовать скидку."})
            promo = data.get("promo", "").strip().upper()
            if len(promo) > 32:
                raise ValueError
            contact = {key: data.get(key, "").strip() for key in ("name", "phone", "email", "address")}
            limits = {"name": 120, "phone": 40, "email": 254, "address": 300}
            if any(len(contact[key]) > limit for key, limit in limits.items()):
                raise ValueError
            if not contact["name"] or not 7 <= len(re.sub(r"\D", "", contact["phone"])) <= 15:
                raise ValueError
            if contact["email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact["email"]):
                raise ValueError
            cart = data["cart"]
            if not isinstance(cart, dict) or not 0 < len(cart) <= 100:
                raise ValueError
            if any(type(quantity) is not int or not 1 <= quantity <= 999 for quantity in cart.values()):
                raise ValueError
            displayed_prices = data["displayedPrices"]
            if not isinstance(displayed_prices, dict) or not displayed_prices.keys() <= cart.keys():
                raise ValueError
            if any(price is not None and (type(price) not in (int, float) or not math.isfinite(price) or price < 0)
                   for price in displayed_prices.values()):
                raise ValueError
        except customer_accounts.AccountError as error:
            return self.reply(error.status, {"error": str(error)})
        except order_storage.DatabaseError:
            return self.reply(503, {"error": "Личный кабинет временно недоступен. Попробуйте позже."})
        except (AttributeError, ValueError, KeyError, TypeError):
            return self.reply(400, {"error": "Проверьте имя, телефон, email и состав корзины."})

        identity = session['id'] if session else None
        fingerprint_parts = [contact, cart, promo, displayed_prices]
        if identity or discount_mode != 'none':
            fingerprint_parts += [identity, discount_mode]
        fingerprint = hashlib.sha256(json.dumps(fingerprint_parts, sort_keys=True).encode()).hexdigest()
        try:
            account_service.ensure()
        except order_storage.DatabaseError:
            return self.reply(503, {"error": "Не удалось сохранить заявку. Попробуйте позже."})
        catalog_error = None
        try:
            service = getattr(self.server, "catalog_service", None)
            catalog = service.refresh().data if service else self.catalog_data()
        except CatalogUnavailable as error:
            catalog_error = str(error)
            catalog = {"products": []}
        products = {item["id"]: item for item in catalog["products"]}
        try:
            with order_storage.connect(DATABASE, write=True) as db:
                db.execute("""CREATE TABLE IF NOT EXISTS orders (
                    request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                    number TEXT NOT NULL UNIQUE, payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new', created TEXT DEFAULT CURRENT_TIMESTAMP)""")
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("SELECT number, fingerprint, payload, customer_id FROM orders WHERE request_id = ?", (request_id,)).fetchone()
                if existing:
                    if existing[1] != fingerprint or existing[3] != identity:
                        return self.reply(409, {"error": "Заявка уже сохранена с другими данными. Обновите страницу."})
                    token = json.loads(existing[2]).get("trackingToken")
                    return self.reply(200, {"number": existing[0], "trackingToken": token})
                if catalog_error:
                    return self.reply(503, {"error": catalog_error})
                if any(key not in products for key in cart):
                    return self.reply(409, {"error": "Состав каталога изменился. Проверьте корзину."})
                if any(key not in displayed_prices or displayed_prices[key] != products[key]["price"] for key in cart):
                    return self.reply(409, {"error": "Цена одного или нескольких товаров изменилась. Обновите страницу и проверьте корзину."})
                lines = [{"id": key, "sku": products[key]["sku"], "name": products[key]["name"],
                          "quantity": quantity, "unitPrice": products[key]["price"]}
                         for key, quantity in cart.items()]
                tracking_token = secrets.token_urlsafe(32)
                account_percent = 0
                first_order = False
                if session:
                    if not account_service.session(self, db):
                        return self.reply(401, {"error": "Войдите в личный кабинет."})
                    benefits = account_service.loyalty(db, identity)
                    if discount_mode == 'first':
                        if not benefits['firstOrderAvailable']:
                            return self.reply(409, {"error": "Скидка на первый заказ сейчас недоступна. Обновите кабинет."})
                        first_order = True
                    elif discount_mode == 'loyalty':
                        account_percent = benefits['discountPercent']
                try:
                    amount = order_amount(lines, promo, account_percent=account_percent, first_order=first_order)
                except ValueError as error:
                    return self.reply(422, {"error": str(error)})
                payload = json.dumps({"contact": contact, "items": lines, "promo": promo, "trackingToken": tracking_token,
                                      "accountPercent": account_percent, "firstOrderApplied": first_order, **amount},
                                     ensure_ascii=False)
                for _ in range(16):
                    # Checkout tabs opened before this release still expect the old format.
                    suffix = str(100000 + secrets.randbelow(900000)) if data.get("numberFormat") == "short" else secrets.token_hex(6).upper()
                    number = f"LS-{suffix}"
                    inserted = db.execute(
                        "INSERT INTO orders (request_id, fingerprint, number, payload, customer_id) VALUES (?, ?, ?, ?, ?) "
                        "ON CONFLICT (number) DO NOTHING", (request_id, fingerprint, number, payload, identity))
                    if inserted.rowcount == 1:
                        break
                else:
                    return self.reply(503, {"error": "Не удалось присвоить номер заявки. Повторите отправку."})
                db.execute("""CREATE TABLE IF NOT EXISTS order_notifications (
                    number TEXT PRIMARY KEY, sent_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_attempt TEXT, last_error TEXT)""")
                db.execute("INSERT INTO order_notifications (number) VALUES (?)", (number,))
        except order_storage.DatabaseError:
            return self.reply(503, {"error": "Сохранение временно недоступно. Повторите отправку."})
        return self.reply(201, {"number": number, "trackingToken": tracking_token})

    def guest_order_status(self):
        if self.headers.get_content_type() != "application/json":
            return self.reply(415, {"error": "Неверный формат запроса."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1000:
                raise ValueError
            data = json.loads(self.rfile.read(size))
            number, key = data["number"], data["key"]
            if not order_storage.ORDER_NUMBER.fullmatch(number) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", key):
                raise ValueError
        except (ValueError, TypeError, KeyError):
            return self.reply(400, {"error": "Проверьте приватную ссылку."})
        missing = {"error": "Заявка не найдена. Проверьте приватную ссылку."}
        if not order_storage.available(DATABASE):
            return self.reply(404, missing)
        try:
            with order_storage.connect(DATABASE) as db:
                row = db.execute("SELECT status, payload FROM orders WHERE number = ?", (number,)).fetchone()
        except order_storage.DatabaseError:
            return self.reply(503, {"error": "Статус временно недоступен. Попробуйте позже."})
        saved = json.loads(row[1]).get("trackingToken") if row else None
        if not saved or not secrets.compare_digest(saved, key):
            return self.reply(404, missing)
        return self.reply(200, {"number": number, "status": STATUS_LABELS.get(row[0], row[0])})

    def change_order_status(self):
        actor = self.manager_actor()
        if not actor or not staff.require_origin(self, actor):
            return
        if self.headers.get_content_type() != "application/x-www-form-urlencoded":
            return self.reply(415, {"error": "Неверный формат формы."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 2000:
                raise ValueError
            fields = parse_qs(self.rfile.read(size).decode(), strict_parsing=True, max_num_fields=4)
            number, current, target, token = (fields[name][0] for name in ("number", "current", "target", "token"))
        except (ValueError, KeyError):
            return self.reply(400, {"error": "Проверьте данные формы."})
        if not hmac.compare_digest(token.encode(), status_token(number, current, actor.form_key).encode()):
            return self.reply(403, {"error": "Откройте список заказов и повторите действие."})
        if target not in TRANSITIONS.get(current, ()):
            return staff.form_error(self, 409, "Выбранный переход недоступен.", staff.ORDERS_PATH, actor)
        if not order_storage.available(DATABASE):
            return self.reply(404, {"error": "Заказ не найден."})
        try:
            with order_storage.connect(DATABASE, write=True) as db:
                db.execute("BEGIN IMMEDIATE")
                if not staff.write_allowed(self, actor, db):
                    return
                result = db.execute("UPDATE orders SET status = ? WHERE number = ? AND status = ? "
                                    "AND (? != 'cancelled' OR json_extract(payload, '$.payment') IS NULL)",
                                    (target, number, current, target))
                if result.rowcount != 1:
                    return staff.form_error(self, 409, "Статус уже изменился. Откройте заказ заново.", staff.ORDERS_PATH, actor)
                db.execute("""CREATE TABLE IF NOT EXISTS order_status_history (
                    number TEXT NOT NULL, previous TEXT NOT NULL, current TEXT NOT NULL,
                    changed TEXT DEFAULT CURRENT_TIMESTAMP)""")
                db.execute("INSERT INTO order_status_history (number, previous, current) VALUES (?, ?, ?)",
                           (number, current, target))
                staff.record(db, number, actor, 'status', f'{STATUS_LABELS[current]} → {STATUS_LABELS[target]}')
        except order_storage.DatabaseError:
            return staff.form_error(self, 503, "Повторите попытку через несколько минут.", staff.ORDERS_PATH, actor)
        return self.customer_service().redirect(self, f'{staff.ORDERS_PATH}?saved=status#{quote(number, safe="")}')

    def adjustment_controls(self, number, status, raw, order, key):
        form = (f'<form class="staff-action" method="post" action="/manager/orders/adjust">'
                f'<input type="hidden" name="number" value="{html.escape(number, quote=True)}">'
                f'<input type="hidden" name="token" value="{adjustment_token(number, status, raw, key)}">')
        if not order.get("payment"):
            if status not in {"in_progress", "completed"} or order.get("total") is None:
                return "<p>Оплата не отмечена.</p>"
            options = "".join(f'<option value="{key}">{name}</option>' for key, name in PAYMENT_METHODS.items())
            return form + f'<label>Способ оплаты <select name="value">{options}</select></label><button name="action" value="payment">Отметить оплату</button></form>'
        payment = order["payment"]
        returns = order.get("returns", [])
        refund_paid = sum(entry["refundDue"] for entry in returns if entry.get("refundPaid"))
        refund_due = sum(entry["refundDue"] for entry in returns if not entry.get("refundPaid"))
        summary = f'<p>Оплачено <strong>{ui.amount(payment["amount"])}</strong> · {PAYMENT_METHODS[payment["method"]]}</p>'
        if returns:
            remaining_total = order["remainingAmount"]["total"]
            summary += ('<dl class="staff-refund-summary">'
                        f'<dt>Итог по оставшимся товарам</dt><dd>{ui.amount(remaining_total)}</dd>'
                        f'<dt>Выплачено по возвратам</dt><dd>{ui.amount(refund_paid)}</dd>'
                        f'<dt>Осталось вернуть</dt><dd>{ui.amount(refund_due)}</dd></dl>')
            item_names = {line["id"]: line["name"] for line in order["items"]}
            for index, entry in enumerate(returns):
                if entry["refundDue"] > 0 and not entry.get("refundPaid"):
                    name = html.escape(item_names[entry["id"]])
                    summary += (form + f'<input type="hidden" name="value" value="{index}">'
                                f'<p>{name} · {entry["quantity"]} шт. · {ui.amount(entry["refundDue"])}</p>'
                                '<button name="action" value="refund_paid">Отметить выплату</button></form>')
        if status != "completed":
            return summary
        options = "".join(
            f'<option value="{html.escape(line["id"], quote=True)}">{html.escape(line["name"])} · осталось {line["quantity"]}</option>'
            for line in order.get("remainingItems", order["items"])
        )
        return (summary + form + f'<label>Товар <select name="value">{options}</select></label>'
                '<label>Количество <input name="quantity" type="number" min="1" value="1" required></label>'
                '<button name="action" value="return">Оформить возврат позиции</button></form>')

    def adjust_order(self):
        actor = self.manager_actor()
        if not actor or not staff.require_origin(self, actor):
            return
        if self.headers.get_content_type() != "application/x-www-form-urlencoded":
            return self.reply(415, {"error": "Неверный формат формы."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 2000:
                raise ValueError
            fields = parse_qs(self.rfile.read(size).decode(), strict_parsing=True, max_num_fields=5)
            number, token, action, value = (fields[key][0] for key in ("number", "token", "action", "value"))
            quantity = int(fields.get("quantity", ["0"])[0])
        except (ValueError, KeyError):
            return self.reply(400, {"error": "Проверьте данные формы."})
        if not order_storage.available(DATABASE):
            return self.reply(404, {"error": "Заказ не найден."})
        try:
            with order_storage.connect(DATABASE, write=True) as db:
                db.execute("BEGIN IMMEDIATE")
                if not staff.write_allowed(self, actor, db):
                    return
                row = db.execute("SELECT status, payload FROM orders WHERE number = ?", (number,)).fetchone()
                if not row:
                    return self.reply(404, {"error": "Заказ не найден."})
                status, raw = row
                if not hmac.compare_digest(token.encode(), adjustment_token(number, status, raw, actor.form_key).encode()):
                    return staff.form_error(self, 409, "Заказ изменился. Откройте его заново.", staff.ORDERS_PATH, actor)
                order = json.loads(raw)
                try:
                    target = apply_adjustment(order, status, action, value, quantity)
                except ValueError as error:
                    return staff.form_error(self, 409, str(error), staff.ORDERS_PATH, actor)
                db.execute("UPDATE orders SET status = ?, payload = ? WHERE number = ?",
                           (target, json.dumps(order, ensure_ascii=False), number))
                if action == 'payment':
                    detail = f'{PAYMENT_METHODS[value]} · {order["payment"]["amount"]} ֏'
                else:
                    entry = order['returns'][-1 if action == 'return' else int(value)]
                    item = next(line for line in order['items'] if line['id'] == entry['id'])
                    detail = f'{item["name"]} · {entry["quantity"]} шт. · {entry["refundDue"]} ֏'
                    if target != status:
                        detail += f' · {STATUS_LABELS[status]} → {STATUS_LABELS[target]}'
                staff.record(db, number, actor, action, detail)
                if target != status:
                    db.execute("""CREATE TABLE IF NOT EXISTS order_status_history (
                        number TEXT NOT NULL, previous TEXT NOT NULL, current TEXT NOT NULL,
                        changed TEXT DEFAULT CURRENT_TIMESTAMP)""")
                    db.execute("INSERT INTO order_status_history (number, previous, current) VALUES (?, ?, ?)",
                               (number, status, target))
        except order_storage.DatabaseError:
            return staff.form_error(self, 503, "Повторите попытку через несколько минут.", staff.ORDERS_PATH, actor)
        return self.customer_service().redirect(self, f'{staff.ORDERS_PATH}?saved={action}#{quote(number, safe="")}')

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
