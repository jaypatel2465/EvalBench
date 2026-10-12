from __future__ import annotations

import asyncio
import hashlib
import time

from app.schemas.domain import GenerationRequest, GenerationResult


class OfflineMockProvider:
    """Deterministic test/demo provider. Never registered as a production provider."""
    name = "mock"
    is_mock = True

    def __init__(self, model: str = "mock-sec-qa-v1", degraded: bool = False, latency_ms: float = 2) -> None:
        self.model, self.degraded, self.simulated_latency_ms = model, degraded, latency_ms

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        started = time.perf_counter()
        await asyncio.sleep(self.simulated_latency_ms / 1000)
        facts = [str(item) for item in request.metadata.get("required_facts", [])]
        expected_citations = [str(item) for item in request.metadata.get("expected_citations", [])]
        category, case_id = request.metadata.get("category"), str(request.metadata.get("case_id", ""))
        should_degrade = self.degraded and int(hashlib.sha256(case_id.encode()).hexdigest()[:2], 16) % 4 == 0
        if category == "refusal":
            response = "The supplied filing does not state that claim, so I cannot support it."
        elif should_degrade:
            response = "The filing does not provide enough information to answer."
        else:
            response = "; ".join(facts) if facts else str(request.metadata.get("reference_answer", ""))
        citations = [] if should_degrade else [{"source_id": item, "quote": "Offline demo citation"} for item in expected_citations]
        input_tokens, output_tokens = len(request.prompt.split()), len(response.split())
        return GenerationResult(response=response, model=self.model, provider=self.name, latency_ms=(time.perf_counter() - started) * 1000,
            input_tokens=input_tokens, output_tokens=output_tokens, total_tokens=input_tokens + output_tokens, estimated_cost=0.0,
            cost_is_estimate=False, finish_reason="stop", citations=citations,
            trace={"mode": "Mock Provider / Offline Demo", "degraded": self.degraded, "tokenizer": "whitespace-v1"})
