import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .tools import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a tool call from the model."""

    tool_name: str
    parameters: Dict[str, Any]


class ToolInterpreter:
    """Interprets and executes tool calls from the model."""

    def __init__(self, tool_registry: ToolRegistry):
        """Initializes the interpreter with a tool registry."""
        self.tool_registry = tool_registry

    def run_tool(self, tool_call: ToolCall) -> Any:
        """Executes a single tool call."""
        return self.tool_registry.run_tool(tool_call.tool_name, tool_call.parameters)

    @staticmethod
    def extract_tool_calls(text: str) -> List[ToolCall]:
        """Extracts tool calls from the model's output."""
        tool_calls: List[ToolCall] = []
        # Simple JSON parsing for now. This will be improved later.
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    if "tool_name" in item and "parameters" in item:
                        tool_calls.append(
                            ToolCall(
                                tool_name=item["tool_name"],
                                parameters=item["parameters"],
                            )
                        )
        except json.JSONDecodeError:
            pass  # Not a JSON response, so no tool calls
        return tool_calls
