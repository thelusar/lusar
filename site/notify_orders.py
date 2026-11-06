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


def telegram_error_details(error):
    try:
        with error:
            body = json.loads(error.read(8192))
        if isinstance(body, dict):
            return body
    except (OSError, ValueError):
        pass
    return {}


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
              AND EXISTS (SELECT 1 FROM orders WHERE orders.number = order_notifications.number AND deleted_at IS NULL)
            ORDER BY last_attempt IS NOT NULL, last_attempt, number LIMIT ?""", (cutoff, limit)).fetchall()
    for (number,) in pending:
        with order_storage.connect(serve.DATABASE, write=True) as db:
            claimed = db.execute("""UPDATE order_notifications
                SET attempts = attempts + 1, last_attempt = CURRENT_TIMESTAMP
                WHERE number = ? AND sent_at IS NULL
                  AND (last_attempt IS NULL OR last_attempt <= ?)
                  AND EXISTS (SELECT 1 FROM orders WHERE orders.number = order_notifications.number AND deleted_at IS NULL)
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
        else:
            logging.info("Уведомление LUSAR %s доставлено в Telegram.", number)


def sender_from_environment(*, expected_group=None):
    token = os.environ.get("LUSAR_TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("LUSAR_TELEGRAM_CHAT_ID", "")
    origin = os.environ.get("LUSAR_MANAGER_ORIGIN", "").rstrip("/")
    parsed = urlparse(origin)
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token) or not re.fullmatch(r"-\d+", chat):
        raise ValueError("Укажите токен бота и ID закрытого чата в настройках окружения.")
    if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise ValueError("Укажите HTTPS-адрес панели в LUSAR_MANAGER_ORIGIN.")
    chat_id = int(chat)

    def request_telegram(method, payload):
        request = Request(f"https://api.telegram.org/bot{token}/{method}", json.dumps(payload).encode(),
                          {"Content-Type": "application/json"})
        with urlopen(request, timeout=10) as response:
            return json.load(response)

    def find_group(candidate):
        try:
            result = request_telegram("getChat", {"chat_id": candidate}).get("result", {})
        except (OSError, ValueError):
            return False
        return (result.get("id") == candidate and result.get("title") == expected_group
                and result.get("type") in {"group", "supergroup"}
                and not (result.get("username") or result.get("active_usernames")))

    def send(number):
        nonlocal chat_id
        message = {
            "chat_id": chat_id,
            "text": f"Новая заявка LUSAR №{number}\n{origin}/manager/orders/#{number}",
            "link_preview_options": {"is_disabled": True},
        }
        try:
            return None if request_telegram("sendMessage", message).get("ok") else "Telegram не принял уведомление"
        except HTTPError as error:
            details = telegram_error_details(error)
            description = str(details.get("description", "")).lower()
            parameters = details.get("parameters") or {}
            migrated = parameters.get("migrate_to_chat_id")
            if error.code == 400 and ("chat not found" in description or type(migrated) is int):
                candidate = migrated if type(migrated) is int else (
                    chat_id - 10**12 if -10**12 < chat_id < 0 else chat_id + 10**12
                )
                if expected_group and candidate < 0 and candidate != chat_id and find_group(candidate):
                    chat_id = candidate
                    logging.info("LUSAR: Telegram подтвердил ID закрытой группы %s. Очередь повторит отправку.", chat_id)
                    return "Telegram подтвердил другой формат ID группы"
                return "Telegram не нашёл группу по указанному ID или у бота нет доступа"
            if error.code == 401:
                return "Telegram отклонил токен бота (HTTP 401)"
            if error.code == 403 or "not enough rights" in description or "write forbidden" in description:
                return "Telegram не разрешил боту писать в группу"
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
