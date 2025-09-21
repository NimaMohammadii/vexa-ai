import os
import re
import time
import logging
from typing import Any, Optional, Dict
import requests


# تنظیم logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# حالت دیباگ
DEBUG_MODE = os.getenv("RUNWAY_DEBUG", "false").lower() == "true"
if DEBUG_MODE:
    logger.setLevel(logging.DEBUG)


class ImageGenerationError(Exception):
    pass


class ImageService:
    def __init__(self):
        logger.info("🚀 راه‌اندازی ImageService")
        
        # تنظیمات API
        self.api_key = os.getenv("RUNWAY_API")
        self.api_version = os.getenv("RUNWAY_API_VERSION", "2024-09-13")
        self.api_url = os.getenv("RUNWAY_API_URL", "https://api.runwayml.com/v1/image/generate")
        self.model = os.getenv("RUNWAY_MODEL", "runway-ml/runway-stable-diffusion-v1-5")
        
        # تنظیمات تصویر
        self.image_width = int(os.getenv("RUNWAY_IMAGE_WIDTH", "512"))
        self.image_height = int(os.getenv("RUNWAY_IMAGE_HEIGHT", "512"))
        self.image_format = os.getenv("RUNWAY_IMAGE_FORMAT", "WEBP")
        
        # تنظیمات timeout
        self.request_timeout = int(os.getenv("RUNWAY_REQUEST_TIMEOUT", "30"))
        self.generation_timeout = int(os.getenv("RUNWAY_GENERATION_TIMEOUT", "300"))
        self.poll_interval = float(os.getenv("RUNWAY_POLL_INTERVAL", "3.0"))

        # لاگ تنظیمات
        logger.info(f"📋 تنظیمات:")
        logger.info(f"   API URL: {self.api_url}")
        logger.info(f"   API Version: {self.api_version}")
        logger.info(f"   Model: {self.model}")
        logger.info(f"   Image Size: {self.image_width}x{self.image_height}")
        logger.info(f"   Format: {self.image_format}")
        logger.info(f"   API Key: {'✅ موجود' if self.api_key else '❌ ناموجود'}")

        # بررسی‌های لازم
        if not self.api_key:
            raise ImageGenerationError("❌ RUNWAY_API key موجود نیست!")

    def _get_headers(self) -> Dict[str, str]:
        """ساخت headers برای درخواست"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        if self.api_version:
            headers["X-Runway-Version"] = self.api_version
            
        return headers

    def _log_request(self, method: str, url: str, data: Any = None):
        """لاگ درخواست"""
        logger.info(f"📤 {method} به {url}")
        if DEBUG_MODE and data:
            # حذف اطلاعات حساس
            safe_data = str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
            logger.debug(f"📋 داده‌های ارسالی: {safe_data}")

    def _log_response(self, response: requests.Response):
        """لاگ پاسخ"""
        logger.info(f"📥 پاسخ: {response.status_code}")
        
        if DEBUG_MODE:
            try:
                # نمایش محتوای پاسخ
                content_preview = response.text[:500] + "..." if len(response.text) > 500 else response.text
                logger.debug(f"📄 محتوای پاسخ: {content_preview}")
            except:
                logger.debug("📄 نمی‌توان محتوای پاسخ را نمایش داد")

    def generate_image_sync(self, prompt: str) -> str:
        """
        تولید تصویر به صورت همزمان (synchronous)
        برمی‌گرداند: URL تصویر تولید شده
        """
        logger.info(f"🎨 شروع تولید تصویر: '{prompt[:50]}...'")
        
        if not prompt or not isinstance(prompt, str):
            raise ImageGenerationError("❌ Prompt باید یک رشته غیرخالی باشد")

        # داده‌های درخواست
        payload = {
            "model": self.model,
            "prompt": prompt,
            "width": self.image_width,
            "height": self.image_height,
            "output_format": self.image_format,
            "num_images": 1,
            "guidance_scale": 7.5,
            "num_inference_steps": 20,
            "seed": None  # برای تصویر تصادفی
        }

        self._log_request("POST", self.api_url, payload)

        try:
            # ارسال درخواست
            response = requests.post(
                self.api_url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.request_timeout
            )
            
            self._log_response(response)

            # بررسی وضعیت پاسخ
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.debug(f"✅ داده‌های دریافتی: {data}")
                    
                    # استخراج URL تصویر
                    image_url = self._extract_image_url(data)
                    if image_url:
                        logger.info(f"🖼️ تصویر تولید شد: {image_url}")
                        return image_url
                    else:
                        logger.error(f"❌ URL تصویر در پاسخ پیدا نشد: {data}")
                        raise ImageGenerationError("URL تصویر در پاسخ API پیدا نشد")
                        
                except ValueError as e:
                    logger.error(f"❌ خطا در پارس JSON: {e}")
                    logger.error(f"📄 محتوای پاسخ: {response.text}")
                    raise ImageGenerationError(f"پاسخ API نامعتبر است: {e}")
                    
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "خطای نامشخص")
                except:
                    error_msg = response.text
                logger.error(f"❌ خطای درخواست (400): {error_msg}")
                raise ImageGenerationError(f"درخواست نامعتبر: {error_msg}")
                
            elif response.status_code == 401:
                logger.error("❌ خطای احراز هویت - API key اشتباه است")
                raise ImageGenerationError("API key نامعتبر است")
                
            elif response.status_code == 403:
                logger.error("❌ دسترسی مجاز نیست")
                raise ImageGenerationError("دسترسی به API مجاز نیست")
                
            elif response.status_code == 429:
                logger.error("❌ محدودیت نرخ درخواست")
                raise ImageGenerationError("تعداد درخواست‌ها از حد مجاز گذشته - کمی صبر کنید")
                
            else:
                logger.error(f"❌ خطای HTTP {response.status_code}: {response.text}")
                raise ImageGenerationError(f"خطای API: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error("⏰ درخواست timeout شد")
            raise ImageGenerationError("درخواست طولانی شد - دوباره تلاش کنید")
            
        except requests.exceptions.ConnectionError:
            logger.error("🌐 خطای اتصال به شبکه")
            raise ImageGenerationError("مشکل در اتصال به API")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ خطای درخواست: {e}")
            raise ImageGenerationError(f"خطا در ارسال درخواست: {e}")

    def _extract_image_url(self, data: Any) -> Optional[str]:
        """استخراج URL تصویر از پاسخ API"""
        logger.debug("🔍 جستجوی URL تصویر در پاسخ")
        
        # حالت‌های مختلف پاسخ API
        possible_paths = [
            # مسیرهای معمول
            ["url"],
            ["image_url"],
            ["output_url"],
            ["result", "url"],
            ["data", 0, "url"],
            ["images", 0, "url"],
            ["outputs", 0, "url"],
            ["results", 0, "url"],
            # مسیرهای تودرتو
            ["data", "url"],
            ["output", "url"],
            ["result", "image_url"],
            ["response", "url"],
            # برای base64
            ["image"],
            ["data", 0, "b64_json"],
            ["images", 0, "b64_json"],
        ]
        
        for path in possible_paths:
            try:
                current = data
                for key in path:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    elif isinstance(current, list) and isinstance(key, int) and len(current) > key:
                        current = current[key]
                    else:
                        break
                else:
                    # اگر به انتهای مسیر رسیدیم
                    if isinstance(current, str) and current:
                        # بررسی اینکه URL معتبر است یا base64
                        if current.startswith(("http://", "https://")):
                            logger.debug(f"✅ URL پیدا شد در مسیر {path}: {current[:50]}...")
                            return current
                        elif current.startswith("data:image/"):
                            logger.debug(f"✅ Data URL پیدا شد در مسیر {path}")
                            return current
                        elif len(current) > 100 and not current.startswith("http"):
                            # احتمالاً base64 است
                            logger.debug(f"✅ Base64 پیدا شد در مسیر {path}")
                            return f"data:image/{self.image_format.lower()};base64,{current}"
            except (KeyError, IndexError, TypeError):
                continue
        
        # اگر هیچ‌کدام پیدا نشد، کل داده را جستجو کن
        logger.debug("🔍 جستجوی عمومی در کل پاسخ")
        return self._deep_search_url(data)

    def _deep_search_url(self, obj: Any, visited: set = None) -> Optional[str]:
        """جستجوی عمیق برای پیدا کردن URL"""
        if visited is None:
            visited = set()
            
        obj_id = id(obj)
        if obj_id in visited:
            return None
        visited.add(obj_id)
        
        if isinstance(obj, str):
            if obj.startswith(("http://", "https://", "data:image/")):
                return obj
        elif isinstance(obj, dict):
            for value in obj.values():
                result = self._deep_search_url(value, visited)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = self._deep_search_url(item, visited)
                if result:
                    return result
        
        return None

    # متدهای سازگاری برای کد قدیمی
    def generate_image(self, prompt: str) -> str:
        """
        همان generate_image_sync - برای سازگاری با کد قدیمی
        """
        return self.generate_image_sync(prompt)

    def get_image_status(self, task_id: str, poll_interval: float = 5.0, timeout: float = 120.0):
        """
        این متد دیگر استفاده نمی‌شود چون از روش synchronous استفاده می‌کنیم
        """
        logger.warning("⚠️ get_image_status deprecated - از generate_image_sync استفاده کنید")
        raise ImageGenerationError("این متد دیگر پشتیبانی نمی‌شود")
