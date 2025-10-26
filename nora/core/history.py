"""
NORA History Manager

Manages persistent chat history with automatic file handling and rotation.
"""

import json
import logging
import pathlib
from typing import Any, Dict, List

from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class HistoryManager:
    """Manages persistent chat history stored in JSON format."""

    def __init__(self, path: str = "~/.nora/history.json") -> None:
        """
        Initialize the history manager.

        Args:
            path: Path to the history file (defaults to ~/.nora/history.json)
        """
        self.path = pathlib.Path(path).expanduser()
        self._ensure_dirs()
        self.vector_store = VectorStore()
        logger.debug(f"HistoryManager initialized with path: {self.path}")

    def _ensure_dirs(self) -> None:
        """Ensure the history directory exists."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> List[Dict[str, str]]:
        """
        Load chat history from file.

        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        if not self.path.exists():
            logger.debug("No history file found, returning empty history")
            return []

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                history = json.load(f)
            logger.info(f"Loaded {len(history)} messages from history")
            # Populate the vector store with the loaded history
            for message in history:
                self.vector_store.add_to_store(message["content"])
            return history
        except Exception as e:
            logger.error(f"Failed to load history from {self.path}: {e}")
            return []

    def save(self, history: List[Dict[str, str]]) -> None:
        """
        Save chat history to file.

        Args:
            history: List of message dictionaries to save
        """
        try:
            self._ensure_dirs()
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
            logger.debug(f"Saved {len(history)} messages to history")
        except Exception as e:
            logger.error(f"Failed to save history to {self.path}: {e}")
            raise

    def clear(self) -> None:
        """Clear all chat history."""
        try:
            if self.path.exists():
                self.path.unlink()
                self.vector_store = VectorStore()  # Re-initialize the vector store
                logger.info("History cleared")
        except Exception as e:
            logger.error(f"Failed to clear history: {e}")
            raise

    def add_message(
        self, history: List[Dict[str, str]], role: str, content: str
    ) -> List[Dict[str, str]]:
        """
        Add a message to history and save it.

        Args:
            history: Current history list
            role: Message role (user, assistant, system)
            content: Message content

        Returns:
            Updated history list
        """
        history.append({"role": role, "content": content})
        self.vector_store.add_to_store(content)
        self.save(history)
        logger.debug(f"Added {role} message to history")
        return history

    def search_history(self, query: str, k: int = 5) -> List[str]:
        """Search the conversation history for similar messages."""
        return self.vector_store.search(query, k)

    def get_recent(
        self, history: List[Dict[str, str]], limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Get the most recent messages from history.

        Args:
            history: Full history list
            limit: Maximum number of messages to return

        Returns:
            List of most recent messages
        """
        return history[-limit:] if len(history) > limit else history
