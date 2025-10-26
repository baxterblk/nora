"""Tests for NORA ConfigManager"""

import pathlib
import tempfile
from unittest.mock import Mock, patch

import pytest

from nora.core.config import DEFAULT_CONFIG, ConfigManager


class TestConfigManager:
    """Test suite for ConfigManager"""

    def test_init_creates_default_config(self, tmp_path):
        """Test that initialization creates default config if file doesn't exist"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        assert manager.config == DEFAULT_CONFIG
        assert manager.path == config_path

    def test_load_existing_config(self, tmp_path):
        """Test loading an existing configuration file"""
        config_path = tmp_path / "test_config.yaml"

        # Create a config file
        import yaml

        test_config = {"model": "test-model", "ollama": {"url": "http://test:11434"}}
        with open(config_path, "w") as f:
            yaml.safe_dump(test_config, f)

        manager = ConfigManager(str(config_path))
        assert manager.config["model"] == "test-model"
        assert manager.config["ollama"]["url"] == "http://test:11434"

    def test_save_config(self, tmp_path):
        """Test saving configuration to file"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        manager.config["test_key"] = "test_value"
        manager.save()

        assert config_path.exists()

        # Reload and verify
        import yaml

        with open(config_path, "r") as f:
            loaded = yaml.safe_load(f)

        assert loaded["test_key"] == "test_value"

    def test_set_nested_value(self, tmp_path):
        """Test setting nested configuration values"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        manager.set("ollama.url", "http://new-url:11434")

        assert manager.config["ollama"]["url"] == "http://new-url:11434"
        assert config_path.exists()

    def test_get_nested_value(self, tmp_path):
        """Test getting nested configuration values"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        manager.config["ollama"]["url"] = "http://test:11434"

        assert manager.get("ollama.url") == "http://test:11434"
        assert manager.get("nonexistent.key", "default") == "default"

    def test_get_ollama_url(self, tmp_path):
        """Test getting Ollama URL"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        url = manager.get_ollama_url()
        assert url == DEFAULT_CONFIG["ollama"]["url"]

    def test_get_model(self, tmp_path):
        """Test getting model name"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        model = manager.get_model()
        assert model == DEFAULT_CONFIG["model"]

    def test_environment_variable_overrides(self, tmp_path):
        """Test that environment variables override config file values"""
        config_path = tmp_path / "test_config.yaml"

        # Create a config with specific values
        import yaml

        test_config = {
            "model": "config-model",
            "ollama": {"url": "http://config:11434", "verify_ssl": False},
        }
        with open(config_path, "w") as f:
            yaml.safe_dump(test_config, f)

        manager = ConfigManager(str(config_path))

        # Test without env vars - should use config values
        assert manager.get_model() == "config-model"
        assert manager.get_ollama_url() == "http://config:11434"

        # Test with env vars - should override config
        with patch.dict(
            "os.environ",
            {"NORA_MODEL": "env-model", "NORA_OLLAMA_URL": "http://env:11434"},
        ):
            assert manager.get_model() == "env-model"
            assert manager.get_ollama_url() == "http://env:11434"

        # After patch, should revert to config values
        assert manager.get_model() == "config-model"
        assert manager.get_ollama_url() == "http://config:11434"

    def test_list_profiles(self, tmp_path):
        """Test listing available profiles"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        manager.config["profiles"] = {
            "production": {"url": "http://prod:11434"},
            "development": {"url": "http://dev:11434"},
        }

        profiles = manager.list_profiles()
        assert "production" in profiles
        assert "development" in profiles

    def test_use_profile_success(self, tmp_path):
        """Test switching to an existing profile"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        manager.config["profiles"] = {
            "test": {"url": "http://test:11434", "verify_ssl": True}
        }

        manager.use_profile("test")

        assert manager.config["ollama"]["url"] == "http://test:11434"
        assert manager.config["ollama"]["verify_ssl"] is True

    def test_use_profile_not_found(self, tmp_path):
        """Test switching to a non-existent profile raises error"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        with pytest.raises(ValueError, match="No such profile"):
            manager.use_profile("nonexistent")

    @patch("requests.get")
    def test_test_connection_success(self, mock_get, tmp_path):
        """Test successful connection test"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        mock_response = Mock()
        mock_response.json.return_value = {"version": "0.1.0"}
        mock_get.return_value = mock_response

        success, result = manager.test_connection()

        assert success is True
        assert result == {"version": "0.1.0"}

    @patch("requests.get")
    def test_test_connection_failure(self, mock_get, tmp_path):
        """Test failed connection test"""
        config_path = tmp_path / "test_config.yaml"
        manager = ConfigManager(str(config_path))

        mock_get.side_effect = Exception("Connection refused")

        success, result = manager.test_connection()

        assert success is False
        assert "Connection refused" in result
