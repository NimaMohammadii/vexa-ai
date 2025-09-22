"""Tests for the Runway image service helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.image.service import ImageGenerationError, ImageService


class DummyResponse:
    """Simple stand-in for ``requests.Response`` used in the tests."""

    def __init__(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Dict[str, Any]:  # noqa: D401 - mimics ``requests.Response``
        """Return the JSON payload."""

        return self._payload


@pytest.fixture(autouse=True)
def _runway_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the service sees a Runway token during the tests."""

    monkeypatch.setenv("RUNWAY_API", "test-token")


def test_generate_image_accepts_wrapped_task_response(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ImageService()

    def fake_request(self: ImageService, method: str, path: str, **_: Any) -> DummyResponse:  # noqa: ANN001
        assert method == "POST" and path == "/tasks"
        return DummyResponse({"data": {"id": "task-xyz", "status": "queued"}})

    monkeypatch.setattr(ImageService, "_request", fake_request)

    task_id = service.generate_image("a friendly robot")
    assert task_id == "task-xyz"


def test_generate_image_ignores_unrelated_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ImageService()

    payload = {
        "user": {"id": "user-123"},
        "data": {
            "items": [
                {"id": "asset-789"},
                {"task": {"id": "runway-task-456", "status": "queued"}},
            ]
        },
    }

    def fake_request(self: ImageService, method: str, path: str, **_: Any) -> DummyResponse:  # noqa: ANN001
        assert method == "POST" and path == "/tasks"
        return DummyResponse(payload)

    monkeypatch.setattr(ImageService, "_request", fake_request)

    task_id = service.generate_image("find the correct id")
    assert task_id == "runway-task-456"


def test_get_image_status_handles_nested_status(monkeypatch: pytest.MonkeyPatch) -> None:
    service = ImageService()

    poll_payloads = [
        {"data": {"status": "pending"}},
        {"task": {"status": "SUCCEEDED"}},
    ]

    def fake_request(self: ImageService, method: str, path: str, **_: Any) -> DummyResponse:  # noqa: ANN001
        if method == "GET" and path == "/tasks/task-xyz":
            if not poll_payloads:
                raise AssertionError("No more poll payloads available")
            return DummyResponse(poll_payloads.pop(0))
        if method == "GET" and path == "/tasks/task-xyz/assets":
            return DummyResponse({"items": [{"url": "https://example.com/image.png"}]})
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(ImageService, "_request", fake_request)
    monkeypatch.setattr("modules.image.service.time.sleep", lambda _: None)

    result = service.get_image_status("task-xyz", poll_interval=0, timeout=5)

    assert result.get("assets")
    assert not poll_payloads


def test_extract_task_id_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure a helpful error is raised when no ID is present."""

    service = ImageService()

    def fake_request(self: ImageService, method: str, path: str, **_: Any) -> DummyResponse:  # noqa: ANN001
        if method == "POST" and path == "/tasks":
            return DummyResponse({"data": {"assets": []}})
        raise AssertionError(f"Unexpected request: {method} {path}")

    monkeypatch.setattr(ImageService, "_request", fake_request)

    with pytest.raises(ImageGenerationError):
        service.generate_image("missing id response")
