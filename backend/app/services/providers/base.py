from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.domain import GenerationRequest, GenerationResult


@runtime_checkable
class ModelProvider(Protocol):
    name: str
    model: str
    is_mock: bool

    async def generate(self, request: GenerationRequest) -> GenerationResult: ...


class ProviderError(RuntimeError):
    def __init__(self, provider: str, message: str, *, retryable: bool = False, status_code: int | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable
        self.status_code = status_code

