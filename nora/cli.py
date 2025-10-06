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


def normalize_endpoint(endpoint: Optional[str]) -> Optional[str]:
    """
    Normalize endpoint value, treating "null" string as None.

    Args:
        endpoint: Endpoint value from config (may be None or "null" string)

    Returns:
        None if endpoint is None or "null" string, otherwise the endpoint value
    """
    if endpoint == "null" or endpoint is None:
        return None
    return endpoint


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

    # Get compatibility mode and endpoint (default to "chat" and None for auto-detect)
    compatibility_mode = config.get("ollama.compatibility", "chat")
    endpoint = normalize_endpoint(config.get("ollama.endpoint", None))

    # Initialize chat client
    chat_client = OllamaChat(ollama_url, model, compatibility_mode=compatibility_mode, endpoint=endpoint)

    # Trigger endpoint detection if not manually set
    if not endpoint:
        detected = chat_client.get_endpoint()
        if detected and detected != endpoint:
            config.set("ollama.endpoint", detected)
            logger.info(f"Auto-detected and saved endpoint: {detected}")

    # Show connection banner with detected endpoint
    utils.connection_banner(ollama_url, model, endpoint=chat_client.get_endpoint())

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
    compatibility_mode = config.get("ollama.compatibility", "chat")
    endpoint = normalize_endpoint(config.get("ollama.endpoint", None))

    chat_client = OllamaChat(ollama_url, model, compatibility_mode=compatibility_mode, endpoint=endpoint)

    # Auto-detect and save endpoint if needed
    if not endpoint:
        detected = chat_client.get_endpoint()
        if detected:
            config.set("ollama.endpoint", detected)

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
    compatibility_mode = config.get("ollama.compatibility", "chat")
    endpoint = normalize_endpoint(config.get("ollama.endpoint", None))
    chat_client = OllamaChat(ollama_url, model, compatibility_mode=compatibility_mode, endpoint=endpoint)

    # Auto-detect and save endpoint if needed
    if not endpoint:
        detected = chat_client.get_endpoint()
        if detected:
            config.set("ollama.endpoint", detected)

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


def run_team(config: ConfigManager, team_config_path: str, plugin_loader: PluginLoader) -> None:
    """
    Run a multi-agent team from config file.

    Args:
        config: Configuration manager instance
        team_config_path: Path to team config YAML
        plugin_loader: Plugin loader instance
    """
    from .core.orchestrator import Orchestrator, AgentTask, load_team_config

    try:
        utils.info(f"Loading team config: {team_config_path}")
        team_config = load_team_config(team_config_path)

        # Load plugins
        plugins = plugin_loader.load_plugins()

        # Create orchestrator
        model = team_config.get("model", config.get_model())
        compatibility_mode = config.get("ollama.compatibility", "chat")
        endpoint = normalize_endpoint(config.get("ollama.endpoint", None))
        chat_client = OllamaChat(config.get_ollama_url(), model, compatibility_mode=compatibility_mode, endpoint=endpoint)

        # Auto-detect and save endpoint if needed
        if not endpoint:
            detected = chat_client.get_endpoint()
            if detected:
                config.set("ollama.endpoint", detected)

        orchestrator = Orchestrator(
            model=model,
            call_fn=chat_client.chat
        )

        # Build agent tasks
        tasks = []
        for agent_config in team_config["agents"]:
            agent_name = agent_config["agent"]
            plugin = plugins.get(agent_name)

            if not plugin:
                utils.warning(f"Agent not found: {agent_name}")
                continue

            task = AgentTask(
                agent_name=agent_config.get("name", agent_name),
                agent_instance=plugin,
                model=model,
                depends_on=agent_config.get("depends_on", []),
                config=agent_config.get("config", {})
            )
            tasks.append(task)

        if not tasks:
            utils.error("No valid agents found in team config")
            sys.exit(1)

        utils.info(f"Running team: {team_config['name']} ({len(tasks)} agents)")

        # Execute team
        mode = team_config["mode"]
        if mode == "sequential":
            results = orchestrator.run_sequential(tasks)
        else:
            results = orchestrator.run_parallel(tasks)

        # Display results
        utils.success(f"Team execution completed")
        for agent_name, result in results.items():
            if result.get("success"):
                utils.success(f"  {agent_name}: Success")
            else:
                utils.error(f"  {agent_name}: Failed - {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"Team execution failed: {e}", exc_info=True)
        utils.error(f"Team execution failed: {e}")
        sys.exit(1)


def index_project_command(project_path: str, project_name: Optional[str] = None, search_query: Optional[str] = None) -> None:
    """
    Index a project directory for code-aware conversations.

    Args:
        project_path: Path to project to index
        project_name: Optional project name
        search_query: Optional search query to run after indexing
    """
    from .core.indexer import ProjectIndexer

    try:
        utils.info(f"Indexing project: {project_path}")

        indexer = ProjectIndexer()
        index_data = indexer.index_project(project_path, project_name)

        # Save index
        indexer.save_index(index_data)

        utils.success(
            f"Indexed {index_data['total_files']} files "
            f"({index_data['total_size'] / 1024:.1f} KB total)"
        )

        # Show language stats
        utils.info("Languages found:")
        for lang, count in index_data["languages"].items():
            print(f"  {lang}: {count} files")

        # Run search if requested
        if search_query:
            utils.info(f"\nSearching for: {search_query}")
            results = indexer.search(search_query, index_data)

            if results:
                utils.success(f"Found {len(results)} results:")
                for i, result in enumerate(results[:5], 1):
                    print(f"\n{i}. {result['relative_path']} (score: {result['relevance_score']})")
                    preview = result.get("content_preview", "")[:200]
                    print(f"   {preview}...")
            else:
                utils.warning("No results found")

    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        utils.error(f"Indexing failed: {e}")
        sys.exit(1)


def serve_api(config: ConfigManager, host: str = "0.0.0.0", port: int = 8001) -> None:
    """
    Start the REST API server.

    Args:
        config: Configuration manager instance
        host: Host to bind to
        port: Port to bind to
    """
    try:
        from .api.server import create_server

        utils.info(f"Starting NORA API server on http://{host}:{port}")
        utils.info("API documentation: http://{host}:{port}/docs")
        utils.info("Press Ctrl+C to stop")

        server = create_server(config, host=host, port=port)
        server.run()

    except ImportError as e:
        logger.error(f"Failed to import API server: {e}")
        utils.error(
            "API server dependencies not installed.\n"
            "Install with: pip install 'nora-cli[api]'"
        )
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start API server: {e}", exc_info=True)
        utils.error(f"Failed to start API server: {e}")
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
    p_agent.add_argument("--team", help="Team config YAML for multi-agent execution")

    # agents (list)
    sub.add_parser("agents", help="List available agents")

    # project
    p_project = sub.add_parser("project", help="Project management commands")
    p_project_sub = p_project.add_subparsers(dest="project_cmd")

    p_new = p_project_sub.add_parser("new", help="Create a new agent plugin")
    p_new.add_argument("name", help="Plugin name")

    p_project_sub.add_parser("list", help="List all plugins (alias for 'nora agents')")

    p_index = p_project_sub.add_parser("index", help="Index a project for code-aware conversations")
    p_index.add_argument("path", help="Project directory to index")
    p_index.add_argument("--name", help="Project name (defaults to directory name)")
    p_index.add_argument("--search", help="Search the index after building")

    # config
    p_conf = sub.add_parser("config", help="Manage configuration")
    p_conf.add_argument(
        "action",
        choices=["show", "set", "use", "test"],
        help="Action to perform"
    )
    p_conf.add_argument("args", nargs="*", help="Action arguments")

    # serve
    p_serve = sub.add_parser("serve", help="Start REST API server")
    p_serve.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=8001, help="Port to bind to (default: 8001)")

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
        if args.team:
            run_team(config, args.team, plugin_loader)
        else:
            run_agent(plugin_loader, config, args.name, model=args.model)

    elif args.cmd == "agents":
        list_agents(plugin_loader)

    elif args.cmd == "project":
        if args.project_cmd == "new":
            scaffold_plugin(args.name)
        elif args.project_cmd == "list":
            list_agents(plugin_loader)
        elif args.project_cmd == "index":
            index_project_command(args.path, args.name, args.search)
        else:
            parser.parse_args(["project", "-h"])

    elif args.cmd == "config":
        config_command(config, args.action, args.args)

    elif args.cmd == "serve":
        serve_api(config, args.host, args.port)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
