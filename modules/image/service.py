import os
import requests
import time

class ImageGenerationError(Exception):
    pass

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

            if resp.status_code == 200:
                try:
                    data = resp.json()
                except ValueError:
                    raise ImageGenerationError(f"Invalid JSON in status response: {resp.text}")

                status = data.get("status")
                succeeded_statuses = {"SUCCEEDED", "COMPLETED", "TASK_STATUS_SUCCEEDED"}
                if status and (status in succeeded_statuses or "SUCCEEDED" in str(status)):
                    output = data.get("output")
                    return output  # خروجی شامل لینک یا داده تصویر
                if status == "FAILED":
                    # اگر پیام خطا داشته باشه برگردونش
                    error_msg = data.get("error", "Unknown error from Runway during generation.")
                    raise ImageGenerationError(f"Runway task failed: {error_msg}")
                # اگر هنوز آماده نیست
                time.sleep(poll_interval)
            elif resp.status_code == 404:
                raise ImageGenerationError(f"Status check 404: task {task_id} not found.")
            else:
                raise ImageGenerationError(f"Error checking status: {resp.status_code} – {resp.text}")

        # اگر زمان تمام شد
        raise ImageGenerationError("Image generation timed out.")
