## DISCLAIMER
This project has largely been vibe-coded and is under EXTREMELY early development. USE AT YOUR OWN PERIL!

# NORA - No Rush (on) Anything

NORA is a project to develop a private, local AI agent that runs entirely on local hardware and software infrastructure. The goal is to provide many of the same functionalities found in large-scale, cloud-based LLMs, but with a focus on user privacy, data security, and financial savings from consolidating or dropping subscriptions to cloud LLM services.

This project is in its early stages of development. The current focus is on foundational features. For a detailed overview of the NORA Project's planned features, milestones, and future direction, please see the [ROADMAP.md](ROADMAP.md) file.

## What's New in v0.4.0

🚀 **Major Release**: Multi-Agent Orchestration & REST API

NORA v0.4.0 introduces powerful new capabilities for coordinating multiple AI agents and accessing NORA remotely:

- **🤝 Multi-Agent Teams**: Coordinate multiple AI agents with sequential or parallel execution modes. Define teams in YAML with dependency resolution and shared memory.
- **🔍 Project Indexing**: Index entire codebases for context-aware conversations. Search across 20+ languages with smart relevance scoring.
- **🌐 REST API**: FastAPI-based REST API with 6 endpoints for chat, agents, teams, and project indexing. Deploy NORA as a service.
- **🧩 Extended Plugins**: New Agent and Tool base classes with lifecycle hooks, context sharing, and backward compatibility.

**Testing**: 95% test pass rate with 87-92% coverage on new modules. See [CHANGELOG.md](CHANGELOG.md) for full details.

**Upgrade**: `pip install -e ".[all]"` to get all new features.

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

# Index a project for context-aware search (v0.4.0)
nora project index /path/to/project
nora project search "keyword"

# Start REST API server (v0.4.0)
nora serve

# Configure NORA
nora config show
nora config test
```

## Documentation

### User Guides
- **[Configuration Guide](docs/Config.md)** - Set up remote Ollama, profiles, and connection settings
- **[Agent Plugin Development](docs/Agents.md)** - Create custom AI agents with the plugin system
- **[Multi-Agent Teams Guide](docs/Teams.md)** - Coordinate multiple agents with orchestration (v0.4.0)

### Developer Resources
- **[Architecture Overview](docs/Overview.md)** - System design, CLI flow, and core components (v0.4.0 updated)
- **[Contributing Guide](docs/Contributing.md)** - Development workflow, testing, and coding standards
- **[Roadmap](ROADMAP.md)** - Future features and version timeline
- **[Changelog](CHANGELOG.md)** - Version history and release notes

### Reference
- **[CLAUDE.md](CLAUDE.md)** - AI assistant context for development

## Features

- **🔒 Privacy-First**: All data stays local, no cloud dependencies
- **🤝 Multi-Agent Teams** *(v0.4.0)*: Coordinate multiple agents with sequential/parallel execution
- **🔍 Project Indexing** *(v0.4.0)*: Index and search codebases across 20+ languages
- **🌐 REST API** *(v0.4.0)*: FastAPI server with 6 endpoints for remote access
- **🤖 Agent Plugins**: Extensible plugin system with Agent/Tool base classes
- **💬 Interactive Chat**: REPL with streaming responses and history
- **📁 Code Context**: Inject file contents for code-aware conversations
- **⚙️ Profile Management**: Switch between local/remote Ollama configurations
- **🎨 Colored Output**: ANSI-based terminal colors for enhanced UX
- **🧪 Fully Tested**: 95% test pass rate with comprehensive CI/CD

## Project Status

**Current Version:** v0.4.0 (Production Ready)

NORA v0.4.0 features multi-agent orchestration, project indexing, REST API, and enhanced plugin framework. See [CHANGELOG.md](CHANGELOG.md) for complete release notes and [ROADMAP.md](ROADMAP.md) for future plans.