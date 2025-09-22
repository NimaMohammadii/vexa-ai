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

    _DEFAULT_BASE_URLS = (
        "https://api.runwayml.com/v1",
        "https://api.dev.runwayml.com/v1",
    )
    _MODEL = os.getenv("RUNWAY_MODEL", "gen4_image_turbo")
    _API_VERSION = os.getenv("RUNWAY_API_VERSION", "2024-11-06")
    _DEFAULT_WIDTH = 1024
    _DEFAULT_HEIGHT = 1024
    _DEFAULT_FORMAT = "webp"
    _REQUEST_TIMEOUT = 30
    _GENERATION_TIMEOUT = 300
    _DEFAULT_POLL_INTERVAL = 3.0

    def __init__(self) -> None:
        token = os.getenv("RUNWAY_API")
        if not token:
            raise ImageGenerationError("کلید دسترسی Runway تنظیم نشده است.")

        self._token = token
        self._base_urls = self._initialise_base_urls()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "vexa-ai-image-service/1.0",
                "X-Runway-Version": self._API_VERSION,
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
            "model": self._MODEL,
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

            status = str(payload.get("status", "")).lower()
            logger.debug(
                "Runway task status",
                extra={"task_id": task_id, "status": status, "payload": payload},
            )

            if status in {"succeeded", "completed", "finished"}:
                assets = self._fetch_assets(task_id)
                if assets:
                    payload.setdefault("assets", assets)
                return payload

            if status in {"failed", "error", "cancelled"}:
                raise ImageGenerationError(self._extract_error(payload))

            time.sleep(poll_delay)

        # مهلت به پایان رسیده است
        raise ImageGenerationError("مهلت دریافت تصویر به پایان رسید.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _initialise_base_urls(self) -> list[str]:
        """Return the list of base URLs to try for the Runway API."""

        configured = os.getenv("RUNWAY_API_URL")
        candidates: tuple[str, ...]
        if configured:
            candidates = (configured,)
        else:
            candidates = self._DEFAULT_BASE_URLS

        normalised: list[str] = []
        for base in candidates:
            base = base.strip()
            if not base:
                continue
            normalised.append(base.rstrip("/"))

        return normalised or list(self._DEFAULT_BASE_URLS)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        timeout: int | float | None = None,
    ) -> requests.Response:
        """Perform an HTTP request and handle connection level errors."""

        last_exception: Exception | None = None
        for index, base_url in enumerate(list(self._base_urls)):
            url = f"{base_url}{path}"
            try:
                response = self._session.request(
                    method,
                    url,
                    json=json,
                    timeout=timeout or self._REQUEST_TIMEOUT,
                )
            except requests.RequestException as exc:  # pragma: no cover - network failure
                last_exception = exc
                logger.warning(
                    "Runway request failed", extra={"url": url, "error": str(exc)}
                )
                continue

            if response.status_code == 404 and index + 1 < len(self._base_urls):
                logger.info(
                    "Runway endpoint not found on base URL, trying fallback",
                    extra={"url": url, "status": response.status_code},
                )
                continue

            if response.status_code >= 400:
                payload = self._safe_json(response, default={})
                message = self._extract_error(payload)
                raise ImageGenerationError(message)

            if index != 0:
                # Cache the working base URL so subsequent calls use it first.
                self._base_urls.pop(index)
                self._base_urls.insert(0, base_url)

            return response

        if last_exception is not None:
            raise ImageGenerationError(
                f"اتصال به Runway ناموفق بود: {last_exception}"
            ) from last_exception

        # All candidates responded with 404. Surface a helpful error.
        raise ImageGenerationError(
            "آدرس سرویس Runway در دسترس نیست. لطفاً مقدار RUNWAY_API_URL را بررسی کن."
        )

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

        candidates = [
            payload.get("error"),
            payload.get("message"),
            payload.get("detail"),
        ]

        # برخی پاسخ‌ها شامل ساختار تو در تو هستند
        details = payload.get("errors")
        if isinstance(details, dict):
            candidates.extend(str(value) for value in details.values())
        elif isinstance(details, list):
            candidates.extend(str(item) for item in details)

        for candidate in candidates:
            text = str(candidate or "").strip()
            if text:
                return text

        return "در پردازش درخواست خطایی رخ داد."
