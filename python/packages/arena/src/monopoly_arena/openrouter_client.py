from __future__ import annotations

import asyncio
import json
import os
import random
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(slots=True)
class OpenRouterResult:
    ok: bool
    status_code: int | None
    response_json: dict[str, Any] | None
    error: str | None
    error_type: str | None
    request_id: str | None


class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_s: float = 30.0,
        max_retries: int = 2,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._extra_headers = extra_headers or {}
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout_s))
        self._rng = random.Random(0)

    def _backoff_delay(self, attempt: int) -> float:
        base = 0.5
        jitter = self._rng.random() * 0.1
        return base * (2**attempt) + jitter

    async def create_chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> OpenRouterResult:
        if not self._api_key:
            return OpenRouterResult(
                ok=False,
                status_code=None,
                response_json=None,
                error="OPENROUTER_API_KEY not set",
                error_type="no_api_key",
                request_id=None,
            )

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools is not None:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            **self._extra_headers,
        }
        url = f"{self._base_url}/chat/completions"
        last_error: OpenRouterResult | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(url, headers=headers, json=payload)
                request_id = response.headers.get("x-request-id") or response.headers.get("openrouter-request-id")
                if response.status_code >= 400:
                    status_code = response.status_code
                    if status_code == 429:
                        error_type = "http_429"
                        retryable = True
                    elif 500 <= status_code < 600:
                        error_type = "http_5xx"
                        retryable = True
                    else:
                        error_type = "http_4xx"
                        retryable = False
                    if retryable and attempt < self._max_retries:
                        await asyncio.sleep(self._backoff_delay(attempt))
                        continue
                    error_text = response.text.strip()
                    return OpenRouterResult(
                        ok=False,
                        status_code=status_code,
                        response_json=None,
                        error=error_text or f"HTTP {status_code}",
                        error_type=error_type,
                        request_id=request_id,
                    )
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    return OpenRouterResult(
                        ok=False,
                        status_code=response.status_code,
                        response_json=None,
                        error="Invalid JSON response from OpenRouter",
                        error_type="invalid_json",
                        request_id=request_id,
                    )
                if request_id is None:
                    request_id = data.get("id")
                return OpenRouterResult(
                    ok=True,
                    status_code=response.status_code,
                    response_json=data,
                    error=None,
                    error_type=None,
                    request_id=request_id,
                )
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_error = OpenRouterResult(
                    ok=False,
                    status_code=None,
                    response_json=None,
                    error=str(exc),
                    error_type="network_error",
                    request_id=None,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(self._backoff_delay(attempt))
                    continue
                return last_error

        return last_error or OpenRouterResult(
            ok=False,
            status_code=None,
            response_json=None,
            error="OpenRouter request failed",
            error_type="unknown",
            request_id=None,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
