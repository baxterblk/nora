# NORA Architecture Overview

## What is NORA?

**NORA (No Rush on Anything)** is a private, local AI agent CLI that provides a command-line interface to Ollama for chat, code assistance, and extensible agent plugins. It runs entirely on local infrastructure with a focus on user privacy and avoiding cloud dependencies.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         NORA CLI                            │
│                      (nora/cli.py)                          │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─────────────────┬─────────────────┬─────────────────┐
             ▼                 ▼                 ▼                 ▼
      ┌────────────┐    ┌────────────┐   ┌────────────┐   ┌────────────┐
      │   Config   │    │  History   │   │    Chat    │   │  Plugins   │
      │  Manager   │    │  Manager   │   │   Client   │   │   Loader   │
      └────────────┘    └────────────┘   └────────────┘   └────────────┘
      config.yaml       history.json     HTTP Requests    Dynamic Load
             │                 │                 │                 │
             ▼                 ▼                 ▼                 ▼
      ┌────────────┐    ┌────────────┐   ┌────────────┐   ┌────────────┐
      │  ~/.nora/  │    │  ~/.nora/  │   │   Ollama   │   │  plugins/  │
      │config.yaml │    │history.json│   │    API     │   │   *.py     │
      └────────────┘    └────────────┘   └────────────┘   └────────────┘
                                                 │
                                                 ▼
                                          ┌────────────┐
                                          │   Local    │
                                          │   Models   │
                                          └────────────┘
```

## Core Components

### 1. CLI Interface (`nora/cli.py`)

The main entry point that orchestrates all functionality:

- **Command Router**: Parses commands and routes to appropriate handlers
- **Argument Parsing**: Uses argparse for structured CLI arguments
- **Logging Setup**: Configures structured logging with optional file output
- **Colored Output**: ANSI-based terminal colors for enhanced UX

### 2. Configuration Manager (`nora/core/config.py`)

Manages YAML-based configuration with profile support:

- **ConfigManager Class**: Load/save configuration, dot-notation access
- **Profile Management**: Switch between different environments
- **Connection Testing**: Validate Ollama API connectivity
- **Type-Safe**: Comprehensive type hints and validation

**Key Methods:**
```python
load() -> Dict[str, Any]               # Load from ~/.nora/config.yaml
save() -> None                          # Persist to disk
get(key_path: str) -> Any               # Dot notation: "ollama.url"
set(key_path: str, value: Any) -> None  # Update nested values
test_connection() -> Tuple[bool, Any]   # Ping Ollama API
```

### 3. History Manager (`nora/core/history.py`)

Persistent JSON-based chat history:

- **HistoryManager Class**: Automatic file handling
- **Message Windowing**: Last 10 messages sent to API (prevents overflow)
- **Full Persistence**: Complete history stored locally
- **Type-Safe**: Strongly typed message structures

**Key Methods:**
```python
load() -> List[Dict[str, str]]                           # Load from disk
save(history: List[Dict[str, str]]) -> None              # Persist to disk
add_message(history, role: str, content: str) -> List    # Append with save
get_recent(history, limit: int = 10) -> List             # Context window
clear() -> None                                          # Reset history
```

### 4. Chat Client (`nora/core/chat.py`)

Ollama API integration with streaming support:

- **OllamaChat Class**: HTTP client for /api/chat endpoint
- **Streaming Responses**: Real-time token display
- **File Context**: Inject code files into prompts
- **Truncation**: Limit file content to 2000 chars

**Key Methods:**
```python
chat(messages, model, stream=False) -> None       # Send request
load_file_context(paths: List[str]) -> str        # Load file content
```

### 5. Plugin Loader (`nora/core/plugins.py`)

Dynamic plugin discovery and execution:

- **PluginLoader Class**: Import plugins at runtime
- **Validation**: Check plugin structure (register, run functions)
- **Error Handling**: Safe loading with fallback
- **Extensibility**: Drop files in plugins/ to add agents

**Key Methods:**
```python
load_plugins() -> Dict[str, Dict[str, Any]]       # Discover all .py files
get_plugin(name: str, plugins) -> Optional[Dict]  # Retrieve by name
run_plugin(name, plugins, model, chat_fn) -> None # Execute plugin
```

### 6. Utilities (`nora/core/utils.py`)

Colored output and logging configuration:

- **Colors Class**: ANSI color code constants
- **Output Functions**: success(), warning(), error(), info()
- **Connection Banner**: Startup status display
- **Logging Setup**: Configure file/console handlers

## v0.4.0 New Components

### 7. Multi-Agent Orchestrator (`nora/core/orchestrator.py`)

**NEW in v0.4.0**: Coordinates execution of multiple agents with shared memory and message passing.

**Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator                         │
│                                                         │
│  ┌─────────────┐      ┌──────────────┐                │
│  │  AgentTask  │──┬──→│ Sequential   │                │
│  │   Queue     │  │   │  Executor    │                │
│  └─────────────┘  │   └──────────────┘                │
│                   │                                     │
│                   └──→│  Parallel    │                │
│                       │  Executor    │                │
│                       └──────────────┘                │
│                              │                          │
│                              ▼                          │
│                    ┌──────────────────┐                │
│                    │  SharedMemory    │                │
│                    │  - Key-Value     │                │
│                    │  - Messages      │                │
│                    └──────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

**Key Classes:**
- **Orchestrator**: Main coordination class
  - `run_sequential(tasks)` - Execute agents in order
  - `run_parallel(tasks)` - Execute with dependency resolution

- **SharedMemory**: Thread-safe memory store
  - `get(key)`, `set(key, value)` - Key-value storage
  - `post_message(sender, message)` - Inter-agent messaging
  - `get_messages()` - Consume pending messages

- **AgentTask**: Represents a single agent in the workflow
  - `agent_name`, `agent_instance`, `model`
  - `depends_on` - List of dependencies
  - `config` - Agent-specific configuration

**Usage Example:**
```python
from nora.core.orchestrator import Orchestrator, AgentTask

orchestrator = Orchestrator(model="deepseek-coder:6.7b", call_fn=chat_fn)

tasks = [
    AgentTask("analyzer", analyzer_agent, model),
    AgentTask("reviewer", reviewer_agent, model, depends_on=["analyzer"]),
]

results = orchestrator.run_sequential(tasks)
```

### 8. Project Context Indexer (`nora/core/indexer.py`)

**NEW in v0.4.0**: Indexes project directories for code-aware conversations.

**Architecture:**
```
Project Directory
      │
      ├─> Walk Files (skip node_modules, __pycache__)
      │
      ├─> Extract Metadata
      │   ├─ Language detection
      │   ├─ Function/class extraction
      │   ├─ Import statements
      │   └─ Content preview
      │
      ├─> Generate Index
      │   └─ ~/.nora/index.json
      │
      └─> Search & Context
          ├─ Keyword search
          ├─ Relevance scoring
          └─ Chat context generation
```

**Key Features:**
- Supports 20+ languages (Python, JS, TS, Go, Rust, Java, etc.)
- Regex-based function/class extraction
- MD5 hash for change detection
- Thread-safe operations
- Simple keyword search with scoring

**Usage Example:**
```python
from nora.core.indexer import ProjectIndexer

indexer = ProjectIndexer()
index_data = indexer.index_project("./my-project")
indexer.save_index(index_data)

results = indexer.search("authentication", max_results=5)
context = indexer.get_context_for_chat("login", max_files=3)
```

### 9. Agent/Tool Base Classes (`nora/core/plugins.py`)

**NEW in v0.4.0**: Abstract base classes for class-based agents and tools.

**Agent Base Class:**
```python
from nora.core import Agent

class MyAgent(Agent):
    def metadata(self):
        return {
            "name": "my-agent",
            "description": "Custom agent",
            "version": "1.0.0",
            "capabilities": ["analysis", "generation"]
        }

    def run(self, context, model, call_fn, tools=None):
        # Agent logic
        return {"success": True, "output": "Result"}

    def on_start(self, context):
        # Optional: Called before run()
        pass

    def on_complete(self, result, context):
        # Optional: Called after successful run()
        pass

    def on_error(self, error, context):
        # Optional: Called on failure
        pass
```

**Tool Base Class:**
```python
from nora.core import Tool

class MyTool(Tool):
    def metadata(self):
        return {
            "name": "read_file",
            "description": "Read file content",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }

    def execute(self, params):
        path = params["path"]
        return pathlib.Path(path).read_text()
```

### 10. REST API Server (`nora/api/server.py`)

**NEW in v0.4.0**: FastAPI-based HTTP API for remote access.

**Architecture:**
```
HTTP Client
    │
    ├─> POST /chat ──────────> OllamaChat ──> Ollama
    │
    ├─> GET /agents ─────────> PluginLoader
    │
    ├─> POST /agents/{name} ─> PluginLoader.run_plugin()
    │
    ├─> POST /projects/index > ProjectIndexer.index_project()
    │
    ├─> POST /projects/search > ProjectIndexer.search()
    │
    └─> POST /team ──────────> Orchestrator ──> Multi-Agent Execution
```

**Endpoints:**
- `GET /` - API info and endpoints list
- `POST /chat` - Send chat messages (streaming support)
- `GET /agents` - List all available agents
- `POST /agents/{name}` - Execute specific agent
- `POST /projects/index` - Index a project directory
- `POST /projects/search` - Search indexed projects
- `POST /team` - Run multi-agent teams

**Usage Example:**
```bash
# Start API server
nora serve --host 0.0.0.0 --port 8001

# Make requests
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'
```

## Complete System Architecture (v0.4.0)

```
┌────────────────────────────────────────────────────────────────┐
│                        NORA v0.4.0                             │
│                                                                │
│  ┌──────────┐           ┌──────────┐          ┌──────────┐   │
│  │   CLI    │           │   REST   │          │  Python  │   │
│  │ Commands │           │   API    │          │  Import  │   │
│  └────┬─────┘           └────┬─────┘          └────┬─────┘   │
│       │                      │                     │          │
│       └──────────────────────┴─────────────────────┘          │
│                              │                                │
│       ┌──────────────────────┴──────────────────────┐         │
│       │            Core Components                   │         │
│       │  - ConfigManager    - PluginLoader          │         │
│       │  - HistoryManager   - OllamaChat            │         │
│       │  - Orchestrator     - ProjectIndexer        │         │
│       └──────────────────────┬──────────────────────┘         │
│                              │                                │
│       ┌──────────────────────┴──────────────────────┐         │
│       │         External Services                    │         │
│       │  - Ollama API (localhost:11434)             │         │
│       │  - User Plugins (nora/plugins/*.py)         │         │
│       │  - Project Files (for indexing)             │         │
│       └─────────────────────────────────────────────┘         │
│                                                                │
│  Storage: ~/.nora/config.yaml, history.json, index.json       │
└────────────────────────────────────────────────────────────────┘
```

## CLI Command Flow

### `nora chat`

Interactive REPL with optional file context:

```
User Input
    ↓
Parse Arguments (--context files, --system prompt)
    ↓
Load Configuration (ConfigManager)
    ↓
Test Ollama Connection (connection_banner)
    ↓
Load Chat History (HistoryManager)
    ↓
Load File Context (if --context provided)
    ↓
╔═════════════════════════════════════╗
║      Interactive Chat Loop          ║
║                                     ║
║  User: > prompt                     ║
║    ↓                                ║
║  Add to History (HistoryManager)    ║
║    ↓                                ║
║  Get Recent 10 Messages             ║
║    ↓                                ║
║  Send to Ollama (OllamaChat)        ║
║    ↓                                ║
║  Stream Response (colored output)   ║
║    ↓                                ║
║  Add Response to History            ║
║    ↓                                ║
║  Loop until /exit                   ║
╚═════════════════════════════════════╝
```

### `nora run "prompt"`

One-shot prompt execution:

```
Parse Arguments (prompt, --context, --system)
    ↓
Load Configuration
    ↓
Load File Context (if provided)
    ↓
Construct Message
    ↓
Send to Ollama (streaming)
    ↓
Display Response
    ↓
Exit
```

### `nora agent <name>`

Run an extensible agent plugin:

```
Parse Arguments (agent name)
    ↓
Load Configuration
    ↓
Load Plugins (PluginLoader)
    ↓
Find Plugin by Name
    ↓
Execute Plugin run() Function
    ↓
Plugin Controls Interaction
    ↓
Exit
```

### `nora project new <name>`

Scaffold a new plugin from template:

```
Parse Arguments (plugin name)
    ↓
Sanitize Name (alphanumeric + underscores)
    ↓
Check Existence (prevent overwrite)
    ↓
Write Template to plugins/<name>.py
    ↓
Display Success Message (colored)
    ↓
Exit
```

### `nora config <subcommand>`

Configuration management:

```
Parse Subcommand (show, set, test, use)
    ↓
┌────────────┬────────────┬────────────┬────────────┐
│   show     │    set     │   test     │    use     │
├────────────┼────────────┼────────────┼────────────┤
│ Display    │ Update key │ Ping Ollama│ Switch     │
│ current    │ with value │ /api/version│ profile   │
│ config     │ (dot path) │ endpoint   │ by name    │
└────────────┴────────────┴────────────┴────────────┘
    ↓
Display Result (colored)
    ↓
Exit
```

## Data Flow Example: Chat Session

```
1. User: nora chat --context nora/cli.py

2. CLI Startup:
   - Load config: http://localhost:11434, model: deepseek-coder:6.7b
   - Test connection: ✓ Connected
   - Display banner:
     ──────────────────────────────────────────────────────
     NORA | Connected | http://localhost:11434 | Model: deepseek-coder:6.7b
     ──────────────────────────────────────────────────────
   - Load history: 15 messages from ~/.nora/history.json
   - Load context: nora/cli.py (truncated to 2000 chars)

3. User Input: > explain the chat_loop function

4. Message Construction:
   messages = [
     {"role": "system", "content": "You are a helpful assistant..."},
     {"role": "user", "content": "FILE: nora/cli.py\n...[file content]..."},
     ...last 8 messages from history...
     {"role": "user", "content": "explain the chat_loop function"}
   ]

5. API Request:
   POST http://localhost:11434/api/chat
   {
     "model": "deepseek-coder:6.7b",
     "messages": [...],
     "stream": true
   }

6. Stream Response:
   {"message": {"content": "The"}}   → print "The"
   {"message": {"content": " chat"}} → print " chat"
   {"message": {"content": "_loop"}} → print "_loop"
   ...
   {"done": true}                    → newline

7. Update History:
   - Append user message to history.json
   - Append assistant response to history.json
   - Save to disk

8. Loop:
   - Prompt for next input
   - Repeat steps 3-7
```

## Extension Points

### Custom Plugins

Add new agents by creating `nora/plugins/myagent.py`:

```python
def register():
    def run(model, call_fn):
        # Your agent logic here
        messages = [{"role": "user", "content": "prompt"}]
        call_fn(messages, model=model, stream=True)

    return {
        "name": "myagent",
        "description": "What it does",
        "run": run
    }
```

Usage: `nora agent myagent`

### Custom Configuration Profiles

Add profiles in `~/.nora/config.yaml`:

```yaml
model: deepseek-coder:6.7b
ollama:
  url: http://localhost:11434
  verify_ssl: false

profiles:
  production:
    model: llama3.2:3b
    ollama:
      url: http://remote-server:11434
      verify_ssl: true

  development:
    model: codellama:7b
    ollama:
      url: http://localhost:11434
```

Usage: `nora config use production`

## Security & Privacy

- **Local-First**: All data stored locally in `~/.nora/`
- **No Cloud**: Direct connection to local/private Ollama instances
- **SSL Optional**: Configurable SSL verification for self-signed certs
- **No Telemetry**: Zero external tracking or analytics

## Performance Considerations

- **History Windowing**: Only last 10 messages sent to API (prevents context overflow)
- **File Truncation**: Context files limited to 2000 chars (prevents token limit issues)
- **Streaming Responses**: Real-time token display for better perceived performance
- **Async-Ready**: Architecture supports future async/await implementation

## Future Architecture Plans

See [ROADMAP.md](../ROADMAP.md) for v0.4.0 goals:
- Multi-agent coordination (orchestrator pattern)
- Project-wide context indexing (full repo awareness)
- Tool interface standardization (function calling)
- API layer for remote access
- Integration with Open-WebUI

---

For more details on specific components:
- **Plugin Development**: See [Agents.md](./Agents.md)
- **Configuration**: See [Config.md](./Config.md)
- **Contributing**: See [Contributing.md](./Contributing.md)
