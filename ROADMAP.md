# NORA Project Roadmap

## Current Status: v0.3.0 (Released)

NORA v0.3.0 represents a major milestone with a complete modular architecture, comprehensive testing, and production-ready infrastructure.

**✅ Completed (v0.3.0):**
- Modular core architecture (chat, config, history, plugins, utils)
- Structured logging with colored output
- Type hints and comprehensive docstrings
- Plugin scaffolding commands (`nora project new/list`)
- Comprehensive pytest test suite (>80% coverage)
- GitHub Actions CI/CD pipeline
- Developer documentation

---

## v0.4.0 Goals: Intelligence & Integration

**Target Release:** Q2 2025
**Focus:** Multi-agent coordination, tool interfaces, and external integrations

### High Priority Features

#### 1. Multi-Agent Runtime 🤖 [PRIORITY: HIGH]

Enable coordination between multiple specialized agents working together on complex tasks.

**Features:**
- [ ] Agent orchestrator pattern for coordination
- [ ] Message passing between agents
- [ ] Shared context/memory store
- [ ] CLI: `nora agent run --team` for multi-agent execution
- [ ] Agent roles and specializations (planner, coder, reviewer, tester)
- [ ] Sequential and parallel agent execution modes
- [ ] Inter-agent communication protocols

**Usage Example:**
```bash
# Run a team of agents on a complex task
nora agent run --team code-review \
  --agents planner,coder,reviewer,tester \
  --context src/

# Define custom agent teams
nora team create bug-hunters \
  --agents analyzer,fixer,tester \
  --coordinator sequential
```

**Technical Considerations:**
- Design agent communication protocol (JSON-based messages)
- Implement shared context store (in-memory or Redis)
- Create orchestrator that manages agent lifecycle
- Support both sequential and parallel execution
- Add conflict resolution for competing agent decisions

---

#### 2. Project Context Indexing 📚 [PRIORITY: HIGH]

Enable full repository awareness for code-understanding agents.

**Features:**
- [ ] Index entire project structure (AST parsing)
- [ ] Semantic code search (embeddings-based)
- [ ] Function/class dependency graphs
- [ ] Automatic context injection based on relevance
- [ ] Incremental indexing on file changes
- [ ] CLI: `nora index build` and `nora index search <query>`
- [ ] Context relevance scoring

**Usage Example:**
```bash
# Build project index
nora index build

# Search for relevant code
nora index search "authentication logic"

# Chat with full repo context (auto-injected)
nora chat --auto-context
> How does the authentication flow work?
```

**Technical Considerations:**
- Use tree-sitter for AST parsing
- Generate embeddings with local models (all-MiniLM-L6-v2)
- Store index in SQLite or vector DB (Chroma/FAISS)
- Implement relevance scoring algorithm
- Handle large codebases efficiently (chunking, caching)
- Support common languages (Python, JS, Go, Rust, Java)

---

#### 3. Tool Interface Standardization 🔧 [PRIORITY: MEDIUM]

Standardize how agents interact with external tools and functions.

**Features:**
- [ ] Function calling interface for agents
- [ ] Built-in tools: file operations, shell commands, search, HTTP requests
- [ ] Tool registration and discovery
- [ ] Permission system for tool execution
- [ ] Tool execution sandboxing
- [ ] CLI: `nora tools list` and `nora tools register <tool>`

**Tool Definition Example:**
```python
# nora/tools/file_ops.py
def register():
    return {
        "name": "read_file",
        "description": "Read contents of a file",
        "parameters": {
            "path": {"type": "string", "description": "File path"}
        },
        "execute": lambda path: pathlib.Path(path).read_text()
    }
```

**Agent Usage:**
```python
def run(model, call_fn, tools):
    # Agent requests file content
    content = tools.call("read_file", {"path": "config.yaml"})

    # Agent uses HTTP tool
    data = tools.call("http_get", {"url": "https://api.example.com/data"})
```

**Technical Considerations:**
- Design tool specification format (JSON Schema)
- Implement tool sandbox with resource limits
- Add permission model (prompt user for dangerous operations)
- Support async tool execution
- Create tool marketplace/registry
- Document tool development guide

---

#### 4. API Layer 🌐 [PRIORITY: MEDIUM]

Expose NORA functionality via REST API for remote access and integrations.

**Features:**
- [ ] RESTful API with FastAPI/Flask
- [ ] API authentication (tokens/API keys)
- [ ] WebSocket support for streaming responses
- [ ] Rate limiting and quota management
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Client SDKs (Python, JS, Go)
- [ ] CLI: `nora serve` to start API server

**API Endpoints:**
```
POST   /api/chat              # Send chat message
GET    /api/agents            # List available agents
POST   /api/agents/{name}     # Run specific agent
GET    /api/config            # Get configuration
PUT    /api/config            # Update configuration
POST   /api/index/build       # Build code index
POST   /api/index/search      # Search indexed code
WS     /api/stream            # WebSocket for streaming
```

**Usage Example:**
```bash
# Start NORA API server
nora serve --port 8080 --auth-token my-secret-token

# Client usage
curl -X POST http://localhost:8080/api/chat \
  -H "Authorization: Bearer my-secret-token" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'
```

**Technical Considerations:**
- Use FastAPI for async/streaming support
- Implement JWT or API key authentication
- Add CORS configuration for web clients
- Support streaming responses (SSE or WebSocket)
- Rate limiting with Redis
- Deploy with Docker/systemd

---

#### 5. Open-WebUI Integration 🖥️ [PRIORITY: MEDIUM]

Integrate NORA with Open-WebUI for a browser-based interface.

**Features:**
- [ ] Open-WebUI compatible API endpoints
- [ ] Model endpoint that proxies to Ollama
- [ ] NORA-specific features in UI (agents, tools, context)
- [ ] Authentication integration
- [ ] Configuration UI for NORA settings
- [ ] Agent management UI

**Architecture:**
```
Open-WebUI (Frontend) → NORA API → Ollama
                             ↓
                        Agents, Tools, Context
```

**Usage:**
```bash
# Start NORA with Open-WebUI compatibility
nora serve --openwebui --port 8080

# Access Open-WebUI at http://localhost:8080
# Use NORA agents and features through the web interface
```

**Technical Considerations:**
- Implement Open-WebUI API compatibility layer
- Map NORA concepts (agents, tools) to UI elements
- Support custom UI components for NORA features
- Handle authentication pass-through
- Deploy with Docker Compose (NORA + Open-WebUI)

---

#### 6. Security & Authentication 🔒 [PRIORITY: HIGH]

Secure remote access and protect sensitive operations.

**Features:**
- [ ] API authentication (JWT tokens, API keys)
- [ ] User management and RBAC (role-based access control)
- [ ] Encrypted configuration storage
- [ ] Audit logging for sensitive operations
- [ ] Rate limiting and abuse prevention
- [ ] Secure tool execution (sandboxing)
- [ ] HTTPS/TLS support

**Security Model:**
```yaml
users:
  alice:
    role: admin
    permissions:
      - chat
      - agents.*
      - tools.*
      - config.*

  bob:
    role: user
    permissions:
      - chat
      - agents.read-only
      - tools.safe-only

  api-client:
    role: service
    permissions:
      - chat
      - agents.specific-list
    rate_limit: 100/hour
```

**Usage:**
```bash
# Create user
nora users create alice --role admin

# Generate API key
nora users token alice --expire 30d

# Start server with auth
nora serve --auth-required --users users.yaml
```

**Technical Considerations:**
- Implement JWT-based authentication
- Store encrypted credentials (bcrypt/argon2)
- Add RBAC with permission checking
- Audit log all operations
- Rate limiting per user/API key
- Secure tool execution (disable dangerous operations)

---

### Medium Priority Features

#### 7. Rich Terminal Interface 🎨 [PRIORITY: MEDIUM]

Enhance CLI with better visuals and interactivity.

**Features:**
- [ ] Syntax highlighting for code blocks (pygments)
- [ ] Progress bars for long operations (tqdm/rich)
- [ ] Interactive prompts with autocomplete (prompt_toolkit)
- [ ] Markdown rendering in terminal (rich)
- [ ] Status indicators and spinners
- [ ] Table formatting for structured output

**Example:**
```bash
nora chat
# Shows rich markdown rendering with syntax highlighting
# Progress bars for model loading
# Autocomplete for commands and file paths
```

---

#### 8. Conversation Branching 🌳 [PRIORITY: LOW]

Enable branching and exploring alternative conversation paths.

**Features:**
- [ ] Branch from any message in history
- [ ] Switch between branches
- [ ] Merge branches
- [ ] Visualize conversation tree
- [ ] CLI: `nora history branch`, `nora history switch`

**Usage:**
```bash
# Create branch from message 5
nora history branch --from 5 --name alternative-approach

# Switch branches
nora history switch alternative-approach

# List branches
nora history branches

# Merge branch
nora history merge alternative-approach
```

---

#### 9. Plugin Versioning & Registry 📦 [PRIORITY: LOW]

Enable plugin discovery, installation, and management.

**Features:**
- [ ] Plugin metadata (version, dependencies, author)
- [ ] Remote plugin registry
- [ ] CLI: `nora plugins install <name>`, `nora plugins search <query>`
- [ ] Plugin update checking
- [ ] Dependency resolution

**Usage:**
```bash
# Search for plugins
nora plugins search code-review

# Install plugin
nora plugins install awesome-code-reviewer

# Update all plugins
nora plugins update --all

# Uninstall plugin
nora plugins uninstall awesome-code-reviewer
```

---

### Technical Debt & Improvements

#### Code Quality
- [ ] Add `black` and `isort` for code formatting
- [ ] Add `mypy` for static type checking
- [ ] Add `flake8` for linting
- [ ] Increase test coverage to >90%
- [ ] Add integration tests (end-to-end CLI tests)
- [ ] Add benchmark tests (performance regression detection)

#### Documentation
- [ ] Add API documentation (Sphinx/MkDocs)
- [ ] Add video tutorials
- [ ] Add architecture diagrams (mermaid/graphviz)
- [ ] Expand agent development guide with more examples
- [ ] Create FAQ document

#### Infrastructure
- [ ] Docker images for easy deployment
- [ ] Kubernetes manifests for production deployment
- [ ] Homebrew formula for macOS installation
- [ ] APT/YUM packages for Linux
- [ ] Ansible playbooks for deployment

---

## Version Timeline

### v0.3.0 (Released) ✅
- Modular architecture
- Testing infrastructure
- Plugin system
- Configuration profiles

### v0.4.0 (Q2 2025) 🎯
**Theme: Intelligence & Integration**
- Multi-agent coordination
- Project context indexing
- Tool interfaces
- API layer
- Open-WebUI integration
- Security & authentication

### v0.5.0 (Q3 2025)
**Theme: User Experience & Polish**
- Rich terminal interface
- Conversation branching
- Plugin registry
- Performance optimizations
- Enhanced documentation

### v1.0.0 (Q4 2025)
**Theme: Production Ready**
- Stable APIs
- Comprehensive documentation
- Enterprise features (SSO, LDAP)
- Cloud deployment guides
- Professional support options

---

## How to Contribute

See [docs/Contributing.md](./docs/Contributing.md) for development workflow and coding standards.

**Priority areas for v0.4.0 contributions:**
1. Multi-agent coordination
2. Project context indexing
3. Tool interface implementation
4. API layer development
5. Security features

**Get involved:**
- Check [GitHub Issues](https://git.blakbox.vip/AI-Labs/nora/issues) for open tasks
- Join discussions on architecture decisions
- Submit PRs for planned features
- Write documentation and tutorials
- Report bugs and suggest improvements

---

## Research & Exploration

Areas for future investigation:
- **Long-term memory**: Persistent context across sessions
- **Agent learning**: Fine-tuning agents on user feedback
- **Voice interface**: Speech-to-text and text-to-speech
- **Collaborative editing**: Real-time multi-user editing
- **IDE integration**: VSCode, IntelliJ, Vim plugins
- **Mobile clients**: iOS and Android apps

---

**Last Updated:** 2025-10-06
**Current Version:** v0.3.0
**Next Release:** v0.4.0 (Q2 2025)

For architectural details, see [docs/Overview.md](./docs/Overview.md).
For contribution guidelines, see [docs/Contributing.md](./docs/Contributing.md).
