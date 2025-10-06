# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NORA (No Rush on Anything) is a private, local AI agent CLI that runs entirely on local infrastructure. It provides an interface to Ollama for chat, code assistance, and extensible agent plugins, with a focus on user privacy and avoiding cloud dependencies.

**Current Status**: Early development (v0.2) - foundational features in place, Phase 1 of roadmap in progress.

## Architecture

### Package Structure

NORA is structured as a Python package with the following layout:
```
nora/
├── __init__.py           # Package initialization
├── cli.py               # Main CLI entry point (~240 lines)
├── config_manager.py    # Configuration system (~70 lines)
└── plugins/
    ├── __init__.py
    └── greeter.py       # Example agent plugin
```

### Core Components

1. **nora/cli.py** (Main CLI, ~240 lines)
   - Entry point for all commands (`chat`, `run`, `agent`, `agents`, `config`)
   - Chat REPL with persistent history (`~/.nora/history.json`)
   - File context injection for code-aware conversations
   - Plugin loader/runner system
   - Ollama API integration via streaming chat endpoint
   - Installed as `nora` command via console_scripts entrypoint

2. **nora/config_manager.py** (Configuration system, ~70 lines)
   - YAML-based configuration at `~/.nora/config.yaml`
   - Multi-profile support for different Ollama endpoints
   - Connection testing and validation
   - Default model: `deepseek-coder:6.7b`

3. **nora/plugins/** (Agent extension system)
   - Python modules that implement `register()` function
   - Returns dict with `name`, `description`, and `run` callback
   - Example: `greeter.py` demonstrates the minimal plugin interface
   - Plugins receive model name and `ollama_chat` function

### Key Design Patterns

- **Plugin Architecture**: All agents are dynamically loaded from `plugins/*.py` via `importlib`
- **Streaming-First**: Ollama responses stream to stdout for real-time feedback
- **Context Injection**: Files can be passed via `--context` to include code in prompts (truncated at 2000 chars)
- **History Management**: Last 10 messages kept in context, full history persisted to JSON
- **Profile System**: Switch between local/remote Ollama instances without reconfiguration

## Development Commands

### Installation

NORA uses modern Python packaging with `pyproject.toml` and hatchling:

```bash
# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dependencies
pip install -e .
```

This installs the `nora` command globally (within the virtualenv).

### Running NORA
```bash
# Interactive chat
nora chat

# With file context for code awareness
nora chat --context nora/config_manager.py nora/cli.py

# One-shot prompt
nora run "explain this code" --context nora/cli.py

# Run an agent
nora agent greeter

# List available agents
nora agents
```

### Configuration Management
```bash
# Show current config
nora config show

# Set a value
nora config set model llama3.2:3b
nora config set ollama.url http://remote-server:11434

# Test Ollama connection
nora config test

# Switch profiles (if multiple configured)
nora config use production
```

### Plugin Development

Create a new agent plugin in `nora/plugins/yourplugin.py`:

```python
def register():
    def run(model, call_fn):
        messages = [{"role": "user", "content": "Your prompt here"}]
        call_fn(messages, model=model, stream=True)

    return {
        "name": "yourplugin",
        "description": "What your agent does",
        "run": run
    }
```

Plugins are automatically discovered at runtime from the `nora/plugins/` directory.

The `call_fn` parameter is the `ollama_chat()` function with signature:
- `messages`: List of `{"role": "user|assistant|system", "content": "..."}`
- `model`: Model name string (default from config)
- `stream`: Boolean (default False, but agents should use True for UX)

## Ollama Integration

NORA expects Ollama to be running and accessible. Default: `http://localhost:11434`

**Required Ollama API endpoint**: `/api/chat` (streaming)

**Message format**:
```python
{
    "model": "deepseek-coder:6.7b",
    "messages": [
        {"role": "system", "content": "optional system prompt"},
        {"role": "user", "content": "user message"},
        {"role": "assistant", "content": "previous response"}
    ],
    "stream": true
}
```

## File Locations

- **Config**: `~/.nora/config.yaml`
- **Chat History**: `~/.nora/history.json`
- **Plugins**: `nora/plugins/*.py` (within the installed package)
- **Virtual Environment**: `.venv/` (if using recommended setup)

## Important Implementation Details

### History Truncation
Only the last 10 messages are sent to Ollama (nora/cli.py:139), but full history is persisted. This prevents context window overflow while maintaining conversation continuity.

### File Context Truncation
File content is limited to `MAX_FILE_TOKENS = 2000` characters per file (nora/cli.py:28). Truncated files show `...[truncated]...` marker.

### SSL Verification
SSL verification is disabled by default for Ollama connections (`verify_ssl: False` in config). This is intentional for local/self-signed certificate scenarios.

### Error Handling
Current error handling is minimal (try/except with silent fallback in history loading). Future work should add more robust error reporting.

## Roadmap Context

This project is in **Phase 1: Foundation & Environment**. Key upcoming work:
- Pre-commit hooks for signed commits
- Repository layout finalization
- Testing framework setup
- Multi-contributor environment alignment

See ROADMAP.md for full Phase 1 task list and future phases.

## Dependencies

**Runtime dependencies** (auto-installed via pip):
- **requests** >= 2.25.0: Ollama HTTP API calls
- **PyYAML** >= 5.4.0: Configuration file parsing

**Standard library** (no installation needed):
- **readline**: Command-line editing in REPL
- **pathlib**: File path handling
- **importlib**: Dynamic plugin loading
- **argparse**: CLI argument parsing

**Build system**:
- **hatchling**: Modern PEP 517 build backend

Python 3.7+ required (f-strings, pathlib, type hints in stdlib).

All dependencies and metadata are defined in `pyproject.toml`.
