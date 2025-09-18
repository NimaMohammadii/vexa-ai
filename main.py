"""Entry point for the Vexa AI bot and GPT mini-app host."""
from __future__ import annotations

import json
import os
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import telebot

from config import BOT_TOKEN, DEBUG
import db

from modules.admin import handlers as admin_handlers
from modules.clone import handlers as clone_handlers
from modules.credit import handlers as credit_handlers
from modules.gpt import handlers as gpt_handlers
from modules.gpt.service import GPTServiceError, chat_completion
from modules.home import handlers as home_handlers
from modules.invite import handlers as invite_handlers
from modules.lang import handlers as lang_handlers
from modules.profile import handlers as profile_handlers
from modules.tts import handlers as tts_handlers

# روت استاتیک‌های مینی‌اپ (index.html, app.js, style.css و ...)
STATIC_DIR = Path(__file__).resolve().parent / "modules" / "gpt"
API_ENDPOINT = "/api/gpt"


class MiniAppHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Serve the GPT mini-app static bundle and proxy GPT chat requests."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    # BaseHTTPRequestHandler signature
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        if DEBUG:
            super().log_message(format, *args)

    # ---- API: POST /api/gpt -------------------------------------------------
    def do_POST(self) -> None:  # noqa: N802
        if self._normalized_path() != API_ENDPOINT:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        payload = self._read_json_payload()
        if payload is None:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body"})
            return

        messages = payload.get("messages")
        if not self._is_non_empty_list(messages):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "messages must be a non-empty list"})
            return

        model = payload.get("model")
        temperature = self._coerce_float(payload.get("temperature"))
        top_p = self._coerce_float(payload.get("top_p"))
        max_tokens = self._coerce_int(payload.get("max_tokens"))

        try:
            data = chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
        except GPTServiceError as exc:
            if DEBUG:
                print("GPT API error:", exc)
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover
            if DEBUG:
                print("Unexpected GPT handler error:", exc)
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error"})
            return

        self._send_json(HTTPStatus.OK, data)

    # ---- Static files (remove querystring, normalize) -----------------------
    def do_GET(self) -> None:  # noqa: N802
        self.path = self._path_without_query()
        # نرمال‌سازی برای / و /gpt به /gpt/
        if self.path in ("/gpt",):
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", "/gpt/")
            self.end_headers()
            return
        if self.path == "/":
            # می‌تونی ریدایرکت بدی به /gpt/ یا index.html روت
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", "/gpt/")
            self.end_headers()
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        self.path = self._path_without_query()
        if self.path in ("/", "/gpt"):
            self.path = "/gpt/"
        super().do_HEAD()

    # ---- Helpers ------------------------------------------------------------
    def _normalized_path(self) -> str:
        return self._path_without_query().rstrip("/") or "/"

    def _path_without_query(self) -> str:
        parsed = urlparse(self.path)
        return parsed.path or "/"

    def _read_json_payload(self) -> Optional[Dict[str, Any]]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        body = self.rfile.read(length) if length else b""
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    @staticmethod
    def _coerce_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _is_non_empty_list(value: Any) -> bool:
        return isinstance(value, list) and bool(value)

    def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def create_bot() -> telebot.TeleBot:
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN در secrets تعریف نشده")
    return telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


def register_modules(bot: telebot.TeleBot) -> None:
    admin_handlers.register(bot)
    lang_handlers.register(bot)
    home_handlers.register(bot)
    tts_handlers.register(bot)
    profile_handlers.register(bot)
    credit_handlers.register(bot)
    invite_handlers.register(bot)
    clone_handlers.register(bot)
    gpt_handlers.register(bot)


def start_http_server(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", port), MiniAppHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, name="gpt-mini-app", daemon=True)
    thread.start()
    return server


def main() -> None:
    db.init_db()
    bot = create_bot()
    register_modules(bot)

    port = int(os.environ.get("PORT", "8000"))
    start_http_server(port)

    if DEBUG:
        print(f"✅ HTTP server listening on 0.0.0.0:{port}")
        print("✅ Bot started (DEBUG)")

    bot.infinity_polling(
        skip_pending=True,
        allowed_updates=[
            "message",
            "callback_query",
            "pre_checkout_query",
            "successful_payment",
        ],
    )


if __name__ == "__main__":
    main()
