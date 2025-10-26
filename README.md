## DISCLAIMER
NORA is in active beta development. While core features are stable and well-tested (100% test pass rate), expect ongoing improvements and occasional breaking changes. Use in production environments at your own discretion.

# NORA - No Rush (on) Anything

NORA is a project to develop a private, local AI agent that runs entirely on local hardware and software infrastructure. The goal is to provide many of the same functionalities found in large-scale, cloud-based LLMs, but with a focus on user privacy, data security, and financial savings from consolidating or dropping subscriptions to cloud LLM services.

This project is in its early stages of development. The current focus is on foundational features. For a detailed overview of the NORA Project's planned features, milestones, and future direction, please see the [ROADMAP.md](ROADMAP.md) file.

## What's New in v0.5.0

🎉 **Major Release**: Simplified Installation & First-Run Wizard

NORA v0.5.0 makes getting started incredibly easy - no more manual configuration!

- **🧙 First-Run Setup Wizard**: Interactive configuration on your first command. Automatically detects Ollama, validates connections, and discovers available models.
- **🔧 Environment Variable Overrides**: Configure NORA via `NORA_OLLAMA_URL` and `NORA_MODEL` - perfect for CI/CD and containerized environments.
- **⚙️ Config Convenience Commands**: New `nora config path` and `nora config reset` commands for easy configuration management.
- **📦 PyPI Ready**: Enhanced packaging metadata - `pipx install nora-cli` (coming soon to PyPI).
- **🚀 Simplified Onboarding**: From clone-to-chat in 2 steps, matching the simplicity of npm-based CLI tools.

**Previous Release - v0.4.0**: Multi-Agent Teams, Project Indexing, REST API, and Extended Plugins.

**Testing**: 100% pass rate on all new features with 83-95% coverage. See [CHANGELOG.md](CHANGELOG.md) for full details.

## Quick Start

### Prerequisites
- Python 3.8+
- [Ollama](https://ollama.ai) installed and running locally

### Installation

**Recommended Installation**:
```bash
# Clone the repository
git clone https://git.blakbox.vip/AI-Labs/nora
cd nora

# Install with pipx (isolated, globally available)
pipx install .

# Or install with pip
pip install .
```

**PyPI Installation** (Coming Soon):
```bash
# Once published to PyPI, you'll be able to install directly:
pipx install nora-cli
```

**Development Installation** (for contributors):
```bash
# Clone the repository
git clone https://git.blakbox.vip/AI-Labs/nora
cd nora

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### First Run

NORA will automatically run an interactive setup wizard on your first command:

```bash
# Run any command to trigger the wizard
nora chat

# Or skip the wizard and use environment variables
NORA_OLLAMA_URL=http://localhost:11434 NORA_MODEL=llama3:8b nora chat
```

### Usage

```bash
# Start an interactive chat
nora chat

# Chat with file context
nora chat --context path/to/file.py

# Run a one-shot prompt
nora run "Tell me about local AI"

# List available agent plugins
nora agents

# Run an agent
nora agent greeter

# Run a multi-agent team (v0.4.0)
nora agent --team team-config.yaml

# Index a project and search within it (v0.4.0)
nora project index /path/to/project --search "keyword"

# Start REST API server (v0.4.0)
nora serve

# Configure NORA
nora config show         # Display current configuration
nora config test         # Test Ollama connection
nora config path         # Show config file location
nora config reset        # Reset to default configuration
```

## Documentation

### User Guides
- **[Configuration Guide](docs/Config.md)** - Set up remote Ollama, profiles, and connection settings
- **[Agent Plugin Development](docs/Agents.md)** - Create custom AI agents with the plugin system
- **[Multi-Agent Teams Guide](docs/Teams.md)** - Coordinate multiple agents with orchestration (v0.4.0)

### Developer Resources
- **[Architecture Overview](docs/Overview.md)** - System design, CLI flow, and core components (v0.4.0 updated)
- **[Contributing Guide](docs/Contributing.md)** - Development workflow, testing, and coding standards
- **[Tools Guide](docs/Tools.md)** - Using and creating tools for agents
- **[Roadmap](ROADMAP.md)** - Future features and version timeline
- **[Changelog](CHANGELOG.md)** - Version history and release notes

### Reference
- **[CLAUDE.md](CLAUDE.md)** - AI assistant context for development

## Features

- **🔒 Privacy-First**: All data stays local, no cloud dependencies
- **🧙 First-Run Wizard** *(v0.5.0)*: Interactive setup on first command with connection validation
- **🔧 Environment Variables** *(v0.5.0)*: Configure via `NORA_OLLAMA_URL` and `NORA_MODEL`
- **⚙️ Config Commands** *(v0.5.0)*: Easy configuration management with `path`, `reset`, and more
- **🤝 Multi-Agent Teams** *(v0.4.0)*: Coordinate multiple agents with sequential/parallel execution
- **🔍 Project Indexing** *(v0.4.0)*: Index and search codebases across 20+ languages
- **🌐 REST API** *(v0.4.0)*: FastAPI server with 6 endpoints for remote access
- **🤖 Agent Plugins**: Extensible plugin system with Agent/Tool base classes
- **🛠️ Extensible Tools**: A flexible tool system that allows agents to interact with the local environment (e.g., file system, shell commands).
- **💬 Interactive Chat**: REPL with streaming responses and history
- **📁 Code Context**: Inject file contents for code-aware conversations
- **🎨 Colored Output**: ANSI-based terminal colors for enhanced UX
- **🧪 Fully Tested**: 100% pass rate on new features with comprehensive CI/CD

## Project Status

**Current Version:** v0.5.0 (Beta)

NORA v0.5.0 features a first-run setup wizard, environment variable overrides, simplified installation, plus all v0.4.0 capabilities including multi-agent orchestration, project indexing, REST API, and enhanced plugin framework.

The core functionality is stable and well-tested, but the project is still in active development. See [CHANGELOG.md](CHANGELOG.md) for complete release notes and [ROADMAP.md](ROADMAP.md) for future plans.