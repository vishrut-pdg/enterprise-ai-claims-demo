"""Policy passages and PostgreSQL vector embeddings."""

from alembic import op

from app.db.models import PolicyChunk

revision = "20261008_policy_vectors"
down_revision = "f325207d03fe"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    PolicyChunk.__table__.create(bind)


def downgrade():
    PolicyChunk.__table__.drop(op.get_bind())
