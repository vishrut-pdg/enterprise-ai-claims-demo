from app.assessment.service import DomainError
from app.rag.embeddings import Embeddings
from app.rag.repository import PolicyRepository


class PolicyRetrieval:
    def __init__(self, session, settings):
        self.session, self.settings = session, settings
        self.embeddings = Embeddings(settings)

    async def retrieve(self, question, policy_ids):
        if not self.settings.rag_enabled:
            return []
        self.session.commit()
        try:
            vector = await self.embeddings.embed(question)
            passages = PolicyRepository(self.session).search(
                policy_ids, self.embeddings.identity, vector
            )
            self.session.commit()
            if not passages:
                raise ValueError("No indexed passages for configured model")
            return passages
        except Exception as exc:
            self.session.rollback()
            raise DomainError(
                "Policy retrieval unavailable. Run the policy index command and check embedding access. No decision was recorded.",
                503,
            ) from exc
