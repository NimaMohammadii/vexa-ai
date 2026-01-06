# modules/gpt/service.py
"""GPT chat completion service helper."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

import requests

from config import (
    DEBUG,
    GPT_API_KEY,
    GPT_API_KEY_HEADER,
    GPT_API_KEY_PREFIX,
    GPT_API_TIMEOUT,
    GPT_API_URL,
    GPT_MAX_TOKENS,
    GPT_MODEL,
    GPT_MODE,
    GPT_SYSTEM_PROMPT,
    GPT_TEMPERATURE,
    GPT_TOP_P,
)

_ALLOWED_ROLES = {"system", "user", "assistant"}
_ASSISTANT_MODES = {"assistant"}


def _is_assistant_mode() -> bool:
    return (GPT_MODE or "").lower() in _ASSISTANT_MODES


class GPTServiceError(RuntimeError):
    """Raised when the upstream GPT provider returns an error."""


_COMMON_KEY_NAMES = {
    "gpt_api",
    "gpt_api_key",
    "openai_api",
    "openai_api_key",
    "openai_key",
    "openai_token",
    "api_key",
    "apikey",
    "api_token",
    "token",
}

_DIRECT_SETTING_NAMES = (
    "GPT_API",
    "GPT_API_KEY",
    "GPTAPI",
    "OPENAI_API",
    "OPENAI_API_KEY",
    "OPENAI_KEY",
    "OPENAI_TOKEN",
    "OPENAI_SECRET_KEY",
)

_cached_api_key: Optional[str] = None


def _clean_candidate(text: str) -> str:
    """Normalise a text snippet that may contain an API key."""

    candidate = (text or "").strip()
    candidate = candidate.strip('"')
    candidate = candidate.strip("'")
    if not candidate:
        return ""

    if candidate.startswith(("{", "[")):
        # Likely JSON; let the caller decode separately
        return candidate

    if "sk-" in candidate:
        candidate = candidate[candidate.index("sk-") :]

    # Stop at obvious separators to avoid trailing punctuation
    for separator in ("\n", "\r", "\t", " ", ",", ";"):
        if separator in candidate:
            candidate = candidate.split(separator, 1)[0]

    candidate = candidate.strip()
    candidate = candidate.strip('"')
    candidate = candidate.strip("'")
    if not candidate:
        return ""

    return candidate


def _looks_like_api_key(text: str, *, allow_loose: bool) -> bool:
    """Heuristic check to make sure we only return plausible API keys."""

    if not text or " " in text:
        return False

    lowered = text.lower()
    if lowered.startswith(("sk-", "rk-", "gpt-", "gpt_")):
        return True

    if lowered.startswith(("http://", "https://")):
        return False

    return allow_loose and len(text) >= 24


def _extract_from_structure(value: Any, *, allow_loose: bool) -> str:
    """Recursively inspect a nested structure (possibly JSON) for an API key."""

    if value is None:
        return ""

    if isinstance(value, (list, tuple, set)):
        for item in value:
            candidate = _extract_from_structure(item, allow_loose=allow_loose)
            if candidate:
                return candidate
        return ""

    if isinstance(value, dict):
        for key, item in value.items():
            key_name = str(key or "").lower()
            candidate = _extract_from_structure(
                item,
                allow_loose=allow_loose or key_name in _COMMON_KEY_NAMES or any(term in key_name for term in ("gpt", "openai")),
            )
            if candidate:
                return candidate
        return ""

    text = _clean_candidate(str(value))
    if not text:
        return ""

    if text.startswith(("{", "[")):
        try:
            parsed = json.loads(text)
        except Exception:
            # Fall through to direct heuristics if parsing fails
            parsed = None
        else:
            return _extract_from_structure(parsed, allow_loose=allow_loose)

    if _looks_like_api_key(text, allow_loose=allow_loose):
        return text

    return ""


def _extract_api_key(value: Any, *, allow_loose: bool = False) -> str:
    """Helper to extract an API key from arbitrary stored values."""

    return _extract_from_structure(value, allow_loose=allow_loose)


def resolve_gpt_api_key(force_refresh: bool = False) -> str:
    """Return the configured GPT API key from env or dynamic settings."""

    global _cached_api_key

    if not force_refresh and _cached_api_key:
        return _cached_api_key

    if GPT_API_KEY:
        _cached_api_key = GPT_API_KEY
        return _cached_api_key

    try:
        import db  # local import to avoid circular dependency at module import time
    except Exception:
        _cached_api_key = ""
        return ""

    # ابتدا تلاش می‌کنیم کلید را از نام‌های رایج (با در نظر گرفتن نسخه حروف کوچک) بخوانیم
    for key_name in _DIRECT_SETTING_NAMES:
        variants = {key_name, key_name.lower(), key_name.replace("_", ""), key_name.replace("_", "-")}
        for variant in variants:
            if not variant:
                continue
            value = db.get_setting(variant)
            candidate = _extract_api_key(value, allow_loose=True)
            if candidate:
                _cached_api_key = candidate
                return candidate

    for key_name in ("GPT_API", "GPT_API_KEY", "OPENAI_API_KEY"):
        for variant in {key_name, key_name.lower()}:
            value = db.get_setting(variant)
            candidate = _extract_api_key(value, allow_loose=True)
            if candidate:
                _cached_api_key = candidate
                return candidate

    try:
        settings = db.get_settings()
    except Exception:
        settings = {}

    # سپس کل جدول تنظیمات را جست‌وجو می‌کنیم تا کلیدهای مرتبط با GPT/OpenAI را بیابیم
    for key, value in settings.items():
        key_name = str(key or "").lower()
        if not key_name:
            continue
        allow_loose = key_name in _COMMON_KEY_NAMES or any(term in key_name for term in ("gpt", "openai"))
        candidate = _extract_api_key(value, allow_loose=allow_loose)
        if candidate:
            _cached_api_key = candidate
            return candidate

    # در نهایت، تمام مقادیر باقی‌مانده را با قواعد سخت‌گیرانه بررسی می‌کنیم
    for value in settings.values():
        candidate = _extract_api_key(value, allow_loose=False)
        if candidate:
            _cached_api_key = candidate
            return candidate

    _cached_api_key = ""
    return ""


def _build_headers() -> Dict[str, str]:
    api_key = resolve_gpt_api_key()
    if not api_key:
        raise GPTServiceError("GPT API key is not configured. Set GPT_API in secrets.")

    header_name = GPT_API_KEY_HEADER or "Authorization"
    header_value = f"{GPT_API_KEY_PREFIX or ''}{api_key}".strip()

    headers = {"Content-Type": "application/json"}
    headers[header_name] = header_value
    if _is_assistant_mode():
        headers.setdefault("OpenAI-Beta", "assistants=v2")
    return headers


def _normalise_message(message: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(message, dict):
        raise GPTServiceError("messages must be a list of role/content objects")

    role = str(message.get("role", "assistant")).strip().lower()
    if role not in _ALLOWED_ROLES:
        raise GPTServiceError(f"Unsupported message role: {role}")

    content = message.get("content")
    if isinstance(content, str):
        if not content.strip():
            raise GPTServiceError("Each message requires non-empty content")
        return {"role": role, "content": content}

    if isinstance(content, list):
        if not content:
            raise GPTServiceError("Each message requires non-empty content")
        validated: List[Dict[str, Any]] = []
        for item in content:
            if not isinstance(item, dict):
                raise GPTServiceError("Each content part must be a dict")
            part_type = (item.get("type") or "").strip()
            if not part_type:
                raise GPTServiceError("Each content part must include a type")
            validated.append(item)
        return {"role": role, "content": validated}

    raise GPTServiceError("Each message requires non-empty content")


def build_default_messages(history: Iterable[Dict[str, str]], user_content: Any) -> List[Dict[str, Any]]:
    """Compose a conversation list starting with the system prompt."""

    messages: List[Dict[str, Any]] = [{"role": "system", "content": GPT_SYSTEM_PROMPT}]
    for item in history:
        try:
            messages.append(_normalise_message(item))
        except GPTServiceError:
            if DEBUG:
                print("Ignoring malformed GPT history item:", item)
    messages.append({"role": "user", "content": user_content})
    return messages


def _prepare_chat_payload(
    normalised: List[Dict[str, Any]],
    *,
    model: Optional[str],
    temperature: Optional[float],
    top_p: Optional[float],
    max_tokens: Optional[int],
) -> Dict[str, Any]:
    chosen_model = (model or GPT_MODEL or "gpt-4o-mini").strip() or "gpt-4o-mini"

    payload: Dict[str, Any] = {
        "model": chosen_model,
        "messages": normalised,
        "temperature": temperature if temperature is not None else GPT_TEMPERATURE,
        "top_p": top_p if top_p is not None else GPT_TOP_P,
    }

    limit = max_tokens if max_tokens is not None else GPT_MAX_TOKENS
    if limit > 0:
        payload["max_tokens"] = limit

    return payload


def _prepare_assistant_payload(
    normalised: List[Dict[str, Any]],
    *,
    model: Optional[str],
    temperature: Optional[float],
    top_p: Optional[float],
    max_tokens: Optional[int],
) -> Dict[str, Any]:
    chosen_model = (model or GPT_MODEL or "gpt-4o-mini").strip() or "gpt-4o-mini"

    def _normalise_assistant_content(content: Any) -> Any:
        if isinstance(content, str):
            text = content.strip()
            if not text:
                return ""
            return [{"type": "input_text", "text": text}]

        if isinstance(content, list):
            parts: List[Dict[str, Any]] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                part_type = (item.get("type") or "").strip()
                if part_type == "text":
                    text = item.get("text") or item.get("content") or item.get("value") or ""
                    if str(text).strip():
                        parts.append({"type": "input_text", "text": str(text)})
                    continue
                if part_type == "image_url":
                    image_url = item.get("image_url")
                    url = ""
                    if isinstance(image_url, dict):
                        url = image_url.get("url") or image_url.get("image_url") or ""
                    elif isinstance(image_url, str):
                        url = image_url
                    if url:
                        parts.append({"type": "input_image", "image_url": url})
                    continue
                if part_type in {"input_text", "input_image"}:
                    parts.append(item)
                    continue
                parts.append(item)
            return parts if parts else ""

        return content

    # The Responses API expects the conversation history under the "input" key.
    payload: Dict[str, Any] = {
        "model": chosen_model,
        "input": [
            {
                "role": item.get("role", "assistant"),
                "content": _normalise_assistant_content(item.get("content", "")),
            }
            for item in normalised
        ],
        "temperature": temperature if temperature is not None else GPT_TEMPERATURE,
        "top_p": top_p if top_p is not None else GPT_TOP_P,
    }

    limit = max_tokens if max_tokens is not None else GPT_MAX_TOKENS
    if limit > 0:
        payload["max_output_tokens"] = limit

    return payload


def _prepare_payload(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    if not isinstance(messages, list) or not messages:
        raise GPTServiceError("messages must be a non-empty list")

    normalised = [_normalise_message(message) for message in messages]

    if _is_assistant_mode():
        return _prepare_assistant_payload(
            normalised,
            model=model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )

    return _prepare_chat_payload(
        normalised,
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )


def chat_completion(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Send the conversation to the configured GPT provider and return the JSON response."""

    payload = _prepare_payload(messages, model=model, temperature=temperature, top_p=top_p, max_tokens=max_tokens)

    try:
        response = requests.post(
            GPT_API_URL,
            headers=_build_headers(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            timeout=GPT_API_TIMEOUT,
        )
    except requests.RequestException as exc:  # pragma: no cover - network failure
        raise GPTServiceError(f"Network error calling GPT API: {exc}") from exc

    text = response.text
    try:
        data = response.json()
    except ValueError as exc:
        if DEBUG:
            print("GPT API returned non-JSON response:", text)
        raise GPTServiceError("Invalid response from GPT API") from exc

    if response.status_code >= 400:
        error_message = None
        if isinstance(data, dict):
            error_message = data.get("error") or data.get("message")
            if isinstance(error_message, dict):
                error_message = error_message.get("message") or error_message.get("code")
        if not error_message:
            error_message = response.reason or "GPT API request failed"
        raise GPTServiceError(str(error_message))

    return data


def extract_message_text(data: Dict[str, Any]) -> str:
    """Utility helper to get the assistant message content from the API response."""

    if not isinstance(data, dict):
        return ""

    # Legacy chat-completions format
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content

    # Responses API helpers
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    texts: List[str] = []

    def _extract_from_blocks(blocks: Any) -> None:
        if not isinstance(blocks, list):
            return
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if isinstance(block.get("text"), str):
                txt = block.get("text", "")
            elif isinstance(block.get("value"), str):
                txt = block.get("value", "")
            elif isinstance(block.get("content"), str):
                txt = block.get("content", "")
            else:
                txt = ""
            if not txt and block.get("type") == "output_text" and isinstance(block.get("text"), str):
                txt = block.get("text", "")
            if isinstance(txt, str) and txt.strip():
                texts.append(txt.strip())

    output = data.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, str) and content.strip():
                texts.append(content.strip())
            _extract_from_blocks(content)
            message = item.get("message")
            if isinstance(message, dict):
                msg_content = message.get("content")
                if isinstance(msg_content, str) and msg_content.strip():
                    texts.append(msg_content.strip())
                _extract_from_blocks(msg_content)

    message = data.get("message")
    if isinstance(message, dict):
        msg_content = message.get("content")
        if isinstance(msg_content, str) and msg_content.strip():
            texts.append(msg_content.strip())
        _extract_from_blocks(msg_content)

    if texts:
        return "\n".join(texts).strip()

    return ""


_search_session: Optional[requests.Session] = None


def _get_search_session() -> requests.Session:
    """Return a cached requests session that bypasses proxy settings."""

    global _search_session
    if _search_session is None:
        session = requests.Session()
        # Using proxies in restricted environments (like some hosting providers)
        # may cause 403 responses. We explicitly disable proxy usage to ensure
        # the DuckDuckGo API remains reachable.
        session.trust_env = False
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
            }
        )
        _search_session = session
    return _search_session


def web_search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """Perform a lightweight web search using the DuckDuckGo instant answer API."""

    q = (query or "").strip()
    if not q:
        return []

    try:
        session = _get_search_session()
        response = session.get(
            "https://api.duckduckgo.com/",
            params={"q": q, "format": "json", "no_redirect": "1", "no_html": "1"},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException:
        # Fall back to the default behaviour (which respects environment proxies)
        # in case the direct connection is blocked but a proxy is required.
        try:
            response = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": q, "format": "json", "no_redirect": "1", "no_html": "1"},
                timeout=10,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "application/json",
                },
            )
            response.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise GPTServiceError(f"Search request failed: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        if DEBUG:
            print("Search API returned non-JSON response:", response.text)
        raise GPTServiceError("Invalid response from search provider") from exc

    results: List[Dict[str, str]] = []

    abstract = payload.get("AbstractText") or payload.get("Abstract")
    abstract_url = payload.get("AbstractURL")
    if abstract:
        results.append(
            {
                "title": payload.get("Heading") or q,
                "url": abstract_url or payload.get("AbstractURL") or payload.get("AbstractSource") or "",
                "snippet": abstract,
            }
        )

    def _collect(items):
        for item in items:
            if not isinstance(item, dict):
                continue
            if "Topics" in item:
                _collect(item.get("Topics") or [])
                continue
            text = item.get("Text") or item.get("Result") or ""
            url = item.get("FirstURL") or item.get("URL") or ""
            title = item.get("Title") or text[:80] or q
            if text or url:
                results.append({"title": title, "url": url, "snippet": text})

    _collect(payload.get("Results") or [])
    _collect(payload.get("RelatedTopics") or [])

    trimmed = results[: max_results if max_results and max_results > 0 else 3]
    return trimmed
