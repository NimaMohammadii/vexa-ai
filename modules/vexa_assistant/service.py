"""Service helpers for the dedicated Vexa Assistant powered by OpenAI."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests

from config import (
    DEBUG,
    GPT_API_KEY_HEADER,
    GPT_API_KEY_PREFIX,
    GPT_API_TIMEOUT,
    VEXA_ASSISTANT_API_KEY,
    VEXA_ASSISTANT_API_URL,
    VEXA_ASSISTANT_ID,
    VEXA_ASSISTANT_MODEL,
)
from modules.gpt.service import extract_message_text, resolve_gpt_api_key


class VexaAssistantError(RuntimeError):
    """Raised when the Vexa Assistant API returns an error."""


__all__ = [
    "VexaAssistantError",
    "ensure_ready",
    "prepare_messages",
    "request_response",
]


_cached_api_key: Optional[str] = None


def resolve_api_key(force_refresh: bool = False) -> str:
    """Return the API key used for the Vexa Assistant."""

    global _cached_api_key

    if not force_refresh and _cached_api_key is not None:
        return _cached_api_key

    if VEXA_ASSISTANT_API_KEY:
        _cached_api_key = VEXA_ASSISTANT_API_KEY
        return _cached_api_key

    key = resolve_gpt_api_key(force_refresh=force_refresh)
    _cached_api_key = key
    return key


def ensure_ready(force_refresh: bool = False) -> tuple[bool, Optional[str]]:
    """Check whether the assistant is configured correctly."""

    key = resolve_api_key(force_refresh=force_refresh)
    if not key:
        return False, "missing_api_key"
    if not VEXA_ASSISTANT_ID:
        return False, "missing_assistant_id"
    return True, None


def prepare_messages(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Transform a conversation history into a payload for the Responses API."""

    normalised: List[Dict[str, Any]] = []
    for item in history:
        role = str(item.get("role", "assistant") or "assistant").strip() or "assistant"
        content = item.get("content", "")
        normalised.append({"role": role, "content": content})

    payload: Dict[str, Any] = {
        "model": (VEXA_ASSISTANT_MODEL or "gpt-4o-mini").strip() or "gpt-4o-mini",
        "input": normalised,
    }

    if VEXA_ASSISTANT_ID:
        payload["assistant_id"] = VEXA_ASSISTANT_ID

    return payload


def request_response(history: List[Dict[str, Any]]) -> str:
    """Send the conversation to the Vexa Assistant and return the answer text."""

    ok, error = ensure_ready()
    if not ok:
        raise VexaAssistantError(error or "not_configured")

    payload = prepare_messages(history)
    api_key = resolve_api_key()

    headers = {
        "Content-Type": "application/json",
        GPT_API_KEY_HEADER: f"{(GPT_API_KEY_PREFIX or '')}{api_key}",
        "OpenAI-Beta": "assistants=v2",
    }

    try:
        response = requests.post(
            VEXA_ASSISTANT_API_URL,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            timeout=GPT_API_TIMEOUT,
        )
    except requests.RequestException as exc:  # pragma: no cover - network errors
        raise VexaAssistantError(f"network_error: {exc}") from exc

    text = response.text
    try:
        data = response.json()
    except ValueError as exc:  # pragma: no cover - invalid responses
        if DEBUG:
            print("Vexa Assistant returned non-JSON response:", text)
        raise VexaAssistantError("invalid_response") from exc

    if response.status_code >= 400:
        message: Optional[str] = None
        if isinstance(data, dict):
            message = data.get("error") or data.get("message")
            if isinstance(message, dict):
                message = message.get("message") or message.get("code")
        raise VexaAssistantError(message or response.reason or "request_failed")

    answer = (extract_message_text(data) or "").strip()
    return answer
