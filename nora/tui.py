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

from nora.core.config import ConfigManager
from nora.core.history import HistoryManager
from nora.core.chat import OllamaChat

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
    return Text("Tips: /help  •  Shift+Enter = newline  •  Ctrl+L = clear", style="hint")

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

    # Load history
    history = history_manager.load()
    for msg in history:
        state.messages.append(Message(role=msg["role"], content=msg["content"]))

    async def llm_reply(prompt: str):
        nonlocal history
        history = history_manager.add_message(history, "user", prompt)
        state.messages.append(Message("user", prompt))

        messages = []
        if system:
            messages.append({"role": "system", "content": system})

        for msg in history_manager.get_recent(history, limit=10):
            messages.append(msg)

        response_stream = chat_client.chat(messages, stream=True)

        full_response = ""
        state.messages.append(Message("assistant", ""))
        for chunk in response_stream:
            full_response += chunk
            state.messages[-1].content = full_response
            live.update(build_screen(model_name))

        history = history_manager.add_message(history, "assistant", full_response)

    console.clear()
    panel = build_screen(model_name)
    with Live(panel, console=console, screen=True, refresh_per_second=30) as live, patch_stdout():
        while True:
            live.update(build_screen(model_name))

            try:
                line = await PromptSession().prompt_async(">>> ")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Bye.[/dim]")
                return

            if not line.strip():
                continue

            state.status = "Thinking…"
            state.last_error = None
            live.update(build_screen(model_name))

            try:
                await llm_reply(line)
                state.status = "Ready"
            except Exception as e:
                state.last_error = f"LLM error: {e}"
                state.status = "Error"

            live.update(build_screen(model_name))