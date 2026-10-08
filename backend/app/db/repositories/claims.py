from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models as m


class ClaimRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_claim(self, claim_id, lock=False):
        stmt = (
            select(m.Claim)
            .where(m.Claim.id == claim_id)
            .execution_options(populate_existing=True)
        )
        return self.session.scalar(stmt.with_for_update() if lock else stmt)

    def list_claims(self):
        return list(self.session.scalars(select(m.Claim).order_by(m.Claim.id)))

    def get(self, model, entity_id):
        return self.session.get(model, entity_id, populate_existing=True)

    def related(self, model, claim_id):
        return list(
            self.session.scalars(
                select(model)
                .where(model.claim_id == claim_id)
                .order_by(model.id)
                .execution_options(populate_existing=True)
            )
        )

    def rules(self, policy_id):
        return list(
            self.session.scalars(
                select(m.PolicyRule)
                .where(m.PolicyRule.policy_id == policy_id)
                .order_by(m.PolicyRule.code)
                .execution_options(populate_existing=True)
            )
        )

    def latest_assessment(self, claim_id):
        return self.session.scalar(
            select(m.ClaimAssessment)
            .where(m.ClaimAssessment.claim_id == claim_id)
            .order_by(m.ClaimAssessment.created_at.desc())
            .limit(1)
        )

    def active_review(self, claim_id):
        return self.session.scalar(
            select(m.ReviewTask).where(
                m.ReviewTask.claim_id == claim_id, m.ReviewTask.active.is_(True)
            )
        )

    def reviews(self):
        return list(
            self.session.scalars(
                select(m.ReviewTask).order_by(m.ReviewTask.created_at.desc())
            )
        )

    def review_history(self, review_id):
        return list(
            self.session.scalars(
                select(m.ReviewDecision)
                .where(m.ReviewDecision.review_id == review_id)
                .order_by(m.ReviewDecision.created_at)
            )
        )

    def audit(self, claim_id):
        return list(
            self.session.scalars(
                select(m.AuditEvent)
                .where(m.AuditEvent.claim_id == claim_id)
                .order_by(m.AuditEvent.created_at)
            )
        )

    def duplicates(self, claim_id, fingerprints):
        if not fingerprints:
            return []
        return list(
            self.session.scalars(
                select(m.Evidence).where(
                    m.Evidence.claim_id != claim_id,
                    m.Evidence.fingerprint.in_(fingerprints),
                )
            )
        )

    def find_previous_outcomes(self, category, exclude_claim, reviewed_only=True):
        statement = select(m.OutcomeRecord).where(
            m.OutcomeRecord.category == category,
            m.OutcomeRecord.claim_id != exclude_claim,
        )
        if reviewed_only:
            statement = statement.where(m.OutcomeRecord.reviewed.is_(True))
        return list(
            self.session.scalars(
                statement.order_by(m.OutcomeRecord.created_at.desc()).limit(5)
            )
        )

    def outcome(self, claim_id):
        return self.session.scalar(
            select(m.OutcomeRecord).where(m.OutcomeRecord.claim_id == claim_id)
        )

    def add(self, entity):
        self.session.add(entity)
        return entity

    def flush(self):
        self.session.flush()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
