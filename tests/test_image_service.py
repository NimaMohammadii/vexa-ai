import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.image import service


def _make_response(payload, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = json.dumps(payload)
    return response


def test_generate_image_uses_input_key():
    image_bytes = b"fake-image"
    task_response = {
        "id": "task_123",
        "state": "SUCCEEDED",
        "result": {
            "outputs": [
                {"uri": "https://cdn.example.com/image.png"},
            ]
        },
    }

    with (
        patch.object(service, "RUNWAY_API_KEY", "test-key"),
        patch.object(service.requests, "request", return_value=_make_response(task_response)) as mock_request,
        patch.object(service.requests, "get", return_value=_make_response({}, 200)) as mock_get,
    ):
        mock_get.return_value.content = image_bytes
        mock_get.return_value.raise_for_status = MagicMock()

        result = service.generate_image("a prompt")

    assert result == image_bytes

    assert mock_request.call_count == 1
    assert mock_get.call_count == 1

    _, kwargs = mock_request.call_args
    assert "json" in kwargs
    assert kwargs["json"]["model"] == "gen4_image"
    assert "input" in kwargs["json"]
    assert "prompt" in kwargs["json"]["input"]
    assert "inputs" not in kwargs["json"]


@pytest.mark.parametrize("bad_prompt", ["", "   "])
def test_generate_image_rejects_empty_prompt(bad_prompt):
    with pytest.raises(service.ImageGenerationError):
        service.generate_image(bad_prompt)
