from app.ai.providers.btp_ai import BTPProvider
from app.ai.providers.mock import MockProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.vertex import VertexProvider
from app.config import get_settings


def create_provider(settings=None):
    settings = settings or get_settings()
    if settings.llm_provider == "mock":
        return MockProvider()
    return {"ollama": OllamaProvider, "vertex": VertexProvider, "btp": BTPProvider}[
        settings.llm_provider
    ](settings)
