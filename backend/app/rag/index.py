"""Run python -m app.rag.index to atomically refresh the policy README index."""

import asyncio
import hashlib
import sys
from pathlib import Path

from sqlalchemy import delete, select

from app.config import get_settings
from app.db.models import Policy, PolicyChunk
from app.db.session import SessionLocal
from app.rag.embeddings import Embeddings

POLICY_ID = "expense-policy"
SOURCE = "docs/policies/README.md"


def chunks(text):
    return [
        (section.split("\n", 1)[0].strip(), section.strip())
        for section in text.split("\n## ")[1:]
    ]


async def index_policy(session, settings, text):
    if not session.get(Policy, POLICY_ID):
        raise ValueError("Seed the expense policy first")
    session.commit()
    adapter = Embeddings(settings)
    prepared = []
    for position, (heading, content) in enumerate(chunks(text)):
        prepared.append(
            PolicyChunk(
                id=f"policy:expense:v2:{position + 1}",
                policy_id=POLICY_ID,
                heading=heading,
                content=content,
                source=SOURCE,
                content_hash=hashlib.sha256(content.encode()).hexdigest(),
                embedding_model=adapter.identity,
                embedding=await adapter.embed(content, document=True),
            )
        )
    if not prepared:
        raise ValueError("Policy requires Markdown sections")
    # Only replace after every embedding succeeds; claims/reviews are untouched.
    session.execute(delete(PolicyChunk).where(PolicyChunk.policy_id == POLICY_ID))
    session.add_all(prepared)
    session.commit()
    return len(prepared)


async def main():
    text = (Path(__file__).resolve().parents[3] / SOURCE).read_text()
    with SessionLocal() as session:
        settings = get_settings()
        if "--if-needed" in sys.argv:
            rows = list(
                session.scalars(
                    select(PolicyChunk).where(PolicyChunk.policy_id == POLICY_ID)
                )
            )
            expected = [
                hashlib.sha256(content.encode()).hexdigest()
                for _, content in chunks(text)
            ]
            existing = sorted(rows, key=lambda c: int(c.id.rsplit(":", 1)[1]))
            if (
                expected
                and [c.content_hash for c in existing] == expected
                and all(
                    c.embedding_model == Embeddings(settings).identity for c in existing
                )
            ):
                print("Policy index is up to date")
                return
        count = await index_policy(session, settings, text)
    print(f"Indexed {count} policy passages")


if __name__ == "__main__":
    asyncio.run(main())
