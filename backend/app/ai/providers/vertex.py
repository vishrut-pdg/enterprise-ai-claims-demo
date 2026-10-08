import asyncio
import json

from app.ai.models import LLMRequest, LLMResponse, ProviderError


class VertexProvider:
    def __init__(self, settings):
        self.settings = settings

    def client(self):
        from google import genai

        if not self.settings.gcp_project_id:
            raise ProviderError("Vertex project is not configured")
        return genai.Client(
            vertexai=True,
            project=self.settings.gcp_project_id,
            location=self.settings.gcp_location,
        )

    async def health(self):
        # Configuration readiness only; inference permission is verified by generate.
        return bool(self.settings.gcp_project_id and self.settings.gcp_location)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        try:
            from google.genai import types

            with self.client() as client:
                response = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=request.model,
                        contents=json.dumps(request.context),
                        config=types.GenerateContentConfig(
                            system_instruction=request.system,
                            temperature=0,
                            response_mime_type="application/json",
                            response_json_schema=request.response_schema,
                        ),
                    ),
                    timeout=self.settings.llm_timeout,
                )
                return LLMResponse(
                    content=response.text or "",
                    provider="vertex",
                    model=request.model,
                    usage=response.usage_metadata.model_dump(mode="json")
                    if response.usage_metadata
                    else {},
                )
        except Exception as exc:
            raise ProviderError(
                "Vertex request failed; check configuration, ADC and model access"
            ) from exc
