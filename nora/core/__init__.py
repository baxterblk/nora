"""
NORA Core Modules

Core functionality for NORA including configuration, chat, history, plugin management, and actions.
"""

from . import utils
from .actions import ActionsManager
from .chat import OllamaChat, load_file_context
from .config import ConfigManager
from .history import HistoryManager
from .indexer import ProjectIndexer
from .plugins import PluginLoader
from .setup import first_run_wizard, should_run_wizard
from .tool_interpreter import ToolCall, ToolInterpreter
from .tools import ToolRegistry
from .vector_store import VectorStore

__all__ = [
    "ConfigManager",
    "HistoryManager",
    "OllamaChat",
    "PluginLoader",
    "ActionsManager",
    "ActionInterpreter",
    "FileAction",
    "CommandAction",
    "ToolInterpreter",
    "ToolRegistry",
    "ToolCall",
    "VectorStore",
    "ProjectIndexer",
    "load_file_context",
    "first_run_wizard",
    "should_run_wizard",
    "utils",
]
