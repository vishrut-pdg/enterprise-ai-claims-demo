from pydantic import BaseModel, Field


class LLMRequest(BaseModel):
    model: str
    system: str
    context: dict
    response_schema: dict
    correlation_id: str


class LLMResponse(BaseModel):
    content: str
    provider: str
    model: str
    usage: dict = Field(default_factory=dict)


class ProviderError(RuntimeError):
    pass
