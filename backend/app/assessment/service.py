import json
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.db import models as m
from app.domain.policy import calculate_checks
from app.telemetry import log, span


class DomainError(Exception):
    def __init__(self, message, status=409):
        self.message, self.status = message, status


def encode(entity):
    if entity is None:
        return None
    result = {}
    for col in entity.__table__.columns:
        value = getattr(entity, col.name)
        if isinstance(value, Decimal):
            value = str(value)
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        result[col.name] = (
            json.loads(json.dumps(value)) if isinstance(value, (dict, list)) else value
        )
    if isinstance(entity, m.OutcomeRecord):
        result.pop(
            "recommendation", None
        )  # Legacy storage field; Week 1 has no AI advice.
    return result


class ClaimService:
    def __init__(self, repository):
        self.repo = repository

    def claim(self, claim_id, lock=False):
        claim = self.repo.get_claim(claim_id, lock)
        if not claim:
            raise DomainError("Claim not found", 404)
        return claim

    def version(self, claim, expected):
        if claim.version != expected:
            raise DomainError("Claim version changed; refresh before retrying")

    def get_claim(self, claim_id):
        claim = self.claim(claim_id)
        return {
            **encode(claim),
            "employee": encode(self.repo.get(m.Employee, claim.employee_id)),
            "lines": [
                encode(line) for line in self.repo.related(m.ClaimLine, claim_id)
            ],
        }

    def get_policy(self, claim_id):
        claim = self.claim(claim_id)
        return {
            **encode(self.repo.get(m.Policy, claim.policy_id)),
            "rules": [encode(r) for r in self.repo.rules(claim.policy_id)],
        }

    def get_evidence(self, claim_id):
        return [encode(e) for e in self.repo.related(m.Evidence, claim_id)]

    def calculate_policy_checks(self, claim_id):
        evidence = self.get_evidence(claim_id)
        duplicates = self.repo.duplicates(
            claim_id, [e["fingerprint"] for e in evidence]
        )
        return [
            f.model_dump()
            for f in calculate_checks(
                self.get_claim(claim_id),
                self.get_policy(claim_id),
                evidence,
                [e.id for e in duplicates],
            )
        ]

    def get_previous_outcomes(self, claim_id):
        claim = self.get_claim(claim_id)
        category = claim["lines"][0]["category"] if claim["lines"] else ""
        return [encode(o) for o in self.repo.find_previous_outcomes(category, claim_id)]

    def audit(self, claim_id, event, actor, run_id, data=None):
        self.repo.add(
            m.AuditEvent(
                claim_id=claim_id,
                event_type=event,
                actor=actor,
                run_id=run_id,
                data=data or {},
            )
        )
        log.info(
            "claim_event",
            claim_id=claim_id,
            event_type=event,
            actor=actor,
            correlation_id=run_id,
        )

    def list_claims(self):
        return [
            {
                **self.get_claim(c.id),
                "assessment": encode(self.repo.latest_assessment(c.id)),
            }
            for c in self.repo.list_claims()
        ]

    def detail(self, claim_id):
        return {
            **self.get_claim(claim_id),
            "policy": self.get_policy(claim_id),
            "evidence": self.get_evidence(claim_id),
            "findings": [
                encode(f) for f in self.repo.related(m.PolicyFinding, claim_id)
            ],
            "assessment": encode(self.repo.latest_assessment(claim_id)),
            "review": encode(self.repo.active_review(claim_id)),
            "history": [encode(a) for a in self.repo.audit(claim_id)],
            "executions": [
                encode(e) for e in self.repo.related(m.AIExecution, claim_id)
            ],
            "outcome": encode(self.repo.outcome(claim_id)),
        }

    async def retrieve_policy(self, context, settings):
        from app.rag.service import PolicyRetrieval

        query = json.dumps(
            {
                "title": context["claim"]["title"],
                "lines": context["claim"]["lines"],
                "checks": context["checks"],
            }
        )
        return await PolicyRetrieval(self.repo.session, settings).retrieve(
            query, [context["policy"]["id"]]
        )

    def prepare(self, claim_id, expected, run_id):
        claim = self.claim(claim_id)
        self.version(claim, expected)
        if claim.status != "submitted":
            raise DomainError("Only submitted claims can be processed")
        # End read transaction before awaiting a model, so current state can be reloaded.
        self.repo.commit()

    def assert_context_current(self, claim_id, context):
        fresh = {
            "claim": self.get_claim(claim_id),
            "policy": self.get_policy(claim_id),
            "evidence": self.get_evidence(claim_id),
            "checks": self.calculate_policy_checks(claim_id),
        }
        original = {key: context[key] for key in fresh}
        if json.dumps(fresh, sort_keys=True) != json.dumps(original, sort_keys=True):
            raise DomainError(
                "Claim, policy or evidence changed; reassessment required"
            )

    def record_context(self, claim_id, expected, context, run_id):
        claim = self.claim(claim_id, lock=True)
        self.version(claim, expected)
        self.assert_context_current(claim_id, context)
        for event in (
            "claim_loaded",
            "policy_selected",
            "evidence_retrieved",
            "checks_executed",
            "ai_summary_requested",
        ):
            self.audit(
                claim_id,
                event,
                "claim_agent",
                run_id,
                {
                    "claim_version": expected,
                    "policy_id": context["policy"]["id"],
                    "evidence_ids": [e["id"] for e in context["evidence"]],
                    **(
                        {"policy_passages": context.get("policy_passages", [])}
                        if event == "ai_summary_requested"
                        else {}
                    ),
                },
            )
        for finding in context["checks"]:
            self.repo.add(
                m.PolicyFinding(claim_id=claim_id, claim_version=expected, **finding)
            )
        self.repo.commit()

    def failure(self, claim_id, run_id, settings, duration, error, trajectory):
        self.repo.rollback()
        self.repo.add(
            m.AIExecution(
                claim_id=claim_id,
                run_id=run_id,
                provider=settings.llm_provider,
                model=settings.llm_model,
                status="failed",
                duration_ms=duration,
                error_code=type(error).__name__,
                trajectory=trajectory,
            )
        )
        self.audit(
            claim_id,
            "processing_failed",
            "system",
            run_id,
            {"error_code": type(error).__name__},
        )
        self.repo.commit()

    def finish(
        self,
        claim_id,
        expected,
        assessment,
        response,
        run_id,
        duration,
        trajectory,
        context,
    ):
        with span("service.controlled_action", run_id):
            claim = self.claim(claim_id, lock=True)
            self.version(claim, expected)
            if claim.status != "submitted":
                raise DomainError("Claim has already been processed")
            self.assert_context_current(claim_id, context)
            checks = self.calculate_policy_checks(claim_id)
            evidence = self.get_evidence(claim_id)
            current_codes = {f["code"] for f in checks}
            if not set(assessment.findings) <= current_codes or not set(
                assessment.evidence_ids
            ) <= {e["id"] for e in evidence}:
                raise DomainError("Assessment sources changed; reassessment required")
            saved = self.repo.add(
                m.ClaimAssessment(
                    claim_id=claim_id,
                    claim_version=expected,
                    run_id=run_id,
                    data=assessment.model_dump(),
                )
            )
            self.repo.flush()
            self.audit(
                claim_id,
                "ai_summary_validated",
                "system",
                run_id,
                {"assessment_id": saved.id},
            )
            self.audit(
                claim_id,
                "facts_summarized",
                "claim_agent",
                run_id,
                {"summary_id": saved.id},
            )
            self.create_review_task(claim, saved, assessment, run_id)
            trajectory.append("create_review_task")
            self.repo.add(
                m.AIExecution(
                    claim_id=claim_id,
                    run_id=run_id,
                    provider=response.provider,
                    model=response.model,
                    status="succeeded",
                    duration_ms=duration,
                    usage=response.usage,
                    trajectory=list(trajectory),
                )
            )
            try:
                self.repo.commit()
            except (StaleDataError, IntegrityError) as exc:
                self.repo.rollback()
                raise DomainError(
                    "Concurrent processing conflict; refresh claim"
                ) from exc
            return self.detail(claim_id)

    def create_review_task(self, claim, saved, assessment, run_id):
        task = self.repo.active_review(claim.id)
        if not task:
            task = self.repo.add(
                m.ReviewTask(
                    claim_id=claim.id,
                    assessment_id=saved.id,
                    reason="Manager approval is required for every expense claim. "
                    + assessment.summary,
                    evidence_ids=assessment.evidence_ids,
                    unresolved_questions=assessment.unresolved_questions,
                )
            )
        claim.status = "pending_manager_review"
        self.repo.flush()
        self.audit(
            claim.id,
            "manager_review_created",
            "system",
            run_id,
            {"review_id": task.id, "evidence_ids": assessment.evidence_ids},
        )
        return task

    def capture_outcome(self, claim, assessment, rationale, reviewed):
        context = self.get_claim(claim.id)
        self.repo.add(
            m.OutcomeRecord(
                claim_id=claim.id,
                category=context["lines"][0]["category"] if context["lines"] else "",
                reviewed=reviewed,
                context=context,
                findings=self.calculate_policy_checks(claim.id),
                recommendation="not_applicable",
                final_decision=claim.status,
                reviewer_rationale=rationale,
                evidence_ids=assessment.evidence_ids,
            )
        )

    def list_reviews(self):
        return [
            {**encode(r), "claim": self.get_claim(r.claim_id)}
            for r in self.repo.reviews()
        ]

    def review_detail(self, review_id):
        task = self.repo.get(m.ReviewTask, review_id)
        if not task:
            raise DomainError("Review not found", 404)
        return {
            **encode(task),
            "claim": self.detail(task.claim_id),
            "decisions": [encode(d) for d in self.repo.review_history(review_id)],
        }

    def manager_decision(self, review_id, request, actor, run_id):
        task = self.repo.get(m.ReviewTask, review_id)
        if not task:
            raise DomainError("Review not found", 404)
        claim = self.claim(task.claim_id, lock=True)
        # Refresh task after acquiring claim lock.
        task = self.repo.get(m.ReviewTask, review_id)
        self.version(claim, request.expected_version)
        if not task.active or claim.status not in (
            "pending_manager_review",
            "under_investigation",
        ):
            raise DomainError("Review is already closed")
        self.repo.add(
            m.ReviewDecision(
                review_id=review_id,
                actor=actor,
                decision=request.decision,
                rationale=request.rationale.strip(),
            )
        )
        previous = claim.status
        # Advance the version for every manager action, including a repeated investigation.
        claim.version += 1
        if request.decision == "investigate":
            task.status = "under_investigation"
            claim.status = "under_investigation"
        else:
            task.active = False
            task.status = "closed"
            claim.status = "accepted" if request.decision == "accept" else "rejected"
            from app.schemas.assessment import Assessment

            assessment = Assessment.model_validate(
                self.repo.get(m.ClaimAssessment, task.assessment_id).data
            )
            self.capture_outcome(claim, assessment, request.rationale, True)
        self.audit(
            claim.id,
            "manager_decision_recorded",
            actor,
            run_id,
            {
                "review_id": review_id,
                "decision": request.decision,
                "previous": previous,
                "result": claim.status,
            },
        )
        try:
            self.repo.commit()
        except (StaleDataError, IntegrityError) as exc:
            self.repo.rollback()
            raise DomainError("Concurrent review conflict") from exc
        return self.review_detail(review_id)
