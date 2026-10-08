import json

import httpx
import pytest

from app.ai.models import LLMRequest
from app.ai.providers.btp_ai import BTPProvider
from app.ai.providers.ollama import OllamaProvider
from app.config import Settings


@pytest.mark.parametrize("kind", ["ollama", "btp"])
async def test_http_provider_contract(monkeypatch, kind):
    calls = []

    def handler(request):
        calls.append(request)
        if str(request.url) == "https://auth.test/token":
            return httpx.Response(200, json={"access_token": "test-token"})
        if kind == "ollama":
            payload = json.loads(request.content)
            assert not payload["stream"] and payload["format"] == {"type": "object"}
            return httpx.Response(
                200, json={"message": {"content": '{"ok":true}'}, "eval_count": 2}
            )
        assert request.headers["AI-Resource-Group"] == "default"
        assert request.headers["Authorization"] == "Bearer test-token"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"ok":true}'}}],
                "usage": {"total_tokens": 3},
            },
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    settings = Settings(
        ollama_base_url="https://ollama.test",
        btp_ai_base_url="https://ai.test",
        btp_ai_deployment_id="deployment",
        btp_token_url="https://auth.test/token",
        btp_client_id="client",
        btp_client_secret="secret",
        _env_file=None,
    )
    provider = OllamaProvider(settings) if kind == "ollama" else BTPProvider(settings)
    result = await provider.generate(
        LLMRequest(
            model="test-model",
            system="Test",
            context={},
            response_schema={"type": "object"},
            correlation_id="test",
        )
    )
    assert (
        result.provider == kind
        and result.model == "test-model"
        and json.loads(result.content) == {"ok": True}
    )


async def test_vertex_contract(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.ai.models import LLMResponse
    from app.ai.providers.vertex import VertexProvider

    generate = AsyncMock(
        return_value=SimpleNamespace(text='{"ok":true}', usage_metadata=None)
    )

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        aio = SimpleNamespace(models=SimpleNamespace(generate_content=generate))

    provider = VertexProvider(Settings(gcp_project_id="test", _env_file=None))
    monkeypatch.setattr(provider, "client", lambda: Client())
    response = await provider.generate(
        LLMRequest(
            model="model",
            system="Instructions",
            context={"grounded": True},
            response_schema={"type": "object"},
            correlation_id="test",
        )
    )
    assert isinstance(response, LLMResponse)
    assert response.provider == "vertex" and response.content == '{"ok":true}'
    assert generate.call_args.kwargs["config"].response_mime_type == "application/json"
