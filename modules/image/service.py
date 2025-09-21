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
        
        # تنظیمات API - endpoint های درست Runway
        self.api_key = os.getenv("RUNWAY_API")
        self.api_version = os.getenv("RUNWAY_API_VERSION", "2024-11-13")
        
        # endpoint های مختلف Runway برای تست
        self.base_url = "https://api.runwayml.com/v1"
        self.endpoints = {
            "tasks": f"{self.base_url}/tasks",
            "images": f"{self.base_url}/images/generate", 
            "generate": f"{self.base_url}/generate",
            "inference": f"{self.base_url}/inference",
        }
        
        # مدل‌های مختلف Runway
        self.available_models = [
            "gen3a_turbo",
            "gen3_turbo", 
            "runway-ml/stable-diffusion-v1-5",
            "runway/stable-diffusion-v1-5",
            "gen2",
            "gen1"
        ]
        
        self.model = os.getenv("RUNWAY_MODEL", "gen3a_turbo")
        
        # تنظیمات تصویر
        self.image_width = int(os.getenv("RUNWAY_IMAGE_WIDTH", "1024"))
        self.image_height = int(os.getenv("RUNWAY_IMAGE_HEIGHT", "1024"))
        self.image_format = os.getenv("RUNWAY_IMAGE_FORMAT", "WEBP")
        
        # تنظیمات timeout
        self.request_timeout = int(os.getenv("RUNWAY_REQUEST_TIMEOUT", "30"))
        self.generation_timeout = int(os.getenv("RUNWAY_GENERATION_TIMEOUT", "300"))
        self.poll_interval = float(os.getenv("RUNWAY_POLL_INTERVAL", "3.0"))

        # لاگ تنظیمات
        logger.info(f"📋 تنظیمات:")
        logger.info(f"   Base URL: {self.base_url}")
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
            "X-Runway-Version": self.api_version,
        }
            
        return headers

    def _test_endpoint(self, url: str) -> bool:
        """تست کردن اینکه endpoint کار می‌کنه یا نه"""
        try:
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            logger.debug(f"🔍 تست {url}: {response.status_code}")
            return response.status_code != 404
        except:
            return False

    def _find_working_endpoint(self) -> str:
        """پیدا کردن endpoint کاری"""
        logger.info("🔍 جستجوی endpoint کاری...")
        
        for name, url in self.endpoints.items():
            logger.debug(f"   تست {name}: {url}")
            if self._test_endpoint(url):
                logger.info(f"✅ endpoint کاری پیدا شد: {name} - {url}")
                return url
        
        # اگر هیچ‌کدام کار نکرد، از tasks استفاده کن (معمولی‌ترین)
        logger.warning("⚠️ هیچ endpoint کاری پیدا نشد - استفاده از tasks")
        return self.endpoints["tasks"]

    def generate_image_async(self, prompt: str) -> str:
        """
        تولید تصویر با روش async (task-based)
        """
        logger.info(f"🎨 شروع تولید تصویر async: '{prompt[:50]}...'")
        
        if not prompt or not isinstance(prompt, str):
            raise ImageGenerationError("❌ Prompt باید یک رشته غیرخالی باشد")

        # پیدا کردن endpoint کاری
        api_url = self._find_working_endpoint()

        # تست چندین ساختار payload
        payloads = [
            # ساختار جدید Gen3
            {
                "model": self.model,
                "input": {
                    "prompt": prompt,
                    "width": self.image_width,
                    "height": self.image_height,
                    "output_format": self.image_format,
                }
            },
            # ساختار قدیمی‌تر
            {
                "model": self.model,
                "prompt": prompt,
                "width": self.image_width,
                "height": self.image_height,
                "output_format": self.image_format,
                "num_images": 1,
            },
            # ساختار ساده
            {
                "prompt": prompt,
                "model": self.model,
                "width": self.image_width,
                "height": self.image_height,
            }
        ]

        for i, payload in enumerate(payloads):
            logger.info(f"🔄 تلاش {i+1} با ساختار {i+1}")
            logger.debug(f"📋 Payload: {payload}")
            
            try:
                response = requests.post(
                    api_url,
                    json=payload,
                    headers=self._get_headers(),
                    timeout=self.request_timeout
                )
                
                logger.info(f"📥 پاسخ: {response.status_code}")
                logger.debug(f"📄 محتوا: {response.text[:300]}...")

                if response.status_code == 200 or response.status_code == 201:
                    try:
                        data = response.json()
                        task_id = data.get("id") or data.get("task_id") or data.get("requestId")
                        
                        if task_id:
                            logger.info(f"✅ Task ایجاد شد: {task_id}")
                            return self._wait_for_completion(task_id, api_url)
                        else:
                            # شاید مستقیماً URL برگرداند
                            image_url = self._extract_image_url(data)
                            if image_url:
                                logger.info(f"🖼️ تصویر مستقیماً دریافت شد: {image_url}")
                                return image_url
                            
                    except ValueError as e:
                        logger.error(f"❌ خطا در پارس JSON: {e}")
                        continue
                        
                elif response.status_code == 404:
                    logger.warning(f"⚠️ Endpoint {api_url} کار نمی‌کنه")
                    continue
                    
                elif response.status_code == 400:
                    try:
                        error_data = response.json()
                        logger.warning(f"⚠️ ساختار payload {i+1} نامعتبر: {error_data}")
                        continue
                    except:
                        logger.warning(f"⚠️ ساختار payload {i+1} نامعتبر")
                        continue
                        
                elif response.status_code == 401:
                    raise ImageGenerationError("❌ API key نامعتبر است")
                    
                else:
                    logger.warning(f"⚠️ پاسخ غیرمنتظره {response.status_code}: {response.text[:200]}")
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏰ Timeout در تلاش {i+1}")
                continue
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"❌ خطا در تلاش {i+1}: {e}")
                continue

        # اگر همه تلاش‌ها شکست خوردند
        raise ImageGenerationError("❌ تمام روش‌های تولید تصویر شکست خوردند")

    def _wait_for_completion(self, task_id: str, base_url: str) -> str:
        """انتظار برای تکمیل task"""
        logger.info(f"⏳ انتظار برای تکمیل task {task_id}")
        
        status_url = f"{base_url.rstrip('/')}/{task_id}"
        start_time = time.time()
        
        while time.time() - start_time < self.generation_timeout:
            try:
                response = requests.get(status_url, headers=self._get_headers(), timeout=20)
                logger.debug(f"📊 بررسی وضعیت: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # بررسی وضعیت
                    status = data.get("status", "").upper()
                    logger.debug(f"📊 وضعیت: {status}")
                    
                    if status in ["SUCCEEDED", "COMPLETED", "FINISHED"]:
                        logger.info("✅ تولید تصویر موفق بود")
                        
                        # جستجوی URL
                        image_url = self._extract_image_url(data)
                        if image_url:
                            return image_url
                        else:
                            # تلاش برای دریافت از endpoint جانبی
                            assets_url = f"{status_url}/assets"
                            assets_response = requests.get(assets_url, headers=self._get_headers())
                            if assets_response.status_code == 200:
                                assets_data = assets_response.json()
                                image_url = self._extract_image_url(assets_data)
                                if image_url:
                                    return image_url
                            
                            raise ImageGenerationError("❌ URL تصویر در پاسخ پیدا نشد")
                    
                    elif status in ["FAILED", "ERROR", "CANCELLED"]:
                        error_msg = data.get("error", data.get("message", "خطای نامشخص"))
                        logger.error(f"❌ تولید تصویر شکست خورد: {error_msg}")
                        raise ImageGenerationError(f"تولید تصویر شکست خورد: {error_msg}")
                    
                    # در حال پردازش
                    logger.debug(f"⏳ در حال پردازش... ({status})")
                    
                elif response.status_code == 404:
                    raise ImageGenerationError(f"❌ Task {task_id} پیدا نشد")
                    
                else:
                    logger.warning(f"⚠️ پاسخ غیرمنتظره {response.status_code}")
                    
            except requests.RequestException as e:
                logger.warning(f"⚠️ خطا در بررسی وضعیت: {e}")
            
            time.sleep(self.poll_interval)
        
        raise ImageGenerationError("⏰ تولید تصویر timeout شد")

    def _extract_image_url(self, data: Any) -> Optional[str]:
        """استخراج URL تصویر از پاسخ"""
        logger.debug("🔍 جستجوی URL تصویر...")
        
        # مسیرهای مختلف ممکن
        paths = [
            ["output", 0, "uri"],
            ["output", "uri"],
            ["outputs", 0, "url"],
            ["artifacts", 0, "uri"],
            ["result", "url"],
            ["url"],
            ["image_url"],
            ["uri"],
            ["signed_url"],
            ["data", "url"],
            ["assets", 0, "url"],
        ]
        
        for path in paths:
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
                    if isinstance(current, str) and current.startswith(("http://", "https://", "data:")):
                        logger.debug(f"✅ URL پیدا شد: {current[:50]}...")
                        return current
            except (KeyError, IndexError, TypeError):
                continue
        
        # جستجوی عمقی
        return self._deep_search_url(data)

    def _deep_search_url(self, obj: Any, visited: set = None) -> Optional[str]:
        """جستجوی عمیق برای URL"""
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

    # متدهای اصلی برای استفاده
    def generate_image(self, prompt: str) -> str:
        """متد اصلی تولید تصویر"""
        return self.generate_image_async(prompt)

    def get_image_status(self, task_id: str, poll_interval: float = 5.0, timeout: float = 120.0):
        """سازگاری با کد قدیمی"""
        logger.warning("⚠️ این متد deprecated است")
        return self._wait_for_completion(task_id, self.endpoints["tasks"])
