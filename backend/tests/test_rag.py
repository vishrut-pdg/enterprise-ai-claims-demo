import pytest
from sqlalchemy import select

from app.assessment.service import DomainError
from app.db.models import PolicyChunk
from app.rag.index import index_policy
from app.rag.service import PolicyRetrieval


@pytest.mark.asyncio
async def test_index_and_retrieve_scoped_passages(service, settings):
    settings.embedding_provider = "mock"
    settings.rag_enabled = True
    text = "# Policy\n\n## Receipts and evidence\nA verified receipt linked to every expense line is required.\n\n## Categories\nMeals travel and supplies are eligible."
    session = service.repo.session
    assert await index_policy(session, settings, text) == 2
    assert await index_policy(session, settings, text) == 2
    assert len(list(session.scalars(select(PolicyChunk)))) == 2
    passages = await PolicyRetrieval(session, settings).retrieve(
        "missing verified receipt evidence", ["expense-policy"]
    )
    assert passages[0]["heading"] == "Receipts and evidence"
    assert all(p["policy_id"] == "expense-policy" for p in passages)
    assert service.claim("CLM-001").status == "submitted"
    with pytest.raises(DomainError):
        await PolicyRetrieval(session, settings).retrieve("receipt", ["another-policy"])


@pytest.mark.asyncio
async def test_model_mismatch_requires_reindex(service, settings):
    settings.embedding_provider = "mock"
    await index_policy(
        service.repo.session,
        settings,
        "# Policy\n\n## Receipts\nVerified receipt required.",
    )
    settings.rag_enabled = True
    settings.embedding_model = "different-model"
    with pytest.raises(DomainError):
        await PolicyRetrieval(service.repo.session, settings).retrieve(
            "receipt", ["expense-policy"]
        )


@pytest.mark.asyncio
async def test_assessment_receives_policy_passages(service, settings):
    from app.ai.providers.mock import MockProvider
    from app.workflows.process_claim import process_claim

    settings.embedding_provider = "mock"
    settings.rag_enabled = True
    await index_policy(
        service.repo.session,
        settings,
        "# Policy\n\n## Receipts\nVerified receipts required for every line.",
    )

    class CapturingProvider(MockProvider):
        async def generate(self, request):
            assert (
                request.context["policy_passages"][0]["source"]
                == "docs/policies/README.md"
            )
            return await super().generate(request)

    result = await process_claim(
        service,
        "CLM-001",
        service.claim("CLM-001").version,
        settings,
        provider=CapturingProvider(),
    )
    assert result["status"] == "pending_manager_review"


@pytest.mark.asyncio
async def test_chat_receives_policy_passages(service, settings):
    from app.ai.providers.mock import MockProvider
    from app.assistant.schemas import ChatRequest
    from app.assistant.service import AssistantService

    settings.embedding_provider = "mock"
    settings.rag_enabled = True
    await index_policy(
        service.repo.session,
        settings,
        "# Policy\n\n## Receipts\nVerified receipts required for every line.",
    )

    class CapturingProvider(MockProvider):
        async def generate(self, request):
            assert request.context["policy_passages"][0]["heading"] == "Receipts"
            assert (
                "policy:expense:v1:1"
                in request.response_schema["properties"]["sources"]["items"]["enum"]
            )
            return await super().generate(request)

    answer = await AssistantService(service, settings, CapturingProvider()).answer(
        ChatRequest(message="Do I need a receipt?", claim_id="CLM-003"), "rag-chat-test"
    )
    assert answer["read_only"]
    assert service.claim("CLM-003").status == "submitted"
