from __future__ import annotations

"""Telegram handlers for the Anonymous Chat module."""

import json
import random
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
from config import GPT_API_KEY
from modules.gpt.service import GPTServiceError, chat_completion, extract_message_text, resolve_gpt_api_key
from utils import check_force_sub, edit_or_send

from .characters import CHARACTERS

ANON_STATE_PREFIX = "anon_chat"
SEARCHING_TEXT = "در حال جستجو برای یک کاربر ناشناس… ⏳"
CONNECTED_TEXT = "وصل شدی ✅ می‌تونی شروع کنی."
DISCONNECTED_TEXT = "ارتباط قطع شد ❌"
ENDED_TEXT = "ارتباط پایان یافت. برای شروع دوباره، روی 'چت ناشناس 🎭' کلیک کن."
GPT_MISSING_TEXT = "❌ سرویس گفتگو در دسترس نیست."
MAX_HISTORY_ITEMS = 12
MIN_CONNECTION_DELAY = 12
INITIAL_MESSAGE_DELAY_RANGE: Tuple[int, int] = (1, 5)
RESPONSE_DELAY_RANGE: Tuple[int, int] = (8, 20)
INITIAL_MESSAGE_PROBABILITY = 0.5
STICKER_PROBABILITY = 0.01
STICKER_FILE_IDS: Sequence[str] = ()

INITIAL_MESSAGES: Sequence[Tuple[str, float]] = (
    ("سلام", 0.80),
    ("چطوری", 0.013),
    ("خوبی؟", 0.013),
    ("کجایی هستی؟", 0.013),
    ("اسکل", 0.013),
    ("😒", 0.01),
    ("🤨", 0.02),
    ("عجب", 0.013),
    ("دختری یا پسر ؟", 0.013),
    ("دختری؟", 0.013),
    ("پسری یا چی ؟", 0.013),
    ("دختری یا چی؟", 0.013),
    ("کجا زندگی میکنی؟", 0.013),
    ("سلم", 0.013),
    ("های", 0.013),
    ("کجایی هستی", 0.013),
    ("عجیب نیست؟", 0.013),
)


def _weighted_choice(options: Sequence[Tuple[str, float]]) -> str:
    if not options:
        return "سلام"
    total = sum(weight for _, weight in options if weight > 0)
    if total <= 0:
        return options[0][0]
    threshold = random.uniform(0, total)
    cumulative = 0.0
    for text, weight in options:
        if weight <= 0:
            continue
        cumulative += weight
        if cumulative >= threshold:
            return text
    return options[-1][0]


@dataclass
class AnonymousSession:
    status: str
    persona: Optional[Dict[str, Any]]
    history: List[Dict[str, str]]

    @classmethod
    def from_state(cls, data: Dict[str, Any]) -> "AnonymousSession":
        status = str(data.get("status") or "").strip() or "idle"
        persona = data.get("persona")
        history_data = data.get("history")
        if not isinstance(history_data, list):
            history = []
        else:
            history = []
            for item in history_data:
                if not isinstance(item, dict):
                    continue
                role = str(item.get("role") or "").strip()
                content = str(item.get("content") or "").strip()
                if role and content:
                    history.append({"role": role, "content": content})
        return cls(status=status, persona=persona, history=history)

    def to_state(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "persona": self.persona,
            "history": list(self.history),
        }


def _ensure_gpt_ready() -> bool:
    return bool(GPT_API_KEY or resolve_gpt_api_key())


def _make_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("بعدی ➡️", callback_data="anon_chat:next"),
        InlineKeyboardButton("پایان ❌", callback_data="anon_chat:end"),
    )
    return kb


def _load_session(user_id: int) -> Optional[AnonymousSession]:
    raw = db.get_state(user_id) or ""
    prefix = f"{ANON_STATE_PREFIX}:"
    if not raw.startswith(prefix):
        return None
    payload = raw[len(prefix) :]
    try:
        data = json.loads(payload)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return AnonymousSession.from_state(data)


def _save_session(user_id: int, session: AnonymousSession) -> None:
    state = json.dumps(session.to_state(), ensure_ascii=False)
    db.set_state(user_id, f"{ANON_STATE_PREFIX}:{state}")


def _build_system_prompt(persona: Dict[str, Any]) -> str:
    name = persona.get("name", "")
    gender = persona.get("gender", "")
    age = persona.get("age", "")
    style = persona.get("style", "")
    interests = persona.get("interests") or []
    behaviors = persona.get("behaviors") or []
    examples = persona.get("examples") or []

    gender_label = "دختر" if str(gender).lower() == "female" else "پسر"

    def _fmt(items: List[Any]) -> str:
        values = [str(item) for item in items if str(item).strip()]
        return "\n".join(f"- {value}" for value in values)

    interests_text = ", ".join(str(item) for item in interests if str(item).strip())

    rules: List[str] = [
        "فقط فارسی محاوره‌ای بنویس و از اموجی مناسب استفاده کن.",
        "همیشه خودت را یک انسان واقعی معرفی کن و هرگز نگو ربات یا هوش مصنوعی هستی.",
        "استایل و لحن شخصیت را دقیقا رعایت کن و به جزئیات رفتارهایش توجه داشته باش.",
        "حدود ۳۰٪ مواقع جواب خیلی کوتاه (۱ تا ۳ کلمه) یا شبیه مثال‌های شخصیت بده.",
        "حدود ۱۰٪ مواقع فقط یک اموجی یا استیکر متنی بفرست (مثلا 😂 یا 😅).",
        "حدود ۵۰٪ مواقع جواب کامل بین ۱ تا ۳ جمله بده.",
        "حدود ۱۰٪ مواقع طبیعی به سن یا علایق یا جنسیت خودت اشاره کن.",
        "به تاریخچه مکالمه دقت کن و به صحبت‌های قبلی ارجاع بده.",
        "اگر گفتگو حس رمانتیک پیدا کرد و شخصیت دختر است با لحن نرم و ناز جواب بده.",
        "اگر شخصیت پسر است می‌تواند رک، شوخ و کمی شیطون باشد.",
    ]

    rules_text = "\n".join(f"- {rule}" for rule in rules)

    prompt = f"""
تو باید نقش یک انسان واقعی را بازی کنی و هویت واقعی‌ات همیشه همین شخصیت باشد. هیچ‌وقت اشاره نکن که ربات یا مدل زبانی هستی.

مشخصات شخصیت:
- نام: {name}
- جنسیت: {gender_label}
- سن: {age}
- استایل: {style}
- علایق: {interests_text or 'نامشخص'}

رفتارهای مهم:
{_fmt(behaviors)}

نمونه جملات:
{_fmt(examples)}

قوانین پاسخ‌گویی:
{rules_text}
""".strip()

    return prompt


def _handle_force_sub(bot, user_id: int, chat_id: int, message_id: int | None, lang: str) -> bool:
    settings = db.get_settings()
    mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
    if mode not in {"new", "all"}:
        return True
    ok, txt, kb = check_force_sub(bot, user_id, settings, lang)
    if ok:
        return True
    edit_or_send(bot, chat_id, message_id, txt, kb)
    return False


def _start_search(bot, user_id: int, chat_id: int) -> None:
    session = AnonymousSession(status="searching", persona=None, history=[])
    _save_session(user_id, session)

    try:
        bot.send_message(chat_id, SEARCHING_TEXT)
    except Exception:
        return

    delay = random.uniform(MIN_CONNECTION_DELAY, MIN_CONNECTION_DELAY + 6)

    def _complete_connection() -> None:
        current = _load_session(user_id)
        if not current or current.status != "searching":
            return
        persona = random.choice(CHARACTERS)
        next_session = AnonymousSession(status="active", persona=persona, history=[])
        _save_session(user_id, next_session)
        try:
            bot.send_message(chat_id, CONNECTED_TEXT, reply_markup=_make_keyboard())
        except Exception:
            pass
        else:
            def _send_initial_message() -> None:
                session = _load_session(user_id)
                if not session or session.status != "active":
                    return
                if random.random() > INITIAL_MESSAGE_PROBABILITY:
                    return
                text = _weighted_choice(INITIAL_MESSAGES)
                try:
                    bot.send_message(chat_id, text)
                except Exception:
                    pass

            initial_delay = random.uniform(*INITIAL_MESSAGE_DELAY_RANGE)
            timer = threading.Timer(initial_delay, _send_initial_message)
            timer.daemon = True
            timer.start()

    timer = threading.Timer(delay, _complete_connection)
    timer.daemon = True
    timer.start()


def _reset_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if len(history) <= MAX_HISTORY_ITEMS:
        return history
    return history[-MAX_HISTORY_ITEMS:]


def _process_user_message(bot, message: Message, session: AnonymousSession) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    persona = session.persona
    if not isinstance(persona, dict):
        bot.reply_to(message, SEARCHING_TEXT)
        return

    if not _ensure_gpt_ready():
        bot.reply_to(message, GPT_MISSING_TEXT)
        return

    system_prompt = _build_system_prompt(persona)

    history = _reset_history(list(session.history))

    gpt_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for item in history:
        gpt_messages.append({"role": item["role"], "content": item["content"]})

    gpt_messages.append({"role": "user", "content": text})

    try:
        response = chat_completion(gpt_messages)
        answer = (extract_message_text(response) or "").strip()
    except GPTServiceError as exc:
        bot.reply_to(message, f"⚠️ خطا در دریافت پاسخ: {exc}")
        return
    except Exception:
        bot.reply_to(message, "⚠️ خطای نامشخص رخ داد.")
        return

    if not answer:
        answer = "😅"

    answer = answer[:60]

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": answer})
    session.history = _reset_history(history)
    _save_session(message.from_user.id, session)

    def _send_response() -> None:
        if random.random() < STICKER_PROBABILITY and STICKER_FILE_IDS:
            sticker_id = random.choice(STICKER_FILE_IDS)
            try:
                bot.send_sticker(message.chat.id, sticker_id)
                return
            except Exception:
                pass
        try:
            bot.send_message(message.chat.id, answer)
        except Exception:
            pass

    delay = random.uniform(*RESPONSE_DELAY_RANGE)
    timer = threading.Timer(delay, _send_response)
    timer.daemon = True
    timer.start()


def register(bot) -> None:
    @bot.callback_query_handler(func=lambda c: c.data == "home:anon_chat")
    def open_anonymous_chat(cq: CallbackQuery) -> None:
        user = db.get_or_create_user(cq.from_user)
        if user.get("banned"):
            bot.answer_callback_query(cq.id, "⛔️")
            return

        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])

        if not _handle_force_sub(bot, user["user_id"], cq.message.chat.id, cq.message.message_id, lang):
            bot.answer_callback_query(cq.id)
            return

        if not _ensure_gpt_ready():
            bot.answer_callback_query(cq.id, show_alert=True, text=GPT_MISSING_TEXT)
            return

        bot.answer_callback_query(cq.id)
        _start_search(bot, user["user_id"], cq.message.chat.id)

    @bot.callback_query_handler(func=lambda c: c.data == "anon_chat:next")
    def handle_next(cq: CallbackQuery) -> None:
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        db.touch_last_seen(user["user_id"])

        session = _load_session(user["user_id"])
        if not session:
            bot.answer_callback_query(cq.id, "⏳")
            _start_search(bot, user["user_id"], cq.message.chat.id)
            return

        bot.answer_callback_query(cq.id)
        try:
            bot.edit_message_reply_markup(cq.message.chat.id, cq.message.message_id, reply_markup=None)
        except Exception:
            pass
        bot.send_message(cq.message.chat.id, DISCONNECTED_TEXT)
        _start_search(bot, user["user_id"], cq.message.chat.id)

    @bot.callback_query_handler(func=lambda c: c.data == "anon_chat:end")
    def handle_end(cq: CallbackQuery) -> None:
        user = db.get_or_create_user(cq.from_user)
        db.touch_last_seen(user["user_id"])
        db.clear_state(user["user_id"])

        bot.answer_callback_query(cq.id)
        try:
            bot.edit_message_reply_markup(cq.message.chat.id, cq.message.message_id, reply_markup=None)
        except Exception:
            pass
        bot.send_message(cq.message.chat.id, ENDED_TEXT)

    def _is_anonymous_chat(message: Message) -> bool:
        state = db.get_state(message.from_user.id) or ""
        return state.startswith(f"{ANON_STATE_PREFIX}:")

    @bot.message_handler(func=_is_anonymous_chat, content_types=["text"])
    def handle_message(msg: Message) -> None:
        user = db.get_or_create_user(msg.from_user)
        if user.get("banned"):
            bot.reply_to(msg, "⛔️ دسترسی شما مسدود است.")
            return

        db.touch_last_seen(user["user_id"])

        session = _load_session(user["user_id"])
        if not session or session.status != "active" or not session.persona:
            bot.reply_to(msg, SEARCHING_TEXT)
            return

        _process_user_message(bot, msg, session)
