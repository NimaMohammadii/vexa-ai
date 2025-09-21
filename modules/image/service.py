import os
import re
import time
from collections import deque
from typing import Any, Iterable

import requests


class ImageGenerationError(Exception):
    pass


# Tokens are matched as whole tokens (split on non-alnum), not substrings,
# to avoid false positives like UNFINISHED matching FINISH.
SUCCESS_TOKENS: set[str] = {
    "SUCCEEDED",
    "COMPLETED",
    "FINISHED",
    "SUCCESS",
    "OK",
    "DONE",
}
FAILURE_TOKENS: set[str] = {
    "FAILED",
    "ERROR",
    "CANCELLED",
    "CANCELED",
    "EXPIRED",
    "DENIED",
    "ABORTED",
    "REJECTED",
}

STATUS_KEYS: tuple[str, ...] = ("status", "state")
OUTPUT_KEYS: tuple[str, ...] = ("output", "outputs", "result", "results")
ERROR_KEYS: tuple[str, ...] = ("error", "message", "detail", "reason")
ASSET_URL_KEYS: tuple[str, ...] = ("uri", "url", "src", "href", "signed_url")


def _iter_key_values(payload: Any, keys: Iterable[str]) -> Iterable[Any]:
    """Yield values for any of the provided keys within nested payloads."""

    if not isinstance(keys, set):
        keys = set(keys)

    visited: set[int] = set()
    queue: deque[Any] = deque([payload])

    while queue:
        current = queue.popleft()
        obj_id = id(current)
        if obj_id in visited:
            continue
        visited.add(obj_id)

        if isinstance(current, dict):
            for key, value in current.items():
                if key in keys:
                    yield value
                queue.append(value)
        elif isinstance(current, (list, tuple, set)):
            queue.extend(current)


def _normalize_tokens(raw: str) -> set[str]:
    # Split by any non-alphanumeric char to extract tokens like TASK, STATUS, SUCCEEDED
    return set(filter(None, re.split(r"[^A-Z0-9]+", raw.upper())))


def _interpret_status(value: Any) -> tuple[str | None, str | None]:
    """Return a tuple of (raw_status, status_kind) if we can recognise it."""
    if value is None:
        return None, None

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None, None
        tokens = _normalize_tokens(raw)
        if tokens & SUCCESS_TOKENS:
            return raw, "success"
        if tokens & FAILURE_TOKENS:
            return raw, "failure"
        return raw, None

    if isinstance(value, dict):
        # Prefer common keys first
        for key in ("value", "status", "state"):
            if key in value:
                raw, kind = _interpret_status(value[key])
                if kind:
                    return raw, kind
        # Fallback: search nested
        for nested in value.values():
            raw, kind = _interpret_status(nested)
            if kind:
                return raw, kind
        return None, None

    if isinstance(value, (list, tuple, set)):
        for item in value:
            raw, kind = _interpret_status(item)
            if kind:
                return raw, kind
        return None, None

    # Coerce other types to string
    return _interpret_status(str(value))


def _extract_first(payload: Any, keys: Iterable[str]) -> Any:
    """Return the first value found for any of the keys within nested payloads."""
    for value in _iter_key_values(payload, keys):
        if value is not None:
            return value
    return None


def _extract_first_url(payload: Any) -> str | None:
    """Find the first URL-like string (uri/url/src/href) anywhere in nested payload."""
    for v in _iter_key_values(payload, ASSET_URL_KEYS):
        if isinstance(v, str):
            s = v.strip()
            if s.startswith(("http://", "https://", "data:")):
                return s
    # As a last resort, look for any http(s) substring in stringified payloads
    if isinstance(payload, str):
        m = re.search(r"https?://[^\s\"'>)]+", payload)
        return m.group(0) if m else None
    return None


class ImageService:
    def __init__(self):
        # از محیط خوانده می‌شود
        self.api_key = os.getenv("RUNWAY_API")
        self.api_version = os.getenv("RUNWAY_API_VERSION")
        # پیش‌فرض به endpoint اصلی تغییر داده شد (قابل override)
        self.api_url = os.getenv("RUNWAY_API_URL", "https://api.runwayml.com/v1/tasks")
        self.model = os.getenv("RUNWAY_MODEL", "gen4_image")
        self.image_width = int(os.getenv("RUNWAY_IMAGE_WIDTH", "512"))
        self.image_height = int(os.getenv("RUNWAY_IMAGE_HEIGHT", "512"))
        self.image_format = os.getenv("RUNWAY_IMAGE_FORMAT", "png")

        # بررسی مقدماتی
        if not self.api_key:
            raise ImageGenerationError("RUNWAY_API key is missing.")
        if not self.api_version:
            raise ImageGenerationError("RUNWAY_API_VERSION is missing.")
        if not self.model:
            raise ImageGenerationError("RUNWAY_MODEL is missing.")

    def _make_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": self.api_version,
        }

    def generate_image(self, prompt: str) -> str:
        """ایجاد تسک تولید تصویر و برگرداندن task_id"""
        if not prompt or not isinstance(prompt, str):
            raise ImageGenerationError("Prompt must be a non-empty string.")

        payload = {
            "model": self.model,
            "input": {
                "prompt": prompt,
                "width": self.image_width,
                "height": self.image_height,
                "output_format": self.image_format,
            },
        }

        # ارسال درخواست
        try:
            resp = requests.post(self.api_url, json=payload, headers=self._make_headers(), timeout=30)
        except requests.RequestException as e:
            raise ImageGenerationError(f"Network error during request: {str(e)}")

        # بررسی پاسخ
        if resp.status_code in (200, 202):
            try:
                data = resp.json()
            except ValueError:
                raise ImageGenerationError(f"Invalid JSON in response. Status {resp.status_code}, body: {resp.text}")

            task_id = data.get("id")
            if not task_id:
                raise ImageGenerationError(f"Runway response missing task id. Response: {data}")
            return task_id

        elif resp.status_code == 400:
            try:
                detail = resp.json()
            except ValueError:
                detail = resp.text
            raise ImageGenerationError(f"Runway API 400: {detail}")

        elif resp.status_code == 404:
            try:
                detail = resp.json()
            except ValueError:
                detail = resp.text
            raise ImageGenerationError(f"Runway API 404: {detail} — احتمالاً مدل یا endpoint اشتباه است.")

        else:
            # بقیه کدهای خطا
            raise ImageGenerationError(f"Runway API {resp.status_code}: {resp.text}")

    def get_image_status(self, task_id: str, poll_interval: float = 5.0, timeout: float = 120.0):
        """
        وضعیت تولید تصویر رو چک می‌کنه تا کامل بشه یا خطا بده.
        خروجی: URL تصویر در صورت موجود بودن؛ در غیر این صورت اولین مقدار از output/outputs/result/results.
        """
        if not task_id:
            raise ImageGenerationError("task_id is required to check status.")

        end_time = time.time() + timeout
        status_url = f"{self.api_url.rstrip('/')}/{task_id}"

        while time.time() < end_time:
            try:
                resp = requests.get(status_url, headers=self._make_headers(), timeout=20)
            except requests.RequestException as e:
                raise ImageGenerationError(f"Network error checking status: {str(e)}")

            if resp.status_code == 202:
                # هنوز در حال پردازش
                time.sleep(poll_interval)
                continue

            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError:
                    raise ImageGenerationError(f"Invalid JSON in status response: {resp.text}")

                # تشخیص وضعیت از هرجای payload به صورت امن (token-based)
                status_raw = None
                status_kind = None
                for candidate in _iter_key_values(data, STATUS_KEYS):
                    raw, kind = _interpret_status(candidate)
                    if kind:
                        status_raw, status_kind = raw, kind
                        break

                # اگر شکست بوده، پیام خطا رو استخراج و raise کنیم
                if status_kind == "failure":
                    error_msg = _extract_first(data, ERROR_KEYS)
                    if isinstance(error_msg, (dict, list, tuple, set)):
                        error_msg = str(error_msg)
                    if not error_msg:
                        error_msg = status_raw or "Unknown error from Runway during generation."
                    raise ImageGenerationError(f"Runway task failed ({status_raw}): {error_msg}")

                # اگر موفقیت تشخیص داده شد، تلاش برای استخراج URL
                if status_kind == "success":
                    # 1) سعی می‌کنیم از هر جای payload یک URL معتبر پیدا کنیم
                    url = _extract_first_url(data)
                    if url:
                        return url

                    # 2) در غیر این صورت، خروجی‌های متعارف را برگردانیم
                    output = _extract_first(data, OUTPUT_KEYS)
                    if output is not None:
                        if isinstance(output, str):
                            return output
                        nested_url = _extract_first_url(output)
                        if nested_url:
                            return nested_url
                        return output  # در نهایت، خود خروجی را برگردان

                    # اگر هنوز خروجی‌ای نیست، کمی صبر کنیم
                    time.sleep(poll_interval)
                    continue

                # سازگاری با APIهایی که صراحتا status == SUCCEEDED دارند
                status_value = data.get("status")
                if status_value:
                    status_tokens = _normalize_tokens(str(status_value))
                    if status_tokens & SUCCESS_TOKENS:
                        url = _extract_first_url(data)
                        if url:
                            return url
                        output = _extract_first(data, OUTPUT_KEYS)
                        if output is not None:
                            if isinstance(output, str):
                                return output
                            nested_url = _extract_first_url(output)
                            if nested_url:
                                return nested_url
                            return output
                        time.sleep(poll_interval)
                        continue
                    if status_tokens & FAILURE_TOKENS:
                        error_msg = _extract_first(data, ERROR_KEYS) or str(status_value)
                        raise ImageGenerationError(f"Runway task failed: {error_msg}")

                # در غیر این صورت هنوز در حال پردازش است
                time.sleep(poll_interval)
                continue

            if resp.status_code == 404:
                raise ImageGenerationError(f"Status check 404: task {task_id} not found.")

            # سایر خطاهای HTTP
            raise ImageGenerationError(f"Error checking status: {resp.status_code} – {resp.text}")

        # اگر زمان تمام شد
        raise ImageGenerationError("Image generation timed out.")
