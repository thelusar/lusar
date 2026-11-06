"""Password-gated test deployment. Accept synthetic data only."""
import base64
import json
import logging
import os
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread

import ai_telegram
import lusar_ai
import notify_orders
import serve
import order_storage
import staff
from catalog_runtime import CatalogService, CatalogUnavailable


class StagingHandler(serve.Handler):
    local_manager_preview = False

    def end_headers(self):
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def staging_authorized(self):
        if secrets.compare_digest(self.headers.get("Authorization", "").encode(), self.staging_auth):
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="LUSAR staging"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()
        return False

    def do_GET(self):
        if self.path == "/healthz":
            return self.reply(200, {"ok": True, "storage": "postgresql" if order_storage.DATABASE_URL else "sqlite",
                                    "catalog": self.server.catalog_service.status(),
                                    "accounts": {"configured": self.customer_service().config.enabled},
                                    "staff": {"owner_configured": staff.owner_id() is not None,
                                              "ui_version": staff.UI_VERSION}})
        if self.staging_authorized():
            if self.path == "/api/ai":
                return self.reply(200, {"available": bool(os.environ.get("OPENAI_API_KEY", "").strip())})
            super().do_GET()

    def do_HEAD(self):
        if self.staging_authorized():
            super().do_HEAD()

    def do_POST(self):
        if self.path == ai_telegram.WEBHOOK:
            return self.telegram_update()
        if self.staging_authorized():
            if self.path == "/api/ai":
                return self.ai_request()
            super().do_POST()

    def read_json(self, limit):
        if self.headers.get_content_type() != "application/json":
            raise ValueError
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= limit:
            raise ValueError
        payload = json.loads(self.rfile.read(size))
        if not isinstance(payload, dict):
            raise ValueError
        return payload

    def ai_request(self):
        origin = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
        if not origin:
            origin = "http://" + self.headers.get("Host", "")
        if self.headers.get("Origin") != origin:
            return self.reply(403, {"error": "Откройте Lusar AI со страницы стенда."})
        try:
            data = self.read_json(lusar_ai.MAX_REQUEST)
            if data.get("consent") is not True:
                return self.reply(400, {"error": "Подтвердите отправку фотографии для обработки."})
            photo = base64.b64decode(data["photo"], validate=True)
            result = lusar_ai.analyze(photo, data.get("wishes", ""), data.get("productId"))
        except (ValueError, KeyError, TypeError):
            return self.reply(400, {"error": "Выберите фото JPEG, PNG или WebP размером до 4 МБ."})
        except lusar_ai.AIError as error:
            return self.reply(error.status, {"error": str(error)})
        return self.reply(200, result)

    def telegram_update(self):
        bot = self.server.ai_bot
        if bot is None:
            return self.reply(404, {"ok": False})
        provided = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not secrets.compare_digest(provided.encode(), bot.secret.encode()):
            return self.reply(403, {"ok": False})
        try:
            payload = self.read_json(ai_telegram.MAX_UPDATE)
            if type(payload.get("update_id")) is not int:
                raise ValueError
        except ValueError:
            return self.reply(400, {"ok": False})
        accepted = bot.enqueue(payload)
        return self.reply(200 if accepted else 503, {"ok": accepted})


def main():
    logging.basicConfig(level=logging.INFO)
    password = os.environ.get("LUSAR_STAGING_PASSWORD", "")
    if len(password) < 24:
        raise SystemExit("Set LUSAR_STAGING_PASSWORD to a generated secret of at least 24 characters.")
    StagingHandler.staging_auth = b"Basic " + base64.b64encode(f"manager:{password}".encode())
    try:
        order_storage.initialize()
    except order_storage.DatabaseError:
        raise SystemExit("PostgreSQL connection or migration failed. Check Render database settings.") from None
    with TemporaryDirectory(prefix="lusar-staging-") as directory:
        serve.DATABASE = Path(directory) / "orders.sqlite"
        catalog = CatalogService(Path(directory) / "catalog")
        try:
            catalog.refresh()
        except CatalogUnavailable:
            pass
        catalog.start()
        lusar_ai.CATALOG_READER = catalog.current_data
        try:
            with serve.ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "10000"))), StagingHandler) as server:
                server.catalog_service = catalog
                server.ai_bot = ai_telegram.start_bot()
                if server.ai_bot is not None:
                    ai_telegram.start_webhook(server.ai_bot)
                if order_storage.DATABASE_URL and os.environ.get("LUSAR_TELEGRAM_BOT_TOKEN"):
                    try:
                        sender = notify_orders.sender_from_environment(expected_group="LUSAR — заявки")
                    except ValueError as error:
                        logging.warning("Уведомления LUSAR отключены. %s", error)
                    else:
                        logging.info("Запущена отправка уведомлений LUSAR в Telegram.")
                        Thread(target=notify_orders.run_worker, args=(sender,), daemon=True).start()
                server.serve_forever()
        finally:
            catalog.close()


if __name__ == "__main__":
    main()
