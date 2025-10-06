"""
NORA Core Modules

Core functionality for NORA including configuration, chat, history, and plugin management.
"""

from .config import ConfigManager
from .history import HistoryManager
from .chat import OllamaChat, load_file_context
from .plugins import PluginLoader, Agent, Tool
from . import utils

__all__ = [
    "ConfigManager",
    "HistoryManager",
    "OllamaChat",
    "PluginLoader",
    "Agent",
    "Tool",
    "load_file_context",
    "utils",
]
