"""
NORA Configuration Manager

Handles user configuration for Ollama connections and profiles with structured logging.
"""

import logging
import pathlib
from typing import Any, Dict, Optional, Tuple
import yaml
import requests

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: Dict[str, Any] = {
    "model": "deepseek-coder:6.7b",
    "ollama": {"url": "http://localhost:11434", "verify_ssl": False},
    "profiles": {},
}


class ConfigManager:
    """Manages NORA configuration with support for multiple profiles and connection testing."""

    def __init__(self, path: str = "~/.nora/config.yaml") -> None:
        """
        Initialize the configuration manager.

        Args:
            path: Path to the configuration file (defaults to ~/.nora/config.yaml)
        """
        self.path = pathlib.Path(path).expanduser()
        self.config = self.load()
        logger.debug(f"ConfigManager initialized with path: {self.path}")

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from file or return defaults.

        Returns:
            Configuration dictionary
        """
        if not self.path.exists():
            logger.info(f"Config file not found at {self.path}, using defaults")
            return DEFAULT_CONFIG.copy()

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config from {self.path}: {e}")
            return DEFAULT_CONFIG.copy()

    def save(self) -> None:
        """Save current configuration to file."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.config, f)
            logger.info(f"Saved configuration to {self.path}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.path}: {e}")
            raise

    def set(self, key_path: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the key (e.g., "ollama.url")
            value: Value to set (use "null" or None to delete the key)

        Example:
            config.set("ollama.url", "http://remote:11434")
            config.set("ollama.endpoint", "null")  # Deletes the key
        """
        keys = key_path.split(".")
        d = self.config

        # Handle "null" string or None as deletion request
        if value == "null" or value is None:
            # Navigate to parent dict
            for k in keys[:-1]:
                if k not in d or not isinstance(d[k], dict):
                    return  # Key doesn't exist, nothing to delete
                d = d[k]
            # Delete the final key if it exists
            if keys[-1] in d:
                del d[keys[-1]]
                self.save()
                logger.info(f"Deleted config {key_path}")
            return

        # Normal set operation
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        self.save()
        logger.info(f"Set config {key_path} = {value}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key_path.split(".")
        d = self.config
        for k in keys:
            if k not in d:
                return default
            d = d[k]
        return d

    def get_ollama_url(self) -> str:
        """
        Get the Ollama API URL from configuration.

        Returns:
            Ollama URL string
        """
        return self.config.get("ollama", {}).get("url", "http://localhost:11434")

    def get_model(self) -> str:
        """
        Get the default model name from configuration.

        Returns:
            Model name string
        """
        return self.config.get("model", "deepseek-coder:6.7b")

    def list_profiles(self) -> list:
        """
        List all available configuration profiles.

        Returns:
            List of profile names
        """
        return list(self.config.get("profiles", {}).keys())

    def use_profile(self, name: str) -> None:
        """
        Switch to a named configuration profile.

        Args:
            name: Profile name

        Raises:
            ValueError: If profile does not exist
        """
        if name not in self.config.get("profiles", {}):
            logger.error(f"Profile '{name}' not found")
            raise ValueError(f"No such profile: {name}")

        self.config["ollama"] = self.config["profiles"][name]
        self.save()
        logger.info(f"Switched to profile: {name}")

    def test_connection(self) -> Tuple[bool, Any]:
        """
        Test connection to Ollama API.

        Returns:
            Tuple of (success: bool, response: dict or error message)
        """
        url = self.get_ollama_url()
        logger.debug(f"Testing connection to {url}")

        try:
            r = requests.get(f"{url}/api/version", timeout=5, verify=False)
            r.raise_for_status()
            result = r.json()
            logger.info(f"Connection successful to {url}")
            return True, result
        except Exception as e:
            logger.error(f"Connection failed to {url}: {e}")
            return False, str(e)
