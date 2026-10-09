"""Embedding adapters; Vertex uses ADC, mock is only for offline tests."""

import asyncio
import hashlib
import math
import re

from app.analytics.metering import measured


class Embeddings:
    def __init__(self, settings, usage_session=None, claim_id=None):
        self.settings = settings
        self.usage_session = usage_session
        self.claim_id = claim_id
        self.identity = f"{settings.embedding_provider}:{settings.embedding_model}:768"

    async def embed(self, text, document=False):
        with measured(
            self.usage_session,
            self.settings,
            "embedding_document" if document else "embedding_query",
            self.settings.embedding_provider,
            self.settings.embedding_model,
            claim_id=self.claim_id,
        ) as measurement:
            return await self._embed(text, document, measurement)

    async def _embed(self, text, document, measurement):
        if self.settings.embedding_provider == "mock":
            vector = [0.0] * 768
            for token in re.findall(r"[a-z0-9]+", text.lower()):
                index = int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % 768
                vector[index] += 1
        else:
            from google import genai
            from google.genai import types

            with genai.Client(
                vertexai=True,
                project=self.settings.gcp_project_id,
                location=self.settings.embedding_location,
            ) as client:
                response = await asyncio.wait_for(
                    client.aio.models.embed_content(
                        model=self.settings.embedding_model,
                        contents=text,
                        config=types.EmbedContentConfig(
                            output_dimensionality=768,
                            task_type="RETRIEVAL_DOCUMENT"
                            if document
                            else "RETRIEVAL_QUERY",
                        ),
                    ),
                    self.settings.llm_timeout,
                )
                vector = response.embeddings[0].values
                measurement.usage = {
                    "billable_character_count": getattr(
                        response.metadata, "billable_character_count", None
                    ),
                    "input_tokens": getattr(
                        response.embeddings[0].statistics, "token_count", None
                    ),
                    "output_tokens": 0,
                }
        if len(vector) != 768 or not all(math.isfinite(v) for v in vector):
            raise ValueError("Invalid embedding")
        norm = math.sqrt(sum(v * v for v in vector))
        if not norm:
            raise ValueError("Empty embedding")
        return [v / norm for v in vector]
