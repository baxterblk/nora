"""
Tests for NORA REST API Server

Tests FastAPI endpoints with mocked dependencies.
Requires: pytest-asyncio, httpx
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

# Check if FastAPI is available
try:
    from fastapi.testclient import TestClient
    from nora.api.server import NoraAPIServer
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    pytest.skip("FastAPI not installed", allow_module_level=True)


@pytest.fixture
def mock_config():
    """Mock ConfigManager for testing."""
    config = Mock()
    config.get_model.return_value = "test-model"
    config.get_ollama_url.return_value = "http://localhost:11434"
    config.config = {
        "model": "test-model",
        "ollama": {"url": "http://localhost:11434", "verify_ssl": False}
    }
    return config


@pytest.fixture
def mock_plugins():
    """Mock plugin data for testing."""
    return {
        "test-agent": {
            "name": "test-agent",
            "description": "Test agent",
            "version": "1.0.0",
            "type": "legacy-function",
            "run": Mock()
        },
        "class-agent": {
            "name": "class-agent",
            "description": "Class-based agent",
            "version": "1.0.0",
            "type": "class-based-agent",
            "instance": Mock()
        }
    }


@pytest.fixture
def api_server(mock_config, mock_plugins):
    """Create API server with mocked dependencies."""
    with patch('nora.api.server.PluginLoader') as MockPluginLoader, \
         patch('nora.api.server.ProjectIndexer') as MockIndexer, \
         patch('nora.api.server.OllamaChat') as MockChat:

        # Setup mock plugin loader
        mock_loader = MockPluginLoader.return_value
        mock_loader.load_plugins.return_value = mock_plugins

        # Setup mock indexer
        mock_indexer = MockIndexer.return_value

        # Setup mock chat client
        mock_chat = MockChat.return_value

        server = NoraAPIServer(config=mock_config)
        server.plugins = mock_plugins

        yield server


@pytest.fixture
def client(api_server):
    """Create TestClient for API testing."""
    return TestClient(api_server.app)


class TestAPIRoot:
    """Tests for root endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "NORA API"
        assert data["version"] == "0.4.0"
        assert "endpoints" in data
        assert isinstance(data["endpoints"], list)


class TestChatEndpoint:
    """Tests for /chat endpoint."""

    def test_chat_endpoint_success(self, client):
        """Test successful chat request."""
        request_data = {
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "model": "test-model",
            "stream": False
        }

        response = client.post("/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "response" in data
        assert data["model"] == "test-model"

    def test_chat_endpoint_default_model(self, client):
        """Test chat with default model."""
        request_data = {
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "stream": False
        }

        response = client.post("/chat", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Should use default model from config
        assert data["model"] == "test-model"

    def test_chat_endpoint_invalid_request(self, client):
        """Test chat with invalid request."""
        response = client.post("/chat", json={})

        # Should return validation error
        assert response.status_code == 422


class TestAgentsEndpoints:
    """Tests for /agents endpoints."""

    def test_list_agents(self, client):
        """Test listing all agents."""
        response = client.get("/agents")

        assert response.status_code == 200
        data = response.json()

        assert "agents" in data
        assert isinstance(data["agents"], list)
        assert len(data["agents"]) == 2

        # Check agent data structure
        agent = data["agents"][0]
        assert "name" in agent
        assert "description" in agent
        assert "version" in agent
        assert "type" in agent

    def test_run_agent_success(self, client, mock_plugins):
        """Test running an agent successfully."""
        # Mock the plugin loader's run_plugin method
        with patch.object(client.app.state, 'plugin_loader', create=True) as mock_loader:
            mock_loader.run_plugin.return_value = True

            # Make API request - note the corrected endpoint format
            request_data = {
                "agent_name": "test-agent",
                "model": "test-model"
            }

            response = client.post("/agents/test-agent", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert data["agent_name"] == "test-agent"
            assert data["success"] is True

    def test_run_agent_not_found(self, client):
        """Test running non-existent agent."""
        request_data = {
            "agent_name": "nonexistent",
            "model": "test-model"
        }

        response = client.post("/agents/nonexistent", json=request_data)

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_run_agent_failure(self, client):
        """Test agent execution failure."""
        with patch.object(client.app.state, 'plugin_loader', create=True) as mock_loader:
            mock_loader.run_plugin.return_value = False

            request_data = {
                "agent_name": "test-agent",
                "model": "test-model"
            }

            response = client.post("/agents/test-agent", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False


class TestProjectsEndpoints:
    """Tests for /projects endpoints."""

    def test_index_project_success(self, client, tmp_path):
        """Test indexing a project."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        # Create a dummy file
        (project_dir / "test.py").write_text("print('hello')")

        request_data = {
            "project_path": str(project_dir),
            "project_name": "test-project"
        }

        with patch('nora.api.server.ProjectIndexer') as MockIndexer:
            mock_indexer = MockIndexer.return_value
            mock_indexer.index_project.return_value = {
                "project_name": "test-project",
                "total_files": 1,
                "total_size": 100,
                "files": []
            }

            response = client.post("/projects/index", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert data["project_name"] == "test-project"
            assert data["total_files"] == 1
            assert data["total_size"] == 100

    def test_index_project_nonexistent_path(self, client):
        """Test indexing non-existent project."""
        request_data = {
            "project_path": "/nonexistent/path"
        }

        with patch('nora.api.server.ProjectIndexer') as MockIndexer:
            mock_indexer = MockIndexer.return_value
            mock_indexer.index_project.side_effect = FileNotFoundError("Path not found")

            response = client.post("/projects/index", json=request_data)

            assert response.status_code == 500

    def test_search_index_success(self, client):
        """Test searching the index."""
        request_data = {
            "query": "test",
            "max_results": 10
        }

        with patch('nora.api.server.ProjectIndexer') as MockIndexer:
            mock_indexer = MockIndexer.return_value
            mock_indexer.search.return_value = [
                {
                    "relative_path": "test.py",
                    "relevance_score": 10,
                    "content_preview": "print('test')"
                }
            ]

            response = client.post("/projects/search", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert data["query"] == "test"
            assert len(data["results"]) == 1
            assert data["results"][0]["relative_path"] == "test.py"

    def test_search_index_no_results(self, client):
        """Test search with no results."""
        request_data = {
            "query": "nonexistent"
        }

        with patch('nora.api.server.ProjectIndexer') as MockIndexer:
            mock_indexer = MockIndexer.return_value
            mock_indexer.search.return_value = []

            response = client.post("/projects/search", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert data["query"] == "nonexistent"
            assert len(data["results"]) == 0


class TestTeamEndpoint:
    """Tests for /team endpoint."""

    def test_run_team_success(self, client, tmp_path):
        """Test running a multi-agent team."""
        # Create team config file
        config_file = tmp_path / "team.yaml"
        config_file.write_text("""
name: test-team
mode: sequential
model: test-model
agents:
  - name: agent1
    agent: test-agent
""")

        request_data = {
            "config_path": str(config_file)
        }

        with patch('nora.api.server.load_team_config') as mock_load, \
             patch('nora.api.server.Orchestrator') as MockOrchestrator:

            mock_load.return_value = {
                "name": "test-team",
                "mode": "sequential",
                "model": "test-model",
                "agents": [
                    {"name": "agent1", "agent": "test-agent"}
                ]
            }

            mock_orchestrator = MockOrchestrator.return_value
            mock_orchestrator.run_sequential.return_value = {
                "agent1": {"success": True, "output": "Done"}
            }

            response = client.post("/team", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert data["team_name"] == "test-team"
            assert "results" in data
            assert "agent1" in data["results"]

    def test_run_team_parallel_mode(self, client, tmp_path):
        """Test running team in parallel mode."""
        config_file = tmp_path / "team.yaml"
        config_file.write_text("""
name: parallel-team
mode: parallel
agents:
  - name: agent1
    agent: test-agent
  - name: agent2
    agent: test-agent
""")

        request_data = {
            "config_path": str(config_file)
        }

        with patch('nora.api.server.load_team_config') as mock_load, \
             patch('nora.api.server.Orchestrator') as MockOrchestrator:

            mock_load.return_value = {
                "name": "parallel-team",
                "mode": "parallel",
                "agents": [
                    {"name": "agent1", "agent": "test-agent"},
                    {"name": "agent2", "agent": "test-agent"}
                ]
            }

            mock_orchestrator = MockOrchestrator.return_value
            mock_orchestrator.run_parallel.return_value = {
                "agent1": {"success": True},
                "agent2": {"success": True}
            }

            response = client.post("/team", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert len(data["results"]) == 2

    def test_run_team_invalid_config(self, client):
        """Test running team with invalid config."""
        request_data = {
            "config_path": "/nonexistent/team.yaml"
        }

        with patch('nora.api.server.load_team_config') as mock_load:
            mock_load.side_effect = FileNotFoundError("Config not found")

            response = client.post("/team", json=request_data)

            assert response.status_code == 500

    def test_run_team_mode_override(self, client, tmp_path):
        """Test running team with mode override."""
        config_file = tmp_path / "team.yaml"
        config_file.write_text("""
name: test-team
mode: sequential
agents:
  - name: agent1
    agent: test-agent
""")

        request_data = {
            "config_path": str(config_file),
            "mode": "parallel"  # Override to parallel
        }

        with patch('nora.api.server.load_team_config') as mock_load, \
             patch('nora.api.server.Orchestrator') as MockOrchestrator:

            mock_load.return_value = {
                "name": "test-team",
                "mode": "sequential",
                "agents": [{"name": "agent1", "agent": "test-agent"}]
            }

            mock_orchestrator = MockOrchestrator.return_value
            mock_orchestrator.run_parallel.return_value = {"agent1": {"success": True}}

            response = client.post("/team", json=request_data)

            # Should call run_parallel instead of run_sequential
            mock_orchestrator.run_parallel.assert_called_once()


class TestAPIRequestValidation:
    """Tests for request validation."""

    def test_chat_missing_messages(self, client):
        """Test chat request without messages."""
        response = client.post("/chat", json={"model": "test-model"})

        assert response.status_code == 422

    def test_agent_invalid_json(self, client):
        """Test agent request with invalid JSON."""
        response = client.post(
            "/agents/test-agent",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_index_missing_path(self, client):
        """Test index request without path."""
        response = client.post("/projects/index", json={})

        assert response.status_code == 422

    def test_search_missing_query(self, client):
        """Test search request without query."""
        response = client.post("/projects/search", json={})

        assert response.status_code == 422


class TestAPIErrorHandling:
    """Tests for error handling."""

    def test_chat_internal_error(self, client):
        """Test chat endpoint with internal error."""
        request_data = {
            "messages": [{"role": "user", "content": "test"}]
        }

        with patch('nora.api.server.OllamaChat') as MockChat:
            mock_chat = MockChat.return_value
            mock_chat.chat.side_effect = Exception("Internal error")

            response = client.post("/chat", json=request_data)

            assert response.status_code == 500

    def test_index_permission_error(self, client):
        """Test index endpoint with permission error."""
        request_data = {
            "project_path": "/restricted/path"
        }

        with patch('nora.api.server.ProjectIndexer') as MockIndexer:
            mock_indexer = MockIndexer.return_value
            mock_indexer.index_project.side_effect = PermissionError("Permission denied")

            response = client.post("/projects/index", json=request_data)

            assert response.status_code == 500


class TestAPIServerCreation:
    """Tests for API server creation and initialization."""

    def test_create_server(self, mock_config):
        """Test server creation."""
        from nora.api.server import create_server

        with patch('nora.api.server.PluginLoader'), \
             patch('nora.api.server.ProjectIndexer'), \
             patch('nora.api.server.OllamaChat'):

            server = create_server(mock_config, host="127.0.0.1", port=9000)

            assert server.host == "127.0.0.1"
            assert server.port == 9000

    def test_server_without_fastapi(self, mock_config):
        """Test server creation without FastAPI installed."""
        with patch('nora.api.server.FASTAPI_AVAILABLE', False):
            from nora.api.server import NoraAPIServer

            with pytest.raises(ImportError, match="FastAPI not installed"):
                NoraAPIServer(config=mock_config)
