import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from a .env file if present.
# We call load_dotenv twice: once with the default search behaviour (which
# respects the current working directory), and once explicitly pointing to a
# .env file that sits next to this config module. This ensures the bot works
# whether it is started from the project root or from another working
# directory.
load_dotenv()
load_dotenv(Path(__file__).resolve().parent / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
RUNWAY_API_KEY = os.getenv("RUNWAY_API") or os.getenv("RUNWAY_API_KEY")
CARD_NUMBER = os.getenv("CARD_NUMBER", "****-****-****-****")

try:
    BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))
except Exception:
    BOT_OWNER_ID = 0

DEBUG = os.getenv("DEBUG", "true").lower() == "true"


def _first_non_empty(*values: Optional[str]) -> str:
    for value in values:
        if value is None:
            continue

        candidate = str(value).strip()
        if candidate:
            return candidate

    return ""


def _parse_float(value: Optional[str], default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _parse_int(value: Optional[str], default: int) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


GPT_API_KEY = _first_non_empty(
    os.getenv("GPT_API"),
    os.getenv("GPT_API_KEY"),
    os.getenv("OPENAI_API_KEY"),
).strip()

_GPT_MODE_RAW = (
    os.getenv("GPT_MODE")
    or os.getenv("GPT_PROVIDER")
    or os.getenv("GPT_API_MODE")
    or "chat"
)
_GPT_MODE_NORMALISED = (_GPT_MODE_RAW or "").strip().lower()
if _GPT_MODE_NORMALISED in {"assistant", "assistants", "assistant-api", "assistant_api", "responses", "response"}:
    GPT_MODE = "assistant"
else:
    GPT_MODE = "chat"

_DEFAULT_CHAT_API_URL = "https://api.openai.com/v1/chat/completions"
_DEFAULT_ASSISTANT_API_URL = "https://api.openai.com/v1/responses"
_default_url = _DEFAULT_ASSISTANT_API_URL if GPT_MODE == "assistant" else _DEFAULT_CHAT_API_URL

GPT_API_URL = (os.getenv("GPT_API_URL") or _default_url).strip() or _default_url
GPT_MODEL = (os.getenv("GPT_MODEL") or "gpt-4o-mini").strip() or "gpt-4o-mini"
GPT_API_TIMEOUT = _parse_float(os.getenv("GPT_API_TIMEOUT", "45"), 45.0)
GPT_API_KEY_HEADER = (os.getenv("GPT_API_KEY_HEADER") or "Authorization").strip() or "Authorization"
GPT_API_KEY_PREFIX = os.getenv("GPT_API_KEY_PREFIX")
if GPT_API_KEY_PREFIX is None:
    GPT_API_KEY_PREFIX = "Bearer "

GPT_ASSISTANT_ID = (
    os.getenv("GPT_ASSISTANT_ID")
    or os.getenv("OPENAI_ASSISTANT_ID")
    or os.getenv("ASSISTANT_ID")
    or ""
).strip()

_DEFAULT_SYSTEM_PROMPT = (
    "You are Vexa GPT. Reply in the user's language with concise, direct answers."
    " Keep responses to one or two short sentences, include only essential facts, and avoid filler."
)
GPT_SYSTEM_PROMPT = (os.getenv("GPT_SYSTEM_PROMPT") or _DEFAULT_SYSTEM_PROMPT).strip() or _DEFAULT_SYSTEM_PROMPT
GPT_HISTORY_LIMIT = max(1, _parse_int(os.getenv("GPT_HISTORY_LIMIT", "6"), 6))
GPT_TEMPERATURE = min(2.0, max(0.0, _parse_float(os.getenv("GPT_TEMPERATURE"), 0.7)))
GPT_TOP_P = min(1.0, max(0.0, _parse_float(os.getenv("GPT_TOP_P"), 1.0)))
GPT_MAX_TOKENS = max(0, _parse_int(os.getenv("GPT_MAX_TOKENS"), 400))
GPT_MESSAGE_COST = _parse_float(os.getenv("GPT_MESSAGE_COST", "1"), 1.0)
GPT_SEARCH_MESSAGE_COST = _parse_float(os.getenv("GPT_SEARCH_MESSAGE_COST", "2"), 2.0)

GPT_RESPONSE_CHAR_LIMIT = max(
    0,
    _parse_int(os.getenv("GPT_RESPONSE_CHAR_LIMIT", "900"), 900),
)

