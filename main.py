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

# ---- Telegram modules ----
from modules.admin import handlers as admin_handlers
from modules.home import handlers as home_handlers
from modules.invite import handlers as invite_handlers
from modules.lang import handlers as lang_handlers
from modules.profile import handlers as profile_handlers
from modules.tts import handlers as tts_handlers
from modules.gpt import handlers as gpt_handlers

# GPT service (برای تماس با API)
from modules.gpt.service import GPTServiceError, chat_completion

# ========================= Mini-App HTTP Server =========================
STATIC_DIR = Path(__file__).resolve().parent / "modules" / "gpt"
API_ENDPOINT = "/api/gpt"
GPT_PREFIX = "/gpt"  # هر آدرسی با /gpt/ باید به استاتیک‌ها مپ شود


class MiniAppHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    سرو کامل مینی‌اپ (index.html, app.js, styles.css)
    + روت‌های API: /api/gpt  و  /api/health
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    # فقط در DEBUG لاگ بزن
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        if DEBUG:
            super().log_message(format, *args)

    # ------------------------ Helpers ------------------------
    def _normalized_path(self) -> str:
        return urlparse(self.path).path

    def _read_json_payload(self) -> Optional[Dict[str, Any]]:
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except Exception:
            n = 0
        raw = self.rfile.read(n) if n > 0 else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return None

    @staticmethod
    def _is_non_empty_list(value: Any) -> bool:
        return isinstance(value, list) and bool(value)

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

    def _json(self, status: int, obj: Dict[str, Any]) -> None:
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    # ------------------------ API: GET /api/health ------------------------
    def _health(self) -> None:
        # بدون لو دادن کلید، فقط وجودش را اعلام می‌کنیم
        try:
            from config import GPT_API_KEY, GPT_MODEL  # import محلی برای به‌روز بودن
            ok = bool(GPT_API_KEY)
            self._json(
                HTTPStatus.OK,
                {"ok": True, "gpt_key_present": ok, "model": (GPT_MODEL or "gpt-4o-mini")},
            )
        except Exception as exc:
            self._json(HTTPStatus.OK, {"ok": False, "error": f"health error: {exc}"})

    # ------------------------ API: POST /api/gpt ------------------------
    def do_POST(self) -> None:  # noqa: N802
        path = self._normalized_path()
        if path != API_ENDPOINT:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        payload = self._read_json_payload()
        if not isinstance(payload, dict):
            self._json(HTTPStatus.OK, {"ok": False, "error": "invalid json"})
            return

        messages = payload.get("messages")
        if not self._is_non_empty_list(messages):
            self._json(HTTPStatus.OK, {"ok": False, "error": "messages must be a non-empty list"})
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
            # موفق
            self._json(HTTPStatus.OK, {"ok": True, "data": data})
            return
        except GPTServiceError as exc:
            # خطای قابل‌پیش‌بینی سمت GPT (کلید اشتباه، مدل نامعتبر، ...)
            if DEBUG:
                print("GPT API error:", exc)
            self._json(HTTPStatus.OK, {"ok": False, "error": str(exc)})
            return
        except Exception as exc:  # خطای غیرمنتظره
            if DEBUG:
                print("Unexpected GPT handler error:", exc)
            self._json(HTTPStatus.OK, {"ok": False, "error": "internal server error"})
            return

    # ------------------------ Static GET ------------------------
    def do_GET(self) -> None:  # noqa: N802
        path = self._normalized_path()

        # Health
        if path == "/api/health":
            self._health()
            return

        # /gpt → /gpt/ (برای اصلاح مسیرهای نسبی)
        if path == GPT_PREFIX:
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", f"{GPT_PREFIX}/")
            self.end_headers()
            return

        # "/" و "/gpt/" → index.html
        if path in ("/", f"{GPT_PREFIX}/"):
            self.path = "/index.html"
            super().do_GET()
            return

        # هر چیزی با /gpt/ شروع شود به ریشه استاتیک مپ کن
        if path.startswith(f"{GPT_PREFIX}/"):
            stripped = path[len(GPT_PREFIX):]  # حذف "/gpt"
            self.path = stripped or "/index.html"
            super().do_GET()
            return

        # سایر مسیرها
        super().do_GET()

    # جلوگیری از کش
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def start_http_server(port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("0.0.0.0", port), MiniAppHTTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, name="gpt-mini-app", daemon=True)
    thread.start()
    return server

# ========================= Telegram Bot Wiring =========================
def create_bot() -> telebot.TeleBot:
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN در secrets تعریف نشده")
    return telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

def register_modules(bot: telebot.TeleBot) -> None:
    admin_handlers.register(bot)
    lang_handlers.register(bot)
    home_handlers.register(bot)
    invite_handlers.register(bot)
    profile_handlers.register(bot)
    tts_handlers.register(bot)
    gpt_handlers.register(bot)

def main() -> None:
    db.init_db()
    bot = create_bot()
    register_modules(bot)

    port = int(os.environ.get("PORT", "8000"))
    start_http_server(port)
    if DEBUG:
        print(f"✅ HTTP server listening on 0.0.0.0:{port}")
        print(f"✅ Serving GPT mini-app from: {STATIC_DIR}")

    bot.infinity_polling(
        skip_pending=True,
        allowed_updates=["message", "callback_query", "pre_checkout_query", "successful_payment"],
    )

if __name__ == "__main__":
    main()
