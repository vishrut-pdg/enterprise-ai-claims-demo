from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid():
    return str(uuid4())


def now():
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Identity:
    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=uid)


class Timestamp:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Employee(Identity, Base):
    __tablename__ = "employees"
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    department: Mapped[str] = mapped_column(String(100))


class Policy(Identity, Base):
    __tablename__ = "policies"
    name: Mapped[str] = mapped_column(String(160))
    text: Mapped[str] = mapped_column(Text)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    auto_accept: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_reject: Mapped[bool] = mapped_column(Boolean, default=True)


class PolicyRule(Identity, Base):
    __tablename__ = "policy_rules"
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"))
    code: Mapped[str] = mapped_column(String(64))
    parameters: Mapped[dict] = mapped_column(JSON)


class Claim(Identity, Timestamp, Base):
    __tablename__ = "claims"
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"))
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"))
    title: Mapped[str] = mapped_column(String(200))
    claim_type: Mapped[str] = mapped_column(String(80), default="expense")
    submitted_date: Mapped[date] = mapped_column(Date, default=date.today)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(40), default="submitted")
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}


class ClaimLine(Identity, Base):
    __tablename__ = "claim_lines"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(200))
    expense_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class Evidence(Identity, Base):
    __tablename__ = "evidence"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    line_id: Mapped[str | None] = mapped_column(
        ForeignKey("claim_lines.id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(128), index=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=True)


class PolicyFinding(Identity, Timestamp, Base):
    __tablename__ = "policy_findings"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    claim_version: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)


class ClaimAssessment(Identity, Timestamp, Base):
    __tablename__ = "claim_assessments"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    claim_version: Mapped[int] = mapped_column(Integer)
    run_id: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(JSON)


class ReviewTask(Identity, Timestamp, Base):
    __tablename__ = "review_tasks"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    assessment_id: Mapped[str] = mapped_column(ForeignKey("claim_assessments.id"))
    status: Mapped[str] = mapped_column(String(40), default="open")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_role: Mapped[str] = mapped_column(String(40), default="manager")
    reason: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list] = mapped_column(JSON)
    unresolved_questions: Mapped[list] = mapped_column(JSON)
    __table_args__ = (
        Index(
            "uq_active_review_claim",
            "claim_id",
            unique=True,
            postgresql_where=text("active = true"),
            sqlite_where=text("active = 1"),
        ),
    )


class ReviewDecision(Identity, Timestamp, Base):
    __tablename__ = "review_decisions"
    review_id: Mapped[str] = mapped_column(ForeignKey("review_tasks.id"))
    actor: Mapped[str] = mapped_column(String(100))
    decision: Mapped[str] = mapped_column(String(40))
    rationale: Mapped[str] = mapped_column(Text)


class AuditEvent(Identity, Timestamp, Base):
    __tablename__ = "audit_events"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(100))
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class AIExecution(Identity, Timestamp, Base):
    __tablename__ = "ai_executions"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"))
    run_id: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40))
    duration_ms: Mapped[int] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    usage: Mapped[dict] = mapped_column(JSON, default=dict)
    trajectory: Mapped[list] = mapped_column(JSON, default=list)


class OutcomeRecord(Identity, Timestamp, Base):
    __tablename__ = "outcome_records"
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), unique=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    reviewed: Mapped[bool] = mapped_column(Boolean)
    context: Mapped[dict] = mapped_column(JSON)
    findings: Mapped[list] = mapped_column(JSON)
    recommendation: Mapped[str] = mapped_column(String(40))
    final_decision: Mapped[str] = mapped_column(String(40))
    reviewer_rationale: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list] = mapped_column(JSON)


class PolicyChunk(Identity, Base):
    __tablename__ = "policy_chunks"
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"), index=True)
    heading: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(200))
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding_model: Mapped[str] = mapped_column(String(200))
    embedding: Mapped[list] = mapped_column(Vector(768).with_variant(JSON(), "sqlite"))
