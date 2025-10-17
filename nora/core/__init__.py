"""
NORA Core Modules

Core functionality for NORA including configuration, chat, history, plugin management, and actions.
"""

from .config import ConfigManager
from .history import HistoryManager
from .chat import OllamaChat, load_file_context
from .plugins import PluginLoader
from .actions import ActionsManager
from .interpreter import ActionInterpreter, FileAction, CommandAction
from .setup import first_run_wizard, should_run_wizard
from . import utils

__all__ = [
    "ConfigManager",
    "HistoryManager",
    "OllamaChat",
    "PluginLoader",
    "ActionsManager",
    "ActionInterpreter",
    "FileAction",
    "CommandAction",
    "load_file_context",
    "first_run_wizard",
    "should_run_wizard",
    "utils",
]
