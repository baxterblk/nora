#!/usr/bin/env python3
"""
NORA CLI — v0.2
Adds:
  - Persistent chat history (~/.nora/history.json)
  - Code-aware file context injection
  - External config (remote Ollama hook)
"""

import os
import sys
import argparse
import requests
import json
import readline
import pathlib
import importlib.util
from .config_manager import ConfigManager

# -------------------------
# Config & paths
# -------------------------
config = ConfigManager()
OLLAMA_URL = config.get_ollama_url()
DEFAULT_MODEL = config.config.get("model", "deepseek-coder:6.7b")
PLUGINS_DIR = pathlib.Path(__file__).parent / "plugins"
HISTORY_PATH = pathlib.Path.home() / ".nora" / "history.json"
MAX_FILE_TOKENS = 2000

# -------------------------
# Utils
# -------------------------
def ensure_dirs():
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

def load_history():
    ensure_dirs()
    if HISTORY_PATH.exists():
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(history):
    ensure_dirs()
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def trim_text(text, limit):
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]..."

def load_file_context(paths):
    ctx = []
    for p in paths or []:
        p = pathlib.Path(p)
        if p.exists() and p.is_file():
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            ctx.append(f"\n--- FILE: {p} ---\n{trim_text(content, MAX_FILE_TOKENS)}")
    return "\n".join(ctx)

# -------------------------
# Core Ollama Chat API
# -------------------------
def ollama_chat(messages, model=DEFAULT_MODEL, stream=False):
    url = f"{OLLAMA_URL}/api/chat"
    payload = {"model": model, "messages": messages, "stream": stream}

    with requests.post(url, json=payload, stream=stream) as resp:
        resp.raise_for_status()
        if stream:
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line.decode("utf-8"))
                delta = data.get("message", {}).get("content", "")
                if delta:
                    print(delta, end="", flush=True)
                if data.get("done"):
                    print()
                    break
        else:
            data = resp.json()
            print(data["message"]["content"])

# -------------------------
# Plugins loader
# -------------------------
def load_plugins():
    plugins = {}
    if not PLUGINS_DIR.exists():
        return plugins
    for f in PLUGINS_DIR.glob("*.py"):
        if f.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(f.stem, f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "register"):
            entry = mod.register()
            plugins[entry["name"]] = entry
    return plugins

# -------------------------
# Chat REPL
# -------------------------
def chat_loop(model=DEFAULT_MODEL, context_files=None, system=None):
    history = load_history()
    file_context = ""
    if context_files:
        file_context = load_file_context(context_files)
        if file_context:
            system = (system or "") + "\n\nYou have access to the following files:\n" + file_context

    print(f"NORA chat — model: {model}")
    print("Type '/exit' to quit, '/clear' to reset history.\n")

    while True:
        try:
            prompt = input("You> ")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting…")
            break

        cmd = prompt.strip().lower()
        if cmd in ["/exit", "exit", "quit"]:
            break
        if cmd == "/clear":
            history = []
            save_history(history)
            print("History cleared.")
            continue

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        for m in history[-10:]:
            messages.append(m)
        messages.append({"role": "user", "content": prompt})

        ollama_chat(messages, model=model, stream=True)

        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": "[streamed above]"})
        save_history(history)
        print()

# -------------------------
# Agent runner
# -------------------------
def run_agent(name, plugins, model=DEFAULT_MODEL):
    if name not in plugins:
        print(f"[!] No such agent: {name}")
        return
    agent = plugins[name]
    print(f"Running agent '{name}' — {agent.get('description','')}")
    agent["run"](model, ollama_chat)

# -------------------------
# CLI entry
# -------------------------
def main():
    parser = argparse.ArgumentParser(prog="nora", description="NORA CLI wrapper for Ollama")
    sub = parser.add_subparsers(dest="cmd")

    # chat
    p_chat = sub.add_parser("chat", help="Interactive REPL chat")
    p_chat.add_argument("-m", "--model", default=DEFAULT_MODEL)
    p_chat.add_argument("--system", help="Optional system prompt")
    p_chat.add_argument("--context", nargs="*", help="File(s) to include as context")

    # run
    p_run = sub.add_parser("run", help="One-shot prompt")
    p_run.add_argument("-m", "--model", default=DEFAULT_MODEL)
    p_run.add_argument("--context", nargs="*", help="File(s) to include as context")
    p_run.add_argument("prompt", nargs="+", help="Prompt text")

    # agent
    p_agent = sub.add_parser("agent", help="Run an installed agent")
    p_agent.add_argument("name", help="Agent name")
    p_agent.add_argument("-m", "--model", default=DEFAULT_MODEL)

    # list agents
    sub.add_parser("agents", help="List installed agents")

    # config management
    p_conf = sub.add_parser("config", help="Manage NORA configuration")
    p_conf.add_argument("action", choices=["show", "set", "use", "test"], help="Action")
    p_conf.add_argument("args", nargs="*", help="Arguments for action")

    args = parser.parse_args()
    plugins = load_plugins()

    if args.cmd == "chat":
        chat_loop(model=args.model, system=args.system, context_files=args.context)
    elif args.cmd == "run":
        text = " ".join(args.prompt)
        context_text = ""
        if args.context:
            context_text = load_file_context(args.context)
        messages = []
        if context_text:
            messages.append({"role": "system", "content": "Context files:\n" + context_text})
        messages.append({"role": "user", "content": text})
        ollama_chat(messages, model=args.model, stream=True)
    elif args.cmd == "agent":
        run_agent(args.name, plugins, model=args.model)
    elif args.cmd == "agents":
        if not plugins:
            print("No agents installed.")
        else:
            for n, a in plugins.items():
                print(f"{n} — {a.get('description','')}")
    elif args.cmd == "config":
        if args.action == "show":
            print(json.dumps(config.config, indent=2))
        elif args.action == "set" and len(args.args) == 2:
            config.set(args.args[0], args.args[1])
            print("Updated.")
        elif args.action == "use" and args.args:
            config.use_profile(args.args[0])
            print(f"Switched to profile: {args.args[0]}")
        elif args.action == "test":
            ok, resp = config.test_connection()
            if ok:
                print("✅ Connected:", resp)
            else:
                print("❌ Connection failed:", resp)
        else:
            print("Invalid usage. Try: nora config show|set|use|test")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
