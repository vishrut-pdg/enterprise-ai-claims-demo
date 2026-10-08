"""Embedding adapters; Vertex uses ADC, mock is only for offline tests."""

import asyncio
import hashlib
import math
import re


class Embeddings:
    def __init__(self, settings):
        self.settings = settings
        self.identity = f"{settings.embedding_provider}:{settings.embedding_model}:768"

    async def embed(self, text, document=False):
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
        if len(vector) != 768 or not all(math.isfinite(v) for v in vector):
            raise ValueError("Invalid embedding")
        norm = math.sqrt(sum(v * v for v in vector))
        if not norm:
            raise ValueError("Empty embedding")
        return [v / norm for v in vector]
