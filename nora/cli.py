#!/usr/bin/env python3
"""
NORA CLI — v0.3
Enhanced with:
  - Modular core architecture
  - Structured logging with colored output
  - Type hints and comprehensive docstrings
  - Project scaffolding commands
  - Connection status banner
"""

import argparse
import json
import logging
import pathlib
import readline  # noqa: F401 - imported for side effects
import sys
from typing import List, Optional

from .core import ConfigManager, HistoryManager, OllamaChat, PluginLoader, load_file_context
from .core import utils

logger = logging.getLogger(__name__)


def chat_loop(
    config: ConfigManager,
    history_manager: HistoryManager,
    model: Optional[str] = None,
    context_files: Optional[List[str]] = None,
    system: Optional[str] = None
) -> None:
    """
    Run an interactive chat REPL.

    Args:
        config: Configuration manager instance
        history_manager: History manager instance
        model: Model name (defaults to config)
        context_files: List of file paths for context injection
        system: System prompt
    """
    model = model or config.get_model()
    ollama_url = config.get_ollama_url()

    # Show connection banner
    utils.connection_banner(ollama_url, model)

    # Initialize chat client
    chat_client = OllamaChat(ollama_url, model)

    # Load history
    history = history_manager.load()

    # Load file context if provided
    file_context = ""
    if context_files:
        file_context = load_file_context(context_files)
        if file_context:
            system = (system or "") + "\n\nYou have access to the following files:\n" + file_context
            utils.info(f"Loaded context from {len(context_files)} file(s)")

    print(f"\nType {utils.colored('/exit', utils.Colors.CYAN)} to quit, {utils.colored('/clear', utils.Colors.CYAN)} to reset history.\n")

    while True:
        try:
            prompt = input(utils.colored("You> ", utils.Colors.BRIGHT_BLUE, bold=True))
        except (EOFError, KeyboardInterrupt):
            print("\nExiting…")
            break

        cmd = prompt.strip().lower()
        if cmd in ["/exit", "exit", "quit"]:
            break

        if cmd == "/clear":
            history_manager.clear()
            history = []
            utils.success("History cleared")
            continue

        # Build messages for API
        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        # Add recent history (last 10 messages)
        for m in history_manager.get_recent(history, limit=10):
            messages.append(m)

        messages.append({"role": "user", "content": prompt})

        # Send chat request
        try:
            chat_client.chat(messages, model=model, stream=True)

            # Update history
            history = history_manager.add_message(history, "user", prompt)
            history = history_manager.add_message(history, "assistant", "[streamed above]")
            print()

        except Exception as e:
            utils.error(f"Chat request failed: {e}")
            logger.exception("Chat request failed")


def run_one_shot(
    config: ConfigManager,
    prompt_text: str,
    model: Optional[str] = None,
    context_files: Optional[List[str]] = None
) -> None:
    """
    Run a one-shot prompt without interactive mode.

    Args:
        config: Configuration manager instance
        prompt_text: The prompt to send
        model: Model name (defaults to config)
        context_files: List of file paths for context injection
    """
    model = model or config.get_model()
    ollama_url = config.get_ollama_url()

    chat_client = OllamaChat(ollama_url, model)

    messages = []

    # Load file context if provided
    if context_files:
        file_context = load_file_context(context_files)
        if file_context:
            messages.append({"role": "system", "content": "Context files:\n" + file_context})

    messages.append({"role": "user", "content": prompt_text})

    try:
        chat_client.chat(messages, model=model, stream=True)
        print()
    except Exception as e:
        utils.error(f"Request failed: {e}")
        logger.exception("One-shot request failed")
        sys.exit(1)


def list_agents(plugin_loader: PluginLoader) -> None:
    """
    List all available agent plugins.

    Args:
        plugin_loader: Plugin loader instance
    """
    plugins = plugin_loader.load_plugins()

    if not plugins:
        utils.warning("No agents installed")
        return

    utils.info("Available agents:")
    for name, plugin in sorted(plugins.items()):
        desc = plugin.get("description", "No description")
        print(f"  {utils.colored(name, utils.Colors.CYAN, bold=True)} — {desc}")


def run_agent(
    plugin_loader: PluginLoader,
    config: ConfigManager,
    name: str,
    model: Optional[str] = None
) -> None:
    """
    Run a named agent plugin.

    Args:
        plugin_loader: Plugin loader instance
        config: Configuration manager instance
        name: Agent name
        model: Model name (defaults to config)
    """
    model = model or config.get_model()
    ollama_url = config.get_ollama_url()

    plugins = plugin_loader.load_plugins()
    plugin = plugin_loader.get_plugin(name, plugins)

    if not plugin:
        utils.error(f"Agent '{name}' not found")
        sys.exit(1)

    utils.info(f"Running agent '{name}' — {plugin.get('description', '')}")

    # Create chat function for the agent
    chat_client = OllamaChat(ollama_url, model)

    def agent_chat(messages, model=model, stream=False):
        chat_client.chat(messages, model=model, stream=stream)

    try:
        plugin["run"](model, agent_chat)
    except Exception as e:
        utils.error(f"Agent '{name}' failed: {e}")
        logger.exception(f"Agent '{name}' failed")
        sys.exit(1)


def scaffold_plugin(name: str) -> None:
    """
    Create a new agent plugin from template.

    Args:
        name: Plugin name (will be sanitized for filename)
    """
    # Sanitize plugin name
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name.lower())

    plugins_dir = pathlib.Path(__file__).parent / "plugins"
    plugin_file = plugins_dir / f"{safe_name}.py"

    if plugin_file.exists():
        utils.error(f"Plugin '{safe_name}' already exists at {plugin_file}")
        sys.exit(1)

    # Template content
    template = f'''"""
{name} Agent Plugin

Add your description here.
"""


def register():
    """Register the {name} agent plugin."""

    def run(model, call_fn):
        """
        Run the {name} agent.

        Args:
            model: Model name to use
            call_fn: Ollama chat function
        """
        # TODO: Implement your agent logic here
        messages = [
            {{"role": "user", "content": "Hello from {name}!"}}
        ]
        call_fn(messages, model=model, stream=True)

    return {{
        "name": "{safe_name}",
        "description": "{name} agent plugin",
        "run": run
    }}
'''

    try:
        plugin_file.write_text(template)
        utils.success(f"Created plugin: {plugin_file}")
        utils.info(f"Edit the file and implement your agent logic")
        utils.info(f"Test with: nora agent {safe_name}")
    except Exception as e:
        utils.error(f"Failed to create plugin: {e}")
        sys.exit(1)


def config_command(config: ConfigManager, action: str, args: List[str]) -> None:
    """
    Handle configuration commands.

    Args:
        config: Configuration manager instance
        action: Action to perform (show, set, use, test)
        args: Additional arguments
    """
    if action == "show":
        print(json.dumps(config.config, indent=2))

    elif action == "set":
        if len(args) != 2:
            utils.error("Usage: nora config set <key> <value>")
            sys.exit(1)
        config.set(args[0], args[1])
        utils.success("Configuration updated")

    elif action == "use":
        if not args:
            utils.error("Usage: nora config use <profile>")
            sys.exit(1)
        try:
            config.use_profile(args[0])
            utils.success(f"Switched to profile: {args[0]}")
        except ValueError as e:
            utils.error(str(e))
            sys.exit(1)

    elif action == "test":
        utils.info("Testing connection to Ollama...")
        ok, resp = config.test_connection()
        if ok:
            utils.success(f"Connected: {resp}")
        else:
            utils.error(f"Connection failed: {resp}")
            sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="nora",
        description="NORA - No Rush (on) Anything: Local AI agent CLI"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--log-file",
        help="Log to file"
    )

    sub = parser.add_subparsers(dest="cmd", help="Commands")

    # chat
    p_chat = sub.add_parser("chat", help="Interactive REPL chat")
    p_chat.add_argument("-m", "--model", help="Model name")
    p_chat.add_argument("--system", help="System prompt")
    p_chat.add_argument("--context", nargs="*", help="File(s) to include as context")

    # run
    p_run = sub.add_parser("run", help="One-shot prompt")
    p_run.add_argument("-m", "--model", help="Model name")
    p_run.add_argument("--context", nargs="*", help="File(s) to include as context")
    p_run.add_argument("prompt", nargs="+", help="Prompt text")

    # agent
    p_agent = sub.add_parser("agent", help="Run an agent plugin")
    p_agent.add_argument("name", help="Agent name")
    p_agent.add_argument("-m", "--model", help="Model name")

    # agents (list)
    sub.add_parser("agents", help="List available agents")

    # project
    p_project = sub.add_parser("project", help="Project management commands")
    p_project_sub = p_project.add_subparsers(dest="project_cmd")

    p_new = p_project_sub.add_parser("new", help="Create a new agent plugin")
    p_new.add_argument("name", help="Plugin name")

    p_project_sub.add_parser("list", help="List all plugins (alias for 'nora agents')")

    # config
    p_conf = sub.add_parser("config", help="Manage configuration")
    p_conf.add_argument(
        "action",
        choices=["show", "set", "use", "test"],
        help="Action to perform"
    )
    p_conf.add_argument("args", nargs="*", help="Action arguments")

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    utils.setup_logging(log_level, args.log_file)

    # Initialize core components
    config = ConfigManager()
    history_manager = HistoryManager()
    plugin_loader = PluginLoader()

    # Route commands
    if args.cmd == "chat":
        chat_loop(
            config,
            history_manager,
            model=args.model,
            context_files=args.context,
            system=args.system
        )

    elif args.cmd == "run":
        prompt_text = " ".join(args.prompt)
        run_one_shot(config, prompt_text, model=args.model, context_files=args.context)

    elif args.cmd == "agent":
        run_agent(plugin_loader, config, args.name, model=args.model)

    elif args.cmd == "agents":
        list_agents(plugin_loader)

    elif args.cmd == "project":
        if args.project_cmd == "new":
            scaffold_plugin(args.name)
        elif args.project_cmd == "list":
            list_agents(plugin_loader)
        else:
            parser.parse_args(["project", "-h"])

    elif args.cmd == "config":
        config_command(config, args.action, args.args)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
