from typing import Protocol

from app.ai.models import LLMRequest, LLMResponse


class LLMProvider(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse: ...
    async def health(self) -> bool: ...
