from __future__ import annotations

import hashlib
from functools import lru_cache
import math
import re

FALLBACK_VECTOR_SIZE = 256


class EmbeddingService:
    @lru_cache(maxsize=1024)
    def embed_text(self, text: str) -> tuple[float, ...]:
        normalized = text.strip()
        if not normalized:
            return tuple([0.0] * FALLBACK_VECTOR_SIZE)

        return tuple(_build_local_semantic_embedding(normalized))

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [list(self.embed_text(text)) for text in texts]


def _build_local_semantic_embedding(text: str) -> list[float]:
    vector = [0.0] * FALLBACK_VECTOR_SIZE
    tokens = _tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % FALLBACK_VECTOR_SIZE
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    base_tokens = re.findall(r"[a-z0-9]+", lowered)
    weighted_tokens: list[str] = []
    for token in base_tokens:
        weighted_tokens.append(token)
        if token.isdigit():
            weighted_tokens.extend([f"num_{len(token)}", token[-2:]])
        elif len(token) > 4:
            weighted_tokens.append(token[:4])
            weighted_tokens.append(token[-4:])
    return weighted_tokens
