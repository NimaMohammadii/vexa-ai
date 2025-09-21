"""Runway image generation service client."""

from __future__ import annotations

import base64
import re
import time
from typing import Any, Iterable

import requests

from config import DEBUG, RUNWAY_API_KEY
from .settings import POLL_INTERVAL, POLL_TIMEOUT

API_URL = "https://api.runwayml.com/v1/tasks"


class ImageGenerationError(RuntimeError):
    """Raised when the Runway image generation fails."""


def is_configured() -> bool:
    return bool(RUNWAY_API_KEY)


def generate_image(prompt: str) -> bytes:
    if not prompt.strip():
        raise ImageGenerationError("Prompt is empty")
    if not is_configured():
        raise ImageGenerationError("Runway API key is missing")

    payload = {
        "model": "gen4_image",
        "input": {
            "prompt": prompt,
            "negative_prompt": "",
            "width": 1280,
            "height": 720,
            "output_format": "png",
        },
    }

    response = _request("POST", API_URL, json=payload)
    if DEBUG:
        print(f"[Runway] task created: {response.get('id')} status={response.get('status')}", flush=True)

    image_bytes = _extract_image_bytes(response)
    if image_bytes:
        return image_bytes

    task_id = response.get("id")
    if not task_id:
        raise ImageGenerationError("Runway response missing task id")

    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        poll_data = _request("GET", f"{API_URL}/{task_id}")
        status = _normalise_status(poll_data.get("status") or poll_data.get("state"))
        if DEBUG:
            print(f"[Runway] poll {task_id}: status={status}", flush=True)
        if status in {"SUCCEEDED", "COMPLETED", "FINISHED"}:
            image_bytes = _extract_image_bytes(poll_data)
            if image_bytes:
                return image_bytes
            raise ImageGenerationError("Runway task completed without image data")
        if status in {"FAILED", "CANCELED", "CANCELLED", "ERROR"}:
            message = _extract_message(poll_data)
            raise ImageGenerationError(f"Runway task failed: {message}")

    raise ImageGenerationError("Runway image generation timed out")


def _normalise_status(status: Any) -> str:
    if not isinstance(status, str):
        return ""
    return status.strip().upper()


def _extract_message(data: dict[str, Any]) -> str:
    for key in ("message", "error", "detail", "details"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return str(data)


def _request(method: str, url: str, **kwargs) -> dict[str, Any]:
    headers = kwargs.pop("headers", {})
    headers.setdefault("Authorization", f"Bearer {RUNWAY_API_KEY}")
    headers.setdefault("Content-Type", "application/json")
    kwargs.setdefault("timeout", 30)
    try:
        response = requests.request(method, url, headers=headers, **kwargs)
    except requests.RequestException as exc:
        raise ImageGenerationError(f"Runway API network error: {exc}") from exc

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400:
        message = _extract_message(payload) if isinstance(payload, dict) else response.text
        raise ImageGenerationError(f"Runway API error ({response.status_code}): {message}")

    if not isinstance(payload, dict):
        raise ImageGenerationError("Unexpected Runway API response")

    return payload


_BASE64_RE = re.compile(r"^data:image/[^;]+;base64,(?P<data>[A-Za-z0-9+/=]+)$")


def _extract_image_bytes(payload: dict[str, Any]) -> bytes | None:
    for url in _iter_urls(payload):
        try:
            return _download(url)
        except ImageGenerationError:
            continue

    b64 = _find_base64(payload)
    if b64:
        try:
            return base64.b64decode(b64)
        except (ValueError, TypeError) as exc:
            if DEBUG:
                print(f"[Runway] failed to decode base64 image: {exc}", flush=True)
    return None


def _iter_urls(node: Any) -> Iterable[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                yield from _iter_urls(value)
            elif isinstance(value, str):
                if value.startswith("http://") or value.startswith("https://"):
                    yield value
    elif isinstance(node, list):
        for item in node:
            yield from _iter_urls(item)


def _find_base64(node: Any) -> str | None:
    if isinstance(node, dict):
        for value in node.values():
            result = _find_base64(value)
            if result:
                return result
    elif isinstance(node, list):
        for item in node:
            result = _find_base64(item)
            if result:
                return result
    elif isinstance(node, str):
        match = _BASE64_RE.match(node.strip())
        if match:
            return match.group("data")
    return None


def _download(url: str) -> bytes:
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.content
    except requests.RequestException as exc:
        raise ImageGenerationError(f"Failed to download image: {exc}") from exc
