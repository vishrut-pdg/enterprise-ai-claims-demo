import json

import httpx

from app.ai.models import LLMRequest, LLMResponse, ProviderError


class BTPProvider:
    """SAP AI Core Azure OpenAI deployment adapter (Generative AI Hub).

    Configure AI API base URL, deployment ID and OAuth client credentials.
    Other Hub model families require their own wire format within this adapter.
    """

    def __init__(self, settings):
        self.settings = settings

    async def health(self):
        return all(
            (
                self.settings.btp_ai_base_url,
                self.settings.btp_ai_deployment_id,
                self.settings.btp_token_url,
                self.settings.btp_client_id,
                self.settings.btp_client_secret,
            )
        )

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not await self.health():
            raise ProviderError("BTP deployment credentials are not configured")
        try:
            async with httpx.AsyncClient(timeout=self.settings.llm_timeout) as client:
                token = await client.post(
                    self.settings.btp_token_url,
                    auth=(self.settings.btp_client_id, self.settings.btp_client_secret),
                    data={"grant_type": "client_credentials"},
                )
                token.raise_for_status()
                url = (
                    self.settings.btp_ai_base_url.rstrip("/")
                    + "/v2/inference/deployments/"
                    + self.settings.btp_ai_deployment_id
                    + "/chat/completions"
                )
                response = await client.post(
                    url,
                    params={"api-version": self.settings.btp_api_version},
                    headers={
                        "Authorization": "Bearer " + token.json()["access_token"],
                        "AI-Resource-Group": self.settings.btp_resource_group,
                    },
                    json={
                        "model": request.model,
                        "temperature": 0,
                        "messages": [
                            {
                                "role": "system",
                                "content": request.system
                                + "\nOutput only JSON matching: "
                                + json.dumps(request.response_schema),
                            },
                            {"role": "user", "content": json.dumps(request.context)},
                        ],
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                data = response.json()
                return LLMResponse(
                    content=data["choices"][0]["message"]["content"],
                    provider="btp",
                    model=request.model,
                    usage=data.get("usage", {}),
                )
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ProviderError("BTP inference request failed") from exc
