# Changelog

All notable changes to NORA will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2025-10-06

### Added

#### Multi-Agent Orchestration
- **Orchestrator**: Coordinate multiple AI agents with sequential or parallel execution modes
- **SharedMemory**: Thread-safe shared context for agent communication with message passing
- **AgentTask**: Task definition system with dependency resolution for parallel workflows
- **Team Configuration**: YAML-based team definitions with agent dependencies and config
- **CLI Commands**: `nora agent --team <config.yaml>` for multi-agent workflows

#### Project Context Indexing
- **ProjectIndexer**: Recursive directory scanning with language detection (20+ languages)
- **Smart Search**: Keyword search with relevance scoring across code, functions, and imports
- **Metadata Extraction**: Automatic function/class detection for Python, JS, TS, Go, Rust, and more
- **Persistent Index**: Save/load indexes to `~/.nora/index.json`
- **CLI Commands**: `nora project index <path>` and `nora project search <query>`

#### Extended Plugin Framework
- **Agent Base Class**: Abstract base class with lifecycle hooks (`on_start`, `on_complete`, `on_error`)
- **Tool Base Class**: Abstract interface for reusable tools with parameter schemas
- **Context-Aware Agents**: Agents receive shared context and can update it via `context_updates`
- **Backward Compatibility**: Legacy function-based plugins still supported

#### REST API Layer
- **FastAPI Server**: Production-ready API with Pydantic validation
- **6 Endpoints**:
  - `GET /` - API info and version
  - `POST /chat` - Interactive chat with streaming
  - `GET /agents` - List available agents
  - `POST /agents/{name}` - Execute agent by name
  - `POST /projects/index` - Index project directory
  - `POST /projects/search` - Search indexed projects
  - `POST /team` - Execute multi-agent team from config
- **CLI Command**: `nora serve` to start API server on port 8001

### Testing

- **Test Coverage**: 95% test pass rate (107/113 tests passing)
- **Module Coverage**: 87% orchestrator, 92% indexer, 85% API
- **New Test Suites**:
  - `tests/test_orchestrator.py` (37 tests, 630 lines)
  - `tests/test_indexer.py` (44 tests, 579 lines)
  - `tests/test_api.py` (32 tests, 539 lines)
- **Test Infrastructure**: pytest-asyncio for async tests, httpx TestClient for API testing
- **CI/CD**: GitHub Actions testing across Python 3.8-3.12 on Ubuntu and macOS

### Documentation

- **Updated Guides**:
  - `docs/Overview.md`: v0.4.0 architecture diagrams, new component documentation
  - `docs/Teams.md`: Comprehensive multi-agent teams guide with examples (700+ lines)
- **Remaining Docs**: API.md, Testing.md, and Agents.md updates planned for v0.4.1

### Dependencies

- **New Required**: None (orchestrator and indexer use stdlib only)
- **New Optional**:
  - `fastapi>=0.100.0`, `uvicorn>=0.23.0`, `pydantic>=2.0.0` for `[api]` extra
  - `pytest-asyncio>=0.21.0`, `httpx>=0.24.0` for `[dev]` extra

### Upgrade Notes

#### For End Users

1. **New Commands Available**:
   ```bash
   # Multi-agent teams
   nora agent --team my-team-config.yaml

   # Project indexing
   nora project index /path/to/project
   nora project search "keyword"

   # REST API server
   nora serve
   ```

2. **Plugin Updates**: Existing plugins continue to work. To use new features (shared context, lifecycle hooks), migrate to class-based agents. See `docs/Agents.md` for migration guide (coming in v0.4.1).

3. **API Access**: Install with `pip install -e ".[api]"` to enable REST API features.

#### For Plugin Developers

1. **Class-Based Agents** (Recommended):
   ```python
   from nora.core import Agent

   class MyAgent(Agent):
       def metadata(self):
           return {"name": "my-agent", "version": "1.0.0"}

       def run(self, context, model, call_fn, tools=None):
           # Access shared context
           data = context.get("key")

           # Return updates
           return {
               "success": True,
               "output": "result",
               "context_updates": {"new_key": "value"}
           }
   ```

2. **Legacy Plugins**: Function-based plugins from v0.3.0 still work without changes.

#### Breaking Changes

- None. All v0.3.0 APIs remain compatible.

---

## [0.3.0] - 2025-09-08

### Added

- Modular core architecture with `nora/core/` package
- Type hints throughout codebase
- Structured logging with file/console handlers
- `nora project new` command for plugin scaffolding
- Comprehensive test suite (>80% coverage)
- CI/CD pipeline with GitHub Actions
- Colored terminal output with `nora.core.utils`

### Changed

- Migrated from monolithic to modular architecture
- Replaced print statements with structured logging
- Enhanced plugin discovery and validation

### Documentation

- Complete rewrite of all documentation
- Added CLAUDE.md for AI assistant context
- Added Contributing.md with development workflow

---

## [0.2.0] - 2025-09-01

### Added

- Configuration management with YAML profiles
- Chat history persistence
- Plugin system with dynamic loading
- Context file injection for code-aware chat

### Changed

- Refactored CLI structure
- Improved error handling

---

## [0.1.0] - 2025-08-25

### Added

- Initial release
- Basic Ollama chat integration
- Interactive REPL
- Configuration file support

---

## Upcoming

### [0.4.1] - Planned

**Focus**: Documentation completion and minor bug fixes

- Complete API.md with endpoint documentation and curl examples
- Complete Testing.md with testing guide and CI/CD flow
- Update Agents.md with Agent/Tool base class migration guide
- Fix 6 minor test assertion issues
- Performance optimizations for large project indexing

See [ROADMAP.md](ROADMAP.md) for long-term plans.
