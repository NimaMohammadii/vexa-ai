"""Handlers for OpenAI-powered text-to-speech."""

from __future__ import annotations

from io import BytesIO
import math
import time

import db
from utils import edit_or_send, ensure_force_sub, is_sound_enabled
from modules.i18n import t
from modules.tts.texts import ask_text, PROCESSING, NO_CREDIT, ERROR, BANNED
from modules.tts.keyboards import no_credit_keyboard
from modules.tts.upsell import schedule_creator_upsell
from .keyboards import keyboard as tts_keyboard
from .settings import (
    STATE_WAIT_TEXT,
    VOICES,
    DEFAULT_VOICE_NAME,
    CHARS_PER_CREDIT,
    CREDIT_PER_10_CHARS,
    OUTPUTS,
    BANNED_WORDS,
)
from .service import synthesize


_NORMALIZE_REPLACEMENTS = {
    "ك": "ک",
    "ي": "ی",
    "ى": "ی",
    "ؤ": "و",
    "إ": "ا",
    "أ": "ا",
    "آ": "ا",
    "ة": "ه",
    "ۀ": "ه",
}


def _normalize_text(text: str) -> str:
    normalized = (text or "").lower()
    for src, dst in _NORMALIZE_REPLACEMENTS.items():
        normalized = normalized.replace(src, dst)
    return normalized.replace("ـ", "").replace("\u200c", " ").replace("\u200d", "")


_BANNED_WORDS = tuple(_normalize_text(word) for word in BANNED_WORDS if word)


def _has_banned_word(text: str) -> bool:
    normalized = _normalize_text(text)
    return any(word and word in normalized for word in _BANNED_WORDS)


def _parse_state(raw: str):
    parts = (raw or "").split(":")
    menu_id = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None
    voice_name = parts[3] if len(parts) >= 4 else DEFAULT_VOICE_NAME
    return menu_id, voice_name


def _make_state(menu_id: int, voice_name: str) -> str:
    return f"{STATE_WAIT_TEXT}:{menu_id}:{voice_name}"

def _resolve_openai_voice(user_id: int, desired_voice: str) -> str | None:
    disabled = db.list_disabled_voices(user_id, "openai")
    if desired_voice in VOICES and desired_voice not in disabled:
        return desired_voice
    for name in VOICES.keys():
        if name not in disabled:
            return name
    return None


def safe_del(bot, chat_id, message_id):
    if not chat_id or not message_id:
        return
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("tts_openai:"))
    def tts_openai_router(cq):
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        if not ensure_force_sub(bot, user["user_id"], cq.message.chat.id, cq.message.message_id, lang):
            bot.answer_callback_query(cq.id)
            return
        if not is_sound_enabled():
            bot.answer_callback_query(cq.id, t("audio_disabled", lang), show_alert=True)
            return

        route = cq.data.split(":", 1)[1]

        if route == "quality:medium":
            state = db.get_state(cq.from_user.id) or ""
            _, voice_name = _parse_state(state)
            resolved = _resolve_openai_voice(user["user_id"], voice_name)
            if not resolved:
                bot.answer_callback_query(cq.id, t("tts_voice_disabled", lang))
                return
            voice_name = resolved

            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                ask_text(
                    lang,
                    voice_name,
                    credit_per_char=CREDIT_PER_10_CHARS,
                    prompt_key="tts_prompt_medium",
                    show_demo_link=False,
                ),
                tts_keyboard(voice_name, lang, user["user_id"]),
            )
            db.set_state(cq.from_user.id, _make_state(cq.message.message_id, voice_name))
            bot.answer_callback_query(cq.id, t("tts_quality_medium", lang))
            return

        if route == "quality:pro":
            from modules.tts.handlers import open_tts as open_pro_tts

            open_pro_tts(bot, cq)
            bot.answer_callback_query(cq.id, t("tts_quality_pro", lang))
            return

        if route.startswith("voice:"):
            name = route.split(":", 1)[1]
            if name not in VOICES:
                bot.answer_callback_query(cq.id, t("tts_voice_not_found", lang))
                return
            if name in db.list_disabled_voices(user["user_id"], "openai"):
                bot.answer_callback_query(cq.id, t("tts_voice_disabled", lang))
                return

            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                ask_text(
                    lang,
                    name,
                    credit_per_char=CREDIT_PER_10_CHARS,
                    prompt_key="tts_prompt_medium",
                    show_demo_link=False,
                ),
                tts_keyboard(name, lang, user["user_id"]),
            )
            db.set_state(cq.from_user.id, _make_state(cq.message.message_id, name))
            bot.answer_callback_query(cq.id, name)
            return

    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_WAIT_TEXT),
        content_types=["text"],
    )
    def on_text_to_tts(msg):
        user = db.get_or_create_user(msg.from_user)
        user_id = user["user_id"]

        current_state = db.get_state(user_id) or ""

        if current_state.startswith("tts_openai:processing"):
            return

        db.set_state(user_id, f"tts_openai:processing:{int(time.time())}")

        cost = 0
        status = None
        try:
            lang = db.get_user_lang(user_id, "fa")

            if not ensure_force_sub(bot, user_id, msg.chat.id, msg.message_id, lang):
                return
            if not is_sound_enabled():
                bot.send_message(msg.chat.id, t("audio_disabled", lang))
                last_menu_id, voice_name = _parse_state(current_state)
                db.set_state(user_id, _make_state(last_menu_id or msg.message_id, voice_name))
                return

            last_menu_id, voice_name = _parse_state(current_state)
            resolved = _resolve_openai_voice(user_id, voice_name)
            if not resolved:
                bot.send_message(msg.chat.id, t("tts_voice_disabled", lang))
                db.set_state(user_id, _make_state(last_menu_id or msg.message_id, voice_name))
                return
            voice_name = resolved
            voice_id = VOICES.get(voice_name)

            text = (msg.text or "").strip()
            if not text:
                return

            if _has_banned_word(text):
                bot.send_message(msg.chat.id, BANNED(lang))
                db.set_state(user_id, _make_state(last_menu_id or msg.message_id, voice_name))
                return

            try:
                db.log_tts_request(user_id, text)
            except Exception:
                pass

            chunks = math.ceil(len(text) / CHARS_PER_CREDIT)
            cost = db.normalize_credit_amount(chunks * CREDIT_PER_10_CHARS)
            balance = db.normalize_credit_amount(user.get("credits", 0))
            if balance < cost:
                bot.send_message(
                    msg.chat.id,
                    NO_CREDIT(lang, balance, cost),
                    reply_markup=no_credit_keyboard(lang),
                )
                return

            if not db.deduct_credits(user_id, cost):
                refreshed = db.get_user(user_id) or {}
                new_balance = db.normalize_credit_amount(refreshed.get("credits", 0))
                bot.send_message(
                    msg.chat.id,
                    NO_CREDIT(lang, new_balance, cost),
                    reply_markup=no_credit_keyboard(lang),
                )
                return

            status = bot.send_message(msg.chat.id, PROCESSING(lang))

            print(
                f"🔥 OPENAI TTS REQUEST: user={user_id}, text_len={len(text)}, voice={voice_name}"
            )
            audio_data = synthesize(text, voice_id, OUTPUTS[0]["mime"])
            print(
                f"✅ OPENAI TTS RESPONSE: user={user_id}, audio_size={len(audio_data)} bytes"
            )

            safe_del(bot, status.chat.id if status else None, status.message_id if status else None)
            if last_menu_id:
                safe_del(bot, msg.chat.id, last_menu_id)

            bio = BytesIO(audio_data)
            bio.name = "Vexa.mp3"
            bot.send_document(msg.chat.id, document=bio)

            new_menu = bot.send_message(
                msg.chat.id,
                ask_text(
                    lang,
                    voice_name,
                    credit_per_char=CREDIT_PER_10_CHARS,
                    prompt_key="tts_prompt_medium",
                    show_demo_link=False,
                ),
                reply_markup=tts_keyboard(voice_name, lang, user_id),
            )
            db.set_state(user_id, _make_state(new_menu.message_id, voice_name))
            schedule_creator_upsell(bot, user_id, msg.chat.id)

        except Exception as e:
            try:
                if cost:
                    db.add_credits(user_id, cost)
                    print(
                        f"❌ OPENAI TTS ERROR: user={user_id}, credits refunded={cost}, error={e}"
                    )
            except Exception:
                pass

            if status:
                safe_del(bot, status.chat.id, status.message_id)
            err = ERROR(lang)
            bot.send_message(msg.chat.id, err)
            db.clear_state(user_id)

        finally:
            current = db.get_state(user_id) or ""
            if current.startswith("tts_openai:processing"):
                db.clear_state(user_id)


def open_tts(bot, cq, voice_name: str | None = None):
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    if not is_sound_enabled():
        edit_or_send(
            bot,
            cq.message.chat.id,
            cq.message.message_id,
            t("audio_disabled", lang),
            None,
        )
        return
    sel = voice_name if voice_name in VOICES else DEFAULT_VOICE_NAME
    edit_or_send(
        bot,
        cq.message.chat.id,
        cq.message.message_id,
        ask_text(
            lang,
            sel,
            credit_per_char=CREDIT_PER_10_CHARS,
            prompt_key="tts_prompt_medium",
            show_demo_link=False,
        ),
        tts_keyboard(sel, lang, user["user_id"]),
    )
    db.set_state(cq.from_user.id, _make_state(cq.message.message_id, sel))
