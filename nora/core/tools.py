import importlib.util
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Discovers, loads, and manages tools."""

    def __init__(self, tool_paths: Optional[List[str]] = None):
        """Initializes the registry and loads tools from the specified paths."""
        self.tool_paths = tool_paths or [
            os.path.join(os.path.dirname(__file__), "..", "tools")
        ]
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.discover_tools()

    def discover_tools(self):
        """Discovers all tools in the specified paths."""
        for path in self.tool_paths:
            for tool_dir in Path(path).iterdir():
                if tool_dir.is_dir():
                    manifest_path = tool_dir / "tool.json"
                    if manifest_path.exists():
                        try:
                            tool = self.load_tool(manifest_path)
                            if tool:
                                self.tools[tool["name"]] = tool
                        except Exception as e:
                            logger.error(
                                f"Failed to load tool from {manifest_path}: {e}"
                            )

    def load_tool(self, manifest_path: Path) -> Optional[Dict[str, Any]]:
        """Loads a single tool from its manifest file."""
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        entrypoint_path = manifest_path.parent / manifest["entrypoint"]
        spec = importlib.util.spec_from_file_location(manifest["name"], entrypoint_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            manifest["run"] = module.run
            return manifest
        return None

    def get_tool(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves a tool from the registry."""
        return self.tools.get(tool_name)

    def run_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Runs a tool with the given parameters."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        return tool["run"](params)
