# Agent Plugin Development Guide

## Overview

NORA's plugin system allows you to create custom AI agents with specialized behaviors. Plugins are Python modules that follow a simple interface and are automatically discovered at runtime.

## Quick Start

### Create a New Agent

Use the built-in scaffolding command:

```bash
nora project new my-agent
```

This creates `nora/plugins/my_agent.py` with a complete template:

```python
"""
My Agent Plugin

Description of what your agent does.
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
        # TODO: Implement your agent logic here
        messages = [
            {"role": "user", "content": "Hello from My Agent!"}
        ]
        call_fn(messages, model=model, stream=True)

    return {
        "name": "my_agent",
        "description": "My Agent plugin",
        "run": run
    }
```

### Run Your Agent

```bash
nora agent my-agent
```

## Plugin Interface

### Required Structure

Every plugin must have a `register()` function that returns a dictionary with three keys:

```python
def register() -> Dict[str, Any]:
    return {
        "name": str,           # Plugin identifier (must match filename)
        "description": str,    # Short description shown in `nora agents`
        "run": Callable        # Function to execute the agent
    }
```

### The `run()` Function

The `run()` function receives two arguments:

- **`model: str`** - The Ollama model to use (from config or --model flag)
- **`call_fn: Callable`** - A function to make Ollama API calls

**Signature:**
```python
def run(model: str, call_fn: Callable[[List[Dict[str, str]], str, bool], None]) -> None:
    """
    Args:
        model: Model name (e.g., "deepseek-coder:6.7b")
        call_fn: Chat function with signature:
                 call_fn(messages, model=model, stream=False)
    """
    pass
```

### The `call_fn` Interface

The `call_fn` function allows your agent to communicate with Ollama:

```python
call_fn(
    messages: List[Dict[str, str]],  # Message history
    model: str = model,               # Model to use
    stream: bool = False              # Enable streaming output
) -> None
```

**Message Format:**
```python
messages = [
    {"role": "system", "content": "System prompt (optional)"},
    {"role": "user", "content": "User message"},
    {"role": "assistant", "content": "Previous assistant response"},
    {"role": "user", "content": "Follow-up message"}
]
```

**Roles:**
- `system`: Instructions for the model's behavior
- `user`: User input or questions
- `assistant`: Model's previous responses (for conversation context)

## Example Agents

### 1. Simple Greeter

```python
"""Greeter Agent - Says hello in multiple languages"""


def register():
    def run(model, call_fn):
        messages = [
            {
                "role": "system",
                "content": "You are a friendly multilingual greeter."
            },
            {
                "role": "user",
                "content": "Greet me in 5 different languages with enthusiasm!"
            }
        ]
        call_fn(messages, model=model, stream=True)

    return {
        "name": "greeter",
        "description": "Multilingual greeting agent",
        "run": run
    }
```

### 2. Code Reviewer

```python
"""Code Review Agent - Analyzes code for best practices"""


def register():
    def run(model, call_fn):
        import sys

        # Read code from stdin or prompt user
        print("Paste your code (Ctrl+D when done):")
        code = sys.stdin.read()

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert code reviewer. Analyze code for:\n"
                    "- Bugs and edge cases\n"
                    "- Performance issues\n"
                    "- Security vulnerabilities\n"
                    "- Best practices and style\n"
                    "Provide specific, actionable feedback."
                )
            },
            {
                "role": "user",
                "content": f"Review this code:\n\n```\n{code}\n```"
            }
        ]
        call_fn(messages, model=model, stream=True)

    return {
        "name": "code_reviewer",
        "description": "Analyzes code for bugs and best practices",
        "run": run
    }
```

### 3. Multi-Turn Conversational Agent

```python
"""Research Assistant - Multi-turn conversation with context"""

import readline  # For better input experience


def register():
    def run(model, call_fn):
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a research assistant. Help users explore topics "
                    "in depth with follow-up questions and detailed explanations."
                )
            }
        ]

        print("Research Assistant (type 'exit' to quit)")
        print("-" * 50)

        while True:
            try:
                user_input = input("\n> ")
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break

            if user_input.strip().lower() == "exit":
                break

            # Add user message to history
            messages.append({"role": "user", "content": user_input})

            # Get response
            print("\nAssistant: ", end="", flush=True)

            # Note: We need to capture the response to add it to history
            # For now, streaming doesn't allow this easily
            # In a production agent, you'd implement response capture

            call_fn(messages, model=model, stream=True)
            print()  # Newline after response

            # For this example, we'll just note that in production
            # you'd parse the streaming response and add it to messages

    return {
        "name": "research_assistant",
        "description": "Multi-turn conversational research helper",
        "run": run
    }
```

### 4. File Analyzer Agent

```python
"""File Analyzer - Analyzes file content and structure"""

import pathlib


def register():
    def run(model, call_fn):
        import sys

        if len(sys.argv) < 3:
            print("Usage: nora agent file_analyzer <file_path>")
            sys.exit(1)

        file_path = sys.argv[2]
        path = pathlib.Path(file_path)

        if not path.exists():
            print(f"Error: File not found: {file_path}")
            sys.exit(1)

        # Read file content
        try:
            content = path.read_text()
        except Exception as e:
            print(f"Error reading file: {e}")
            sys.exit(1)

        # Truncate if too large
        MAX_CHARS = 4000
        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS] + "\n...[truncated]..."

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a file analysis expert. Analyze files for:\n"
                    "- Purpose and functionality\n"
                    "- Code structure and organization\n"
                    "- Dependencies and imports\n"
                    "- Potential issues or improvements\n"
                    "- Documentation quality"
                )
            },
            {
                "role": "user",
                "content": f"Analyze this file ({path.name}):\n\n```\n{content}\n```"
            }
        ]

        call_fn(messages, model=model, stream=True)

    return {
        "name": "file_analyzer",
        "description": "Analyzes file content and structure",
        "run": run
    }
```

## Best Practices

### 1. Use System Prompts

Define the agent's behavior and constraints in a system message:

```python
messages = [
    {
        "role": "system",
        "content": (
            "You are a Python expert. Provide concise, runnable code examples. "
            "Always include error handling and type hints."
        )
    },
    # ... user messages
]
```

### 2. Handle User Input Safely

```python
def run(model, call_fn):
    import sys

    try:
        user_input = input("Enter prompt: ")
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    # Validate/sanitize input
    if not user_input.strip():
        print("Error: Empty input")
        return

    # ... proceed with agent logic
```

### 3. Provide Clear User Feedback

```python
from nora.core import utils

def run(model, call_fn):
    utils.info("Starting analysis...")

    # Do work

    utils.success("Analysis complete!")
```

### 4. Document Your Agent

```python
"""
Code Explainer Agent

This agent takes code snippets and provides detailed explanations of:
- What the code does (high-level purpose)
- How it works (line-by-line breakdown)
- Key concepts and patterns used
- Potential use cases

Usage:
    nora agent code_explainer

Examples:
    $ nora agent code_explainer
    Paste code: [your code here]
    Ctrl+D to submit
"""
```

### 5. Use Streaming for Better UX

```python
# Enable streaming for real-time responses
call_fn(messages, model=model, stream=True)

# Disable streaming if you need to capture the full response
call_fn(messages, model=model, stream=False)
```

### 6. Limit Input Size

```python
MAX_INPUT_SIZE = 4000  # chars

def run(model, call_fn):
    content = get_user_input()

    if len(content) > MAX_INPUT_SIZE:
        content = content[:MAX_INPUT_SIZE] + "\n...[truncated]..."
        print(f"⚠ Input truncated to {MAX_INPUT_SIZE} characters")

    # ... proceed
```

## Advanced Patterns

### Multi-Turn with State

For agents that maintain conversation state:

```python
def register():
    def run(model, call_fn):
        state = {
            "messages": [
                {"role": "system", "content": "System prompt"}
            ],
            "context": {}
        }

        while True:
            user_input = input("> ")
            if user_input == "exit":
                break

            # Update state
            state["messages"].append(
                {"role": "user", "content": user_input}
            )

            # Call model
            call_fn(state["messages"], model=model, stream=True)

            # In production, capture response and add to state["messages"]

    return {"name": "stateful", "description": "...", "run": run}
```

### Chained Prompts

For complex workflows with multiple steps:

```python
def run(model, call_fn):
    # Step 1: Analyze
    messages = [
        {"role": "user", "content": "Analyze this: ..."}
    ]
    # In production, capture response
    call_fn(messages, model=model, stream=False)

    # Step 2: Summarize (using previous response)
    messages.append(
        {"role": "user", "content": "Now summarize your analysis"}
    )
    call_fn(messages, model=model, stream=True)
```

### Tool-Using Agents

For agents that execute code or call external APIs:

```python
def run(model, call_fn):
    import subprocess

    messages = [
        {
            "role": "system",
            "content": (
                "You are a system administrator. When asked to check "
                "system status, respond with shell commands to run."
            )
        },
        {"role": "user", "content": "Check disk usage"}
    ]

    # Get command from model
    # In production, parse response to extract command
    call_fn(messages, model=model, stream=False)

    # Execute (with safety checks!)
    result = subprocess.run(
        ["df", "-h"],
        capture_output=True,
        text=True
    )

    # Send result back to model
    messages.append(
        {
            "role": "user",
            "content": f"Command output:\n{result.stdout}"
        }
    )
    call_fn(messages, model=model, stream=True)
```

## Testing Your Agent

### Manual Testing

```bash
# Run your agent
nora agent my-agent

# With specific model
nora agent my-agent --model llama3.2:3b

# With verbose logging
nora -v agent my-agent
```

### Debugging

Enable verbose logging to see API requests:

```bash
nora -v --log-file debug.log agent my-agent
```

Check the log file for:
- Plugin loading status
- API request payloads
- Response details
- Error tracebacks

### Unit Testing

Create tests in `tests/test_agents.py`:

```python
from nora.core.plugins import PluginLoader
import pathlib


def test_my_agent_loads():
    """Test that my_agent plugin loads successfully"""
    loader = PluginLoader()
    plugins = loader.load_plugins()

    assert "my_agent" in plugins
    assert "description" in plugins["my_agent"]
    assert "run" in plugins["my_agent"]
    assert callable(plugins["my_agent"]["run"])


def test_my_agent_structure():
    """Test my_agent has correct structure"""
    # Load plugin directly
    plugin_file = pathlib.Path("nora/plugins/my_agent.py")
    assert plugin_file.exists()

    # Import and check
    spec = importlib.util.spec_from_file_location("my_agent", plugin_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert hasattr(module, "register")
    plugin = module.register()

    assert plugin["name"] == "my_agent"
    assert "description" in plugin
    assert callable(plugin["run"])
```

## Troubleshooting

### Plugin Not Found

**Issue:** `nora agent my-agent` says "Plugin not found"

**Solutions:**
- Check filename matches plugin name: `my_agent.py` for `nora agent my_agent`
- Ensure file is in `nora/plugins/` directory
- Check file has `register()` function
- Verify `register()` returns correct dictionary structure

### Import Errors

**Issue:** Plugin fails to load with `ImportError`

**Solutions:**
- Check all imports are available in the environment
- Use absolute imports: `from nora.core import utils`
- Avoid circular imports
- Install missing dependencies: `pip install <package>`

### Agent Crashes

**Issue:** Agent exits unexpectedly

**Solutions:**
- Add try/except blocks around risky operations
- Handle `EOFError` and `KeyboardInterrupt` for user input
- Validate inputs before using them
- Check file paths exist before reading
- Use `--log-file` to capture error tracebacks

## Contributing Agents

To contribute your agent to NORA:

1. Create a well-documented plugin in `nora/plugins/`
2. Add unit tests in `tests/test_agents.py`
3. Update this guide with an example (if novel pattern)
4. Submit a pull request with:
   - Plugin file
   - Tests
   - Documentation
   - Usage example

See [Contributing.md](./Contributing.md) for full guidelines.

## Future Plugin Features (v0.4.0+)

Planned enhancements:
- **Tool Interface**: Standardized function calling for agents
- **State Persistence**: Save/load agent state between runs
- **Multi-Agent Orchestration**: Agents that coordinate with other agents
- **Plugin Dependencies**: Declare required packages in plugin metadata
- **Plugin Registry**: Remote plugin discovery and installation
- **Agent Templates**: More scaffolding options (web, data, system, etc.)

See [ROADMAP.md](../ROADMAP.md) for details.

---

**Next Steps:**
- Create your first agent: `nora project new my-agent`
- Explore examples in `nora/plugins/`
- Read [Overview.md](./Overview.md) for architecture details
- Check [Contributing.md](./Contributing.md) for development workflow
