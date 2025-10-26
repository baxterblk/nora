import logging

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorStore:
    """A simple vector store for conversational history."""

    def __init__(self, model_name="all-MiniLM-L6-v2"):
        """Initializes the vector store."""
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.documents = []

    def add_to_store(self, text: str):
        """Adds a text to the vector store."""
        self.documents.append(text)
        embedding = self.model.encode([text])
        faiss.normalize_L2(embedding)
        if self.index is None:
            self.index = faiss.IndexFlatIP(embedding.shape[1])
        self.index.add(embedding)
        logger.info(f"Added to vector store: {text}")

    def search(self, query: str, k: int = 5, threshold: float = 0.5):
        """Searches the vector store for the most similar texts."""
        if self.index is None:
            return []

        num_documents = self.index.ntotal
        if k > num_documents:
            k = num_documents

        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        distances, indices = self.index.search(query_embedding, k)

        results = []
        for i, dist in zip(indices[0], distances[0]):
            if i == -1:  # faiss returns -1 for empty results
                continue
            if dist > threshold:
                results.append(self.documents[i])
        return results
