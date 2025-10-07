# NORA Actions System

**Status**: Production (v0.4.2)

The NORA Actions System enables AI models running through Ollama to create, modify, and manage files on your local machine, similar to Claude Code CLI or Google Gemini CLI.

## Overview

When you interact with NORA in chat mode with actions enabled, the AI model can:
- ✅ Create new files with specified content
- ✅ Read existing files
- ✅ Append content to files
- ✅ Delete files (with confirmation)
- ✅ Run shell commands (sandboxed)
- ✅ List files in directories

All operations are **restricted to the project directory** where NORA was launched, providing security through sandboxing.

## Quick Start

### Enable Actions

```bash
# Enable actions in chat mode
nora chat --enable-actions

# Disable safety confirmations (for experienced users)
nora chat --enable-actions --no-confirm
```

### Example Session

**User Prompt:**
```
You> create a simple HTML welcome page
```

**AI Response:**
```
# File: index.html
```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8">
    <title>Welcome</title>
  </head>
  <body>
    <h1>Welcome to NORA!</h1>
    <p>This page was created by AI.</p>
  </body>
</html>
```
```

**NORA Actions:**
```
✓ Created: index.html
```

## File Operation Formats

NORA supports multiple formats for specifying file operations in model output.

### 1. Header Style (Recommended)

The AI should use this format for file creation:

```
# File: path/to/file.ext
```language
content here
```
```

**Example:**
```
# File: app.py
```python
def hello():
    print("Hello, world!")
```
```

### 2. Inline Path

```
```language path/to/file.ext
content here
```
```

### 3. JSON Actions (Advanced)

For complex operations:

```
<NORA_ACTION>
{
    "action": "create",
    "path": "config.json",
    "content": "{\"debug\": true}"
}
</NORA_ACTION>
```

### 4. Command Execution

```
<NORA_COMMAND>npm install</NORA_COMMAND>
```

## Security Features

### 🔒 Sandboxing

All file operations are restricted to the project directory where `nora` was launched:

✅ **Allowed:**
- `./src/app.py`
- `config.json`
- `docs/readme.md`

❌ **Blocked:**
- `../../../etc/passwd`
- `/etc/hosts`
- `~/.ssh/id_rsa`

### 🛡️ Safe Mode

By default, NORA prompts before overwriting existing files:

```
File index.html already exists. Overwrite? (y/N):
```

Disable with `--no-confirm`.

### ⚠️ Command Filtering

Dangerous command patterns are automatically blocked:
- `rm -rf` - Recursive deletion
- `sudo` - Privilege escalation
- Redirection (`>`, `>>`)
- Permission changes (`chmod`, `chown`)

### ⏱️ Timeout Protection

All commands have a 30-second timeout to prevent hanging processes.

## CLI Flags

### `--enable-actions`

Enable file operations from model output:

```bash
nora chat --enable-actions
```

Without this flag, actions are detected but not executed (preview mode).

### `--no-confirm`

Skip file overwrite confirmations:

```bash
nora chat --enable-actions --no-confirm
```

⚠️ **Warning:** Use carefully - overwrites without asking!

## Use Cases

### Web Development

```
You> create a responsive landing page with navigation
```

Creates: `index.html`, `styles.css`, `script.js`

### Python Projects

```
You> set up a Flask app with home and about routes
```

Creates:
- `app.py` - Main application
- `templates/home.html`
- `templates/about.html`
- `static/style.css`
- `requirements.txt`

### Configuration Files

```
You> create docker-compose for MySQL and Redis
```

Creates: `docker-compose.yml` with multi-service setup

### Scripts & Automation

```
You> write a backup script for my database
```

Creates: Executable bash script with error handling

## Troubleshooting

### Actions Not Detected

Ensure the AI uses supported formats:

```
You> Create test.py with print("hello")

# The AI should respond with:
# File: test.py
```python
print("hello")
```
```

### File Overwrite Blocked

Respond with `y` to the prompt or use `--no-confirm`.

### Command Blocked

Check if command contains dangerous patterns. Review security settings.

### Permission Denied

Ensure the launch directory is writable.

## Best Practices

1. ✅ **Be Explicit** - Clearly specify file names and paths
2. ✅ **Use Safe Mode** - Keep confirmations on by default
3. ✅ **Review Output** - Always review generated code
4. ✅ **Start Small** - Test with simple files first
5. ✅ **Version Control** - Use git to track AI changes

## Future Enhancements

- [ ] File diff previews before overwriting
- [ ] Rollback/undo functionality
- [ ] Automatic git commits for AI changes
- [ ] Binary file support
- [ ] Template-based generation
- [ ] Multi-file refactoring
