# NORA REST API Documentation

## Overview

NORA v0.4.0 provides a REST API built with FastAPI that exposes all NORA functionality via HTTP endpoints. This enables remote access to chat, agents, project indexing, and multi-agent orchestration.

**Base URL**: `http://localhost:8001` (default)
**API Version**: 0.4.0

## Starting the API Server

```bash
# Install API dependencies
pip install -e ".[api]"

# Start server on default port (8001)
nora serve

# Start on custom host/port
nora serve --host 0.0.0.0 --port 9000
```

The server runs with uvicorn and includes:
- Automatic request validation via Pydantic
- OpenAPI/Swagger documentation at `/docs`
- ReDoc documentation at `/redoc`
- Structured logging for all requests

## Authentication

**Current Status**: No authentication required (v0.4.0)

⚠️ **Security Note**: The API server has no authentication in v0.4.0. Only run on trusted networks or localhost. Authentication will be added in a future release.

## Endpoints

### 1. GET / - API Information

Get API version and available endpoints.

**Request**:
```bash
curl http://localhost:8001/
```

**Response** (200 OK):
```json
{
  "name": "NORA API",
  "version": "0.4.0",
  "endpoints": [
    "/chat",
    "/agents",
    "/agents/{name}",
    "/projects/index",
    "/projects/search",
    "/team"
  ]
}
```

**Use Case**: Health check and API discovery.

---

### 2. POST /chat - Chat with Ollama

Send messages to Ollama for interactive chat.

**Request Schema**:
```json
{
  "messages": [
    {"role": "user", "content": "string"},
    {"role": "assistant", "content": "string"}
  ],
  "model": "string (optional)",
  "stream": false
}
```

**Fields**:
- `messages` (required): Array of message objects with `role` and `content`
- `model` (optional): Ollama model to use (defaults to config default)
- `stream` (optional): Enable streaming responses (default: false)

**Example Request**:
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Explain what NORA does"}
    ],
    "model": "deepseek-coder:6.7b",
    "stream": false
  }'
```

**Response** (200 OK):
```json
{
  "response": "NORA is a private, local AI agent CLI...",
  "model": "deepseek-coder:6.7b"
}
```

**Error Responses**:
- `422 Unprocessable Entity`: Invalid request format
- `500 Internal Server Error`: Ollama connection error or model not available

**Example Error**:
```json
{
  "detail": "Connection refused to Ollama server"
}
```

---

### 3. GET /agents - List Available Agents

Get all registered agent plugins.

**Request**:
```bash
curl http://localhost:8001/agents
```

**Response** (200 OK):
```json
{
  "agents": [
    {
      "name": "greeter",
      "description": "Simple greeting agent",
      "version": "1.0.0",
      "type": "legacy-function"
    },
    {
      "name": "code_analyzer",
      "description": "Analyze code for patterns",
      "version": "1.2.0",
      "type": "class-based"
    }
  ]
}
```

**Fields**:
- `name`: Agent identifier (matches plugin filename)
- `description`: Human-readable description
- `version`: Agent version string
- `type`: Plugin type (`legacy-function` or `class-based`)

**Use Case**: Discover available agents before execution.

---

### 4. POST /agents/{agent_name} - Execute Agent

Run a specific agent by name.

**Path Parameters**:
- `agent_name` (required): Name of agent to execute

**Request Schema**:
```json
{
  "agent_name": "string",
  "model": "string (optional)",
  "context": {
    "key": "value"
  }
}
```

**Fields**:
- `agent_name`: Agent to execute (matches plugin name)
- `model` (optional): Override default model for this execution
- `context` (optional): Additional context data for agent

**Example Request**:
```bash
curl -X POST http://localhost:8001/agents/greeter \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "greeter",
    "model": "llama3.2:3b",
    "context": {"user": "Alice"}
  }'
```

**Response** (200 OK):
```json
{
  "agent_name": "greeter",
  "success": true,
  "output": "Agent completed",
  "error": null
}
```

**Response on Failure** (200 OK with error):
```json
{
  "agent_name": "invalid_agent",
  "success": false,
  "output": null,
  "error": "Agent execution failed"
}
```

**Error Responses**:
- `404 Not Found`: Agent does not exist
- `500 Internal Server Error`: Unexpected error during execution

**Example 404 Error**:
```json
{
  "detail": "Agent not found: invalid_agent"
}
```

---

### 5. POST /projects/index - Index Project

Index a project directory for code-aware search.

**Request Schema**:
```json
{
  "project_path": "/absolute/path/to/project",
  "project_name": "string (optional)"
}
```

**Fields**:
- `project_path` (required): Absolute path to project directory
- `project_name` (optional): Human-readable project name (defaults to directory name)

**Example Request**:
```bash
curl -X POST http://localhost:8001/projects/index \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "/home/user/myproject",
    "project_name": "My Project"
  }'
```

**Response** (200 OK):
```json
{
  "project_name": "My Project",
  "total_files": 127,
  "total_size": 2458621
}
```

**Fields**:
- `project_name`: Name of indexed project
- `total_files`: Number of files indexed
- `total_size`: Total size in bytes

**Error Responses**:
- `422 Unprocessable Entity`: Invalid path format
- `500 Internal Server Error`: Directory not found or permission denied

**Example Error**:
```json
{
  "detail": "Directory not found: /invalid/path"
}
```

**Notes**:
- Index is saved to `~/.nora/index.json`
- Supports 20+ languages (Python, JS, TS, Go, Rust, Java, etc.)
- Automatically skips `node_modules`, `__pycache__`, `.git`, `.venv`
- Files larger than 1MB are skipped by default

---

### 6. POST /projects/search - Search Project Index

Search the indexed project with keyword matching.

**Request Schema**:
```json
{
  "query": "string",
  "max_results": 10
}
```

**Fields**:
- `query` (required): Search keywords or phrase
- `max_results` (optional): Maximum results to return (default: 10)

**Example Request**:
```bash
curl -X POST http://localhost:8001/projects/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "authentication",
    "max_results": 5
  }'
```

**Response** (200 OK):
```json
{
  "query": "authentication",
  "results": [
    {
      "path": "src/auth/login.py",
      "language": "python",
      "size": 3421,
      "functions": ["authenticate_user", "validate_token"],
      "score": 15,
      "preview": "def authenticate_user(username, password)..."
    },
    {
      "path": "src/auth/middleware.py",
      "language": "python",
      "size": 1892,
      "functions": ["auth_middleware", "check_permissions"],
      "score": 10,
      "preview": "class AuthMiddleware..."
    }
  ]
}
```

**Result Fields**:
- `path`: Relative path from project root
- `language`: Detected programming language
- `size`: File size in bytes
- `functions`: Extracted function/class names
- `score`: Relevance score (higher is better)
- `preview`: First 500 characters of file

**Error Responses**:
- `422 Unprocessable Entity`: Invalid query format
- `500 Internal Server Error`: Index not loaded or search error

**Scoring Algorithm**:
- Path match: 10 points
- Content match: 5 points per occurrence
- Function name match: 8 points per function
- Import match: 3 points per import

---

### 7. POST /team - Run Multi-Agent Team

Execute a multi-agent team from a YAML configuration file.

**Request Schema**:
```json
{
  "config_path": "/path/to/team-config.yaml",
  "mode": "sequential|parallel (optional)"
}
```

**Fields**:
- `config_path` (required): Path to team YAML configuration
- `mode` (optional): Override execution mode from config

**Example Request**:
```bash
curl -X POST http://localhost:8001/team \
  -H "Content-Type: application/json" \
  -d '{
    "config_path": "/home/user/my-team.yaml",
    "mode": "parallel"
  }'
```

**Team Config Example** (`my-team.yaml`):
```yaml
name: code-review-team
mode: sequential
model: deepseek-coder:6.7b
agents:
  - name: analyzer
    agent: code_analyzer
    config:
      depth: 3
  - name: reviewer
    agent: code_reviewer
    depends_on: [analyzer]
```

**Response** (200 OK):
```json
{
  "team_name": "code-review-team",
  "results": {
    "analyzer": {
      "success": true,
      "output": "Analysis complete",
      "context_updates": {
        "issues_found": 3
      }
    },
    "reviewer": {
      "success": true,
      "output": "Review complete",
      "context_updates": {
        "review_score": 8.5
      }
    }
  }
}
```

**Result Structure**:
- `team_name`: Name from YAML config
- `results`: Dict of agent results keyed by agent name
  - `success`: Boolean execution status
  - `output`: Agent output message
  - `context_updates`: Shared memory updates from agent

**Error Responses**:
- `422 Unprocessable Entity`: Invalid config path or YAML format
- `500 Internal Server Error`: Agent not found or execution error

**Example Error**:
```json
{
  "detail": "Agent not found in config: invalid_agent"
}
```

**Notes**:
- `sequential` mode: Agents run one after another
- `parallel` mode: Agents run concurrently with dependency resolution
- Agents share memory via `context_updates`
- See [Teams.md](Teams.md) for complete team configuration guide

---

## Interactive API Documentation

FastAPI provides interactive documentation:

### Swagger UI
```
http://localhost:8001/docs
```

- Try out endpoints in browser
- Auto-generated from Pydantic models
- Request/response examples

### ReDoc
```
http://localhost:8001/redoc
```

- Clean, searchable documentation
- Schema explorer
- Export as OpenAPI JSON

## Error Handling

All endpoints follow consistent error formats:

**Validation Error** (422):
```json
{
  "detail": [
    {
      "loc": ["body", "messages"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**Server Error** (500):
```json
{
  "detail": "Internal server error message"
}
```

## Usage Examples

### Complete Chat Session

```bash
# 1. Check API is running
curl http://localhost:8001/

# 2. List available models (via config)
curl http://localhost:8001/agents

# 3. Start chat conversation
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is NORA?"}
    ]
  }'

# 4. Continue conversation
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "What is NORA?"},
      {"role": "assistant", "content": "NORA is a local AI agent..."},
      {"role": "user", "content": "How do I install it?"}
    ]
  }'
```

### Project Indexing Workflow

```bash
# 1. Index a project
curl -X POST http://localhost:8001/projects/index \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "/home/user/myproject",
    "project_name": "My Project"
  }'

# Response: {"project_name": "My Project", "total_files": 127, "total_size": 2458621}

# 2. Search for functions
curl -X POST http://localhost:8001/projects/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "database connection",
    "max_results": 5
  }'

# 3. Search for specific files
curl -X POST http://localhost:8001/projects/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "config.py",
    "max_results": 3
  }'
```

### Multi-Agent Team Execution

```bash
# 1. Create team config (team-config.yaml)
cat > team-config.yaml << EOF
name: analysis-team
mode: parallel
model: deepseek-coder:6.7b
agents:
  - name: linter
    agent: code_linter
  - name: analyzer
    agent: code_analyzer
  - name: report
    agent: report_generator
    depends_on: [linter, analyzer]
EOF

# 2. Execute team
curl -X POST http://localhost:8001/team \
  -H "Content-Type: application/json" \
  -d '{
    "config_path": "./team-config.yaml",
    "mode": "parallel"
  }'

# 3. Check results
# Response shows status of each agent and shared context
```

## Python Client Example

```python
import requests

class NoraClient:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url

    def chat(self, messages, model=None):
        """Send chat messages."""
        response = requests.post(
            f"{self.base_url}/chat",
            json={"messages": messages, "model": model, "stream": False}
        )
        return response.json()

    def list_agents(self):
        """Get available agents."""
        response = requests.get(f"{self.base_url}/agents")
        return response.json()["agents"]

    def run_agent(self, agent_name, context=None):
        """Execute an agent."""
        response = requests.post(
            f"{self.base_url}/agents/{agent_name}",
            json={"agent_name": agent_name, "context": context or {}}
        )
        return response.json()

    def index_project(self, project_path, project_name=None):
        """Index a project directory."""
        response = requests.post(
            f"{self.base_url}/projects/index",
            json={"project_path": project_path, "project_name": project_name}
        )
        return response.json()

    def search_project(self, query, max_results=10):
        """Search indexed project."""
        response = requests.post(
            f"{self.base_url}/projects/search",
            json={"query": query, "max_results": max_results}
        )
        return response.json()

    def run_team(self, config_path, mode=None):
        """Execute multi-agent team."""
        response = requests.post(
            f"{self.base_url}/team",
            json={"config_path": config_path, "mode": mode}
        )
        return response.json()

# Usage
client = NoraClient()

# Chat
result = client.chat([
    {"role": "user", "content": "Hello!"}
])
print(result["response"])

# List agents
agents = client.list_agents()
for agent in agents:
    print(f"{agent['name']}: {agent['description']}")

# Run agent
result = client.run_agent("greeter")
print(result)

# Index and search
index_result = client.index_project("/path/to/project")
print(f"Indexed {index_result['total_files']} files")

search_results = client.search_project("authentication")
for result in search_results["results"]:
    print(f"{result['path']}: {result['score']}")
```

## Performance Considerations

### Response Times

Typical response times on local hardware:

| Endpoint | Avg Time | Notes |
|----------|----------|-------|
| GET / | <10ms | Instant |
| GET /agents | <50ms | Plugin loading |
| POST /chat | 500ms - 5s | Depends on model and prompt |
| POST /agents/{name} | 500ms - 10s | Depends on agent complexity |
| POST /projects/index | 100ms - 30s | Depends on project size |
| POST /projects/search | 50ms - 500ms | Depends on index size |
| POST /team | 1s - 60s | Depends on team complexity |

### Rate Limiting

**Current Status**: No rate limiting (v0.4.0)

Recommendations:
- Run on localhost or trusted networks only
- Consider reverse proxy (nginx) with rate limiting for production
- Monitor Ollama resource usage during concurrent requests

### Concurrency

- FastAPI uses async handlers for non-blocking I/O
- Ollama chat requests are synchronous (blocks until complete)
- Multiple concurrent requests may queue at Ollama
- Consider running multiple Ollama instances for high concurrency

## Troubleshooting

### Server Won't Start

```bash
# Check if port is in use
lsof -i :8001

# Check FastAPI installation
python -c "import fastapi; print(fastapi.__version__)"

# Check uvicorn installation
python -c "import uvicorn; print(uvicorn.__version__)"

# Reinstall API dependencies
pip install -e ".[api]"
```

### Connection Refused to Ollama

```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Check NORA config
nora config show

# Test connection
nora config test
```

### 422 Validation Errors

```bash
# Check request JSON format
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -v \
  -d '{"messages": [{"role": "user", "content": "test"}]}'

# View detailed error in response body
```

### Agent Not Found (404)

```bash
# List available agents
curl http://localhost:8001/agents

# Verify plugin exists
ls nora/plugins/*.py

# Check plugin registration
nora agents
```

## Future Enhancements

Planned for v0.5.0+:

- **Authentication**: API key or JWT-based auth
- **Rate Limiting**: Per-client request limits
- **Streaming**: Server-sent events for streaming chat responses
- **Webhooks**: Callback URLs for long-running operations
- **Batch Operations**: Process multiple requests in single API call
- **WebSocket**: Real-time bidirectional communication
- **API Versioning**: `/v1/`, `/v2/` path prefixes

See [ROADMAP.md](../ROADMAP.md) for details.

---

**Next Steps:**
- Try the interactive docs at `/docs`
- See [Teams.md](Teams.md) for multi-agent configuration
- See [Testing.md](Testing.md) for API testing guide
- Check [CHANGELOG.md](../CHANGELOG.md) for version history
