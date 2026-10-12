from __future__ import annotations

import time
from typing import Any

import httpx

from app.schemas.domain import GenerationRequest, GenerationResult
from app.services.providers.base import ProviderError


class HTTPModelProvider:
    is_mock = False

    def __init__(self, *, name: str, model: str, base_url: str, api_key: str | None = None, timeout: float = 45,
                 input_cost_per_million: float | None = None, output_cost_per_million: float | None = None) -> None:
        self.name, self.model, self.base_url = name, model, base_url.rstrip("/")
        self.api_key, self.timeout = api_key, timeout
        self.input_cost_per_million, self.output_cost_per_million = input_cost_per_million, output_cost_per_million

    def _cost(self, input_tokens: int | None, output_tokens: int | None) -> float | None:
        if input_tokens is None or output_tokens is None or self.input_cost_per_million is None or self.output_cost_per_million is None:
            return None
        return input_tokens * self.input_cost_per_million / 1_000_000 + output_tokens * self.output_cost_per_million / 1_000_000

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if self.name != "ollama" and not self.api_key:
            raise ProviderError(self.name, f"{self.name} is not configured; set its API key", retryable=False)
        started = time.perf_counter()
        headers = {"content-type": "application/json"}
        if self.name == "openai":
            headers["authorization"] = f"Bearer {self.api_key}"
            url = f"{self.base_url}/responses"
            payload = {"model": self.model, "input": request.prompt, "temperature": request.temperature, "max_output_tokens": request.max_tokens}
        elif self.name == "anthropic":
            headers.update({"x-api-key": str(self.api_key), "anthropic-version": "2023-06-01"})
            url = f"{self.base_url}/messages"
            payload = {"model": self.model, "max_tokens": request.max_tokens, "temperature": request.temperature, "messages": [{"role": "user", "content": request.prompt}]}
        elif self.name == "google":
            url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
            payload = {"contents": [{"parts": [{"text": request.prompt}]}], "generationConfig": {"temperature": request.temperature, "maxOutputTokens": request.max_tokens}}
        elif self.name == "ollama":
            url = f"{self.base_url}/api/generate"
            payload = {"model": self.model, "prompt": request.prompt, "stream": False, "options": {"temperature": request.temperature, "num_predict": request.max_tokens}}
        else:
            raise ProviderError(self.name, "unsupported provider", retryable=False)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ProviderError(self.name, f"provider HTTP {status}", retryable=status == 429 or status >= 500, status_code=status) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(self.name, f"provider request failed: {type(exc).__name__}: {exc}", retryable=True) from exc
        latency = (time.perf_counter() - started) * 1000
        text, usage, finish = self._normalize(data)
        input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
        return GenerationResult(response=text, model=self.model, latency_ms=latency, input_tokens=input_tokens,
            output_tokens=output_tokens, total_tokens=(input_tokens + output_tokens) if input_tokens is not None and output_tokens is not None else None,
            estimated_cost=self._cost(input_tokens, output_tokens), cost_is_estimate=True, finish_reason=finish, provider=self.name,
            trace={"provider_request_id": data.get("id")})

    def _normalize(self, data: dict[str, Any]) -> tuple[str, dict[str, int | None], str | None]:
        if self.name == "openai":
            chunks = [part.get("text", "") for item in data.get("output", []) for part in item.get("content", []) if part.get("type") == "output_text"]
            usage = data.get("usage", {})
            return "".join(chunks), {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens")}, data.get("status")
        if self.name == "anthropic":
            usage = data.get("usage", {})
            return "".join(item.get("text", "") for item in data.get("content", []) if item.get("type") == "text"), {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens")}, data.get("stop_reason")
        if self.name == "google":
            candidates = data.get("candidates", [])
            text = "".join(part.get("text", "") for candidate in candidates for part in candidate.get("content", {}).get("parts", []))
            usage = data.get("usageMetadata", {})
            return text, {"input_tokens": usage.get("promptTokenCount"), "output_tokens": usage.get("candidatesTokenCount")}, candidates[0].get("finishReason") if candidates else None
        return data.get("response", ""), {"input_tokens": data.get("prompt_eval_count"), "output_tokens": data.get("eval_count")}, data.get("done_reason")


class TargetAPIProvider:
    """Adapter for any target implementing POST /query."""
    is_mock = False

    def __init__(self, target_url: str, model: str = "external-target", timeout: float = 45) -> None:
        self.name, self.model, self.target_url, self.timeout = "target_api", model, target_url, timeout

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.target_url, json={"question": request.prompt})
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise ProviderError(self.name, f"target request failed: {exc}", retryable=True) from exc
        return GenerationResult(response=data["answer"], model=data.get("model", self.model), provider=self.name,
            latency_ms=float(data.get("latency_ms", (time.perf_counter() - started) * 1000)), input_tokens=data.get("input_tokens"),
            output_tokens=data.get("output_tokens"), total_tokens=data.get("total_tokens"), estimated_cost=data.get("estimated_cost"),
            cost_is_estimate=data.get("cost_is_estimate", True), citations=data.get("citations", []), trace=data.get("trace", {}),
            finish_reason=data.get("finish_reason"))

