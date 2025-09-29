"""HTTP API for Vexa external integrations.

This module exposes a lightweight FastAPI application that allows
authenticated users to spend their existing credits on image generation
and text-to-speech conversions. Authentication is handled via per-user
API tokens that can be managed inside the Telegram bot.
"""
from __future__ import annotations

import base64
import logging
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

import db
from modules.image.service import ImageGenerationError, ImageService
from modules.image.settings import CREDIT_COST as IMAGE_CREDIT_COST, POLL_INTERVAL, POLL_TIMEOUT
from modules.tts.service import synthesize
from modules.tts.settings import BANNED_WORDS, CREDIT_PER_CHAR, DEFAULT_VOICE_NAME, VOICES

logger = logging.getLogger(__name__)

# Ensure the database schema exists when the API server boots.
db.init_db()

app = FastAPI(
    title="Vexa API",
    description="Programmatic access to Vexa's image generation and TTS services.",
    version="1.0.0",
)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class ImageRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt that describes the desired image")
    reference_image: str | None = Field(
        default=None,
        description="Optional base64-encoded reference image (raw base64 or data URI)",
    )
    mime_type: str | None = Field(
        default=None,
        description="Optional MIME type for the reference image (used when reference_image is provided)",
    )


class ImageResponse(BaseModel):
    image_url: str
    credits_charged: float
    credits_remaining: float


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text that should be converted to speech")
    voice_id: str | None = Field(
        default=None,
        description="Voice identifier (use the display name shown in the bot)",
    )
    mime_type: str | None = Field(
        default="audio/mpeg",
        description="Desired audio MIME type supported by ElevenLabs",
    )


class TTSResponse(BaseModel):
    audio_base64: str
    mime_type: str
    voice_id: str
    credits_charged: float
    credits_remaining: float


def _normalize_text(text: str) -> str:
    replacements = {
        "ك": "ک",
        "ي": "ی",
        "ى": "ی",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "آ": "ا",
        "ة": "ه",
        "ۀ": "ه",
    }
    normalized = (text or "").lower()
    for src, dst in replacements.items():
        normalized = normalized.replace(src, dst)
    return normalized.replace("ـ", "").replace("\u200c", " ").replace("\u200d", "")


_BANNED_LOOKUP = tuple(_normalize_text(word) for word in BANNED_WORDS if word)
_VOICE_NAME_MAP = {name.lower(): name for name in VOICES.keys()}


def _contains_banned_word(text: str) -> bool:
    normalized = _normalize_text(text)
    return any(word and word in normalized for word in _BANNED_LOOKUP)


def _decode_reference_image(encoded: str) -> bytes:
    cleaned = encoded.strip()
    if cleaned.startswith("data:"):
        try:
            cleaned = cleaned.split(",", 1)[1]
        except IndexError as exc:
            raise ValueError("Invalid data URI for reference image") from exc
    try:
        return base64.b64decode(cleaned)
    except Exception as exc:  # pragma: no cover - defensive; FastAPI handles validation
        raise ValueError("Reference image is not valid base64 data") from exc


def _extract_image_url(data: Any, _visited: set[int] | None = None) -> str | None:
    if _visited is None:
        _visited = set()
    data_id = id(data)
    if data_id in _visited:
        return None
    _visited.add(data_id)

    if isinstance(data, str):
        candidate = data.strip()
        if any(candidate.startswith(prefix) for prefix in ("http://", "https://")):
            return candidate
        return None

    if isinstance(data, dict):
        priority_keys = (
            "url",
            "image_url",
            "output_url",
            "result_url",
            "download_url",
            "file_url",
            "asset_url",
            "src",
            "href",
            "link",
            "path",
            "uri",
            "output",
        )
        for key in priority_keys:
            if key in data:
                url = _extract_image_url(data[key], _visited)
                if url:
                    return url
        lower_priority = {key.lower() for key in priority_keys}
        for key, value in data.items():
            if key.lower() in lower_priority:
                continue
            url = _extract_image_url(value, _visited)
            if url:
                return url
        return None

    if isinstance(data, (list, tuple, set)):
        for item in data:
            url = _extract_image_url(item, _visited)
            if url:
                return url
        return None

    return None


async def _get_current_user(api_key: str = Depends(_api_key_header)):
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key is missing")

    user = db.get_user_by_api_token(api_key)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if user.get("banned"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is banned")

    db.touch_last_seen(user["user_id"])
    return user


@app.post("/v1/image", response_model=ImageResponse)
async def generate_image(payload: ImageRequest, current_user=Depends(_get_current_user)):
    prompt = (payload.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prompt must not be empty")

    fresh = db.get_user(current_user["user_id"]) or current_user
    credits = float(fresh.get("credits") or 0)
    if credits < IMAGE_CREDIT_COST:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits")

    try:
        service = ImageService()
    except ImageGenerationError as exc:
        logger.exception("Image service not configured", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    reference_bytes = None
    mime_type = payload.mime_type
    if payload.reference_image:
        try:
            reference_bytes = _decode_reference_image(payload.reference_image)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        if reference_bytes is not None:
            task_id = service.generate_image_from_image(
                prompt,
                reference_bytes,
                mime_type=mime_type,
            )
        else:
            task_id = service.generate_image(prompt)

        result = service.get_image_status(
            task_id,
            poll_interval=POLL_INTERVAL,
            timeout=POLL_TIMEOUT,
        )
    except ImageGenerationError as exc:
        logger.exception("Image generation failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    image_url = result.get("url") or _extract_image_url(result)
    if not image_url:
        logger.error("Could not extract image URL from response: %s", result)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Image URL not found in provider response")

    if not db.deduct_credits(current_user["user_id"], IMAGE_CREDIT_COST):
        logger.warning("Credit deduction failed after image generation", extra={"user_id": current_user["user_id"]})
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to deduct credits")

    try:
        db.log_image_generation(current_user["user_id"], prompt, image_url)
    except Exception:
        logger.exception("Failed to log image generation", extra={"user_id": current_user["user_id"]})

    updated = db.get_user(current_user["user_id"]) or fresh
    remaining = float(updated.get("credits") or 0)

    return ImageResponse(
        image_url=image_url,
        credits_charged=float(IMAGE_CREDIT_COST),
        credits_remaining=remaining,
    )


@app.post("/v1/tts", response_model=TTSResponse)
async def text_to_speech(payload: TTSRequest, current_user=Depends(_get_current_user)):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text must not be empty")

    if _contains_banned_word(text):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text contains blocked words")

    voice_key = (payload.voice_id or DEFAULT_VOICE_NAME).strip()
    normalized_voice = _VOICE_NAME_MAP.get(voice_key.lower())
    if not normalized_voice:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Voice not found")
    voice_id = VOICES[normalized_voice]

    cost = round(len(text) * CREDIT_PER_CHAR, 2)
    if cost <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text is too short")

    fresh = db.get_user(current_user["user_id"]) or current_user
    credits = float(fresh.get("credits") or 0)
    if credits < cost:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits")

    try:
        audio_bytes = synthesize(text, voice_id, payload.mime_type or "audio/mpeg")
    except Exception as exc:
        logger.exception("TTS synthesis failed", exc_info=exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="TTS synthesis failed") from exc

    if not db.deduct_credits(current_user["user_id"], cost):
        logger.warning("Credit deduction failed after TTS", extra={"user_id": current_user["user_id"]})
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to deduct credits")

    try:
        db.log_tts_request(current_user["user_id"], text)
    except Exception:
        logger.exception("Failed to log TTS request", extra={"user_id": current_user["user_id"]})

    updated = db.get_user(current_user["user_id"]) or fresh
    remaining = float(updated.get("credits") or 0)

    audio_base64 = base64.b64encode(audio_bytes).decode("ascii")
    return TTSResponse(
        audio_base64=audio_base64,
        mime_type=payload.mime_type or "audio/mpeg",
        voice_id=normalized_voice,
        credits_charged=cost,
        credits_remaining=remaining,
    )


@app.get("/v1/voices")
async def list_voices(current_user=Depends(_get_current_user)):
    """Return the list of available voice identifiers."""
    voices = [{"id": name, "voice_id": voice_id} for name, voice_id in VOICES.items()]
    return JSONResponse({"voices": voices})
