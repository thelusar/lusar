"""Deliver queued order notices to the configured private Telegram chat."""
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import order_storage
import serve


def deliver_pending(send, *, limit=20):
    if not order_storage.available(serve.DATABASE):
        return
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(sep=" ", timespec="seconds")
    with order_storage.connect(serve.DATABASE) as db:
        if not order_storage.DATABASE_URL and not db.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'order_notifications'"
        ).fetchone():
            return
        pending = db.execute("""SELECT number FROM order_notifications
            WHERE sent_at IS NULL AND (last_attempt IS NULL OR last_attempt <= ?)
            ORDER BY last_attempt IS NOT NULL, last_attempt, number LIMIT ?""", (cutoff, limit)).fetchall()
    for (number,) in pending:
        with order_storage.connect(serve.DATABASE, write=True) as db:
            claimed = db.execute("""UPDATE order_notifications
                SET attempts = attempts + 1, last_attempt = CURRENT_TIMESTAMP
                WHERE number = ? AND sent_at IS NULL
                  AND (last_attempt IS NULL OR last_attempt <= ?)
                RETURNING attempts""", (number, cutoff)).fetchone()
        if not claimed:
            continue
        error = send(number)
        with order_storage.connect(serve.DATABASE, write=True) as db:
            db.execute("""UPDATE order_notifications
                SET sent_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END, last_error = ?
                WHERE number = ? AND attempts = ? AND sent_at IS NULL""", (error is None, error, number, claimed[0]))
        if error:
            logging.warning("Уведомление LUSAR %s не доставлено: %s", number, error)


def sender_from_environment():
    token = os.environ.get("LUSAR_TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("LUSAR_TELEGRAM_CHAT_ID", "")
    origin = os.environ.get("LUSAR_MANAGER_ORIGIN", "").rstrip("/")
    parsed = urlparse(origin)
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token) or not re.fullmatch(r"-\d+", chat):
        raise ValueError("Укажите токен бота и ID закрытого чата в настройках окружения.")
    if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise ValueError("Укажите HTTPS-адрес панели в LUSAR_MANAGER_ORIGIN.")

    def send(number):
        payload = json.dumps({
            "chat_id": chat,
            "text": f"Новая заявка LUSAR №{number}\n{origin}/manager/orders/#{number}",
            "link_preview_options": {"is_disabled": True},
        }).encode()
        request = Request(f"https://api.telegram.org/bot{token}/sendMessage", payload,
                          {"Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=10) as response:
                return None if json.load(response).get("ok") else "Telegram не принял уведомление"
        except HTTPError as error:
            return f"Telegram HTTP {error.code}"
        except (URLError, TimeoutError, ValueError):
            return "Telegram временно недоступен"

    return send


def run_worker(send):
    while True:
        try:
            deliver_pending(send)
        except order_storage.DatabaseError:
            logging.warning("Не удалось обработать очередь уведомлений LUSAR. Попытка повторится.")
        time.sleep(15)


def main():
    try:
        sender = sender_from_environment()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    deliver_pending(sender)


if __name__ == "__main__":
    main()
