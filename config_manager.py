#!/usr/bin/env python3
"""
NORA Config Manager
Handles user configuration for Ollama connections and profiles.
"""

import pathlib
import yaml
import requests

DEFAULT_CONFIG = {
    "model": "deepseek-coder:6.7b",
    "ollama": {"url": "http://localhost:11434", "verify_ssl": False},
    "profiles": {},
}


class ConfigManager:
    def __init__(self, path="~/.nora/config.yaml"):
        self.path = pathlib.Path(path).expanduser()
        self.config = self.load()

    def load(self):
        if not self.path.exists():
            return DEFAULT_CONFIG.copy()
        with open(self.path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.config, f)

    def set(self, key_path, value):
        keys = key_path.split(".")
        d = self.config
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        self.save()

    def get(self, key_path, default=None):
        keys = key_path.split(".")
        d = self.config
        for k in keys:
            if k not in d:
                return default
            d = d[k]
        return d

    def get_ollama_url(self):
        return self.config.get("ollama", {}).get("url", "http://localhost:11434")

    def list_profiles(self):
        return self.config.get("profiles", {}).keys()

    def use_profile(self, name):
        if name not in self.config.get("profiles", {}):
            raise ValueError(f"No such profile: {name}")
        self.config["ollama"] = self.config["profiles"][name]
        self.save()

    def test_connection(self):
        url = self.get_ollama_url()
        try:
            r = requests.get(f"{url}/api/version", timeout=5, verify=False)
            r.raise_for_status()
            return True, r.json()
        except Exception as e:
            return False, str(e)
