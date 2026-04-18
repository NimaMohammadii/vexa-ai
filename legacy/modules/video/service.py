"""Runway video generation service."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import requests


logger = logging.getLogger(__name__)


class VideoGenerationError(RuntimeError):
    """Raised when a video cannot be generated."""


class VideoService:
    """Client for interacting with the Runway video generation API."""

    _DEFAULT_BASE_URLS = (
        "https://api.dev.runwayml.com/v1",
        "https://api.runwayml.com/v1",
    )
    _MODEL = os.getenv("RUNWAY_VIDEO_MODEL", "veo-3")
    _API_VERSION = os.getenv("RUNWAY_API_VERSION", "2024-11-06")
    _DEFAULT_RATIO = os.getenv("RUNWAY_VIDEO_RATIO", "16:9")
    _DEFAULT_DURATION = int(os.getenv("RUNWAY_VIDEO_DURATION", "8"))
    _DEFAULT_FORMAT = os.getenv("RUNWAY_VIDEO_FORMAT", "mp4")
    _REQUEST_TIMEOUT = 30
    _GENERATION_TIMEOUT = 1200
    _DEFAULT_POLL_INTERVAL = 5.0

    def __init__(self) -> None:
        token = os.getenv("RUNWAY_API")
        if not token:
            raise VideoGenerationError("کلید دسترسی Runway تنظیم نشده است.")

        self._token = token
        self._base_urls = self._initialise_base_urls()
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "vexa-ai-video-service/1.0",
                "X-Runway-Version": self._API_VERSION,
            }
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_video(self, prompt: str) -> str:
        """Submit a new video generation task and return the task identifier."""

        cleaned = (prompt or "").strip()
        if not cleaned:
            raise VideoGenerationError("متن ویدیو نباید خالی باشد.")

        payload_variants = self._build_payload_variants(cleaned)
        last_error: VideoGenerationError | None = None

        for index, payload in enumerate(payload_variants):
            log_payload = dict(payload)
            if "prompt" in log_payload:
                log_payload["prompt"] = "<omitted>"
            if "promptText" in log_payload:
                log_payload["promptText"] = "<omitted>"

            logger.debug(
                "Submitting video generation task",
                extra={"payload": log_payload, "attempt": index + 1},
            )

            try:
                response = self._request("POST", "/text_to_video", json=payload)
            except VideoGenerationError as exc:
                last_error = exc
                if (
                    index + 1 < len(payload_variants)
                    and "Validation of body failed" in str(exc)
                ):
                    logger.info(
                        "Runway rejected payload, trying fallback schema",
                        extra={"payload_keys": list(payload.keys())},
                    )
                    continue
                raise

            data = self._safe_json(response)
            break
        else:  # pragma: no cover - defensive guard, should not happen
            raise last_error or VideoGenerationError("ارسال درخواست به Runway ناموفق بود.")

        task_id = self._extract_task_id(data) or data.get("id")
        if not task_id:
            logger.error("No task ID in video response", extra={"response": data})
            raise VideoGenerationError("شناسهٔ تسک از پاسخ Runway دریافت نشد.")

        logger.info("Runway video task created", extra={"task_id": task_id})
        return str(task_id)

    def get_video_status(
        self,
        task_id: str,
        *,
        poll_interval: float | None = None,
        timeout: float | None = None,
    ) -> Dict[str, Any]:
        """Poll the task until completion and return the resulting URLs."""

        if not task_id:
            raise VideoGenerationError("شناسهٔ تسک معتبر نیست.")

        poll_delay = poll_interval or self._DEFAULT_POLL_INTERVAL
        deadline = time.time() + float(timeout or self._GENERATION_TIMEOUT)

        while time.time() < deadline:
            response = self._request("GET", f"/tasks/{task_id}")
            payload = self._safe_json(response)

            status = str(payload.get("status", "")).upper()
            logger.debug("Task %s status: %s", task_id, status)

            if status == "SUCCEEDED":
                video_url = self._extract_video_url(payload)
                cover_url = self._extract_cover_url(payload)

                if not video_url:
                    assets = self._fetch_assets(task_id)
                    video_url = self._extract_video_url(assets)
                    cover_url = cover_url or self._extract_cover_url(assets)

                if not video_url:
                    raise VideoGenerationError("خروجی ویدیو در پاسخ موفق پیدا نشد.")

                return {
                    "url": video_url,
                    "cover": cover_url,
                }

            if status in {"FAILED", "CANCELED"}:
                error_msg = (
                    payload.get("failure_reason")
                    or payload.get("error")
                    or "تولید ویدیو ناموفق بود."
                )
                raise VideoGenerationError(f"خطا: {error_msg}")

            time.sleep(poll_delay)

        raise VideoGenerationError("مهلت دریافت ویدیو به پایان رسید.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _initialise_base_urls(self) -> list[str]:
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

    def _build_payload_variants(self, prompt: str) -> list[Dict[str, Any]]:
        base_duration = self._DEFAULT_DURATION
        base_ratio = self._DEFAULT_RATIO
        base_format = self._DEFAULT_FORMAT

        modern_payload: Dict[str, Any] = {
            "model": self._MODEL,
            "prompt": prompt,
            "aspectRatio": base_ratio,
            "duration": base_duration,
            "outputFormat": base_format,
        }

        legacy_payload: Dict[str, Any] = {
            "promptText": prompt,
            "model": self._MODEL,
            "ratio": base_ratio,
            "duration": base_duration,
            "outputFormat": base_format,
        }

        return [modern_payload, legacy_payload]

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        timeout: int | float | None = None,
    ) -> requests.Response:
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
                raise VideoGenerationError(message)

            if index != 0:
                self._base_urls.pop(index)
                self._base_urls.insert(0, base_url)

            return response

        if last_exception is not None:
            raise VideoGenerationError(
                f"اتصال به Runway ناموفق بود: {last_exception}"
            ) from last_exception

        raise VideoGenerationError(
            "آدرس سرویس Runway در دسترس نیست. لطفاً مقدار RUNWAY_API_URL را بررسی کن."
        )

    def _fetch_assets(self, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self._request("GET", f"/tasks/{task_id}/assets")
        except VideoGenerationError:
            logger.debug("No assets available for video task", extra={"task_id": task_id})
            return None

        return self._safe_json(response)

    @staticmethod
    def _safe_json(response: requests.Response, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            parsed = response.json()
        except ValueError:
            if default is not None:
                return default
            raise VideoGenerationError("پاسخ غیرقابل‌پارس از Runway دریافت شد.") from None

        if isinstance(parsed, dict):
            return parsed

        return {"data": parsed}

    @classmethod
    def _extract_error(cls, payload: Dict[str, Any]) -> str:
        primary = cls._find_first_value(
            payload,
            (
                "message",
                "detail",
                "error",
                "description",
                "error_description",
                "error_message",
                "reason",
                "title",
                "msg",
            ),
        )
        text = cls._normalise_text(primary)
        if text:
            return text

        details = payload.get("errors")
        candidates: list[Any] = []
        if isinstance(details, dict):
            candidates.extend(str(value) for value in details.values())
        elif isinstance(details, list):
            candidates.extend(str(item) for item in details)

        for candidate in candidates:
            text = cls._normalise_text(candidate)
            if text:
                return text

        return "در پردازش درخواست خطایی رخ داد."

    @staticmethod
    def _normalise_text(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if value is None:
            return ""
        return str(value).strip()

    @classmethod
    def _extract_task_id(cls, payload: Dict[str, Any]) -> str | None:
        if not isinstance(payload, dict):
            return None

        for key in ("task_id", "id"):
            raw = payload.get(key)
            text = cls._normalise_text(raw)
            if text:
                return text

        task = payload.get("task")
        if isinstance(task, dict):
            return cls._extract_task_id(task)

        return None

    @classmethod
    def _extract_video_url(cls, payload: Any) -> str | None:
        if isinstance(payload, dict):
            for key in (
                "video_url",
                "video",
                "url",
                "download_url",
                "output_url",
                "asset_url",
                "href",
                "source",
            ):
                if key in payload:
                    candidate = cls._extract_video_url(payload[key])
                    if candidate:
                        return candidate

            outputs = payload.get("outputs")
            if isinstance(outputs, list):
                for item in outputs:
                    candidate = cls._extract_video_url(item)
                    if candidate:
                        return candidate

        if isinstance(payload, (list, tuple, set)):
            for item in payload:
                candidate = cls._extract_video_url(item)
                if candidate:
                    return candidate

        if isinstance(payload, str):
            text = payload.strip()
            if any(
                text.startswith(prefix)
                for prefix in ("http://", "https://", "//", "ftp://")
            ) and any(ext in text for ext in (".mp4", ".mov", ".webm")):
                return text

        return None

    @classmethod
    def _extract_cover_url(cls, payload: Any) -> str | None:
        if isinstance(payload, dict):
            for key in ("cover_url", "thumbnail", "preview", "image"):
                if key in payload:
                    candidate = cls._extract_cover_url(payload[key])
                    if candidate:
                        return candidate

        if isinstance(payload, (list, tuple, set)):
            for item in payload:
                candidate = cls._extract_cover_url(item)
                if candidate:
                    return candidate

        if isinstance(payload, str):
            text = payload.strip()
            if any(
                text.startswith(prefix)
                for prefix in ("http://", "https://", "//", "data:image")
            ):
                return text

        return None

    @classmethod
    def _find_first_value(
        cls,
        data: Any,
        keys: tuple[str, ...],
        _visited: Optional[set[int]] = None,
    ) -> Any | None:
        if _visited is None:
            _visited = set()

        obj_id = id(data)
        if obj_id in _visited:
            return None
        _visited.add(obj_id)

        if isinstance(data, dict):
            for key, value in data.items():
                if key in keys:
                    text = cls._normalise_text(value)
                    if text:
                        return value
                result = cls._find_first_value(value, keys, _visited)
                if result is not None:
                    return result

        elif isinstance(data, (list, tuple, set)):
            for item in data:
                result = cls._find_first_value(item, keys, _visited)
                if result is not None:
                    return result

        return None
