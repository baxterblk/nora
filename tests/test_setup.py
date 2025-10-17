"""Tests for NORA first-run setup wizard"""

import tempfile
import pathlib
import pytest
import os
from unittest.mock import patch, Mock, call
from io import StringIO

from nora.core.setup import first_run_wizard, should_run_wizard, check_ollama_connection, get_available_models
from nora.core.config import ConfigManager, DEFAULT_CONFIG


class TestSetupWizard:
    """Test suite for first-run setup wizard"""

    def test_should_run_wizard_no_config(self, tmp_path, monkeypatch):
        """Test that wizard should run when no config exists"""
        # Set temporary config path
        monkeypatch.setenv("HOME", str(tmp_path))
        config_dir = tmp_path / ".nora"
        config_dir.mkdir()

        # No config file exists
        assert should_run_wizard() is True

    def test_should_run_wizard_config_exists(self, tmp_path, monkeypatch):
        """Test that wizard should NOT run when config exists"""
        # Set temporary config path
        monkeypatch.setenv("HOME", str(tmp_path))
        config_dir = tmp_path / ".nora"
        config_dir.mkdir()

        # Create config file
        config_path = config_dir / "config.yaml"
        config_path.write_text("model: test\n")

        # Should not run wizard
        assert should_run_wizard() is False

    def test_should_run_wizard_ci_environment(self, tmp_path, monkeypatch):
        """Test that wizard should NOT run in CI environment"""
        # Set CI environment variable
        monkeypatch.setenv("NORA_CI", "true")

        # Should not run wizard even if no config
        assert should_run_wizard() is False

    @patch('nora.core.setup.requests.get')
    def test_check_ollama_connection_success(self, mock_get):
        """Test successful Ollama connection"""
        mock_response = Mock()
        mock_response.json.return_value = {"version": "0.1.0"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        success, response = check_ollama_connection("http://localhost:11434")

        assert success is True
        assert response == {"version": "0.1.0"}
        mock_get.assert_called_once_with("http://localhost:11434/api/version", timeout=5, verify=False)

    @patch('nora.core.setup.requests.get')
    def test_check_ollama_connection_failure(self, mock_get):
        """Test failed Ollama connection"""
        mock_get.side_effect = Exception("Connection refused")

        success, response = check_ollama_connection("http://localhost:11434")

        assert success is False
        assert response is None

    @patch('nora.core.setup.requests.get')
    def test_get_available_models_success(self, mock_get):
        """Test getting available models"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:8b"},
                {"name": "deepseek-coder:6.7b"}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        models = get_available_models("http://localhost:11434")

        assert models == ["llama3:8b", "deepseek-coder:6.7b"]

    @patch('nora.core.setup.requests.get')
    def test_get_available_models_failure(self, mock_get):
        """Test getting models when API fails"""
        mock_get.side_effect = Exception("Connection refused")

        models = get_available_models("http://localhost:11434")

        assert models == []

    @patch('nora.core.setup.check_ollama_connection')
    @patch('nora.core.setup.get_available_models')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_wizard_with_defaults(self, mock_print, mock_input, mock_get_models, mock_check_conn, tmp_path, monkeypatch):
        """Test wizard flow with all default values"""
        # Setup
        monkeypatch.setenv("HOME", str(tmp_path))
        config_dir = tmp_path / ".nora"
        config_dir.mkdir()

        # Mock successful connection
        mock_check_conn.return_value = (True, {"version": "0.1.0"})

        # Mock available models
        mock_get_models.return_value = ["llama3:8b", "deepseek-coder:6.7b"]

        # Mock user inputs (all defaults - just pressing Enter)
        mock_input.side_effect = ["", ""]  # URL default, Model default

        # Run wizard
        config = first_run_wizard()

        # Verify configuration
        assert config["ollama"]["url"] == DEFAULT_CONFIG["ollama"]["url"]
        assert config["model"] == "llama3:8b"  # First model from list

        # Verify config was saved
        config_path = config_dir / "config.yaml"
        assert config_path.exists()

    @patch('nora.core.setup.check_ollama_connection')
    @patch('nora.core.setup.get_available_models')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_wizard_with_custom_values(self, mock_print, mock_input, mock_get_models, mock_check_conn, tmp_path, monkeypatch):
        """Test wizard flow with custom user values"""
        # Setup
        monkeypatch.setenv("HOME", str(tmp_path))
        config_dir = tmp_path / ".nora"
        config_dir.mkdir()

        # Mock successful connection
        mock_check_conn.return_value = (True, {"version": "0.1.0"})

        # Mock available models
        mock_get_models.return_value = ["llama3:8b", "deepseek-coder:6.7b"]

        # Mock user inputs (custom values)
        mock_input.side_effect = [
            "http://custom:11434",  # Custom URL
            "custom-model:1b"       # Custom model
        ]

        # Run wizard
        config = first_run_wizard()

        # Verify configuration
        assert config["ollama"]["url"] == "http://custom:11434"
        assert config["model"] == "custom-model:1b"

    @patch('nora.core.setup.check_ollama_connection')
    @patch('nora.core.setup.get_available_models')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_wizard_connection_retry(self, mock_print, mock_input, mock_get_models, mock_check_conn, tmp_path, monkeypatch):
        """Test wizard connection failure and retry flow"""
        # Setup
        monkeypatch.setenv("HOME", str(tmp_path))
        config_dir = tmp_path / ".nora"
        config_dir.mkdir()

        # Mock connection failure then success
        mock_check_conn.side_effect = [
            (False, None),  # First attempt fails
            (True, {"version": "0.1.0"})  # Second attempt succeeds
        ]

        # Mock available models
        mock_get_models.return_value = ["llama3:8b"]

        # Mock user inputs
        mock_input.side_effect = [
            "",  # First URL (default)
            "Y",  # Retry after failure
            "http://localhost:11434",  # Retry URL
            ""  # Model (default)
        ]

        # Run wizard
        config = first_run_wizard()

        # Verify it eventually succeeded
        assert config["ollama"]["url"] == "http://localhost:11434"
        assert mock_check_conn.call_count == 2

    @patch('nora.core.setup.check_ollama_connection')
    @patch('nora.core.setup.get_available_models')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_wizard_no_models_available(self, mock_print, mock_input, mock_get_models, mock_check_conn, tmp_path, monkeypatch):
        """Test wizard when no models are available"""
        # Setup
        monkeypatch.setenv("HOME", str(tmp_path))
        config_dir = tmp_path / ".nora"
        config_dir.mkdir()

        # Mock successful connection
        mock_check_conn.return_value = (True, {"version": "0.1.0"})

        # Mock NO available models
        mock_get_models.return_value = []

        # Mock user inputs
        mock_input.side_effect = [""]  # URL default

        # Run wizard
        config = first_run_wizard()

        # Should use DEFAULT_CONFIG model when no models available
        assert config["model"] == DEFAULT_CONFIG["model"]
