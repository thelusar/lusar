"""Deliver queued order notices to the configured private Telegram chat."""
import json
import os
import re
import sqlite3
from contextlib import closing
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from serve import DATABASE


def deliver_pending(db, send, *, limit=20):
    pending = db.execute("""SELECT number FROM order_notifications
        WHERE sent_at IS NULL AND (last_attempt IS NULL OR last_attempt <= datetime('now', '-1 minute'))
        ORDER BY rowid LIMIT ?""", (limit,)).fetchall()
    for (number,) in pending:
        with db:
            claimed = db.execute("""UPDATE order_notifications
                SET attempts = attempts + 1, last_attempt = CURRENT_TIMESTAMP
                WHERE number = ? AND sent_at IS NULL
                  AND (last_attempt IS NULL OR last_attempt <= datetime('now', '-1 minute'))""", (number,))
        if claimed.rowcount != 1:
            continue
        error = send(number)
        with db:
            if error:
                db.execute("UPDATE order_notifications SET last_error = ? WHERE number = ?", (error, number))
            else:
                db.execute("UPDATE order_notifications SET sent_at = CURRENT_TIMESTAMP, last_error = NULL WHERE number = ?", (number,))


def main():
    token = os.environ.get("LUSAR_TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("LUSAR_TELEGRAM_CHAT_ID", "")
    origin = os.environ.get("LUSAR_MANAGER_ORIGIN", "").rstrip("/")
    parsed = urlparse(origin)
    if not re.fullmatch(r"\d+:[A-Za-z0-9_-]+", token) or not re.fullmatch(r"-\d+", chat):
        raise SystemExit("Укажите токен бота и ID закрытого чата в настройках окружения.")
    if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise SystemExit("Укажите HTTPS-адрес панели в LUSAR_MANAGER_ORIGIN.")

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

    if not DATABASE.is_file():
        return
    with closing(sqlite3.connect(DATABASE)) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE name = 'order_notifications'").fetchone():
            deliver_pending(db, send)


if __name__ == "__main__":
    main()
