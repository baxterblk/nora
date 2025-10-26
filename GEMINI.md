# NORA - No Rush (on) Anything

## Project Overview

NORA is a Python-based command-line interface (CLI) application designed to interact with local AI models through the Ollama service. It aims to provide a private, local AI agent that runs entirely on the user's own hardware, ensuring data privacy and security.

The project is structured as a Python package named `nora`. The main entry point is `nora/cli.py`, which uses the `argparse` library to handle command-line arguments. The core logic is located in the `nora/core/` directory, which includes modules for managing chat interactions (`chat.py`), configuration (`config.py`), multi-agent orchestration (`orchestrator.py`), and project file indexing (`indexer.py`).

NORA also provides a REST API built with FastAPI (`nora/api/server.py`) to expose its functionality over HTTP. The application is extensible through a plugin system for creating custom AI agents, located in the `nora/plugins/` directory.

## Building and Running

### Installation

The project uses `pyproject.toml` to manage dependencies and packaging. Installation can be done using `pip`:

```bash
# For regular use
pip install .

# For development (editable mode with dev dependencies)
pip install -e ".[dev]"
```

### Running the Application

The main command-line interface is accessed through the `nora` script:

```bash
# Start an interactive chat session
nora chat

# Run a one-shot prompt
nora run "What is the capital of France?"

# List available agent plugins
nora agents

# Run a specific agent
nora agent <agent_name>

# Index a project directory
nora project index /path/to/project

# Start the REST API server
nora serve
```

### Testing

The project uses `pytest` for testing. Tests are located in the `tests/` directory.

```bash
# Run all tests
pytest
```

## Development Conventions

*   **Dependencies:** Project dependencies are managed in `pyproject.toml`. A `requirements.txt` file is also present for backward compatibility.
*   **CLI:** The command-line interface is built using Python's `argparse` module.
*   **API:** A REST API is provided using the FastAPI framework.
*   **Plugins:** The application can be extended with agent plugins located in the `nora/plugins/` directory.
*   **Testing:** `pytest` is the testing framework of choice.
*   **Orchestration:** The `nora/core/orchestrator.py` module allows for the coordination of multiple AI agents in both sequential and parallel execution modes.

## Important Implementation Details

### History Windowing
Only the last 10 messages are sent to Ollama to prevent context window overflow, but the full conversation history is saved locally.

### File Context Truncation
When files are provided as context to the chat, their content is truncated to 2000 characters per file.

### Colored Output
The CLI uses ANSI color codes to provide colored output for different message types (success, warning, error, info).

### Structured Logging
NORA uses Python's `logging` module for structured logging. Logs are sent to `stderr` at the `WARNING` level and above, and can be written to a file if specified with the `--log-file` argument.

### SSL Verification
SSL verification is disabled by default for Ollama connections to simplify setup for local and self-signed certificates.

## File Locations

- **Config**: `~/.nora/config.yaml`
- **Chat History**: `~/.nora/history.json`
- **Plugins**: `nora/plugins/*.py` (within the installed package)

## Project Status and Roadmap

This project is in active development. The current focus is on core features and stability. For more details on planned features and future direction, please refer to the `ROADMAP.md` file.