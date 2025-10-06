# NORA - No Rush (on) Anything

NORA is a project to develop a private, local AI agent that runs entirely on local hardware and software infrastructure. The goal is to provide many of the same functionalities found in large-scale, cloud-based LLMs, but with a focus on user privacy, data security, and financial savings from consolidating or dropping subscriptions to cloud LLM services.

This project is in its early stages of development. The current focus is on foundational features. For a detailed overview of the NORA Project's planned features, milestones, and future direction, please see the [ROADMAP.md](ROADMAP.md) file.

## Quick Start

### Prerequisites
- Python 3.7+
- [Ollama](https://ollama.ai) installed and running locally

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd nora

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install NORA in editable mode
pip install -e .
```

### Usage

```bash
# Start an interactive chat
nora chat

# Run a one-shot prompt
nora run "Tell me about local AI"

# List available agent plugins
nora agents

# Run an agent
nora agent greeter

# Configure NORA
nora config show
nora config test
```

## Documentation

### User Guides
- **[Configuration Guide](docs/Config.md)** - Set up remote Ollama, profiles, and connection settings
- **[Agent Plugin Development](docs/Agents.md)** - Create custom AI agents with the plugin system

### Developer Resources
- **[Architecture Overview](docs/Overview.md)** - System design, CLI flow, and core components
- **[Contributing Guide](docs/Contributing.md)** - Development workflow, testing, and coding standards
- **[Roadmap](ROADMAP.md)** - Future features and version timeline (v0.4.0 goals)

### Reference
- **[CLAUDE.md](CLAUDE.md)** - AI assistant context for development

## Features

- **🔒 Privacy-First**: All data stays local, no cloud dependencies
- **🤖 Agent Plugins**: Extensible plugin system for specialized AI agents
- **💬 Interactive Chat**: REPL with streaming responses and history
- **📁 Code Context**: Inject file contents for code-aware conversations
- **⚙️ Profile Management**: Switch between local/remote Ollama configurations
- **🎨 Colored Output**: ANSI-based terminal colors for enhanced UX
- **🧪 Fully Tested**: >80% test coverage with CI/CD pipeline

## Project Status

**Current Version:** v0.3.0 (Production Ready)

NORA v0.3.0 features a modular architecture, comprehensive testing, and production-ready infrastructure. See [ROADMAP.md](ROADMAP.md) for v0.4.0 plans including multi-agent coordination, project context indexing, and API layer.