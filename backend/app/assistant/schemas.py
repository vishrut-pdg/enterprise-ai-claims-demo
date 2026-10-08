from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=6000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    claim_id: str | None = Field(default=None, max_length=64)
    history: list[ChatTurn] = Field(default_factory=list, max_length=8)

    @field_validator("message")
    @classmethod
    def trim_message(cls, value):
        if not value.strip():
            raise ValueError("Enter a question")
        return value.strip()


class ChatAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    answer: str = Field(min_length=1, max_length=6000)
    sources: list[str]
