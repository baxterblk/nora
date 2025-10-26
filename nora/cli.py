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
import requests  # type: ignore  # type: ignore
import sys
from typing import List, Optional

import argcomplete

from .core import utils
from .core.actions import ActionsManager
from .core.chat import OllamaChat, load_file_context
from .core.config import ConfigManager, DEFAULT_CONFIG
from .core.history import HistoryManager
from .core.indexer import ProjectIndexer
from .core.interpreter import ActionInterpreter
from .core.plugins import PluginLoader
from .core.setup import first_run_wizard, should_run_wizard
from .core.tool_interpreter import ToolInterpreter
from .core.tools import ToolRegistry

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


def setup_readline_completion():
    """Sets up readline completion for / commands."""
    commands = ["/exit", "/clear"]

    def completer(text, state):
        line = readline.get_line_buffer()

        if line.startswith("/"):
            options = [cmd for cmd in commands if cmd.startswith(text)]
            if state < len(options):
                return options[state]
            else:
                return None
        return None

    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")


def chat_loop(
    config: ConfigManager,
    history_manager: HistoryManager,
    model: Optional[str] = None,
    context_files: Optional[List[str]] = None,
    system: Optional[str] = None,
    enable_actions: bool = False,
    safe_mode: bool = True,
    enable_tools: bool = False,
    auto_context: bool = False,
) -> None:
    """
    Run an interactive chat REPL with optional file actions support.

    Args:
        config: Configuration manager instance
        history_manager: History manager instance
        model: Model name (defaults to config)
        context_files: List of file paths for context injection
        system: System prompt
        enable_actions: If True, execute file operations from model output
        safe_mode: If True, prompt before overwriting files (ignored if enable_actions=False)
    """
    setup_readline_completion()
    model = model or config.get_model()
    ollama_url = config.get_ollama_url()

    # Get compatibility mode and endpoint (default to "chat" and None for auto-detect)
    compatibility_mode = config.get("ollama.compatibility", "chat")
    endpoint = normalize_endpoint(config.get("ollama.endpoint", None))

    # Initialize chat client
    chat_client = OllamaChat(
        ollama_url, model, compatibility_mode=compatibility_mode, endpoint=endpoint
    )

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

    # Initialize tool system if enabled
    tool_registry: Optional[ToolRegistry] = None
    tool_interpreter: Optional[ToolInterpreter] = None
    if enable_tools:
        tool_registry = ToolRegistry()
        tool_interpreter = ToolInterpreter(tool_registry)
        utils.info("Tools enabled")

    # Initialize actions system if enabled
    actions_manager: Optional[ActionsManager] = None
    interpreter: Optional[ActionInterpreter] = None

    if enable_actions:
        import os

        actions_manager = ActionsManager(project_root=os.getcwd(), safe_mode=safe_mode)
        interpreter = ActionInterpreter()
        utils.info(f"Actions enabled (safe_mode={'on' if safe_mode else 'off'})")
        logger.info(f"ActionsManager initialized at {os.getcwd()}")

    # Initialize Project Indexer for auto-context
    indexer: Optional[ProjectIndexer] = None
    if auto_context:
        utils.info("Auto-context is enabled. Indexing current directory...")
        try:
            indexer = ProjectIndexer()
            indexer.index_project(".")
            utils.info(f"Indexed {indexer.get_index_stats()['total_files']} files.")
        except Exception as e:
            utils.error(f"Auto-context failed during indexing: {e}")

    # Load file context if provided
    file_context = ""
    if context_files:
        file_context = load_file_context(context_files)
        if file_context:
            system = (
                (system or "")
                + "\n\nYou have access to the following files:\n"
                + file_context
            )
            utils.info(f"Loaded context from {len(context_files)} file(s)")

    # Add actions system prompt if actions are enabled
    if enable_actions and interpreter:
        actions_prompt = interpreter.format_system_prompt()
        system = (system or "") + "\n\n" + actions_prompt

    print(
        f"\nType {utils.colored('/exit', utils.Colors.CYAN)} to quit, {utils.colored('/clear', utils.Colors.CYAN)} to reset history.\n"
    )

    while True:
        try:
            prompt = input(utils.colored("│ ", utils.Colors.CYAN, bold=True))
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

        if auto_context and indexer:
            try:
                results = indexer.search(prompt, max_results=3)
                if results:
                    context_files = [result["path"] for result in results]
                    file_context = load_file_context(context_files)
                    if file_context:
                        system = (
                            (system or "")
                            + "\n\nYou have access to the following files:\n"
                            + file_context
                        )
                        utils.info(f"Loaded context from {len(context_files)} file(s)")
            except Exception as e:
                utils.error(f"Auto-context failed during search: {e}")

        # Summarize history if it gets too long
        history_summary_threshold = config.get("history_summary_threshold", 20)
        if len(history) > history_summary_threshold:
            utils.info("History is long, summarizing...")
            try:
                history_text = "\n".join([m["content"] for m in history])
                summary = chat_client.summarize(history_text)
                if summary:
                    history_manager.clear()
                    history = []
                    history = history_manager.add_message(
                        history,
                        "system",
                        f"This is a summary of the previous conversation:\n{summary}",
                    )
                    utils.success("History summarized.")
                else:
                    utils.warning("History summarization failed.")
            except Exception as e:
                utils.error(f"History summarization failed: {e}")

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
            response = chat_client.chat(messages, model=model, stream=True)

            # Extract response content
            response_text = ""
            if response:
                if "message" in response:
                    response_text = response["message"]["content"]
                elif "response" in response:
                    response_text = response["response"]

            # Update history
            history = history_manager.add_message(history, "user", prompt)
            history = history_manager.add_message(
                history, "assistant", response_text or "[streamed above]"
            )
            print()

            # Process tool calls if enabled
            if enable_tools and tool_interpreter and response_text:
                tool_calls = tool_interpreter.extract_tool_calls(response_text)
                for tool_call in tool_calls:
                    utils.info(f"Executing tool: {tool_call.tool_name}")
                    try:
                        if tool_registry:
                            result = tool_registry.run_tool(
                                tool_call.tool_name, tool_call.parameters
                            )
                        history = history_manager.add_message(
                            history,
                            "tool",
                            json.dumps(
                                {"tool_name": tool_call.tool_name, "result": result}
                            ),
                        )
                        utils.success(
                            f"Tool {tool_call.tool_name} executed successfully."
                        )
                    except Exception as e:
                        utils.error(f"Tool {tool_call.tool_name} failed: {e}")
                        history = history_manager.add_message(
                            history,
                            "tool",
                            json.dumps(
                                {"tool_name": tool_call.tool_name, "error": str(e)}
                            ),
                        )

            # Process actions if enabled
            if enable_actions and interpreter and actions_manager and response_text:
                file_actions = interpreter.extract_actions(response_text)
                command_actions = interpreter.extract_commands(response_text)

                # Execute file actions
                for action in file_actions:
                    if action.action_type == "create" and action.content:
                        success, msg = actions_manager.create_file(
                            action.path, action.content
                        )
                        if success:
                            utils.success(msg)
                        else:
                            utils.error(msg)

                    elif action.action_type == "append" and action.content:
                        success, msg = actions_manager.append_file(
                            action.path, action.content
                        )
                        if success:
                            utils.info(f"✏️  {msg}")
                        else:
                            utils.error(msg)

                    elif action.action_type == "read":
                        success, content = actions_manager.read_file(action.path)
                        if success:
                            utils.info(f"📖 Read: {action.path} ({len(content)} chars)")
                        else:
                            utils.error(content)

                    elif action.action_type == "delete":
                        success, msg = actions_manager.delete_file(action.path)
                        if success:
                            utils.info(f"🗑️  {msg}")
                        else:
                            utils.error(msg)

                # Execute command actions
                for cmd_action in command_actions:
                    utils.info(f"⚙️  Running: {cmd_action.command}")
                    success, output = actions_manager.run_command(
                        cmd_action.command, cwd=cmd_action.cwd
                    )
                    if success:
                        utils.success(f"Command succeeded: {cmd_action.command}")
                        if output.strip():
                            print(output)
                    else:
                        utils.error(f"Command failed: {output}")

        except requests.exceptions.ConnectionError as e:
            utils.error(f"Connection to Ollama failed: {e}")
            logger.exception("Ollama connection failed")
        except Exception as e:
            utils.error(f"An unexpected error occurred: {e}")
            logger.exception("An unexpected error occurred in chat_loop")


def run_one_shot(
    config: ConfigManager,
    prompt_text: str,
    model: Optional[str] = None,
    context_files: Optional[List[str]] = None,
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

    chat_client = OllamaChat(
        ollama_url, model, compatibility_mode=compatibility_mode, endpoint=endpoint
    )

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
            messages.append(
                {"role": "system", "content": "Context files:\n" + file_context}
            )

    messages.append({"role": "user", "content": prompt_text})

    try:
        chat_client.chat(messages, model=model, stream=True)
        print()
    except requests.exceptions.ConnectionError as e:
        utils.error(f"Connection to Ollama failed: {e}")
        logger.exception("Ollama connection failed")
        sys.exit(1)
    except Exception as e:
        utils.error(f"An unexpected error occurred: {e}")
        logger.exception("An unexpected error occurred in run_one_shot")
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
    # Determine column widths
    max_name = max(len(name) for name in plugins.keys())
    max_desc = 0
    for plugin in plugins.values():
        desc = plugin.get("description", "No description")
        if len(desc) > max_desc:
            max_desc = len(desc)

    # Print header
    print(
        f"  {utils.colored('Name'.ljust(max_name), utils.Colors.CYAN, bold=True)}  {utils.colored('Description'.ljust(max_desc), utils.Colors.CYAN, bold=True)}"
    )
    print(f"  {'-' * max_name}  {'-' * max_desc}")

    for name, plugin in sorted(plugins.items()):
        desc = plugin.get("description", "No description")
        print(f"  {name.ljust(max_name)}  {desc.ljust(max_desc)}")


def run_agent(
    plugin_loader: PluginLoader,
    config: ConfigManager,
    name: str,
    model: Optional[str] = None,
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
    chat_client = OllamaChat(
        ollama_url, model, compatibility_mode=compatibility_mode, endpoint=endpoint
    )

    # Auto-detect and save endpoint if needed
    if not endpoint:
        detected = chat_client.get_endpoint()
        if detected:
            config.set("ollama.endpoint", detected)

    def agent_chat(messages, model=model, stream=False):
        chat_client.chat(messages, model=model, stream=stream)

    try:
        plugin["run"](model, agent_chat)
    except requests.exceptions.ConnectionError as e:
        utils.error(f"Connection to Ollama failed for agent '{name}': {e}")
        logger.exception(f"Ollama connection failed for agent '{name}' failed")
        sys.exit(1)
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
        action: Action to perform (show, set, use, test, path, reset)
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

    elif action == "path":
        print(config.path)

    elif action == "reset":
        config.config = DEFAULT_CONFIG.copy()
        config.save()
        utils.success(f"Configuration reset to defaults at {config.path}")


def run_team(
    config: ConfigManager, team_config_path: str, plugin_loader: PluginLoader
) -> None:
    """
    Run a multi-agent team from config file.

    Args:
        config: Configuration manager instance
        team_config_path: Path to team config YAML
        plugin_loader: Plugin loader instance
    """
    from .core.orchestrator import AgentTask, Orchestrator, load_team_config

    try:
        utils.info(f"Loading team config: {team_config_path}")
        team_config = load_team_config(team_config_path)

        # Load plugins
        plugins = plugin_loader.load_plugins()

        # Create orchestrator
        model = team_config.get("model", config.get_model())
        compatibility_mode = config.get("ollama.compatibility", "chat")
        endpoint = normalize_endpoint(config.get("ollama.endpoint", None))
        chat_client = OllamaChat(
            config.get_ollama_url(),
            model,
            compatibility_mode=compatibility_mode,
            endpoint=endpoint,
        )

        # Auto-detect and save endpoint if needed
        if not endpoint:
            detected = chat_client.get_endpoint()
            if detected:
                config.set("ollama.endpoint", detected)

        orchestrator = Orchestrator(model=model, call_fn=chat_client.chat)

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
                config=agent_config.get("config", {}),
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
                utils.error(
                    f"  {agent_name}: Failed - {result.get('error', 'Unknown error')}"
                )

    except Exception as e:
        logger.error(f"Team execution failed: {e}", exc_info=True)
        utils.error(f"Team execution failed: {e}")
        sys.exit(1)


def index_project_command(
    project_path: str,
    project_name: Optional[str] = None,
    search_query: Optional[str] = None,
) -> None:
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
            results = indexer.search(search_query)

            if results:
                utils.success(f"Found {len(results)} results:")
                for i, result in enumerate(results[:5], 1):
                    print(
                        f"\n{i}. {result['relative_path']} (score: {result['relevance_score']})"
                    )
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
        prog="nora", description="NORA - No Rush (on) Anything: Local AI agent CLI"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument("--log-file", help="Log to file")

    parser.add_argument(
        "--no-wizard", action="store_true", help="Skip first-run setup wizard"
    )

    sub = parser.add_subparsers(dest="cmd", help="Commands")

    # chat
    p_chat = sub.add_parser("chat", help="Interactive REPL chat")
    p_chat.add_argument("-m", "--model", help="Model name")
    p_chat.add_argument("--system", help="System prompt")
    p_chat.add_argument("--context", nargs="*", help="File(s) to include as context")
    p_chat.add_argument(
        "--enable-actions",
        action="store_true",
        help="Enable file operations and command execution from model output",
    )
    p_chat.add_argument(
        "--no-confirm",
        action="store_true",
        help="Skip confirmation prompts for file overwrites (use with --enable-actions)",
    )

    p_chat.add_argument(
        "--enable-tools",
        action="store_true",
        help="Enable tool execution from model output",
    )

    p_chat.add_argument(
        "--auto-context",
        action="store_true",
        help="Automatically select relevant files from the current directory as context",
    )

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

    p_index = p_project_sub.add_parser(
        "index", help="Index a project for code-aware conversations"
    )
    p_index.add_argument("path", help="Project directory to index")
    p_index.add_argument("--name", help="Project name (defaults to directory name)")
    p_index.add_argument("--search", help="Search the index after building")

    # config
    p_conf = sub.add_parser("config", help="Manage configuration")
    p_conf.add_argument(
        "action",
        choices=["show", "set", "use", "test", "path", "reset"],
        help="Action to perform",
    )
    p_conf.add_argument("args", nargs="*", help="Action arguments")

    # serve
    p_serve = sub.add_parser("serve", help="Start REST API server")
    p_serve.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    p_serve.add_argument(
        "--port", type=int, default=8001, help="Port to bind to (default: 8001)"
    )

    argcomplete.autocomplete(parser)

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    utils.setup_logging(log_level, args.log_file)

    # Run first-run wizard if needed
    # Only run for commands that need configuration (not config, serve, or help)
    if (
        not args.no_wizard
        and args.cmd
        and args.cmd not in ["config"]
        and should_run_wizard()
    ):
        first_run_wizard()

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
            system=args.system,
            enable_actions=args.enable_actions,
            safe_mode=not args.no_confirm,
            enable_tools=args.enable_tools,
            auto_context=args.auto_context,
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
