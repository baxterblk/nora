"""
NORA Plugin Loader

Dynamic plugin discovery and loading system for extensible agents and tools.
Supports both legacy function-based plugins and new class-based plugins.
"""

import importlib.util
import logging
import pathlib
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List

logger = logging.getLogger(__name__)


# Abstract Base Classes for v0.4.0+

class Agent(ABC):
    """
    Abstract base class for NORA agents.

    All agents must implement metadata() and run() methods.
    Optional hooks: on_start(), on_complete(), on_error()
    """

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """
        Return agent metadata.

        Required keys:
            name: str - Unique agent identifier
            description: str - Short description
            version: str - Semantic version

        Optional keys:
            author: str
            capabilities: List[str] - What the agent can do
            requires_tools: List[str] - Tool dependencies
            config_schema: Dict - JSON schema for configuration

        Returns:
            Agent metadata dictionary
        """
        pass

    @abstractmethod
    def run(
        self,
        context: Dict[str, Any],
        model: str,
        call_fn: Callable,
        tools: Optional[Dict[str, "Tool"]] = None
    ) -> Dict[str, Any]:
        """
        Execute the agent's main logic.

        Args:
            context: Shared context (memory, config, etc.)
            model: Ollama model to use
            call_fn: Function to call Ollama API
            tools: Available tools the agent can use

        Returns:
            Result dictionary with:
                success: bool
                output: Any
                context_updates: Dict (optional) - Updates to shared context
        """
        pass

    def on_start(self, context: Dict[str, Any]) -> None:
        """Hook called before run() - optional override."""
        pass

    def on_complete(self, result: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Hook called after successful run() - optional override."""
        pass

    def on_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Hook called on run() failure - optional override."""
        pass


class Tool(ABC):
    """
    Abstract base class for NORA tools.

    Tools are functions that agents can call to perform actions
    (file I/O, HTTP requests, shell commands, etc.)
    """

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """
        Return tool metadata.

        Required keys:
            name: str - Unique tool identifier
            description: str - What the tool does
            parameters: Dict - JSON schema for parameters

        Optional keys:
            returns: Dict - JSON schema for return value
            dangerous: bool - Requires user confirmation
            rate_limit: int - Max calls per minute

        Returns:
            Tool metadata dictionary
        """
        pass

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Any:
        """
        Execute the tool with given parameters.

        Args:
            params: Parameters matching the schema from metadata()

        Returns:
            Tool output (type matches returns schema)

        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If execution fails
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """
        Validate parameters against schema - optional override.

        Args:
            params: Parameters to validate

        Returns:
            True if valid, False otherwise
        """
        # Basic validation - override for custom logic
        schema = self.metadata().get("parameters", {})
        required = schema.get("required", [])
        return all(key in params for key in required)


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

        Supports both legacy function-based plugins and new class-based plugins.

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

            # Check for class-based agent (v0.4.0+)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, Agent) and attr is not Agent:
                    try:
                        agent_instance = attr()
                        metadata = agent_instance.metadata()

                        # Validate metadata schema
                        if not self._validate_agent_metadata(metadata, file_path):
                            return None

                        # Wrap class-based agent in legacy format
                        return {
                            "name": metadata["name"],
                            "description": metadata.get("description", ""),
                            "version": metadata.get("version", "0.1.0"),
                            "type": "class-based-agent",
                            "instance": agent_instance,
                            "run": lambda model, call_fn, ctx=None: agent_instance.run(
                                context=ctx or {},
                                model=model,
                                call_fn=call_fn
                            )
                        }
                    except Exception as e:
                        logger.error(f"Failed to instantiate agent from {file_path}: {e}")
                        return None

            # Fall back to legacy function-based plugin
            if not hasattr(module, "register"):
                logger.warning(f"Plugin {file_path.name} missing 'register' function or Agent class")
                return None

            entry = module.register()

            # Validate legacy plugin structure
            if not isinstance(entry, dict) or "name" not in entry or "run" not in entry:
                logger.error(f"Plugin {file_path.name} has invalid structure")
                return None

            # Mark as legacy type
            entry["type"] = "legacy-function"
            return entry

        except Exception as e:
            logger.error(f"Failed to load plugin from {file_path}: {e}", exc_info=True)
            return None

    def _validate_agent_metadata(self, metadata: Dict[str, Any], file_path: pathlib.Path) -> bool:
        """
        Validate agent metadata against schema.

        Args:
            metadata: Agent metadata dictionary
            file_path: Path to plugin file (for error messages)

        Returns:
            True if valid, False otherwise
        """
        required_keys = ["name", "description", "version"]

        for key in required_keys:
            if key not in metadata:
                logger.error(f"Agent {file_path.name} missing required metadata key: {key}")
                return False

        # Validate types
        if not isinstance(metadata["name"], str):
            logger.error(f"Agent {file_path.name} metadata 'name' must be string")
            return False

        if not isinstance(metadata["description"], str):
            logger.error(f"Agent {file_path.name} metadata 'description' must be string")
            return False

        if not isinstance(metadata["version"], str):
            logger.error(f"Agent {file_path.name} metadata 'version' must be string")
            return False

        # Validate optional fields
        if "capabilities" in metadata and not isinstance(metadata["capabilities"], list):
            logger.error(f"Agent {file_path.name} metadata 'capabilities' must be list")
            return False

        if "requires_tools" in metadata and not isinstance(metadata["requires_tools"], list):
            logger.error(f"Agent {file_path.name} metadata 'requires_tools' must be list")
            return False

        logger.debug(f"Validated metadata for agent: {metadata['name']}")
        return True

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
