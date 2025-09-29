"""FastAPI application providing API key protected endpoints for Vexa AI."""
from __future__ import annotations

import hmac
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import JSONResponse

import db
from config import (
    ADMIN_API_KEY,
    API_CREDIT_COST,
    API_KEY_HEADER_NAME,
)

logger = logging.getLogger(__name__)

db.init_db()

app = FastAPI(
    title="Vexa AI API",
    version="1.0.0",
    description=(
        "Protected API for Vexa AI. Every request must include a valid API key "
        "and will deduct credits from the owning user."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

api_router = APIRouter(prefix="/api", tags=["client"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


def _api_key_missing_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key is required.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def _api_key_invalid_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key is invalid or has been revoked.",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def _insufficient_credit_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="Not enough credits to fulfil the request.",
    )


async def require_authenticated_user(
    api_key: str | None = Header(default=None, alias=API_KEY_HEADER_NAME),
) -> Dict[str, Any]:
    if not api_key:
        raise _api_key_missing_exception()

    user = db.verify_api_key(api_key)
    if not user:
        raise _api_key_invalid_exception()

    credits_before = int(user.get("credits") or 0)
    if not db.consume_api_credit(user["user_id"], API_CREDIT_COST):
        raise _insufficient_credit_exception()

    user["credits"] = max(0, credits_before - API_CREDIT_COST)
    user["api_key"] = api_key
    return user


async def require_admin(
    admin_key: str | None = Header(default=None, alias="X-Admin-API-Key"),
) -> None:
    configured = (ADMIN_API_KEY or "").strip()
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_API_KEY is not configured on the server.",
        )
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin API key is required.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if not hmac.compare_digest(admin_key, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin API key is invalid.",
            headers={"WWW-Authenticate": "ApiKey"},
        )


@api_router.get("/ping", summary="Health-check endpoint")
async def ping(user: Dict[str, Any] = Depends(require_authenticated_user)) -> Dict[str, Any]:
    """A lightweight endpoint to test API key authentication."""

    return {
        "status": "ok",
        "message": "Welcome to Vexa AI API",
        "user_id": user["user_id"],
        "credits_remaining": user["credits"],
    }


@api_router.post("/echo", summary="Echo helper endpoint")
async def echo(
    payload: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_authenticated_user),
) -> Dict[str, Any]:
    """Returns the payload that was sent in to confirm authentication works."""

    return {
        "received": payload,
        "user_id": user["user_id"],
        "credits_remaining": user["credits"],
    }


@admin_router.get("/users/{user_id}/api-key", summary="Inspect a user's API key")
async def admin_get_api_key(
    user_id: int,
    reveal: bool = False,
    _: None = Depends(require_admin),
):
    info = db.get_user_api_key(user_id, reveal=reveal)
    if not info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if info.get("api_key") and reveal:
        logger.info("Admin viewed API key for user %s", user_id)
    return info


@admin_router.post("/users/{user_id}/api-key/regenerate", summary="Regenerate a user's API key")
async def admin_regenerate_api_key(
    user_id: int,
    _: None = Depends(require_admin),
):
    try:
        new_key = db.regenerate_user_api_key(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    logger.info("Admin regenerated API key for user %s", user_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "user_id": user_id,
            "api_key": new_key,
            "message": "API key regenerated successfully. Share this key securely with the user.",
        },
    )


@admin_router.post("/users/{user_id}/api-key/revoke", summary="Revoke a user's API key")
async def admin_revoke_api_key(
    user_id: int,
    _: None = Depends(require_admin),
):
    try:
        db.revoke_user_api_key(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    logger.info("Admin revoked API key for user %s", user_id)
    return {"user_id": user_id, "message": "API key revoked."}


@admin_router.post("/users/{user_id}/api-key/issue", summary="Issue an API key if missing")
async def admin_issue_api_key(
    user_id: int,
    _: None = Depends(require_admin),
):
    try:
        api_key = db.ensure_user_api_key(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {
        "user_id": user_id,
        "api_key": api_key,
        "message": "API key issued successfully.",
    }


app.include_router(api_router)
app.include_router(admin_router)


@app.get("/", include_in_schema=False)
async def root() -> Dict[str, Any]:
    """Redirect users to the documentation when they hit the bare domain."""

    return {
        "message": "Vexa AI API is running. Visit /api/docs for the interactive documentation.",
        "docs_url": "/api/docs",
    }


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    import uvicorn

    uvicorn.run("api_app:app", host="0.0.0.0", port=8000, reload=False)

