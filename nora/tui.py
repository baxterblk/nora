#!/usr/bin/env python3
# nora_chat.py
# A single-file terminal chat UI for NORA with a Gemini/Claude/Codex-style look.

import asyncio
import os
import sys
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console, Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout

from nora.core.actions import ActionsManager
from nora.core.chat import OllamaChat, load_file_context
from nora.core.config import ConfigManager
from nora.core.history import HistoryManager
from nora.core.interpreter import ActionInterpreter
from nora.core.tool_interpreter import ToolInterpreter
from nora.core.tools import ToolRegistry

# --------------------------- 
# Tunables / Style
# --------------------------- 
THEME = Theme({
    "header": "bold cyan",
    "badge": "black on bright_white",
    "dim": "grey58",
    "role_user": "bold white",
    "role_assistant": "bold green",
    "model": "magenta",
    "warn": "bold yellow",
    "err": "bold red",
    "hint": "italic grey58",
    "time": "cyan",
})
console = Console(theme=THEME)

APP_NAME = "NORA CLI"

# --------------------------- 
# Chat state
# --------------------------- 
@dataclass
class Message:
    role: str               # "user" | "assistant" | "system"
    content: str
    time: datetime = field(default_factory=datetime.now)

@dataclass
class ChatState:
    messages: List[Message] = field(default_factory=list)
    status: str = "Ready"
    token_count: int = 0
    last_error: Optional[str] = None
    pasted_store: dict = field(default_factory=dict)  # id -> text (for large paste placeholders)

state = ChatState()

# --------------------------- 
# Helpers
# --------------------------- 
def update_token_count() -> None:
    """Recalculate the approximate token count displayed in the status bar."""
    state.token_count = sum(len(m.content.split()) for m in state.messages)

# --------------------------- 
# Rendering
# --------------------------- 
def render_header(model_name: str) -> Panel:
    left = Text(APP_NAME, style="header")
    right = Text(f"Model: {model_name}", style="model")
    line = Text.assemble(left, Text("  │  ", style="dim"), right)
    return Panel(line, box=ROUNDED, border_style="cyan", padding=(0,1))

def render_badges() -> Text:
    badges = Text()
    badges.append("  interactive ", style="badge")
    badges.append("  chat ", style="badge")
    badges.append("  beta ", style="badge")
    return badges

def render_messages() -> Group:
    rows = []
    for m in state.messages[-200:]:
        role_style = "role_user" if m.role == "user" else "role_assistant" if m.role == "assistant" else "dim"
        ts = Text(m.time.strftime("%H:%M:%S"), style="time")
        role = Text(m.role.upper(), style=role_style)
        header = Text.assemble(ts, Text("  "), role)
        rows.append(Text("\n"))
        rows.append(header)
        rows.append(Rule(characters="─", style="dim"))
        content = Markdown(m.content) if any(x in m.content for x in ("#", "* ", "`", "> ")) else Text(m.content)
        rows.append(content)
    if not rows:
        rows = [Align.center(Text("No messages yet. Start typing below.", style="hint"), vertical="middle")]
    return Group(*rows)

def render_status() -> Panel:
    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    left = Text(state.status, style="dim")
    right = Text(f"Tokens: {state.token_count}", style="dim")
    grid.add_row(left, right)
    err_panel = None
    if state.last_error:
        err_panel = Panel(Text(state.last_error, style="err"), border_style="red", box=ROUNDED)
        return Group(Panel(grid, border_style="cyan", box=ROUNDED), err_panel)
    return Panel(grid, border_style="cyan", box=ROUNDED)

def render_hints() -> Text:
    return Text(
        "Commands: /help  •  /clear history  •  /quit to exit",
        style="hint",
    )

def build_screen(model_name: str) -> Panel:
    content = Group(
        render_header(model_name),
        render_badges(),
        render_messages(),
        render_status(),
        render_hints(),
        Text("")  # bottom padding
    )
    return Panel(content, box=ROUNDED, border_style="cyan", padding=(1,2))

# --------------------------- 
# Main loop
# --------------------------- 
async def run_chat_ui(
    config: ConfigManager,
    history_manager: HistoryManager,
    model: Optional[str] = None,
    context_files: Optional[List[str]] = None,
    system: Optional[str] = None,
    enable_actions: bool = False,
    safe_mode: bool = True,
    enable_tools: bool = False,
    auto_context: bool = False,
):
    model_name = model or config.get_model()
    chat_client = OllamaChat(config.get_ollama_url(), model_name)
    actions_manager = ActionsManager(safe_mode=safe_mode) if enable_actions else None
    action_interpreter = ActionInterpreter() if enable_actions else None
    tool_registry = ToolRegistry() if enable_tools else None
    tool_interpreter = ToolInterpreter(tool_registry) if enable_tools else None

    base_messages: List[dict] = []
    if system:
        base_messages.append({"role": "system", "content": system})
    file_context = load_file_context(context_files)
    if file_context:
        base_messages.append(
            {
                "role": "system",
                "content": "Context files provided:\n" + file_context,
            }
        )
    if action_interpreter:
        base_messages.append(
            {"role": "system", "content": action_interpreter.format_system_prompt()}
        )
    if tool_registry and tool_registry.tools:
        tool_lines = [
            "You can call registered tools by returning JSON like "
            '[{"tool_name": "name", "parameters": {...}}].',
            "Available tools:",
        ]
        for tool in sorted(tool_registry.tools.values(), key=lambda t: t["name"]):
            description = tool.get("description", "No description provided")
            tool_lines.append(f"- {tool['name']}: {description}")
        base_messages.append({"role": "system", "content": "\n".join(tool_lines)})

    prompt_session = PromptSession(history=InMemoryHistory())
    history = history_manager.load()
    for msg in history:
        state.messages.append(Message(role=msg["role"], content=msg["content"]))
    update_token_count()

    def record_system_message(text: str, persist: bool = False) -> None:
        nonlocal history
        if not text:
            return
        state.messages.append(Message("system", text))
        if persist:
            history = history_manager.add_message(history, "system", text)
        update_token_count()

    def handle_actions(response_text: str) -> None:
        if not action_interpreter:
            return
        file_actions = action_interpreter.extract_actions(response_text)
        command_actions = action_interpreter.extract_commands(response_text)
        if not file_actions and not command_actions:
            return
        lines: List[str] = []
        if not actions_manager:
            lines.append("Actions detected but execution is disabled.")
        elif actions_manager.safe_mode:
            if file_actions:
                lines.append("Detected file actions (safe mode, not executed):")
                for action in file_actions:
                    lines.append(f"- {action.action_type} {action.path}")
                    if action.content:
                        preview = textwrap.shorten(
                            " ".join(action.content.split()), width=140
                        )
                        lines.append(f"    Preview: {preview}")
            if command_actions:
                lines.append("Detected commands (safe mode, not executed):")
                for command in command_actions:
                    lines.append(f"- {command.command}")
            lines.append(
                "Re-run with --no-confirm to apply actions automatically."
            )
        else:
            if file_actions:
                lines.append("Applied file actions:")
                for action in file_actions:
                    try:
                        if action.action_type == "create":
                            success, message = actions_manager.create_file(
                                action.path, action.content or "", force=True
                            )
                        elif action.action_type == "append":
                            success, message = actions_manager.append_file(
                                action.path, action.content or ""
                            )
                        elif action.action_type == "read":
                            success, message = actions_manager.read_file(action.path)
                        elif action.action_type == "delete":
                            success, message = actions_manager.delete_file(
                                action.path, force=True
                            )
                        else:
                            success = False
                            message = f"Unsupported action: {action.action_type}"
                        status = "✓" if success else "✗"
                        lines.append(f"  {status} {message}")
                        if action.action_type == "read" and success and message:
                            snippet = textwrap.shorten(
                                " ".join(message.split()), width=160
                            )
                            lines.append(f"    Output: {snippet}")
                    except Exception as exc:  # pragma: no cover - defensive
                        lines.append(f"  ✗ Error applying {action.path}: {exc}")
            if command_actions:
                lines.append("Command execution results:")
                for command in command_actions:
                    try:
                        success, output = actions_manager.run_command(command.command)
                        status = "✓" if success else "✗"
                        lines.append(f"  {status} {command.command}")
                        if output:
                            snippet = textwrap.shorten(
                                " ".join(output.split()), width=160
                            )
                            lines.append(f"    Output: {snippet}")
                    except Exception as exc:  # pragma: no cover - defensive
                        lines.append(
                            f"  ✗ Error running '{command.command}': {exc}"
                        )
        record_system_message("\n".join(lines), persist=True)

    def handle_tool_calls(response_text: str) -> None:
        if not tool_interpreter:
            return
        tool_calls = tool_interpreter.extract_tool_calls(response_text)
        if not tool_calls:
            return
        lines = ["Tool execution results:"]
        for call in tool_calls:
            if not tool_registry or call.tool_name not in tool_registry.tools:
                lines.append(f"- {call.tool_name}: tool not available")
                continue
            try:
                result = tool_interpreter.run_tool(call)
                output = str(result).strip() or "(no output)"
                lines.append(f"- {call.tool_name}: success")
                lines.append(textwrap.indent(output, "    "))
            except Exception as exc:  # pragma: no cover - defensive
                lines.append(f"- {call.tool_name}: error {exc}")
        record_system_message("\n".join(lines), persist=True)

    async def llm_reply(prompt: str):
        nonlocal history
        history = history_manager.add_message(history, "user", prompt)
        state.messages.append(Message("user", prompt))
        update_token_count()

        messages: List[dict] = list(base_messages)
        messages.extend(history_manager.get_recent(history, limit=10))

        if auto_context:
            related = history_manager.search_history(prompt, k=3)
            if related:
                context_note = "Auto-context suggestions:\n" + "\n---\n".join(related)
                messages.append({"role": "system", "content": context_note})
                state.messages.append(Message("system", context_note))
                update_token_count()

        response_stream = chat_client.chat(messages, stream=True)

        full_response = ""
        assistant_message = Message("assistant", "")
        state.messages.append(assistant_message)
        for chunk in response_stream:
            full_response += chunk
            assistant_message.content = full_response
            update_token_count()
            live.update(build_screen(model_name))

        history = history_manager.add_message(history, "assistant", full_response)
        update_token_count()
        handle_actions(full_response)
        handle_tool_calls(full_response)

    console.clear()
    panel = build_screen(model_name)
    with Live(panel, console=console, screen=True, refresh_per_second=30) as live, patch_stdout():
        while True:
            live.update(build_screen(model_name))

            try:
                line = await prompt_session.prompt_async(">>> ")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Bye.[/dim]")
                return

            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("/"):
                command = stripped[1:].lower()
                if command in {"quit", "exit"}:
                    console.print("\n[dim]Bye.[/dim]")
                    return
                if command == "help":
                    record_system_message(
                        "Commands: /help, /clear, /quit — actions/tools run depends on flags."
                    )
                elif command == "clear":
                    history_manager.clear()
                    history = []
                    state.messages.clear()
                    state.status = "History cleared"
                    state.last_error = None
                    record_system_message("Chat history cleared.")
                else:
                    state.last_error = f"Unknown command: {command}"
                live.update(build_screen(model_name))
                continue

            state.status = "Thinking…"
            state.last_error = None
            live.update(build_screen(model_name))

            try:
                await llm_reply(stripped)
                state.status = "Ready"
            except Exception as e:  # pragma: no cover - user feedback path
                state.last_error = f"LLM error: {e}"
                state.status = "Error"

            live.update(build_screen(model_name))