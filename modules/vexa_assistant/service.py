"""Service helpers for the dedicated Vexa Assistant powered by OpenAI."""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, Iterable, List, Optional

from openai import OpenAI

from config import (
    DEBUG,
    GPT_API_KEY_HEADER,
    GPT_API_KEY_PREFIX,
    GPT_API_TIMEOUT,
    VEXA_ASSISTANT_API_KEY,
    VEXA_ASSISTANT_API_URL,
    VEXA_ASSISTANT_ID,
    VEXA_ASSISTANT_MODEL,
)
from modules.gpt.service import extract_message_text, resolve_gpt_api_key, web_search


class VexaAssistantError(RuntimeError):
    """Raised when the Vexa Assistant API returns an error."""


_cached_api_key: Optional[str] = None


_RESPONSE_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for up-to-date information using DuckDuckGo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query provided by the user.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "default": 3,
                        "description": "Maximum number of results to return.",
                    },
                },
                "required": ["query"],
            },
        },
    }
]


def resolve_api_key(force_refresh: bool = False) -> str:
    """Return the API key used for the Vexa Assistant."""

    global _cached_api_key

    if not force_refresh and _cached_api_key is not None:
        return _cached_api_key

    if VEXA_ASSISTANT_API_KEY:
        _cached_api_key = VEXA_ASSISTANT_API_KEY
        return _cached_api_key

    key = resolve_gpt_api_key(force_refresh=force_refresh)
    _cached_api_key = key
    return key


def ensure_ready(force_refresh: bool = False) -> tuple[bool, Optional[str]]:
    """Check whether the assistant is configured correctly."""

    key = resolve_api_key(force_refresh=force_refresh)
    if not key:
        return False, "missing_api_key"
    return True, None


def prepare_messages(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalise a conversation history for API consumption."""

    normalised: List[Dict[str, Any]] = []
    for item in history:
        role = str(item.get("role", "assistant") or "assistant").strip() or "assistant"
        content = item.get("content", "")
        normalised.append({"role": role, "content": content})

    return normalised


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------


def _normalise_base_url(url: Optional[str]) -> str:
    """Return the base URL to be used with the OpenAI client."""

    if not url:
        return "https://api.openai.com/v1"

    candidate = url.strip()
    if not candidate:
        return "https://api.openai.com/v1"

    for suffix in ("/responses", "/chat/completions"):
        if candidate.endswith(suffix):
            candidate = candidate[: -len(suffix)]
            break

    return candidate.rstrip("/") or "https://api.openai.com/v1"


def _build_client(api_key: str) -> OpenAI:
    base_url = _normalise_base_url(VEXA_ASSISTANT_API_URL)
    header_name = (GPT_API_KEY_HEADER or "Authorization").strip() or "Authorization"
    prefix = GPT_API_KEY_PREFIX or ""

    extra_headers: Dict[str, str] = {"OpenAI-Beta": "assistants=v2"}
    if header_name.lower() != "authorization":
        extra_headers[header_name] = f"{prefix}{api_key}"

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=GPT_API_TIMEOUT,
        default_headers=extra_headers or None,
    )

    if header_name.lower() == "authorization" and prefix and not prefix.lower().startswith("bearer"):
        transport = getattr(client, "_client", None)
        config = getattr(transport, "config", None)
        if config is not None and hasattr(config, "default_headers"):
            config.default_headers["Authorization"] = f"{prefix}{api_key}"  # type: ignore[index]

    return client


def _to_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    for attr in ("model_dump", "to_dict"):
        if hasattr(value, attr):
            method = getattr(value, attr)
            try:
                data = method()
            except TypeError:
                data = method
            if isinstance(data, dict):
                return data
    if hasattr(value, "json"):
        try:
            return json.loads(value.json())
        except Exception:  # pragma: no cover - defensive
            return {}
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {}


def _serialise_tool_result(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, (dict, list)):
        try:
            return json.dumps(result, ensure_ascii=False)
        except TypeError:
            return json.dumps(str(result), ensure_ascii=False)
    return str(result)


# ---------------------------------------------------------------------------
# Built-in tools
# ---------------------------------------------------------------------------


def _format_search_results(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "No results were found for the requested search."

    lines: List[str] = []
    for index, item in enumerate(results, start=1):
        title = str(item.get("title") or "Untitled result").strip()
        url = str(item.get("url") or "").strip()
        snippet = str(item.get("snippet") or "").strip()

        header = f"{index}. {title}" if title else f"{index}. Result"
        if url:
            header = f"{header} — {url}"
        lines.append(header)
        if snippet:
            lines.append(snippet)

    return "\n".join(lines)


def do_web_search(args: Dict[str, Any]) -> str:
    query = args.get("query") or args.get("q") or ""
    if not query:
        return "Web search was requested but no query was provided."

    try:
        results = web_search(str(query), max_results=int(args.get("max_results", 3)))
    except Exception as exc:  # pragma: no cover - network errors
        return f"Web search failed: {exc}"

    return _format_search_results(results)


def call_openai_image(args: Dict[str, Any]) -> Any:
    client: Optional[OpenAI] = args.get("_client")
    if client is None:
        return "OpenAI client not available for image generation."

    prompt = args.get("prompt") or args.get("description") or args.get("text")
    if not prompt:
        return "Image generation requires a prompt."

    model = (args.get("model") or "gpt-image-1").strip() or "gpt-image-1"

    try:
        response = client.images.generate(model=model, prompt=prompt)
    except Exception as exc:  # pragma: no cover - network errors
        return f"Image generation failed: {exc}"

    urls: List[str] = []
    data = getattr(response, "data", None)
    if isinstance(data, Iterable):
        for item in data:
            item_dict = _to_dict(item)
            url = item_dict.get("url")
            if url:
                urls.append(url)

    if not urls:
        return "The image API did not return any URLs."

    return {"urls": urls}


def analyze_file(args: Dict[str, Any]) -> str:
    name = args.get("file_name") or args.get("file_id") or "unknown file"
    return f"File analysis is not available in this deployment. Received: {name}"


def run_python_code(args: Dict[str, Any]) -> str:
    code = args.get("code") or args.get("python") or args.get("source")
    if not code:
        return "No Python code was provided for execution."
    return "Code execution is disabled for security reasons in this environment."


def analyze_uploaded_image(args: Dict[str, Any]) -> str:
    client: Optional[OpenAI] = args.get("_client")
    if client is None:
        return "OpenAI client not available for image analysis."

    prompt = (
        args.get("prompt")
        or args.get("instruction")
        or "Provide a detailed description of the supplied image."
    )
    model = (args.get("model") or "gpt-4o-mini").strip() or "gpt-4o-mini"
    image_url = args.get("image_url") or args.get("url")
    image_file_id = args.get("image_file_id") or args.get("file_id")

    if not image_url and not image_file_id:
        return "Image analysis requires an image_url or image_file_id."

    content: List[Dict[str, Any]] = [{"type": "input_text", "text": prompt}]
    if image_url:
        content.append({"type": "input_image", "image_url": {"url": image_url}})
    if image_file_id:
        content.append({"type": "input_image", "image_file_id": image_file_id})

    try:
        response = client.responses.create(
            model=model,
            messages=[{"role": "user", "content": content}],
        )
    except Exception as exc:  # pragma: no cover - network errors
        return f"Image analysis failed: {exc}"

    return _extract_output_text(response)


tool_router: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "web_search": do_web_search,
    "create_image": call_openai_image,
    "analyze_file": analyze_file,
    "run_code": run_python_code,
    "analyze_image": analyze_uploaded_image,
    "analyze_uploaded_image": analyze_uploaded_image,
}


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _extract_output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    data = _to_dict(response)
    if data:
        outputs = data.get("output") or data.get("outputs")
        if isinstance(outputs, list):
            parts: List[str] = []
            for item in outputs:
                item_dict = _to_dict(item)
                content = item_dict.get("content")
                if isinstance(content, list):
                    for part in content:
                        part_dict = _to_dict(part)
                        text_dict = part_dict.get("text") or part_dict.get("output_text")
                        if isinstance(text_dict, dict):
                            value = text_dict.get("value") or text_dict.get("text")
                            if isinstance(value, str):
                                parts.append(value)
                        elif isinstance(text_dict, str):
                            parts.append(text_dict)
                        elif part_dict.get("type") == "text":
                            nested = part_dict.get("value")
                            if isinstance(nested, str):
                                parts.append(nested)
            if parts:
                return "\n".join(part.strip() for part in parts if isinstance(part, str) and part.strip())

        extracted = extract_message_text(data)
        if extracted:
            return extracted.strip()

    return ""


def _message_content_to_text(content: Iterable[Any]) -> str:
    parts: List[str] = []
    for item in content:
        item_dict = _to_dict(item)
        text_block = item_dict.get("text") or item_dict.get("output_text")
        if isinstance(text_block, dict):
            value = text_block.get("value") or text_block.get("text")
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
        elif isinstance(text_block, str) and text_block.strip():
            parts.append(text_block.strip())
        elif isinstance(item_dict.get("type"), str):
            value = item_dict.get("value")
            if isinstance(value, str) and value.strip():
                parts.append(value.strip())
    return "\n".join(parts)


def _latest_assistant_message(client: OpenAI, thread_id: str) -> str:
    try:
        messages = client.beta.threads.messages.list(thread_id=thread_id, order="desc", limit=10)
    except Exception as exc:  # pragma: no cover - network errors
        raise VexaAssistantError(f"failed_to_fetch_messages: {exc}") from exc

    data = getattr(messages, "data", None)
    if not isinstance(data, Iterable):
        return ""

    for message in data:
        message_dict = _to_dict(message)
        if message_dict.get("role") != "assistant":
            continue
        content = message_dict.get("content")
        if isinstance(content, list):
            text = _message_content_to_text(content)
            if text:
                return text
    return ""


def _handle_requires_action(client: OpenAI, thread_id: str, run: Any) -> Any:
    action = getattr(run, "required_action", None)
    if action is None:
        return run

    submit = getattr(action, "submit_tool_outputs", None)
    if submit is None:
        return run

    tool_calls = getattr(submit, "tool_calls", None)
    if not isinstance(tool_calls, Iterable):
        return run

    outputs: List[Dict[str, str]] = []
    for tool_call in tool_calls:
        tool_dict = _to_dict(tool_call)
        function_dict = tool_dict.get("function", {}) if isinstance(tool_dict, dict) else {}
        name = function_dict.get("name")
        raw_arguments = function_dict.get("arguments")

        if not name:
            continue

        try:
            parsed_args = json.loads(raw_arguments or "{}") if raw_arguments else {}
        except json.JSONDecodeError:
            parsed_args = {"raw_arguments": raw_arguments}

        parsed_args["_client"] = client

        handler = tool_router.get(name)
        if handler is None:
            result = f"Tool '{name}' is not implemented."
        else:
            try:
                result = handler(parsed_args)
            except Exception as exc:  # pragma: no cover - defensive
                if DEBUG:
                    print(f"Tool '{name}' raised an exception:", exc)
                result = f"Tool '{name}' failed: {exc}"

        outputs.append(
            {
                "tool_call_id": tool_dict.get("id") or getattr(tool_call, "id", ""),
                "output": _serialise_tool_result(result),
            }
        )

    try:
        return client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=getattr(run, "id"),
            tool_outputs=outputs,
        )
    except Exception as exc:  # pragma: no cover - network errors
        raise VexaAssistantError(f"submit_tool_outputs_failed: {exc}") from exc


def _handle_response_requires_action(client: OpenAI, response: Any) -> Any:
    action = getattr(response, "required_action", None)
    if action is None:
        return response

    submit = getattr(action, "submit_tool_outputs", None)
    if submit is None:
        return response

    tool_calls = getattr(submit, "tool_calls", None)
    if not isinstance(tool_calls, Iterable):
        return response

    outputs: List[Dict[str, str]] = []
    for tool_call in tool_calls:
        tool_dict = _to_dict(tool_call)
        function_dict = tool_dict.get("function", {}) if isinstance(tool_dict, dict) else {}
        name = function_dict.get("name")
        raw_arguments = function_dict.get("arguments")

        if not name:
            continue

        try:
            parsed_args = json.loads(raw_arguments or "{}") if raw_arguments else {}
        except json.JSONDecodeError:
            parsed_args = {"raw_arguments": raw_arguments}

        parsed_args["_client"] = client

        handler = tool_router.get(name)
        if handler is None:
            result = f"Tool '{name}' is not implemented."
        else:
            try:
                result = handler(parsed_args)
            except Exception as exc:  # pragma: no cover - defensive
                if DEBUG:
                    print(f"Tool '{name}' raised an exception:", exc)
                result = f"Tool '{name}' failed: {exc}"

        outputs.append(
            {
                "tool_call_id": tool_dict.get("id") or getattr(tool_call, "id", ""),
                "output": _serialise_tool_result(result),
            }
        )

    try:
        return client.responses.submit_tool_outputs(
            response_id=getattr(response, "id"),
            tool_outputs=outputs,
        )
    except Exception as exc:  # pragma: no cover - network errors
        raise VexaAssistantError(f"submit_tool_outputs_failed: {exc}") from exc


def _wait_for_response_completion(client: OpenAI, response: Any) -> Any:
    poll_interval = 0.5
    max_wait = 90
    waited = 0.0

    current = response
    while True:
        status = getattr(current, "status", None)
        if status in {None, "completed"}:
            return current
        if status == "requires_action":
            current = _handle_response_requires_action(client, current)
            waited = 0.0
            continue
        if status in {"failed", "cancelled", "expired"}:
            error = getattr(current, "last_error", None)
            message = "response_failed"
            if error is not None:
                error_dict = _to_dict(error)
                message = error_dict.get("message") or error_dict.get("code") or message
            raise VexaAssistantError(message)

        time.sleep(poll_interval)
        waited += poll_interval
        if waited >= max_wait:
            raise VexaAssistantError("response_timeout")
        try:
            current = client.responses.retrieve(getattr(current, "id"))
        except Exception as exc:  # pragma: no cover - network errors
            raise VexaAssistantError(f"response_retrieve_failed: {exc}") from exc


def _wait_for_run_completion(client: OpenAI, thread_id: str, run: Any) -> str:
    poll_interval = 0.5
    max_wait = 90
    waited = 0.0

    current_run = run
    while True:
        status = getattr(current_run, "status", None)
        if status == "completed":
            return _latest_assistant_message(client, thread_id)
        if status == "requires_action":
            current_run = _handle_requires_action(client, thread_id, current_run)
            waited = 0.0
            continue
        if status in {"failed", "cancelled", "expired"}:
            error = getattr(current_run, "last_error", None)
            message = "run_failed"
            if error is not None:
                error_dict = _to_dict(error)
                message = error_dict.get("message") or error_dict.get("code") or message
            raise VexaAssistantError(message)

        time.sleep(poll_interval)
        waited += poll_interval
        if waited >= max_wait:
            raise VexaAssistantError("run_timeout")
        try:
            current_run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=getattr(current_run, "id"),
            )
        except Exception as exc:  # pragma: no cover - network errors
            raise VexaAssistantError(f"run_retrieve_failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def request_response(history: List[Dict[str, Any]]) -> str:
    """Send the conversation to the Vexa Assistant and return the answer text."""

    ok, error = ensure_ready()
    if not ok:
        raise VexaAssistantError(error or "not_configured")

    messages = prepare_messages(history)
    api_key = resolve_api_key()
    client = _build_client(api_key)

    assistant_id = (VEXA_ASSISTANT_ID or "").strip()
    model_override = (VEXA_ASSISTANT_MODEL or "").strip()

    if not assistant_id:
        try:
            response = client.responses.create(
                model=model_override or "gpt-4o-mini",
                messages=messages,
                tools=_RESPONSE_TOOLS,
            )
        except Exception as exc:  # pragma: no cover - network errors
            raise VexaAssistantError(f"request_failed: {exc}") from exc
        response = _wait_for_response_completion(client, response)
        answer = _extract_output_text(response)
        return answer.strip()

    try:
        thread = client.beta.threads.create(messages=messages)
    except Exception as exc:  # pragma: no cover - network errors
        raise VexaAssistantError(f"thread_create_failed: {exc}") from exc

    try:
        run_kwargs: Dict[str, Any] = {"thread_id": thread.id, "assistant_id": assistant_id}
        if model_override:
            run_kwargs["model"] = model_override
        run = client.beta.threads.runs.create(**run_kwargs)
    except Exception as exc:  # pragma: no cover - network errors
        raise VexaAssistantError(f"run_create_failed: {exc}") from exc

    answer = _wait_for_run_completion(client, thread.id, run)
    return answer.strip()


__all__ = [
    "VexaAssistantError",
    "ensure_ready",
    "prepare_messages",
    "request_response",
]
