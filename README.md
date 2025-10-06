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

For detailed documentation, see [CLAUDE.md](CLAUDE.md).

*Additional documentation will be added as the project matures.*