"""Measured AI generation, chatbot and embedding requests."""

from alembic import op

from app.db.models import AIUsageEvent

revision = "20261009_ai_usage"
down_revision = "20261008_policy_vectors"
branch_labels = None
depends_on = None


def upgrade():
    AIUsageEvent.__table__.create(op.get_bind())


def downgrade():
    AIUsageEvent.__table__.drop(op.get_bind())
