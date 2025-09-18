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
from modules.gpt import service as gpt_service  # برای /api/gpt

# ========================= Mini-App HTTP Server =========================
STATIC_DIR = Path(__file__).resolve().parent / "modules" / "gpt"
API_ENDPOINT = "/api/gpt"
_GPT_PREFIX = "/gpt"         # هرچی با /gpt/ شروع شد باید به ریشه استاتیک مپ شود

class MiniAppHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    سرو کامل مینی‌اپ (index.html, app.js, styles.css)
    + روت POST برای /api/gpt که به OpenAI وصل می‌شود (modules.gpt.service).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    # لاگ فقط در DEBUG
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

    def _json(self, status: int, obj: Dict[str, Any]) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))

    # ------------------------ API: POST /api/gpt ------------------------
    def do_POST(self) -> None:  # noqa: N802
        if self._normalized_path() != API_ENDPOINT:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        payload = self._read_json_payload()
        if not isinstance(payload, dict):
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid json"})
            return

        prompt = (payload.get("prompt") or "").strip()
        history = payload.get("history") or []          # [{role, content}, ...]
        model = (payload.get("model") or "gpt-4o-mini").strip()
        system_prompt = payload.get("systemPrompt")

        if not prompt:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "empty prompt"})
            return

        # فقط رول‌های مجاز را عبور بده
        safe_history = [
            {"role": m.get("role"), "content": m.get("content")}
            for m in history
            if isinstance(m, dict)
            and m.get("role") in {"system", "user", "assistant"}
            and isinstance(m.get("content"), str)
        ]

        try:
            data = gpt_service.request_chat(
                prompt=prompt,
                history=safe_history,
                model=model,
                system_prompt=system_prompt,
            )
            reply = gpt_service.extract_message_text(data) or ""
            self._json(HTTPStatus.OK, {"ok": True, "reply": reply, "raw": data})
        except gpt_service.GPTServiceError as exc:
            self._json(HTTPStatus.BAD_GATEWAY, {"ok": False, "error": str(exc)})

    # ------------------------ Static GET ------------------------
    def do_GET(self) -> None:  # noqa: N802
        path = self._normalized_path()

        # 1) /gpt → /gpt/ (برای درست‌شدن مسیرهای نسبی)
        if path == _GPT_PREFIX:
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", _GPT_PREFIX + "/")
            self.end_headers()
            return

        # 2) "/", "/gpt/" → index.html
        if path == "/" or path == _GPT_PREFIX + "/":
            self.path = "/index.html"
            return super().do_GET()

        # 3) هرچیزی که با /gpt/ شروع می‌شود را به ریشه استاتیک مپ کن:
        #    /gpt/styles.css  -> /styles.css
        #    /gpt/app.js      -> /app.js
        #    /gpt/anything    -> /anything
        if path.startswith(_GPT_PREFIX + "/"):
            stripped = path[len(_GPT_PREFIX):]  # حذف "/gpt"
            self.path = stripped if stripped else "/index.html"
            return super().do_GET()

        # 4) سایر مسیرها را عادی سرو کن
        return super().do_GET()

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
        raise RuntimeError("BOT_TOKEN is not set")
    return telebot.TeleBot(BOT_TOKEN, parse_mode=None)

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
        allowed_updates=["message","callback_query","pre_checkout_query","successful_payment"],
    )

if __name__ == "__main__":
    main()
