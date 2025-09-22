
"""Runway image generation service."""

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

    _BASE_URL = "https://api.dev.runwayml.com/v1"
    _MODEL = "gen4_image"
    _API_VERSION = "2024-06-01"
    _DEFAULT_WIDTH = 512
    _DEFAULT_HEIGHT = 512
    _DEFAULT_FORMAT = "png"
    _REQUEST_TIMEOUT = 30
    _GENERATION_TIMEOUT = 120
    _DEFAULT_POLL_INTERVAL = 3.0

    def __init__(self) -> None:
        token = os.getenv("RUNWAY_API")
        if not token:
            raise ImageGenerationError("کلید دسترسی Runway تنظیم نشده است.")

        self._token = token
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "vexa-ai-image-service/1.0",
            "X-Runway-Version": self._API_VERSION,
        })

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

        try:
            response = self._session.post(
                f"{self._BASE_URL}/tasks",
                json=payload,
                timeout=self._REQUEST_TIMEOUT
            )
            logger.debug("Runway POST response: %s", response.text)
        except Exception as e:
            raise ImageGenerationError(f"درخواست به Runway با خطا مواجه شد: {e}")

        if response.status_code not in (200, 202):
            raise ImageGenerationError(
                f"درخواست با خطا برگشت: {response.status_code} - {response.text}"
            )

        try:
            data = response.json()
        except Exception:
            raise ImageGenerationError("پاسخ JSON معتبر از Runway دریافت نشد.")

        task_id = data.get("id") or data.get("task_id")
        if not task_id:
            raise ImageGenerationError("شناسهٔ تسک از پاسخ Runway دریافت نشد.")
        return str(task_id)

    def get_image_status(self, task_id: str) -> list[dict[str, Any]]:
        """Poll the task until it's complete and return the result assets."""
        start_time = time.time()

        while time.time() - start_time < self._GENERATION_TIMEOUT:
            try:
                response = self._session.get(
                    f"{self._BASE_URL}/tasks/{task_id}",
                    timeout=self._REQUEST_TIMEOUT,
                )
            except Exception as e:
                raise ImageGenerationError(f"خطا در بررسی وضعیت تسک: {e}")

            if response.status_code != 200:
                raise ImageGenerationError(
                    f"خطا در بررسی وضعیت تصویر: {response.status_code} - {response.text}"
                )

            try:
                data = response.json()
            except Exception:
                raise ImageGenerationError("پاسخ وضعیت JSON نامعتبر بود.")

            status = (data.get("status") or "").lower()
            if status in ("succeeded", "completed", "finished"):
                output = data.get("output") or {}
                assets = output.get("assets") or []
                if not assets:
                    raise ImageGenerationError("تصویری در خروجی دریافت نشد.")
                return assets
            elif status in ("failed", "error", "canceled"):
                error_msg = data.get("error", "تولید تصویر ناموفق بود.")
                raise ImageGenerationError(error_msg)

            time.sleep(self._DEFAULT_POLL_INTERVAL)

        raise ImageGenerationError("مهلت تولید تصویر به پایان رسید.")
