from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.services.providers.base import ModelProvider
from app.services.providers.http import HTTPModelProvider, TargetAPIProvider
from app.services.providers.mock import OfflineMockProvider


def build_provider(config: dict[str, Any], settings: Settings | None = None) -> ModelProvider:
    settings = settings or get_settings()
    provider, model = str(config["provider"]), str(config["model"])
    pricing = config.get("pricing", {})
    if provider == "mock":
        params = config.get("parameters", {})
        return OfflineMockProvider(model, bool(params.get("degraded", False)), float(params.get("latency_ms", 2)))
    if provider == "target_api":
        return TargetAPIProvider(str(config["target_url"]), model, settings.eval_timeout)
    endpoints = {"openai": ("https://api.openai.com/v1", settings.openai_api_key),
                 "anthropic": ("https://api.anthropic.com/v1", settings.anthropic_api_key),
                 "google": ("https://generativelanguage.googleapis.com/v1beta", settings.google_api_key),
                 "ollama": (settings.ollama_base_url, None)}
    if provider not in endpoints:
        raise ValueError(f"unsupported provider: {provider}")
    base_url, key = endpoints[provider]
    return HTTPModelProvider(name=provider, model=model, base_url=str(config.get("base_url", base_url)), api_key=key,
        timeout=settings.eval_timeout, input_cost_per_million=pricing.get("input_per_million"),
        output_cost_per_million=pricing.get("output_per_million"))

