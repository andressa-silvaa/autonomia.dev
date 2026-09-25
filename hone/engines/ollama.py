from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

AVAILABILITY_TIMEOUT_SECONDS = 2
JSON_CONTENT_TYPE = "application/json"
HTTP_NOT_FOUND = 404


class OllamaUnavailableError(Exception):
    def __init__(self, base_url: str) -> None:
        super().__init__(f"Ollama is not answering at {base_url}")
        self.base_url = base_url


class OllamaModelMissingError(Exception):
    def __init__(self, model: str) -> None:
        super().__init__(f"Ollama model {model!r} is not installed")
        self.model = model


class OllamaResponseError(Exception):
    pass


def _request_json(url: str, payload: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": JSON_CONTENT_TYPE},
        method="POST" if data else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def installed_models(base_url: str) -> list[str]:
    try:
        body = _request_json(f"{base_url}/api/tags", None, AVAILABILITY_TIMEOUT_SECONDS)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise OllamaUnavailableError(base_url) from exc
    return [model.get("name", "") for model in body.get("models", [])]


def ensure_model(base_url: str, model: str) -> None:
    names = installed_models(base_url)
    if model not in names and f"{model}:latest" not in names:
        raise OllamaModelMissingError(model)


def chat_json(
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "stream": False,
        "format": schema,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    try:
        body = _request_json(f"{base_url}/api/chat", payload, timeout)
    except urllib.error.HTTPError as exc:
        if exc.code == HTTP_NOT_FOUND:
            raise OllamaModelMissingError(model) from exc
        raise OllamaResponseError(f"Ollama answered HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise OllamaUnavailableError(base_url) from exc

    try:
        return json.loads(body["message"]["content"])
    except (KeyError, TypeError, ValueError) as exc:
        raise OllamaResponseError(
            "Ollama returned something that is not the expected JSON"
        ) from exc
