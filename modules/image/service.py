import os
import time
from collections import deque
from typing import Any, Iterable

import requests

class ImageGenerationError(Exception):
    pass


SUCCESS_MATCHERS: tuple[str, ...] = ("SUCCEED", "SUCCESS", "COMPLETE", "FINISH")
FAILURE_MATCHERS: tuple[str, ...] = ("FAIL", "ERROR", "CANCEL", "EXPIRE", "DENY", "ABORT")
STATUS_KEYS: tuple[str, ...] = ("status", "state")
OUTPUT_KEYS: tuple[str, ...] = ("output", "outputs", "result", "results")
ERROR_KEYS: tuple[str, ...] = ("error", "message", "detail", "reason")


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


def _interpret_status(value: Any) -> tuple[str | None, str | None]:
    """Return a tuple of (raw_status, status_kind) if we can recognise it."""

    if value is None:
        return None, None

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None, None
        upper = raw.upper()
        for keyword in SUCCESS_MATCHERS:
            if keyword in upper:
                return raw, "success"
        for keyword in FAILURE_MATCHERS:
            if keyword in upper:
                return raw, "failure"
        return raw, None

    if isinstance(value, dict):
        for key in ("value", "status", "state"):
            if key in value:
                raw, kind = _interpret_status(value[key])
                if kind:
                    return raw, kind
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

    return _interpret_status(str(value))


def _extract_first(payload: Any, keys: Iterable[str]) -> Any:
    """Return the first value found for any of the keys within nested payloads."""

    for value in _iter_key_values(payload, keys):
        if value is not None:
            return value
    return None


class ImageService:
    def __init__(self):
        # از محیط خوانده می‌شود
        self.api_key = os.getenv("RUNWAY_API")
        self.api_version = os.getenv("RUNWAY_API_VERSION")
        self.api_url = os.getenv("RUNWAY_API_URL", "https://api.dev.runwayml.com/v1/tasks")
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
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": self.api_version
        }
        return headers

    def generate_image(self, prompt: str):
        if not prompt or not isinstance(prompt, str):
            raise ImageGenerationError("Prompt must be a non-empty string.")

        payload = {
            "model": self.model,
            "input": {
                "prompt": prompt,
                "width": self.image_width,
                "height": self.image_height,
                "output_format": self.image_format
            }
        }

        # ارسال درخواست
        try:
            resp = requests.post(self.api_url, json=payload, headers=self._make_headers(), timeout=30)
        except requests.RequestException as e:
            raise ImageGenerationError(f"Network error during request: {str(e)}")

        # بررسی پاسخ
        if resp.status_code == 202 or resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                raise ImageGenerationError(f"Invalid JSON in response. Status {resp.status_code}, body: {resp.text}")

            task_id = data.get("id")
            if not task_id:
                raise ImageGenerationError(f"Runway response missing task id. Response: {data}")
            return task_id

        elif resp.status_code == 400:
            raise ImageGenerationError(f"Runway API 400: {resp.json()}")

        elif resp.status_code == 404:
            raise ImageGenerationError(f"Runway API 404: {resp.json()} — احتمالاً مدل یا endpoint اشتباه است.")

        else:
            # بقیه کدهای خطا
            raise ImageGenerationError(f"Runway API {resp.status_code}: {resp.text}")

    def get_image_status(self, task_id: str, poll_interval: float = 5.0, timeout: float = 120.0):
        """
        وضعیت تولید تصویر رو چک می‌کنه تا کامل بشه یا خطا بده.
        """
        if not task_id:
            raise ImageGenerationError("task_id is required to check status.")

        end_time = time.time() + timeout
        status_url = f"{self.api_url}/{task_id}"

        while time.time() < end_time:
            try:
                resp = requests.get(status_url, headers=self._make_headers(), timeout=20)
            except requests.RequestException as e:
                raise ImageGenerationError(f"Network error checking status: {str(e)}")

            if resp.status_code == 202:
                time.sleep(poll_interval)
                continue

            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError:
                    raise ImageGenerationError(f"Invalid JSON in status response: {resp.text}")

                status_raw = None
                status_kind = None
                for candidate in _iter_key_values(data, STATUS_KEYS):
                    raw, kind = _interpret_status(candidate)
                    if kind:
                        status_raw, status_kind = raw, kind
                        break

                if not status_kind:
                    time.sleep(poll_interval)
                    continue

                if status_kind == "success":
                    output = (
                        data.get("output")
                        or data.get("outputs")
                        or data.get("result")
                        or data.get("results")
                    )
                    if output is None:
                        output = _extract_first(data, OUTPUT_KEYS)
                    if output is None:
                        raise ImageGenerationError(
                            f"Runway task completed but no output returned. Response: {data}"
                        )
                    return output

                elif status_kind == "failure":
                    error_msg = data.get("error") or _extract_first(data, ERROR_KEYS)
                    if isinstance(error_msg, (dict, list, tuple, set)):
                        error_msg = str(error_msg)
                    if not error_msg:
                        error_msg = status_raw or "Unknown error from Runway during generation."
                    raise ImageGenerationError(f"Runway task failed ({status_raw}): {error_msg}")

                else:
                    time.sleep(poll_interval)
            elif resp.status_code == 404:
                raise ImageGenerationError(f"Status check 404: task {task_id} not found.")
            else:
                raise ImageGenerationError(f"Error checking status: {resp.status_code} – {resp.text}")

        # اگر زمان تمام شد
        raise ImageGenerationError("Image generation timed out.")
