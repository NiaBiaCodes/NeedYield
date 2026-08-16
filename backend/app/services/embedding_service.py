import hashlib
import math
import os
import re


class EmbeddingService:
    """Gemini embeddings with a deterministic local embedding fallback."""

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.dimension = 768 if self.api_key else 384
        self.provider = "gemini-embedding-001" if self.api_key else "local-hashed-embedding"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.api_key:
            try:
                from google import genai
                from google.genai import types
                client = genai.Client(api_key=self.api_key)
                response = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=texts,
                    config=types.EmbedContentConfig(output_dimensionality=self.dimension),
                )
                return [list(item.values) for item in response.embeddings]
            except Exception:
                self.provider = "local-hashed-embedding"
                self.dimension = 384
        return [self._local_embedding(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def _local_embedding(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        phrases = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for token in phrases:
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


embedding_service = EmbeddingService()
