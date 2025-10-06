# Contributing to NORA

Thank you for your interest in contributing to NORA! This guide will help you get started with development, testing, and submitting contributions.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Development Setup

### Prerequisites

- **Python 3.7+** (3.8+ recommended for full type hint support)
- **Git** with GPG configured (for signed commits)
- **Ollama** installed and running locally for testing

### Initial Setup

1. **Clone the repository:**

```bash
git clone https://git.blakbox.vip/AI-Labs/nora
cd nora
```

2. **Create a virtual environment:**

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install in editable mode with dev dependencies:**

```bash
pip install -e ".[dev]"
```

This installs:
- NORA in editable mode (changes reflect immediately)
- `pytest`, `pytest-cov`, `pytest-mock` for testing
- Runtime dependencies: `requests`, `PyYAML`

4. **Verify installation:**

```bash
nora --version
nora config test
pytest
```

## Project Structure

```
nora/
├── nora/                      # Main package
│   ├── __init__.py            # Package metadata (version)
│   ├── cli.py                 # CLI interface (~400 lines)
│   ├── core/                  # Core functionality modules
│   │   ├── __init__.py        # Core exports
│   │   ├── config.py          # Configuration management
│   │   ├── history.py         # Chat history persistence
│   │   ├── chat.py            # Ollama API client
│   │   ├── plugins.py         # Plugin loader/manager
│   │   └── utils.py           # Colored output & logging
│   ├── plugins/               # Agent plugins
│   │   ├── __init__.py
│   │   └── greeter.py         # Example plugin
│   └── config_manager.py      # Legacy (deprecated)
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── test_config.py         # ConfigManager tests
│   ├── test_history.py        # HistoryManager tests
│   └── test_plugins.py        # PluginLoader tests
├── docs/                      # Documentation
│   ├── Overview.md
│   ├── Agents.md
│   ├── Config.md
│   └── Contributing.md (this file)
├── .github/
│   └── workflows/
│       └── tests.yml          # CI/CD pipeline
├── pyproject.toml             # Package metadata & dependencies
├── pytest.ini                 # pytest configuration
├── .gitignore
├── README.md
├── ROADMAP.md
└── CLAUDE.md                  # AI assistant context
```

### Key Files

- **`nora/cli.py`**: Main CLI interface, all commands route through here
- **`nora/core/config.py`**: ConfigManager class for YAML config
- **`nora/core/history.py`**: HistoryManager for chat persistence
- **`nora/core/chat.py`**: OllamaChat client for API calls
- **`nora/core/plugins.py`**: PluginLoader for dynamic agent loading
- **`nora/core/utils.py`**: Colored output, logging setup, banners
- **`pyproject.toml`**: Package metadata, dependencies, entrypoints

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Edit files in `nora/` or `tests/`.

**Hot Reload:**
Since you installed with `pip install -e .`, changes to Python files are immediately reflected. No need to reinstall.

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=nora --cov-report=term-missing
```

### 4. Manual Testing

```bash
# Test CLI commands
nora chat
nora run "test prompt"
nora agent greeter
nora config show
nora project new test-agent

# Test with verbose logging
nora -v chat

# Test with log file
nora --log-file debug.log chat
```

### 5. Check Code Quality

```bash
# Format code (coming soon - see Coding Standards)
black nora tests
isort nora tests

# Type checking (coming soon)
mypy nora

# Linting (coming soon)
flake8 nora
```

### 6. Commit Changes

```bash
git add .
git commit -m "Add feature: description of changes"
```

**Commit Message Format:**
```
<type>: <short description>

<optional longer description>

<optional references to issues>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test changes
- `refactor:` Code refactoring
- `style:` Formatting changes
- `chore:` Build/tooling changes

**Examples:**
```
feat: Add multi-agent orchestration support

Implements agent coordination with shared context
and message passing between agents.

Fixes #42
```

```
fix: Handle connection timeout in ConfigManager

Increases default timeout from 5s to 30s for
slow network connections.
```

### 7. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on the repository.

## Coding Standards

### Python Style Guide

NORA follows **PEP 8** with some modifications:

- **Line length**: 100 characters (not 79)
- **Quotes**: Double quotes preferred (`"string"` not `'string'`)
- **Imports**: Absolute imports for modules, relative for intra-package

### Type Hints

**All public functions must have type hints:**

```python
def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    pass

def save_config(config: Dict[str, Any], path: str) -> None:
    """Save configuration to YAML file."""
    pass

def get_recent_messages(
    history: List[Dict[str, str]],
    limit: int = 10
) -> List[Dict[str, str]]:
    """Get the most recent messages from history."""
    pass
```

**Import type hints from `typing`:**

```python
from typing import List, Dict, Optional, Any, Tuple, Callable
```

### Docstrings

**All public functions must have docstrings:**

```python
def chat_loop(
    config: ConfigManager,
    history_manager: HistoryManager,
    model: Optional[str] = None,
    context_files: Optional[List[str]] = None,
    system: Optional[str] = None
) -> None:
    """
    Run an interactive chat REPL with Ollama.

    Args:
        config: Configuration manager instance
        history_manager: History manager instance
        model: Optional model override
        context_files: Optional list of files to include as context
        system: Optional system prompt

    Returns:
        None

    Raises:
        KeyboardInterrupt: When user presses Ctrl+C
        EOFError: When user presses Ctrl+D
    """
    pass
```

**Module docstrings:**

```python
"""
NORA Configuration Manager

Handles user configuration for Ollama connections and profiles with structured logging.
"""

import logging
import pathlib
# ...
```

### Logging

**Use structured logging, not print():**

```python
import logging

logger = logging.getLogger(__name__)

def my_function():
    logger.debug("Starting function")
    logger.info("Important event")
    logger.warning("Something unexpected")
    logger.error("Error occurred", exc_info=True)
```

**For user-facing output, use colored helpers:**

```python
from nora.core import utils

utils.success("Operation completed!")
utils.warning("Potential issue detected")
utils.error("Operation failed")
utils.info("Informational message")
```

### Error Handling

**Handle exceptions gracefully:**

```python
def load_file(path: str) -> str:
    """Load file content."""
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"File not found: {path}")
        utils.error(f"File not found: {path}")
        raise
    except PermissionError:
        logger.error(f"Permission denied: {path}")
        utils.error(f"Permission denied: {path}")
        raise
    except Exception as e:
        logger.error(f"Failed to load file: {e}", exc_info=True)
        utils.error(f"Failed to load file: {e}")
        raise
```

### Import Organization

**Group imports in this order:**

```python
# Standard library
import json
import logging
import pathlib
from typing import List, Dict, Optional

# Third-party
import requests
import yaml

# Local/intra-package
from .config import ConfigManager
from .utils import colored, success
from nora.core import PluginLoader
```

## Testing

### Test Structure

Tests are located in `tests/` and mirror the package structure:

```
tests/
├── test_config.py         # Tests for nora/core/config.py
├── test_history.py        # Tests for nora/core/history.py
└── test_plugins.py        # Tests for nora/core/plugins.py
```

### Writing Tests

**Use pytest with fixtures and mocking:**

```python
import pytest
from unittest.mock import Mock, patch, mock_open
from nora.core.config import ConfigManager


class TestConfigManager:
    """Tests for ConfigManager class"""

    def test_load_creates_default_config(self, tmp_path):
        """Test that load() creates default config if file doesn't exist"""
        config_path = tmp_path / "config.yaml"
        manager = ConfigManager(str(config_path))

        assert config_path.exists()
        assert manager.config["model"] == "deepseek-coder:6.7b"

    @patch('requests.get')
    def test_test_connection_success(self, mock_get, tmp_path):
        """Test successful connection test"""
        config_path = tmp_path / "config.yaml"
        manager = ConfigManager(str(config_path))

        mock_response = Mock()
        mock_response.json.return_value = {"version": "0.1.0"}
        mock_get.return_value = mock_response

        success, result = manager.test_connection()

        assert success is True
        assert result == {"version": "0.1.0"}

    def test_set_nested_key(self, tmp_path):
        """Test setting nested configuration keys"""
        config_path = tmp_path / "config.yaml"
        manager = ConfigManager(str(config_path))

        manager.set("ollama.url", "http://remote:11434")

        assert manager.get("ollama.url") == "http://remote:11434"
```

### Test Coverage

**Aim for >80% coverage:**

```bash
pytest --cov=nora --cov-report=html
open htmlcov/index.html  # View coverage report
```

**Coverage requirements:**
- Core modules: >90% coverage
- CLI: >70% coverage (some manual interaction paths)
- Plugins: >60% coverage (agents vary widely)

### Running Tests Locally

```bash
# All tests
pytest

# Specific test file
pytest tests/test_config.py

# Specific test class
pytest tests/test_config.py::TestConfigManager

# Specific test method
pytest tests/test_config.py::TestConfigManager::test_load_creates_default_config

# With verbose output
pytest -v

# With coverage
pytest --cov=nora --cov-report=term-missing

# Stop on first failure
pytest -x

# Run only failed tests from last run
pytest --lf
```

### CI/CD Testing

Tests run automatically on push via GitHub Actions (`.github/workflows/tests.yml`):

- **Matrix testing**: Python 3.8, 3.9, 3.10, 3.11, 3.12
- **Platforms**: Ubuntu, macOS
- **Steps**: Install deps → Run pytest → Upload coverage

## Documentation

### Code Documentation

- **All public functions**: Type hints + docstrings
- **All modules**: Module-level docstrings
- **All classes**: Class docstrings with usage examples

### User Documentation

Update relevant docs in `docs/`:

- **New features**: Add to [Overview.md](./Overview.md)
- **Plugin development**: Update [Agents.md](./Agents.md)
- **Configuration**: Update [Config.md](./Config.md)
- **This file**: Keep updated with workflow changes

### CLAUDE.md

For significant architecture changes, update `CLAUDE.md` so AI assistants understand the codebase structure.

### README.md

Keep the README in sync:
- Installation instructions
- Quick start examples
- Link to new docs

## Submitting Changes

### Pre-Submission Checklist

Before submitting a pull request:

- [ ] All tests pass: `pytest`
- [ ] Coverage is adequate: `pytest --cov=nora`
- [ ] Code is formatted (when tools are added)
- [ ] Type hints added to new functions
- [ ] Docstrings added to new functions/classes
- [ ] Relevant docs updated
- [ ] Manual testing completed
- [ ] Commit messages follow format
- [ ] No sensitive data in commits (API keys, tokens, etc.)

### Pull Request Process

1. **Create a pull request** with:
   - Clear title describing the change
   - Description of what changed and why
   - References to related issues
   - Screenshots (if UI changes)

2. **Address review feedback** by:
   - Making requested changes
   - Responding to comments
   - Pushing additional commits

3. **Wait for CI to pass**:
   - All tests must pass
   - Coverage should not decrease significantly

4. **Merge when approved**:
   - Squash commits if many small commits
   - Use merge commit for feature branches

### Code Review Guidelines

**For reviewers:**
- Check for proper type hints and docstrings
- Verify tests cover new functionality
- Look for potential edge cases
- Ensure logging is appropriate
- Confirm error handling is robust
- Check for security issues
- Verify documentation is updated

**For contributors:**
- Respond to feedback promptly
- Ask questions if feedback is unclear
- Be open to suggestions
- Don't take criticism personally

## Release Process

### Versioning

NORA follows **Semantic Versioning** (semver):

```
MAJOR.MINOR.PATCH

Example: 0.3.0
```

- **MAJOR**: Breaking changes (API incompatibility)
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

### Release Checklist

For maintainers preparing a release:

1. **Update version number:**

```python
# nora/__init__.py
__version__ = "0.4.0"

# pyproject.toml
[project]
version = "0.4.0"
```

2. **Update ROADMAP.md** with completed features

3. **Update CHANGELOG.md** (if exists) with changes

4. **Run full test suite:**

```bash
pytest --cov=nora --cov-report=term-missing
```

5. **Tag the release:**

```bash
git tag -a v0.4.0 -m "Release v0.4.0: Description of changes"
git push origin v0.4.0
```

6. **Create GitHub release** with:
   - Tag: `v0.4.0`
   - Title: "NORA v0.4.0"
   - Description: Major changes and features
   - Attach any build artifacts

## Common Development Tasks

### Adding a New Core Module

1. Create `nora/core/newmodule.py` with:
   - Module docstring
   - Type hints on all functions
   - Structured logging with `logger = logging.getLogger(__name__)`

2. Add to `nora/core/__init__.py`:

```python
from .newmodule import NewClass, new_function

__all__ = [
    # ... existing exports
    "NewClass",
    "new_function",
]
```

3. Create `tests/test_newmodule.py` with comprehensive tests

4. Update `CLAUDE.md` with module description

### Adding a New CLI Command

1. Add subparser in `nora/cli.py`:

```python
# In main() function
subparsers = parser.add_subparsers(dest="command", help="Available commands")

# Add new command
newcmd_parser = subparsers.add_parser(
    "newcmd",
    help="Description of new command"
)
newcmd_parser.add_argument("--option", help="Option description")
```

2. Create handler function:

```python
def handle_newcmd(args, config: ConfigManager) -> None:
    """Handle the newcmd command."""
    # Implementation
    pass
```

3. Route command in main():

```python
if args.command == "newcmd":
    handle_newcmd(args, config)
```

4. Add tests for new command

5. Update docs with usage examples

### Adding a New Plugin

Use the scaffolding tool:

```bash
nora project new my-plugin
```

Then edit `nora/plugins/my_plugin.py` with your logic.

See [Agents.md](./Agents.md) for full plugin development guide.

## Getting Help

- **Issues**: Check [GitHub Issues](https://git.blakbox.vip/AI-Labs/nora/issues)
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Read [docs/](../docs/)
- **Code Questions**: Look at existing code or ask in discussions

## Code of Conduct

### Our Standards

- **Be respectful** of differing viewpoints
- **Be constructive** in criticism
- **Focus on the code**, not the person
- **Help newcomers** learn the codebase
- **Be patient** with review processes

### Our Responsibilities

Maintainers will:
- Review PRs in a timely manner
- Provide constructive feedback
- Maintain code quality standards
- Keep documentation updated
- Help contributors succeed

## License

By contributing to NORA, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

---

**Thank you for contributing to NORA!**

Questions? Open an issue or discussion on the repository.

**Next Steps:**
- Set up your development environment
- Pick an issue to work on
- Read [Overview.md](./Overview.md) for architecture
- Check [ROADMAP.md](../ROADMAP.md) for future plans
