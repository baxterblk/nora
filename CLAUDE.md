# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NORA (No Rush on Anything) is a private, local AI agent CLI that runs entirely on local infrastructure. It provides an interface to Ollama for chat, code assistance, and extensible agent plugins, with a focus on user privacy and avoiding cloud dependencies.

**Current Status**: v0.3.0 - Production-ready with modular architecture, comprehensive testing, and CI/CD.

## Architecture

### Package Structure

NORA follows a modular architecture with clear separation of concerns:

```
nora/
├── __init__.py              # Package metadata (v0.3.0)
├── cli.py                   # Main CLI interface (~400 lines)
├── core/                    # Core functionality modules
│   ├── __init__.py          # Core exports
│   ├── config.py            # Configuration management
│   ├── history.py           # Chat history persistence
│   ├── chat.py              # Ollama API client
│   ├── plugins.py           # Plugin loader/manager
│   └── utils.py             # Colored output & logging
├── plugins/                 # Agent plugins directory
│   ├── __init__.py
│   └── greeter.py           # Example plugin
└── config_manager.py        # Legacy (deprecated, use core.config)

tests/
├── __init__.py
├── test_config.py           # ConfigManager tests
├── test_history.py          # HistoryManager tests
└── test_plugins.py          # PluginLoader tests
```

### Core Modules

#### 1. **nora/core/config.py** - Configuration Management
- `ConfigManager`: YAML-based configuration with profile support
- Type-hinted methods with comprehensive docstrings
- Structured logging throughout
- Connection testing to Ollama API

Key Methods:
- `load()`, `save()`: Config file I/O
- `get(key_path)`, `set(key_path, value)`: Dot-notation access
- `use_profile(name)`: Switch between environments
- `test_connection()`: Validate Ollama connectivity

#### 2. **nora/core/history.py** - History Management
- `HistoryManager`: Persistent JSON-based chat history
- Automatic directory creation
- Recent message retrieval (windowing)
- Clear history functionality

Key Methods:
- `load()`, `save(history)`: Persistence layer
- `add_message(history, role, content)`: Append with save
- `get_recent(history, limit=10)`: Context window management
- `clear()`: Reset history

#### 3. **nora/core/chat.py** - Ollama Integration
- `OllamaChat`: Streaming chat client
- `load_file_context(paths)`: File injection for code-aware conversations
- Automatic truncation at 2000 chars per file
- Error handling with logging

Key Methods:
- `chat(messages, model, stream)`: Send requests to Ollama
- `_handle_stream(response)`: Process streaming responses

#### 4. **nora/core/plugins.py** - Plugin System
- `PluginLoader`: Dynamic plugin discovery and loading
- Validation of plugin structure
- Safe error handling for malformed plugins
- Run-time plugin execution

Key Methods:
- `load_plugins()`: Discover all .py files in plugins/
- `get_plugin(name, plugins)`: Retrieve by name
- `run_plugin(name, plugins, model, chat_fn)`: Execute plugin

#### 5. **nora/core/utils.py** - Utilities
- `Colors`: ANSI color code constants
- Output functions: `success()`, `warning()`, `error()`, `info()`
- `connection_banner()`: Startup status display
- `setup_logging()`: Configure structured logging

### Key Design Patterns

- **Modular Core Architecture**: Separation of concerns with dedicated modules
- **Type Hints**: Comprehensive type annotations for IDE support
- **Structured Logging**: Python logging framework with file/console handlers
- **Colored Output**: ANSI-based terminal colors for UX
- **Plugin Architecture**: Dynamic loading via importlib
- **Context Injection**: File content for code-aware conversations
- **History Windowing**: Last 10 messages sent to API, full history persisted

## Development Commands

### Installation

NORA uses modern Python packaging with `pyproject.toml` and hatchling:

```bash
# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dependencies
pip install -e .

# Install with development dependencies (pytest, coverage, etc.)
pip install -e ".[dev]"
```

### Running NORA

All commands support verbose logging with `-v` flag and log file output with `--log-file`:

```bash
# Interactive chat with connection banner
nora chat

# Chat with file context for code awareness
nora chat --context nora/core/config.py nora/core/chat.py

# Chat with verbose logging
nora -v chat

# One-shot prompt
nora run "explain this code" --context nora/cli.py

# Run an agent
nora agent greeter

# List available agents
nora agents
```

### Project Management

New in v0.3: Plugin scaffolding commands

```bash
# Create a new plugin from template
nora project new my-agent

# List all plugins (alias for nora agents)
nora project list
```

This creates `nora/plugins/my_agent.py` with a complete template including:
- register() function
- run() function with proper signature
- Docstrings and TODO comments

### Configuration Management

```bash
# Show current config
nora config show

# Set a value (supports dot notation)
nora config set model llama3.2:3b
nora config set ollama.url http://remote-server:11434

# Test Ollama connection (with colored output)
nora config test

# Switch profiles (if multiple configured)
nora config use production
```

### Testing

```bash
# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=nora --cov-report=html

# Run tests for specific module
pytest tests/test_plugins.py::TestPluginLoader::test_load_valid_plugin
```

### Plugin Development

Create a new agent plugin in `nora/plugins/yourplugin.py`:

```python
"""
Your Plugin Description

Detailed description of what your agent does.
"""


def register():
    """Register the plugin with NORA."""

    def run(model, call_fn):
        """
        Run the agent logic.

        Args:
            model: Model name to use
            call_fn: Ollama chat function with signature:
                     call_fn(messages, model=model, stream=False)
        """
        messages = [
            {"role": "user", "content": "Your prompt here"}
        ]
        call_fn(messages, model=model, stream=True)

    return {
        "name": "yourplugin",          # Must match filename
        "description": "What it does",  # Shown in nora agents
        "run": run                      # Callable function
    }
```

Plugins are automatically discovered at runtime from `nora/plugins/*.py`.

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

**Connection Banner**: On `nora chat`, displays:
```
──────────────────────────────────────────────────────────────────────
NORA | Connected | http://localhost:11434 | Model: deepseek-coder:6.7b
──────────────────────────────────────────────────────────────────────
```

## File Locations

- **Config**: `~/.nora/config.yaml`
- **Chat History**: `~/.nora/history.json`
- **Plugins**: `nora/plugins/*.py` (within the installed package)
- **Virtual Environment**: `.venv/` (if using recommended setup)
- **Logs**: Optional file specified with `--log-file` flag

## Important Implementation Details

### History Windowing
Only the last 10 messages are sent to Ollama (nora/core/history.py:82), but full history is persisted. This prevents context window overflow while maintaining conversation continuity.

### File Context Truncation
File content is limited to `MAX_FILE_TOKENS = 2000` characters per file (nora/core/chat.py:13). Truncated files show `...[truncated]...` marker.

### Colored Output
All user-facing messages use ANSI colors via `nora.core.utils`:
- **Green (✓)**: Success messages
- **Yellow (⚠)**: Warnings
- **Red (✗)**: Errors
- **Cyan (ℹ)**: Info messages

### Structured Logging
Logging configured via `utils.setup_logging()`:
- **Console**: WARNING and above (stderr)
- **File**: All levels if `--log-file` specified
- **Format**: `YYYY-MM-DD HH:MM:SS | module | LEVEL | message`

### SSL Verification
SSL verification is disabled by default for Ollama connections (`verify_ssl: False` in config). This is intentional for local/self-signed certificate scenarios.

## Testing

NORA uses pytest with comprehensive test coverage:

### Test Structure
- `tests/test_config.py`: ConfigManager with mocked requests
- `tests/test_history.py`: HistoryManager with temp directories
- `tests/test_plugins.py`: PluginLoader with dynamic plugin creation

### Running Tests
```bash
# All tests with coverage
pytest --cov=nora --cov-report=term-missing

# Specific test class
pytest tests/test_config.py::TestConfigManager

# With verbose output and markers
pytest -v --strict-markers
```

### CI/CD
GitHub Actions workflow (`.github/workflows/tests.yml`):
- Matrix testing: Python 3.8-3.12 on Ubuntu & macOS
- Pytest with coverage reports
- Code formatting checks (black, isort)
- Type checking (mypy)
- Linting (flake8)

## Type Hints

All public functions have type hints:
```python
def chat_loop(
    config: ConfigManager,
    history_manager: HistoryManager,
    model: Optional[str] = None,
    context_files: Optional[List[str]] = None,
    system: Optional[str] = None
) -> None:
    """Run an interactive chat REPL."""
```

## Future Enhancements

Documented in the code, planned for future versions:
- Project-wide context indexing (full repo awareness)
- Agent orchestration (multi-agent coordination)
- Rich terminal interface (progress bars, syntax highlighting)
- Config encryption for API keys/secrets
- Plugin versioning and dependency management
- Remote plugin repository
- Conversation branching and replay

## Dependencies

**Runtime dependencies** (auto-installed via pip):
- **requests** >= 2.25.0: Ollama HTTP API calls
- **PyYAML** >= 5.4.0: Configuration file parsing

**Development dependencies** (install with `.[dev]`):
- **pytest** >= 7.0.0: Testing framework
- **pytest-cov** >= 4.0.0: Coverage reporting
- **pytest-mock** >= 3.10.0: Mocking utilities

**Standard library** (no installation needed):
- **logging**: Structured logging
- **pathlib**: File path handling
- **importlib**: Dynamic plugin loading
- **argparse**: CLI argument parsing
- **readline**: REPL line editing
- **json**: History persistence
- **typing**: Type hints

**Build system**:
- **hatchling**: Modern PEP 517 build backend

Python 3.7+ required (f-strings, pathlib, type hints in stdlib).

All dependencies and metadata are defined in `pyproject.toml`.

## Roadmap Context

This project is in **Phase 1: Foundation & Environment** (mostly complete). v0.3.0 achievements:
- ✅ Modular core architecture
- ✅ Comprehensive type hints and docstrings
- ✅ Structured logging with colored output
- ✅ Plugin scaffolding commands
- ✅ Full test suite with >80% coverage
- ✅ CI/CD with GitHub Actions

See ROADMAP.md for full Phase 1 completion status and future phases.

## Development Workflow

### Repository Access

**Git Repository**: https://git.blakbox.vip/AI-Labs/nora

**Credentials**:
- Username: `baxterblk`
- App Token: `23af4ebb733319544df49917ae053a44ee859dd2`

**Configure Git Authentication** (for pushing):
```bash
# Option 1: Use git credential helper (stores in ~/.git-credentials)
git config --global credential.helper store
git push  # Will prompt once, then remember

# Option 2: Include credentials in remote URL
git remote set-url origin https://baxterblk:23af4ebb733319544df49917ae053a44ee859dd2@git.blakbox.vip/AI-Labs/nora

# Option 3: Use GIT_ASKPASS environment variable
echo 'echo 23af4ebb733319544df49917ae053a44ee859dd2' > ~/.git-askpass.sh
chmod +x ~/.git-askpass.sh
export GIT_ASKPASS=~/.git-askpass.sh
```

### Workflow Steps

1. **Clone and setup**:
   ```bash
   git clone https://git.blakbox.vip/AI-Labs/nora
   cd nora
   python3 -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   ```

2. **Make changes** in `nora/` or `tests/`

3. **Run tests**: `pytest`

4. **Check formatting**: `black nora tests && isort nora tests`

5. **Commit and push** - CI will run automatically

## Common Tasks

**Adding a new core module**:
1. Create `nora/core/newmodule.py` with type hints and docstrings
2. Add to `nora/core/__init__.py` exports
3. Import in `nora/cli.py`
4. Create `tests/test_newmodule.py`
5. Update this documentation

**Adding a new CLI command**:
1. Add parser in `cli.py` main()
2. Create handler function with type hints
3. Add to command routing section
4. Update help text and this documentation
5. Add integration test

**Debugging**:
```bash
# Verbose logging to console
nora -v chat

# Log to file for analysis
nora --log-file debug.log chat

# Interactive Python with NORA loaded
python -c "from nora.core import *; import code; code.interact(local=locals())"
```
