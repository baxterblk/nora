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

## Class-Based Agents (v0.4.0+)

### Overview

NORA v0.4.0 introduces class-based agents using abstract base classes (ABC). Class-based agents are **recommended** for:
- Multi-agent teams (context sharing)
- Lifecycle hooks (on_start, on_complete, on_error)
- Tool integration
- State management across calls

**Backward Compatibility**: Legacy function-based plugins continue to work without changes.

### Agent Base Class

The `Agent` abstract base class provides structure for sophisticated agents:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable

class Agent(ABC):
    """Abstract base class for NORA agents."""

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """
        Return agent metadata.

        Returns:
            dict with keys: name, description, version, capabilities
        """
        pass

    @abstractmethod
    def run(
        self,
        context: Dict[str, Any],
        model: str,
        call_fn: Callable,
        tools: Optional[Dict[str, "Tool"]] = None
    ) -> Dict[str, Any]:
        """
        Execute agent logic.

        Args:
            context: Shared context from orchestrator or previous agents
            model: Ollama model to use
            call_fn: Function to call Ollama API
            tools: Available tools for this agent

        Returns:
            dict with keys:
                - success: bool
                - output: Any (agent result)
                - context_updates: dict (optional, updates shared context)
        """
        pass

    def on_start(self, context: Dict[str, Any]) -> None:
        """Hook called before run(). Override for setup."""
        pass

    def on_complete(self, result: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Hook called after successful run(). Override for cleanup."""
        pass

    def on_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Hook called on execution error. Override for error handling."""
        pass
```

### Example: Class-Based Code Analyzer

```python
"""
Code Analyzer Agent (Class-Based)

Analyzes code for patterns, issues, and improvements.
Compatible with multi-agent teams and context sharing.
"""

from nora.core import Agent
from typing import Dict, Any, Callable, Optional


class CodeAnalyzerAgent(Agent):
    """Analyzes code for patterns and potential issues."""

    def metadata(self) -> Dict[str, Any]:
        """Return agent metadata."""
        return {
            "name": "code_analyzer",
            "description": "Analyzes code for patterns, bugs, and improvements",
            "version": "2.0.0",
            "capabilities": ["analysis", "code-review", "team-compatible"]
        }

    def run(
        self,
        context: Dict[str, Any],
        model: str,
        call_fn: Callable,
        tools: Optional[Dict[str, "Tool"]] = None
    ) -> Dict[str, Any]:
        """Run code analysis."""
        # Access shared context from previous agents
        code = context.get("code", None)
        config = context.get("config", {})
        depth = config.get("depth", 3)

        if not code:
            return {
                "success": False,
                "output": "No code provided in context",
                "error": "Missing 'code' key in context"
            }

        # Build prompt
        messages = [
            {
                "role": "system",
                "content": f"You are a code analyzer. Analysis depth: {depth}/10"
            },
            {
                "role": "user",
                "content": f"Analyze this code:\n\n```\n{code}\n```"
            }
        ]

        # Call Ollama
        try:
            response = call_fn(messages, model=model, stream=False)
            analysis = response.get("response", "")

            # Return result and update shared context
            return {
                "success": True,
                "output": analysis,
                "context_updates": {
                    "analysis_result": analysis,
                    "issues_found": analysis.count("Issue:"),
                    "analyzer_version": "2.0.0"
                }
            }

        except Exception as e:
            return {
                "success": False,
                "output": None,
                "error": str(e)
            }

    def on_start(self, context: Dict[str, Any]) -> None:
        """Called before analysis starts."""
        print(f"🔍 Starting code analysis...")
        print(f"   Context keys: {list(context.keys())}")

    def on_complete(self, result: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Called after successful analysis."""
        issues = result.get("context_updates", {}).get("issues_found", 0)
        print(f"✓ Analysis complete: {issues} issues found")

    def on_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Called on error."""
        print(f"✗ Analysis failed: {error}")


# Register function for plugin discovery
def register():
    """Register the class-based agent."""
    return {
        "name": "code_analyzer",
        "description": "Class-based code analyzer with team support",
        "version": "2.0.0",
        "type": "class-based",
        "agent_class": CodeAnalyzerAgent
    }
```

### Tool Base Class

Tools are reusable utilities that agents can invoke:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class Tool(ABC):
    """Abstract base class for agent tools."""

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """
        Return tool metadata.

        Returns:
            dict with keys:
                - name: Tool identifier
                - description: What the tool does
                - parameters: JSON schema for parameters
        """
        pass

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Any:
        """
        Execute tool logic.

        Args:
            params: Tool parameters matching schema

        Returns:
            Tool execution result
        """
        pass
```

### Example: File Reader Tool

```python
"""File Reader Tool - Read file contents safely"""

from nora.core import Tool
from typing import Dict, Any
import pathlib


class FileReaderTool(Tool):
    """Tool for reading file contents."""

    def metadata(self) -> Dict[str, Any]:
        """Return tool metadata."""
        return {
            "name": "file_reader",
            "description": "Read file contents with size limits",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to read"
                    },
                    "max_size": {
                        "type": "integer",
                        "description": "Maximum file size in bytes",
                        "default": 1048576  # 1 MB
                    }
                },
                "required": ["file_path"]
            }
        }

    def execute(self, params: Dict[str, Any]) -> Any:
        """Read file with safety checks."""
        file_path = pathlib.Path(params["file_path"])
        max_size = params.get("max_size", 1048576)

        # Validate file exists
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}

        # Check file size
        if file_path.stat().st_size > max_size:
            return {"error": f"File too large (>{max_size} bytes)"}

        # Read file
        try:
            content = file_path.read_text()
            return {
                "success": True,
                "content": content,
                "size": len(content),
                "path": str(file_path)
            }
        except Exception as e:
            return {"error": f"Read error: {e}"}


def register():
    """Register the tool."""
    return {
        "name": "file_reader",
        "description": "Safely read file contents",
        "type": "tool",
        "tool_class": FileReaderTool
    }
```

### Using Tools in Agents

```python
class CodeAnalyzerAgent(Agent):
    """Agent that uses file_reader tool."""

    def run(self, context, model, call_fn, tools=None):
        # Get file_reader tool
        if tools and "file_reader" in tools:
            file_tool = tools["file_reader"]

            # Use tool to read file
            result = file_tool.execute({
                "file_path": "/path/to/code.py",
                "max_size": 5000000
            })

            if result.get("success"):
                code = result["content"]

                # Analyze the code
                messages = [{"role": "user", "content": f"Analyze: {code}"}]
                call_fn(messages, model=model, stream=False)

                return {"success": True, "output": "Analysis complete"}

        return {"success": False, "error": "Tool not available"}
```

## Migrating to Class-Based Agents

### Why Migrate?

**Benefits of class-based agents:**
1. **Context Sharing**: Access data from previous agents in teams
2. **Lifecycle Hooks**: Setup/cleanup with on_start, on_complete, on_error
3. **Tool Integration**: Use standardized tools across agents
4. **Better Testing**: Mock context and tools easily
5. **Team Compatible**: Required for multi-agent orchestration

### Migration Guide

#### Legacy Function-Based Agent

```python
def register():
    """Legacy function-based agent."""

    def run(model, call_fn):
        messages = [{"role": "user", "content": "Hello"}]
        call_fn(messages, model=model, stream=True)

    return {
        "name": "greeter",
        "description": "Simple greeter",
        "run": run
    }
```

#### Migrated Class-Based Agent

```python
from nora.core import Agent
from typing import Dict, Any, Callable, Optional


class GreeterAgent(Agent):
    """Migrated greeter agent."""

    def metadata(self) -> Dict[str, Any]:
        """Return metadata."""
        return {
            "name": "greeter",
            "description": "Simple greeter (class-based)",
            "version": "2.0.0"
        }

    def run(
        self,
        context: Dict[str, Any],
        model: str,
        call_fn: Callable,
        tools: Optional[Dict[str, "Tool"]] = None
    ) -> Dict[str, Any]:
        """Run greeter logic."""
        # Access context if available
        user_name = context.get("user_name", "User")

        messages = [
            {"role": "user", "content": f"Greet {user_name}"}
        ]

        try:
            call_fn(messages, model=model, stream=True)

            return {
                "success": True,
                "output": f"Greeted {user_name}",
                "context_updates": {
                    "greeted": True,
                    "greeted_user": user_name
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def on_start(self, context: Dict[str, Any]) -> None:
        """Log startup."""
        print("👋 Greeter agent starting...")

    def on_complete(self, result: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Log completion."""
        print("✓ Greeting complete!")


def register():
    """Register the class-based agent."""
    return {
        "name": "greeter",
        "description": "Class-based greeter",
        "version": "2.0.0",
        "type": "class-based",
        "agent_class": GreeterAgent
    }
```

### Migration Checklist

- [ ] Create class inheriting from `Agent`
- [ ] Implement `metadata()` method
- [ ] Implement `run()` method with new signature
- [ ] Update `register()` to return `agent_class`
- [ ] Add context handling in `run()`
- [ ] Return dict with `success`, `output`, `context_updates`
- [ ] (Optional) Implement lifecycle hooks
- [ ] Update tests to use new context-aware pattern
- [ ] Update documentation with new usage

## Team-Compatible Agents

Agents designed for multi-agent teams should:

### 1. Accept and Use Context

```python
def run(self, context, model, call_fn, tools=None):
    # Read from previous agents
    previous_result = context.get("analysis_result")

    # Use it
    messages = [
        {"role": "user", "content": f"Review: {previous_result}"}
    ]
    call_fn(messages, model=model, stream=False)
```

### 2. Update Shared Context

```python
    return {
        "success": True,
        "output": "Review complete",
        "context_updates": {
            "review_score": 8.5,
            "issues": ["Issue 1", "Issue 2"],
            "reviewer_name": "ReviewAgent"
        }
    }
```

### 3. Handle Missing Context Gracefully

```python
def run(self, context, model, call_fn, tools=None):
    code = context.get("code")

    if not code:
        return {
            "success": False,
            "output": "No code to analyze",
            "error": "Missing 'code' in context"
        }

    # Proceed with analysis
```

### 4. Use Configuration from Context

```python
def run(self, context, model, call_fn, tools=None):
    # Agent-specific config from team YAML
    config = context.get("config", {})
    depth = config.get("depth", 3)
    strict = config.get("strict", False)

    # Use config
    system_prompt = f"Analysis depth: {depth}, Strict mode: {strict}"
```

### 5. Implement Lifecycle Hooks

```python
def on_start(self, context: Dict[str, Any]) -> None:
    """Log context on startup."""
    print(f"Starting with context keys: {list(context.keys())}")

def on_complete(self, result: Dict[str, Any], context: Dict[str, Any]) -> None:
    """Log success."""
    print(f"✓ Success: {result.get('output')}")

def on_error(self, error: Exception, context: Dict[str, Any]) -> None:
    """Log error with context."""
    print(f"✗ Error: {error}")
    print(f"Context at error: {context}")
```

### Complete Team Example

```python
"""
Code Review Team Workflow

1. FetcherAgent: Loads code from file
2. AnalyzerAgent: Analyzes code
3. ReviewerAgent: Reviews analysis
4. ReportAgent: Generates final report

Each agent updates shared context for next agent.
"""

from nora.core import Agent


class FetcherAgent(Agent):
    """Fetches code from file path."""

    def metadata(self):
        return {"name": "fetcher", "description": "Fetch code"}

    def run(self, context, model, call_fn, tools=None):
        file_path = context.get("config", {}).get("file_path")

        # Read file (simplified)
        code = open(file_path).read()

        return {
            "success": True,
            "output": f"Loaded {len(code)} chars",
            "context_updates": {
                "code": code,
                "file_path": file_path
            }
        }


class AnalyzerAgent(Agent):
    """Analyzes code from context."""

    def metadata(self):
        return {"name": "analyzer", "description": "Analyze code"}

    def run(self, context, model, call_fn, tools=None):
        code = context.get("code")

        messages = [
            {"role": "user", "content": f"Analyze: {code}"}
        ]
        response = call_fn(messages, model=model, stream=False)

        return {
            "success": True,
            "output": response["response"],
            "context_updates": {
                "analysis": response["response"]
            }
        }


class ReviewerAgent(Agent):
    """Reviews analysis from context."""

    def metadata(self):
        return {"name": "reviewer", "description": "Review analysis"}

    def run(self, context, model, call_fn, tools=None):
        analysis = context.get("analysis")

        messages = [
            {"role": "user", "content": f"Review: {analysis}"}
        ]
        response = call_fn(messages, model=model, stream=False)

        return {
            "success": True,
            "output": response["response"],
            "context_updates": {
                "review": response["response"],
                "review_score": 8.5
            }
        }


# Team configuration (team-config.yaml):
# name: code-review-team
# mode: sequential
# agents:
#   - name: fetch
#     agent: fetcher
#     config:
#       file_path: /path/to/code.py
#   - name: analyze
#     agent: analyzer
#     depends_on: [fetch]
#   - name: review
#     agent: reviewer
#     depends_on: [analyze]
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

## Plugin Features by Version

### v0.4.0 (Released)
- ✅ **Tool Interface**: Abstract Tool base class for standardized function calling
- ✅ **Multi-Agent Orchestration**: Orchestrator for sequential/parallel agent teams
- ✅ **Agent Base Class**: Context-aware agents with lifecycle hooks
- ✅ **Context Sharing**: Shared memory between agents in teams
- ✅ **Team Configuration**: YAML-based team definitions

### v0.4.1+ (Planned)
- **State Persistence**: Save/load agent state between runs
- **Plugin Dependencies**: Declare required packages in plugin metadata
- **Plugin Registry**: Remote plugin discovery and installation
- **Agent Templates**: More scaffolding options (web, data, system, etc.)
- **Tool Marketplace**: Shared tool library across agents
- **Agent Versioning**: Semantic versioning for agent plugins
- **Hot Reload**: Dynamic plugin reload without restart

See [ROADMAP.md](../ROADMAP.md) for full roadmap.

---

**Next Steps:**
- Create your first agent: `nora project new my-agent`
- Explore examples in `nora/plugins/`
- Read [Overview.md](./Overview.md) for architecture details
- Check [Contributing.md](./Contributing.md) for development workflow
