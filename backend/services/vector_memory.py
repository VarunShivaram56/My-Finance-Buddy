from __future__ import annotations

import uuid
import logging

import chromadb

from rag.embeddings import EmbeddingService
from utils.config import settings


logger = logging.getLogger(__name__)


class VectorMerchantMemory:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient(path=settings.chroma_dir)
        self.collection = self.client.get_or_create_collection(name="merchant_categories")
        self.embedding_service = EmbeddingService()
        self.available = settings.enable_vector_memory

    def remember(self, merchant: str, category: str) -> None:
        if not self.available:
            return
        try:
            embeddings = self.embedding_service.embed_many([merchant])
            self.collection.upsert(
                ids=[str(uuid.uuid4())],
                documents=[merchant],
                embeddings=embeddings,
                metadatas=[{"category": category}],
            )
        except Exception as exc:
            self.available = False
            logger.warning("Disabling vector memory after embedding failure: %s", exc)

    def lookup(self, merchant: str) -> str | None:
        if not self.available or self.collection.count() == 0:
            return None
        try:
            embeddings = self.embedding_service.embed_many([merchant])
            result = self.collection.query(query_embeddings=embeddings, n_results=1)
        except Exception as exc:
            self.available = False
            logger.warning("Disabling vector memory lookup after embedding failure: %s", exc)
            return None
        if not result["metadatas"] or not result["metadatas"][0]:
            return None
        match = result["metadatas"][0][0]
        distance = result["distances"][0][0] if result.get("distances") else None
        if distance is not None and distance > 0.25:
            return None
        return match.get("category")
