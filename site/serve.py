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
from loyalty import FIRST_ORDER_PERCENT

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
PAYMENT_METHODS = {"store": "В магазине", "receipt": "По чеку менеджера", "delivery": "При получении"}


def status_token(number, status):
    return hmac.new(MANAGER_FORM_KEY, f"{number}:{status}".encode(), "sha256").hexdigest()


def adjustment_token(number, status, payload):
    return status_token(number, status + ":" + hashlib.sha256(payload.encode()).hexdigest())


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
                          first_order=bool(order.get("firstOrderDiscount")))
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "dist"), **kwargs)

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
        self.wfile.write(body)

    def manager_authorized(self):
        password = os.environ.get("LUSAR_LOCAL_MANAGER_PASSWORD")
        if not password:
            self.send_error(404)
            return False
        expected = b"Basic " + base64.b64encode(f"manager:{password}".encode())
        if not secrets.compare_digest(self.headers.get("Authorization", "").encode(), expected):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="LUSAR local preview"')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return False
        return True

    def redirect_permanently(self, location):
        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def public_redirect(self):
        url = urlsplit(self.path)
        if url.path == "/catalog.html":
            product_id = parse_qs(url.query).get("product", [""])[0]
            if not product_id:
                return self.redirect_permanently("/catalog")
            catalog = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
            if any(item["id"] == product_id for item in catalog["products"]):
                return self.redirect_permanently("/catalog/product/" + quote(product_id, safe=""))
            return self.send_error(404, "Product unavailable")
        root = (ROOT / "dist").resolve()
        path = unquote(url.path)
        brand_id = path.removesuffix("/index.html").rstrip("/").removeprefix("/brands/")
        if path.startswith("/brands/") and brand_id in BRANDS:
            destination = BRANDS[brand_id]["path"]
            if (root / "brands" / destination / "index.html").is_file():
                return self.redirect_permanently("/brands/" + destination)
        target = (root / path.lstrip("/")).resolve()
        if not target.is_relative_to(root):
            return self.send_error(404)
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
        return self.public_redirect()

    def do_GET(self):
        if self.path != "/manager/orders/":
            return self.public_redirect()
        if not self.manager_authorized():
            return
        rows = []
        if DATABASE.is_file():
            with closing(sqlite3.connect(DATABASE)) as db:
                rows = db.execute("SELECT number, status, created, payload FROM orders ORDER BY created DESC").fetchall()
        cards = []
        for number, status, created, raw in rows:
            order = json.loads(raw)
            contact = order["contact"]
            lines = "".join(
                f'<li>{html.escape(line["name"])} · {html.escape(line["sku"])} · {line["quantity"]} шт.</li>'
                for line in order["items"]
            )
            total = order.get("total")
            summary = "Сумму нужно уточнить" if total is None else f"Итог: {total} ֏"
            details = " · ".join(html.escape(value) for value in contact.values() if value)
            targets = TRANSITIONS.get(status, ())
            if order.get("payment"):
                targets = tuple(target for target in targets if target != "cancelled")
            options = "".join(f'<option value="{target}">{STATUS_LABELS[target]}</option>' for target in targets)
            controls = (f'<form method="post" action="/manager/orders/status">'
                        f'<input type="hidden" name="number" value="{html.escape(number, quote=True)}">'
                        f'<input type="hidden" name="current" value="{html.escape(status, quote=True)}">'
                        f'<input type="hidden" name="token" value="{status_token(number, status)}">'
                        f'<label>Новый статус <select name="target">{options}</select></label>'
                        '<button>Сохранить статус</button></form>') if options else ""
            cards.append(f'<article id="{html.escape(number, quote=True)}"><h2>{html.escape(number)}</h2><p>{html.escape(created)} · '
                         f'{html.escape(STATUS_LABELS.get(status, status))}</p>'
                         f'<p>{details}</p><ul>{lines}</ul><p>{summary}</p>{controls}'
                         f'{self.adjustment_controls(number, status, raw, order)}</article>')
        content = "".join(cards) or "<p>Заявок пока нет.</p>"
        body = ('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="robots" content="noindex">'
                '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Заказы LUSAR</title>'
                '<link rel="stylesheet" href="/site.css"><main><h1>Заказы LUSAR</h1>' + content + "</main></html>").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path == "/api/order-status":
            return self.guest_order_status()
        if self.path == "/manager/orders/adjust":
            return self.adjust_order()
        if self.path == "/manager/orders/status":
            return self.change_order_status()
        if self.path != "/api/orders":
            return self.reply(404, {"error": "Страница не найдена."})
        if self.headers.get_content_type() != "application/json":
            return self.reply(415, {"error": "Неверный формат заявки."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16000:
                raise ValueError
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError
            request_id = str(uuid.UUID(data["requestId"]))
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
        except (AttributeError, ValueError, KeyError, TypeError):
            return self.reply(400, {"error": "Проверьте имя, телефон, email и состав корзины."})

        fingerprint = hashlib.sha256(json.dumps([contact, cart, promo, displayed_prices], sort_keys=True).encode()).hexdigest()
        catalog = json.loads(CATALOG.read_text(encoding="utf-8-sig"))
        products = {item["id"]: item for item in catalog["products"]}
        try:
            with closing(sqlite3.connect(DATABASE)) as db, db:
                db.execute("""CREATE TABLE IF NOT EXISTS orders (
                    request_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                    number TEXT NOT NULL UNIQUE, payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new', created TEXT DEFAULT CURRENT_TIMESTAMP)""")
                db.execute("BEGIN IMMEDIATE")
                existing = db.execute("SELECT number, fingerprint, payload FROM orders WHERE request_id = ?", (request_id,)).fetchone()
                if existing:
                    if existing[1] != fingerprint:
                        return self.reply(409, {"error": "Заявка уже сохранена с другими данными. Номер: " + existing[0]})
                    token = json.loads(existing[2]).get("trackingToken")
                    return self.reply(200, {"number": existing[0], "trackingToken": token})
                if any(key not in products for key in cart):
                    return self.reply(409, {"error": "Состав каталога изменился. Проверьте корзину."})
                if any(key not in displayed_prices or displayed_prices[key] != products[key]["price"] for key in cart):
                    return self.reply(409, {"error": "Цена одного или нескольких товаров изменилась. Обновите страницу и проверьте корзину."})
                lines = [{"id": key, "sku": products[key]["sku"], "name": products[key]["name"],
                          "quantity": quantity, "unitPrice": products[key]["price"]}
                         for key, quantity in cart.items()]
                number = "LS-" + secrets.token_hex(6).upper()
                tracking_token = secrets.token_urlsafe(32)
                try:
                    amount = order_amount(lines, promo)
                except ValueError as error:
                    return self.reply(422, {"error": str(error)})
                db.execute("INSERT INTO orders (request_id, fingerprint, number, payload) VALUES (?, ?, ?, ?)",
                           (request_id, fingerprint, number, json.dumps(
                               {"contact": contact, "items": lines, "promo": promo, "trackingToken": tracking_token, **amount},
                               ensure_ascii=False)))
                db.execute("""CREATE TABLE IF NOT EXISTS order_notifications (
                    number TEXT PRIMARY KEY, sent_at TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_attempt TEXT, last_error TEXT)""")
                db.execute("INSERT INTO order_notifications (number) VALUES (?)", (number,))
        except sqlite3.Error:
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
            if not re.fullmatch(r"LS-[A-F0-9]{12}", number) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", key):
                raise ValueError
        except (ValueError, TypeError, KeyError):
            return self.reply(400, {"error": "Проверьте приватную ссылку."})
        missing = {"error": "Заявка не найдена. Проверьте приватную ссылку."}
        if not DATABASE.is_file():
            return self.reply(404, missing)
        try:
            with closing(sqlite3.connect(DATABASE)) as db:
                row = db.execute("SELECT status, payload FROM orders WHERE number = ?", (number,)).fetchone()
        except sqlite3.Error:
            return self.reply(503, {"error": "Статус временно недоступен. Попробуйте позже."})
        saved = json.loads(row[1]).get("trackingToken") if row else None
        if not saved or not secrets.compare_digest(saved, key):
            return self.reply(404, missing)
        return self.reply(200, {"number": number, "status": STATUS_LABELS.get(row[0], row[0])})

    def change_order_status(self):
        if not self.manager_authorized():
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
        if not hmac.compare_digest(token.encode(), status_token(number, current).encode()):
            return self.reply(403, {"error": "Откройте список заказов и повторите действие."})
        if target not in TRANSITIONS.get(current, ()):
            return self.reply(409, {"error": "Этот переход недоступен."})
        if not DATABASE.is_file():
            return self.reply(404, {"error": "Заказ не найден."})
        try:
            with closing(sqlite3.connect(DATABASE)) as db, db:
                result = db.execute("UPDATE orders SET status = ? WHERE number = ? AND status = ? "
                                    "AND (? != 'cancelled' OR json_extract(payload, '$.payment') IS NULL)",
                                    (target, number, current, target))
                if result.rowcount != 1:
                    return self.reply(409, {"error": "Статус уже изменился. Обновите список заказов."})
                db.execute("""CREATE TABLE IF NOT EXISTS order_status_history (
                    number TEXT NOT NULL, previous TEXT NOT NULL, current TEXT NOT NULL,
                    changed TEXT DEFAULT CURRENT_TIMESTAMP)""")
                db.execute("INSERT INTO order_status_history (number, previous, current) VALUES (?, ?, ?)",
                           (number, current, target))
        except sqlite3.Error:
            return self.reply(503, {"error": "Не удалось сохранить статус. Повторите попытку."})
        self.send_response(303)
        self.send_header("Location", "/manager/orders/")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def adjustment_controls(self, number, status, raw, order):
        form = (f'<form method="post" action="/manager/orders/adjust">'
                f'<input type="hidden" name="number" value="{html.escape(number, quote=True)}">'
                f'<input type="hidden" name="token" value="{adjustment_token(number, status, raw)}">')
        if not order.get("payment"):
            if status not in {"in_progress", "completed"} or order.get("total") is None:
                return "<p>Оплата не отмечена.</p>"
            options = "".join(f'<option value="{key}">{name}</option>' for key, name in PAYMENT_METHODS.items())
            return form + f'<label>Способ оплаты <select name="value">{options}</select></label><button name="action" value="payment">Отметить оплату</button></form>'
        payment = order["payment"]
        returns = order.get("returns", [])
        refund_paid = sum(entry["refundDue"] for entry in returns if entry.get("refundPaid"))
        refund_due = sum(entry["refundDue"] for entry in returns if not entry.get("refundPaid"))
        summary = f'<p>Оплачено: {payment["amount"]} ֏ · {PAYMENT_METHODS[payment["method"]]}</p>'
        if returns:
            remaining_total = order["remainingAmount"]["total"]
            summary += (f"<p>Итог по оставшимся товарам: {remaining_total} ֏ · "
                        f"Выплачено по возвратам: {refund_paid} ֏ · Осталось вернуть: {refund_due} ֏</p>")
            item_names = {line["id"]: line["name"] for line in order["items"]}
            for index, entry in enumerate(returns):
                if entry["refundDue"] > 0 and not entry.get("refundPaid"):
                    name = html.escape(item_names[entry["id"]])
                    summary += (form + f'<input type="hidden" name="value" value="{index}">'
                                f'<p>{name} · {entry["quantity"]} шт. · {entry["refundDue"]} ֏</p>'
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
        if not self.manager_authorized():
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
        if not DATABASE.is_file():
            return self.reply(404, {"error": "Заказ не найден."})
        try:
            with closing(sqlite3.connect(DATABASE)) as db, db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT status, payload FROM orders WHERE number = ?", (number,)).fetchone()
                if not row:
                    return self.reply(404, {"error": "Заказ не найден."})
                status, raw = row
                if not hmac.compare_digest(token.encode(), adjustment_token(number, status, raw).encode()):
                    return self.reply(409, {"error": "Заказ изменился. Обновите список заказов."})
                order = json.loads(raw)
                try:
                    target = apply_adjustment(order, status, action, value, quantity)
                except ValueError as error:
                    return self.reply(409, {"error": str(error)})
                db.execute("UPDATE orders SET status = ?, payload = ? WHERE number = ?",
                           (target, json.dumps(order, ensure_ascii=False), number))
                if target != status:
                    db.execute("""CREATE TABLE IF NOT EXISTS order_status_history (
                        number TEXT NOT NULL, previous TEXT NOT NULL, current TEXT NOT NULL,
                        changed TEXT DEFAULT CURRENT_TIMESTAMP)""")
                    db.execute("INSERT INTO order_status_history (number, previous, current) VALUES (?, ?, ?)",
                               (number, status, target))
        except sqlite3.Error:
            return self.reply(503, {"error": "Не удалось сохранить изменение."})
        self.send_response(303)
        self.send_header("Location", "/manager/orders/")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
