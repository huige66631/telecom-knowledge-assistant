from __future__ import annotations

import hashlib
import math
import re


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{1,2}")


class LocalEmbeddingFunction:
    """Deterministic local embedding function to avoid a second API dependency."""

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = dimensions

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in input]

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for offset in range(0, 32, 4):
                index = int.from_bytes(digest[offset : offset + 4], "big") % self.dimensions
                sign = 1.0 if digest[offset] % 2 == 0 else -1.0
                vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm > 0:
            vector = [value / norm for value in vector]
        return vector


def build_embedding_function() -> LocalEmbeddingFunction:
    return LocalEmbeddingFunction()
