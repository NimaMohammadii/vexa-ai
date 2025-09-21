"""Runway image generation service.

This module provides a thin wrapper around the Runway asynchronous task API
and exposes two high level methods that are used by the Telegram handlers:
``generate_image`` for submitting a new prompt and ``get_image_status`` for
polling the task until it is finished.

The implementation keeps the configuration inside the code as requested; the
only external dependency is the ``RUNWAY_API`` environment variable which must
hold the Runway API token.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import requests


logger = logging.getLogger(__name__)


class ImageGenerationError(RuntimeError):
    """Raised when an image cannot be generated."""


class ImageService:
    """Client for interacting with the Runway image generation API."""

    _DEFAULT_BASE_URL = "https://api.dev.runwayml.com/v1"
    _DEFAULT_MODEL = "gen4_image_turbo"
    _DEFAULT_API_VERSION = "2024-11-06"
    _BASE_URL = os.getenv("RUNWAY_API_URL") or "https://api.dev.runwayml.com/v1"
    _MODEL = os.getenv("RUNWAY_MODEL", "gen4_image_turbo")
    _API_VERSION = os.getenv("RUNWAY_API_VERSION", "2024-11-06")
    _DEFAULT_WIDTH = 1024
    _DEFAULT_HEIGHT = 1024
    _DEFAULT_FORMAT = "webp"
    _REQUEST_TIMEOUT = 30
    _GENERATION_TIMEOUT = 300
    _DEFAULT_POLL_INTERVAL = 3.0
    _GENERIC_ERROR_MESSAGE = "در پردازش درخواست خطایی رخ داد."

    def __init__(self) -> None:
        token = os.getenv("RUNWAY_API")
        if not token:
            raise ImageGenerationError("کلید دسترسی Runway تنظیم نشده است.")

        self._token = token
        self._base_url = self._normalise_base_url(
            os.getenv("RUNWAY_API_URL"),
            self._DEFAULT_BASE_URL,
        )
        self._model = self._normalise_str(os.getenv("RUNWAY_MODEL"), self._DEFAULT_MODEL)
        self._api_version = self._normalise_str(
            os.getenv("RUNWAY_API_VERSION"),
            self._DEFAULT_API_VERSION,
        )
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "vexa-ai-image-service/1.0",
                "X-Runway-Version": self._api_version,
            }
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_image(self, prompt: str) -> str:
        """Submit a new generation task and return the task identifier."""

        cleaned = (prompt or "").strip()
        if not cleaned:
            raise ImageGenerationError("متن تصویر نباید خالی باشد.")

        payload: Dict[str, Any] = {
            "model": self._model,
            "input": {
                "prompt": cleaned,
                "width": self._DEFAULT_WIDTH,
                "height": self._DEFAULT_HEIGHT,
                "output_format": self._DEFAULT_FORMAT,
            },
        }

        logger.debug("Submitting generation task to Runway", extra={"payload": payload})
        response = self._request("POST", "/tasks", json=payload)
        data = self._safe_json(response)

        task_id = data.get("id") or data.get("task_id")
        if not task_id:
            raise ImageGenerationError("شناسهٔ تسک از پاسخ Runway دریافت نشد.")

        logger.info("Runway task created", extra={"task_id": task_id})
        return str(task_id)

    def get_image_status(
        self,
        task_id: str,
        *,
        poll_interval: float | None = None,
        timeout: float | None = None,
    ) -> Dict[str, Any]:
        """Poll the given task until it is finished and return the response."""

        if not task_id:
            raise ImageGenerationError("شناسهٔ تسک معتبر نیست.")

        poll_delay = poll_interval or self._DEFAULT_POLL_INTERVAL
        deadline = time.time() + float(timeout or self._GENERATION_TIMEOUT)

        while time.time() < deadline:
            response = self._request("GET", f"/tasks/{task_id}")
            payload = self._safe_json(response)

            status = self._extract_status(payload)
            normalised_status = status.lower()
            logger.debug(
                "Runway task status",
                extra={"task_id": task_id, "status": normalised_status, "payload": payload},
            )

            if self._is_success_state(normalised_status, payload):
                assets = self._fetch_assets(task_id)
                if assets:
                    payload.setdefault("assets", assets)
                return payload

            if self._is_failure_state(normalised_status, payload):
            if status in {"failed", "error", "cancelled"}:
                raise ImageGenerationError(self._format_error(payload))

            time.sleep(poll_delay)

        # مهلت به پایان رسیده است
        raise ImageGenerationError("مهلت دریافت تصویر به پایان رسید.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        timeout: int | float | None = None,
    ) -> requests.Response:
        """Perform an HTTP request and handle connection level errors."""

        url = self._build_url(path)
        try:
            response = self._session.request(
                method,
                url,
                json=json,
                timeout=timeout or self._REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise ImageGenerationError(f"اتصال به Runway ناموفق بود: {exc}") from exc

        if response.status_code >= 400:
            payload = self._safe_json(response, default={})
            message = self._format_error(payload, response)
            raise ImageGenerationError(message)

        return response

    def _fetch_assets(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Try to fetch the assets for a finished task."""

        try:
            response = self._request("GET", f"/tasks/{task_id}/assets")
        except ImageGenerationError:
            # Some endpoints might not expose assets; swallow the error to return
            # the original payload obtained from ``/tasks/{task_id}``.
            logger.debug("No assets available for task", extra={"task_id": task_id})
            return None

        return self._safe_json(response)

    @staticmethod
    def _safe_json(response: requests.Response, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return the JSON payload or the provided default."""

        try:
            parsed = response.json()
        except ValueError:
            if default is not None:
                return default
            raise ImageGenerationError("پاسخ غیرقابل‌پارس از Runway دریافت شد.") from None

        if isinstance(parsed, dict):
            return parsed

        return {"data": parsed}

    @staticmethod
    def _extract_error(payload: Dict[str, Any]) -> str:
        """Extract a user friendly error message from an API response."""

        candidates = []

        error_obj = payload.get("error")
        if isinstance(error_obj, dict):
            for key in ("message", "detail", "error", "code"):
                value = error_obj.get(key)
                if value:
                    candidates.append(value)
        elif error_obj:
            candidates.append(error_obj)

        candidates.extend(
            payload.get(key)
            for key in ("message", "detail", "title", "description")
            if payload.get(key)
        )

        details = payload.get("errors")
        if isinstance(details, dict):
            candidates.extend(details.values())
        elif isinstance(details, list):
            candidates.extend(details)

        for candidate in candidates:
            text = str(candidate or "").strip()
            if text:
                return text

        return ""

    def _format_error(
        self,
        payload: Dict[str, Any] | None,
        response: requests.Response | None = None,
    ) -> str:
        """Return the best available error message for the user."""

        message = self._extract_error(payload or {})
        if message:
            return message

        if response is not None:
            snippet = (response.text or "").strip()
            if snippet:
                snippet = " ".join(snippet.split())
                snippet = snippet[:200]
                return f"HTTP {response.status_code}: {snippet}"
            if response.reason:
                return f"HTTP {response.status_code}: {response.reason}"

        return self._GENERIC_ERROR_MESSAGE

    @staticmethod
    def _normalise_base_url(candidate: Optional[str], default: str) -> str:
        """Normalise the configured base URL and ensure it has no trailing slash."""

        if candidate:
            trimmed = candidate.strip()
            if trimmed:
                return trimmed.rstrip("/")
        return default

    @staticmethod
    def _normalise_str(candidate: Optional[str], default: str) -> str:
        if candidate is None:
            return default

        trimmed = candidate.strip()
        return trimmed or default

    def _build_url(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self._base_url}{path}"

    @staticmethod
    def _extract_status(payload: Dict[str, Any]) -> str:
        """Extract the most relevant status string from a Runway response."""

        visited: set[int] = set()
        stack: list[Any] = [payload]

        while stack:
            current = stack.pop()
            identifier = id(current)
            if identifier in visited:
                continue
            visited.add(identifier)

            if isinstance(current, dict):
                for key, value in current.items():
                    lowered = key.lower()
                    if lowered in {"status", "state", "phase"} and not isinstance(
                        value, (dict, list, tuple, set)
                    ):
                        text = str(value or "").strip()
                        if text:
                            return text

                    if isinstance(value, (dict, list, tuple, set)):
                        stack.append(value)
            elif isinstance(current, (list, tuple, set)):
                stack.extend(current)

        return ""

    @staticmethod
    def _is_success_state(status: str, payload: Dict[str, Any]) -> bool:
        """Return True if the payload represents a finished successful task."""

        if status in {"succeeded", "completed", "finished", "success", "done"}:
            return True

        return ImageService._extract_truthy_flag(
            payload,
            {"done", "is_done", "completed", "is_completed", "success", "succeeded"},
        )

    @staticmethod
    def _is_failure_state(status: str, payload: Dict[str, Any]) -> bool:
        """Return True if the payload indicates a terminal error state."""

        if status in {"failed", "error", "cancelled", "canceled", "rejected"}:
            return True

        return ImageService._extract_truthy_flag(
            payload,
            {"failed", "is_failed", "error", "has_error", "cancelled", "canceled"},
        )

    @staticmethod
    def _extract_truthy_flag(payload: Dict[str, Any], keys: set[str]) -> bool:
        """Look for boolean-esque keys anywhere inside the payload."""

        visited: set[int] = set()
        stack: list[Any] = [payload]

        while stack:
            current = stack.pop()
            identifier = id(current)
            if identifier in visited:
                continue
            visited.add(identifier)

            if isinstance(current, dict):
                for key, value in current.items():
                    lowered = key.lower()
                    if lowered in keys and not isinstance(value, (dict, list, tuple, set)):
                        if isinstance(value, bool):
                            return bool(value)
                        text = str(value or "").strip().lower()
                        if text in {"true", "1", "yes"}:
                            return True
                    elif isinstance(value, (dict, list, tuple, set)):
                        stack.append(value)
            elif isinstance(current, (list, tuple, set)):
                stack.extend(current)

        return False
