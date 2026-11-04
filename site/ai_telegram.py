"""Private Telegram entry point for the staging Lusar AI service."""

import base64
import hashlib
import hmac
import json
import logging
import os
import re
from collections import deque
from queue import Full, Queue
from threading import Lock, Thread
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from lusar_ai import AIError, MAX_PHOTO, analyze, multipart_payload


WEBHOOK = "/api/telegram/lusar-ai"
MAX_UPDATE = 64 * 1024


def connection_error(error):
    if isinstance(error, HTTPError):
        with error:
            try:
                description = str(json.loads(error.read(4096)).get("description", "")).lower()
            except (OSError, ValueError, AttributeError):
                description = ""
        if error.code in {401, 404}:
            return f"Telegram отклонил токен бота (HTTP {error.code})"
        if "webhook" in description and ("resolve" in description or "getaddrinfo" in description):
            return "Telegram не смог разрешить адрес Render"
        if "webhook" in description and ("ssl" in description or "certificate" in description):
            return "Telegram отклонил TLS-сертификат адреса Render"
        return f"Telegram вернул HTTP {error.code}"
    if isinstance(error, TimeoutError) or isinstance(getattr(error, "reason", None), TimeoutError):
        return "истекло время ожидания ответа Telegram"
    if isinstance(error, (URLError, OSError)):
        return "сетевая ошибка при обращении к Telegram"
    return "Telegram вернул неожиданный ответ"


class AIBot:
    def __init__(self, token, origin, allowed_users):
        self.token = token
        self.origin = origin
        self.allowed_users = allowed_users
        self.secret = hmac.new(token.encode(), b"LUSAR AI webhook v1", hashlib.sha256).hexdigest()
        self.pending = Queue(maxsize=3)
        self.seen = deque(maxlen=256)
        self.lock = Lock()

    def request(self, method, payload, *, content_type="application/json", timeout=12):
        body = json.dumps(payload).encode() if content_type == "application/json" else payload
        request = Request(f"https://api.telegram.org/bot{self.token}/{method}", body,
                          {"Content-Type": content_type})
        with urlopen(request, timeout=timeout) as response:
            result = json.load(response)
        if not result.get("ok"):
            raise ValueError("Telegram request rejected")
        return result.get("result")

    def send(self, chat_id, message):
        self.request("sendMessage", {"chat_id": chat_id, "text": message[:4000],
                                     "link_preview_options": {"is_disabled": True}})

    def send_mockup(self, chat_id, image):
        photo = base64.b64decode(image.split(",", 1)[1], validate=True)
        body, content_type = multipart_payload(
            {"chat_id": chat_id, "caption": "Примерная визуализация светильников LUSAR в вашей комнате."},
            [("photo", photo, "image/png")])
        self.request("sendPhoto", body, content_type=content_type)

    def enqueue(self, update):
        with self.lock:
            update_id = update["update_id"]
            if update_id in self.seen:
                return True
            try:
                self.pending.put_nowait(update)
            except Full:
                return False
            self.seen.append(update_id)
            return True

    def connect(self):
        target = self.origin + WEBHOOK
        for attempt in range(1, 4):
            try:
                self.request("getMe", {})
            except (OSError, ValueError) as error:
                logging.warning("LUSAR AI: getMe, попытка %s: %s.", attempt, connection_error(error))
                if isinstance(error, HTTPError) and error.code in {401, 404}:
                    return None
            else:
                try:
                    self.request("setWebhook", {"url": target, "secret_token": self.secret,
                                                "allowed_updates": ["message"], "max_connections": 2}, timeout=40)
                    return "webhook"
                except (OSError, ValueError) as error:
                    logging.warning("LUSAR AI: setWebhook, попытка %s: %s.", attempt, connection_error(error))
                try:
                    current = self.request("getWebhookInfo", {})["url"]
                except (OSError, ValueError, KeyError, TypeError) as error:
                    logging.warning("LUSAR AI: getWebhookInfo: %s.", connection_error(error))
                else:
                    if current == target:
                        return "webhook"
                    if not current and attempt == 3:
                        return "polling"
            if attempt < 3:
                sleep(5)
        return None

    def process_safely(self, update):
        try:
            self.process(update)
        except (OSError, ValueError, KeyError, TypeError) as error:
            logging.warning("LUSAR AI: не удалось обработать обновление Telegram: %s.", connection_error(error))

    def poll(self):
        offset = None
        while True:
            query = {"timeout": 20, "allowed_updates": ["message"]}
            if offset is not None:
                query["offset"] = offset
            try:
                updates = self.request("getUpdates", query, timeout=30)
                for update in updates:
                    self.process_safely(update)
                    offset = update["update_id"] + 1
            except (OSError, ValueError, KeyError, TypeError) as error:
                if isinstance(error, HTTPError) and error.code == 409:
                    try:
                        if self.request("getWebhookInfo", {})["url"] == self.origin + WEBHOOK:
                            return
                    except (OSError, ValueError, KeyError, TypeError):
                        pass
                logging.warning("LUSAR AI: getUpdates: %s.", connection_error(error))
                sleep(10)

    def run(self):
        sleep(8)
        mode = self.connect()
        if mode == "polling":
            logging.warning("LUSAR AI: webhook не зарегистрирован. Временно читаем Telegram через getUpdates.")
            self.poll()
            mode = "webhook"
        if mode == "webhook":
            logging.info("LUSAR AI: webhook Telegram подключён.")
        while True:
            update = self.pending.get()
            try:
                self.process_safely(update)
            finally:
                self.pending.task_done()

    def process(self, update):
        message = update.get("message", {})
        chat = message.get("chat", {})
        if chat.get("type") != "private":
            return
        chat_id = chat["id"]
        command = message.get("text", "").split(maxsplit=1)
        if command and command[0].split("@", 1)[0] == "/start":
            privacy = "Для подбора фото и подпись передаются в OpenAI. Используйте фото без людей и личных данных."
            if chat_id not in self.allowed_users:
                self.send(chat_id, f"Lusar AI сейчас тестируется. Ваш ID для доступа: {chat_id}.\n\n{privacy}")
                return
            self.send(chat_id, "Пришлите фото комнаты с пожеланиями в подписи. "
                               f"Я верну примерку светильников и ссылки на модели.\n\n{privacy}")
            return
        if chat_id not in self.allowed_users:
            return
        photos = message.get("photo")
        if not photos:
            self.send(chat_id, "Пришлите фото комнаты. Пожелания можно добавить в подпись к фотографии.")
            return
        try:
            photo = next((item for item in reversed(photos) if item.get("file_size", 0) <= MAX_PHOTO), None)
            if photo is None:
                raise AIError(413, "Пришлите фото размером до 4 МБ.")
            file_path = self.request("getFile", {"file_id": photo["file_id"]})["file_path"]
            if not re.fullmatch(r"[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+", file_path):
                raise AIError(502, "Не удалось открыть фотографию из Telegram.")
            with urlopen(f"https://api.telegram.org/file/bot{self.token}/{file_path}", timeout=12) as response:
                photo_bytes = response.read(MAX_PHOTO + 1)
            answer = analyze(photo_bytes, message.get("caption", ""))
        except AIError as error:
            self.send(chat_id, str(error))
            return
        lines = [answer["advice"]]
        mockup_sent = False
        if answer.get("image"):
            try:
                self.send_mockup(chat_id, answer["image"])
                mockup_sent = True
            except (OSError, ValueError, IndexError):
                logging.warning("LUSAR AI: Telegram не принял визуализацию.")
                lines.append("Визуализацию не удалось отправить в Telegram. Ниже — подборка товаров.")
        elif answer.get("imageError"):
            lines.append(answer["imageError"])
        for item in answer["products"]:
            label = "В примерке · " if mockup_sent and item["inMockup"] else ""
            lines.append(f"{label}{item['name']} · {item['sku']}\n{item['reason']}\n{self.origin}{item['path']}")
        self.send(chat_id, "\n\n".join(lines) or "По этому фото не удалось подобрать светильники.")


def start_bot():
    token = os.environ.get("LUSAR_AI_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return None
    origin = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
    parsed = urlparse(origin)
    allowed = os.environ.get("LUSAR_AI_TELEGRAM_USER_IDS", "").strip()
    if (not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token)
            or token == os.environ.get("LUSAR_TELEGRAM_BOT_TOKEN", "").strip()
            or parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment
            or (allowed and not re.fullmatch(r"[0-9]+(?:\s*,\s*[0-9]+)*", allowed))):
        logging.warning("LUSAR AI: проверьте отдельный токен бота, адрес Render и ID тестировщиков.")
        return None
    bot = AIBot(token, origin, {int(value) for value in allowed.split(",")} if allowed else set())
    return bot


def start_webhook(bot):
    Thread(target=bot.run, daemon=True).start()
