import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    """A simple vector store for conversational history."""

    def __init__(self, model_name='all-MiniLM-L6-v2'):
        """Initializes the vector store."""
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.documents = []

    def add_to_store(self, text: str):
        """Adds a text to the vector store."""
        self.documents.append(text)
        embedding = self.model.encode([text])
        if self.index is None:
            self.index = faiss.IndexFlatL2(embedding.shape[1])
        self.index.add(embedding)
        logger.info(f"Added to vector store: {text}")

    def search(self, query: str, k: int = 5):
        """Searches the vector store for the most similar texts."""
        if self.index is None:
            return []
        query_embedding = self.model.encode([query])
        distances, indices = self.index.search(query_embedding, k)
        return [self.documents[i] for i in indices[0]]
