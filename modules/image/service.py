# modules/image/service.py
"""RunwayML image generation client (dev API + required version header)."""

from __future__ import annotations
import base64, os, time, re
from typing import Any, Dict, Iterable, Optional
import requests

# === ENV ===
RUNWAY_API = (os.getenv("RUNWAY_API") or "").strip()
# چون کلیدت از dev گرفتی، پیش‌فرض dev می‌ذاریم. اگر خواستی دستی override کن.
RUNWAY_API_URL = (os.getenv("RUNWAY_API_URL") or "https://api.dev.runwayml.com/v1/tasks").strip()
RUNWAY_MODEL = (os.getenv("RUNWAY_MODEL") or "gen4_image").strip()
RUNWAY_API_VERSION = (os.getenv("RUNWAY_API_VERSION") or "").strip()  # هدر لازم
IMAGE_WIDTH = int(os.getenv("RUNWAY_IMAGE_WIDTH", "1024"))
IMAGE_HEIGHT = int(os.getenv("RUNWAY_IMAGE_HEIGHT", "1024"))
IMAGE_FORMAT = (os.getenv("RUNWAY_IMAGE_FORMAT") or "png").strip()
POLL_INTERVAL = float(os.getenv("RUNWAY_POLL_INTERVAL", "0.8"))
POLL_TIMEOUT = float(os.getenv("RUNWAY_POLL_TIMEOUT", "60"))
DEBUG = (os.getenv("DEBUG", "false").lower() == "true")

class ImageGenerationError(RuntimeError): pass

def is_configured() -> bool:
    return bool(RUNWAY_API)

def _request(method: str, url: str, *, _can_retry: bool = True, **kwargs) -> Dict[str, Any]:
    global RUNWAY_API_VERSION
    kwargs = dict(kwargs)
    headers = dict(kwargs.pop("headers", {}))
    headers.setdefault("Authorization", f"Bearer {RUNWAY_API}")
    headers.setdefault("Content-Type", "application/json")
    # ⬇️ مهم: ارور 400 می‌خواست این هدر رو
    if RUNWAY_API_VERSION:
        headers.setdefault("X-Runway-Version", RUNWAY_API_VERSION)
    kwargs.setdefault("timeout", 30)
    try:
        resp = requests.request(method, url, headers=headers, **kwargs)
    except requests.RequestException as exc:
        raise ImageGenerationError(f"Runway network error: {exc}") from exc

    try:
        data = resp.json()
    except ValueError:
        data = {}

    if resp.status_code >= 400:
        msg = _extract_message(data) or resp.text
        if resp.status_code == 400 and _can_retry:
            hinted_version = _extract_version_hint(msg)
            current_version = headers.get("X-Runway-Version", "")
            if hinted_version and hinted_version != current_version:
                if DEBUG:
                    print(
                        f"[Runway] retry with hinted API version {hinted_version} (was {current_version or 'unset'})",
                        flush=True,
                    )
                headers["X-Runway-Version"] = hinted_version
                RUNWAY_API_VERSION = hinted_version
                kwargs["headers"] = headers
                return _request(method, url, _can_retry=False, **kwargs)
            if _looks_like_invalid_version(msg) and current_version:
                if DEBUG:
                    print(
                        "[Runway] retrying without X-Runway-Version header (server rejected current version)",
                        flush=True,
                    )
                headers.pop("X-Runway-Version", None)
                RUNWAY_API_VERSION = ""
                kwargs["headers"] = headers
                return _request(method, url, _can_retry=False, **kwargs)
        raise ImageGenerationError(f"Runway API {resp.status_code}: {msg}")
    return data

def generate_image(prompt: str, *, width: Optional[int] = None, height: Optional[int] = None) -> bytes:
    p = (prompt or "").strip()
    if not p: raise ImageGenerationError("Prompt is empty.")
    if not is_configured(): raise ImageGenerationError("RUNWAY_API env var is missing.")

    w = int(width or IMAGE_WIDTH); h = int(height or IMAGE_HEIGHT)
    payload = {
        "model": RUNWAY_MODEL,
        "input": { "prompt": p, "width": w, "height": h, "output_format": IMAGE_FORMAT },
    }

    data = _request("POST", RUNWAY_API_URL, json=payload)
    if DEBUG: print(f"[Runway] created: id={data.get('id')} status={data.get('status')}", flush=True)

    img = _extract_image_bytes(data)
    if img: return img

    task_id = data.get("id")
    if not task_id: raise ImageGenerationError("Runway response missing task id.")

    t0 = time.time()
    while True:
        if time.time() - t0 > POLL_TIMEOUT:
            raise ImageGenerationError("Runway polling timeout.")
        time.sleep(POLL_INTERVAL)
        poll = _request("GET", f"{RUNWAY_API_URL}/{task_id}")
        status = _upper(poll.get("status") or poll.get("state"))
        if DEBUG: print(f"[Runway] poll {task_id}: {status}", flush=True)

        if status in {"SUCCEEDED","COMPLETED","FINISHED"}:
            img = _extract_image_bytes(poll)
            if img: return img
            raise ImageGenerationError("Runway finished but no image found.")
        if status in {"FAILED","CANCELED","CANCELLED","ERROR"}:
            raise ImageGenerationError(f"Runway failed: {_extract_message(poll)}")

def _upper(x: Any) -> str: return str(x or "").strip().upper()
def _extract_message(d: Dict[str, Any]) -> str:
    for k in ("message","error","detail","details"):
        v = d.get(k)
        if isinstance(v,str) and v.strip(): return v
    return str(d)

_VERSION_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
def _extract_version_hint(msg: str) -> Optional[str]:
    if not isinstance(msg, str):
        return None
    m = _VERSION_RE.search(msg)
    if not m:
        return None
    return m.group(1)

def _looks_like_invalid_version(msg: Any) -> bool:
    if not isinstance(msg, str):
        return False
    m = msg.lower()
    return "api version" in m and "not valid" in m

def _extract_image_bytes(payload: Dict[str, Any]) -> Optional[bytes]:
    for url in _iter_urls(payload):
        try: return _download(url)
        except ImageGenerationError: continue
    b64 = _find_base64(payload)
    if b64:
        try: return base64.b64decode(b64)
        except Exception: 
            if DEBUG: print("[Runway] base64 decode failed.", flush=True)
    return None

def _iter_urls(node: Any):
    if isinstance(node, dict):
        for v in node.values(): yield from _iter_urls(v)
    elif isinstance(node, list):
        for it in node: yield from _iter_urls(it)
    elif isinstance(node, str):
        if node.startswith("http://") or node.startswith("https://"): yield node

_B64_RE = re.compile(r"^data:image/[^;]+;base64,(?P<data>[A-Za-z0-9+/=]+)$")
def _find_base64(node: Any) -> Optional[str]:
    if isinstance(node, dict):
        for v in node.values():
            r = _find_base64(v)
            if r: return r
    elif isinstance(node, list):
        for it in node:
            r = _find_base64(it)
            if r: return r
    elif isinstance(node, str):
        m = _B64_RE.match(node.strip())
        if m: return m.group("data")
    return None

def _download(url: str) -> bytes:
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        return r.content
    except requests.RequestException as exc:
        raise ImageGenerationError(f"Download failed: {exc}") from exc
