"""
NORA Plugin Loader

Dynamic plugin discovery and loading system for extensible agents.
"""

import importlib.util
import logging
import pathlib
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class PluginLoader:
    """Dynamically loads and manages NORA agent plugins."""

    def __init__(self, plugins_dir: Optional[pathlib.Path] = None) -> None:
        """
        Initialize the plugin loader.

        Args:
            plugins_dir: Directory containing plugin files (defaults to nora/plugins/)
        """
        if plugins_dir is None:
            # Default to nora/plugins/ relative to this file
            self.plugins_dir = pathlib.Path(__file__).parent.parent / "plugins"
        else:
            self.plugins_dir = plugins_dir

        logger.debug(f"PluginLoader initialized with directory: {self.plugins_dir}")

    def load_plugins(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all plugins from the plugins directory.

        Returns:
            Dictionary mapping plugin names to their registration data
        """
        plugins: Dict[str, Dict[str, Any]] = {}

        if not self.plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return plugins

        for file_path in self.plugins_dir.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            plugin = self._load_plugin(file_path)
            if plugin:
                plugins[plugin["name"]] = plugin
                logger.info(f"Loaded plugin: {plugin['name']}")

        logger.debug(f"Loaded {len(plugins)} plugins total")
        return plugins

    def _load_plugin(self, file_path: pathlib.Path) -> Optional[Dict[str, Any]]:
        """
        Load a single plugin from a file.

        Args:
            file_path: Path to the plugin file

        Returns:
            Plugin registration dictionary or None if loading failed
        """
        try:
            spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
            if spec is None or spec.loader is None:
                logger.error(f"Failed to create module spec for {file_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "register"):
                logger.warning(f"Plugin {file_path.name} missing 'register' function")
                return None

            entry = module.register()

            # Validate plugin structure
            if not isinstance(entry, dict) or "name" not in entry or "run" not in entry:
                logger.error(f"Plugin {file_path.name} has invalid structure")
                return None

            return entry

        except Exception as e:
            logger.error(f"Failed to load plugin from {file_path}: {e}")
            return None

    def get_plugin(self, name: str, plugins: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Get a plugin by name.

        Args:
            name: Plugin name
            plugins: Dictionary of loaded plugins

        Returns:
            Plugin dictionary or None if not found
        """
        return plugins.get(name)

    def run_plugin(
        self,
        name: str,
        plugins: Dict[str, Dict[str, Any]],
        model: str,
        chat_fn: Callable
    ) -> bool:
        """
        Run a plugin by name.

        Args:
            name: Plugin name
            plugins: Dictionary of loaded plugins
            model: Model name to use
            chat_fn: Chat function to pass to the plugin

        Returns:
            True if plugin ran successfully, False otherwise
        """
        plugin = self.get_plugin(name, plugins)
        if not plugin:
            logger.error(f"Plugin '{name}' not found")
            return False

        try:
            logger.info(f"Running plugin: {name}")
            plugin["run"](model, chat_fn)
            return True
        except Exception as e:
            logger.error(f"Plugin '{name}' failed: {e}")
            return False
