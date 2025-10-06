# NORA Testing Guide

## Overview

NORA uses pytest for comprehensive testing with >90% code coverage. The test suite includes unit tests, integration tests, async tests, and mocked external dependencies.

**Test Framework**: pytest 7.0+
**Coverage Tool**: pytest-cov 4.0+
**Async Testing**: pytest-asyncio 0.21+
**HTTP Testing**: httpx 0.24+ (for FastAPI)

## Quick Start

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage report
pytest --cov=nora --cov-report=term-missing

# Run specific test file
pytest tests/test_config.py

# Run specific test function
pytest tests/test_config.py::TestConfigManager::test_get_set

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_orchestrator"
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py           # Shared fixtures
├── test_config.py        # ConfigManager tests (14 tests)
├── test_history.py       # HistoryManager tests (9 tests)
├── test_plugins.py       # PluginLoader tests (17 tests)
├── test_orchestrator.py  # Orchestrator tests (37 tests)
├── test_indexer.py       # ProjectIndexer tests (44 tests)
└── test_api.py           # FastAPI tests (32 tests)
```

**Total**: 153 tests, 95%+ pass rate, 87-92% coverage on new modules.

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output and stop on first failure
pytest -v -x

# Run only failed tests from last run
pytest --lf

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Show test durations
pytest --durations=10
```

### Coverage Reports

```bash
# Terminal report with missing lines
pytest --cov=nora --cov-report=term-missing

# HTML report (open htmlcov/index.html)
pytest --cov=nora --cov-report=html

# XML report (for CI tools)
pytest --cov=nora --cov-report=xml

# Combined report
pytest --cov=nora --cov-report=term-missing --cov-report=html
```

### Filtering Tests

```bash
# Run specific module tests
pytest tests/test_orchestrator.py

# Run specific test class
pytest tests/test_config.py::TestConfigManager

# Run specific test method
pytest tests/test_config.py::TestConfigManager::test_get_set

# Run tests matching keyword
pytest -k "sequential"  # Matches test names containing "sequential"

# Run tests by marker
pytest -m asyncio  # Run only async tests
```

### Debugging Tests

```bash
# Show print statements
pytest -s

# Drop into debugger on failure
pytest --pdb

# Show local variables on failure
pytest -l

# Verbose output with full diff
pytest -vv
```

## Test Organization

### Core Module Tests

#### 1. test_config.py - Configuration Management

Tests `nora/core/config.py` (ConfigManager):

```python
class TestConfigManager:
    def test_get_set(self, temp_config_dir):
        """Test getting and setting configuration values."""
        config = ConfigManager(config_dir=temp_config_dir)
        config.set("model", "llama3.2:3b")
        assert config.get("model") == "llama3.2:3b"

    def test_connection(self, temp_config_dir, mock_ollama_success):
        """Test Ollama connection validation."""
        config = ConfigManager(config_dir=temp_config_dir)
        success, message = config.test_connection()
        assert success is True
```

**Key patterns**:
- Uses `tmp_path` fixture for isolated config directories
- Mocks `requests.get()` for Ollama API calls
- Tests profile management and nested config access

#### 2. test_history.py - History Management

Tests `nora/core/history.py` (HistoryManager):

```python
def test_add_message(history_manager, mock_history):
    """Test adding messages to history."""
    history_manager.add_message(mock_history, "user", "Hello")
    assert len(mock_history) == 1
    assert mock_history[0]["role"] == "user"
```

**Key patterns**:
- Uses temporary directories for history files
- Tests windowing (last 10 messages)
- Tests persistence and loading

#### 3. test_plugins.py - Plugin System

Tests `nora/core/plugins.py` (PluginLoader, Agent, Tool):

```python
def test_load_valid_plugin(plugin_loader, temp_plugin_dir):
    """Test loading a valid plugin."""
    # Create plugin file dynamically
    plugin_path = temp_plugin_dir / "test_plugin.py"
    plugin_path.write_text('''
def register():
    return {
        "name": "test_plugin",
        "description": "Test",
        "run": lambda m, c: None
    }
''')

    plugins = plugin_loader.load_plugins()
    assert "test_plugin" in plugins
```

**Key patterns**:
- Creates plugins dynamically in temp directories
- Tests both class-based and function-based plugins
- Tests Agent and Tool abstract base classes

### v0.4.0 Module Tests

#### 4. test_orchestrator.py - Multi-Agent Orchestration

Tests `nora/core/orchestrator.py` (Orchestrator, SharedMemory):

```python
def test_shared_memory_thread_safety(orchestrator):
    """Test thread-safe operations on SharedMemory."""
    import threading

    def writer(key, value):
        orchestrator.shared_memory.set(key, value)

    threads = [
        threading.Thread(target=writer, args=(f"key{i}", i))
        for i in range(100)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify all writes succeeded
    for i in range(100):
        assert orchestrator.shared_memory.get(f"key{i}") == i
```

**Key patterns**:
- Mocks `call_fn` to avoid Ollama calls
- Tests sequential and parallel execution
- Tests dependency resolution and shared memory
- Thread safety tests with concurrent operations

#### 5. test_indexer.py - Project Indexing

Tests `nora/core/indexer.py` (ProjectIndexer):

```python
def test_index_python_file(indexer, temp_project):
    """Test indexing a Python file."""
    # Create test file
    (temp_project / "test.py").write_text('''
def hello():
    """Greet the user."""
    return "Hello"

class Greeter:
    pass
''')

    index_data = indexer.index_project(str(temp_project))

    assert index_data["total_files"] == 1
    file_entry = index_data["files"][0]
    assert file_entry["language"] == "python"
    assert "hello" in file_entry["functions"]
    assert "Greeter" in file_entry["functions"]
```

**Key patterns**:
- Creates temporary project structures
- Tests language detection for 20+ languages
- Tests function/class extraction
- Tests search with relevance scoring
- Edge cases: unicode, deep nesting, binary files

#### 6. test_api.py - REST API

Tests `nora/api/server.py` (FastAPI endpoints):

```python
@pytest.mark.asyncio
async def test_chat_endpoint(api_client, mock_ollama):
    """Test POST /chat endpoint."""
    response = api_client.post(
        "/chat",
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "test-model",
            "stream": False
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["model"] == "test-model"
```

**Key patterns**:
- Uses FastAPI `TestClient` from httpx
- Mocks all external dependencies (Ollama, PluginLoader, ProjectIndexer)
- Tests all 6 endpoints
- Tests error handling and validation

## Writing New Tests

### Test Structure Template

```python
"""
Module: test_myfeature.py
Tests for nora/core/myfeature.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from nora.core.myfeature import MyClass


class TestMyClass:
    """Test suite for MyClass."""

    @pytest.fixture
    def my_instance(self):
        """Create MyClass instance for testing."""
        return MyClass()

    def test_basic_functionality(self, my_instance):
        """Test basic feature."""
        result = my_instance.do_something()
        assert result == expected_value

    def test_error_handling(self, my_instance):
        """Test error conditions."""
        with pytest.raises(ValueError):
            my_instance.do_something(invalid_input)

    @patch('nora.core.myfeature.external_dependency')
    def test_with_mock(self, mock_dep, my_instance):
        """Test with mocked dependency."""
        mock_dep.return_value = "mocked"
        result = my_instance.use_dependency()
        assert result == "mocked"
        mock_dep.assert_called_once()
```

### Test Naming Conventions

- **File naming**: `test_<module_name>.py`
- **Class naming**: `Test<ClassName>`
- **Method naming**: `test_<feature>_<condition>`

Examples:
```python
def test_config_get_default()           # Feature + condition
def test_history_add_message()          # Feature + action
def test_orchestrator_parallel_mode()   # Feature + mode
def test_indexer_empty_project()        # Feature + edge case
def test_api_chat_endpoint_error()      # Endpoint + error case
```

### Fixtures

Use fixtures for reusable test setup:

```python
@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory."""
    return tmp_path

@pytest.fixture
def config_manager(temp_dir):
    """Create ConfigManager with temp directory."""
    return ConfigManager(config_dir=temp_dir)

@pytest.fixture
def mock_ollama():
    """Mock Ollama API responses."""
    with patch('requests.post') as mock:
        mock.return_value.json.return_value = {"response": "test"}
        yield mock
```

### Mocking Strategies

#### Mock External APIs

```python
@patch('requests.get')
def test_with_mock_api(mock_get):
    """Mock HTTP requests."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"status": "ok"}

    # Your test code
    result = make_api_call()
    assert result["status"] == "ok"
    mock_get.assert_called_once()
```

#### Mock File System

```python
def test_with_temp_files(tmp_path):
    """Use pytest's tmp_path fixture."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    # Your test code
    result = process_file(str(test_file))
    assert result is not None
```

#### Mock Ollama Chat

```python
@pytest.fixture
def mock_chat_fn():
    """Mock Ollama chat function."""
    def chat_fn(messages, model=None, stream=False):
        return {"response": "Mocked response"}
    return chat_fn

def test_agent_with_mock_chat(mock_chat_fn):
    """Test agent without calling real Ollama."""
    agent = MyAgent()
    result = agent.run({}, "model", mock_chat_fn)
    assert result["success"] is True
```

## Async Testing

NORA uses pytest-asyncio for testing async code (FastAPI endpoints).

### Basic Async Test

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await my_async_function()
    assert result == expected
```

### FastAPI Testing

```python
from fastapi.testclient import TestClient

@pytest.fixture
def api_client(mock_config, mock_plugins):
    """Create FastAPI test client."""
    from nora.api.server import create_server

    with patch('nora.api.server.PluginLoader') as mock_loader:
        mock_loader.return_value.load_plugins.return_value = mock_plugins

        server = create_server(mock_config)
        client = TestClient(server.app)
        yield client

def test_api_endpoint(api_client):
    """Test API endpoint (not async, but tests async handler)."""
    response = api_client.get("/")
    assert response.status_code == 200
```

**Note**: FastAPI TestClient handles async automatically, so test functions don't need to be async.

### Async Fixtures

```python
@pytest.fixture
async def async_resource():
    """Async fixture for resource."""
    resource = await create_async_resource()
    yield resource
    await resource.cleanup()
```

## CI/CD Integration

### GitHub Actions Workflow

NORA uses GitHub Actions for automated testing. See `.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ["3.8", "3.9", "3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[all]"

    - name: Run tests with pytest
      run: |
        pytest tests/ -v --cov=nora --cov-report=xml --cov-report=term

    - name: Upload coverage
      if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.11'
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        fail_ci_if_error: false
```

**Matrix Testing**:
- Python 3.8, 3.9, 3.10, 3.11, 3.12
- Ubuntu and macOS
- Total: 10 test configurations per commit

**Coverage Reporting**:
- Uploads to Codecov (on ubuntu-latest + Python 3.11)
- XML format for CI tools
- Terminal format for PR comments

### Running Tests Like CI

```bash
# Replicate CI environment
python -m pip install --upgrade pip
pip install -e ".[all]"

# Run tests with same options as CI
pytest tests/ -v --cov=nora --cov-report=xml --cov-report=term

# Check coverage threshold (85%)
pytest --cov=nora --cov-report=term --cov-fail-under=85
```

## Coverage Analysis

### Viewing Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=nora --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

**HTML Report Features**:
- Line-by-line coverage highlighting
- Branch coverage analysis
- Missing line numbers
- Per-module coverage breakdown

### Current Coverage Stats

| Module | Coverage | Lines | Missing |
|--------|----------|-------|---------|
| nora/core/config.py | 92% | 150 | 12 |
| nora/core/history.py | 95% | 80 | 4 |
| nora/core/chat.py | 88% | 120 | 14 |
| nora/core/plugins.py | 90% | 200 | 20 |
| nora/core/utils.py | 85% | 60 | 9 |
| nora/core/orchestrator.py | 87% | 400 | 52 |
| nora/core/indexer.py | 92% | 500 | 40 |
| nora/api/server.py | 85% | 430 | 65 |
| **Overall** | **89%** | **1940** | **216** |

### Improving Coverage

1. **Identify Missing Lines**:
   ```bash
   pytest --cov=nora --cov-report=term-missing | grep "TOTAL"
   ```

2. **Focus on Specific Module**:
   ```bash
   pytest tests/test_indexer.py --cov=nora/core/indexer.py --cov-report=term-missing
   ```

3. **Add Tests for Edge Cases**:
   - Error conditions
   - Boundary values
   - Exception handling
   - Concurrent operations

## Test Performance

### Profiling Test Suite

```bash
# Show 10 slowest tests
pytest --durations=10

# Show all durations
pytest --durations=0

# Profile test execution
pytest --profile
```

### Optimization Tips

1. **Use Fixtures for Expensive Setup**:
   ```python
   @pytest.fixture(scope="module")  # Reuse across module
   def expensive_resource():
       return load_large_dataset()
   ```

2. **Mock External Dependencies**:
   - Don't call real Ollama API
   - Don't make real HTTP requests
   - Use temp directories for files

3. **Parallel Execution**:
   ```bash
   pip install pytest-xdist
   pytest -n auto  # Use all CPU cores
   ```

### Benchmark Results

Current test suite performance (on Intel i7, 16GB RAM):

| Test Suite | Tests | Duration | Notes |
|------------|-------|----------|-------|
| test_config.py | 14 | 0.3s | Fast (mocked) |
| test_history.py | 9 | 0.2s | Fast (temp files) |
| test_plugins.py | 17 | 0.5s | Dynamic plugin creation |
| test_orchestrator.py | 37 | 1.2s | Thread safety tests |
| test_indexer.py | 44 | 2.1s | File I/O heavy |
| test_api.py | 32 | 0.8s | FastAPI TestClient |
| **Total** | **153** | **~5s** | Serial execution |

With parallel execution (`-n auto`): ~2 seconds on 4 cores.

## Troubleshooting

### Common Test Failures

#### 1. Import Errors

```bash
# Error: ModuleNotFoundError: No module named 'nora'
# Solution: Install in editable mode
pip install -e .
```

#### 2. Fixture Not Found

```bash
# Error: fixture 'my_fixture' not found
# Solution: Check conftest.py or fixture scope
pytest tests/test_myfile.py -v
```

#### 3. Async Test Not Running

```bash
# Error: Test function is async but not marked with @pytest.mark.asyncio
# Solution: Add marker
@pytest.mark.asyncio
async def test_my_async_function():
    ...
```

#### 4. Coverage Not Updating

```bash
# Solution: Clear .coverage file
rm .coverage
pytest --cov=nora
```

### Debug Test Failures

```bash
# Show full output
pytest -s -v

# Drop into pdb debugger
pytest --pdb

# Show local variables
pytest -l

# Rerun only failed tests
pytest --lf

# Stop on first failure
pytest -x
```

## Best Practices

### 1. Test Independence

Each test should run independently:

```python
# GOOD: Uses fixture for isolation
def test_with_fixture(temp_dir):
    config = ConfigManager(config_dir=temp_dir)
    # Test code

# BAD: Relies on global state
def test_with_global():
    config = ConfigManager()  # Uses shared ~/.nora/
    # Test code
```

### 2. Descriptive Test Names

```python
# GOOD: Clear intent
def test_config_get_returns_default_when_key_missing():
    ...

# BAD: Unclear
def test_1():
    ...
```

### 3. One Assertion Per Test (When Possible)

```python
# GOOD: Focused test
def test_get_returns_value():
    assert config.get("key") == "value"

def test_get_returns_default():
    assert config.get("missing") is None

# ACCEPTABLE: Related assertions
def test_agent_execution():
    result = agent.run()
    assert result["success"] is True
    assert "output" in result
```

### 4. Mock External Dependencies

```python
# GOOD: Mock Ollama
@patch('requests.post')
def test_chat(mock_post):
    mock_post.return_value.json.return_value = {"response": "test"}
    # Test code

# BAD: Real API call
def test_chat_real():
    response = requests.post("http://localhost:11434/api/chat", ...)
    # Fails if Ollama not running
```

### 5. Use Fixtures for Setup

```python
# GOOD: Reusable fixture
@pytest.fixture
def config():
    return ConfigManager(config_dir="/tmp/test")

def test_with_fixture(config):
    assert config.get("key") is not None

# BAD: Repeated setup
def test_1():
    config = ConfigManager(config_dir="/tmp/test")
    ...

def test_2():
    config = ConfigManager(config_dir="/tmp/test")
    ...
```

## Continuous Integration

### Pre-Commit Checks

```bash
# Run tests before committing
pytest

# Check coverage threshold
pytest --cov=nora --cov-fail-under=85

# Run linting (optional)
black --check nora tests
isort --check-only nora tests
mypy nora --ignore-missing-imports
```

### Git Hooks

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
echo "Running tests..."
pytest --cov=nora --cov-fail-under=85
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

```bash
chmod +x .git/hooks/pre-commit
```

## Performance Testing (v0.4.1)

### ProjectIndexer Benchmarks

**Test Setup**: Index NORA codebase (~150 files, ~15,000 lines)

```bash
# Benchmark indexing
python -m timeit -n 5 'from nora.core.indexer import ProjectIndexer; indexer = ProjectIndexer(); indexer.index_project(".")'
```

**Results** (v0.4.0 baseline):
- **Duration**: 2.3 seconds average
- **Files Indexed**: 147
- **Total Size**: 1.2 MB
- **Throughput**: ~64 files/second

**v0.4.1 Optimization** (with file hash caching):
- **Duration**: 0.4 seconds average (5.7x faster on re-index)
- **Cache Hit Rate**: 95% (unchanged files)
- **Throughput**: ~367 files/second

See implementation details in `nora/core/indexer.py:_compute_file_hash()`.

---

## Next Steps

- See [API.md](API.md) for REST API testing examples
- See [Teams.md](Teams.md) for multi-agent orchestration testing
- See [Agents.md](Agents.md) for plugin testing patterns
- Check [Contributing.md](Contributing.md) for development workflow

## Appendix: pytest.ini Configuration

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=nora
    --cov-report=term-missing
    --cov-report=html
markers =
    asyncio: mark test as async (handled by pytest-asyncio)
```

**Configuration Explained**:
- `testpaths`: Look for tests in `tests/` directory
- `python_files`: Test files start with `test_`
- `asyncio_mode = auto`: Auto-detect async tests
- `--strict-markers`: Fail on unknown markers
- `--tb=short`: Short traceback format
- `-v`: Verbose output

## Contact

For testing questions or CI/CD issues, see:
- GitHub Issues: [NORA Issues](https://git.blakbox.vip/AI-Labs/nora/issues)
- Documentation: [Overview.md](Overview.md)
