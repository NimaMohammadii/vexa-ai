import os
import re
import time
import logging
from collections import deque
from typing import Any, Iterable

import requests


# تنظیم logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# حالت دیباگ
DEBUG_MODE = os.getenv("RUNWAY_DEBUG", "false").lower() == "true"
if DEBUG_MODE:
    logger.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG)


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
        logger.info("🚀 آغاز راه‌اندازی ImageService")
        
        # از محیط خوانده می‌شود
        self.api_key = os.getenv("RUNWAY_API")
        self.api_version = os.getenv("RUNWAY_API_VERSION")
        # پیش‌فرض به endpoint اصلی تغییر داده شد (قابل override)
        self.api_url = os.getenv("RUNWAY_API_URL", "https://api.runwayml.com/v1/tasks")
        self.model = os.getenv("RUNWAY_MODEL", "gen4_image")
        self.image_width = int(os.getenv("RUNWAY_IMAGE_WIDTH", "512"))
        self.image_height = int(os.getenv("RUNWAY_IMAGE_HEIGHT", "512"))
        self.image_format = os.getenv("RUNWAY_IMAGE_FORMAT", "png")

        # لاگ تنظیمات (بدون API key)
        logger.info(f"📋 تنظیمات ImageService:")
        logger.info(f"   API URL: {self.api_url}")
        logger.info(f"   API Version: {self.api_version}")
        logger.info(f"   Model: {self.model}")
        logger.info(f"   Image Size: {self.image_width}x{self.image_height}")
        logger.info(f"   Format: {self.image_format}")
        logger.info(f"   API Key present: {'✅' if self.api_key else '❌'}")

        # بررسی مقدماتی
        if not self.api_key:
            logger.error("❌ RUNWAY_API key is missing!")
            raise ImageGenerationError("RUNWAY_API key is missing.")
        if not self.api_version:
            logger.error("❌ RUNWAY_API_VERSION is missing!")
            raise ImageGenerationError("RUNWAY_API_VERSION is missing.")
        if not self.model:
            logger.error("❌ RUNWAY_MODEL is missing!")
            raise ImageGenerationError("RUNWAY_MODEL is missing.")
            
        logger.info("✅ ImageService راه‌اندازی شد")

    def _make_headers(self):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": self.api_version,
        }
        
        # لاگ headers (بدون API key)
        safe_headers = headers.copy()
        if "Authorization" in safe_headers:
            safe_headers["Authorization"] = "Bearer [HIDDEN]"
        logger.debug(f"🔐 Headers: {safe_headers}")
        
        return headers

    def _log_request(self, method: str, url: str, payload: Any = None):
        """لاگ کردن درخواست به صورت امن"""
        logger.info(f"📤 {method} درخواست به: {url}")
        if payload and DEBUG_MODE:
            logger.debug(f"📋 Payload: {payload}")

    def _log_response(self, response: requests.Response):
        """لاگ کردن پاسخ"""
        logger.info(f"📥 پاسخ: {response.status_code}")
        if DEBUG_MODE:
            try:
                response_data = response.json() if response.content else {}
                logger.debug(f"📋 Response body: {response_data}")
            except:
                logger.debug(f"📋 Response text: {response.text[:500]}...")

    def _fetch_endpoint_json(self, url: str) -> Any | None:
        logger.debug(f"🔍 تلاش برای دریافت JSON از: {url}")
        try:
            r = requests.get(url, headers=self._make_headers(), timeout=20)
            self._log_response(r)
        except requests.RequestException as e:
            logger.warning(f"⚠️ خطا در درخواست به {url}: {e}")
            return None
        if r.status_code != 200:
            logger.warning(f"⚠️ پاسخ غیرموفق از {url}: {r.status_code}")
            return None
        try:
            data = r.json()
            logger.debug(f"✅ JSON دریافت شد از {url}")
            return data
        except ValueError as e:
            logger.warning(f"⚠️ خطا در پارس JSON از {url}: {e}")
            return None

    def _fetch_assets_like(self, task_id: str) -> Any | None:
        """Try multiple known endpoints where Runway may expose artifacts."""
        logger.debug(f"🔍 جستجوی assets برای task {task_id}")
        base = self.api_url.rstrip("/")
        candidates = (
            f"{base}/{task_id}/assets",
            f"{base}/{task_id}/artifacts",
            f"{base}/{task_id}/output",
        )
        for u in candidates:
            logger.debug(f"   تلاش: {u}")
            data = self._fetch_endpoint_json(u)
            if data is not None:
                logger.info(f"✅ Assets پیدا شد در: {u}")
                return data
        logger.warning(f"⚠️ هیچ assets برای task {task_id} پیدا نشد")
        return None

    def generate_image(self, prompt: str) -> str:
        """ایجاد تسک تولید تصویر و برگرداندن task_id"""
        logger.info(f"🎨 شروع تولید تصویر با prompt: '{prompt[:50]}...'")
        
        if not prompt or not isinstance(prompt, str):
            logger.error("❌ Prompt نامعتبر است")
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

        self._log_request("POST", self.api_url, payload)

        # ارسال درخواست
        try:
            resp = requests.post(self.api_url, json=payload, headers=self._make_headers(), timeout=30)
            self._log_response(resp)
        except requests.RequestException as e:
            logger.error(f"❌ خطای شبکه: {e}")
            raise ImageGenerationError(f"Network error during request: {str(e)}")

        # بررسی پاسخ (۲۰۱ را هم قبول کن)
        if resp.status_code in (200, 201, 202):
            try:
                data = resp.json()
                logger.debug(f"✅ پاسخ موفق: {data}")
            except ValueError:
                logger.error(f"❌ JSON نامعتبر در پاسخ: {resp.text}")
                raise ImageGenerationError(f"Invalid JSON in response. Status {resp.status_code}, body: {resp.text}")

            task_id = data.get("id")
            if not task_id:
                logger.error(f"❌ task_id در پاسخ وجود ندارد: {data}")
                raise ImageGenerationError(f"Runway response missing task id. Response: {data}")
            
            logger.info(f"✅ تسک ایجاد شد با ID: {task_id}")
            return task_id

        elif resp.status_code == 400:
            try:
                detail = resp.json()
                logger.error(f"❌ خطای 400: {detail}")
            except ValueError:
                detail = resp.text
                logger.error(f"❌ خطای 400 (متن): {detail}")
            raise ImageGenerationError(f"Runway API 400: {detail}")

        elif resp.status_code == 401:
            logger.error("❌ خطای احراز هویت (401) - API key اشتباه است")
            raise ImageGenerationError("Authentication failed - check your RUNWAY_API key")

        elif resp.status_code == 404:
            try:
                detail = resp.json()
            except ValueError:
                detail = resp.text
            logger.error(f"❌ خطای 404: {detail}")
            raise ImageGenerationError(f"Runway API 404: {detail} — احتمالاً مدل یا endpoint اشتباه است.")

        else:
            # بقیه کدهای خطا
            logger.error(f"❌ خطای HTTP {resp.status_code}: {resp.text}")
            raise ImageGenerationError(f"Runway API {resp.status_code}: {resp.text}")

    def get_image_status(self, task_id: str, poll_interval: float = 5.0, timeout: float = 120.0):
        """
        وضعیت تولید تصویر رو چک می‌کنه تا کامل بشه یا خطا بده.
        """
        logger.info(f"⏳ چک کردن وضعیت task {task_id}")
        
        if not task_id:
            logger.error("❌ task_id خالی است")
            raise ImageGenerationError("task_id is required to check status.")

        end_time = time.time() + timeout
        status_url = f"{self.api_url.rstrip('/')}/{task_id}"
        poll_count = 0

        while time.time() < end_time:
            poll_count += 1
            logger.debug(f"🔄 Polling شماره {poll_count} برای task {task_id}")
            
            try:
                resp = requests.get(status_url, headers=self._make_headers(), timeout=20)
                self._log_response(resp)
            except requests.RequestException as e:
                logger.error(f"❌ خطای شبکه در چک وضعیت: {e}")
                raise ImageGenerationError(f"Network error checking status: {str(e)}")

            if resp.status_code == 202:
                # هنوز در حال پردازش
                logger.debug(f"⏳ Task در حال پردازش (202) - انتظار {poll_interval} ثانیه")
                time.sleep(poll_interval)
                continue

            if resp.status_code == 200:
                try:
                    data = resp.json()
                    logger.debug(f"📋 داده‌های وضعیت: {data}")
                except ValueError:
                    logger.error(f"❌ JSON نامعتبر در پاسخ وضعیت: {resp.text}")
                    raise ImageGenerationError(f"Invalid JSON in status response: {resp.text}")

                # تشخیص وضعیت از هرجای payload به صورت امن (token-based)
                status_raw = None
                status_kind = None
                for candidate in _iter_key_values(data, STATUS_KEYS):
                    raw, kind = _interpret_status(candidate)
                    if kind:
                        status_raw, status_kind = raw, kind
                        logger.info(f"📊 وضعیت تشخیص داده شد: {raw} ({kind})")
                        break

                # اگر شکست بوده، پیام خطا رو استخراج و raise کنیم
                if status_kind == "failure":
                    error_msg = _extract_first(data, ERROR_KEYS)
                    if isinstance(error_msg, (dict, list, tuple, set)):
                        error_msg = str(error_msg)
                    if not error_msg:
                        error_msg = status_raw or "Unknown error from Runway during generation."
                    logger.error(f"❌ Task شکست خورد: {error_msg}")
                    raise ImageGenerationError(f"Runway task failed ({status_raw}): {error_msg}")

                # اگر موفقیت تشخیص داده شد، خروجی/URL یا assets را برگردان
                if status_kind == "success":
                    logger.info("✅ Task موفقیت‌آمیز بود - جستجوی خروجی")
                    
                    # 1) جستجوی URL در خود payload
                    url = _extract_first_url(data)
                    if url:
                        logger.info(f"🖼️ URL تصویر پیدا شد: {url}")
                        return url

                    # 2) تلاش برای خروجی‌های متعارف
                    output = _extract_first(data, OUTPUT_KEYS)
                    if output is not None:
                        logger.debug(f"📤 خروجی پیدا شد: {type(output)}")
                        if isinstance(output, str):
                            # ممکن است خودش URL یا data:image باشد
                            logger.info(f"📄 خروجی متنی: {output}")
                            return output
                        nested_url = _extract_first_url(output)
                        if nested_url:
                            logger.info(f"🖼️ URL در خروجی پیدا شد: {nested_url}")
                            return nested_url
                        # اگر ساختار تو در تو ولی بدون URL بود، کل خروجی را به لایه بالاتر بده
                        logger.debug("📦 خروجی پیچیده - برگرداندن به لایه بالاتر")
                        return output

                    # 3) در صورت نبود خروجی در payload، از endpoints جانبی بگیر
                    logger.debug("🔍 جستجو در endpoints جانبی")
                    side = self._fetch_assets_like(task_id)
                    if side is not None:
                        side_url = _extract_first_url(side)
                        if side_url:
                            logger.info(f"🖼️ URL در assets پیدا شد: {side_url}")
                            return side_url
                        logger.debug("📦 Assets پیچیده - برگرداندن به لایه بالاتر")
                        return side  # اجازه بده لایه بالاتر خودش استخراج کند

                    # اگر هیچ کدام نبود، همین data را بده تا گیر نکند
                    logger.warning("⚠️ هیچ خروجی واضحی پیدا نشد - برگرداندن کل payload")
                    return data

                # سازگاری با APIهایی که صراحتا status == SUCCEEDED دارند
                status_value = data.get("status")
                if status_value:
                    status_tokens = _normalize_tokens(str(status_value))
                    logger.debug(f"🔍 بررسی status tokens: {status_tokens}")
                    
                    if status_tokens & SUCCESS_TOKENS:
                        logger.info(f"✅ وضعیت موفق تشخیص داده شد: {status_value}")
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
                        side = self._fetch_assets_like(task_id)
                        if side is not None:
                            side_url = _extract_first_url(side)
                            if side_url:
                                return side_url
                            return side
                        return data  # موفق شده اما خروجی پیدا نشد، payload را برگردان

                    if status_tokens & FAILURE_TOKENS:
                        error_msg = _extract_first(data, ERROR_KEYS) or str(status_value)
                        logger.error(f"❌ Task شکست خورد (از status): {error_msg}")
                        raise ImageGenerationError(f"Runway task failed: {error_msg}")

                # در غیر این صورت هنوز در حال پردازش است
                logger.debug("⏳ هنوز در حال پردازش - ادامه polling")
                time.sleep(poll_interval)
                continue

            if resp.status_code == 404:
                logger.error(f"❌ Task {task_id} پیدا نشد (404)")
                raise ImageGenerationError(f"Status check 404: task {task_id} not found.")

            # سایر خطاهای HTTP
            logger.error(f"❌ خطا در چک وضعیت: {resp.status_code} - {resp.text}")
            raise ImageGenerationError(f"Error checking status: {resp.status_code} – {resp.text}")

        # اگر زمان تمام شد
        logger.error(f"⏰ Timeout بعد از {poll_count} تلاش")
        raise ImageGenerationError("Image generation timed out.")
