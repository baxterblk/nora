# NORA v0.4.1 Milestone

**Focus**: Documentation Completion & Minor Fixes
**Target Release**: 2025-10-20
**Type**: Patch Release

## Overview

Version 0.4.1 is a documentation and bug fix release to complete the v0.4.0 deliverables. No new features will be added; the focus is on completing comprehensive documentation for all v0.4.0 features and addressing minor test failures.

## Tasks

### Documentation (High Priority)

#### 1. Create docs/API.md
**Status**: Not Started
**Assignee**: TBD
**Estimated Effort**: 2-3 hours

Document all 6 FastAPI endpoints with comprehensive examples:

- [ ] `GET /` - API information and version
- [ ] `POST /chat` - Interactive chat endpoint with streaming
- [ ] `GET /agents` - List available agents
- [ ] `POST /agents/{name}` - Execute specific agent
- [ ] `POST /projects/index` - Index project directory
- [ ] `POST /projects/search` - Search indexed projects
- [ ] `POST /team` - Execute multi-agent team

For each endpoint, include:
- Description and purpose
- Request format (JSON schema)
- Response format (JSON schema)
- curl examples with realistic payloads
- Error responses and status codes
- Authentication requirements (if any)

#### 2. Create docs/Testing.md
**Status**: Not Started
**Assignee**: TBD
**Estimated Effort**: 2 hours

Comprehensive testing guide covering:

- [ ] How to run tests locally (`pytest`)
- [ ] Running specific test files/classes/functions
- [ ] Viewing coverage reports (terminal, HTML)
- [ ] CI/CD pipeline explanation (GitHub Actions)
- [ ] Writing new tests (patterns and best practices)
- [ ] Mocking Ollama API in tests
- [ ] Async testing with pytest-asyncio
- [ ] Test fixtures and conftest.py usage

#### 3. Update docs/Agents.md
**Status**: Not Started
**Assignee**: TBD
**Estimated Effort**: 1-2 hours

Add v0.4.0 plugin framework documentation:

- [ ] Agent base class with code examples
- [ ] Tool base class with code examples
- [ ] Migration guide: function-based → class-based
- [ ] Context-aware agents (accessing/updating shared context)
- [ ] Lifecycle hooks (`on_start`, `on_complete`, `on_error`)
- [ ] Using tools within agents
- [ ] Backward compatibility notes

### Bug Fixes (Medium Priority)

#### 4. Fix Test Assertion Issues
**Status**: Not Started
**Assignee**: TBD
**Estimated Effort**: 2-3 hours

Address 6 failing tests (95% → 100% pass rate):

- [ ] `test_run_agent_not_found` - Fix HTTP status code expectation (404 vs 200)
- [ ] `test_run_agent_failure` - Configure mock properly for agent failure
- [ ] `test_index_project_success` - Fix Pydantic validation with mocks
- [ ] `test_search_index_success` - Return actual results from mock
- [ ] `test_chat_internal_error` - Ensure 500 status for internal errors
- [ ] `test_sequential_agent_failure` - Capture error in task.error field

All failures are test-side issues, not code bugs. Fixes should improve test assertions and mocking.

### Performance Optimizations (Low Priority)

#### 5. Optimize Project Indexing for Large Codebases
**Status**: Not Started
**Assignee**: TBD
**Estimated Effort**: 3-4 hours

Enhancements to `nora/core/indexer.py`:

- [ ] Implement incremental indexing (only re-index changed files)
- [ ] Add progress bars for large directory scans
- [ ] Support `.noraignore` file for custom exclusions
- [ ] Cache parsed function/class signatures
- [ ] Add configurable file size limits
- [ ] Benchmark indexing performance on 10K+ file projects

## Success Criteria

- [ ] All documentation tasks completed
- [ ] 100% test pass rate (113/113 tests)
- [ ] No regressions from v0.4.0
- [ ] Updated CHANGELOG.md with v0.4.1 notes
- [ ] Git tag created and pushed

## Out of Scope

The following are explicitly **NOT** included in v0.4.1:

- New features or capabilities
- Breaking changes to APIs
- Major refactoring
- Dependency updates (unless required for bug fixes)

These items are deferred to v0.5.0 or later.

## Release Checklist

- [ ] Complete all documentation tasks
- [ ] Fix all 6 test failures
- [ ] Update CHANGELOG.md with v0.4.1 section
- [ ] Run full test suite: `pytest tests/ -v --cov=nora`
- [ ] Verify coverage ≥85% on all modules
- [ ] Update version in `nora/__init__.py` to `0.4.1`
- [ ] Update version in `pyproject.toml` to `0.4.1`
- [ ] Commit with message: "Release NORA v0.4.1"
- [ ] Create tag: `git tag -a v0.4.1 -m "NORA v0.4.1: Documentation & Fixes"`
- [ ] Push commit and tag: `git push origin main && git push origin v0.4.1`
- [ ] Verify CI pipeline passes on GitHub Actions
- [ ] Announce release (README badge update, etc.)

## Notes

- Documentation is the primary focus of this release
- All test failures are test-side issues, not production bugs
- Performance optimizations are nice-to-have, not blockers
- Aim for release within 2 weeks of v0.4.0 (by 2025-10-20)

## Related Issues

Link any GitHub issues or tasks here:

- [ ] Issue #XXX: Complete API documentation
- [ ] Issue #XXX: Fix test assertion failures
- [ ] Issue #XXX: Add testing guide

## Version History Context

- **v0.4.0** (2025-10-06): Multi-agent orchestration, project indexing, REST API
- **v0.4.1** (Target: 2025-10-20): Documentation completion & bug fixes
- **v0.5.0** (Planned): TBD based on ROADMAP.md Phase 2 goals
