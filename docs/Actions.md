# NORA Actions System

**Status**: In Development (v0.4.0-dev)

The NORA Actions System enables AI models running through Ollama to create, modify, and manage files on your local machine, similar to Claude Code CLI or Google Gemini CLI.

## Overview

When you interact with NORA in chat mode with actions enabled, the AI model can:
- Create new files with specified content
- Read existing files
- Append content to files
- Delete files (with confirmation)
- Run shell commands (sandboxed)
- List files in directories

All operations are **restricted to the project directory** where NORA was launched, providing security through sandboxing.

## Quick Start

### Enable Actions

```bash
# Enable actions in chat mode
nora chat --enable-actions

# Enable with specific project root
nora chat --enable-actions --project-root /path/to/project

# Disable safety confirmations (dangerous!)
nora chat --enable-actions --no-confirm
```

### Example Usage

```
You> create a simple HTML welcome page