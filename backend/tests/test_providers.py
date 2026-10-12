import pytest

from app.schemas.domain import GenerationRequest
from app.services.providers.base import ProviderError
from app.services.providers.http import HTTPModelProvider
from app.services.providers.mock import OfflineMockProvider


@pytest.mark.asyncio
async def test_mock_provider_is_deterministic_and_labeled():
    provider = OfflineMockProvider(latency_ms=0)
    request = GenerationRequest(prompt="question", metadata={"case_id": "sec-1", "required_facts": ["Fact"], "expected_citations": ["doc"]})
    first, second = await provider.generate(request), await provider.generate(request)
    assert first.response == second.response == "Fact"
    assert first.trace["mode"] == "Mock Provider / Offline Demo"
    assert first.estimated_cost == 0 and first.cost_is_estimate is False


@pytest.mark.asyncio
async def test_unconfigured_hosted_provider_fails_explicitly():
    provider = HTTPModelProvider(name="openai", model="test", base_url="https://example.invalid")
    with pytest.raises(ProviderError, match="not configured"):
        await provider.generate(GenerationRequest(prompt="hello"))

