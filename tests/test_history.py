"""Tests for NORA HistoryManager"""

import json
import pytest

from nora.core.history import HistoryManager


class TestHistoryManager:
    """Test suite for HistoryManager"""

    def test_init_creates_path(self, tmp_path):
        """Test that initialization sets up the path correctly"""
        history_path = tmp_path / "test_history.json"
        manager = HistoryManager(str(history_path))

        assert manager.path == history_path

    def test_load_empty_history(self, tmp_path):
        """Test loading when no history file exists"""
        history_path = tmp_path / "test_history.json"
        manager = HistoryManager(str(history_path))

        history = manager.load()

        assert history == []

    def test_save_and_load_history(self, tmp_path):
        """Test saving and loading history"""
        history_path = tmp_path / "test_history.json"
        manager = HistoryManager(str(history_path))

        test_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        manager.save(test_history)

        # Load and verify
        loaded = manager.load()
        assert len(loaded) == 2
        assert loaded[0]["role"] == "user"
        assert loaded[0]["content"] == "Hello"
        assert loaded[1]["role"] == "assistant"

    def test_clear_history(self, tmp_path):
        """Test clearing history"""
        history_path = tmp_path / "test_history.json"
        manager = HistoryManager(str(history_path))

        # Create some history
        test_history = [{"role": "user", "content": "Test"}]
        manager.save(test_history)

        assert history_path.exists()

        # Clear it
        manager.clear()

        assert not history_path.exists()

    def test_add_message(self, tmp_path):
        """Test adding a message to history"""
        history_path = tmp_path / "test_history.json"
        manager = HistoryManager(str(history_path))

        history = []
        history = manager.add_message(history, "user", "Hello")

        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"

        # Verify it was saved
        loaded = manager.load()
        assert len(loaded) == 1

    def test_add_multiple_messages(self, tmp_path):
        """Test adding multiple messages"""
        history_path = tmp_path / "test_history.json"
        manager = HistoryManager(str(history_path))

        history = []
        history = manager.add_message(history, "user", "First")
        history = manager.add_message(history, "assistant", "Second")
        history = manager.add_message(history, "user", "Third")

        assert len(history) == 3
        assert history[0]["content"] == "First"
        assert history[1]["content"] == "Second"
        assert history[2]["content"] == "Third"

    def test_get_recent_within_limit(self, tmp_path):
        """Test getting recent messages when under limit"""
        history_path = tmp_path / "test_history.json"
        manager = HistoryManager(str(history_path))

        history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(5)
        ]

        recent = manager.get_recent(history, limit=10)

        assert len(recent) == 5

    def test_get_recent_over_limit(self, tmp_path):
        """Test getting recent messages when over limit"""
        history_path = tmp_path / "test_history.json"
        manager = HistoryManager(str(history_path))

        history = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(20)
        ]

        recent = manager.get_recent(history, limit=10)

        assert len(recent) == 10
        assert recent[0]["content"] == "Message 10"
        assert recent[-1]["content"] == "Message 19"

    def test_load_corrupted_history(self, tmp_path):
        """Test loading corrupted history file returns empty list"""
        history_path = tmp_path / "test_history.json"
        manager = HistoryManager(str(history_path))

        # Write corrupted JSON
        with open(history_path, "w") as f:
            f.write("{ this is not valid json")

        history = manager.load()

        assert history == []
