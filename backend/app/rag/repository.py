from sqlalchemy import select

from app.db.models import PolicyChunk


class PolicyRepository:
    def __init__(self, session):
        self.session = session

    def search(self, policy_ids, identity, vector, limit=4):
        statement = select(PolicyChunk).where(
            PolicyChunk.policy_id.in_(policy_ids),
            PolicyChunk.embedding_model == identity,
        )
        if self.session.bind.dialect.name == "postgresql":
            rows = list(
                self.session.scalars(
                    statement.order_by(
                        PolicyChunk.embedding.cosine_distance(vector)
                    ).limit(limit)
                )
            )
        else:
            rows = sorted(
                self.session.scalars(statement),
                key=lambda c: (
                    -sum(a * b for a, b in zip(c.embedding, vector, strict=True))
                ),
            )[:limit]
        return [
            {
                "id": c.id,
                "policy_id": c.policy_id,
                "heading": c.heading,
                "text": c.content,
                "source": c.source,
            }
            for c in rows
        ]
