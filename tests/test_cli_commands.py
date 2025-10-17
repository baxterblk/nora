"""Tests for NORA CLI commands"""

import tempfile
import pathlib
import pytest
from unittest.mock import patch
from io import StringIO

from nora.cli import config_command
from nora.core.config import ConfigManager, DEFAULT_CONFIG


class TestConfigCommand:
    """Test suite for config_command function"""

    def test_config_path(self, tmp_path, capsys):
        """Test that 'nora config path' prints the config file path"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        # Run config path command
        config_command(manager, "path", [])

        # Check that path was printed to stdout
        captured = capsys.readouterr()
        assert str(config_path) in captured.out

    def test_config_reset(self, tmp_path):
        """Test that 'nora config reset' restores default configuration"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        # Modify config
        manager.config["model"] = "modified-model"
        manager.config["ollama"]["url"] = "http://modified:11434"
        manager.save()

        # Verify it was modified
        assert manager.config["model"] == "modified-model"
        assert manager.config["ollama"]["url"] == "http://modified:11434"

        # Run config reset command
        config_command(manager, "reset", [])

        # Verify config was reset to defaults
        assert manager.config["model"] == DEFAULT_CONFIG["model"]
        assert manager.config["ollama"]["url"] == DEFAULT_CONFIG["ollama"]["url"]
        assert manager.config == DEFAULT_CONFIG

        # Verify it was saved to file
        manager_reloaded = ConfigManager(str(config_path))
        assert manager_reloaded.config == DEFAULT_CONFIG
