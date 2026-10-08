import json

import httpx

from app.ai.models import LLMRequest, LLMResponse, ProviderError


class OllamaProvider:
    def __init__(self, settings):
        self.settings = settings

    async def health(self):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(self.settings.ollama_base_url + "/api/tags")
                return response.is_success
        except httpx.HTTPError:
            return False

    async def generate(self, request: LLMRequest) -> LLMResponse:
        try:
            async with httpx.AsyncClient(timeout=self.settings.llm_timeout) as client:
                response = await client.post(
                    self.settings.ollama_base_url + "/api/chat",
                    json={
                        "model": request.model,
                        "stream": False,
                        "format": request.response_schema,
                        "options": {"temperature": 0},
                        "messages": [
                            {"role": "system", "content": request.system},
                            {"role": "user", "content": json.dumps(request.context)},
                        ],
                    },
                )
                response.raise_for_status()
                data = response.json()
                return LLMResponse(
                    content=data["message"]["content"],
                    provider="ollama",
                    model=request.model,
                    usage={
                        k: data[k]
                        for k in ("prompt_eval_count", "eval_count")
                        if k in data
                    },
                )
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ProviderError("Ollama request failed") from exc
