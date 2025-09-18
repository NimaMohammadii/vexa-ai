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
    GPT_SYSTEM_PROMPT,
    GPT_TEMPERATURE,
    GPT_TOP_P,
)

_ALLOWED_ROLES = {"system", "user", "assistant"}


class GPTServiceError(RuntimeError):
    """Raised when the upstream GPT provider returns an error."""


def _build_headers() -> Dict[str, str]:
    if not GPT_API_KEY:
        raise GPTServiceError("GPT API key is not configured. Set GPT_API in secrets.")

    header_name = GPT_API_KEY_HEADER or "Authorization"
    header_value = f"{GPT_API_KEY_PREFIX or ''}{GPT_API_KEY}".strip()

    headers = {"Content-Type": "application/json"}
    headers[header_name] = header_value
    return headers


def _normalise_message(message: Dict[str, Any]) -> Dict[str, str]:
    if not isinstance(message, dict):
        raise GPTServiceError("messages must be a list of role/content objects")

    role = str(message.get("role", "assistant")).strip().lower()
    if role not in _ALLOWED_ROLES:
        raise GPTServiceError(f"Unsupported message role: {role}")

    content = message.get("content")
    if not isinstance(content, str) or not content:
        raise GPTServiceError("Each message requires non-empty string content")

    return {"role": role, "content": content}


def build_default_messages(history: Iterable[Dict[str, str]], user_text: str) -> List[Dict[str, str]]:
    """Compose a conversation list starting with the system prompt."""

    messages: List[Dict[str, str]] = [{"role": "system", "content": GPT_SYSTEM_PROMPT}]
    for item in history:
        try:
            messages.append(_normalise_message(item))
        except GPTServiceError:
            if DEBUG:
                print("Ignoring malformed GPT history item:", item)
    messages.append({"role": "user", "content": user_text})
    return messages


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

    choices = data.get("choices") if isinstance(data, dict) else None
    if not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    return content or ""
