import json

import pytest

from app.ai.providers.mock import MockProvider
from app.assessment.service import DomainError
from app.db import models as m
from app.workflows.process_claim import process_claim


class ChangedSources(MockProvider):
    def __init__(self, service):
        self.service = service

    async def generate(self, request):
        policy = self.service.repo.get(m.Policy, "expense-policy")
        policy.auto_accept = not policy.auto_accept
        self.service.repo.commit()
        return await super().generate(request)


async def test_sources_changed_during_model_call(service, settings):
    with pytest.raises(DomainError, match="changed"):
        await process_claim(
            service, "CLM-001", 1, settings, provider=ChangedSources(service)
        )
    assert service.detail("CLM-001")["status"] == "submitted"
    assert service.detail("CLM-001")["assessment"] is None


async def test_auto_accept_disabled(service, settings):
    service.repo.get(m.Policy, "expense-policy").auto_accept = False
    service.repo.commit()
    result = await process_claim(service, "CLM-001", 1, settings)
    assert result["status"] == "pending_manager_review"


class UnknownEvidence(MockProvider):
    async def generate(self, request):
        response = await super().generate(request)
        data = json.loads(response.content)
        data["evidence_ids"] = ["invented-receipt"]
        response.content = json.dumps(data)
        return response


async def test_unknown_evidence_fails_safely(service, settings):
    with pytest.raises(DomainError):
        await process_claim(service, "CLM-001", 1, settings, provider=UnknownEvidence())
    assert service.detail("CLM-001")["status"] == "submitted"


class LowConfidence(MockProvider):
    async def generate(self, request):
        response = await super().generate(request)
        data = json.loads(response.content)
        data["confidence"] = 0.3
        response.content = json.dumps(data)
        return response


async def test_low_confidence_requires_human(service, settings):
    result = await process_claim(
        service, "CLM-001", 1, settings, provider=LowConfidence()
    )
    assert result["status"] == "pending_manager_review"
