"""
NORA REST API Server

FastAPI-based REST API exposing NORA functionality via HTTP endpoints.
"""

import logging
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, status
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    HTTPException = None
    BaseModel = None

from nora.core import ConfigManager, PluginLoader, OllamaChat
from nora.core.indexer import ProjectIndexer
from nora.core.orchestrator import Orchestrator, AgentTask, load_team_config

logger = logging.getLogger(__name__)


# Pydantic Models for API

class ChatRequest(BaseModel):
    """Chat request model."""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str
    model: str


class AgentRequest(BaseModel):
    """Agent execution request."""
    agent_name: str
    model: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Agent execution response."""
    agent_name: str
    success: bool
    output: Any
    error: Optional[str] = None


class IndexRequest(BaseModel):
    """Project indexing request."""
    project_path: str
    project_name: Optional[str] = None


class IndexResponse(BaseModel):
    """Project indexing response."""
    project_name: str
    total_files: int
    total_size: int


class SearchRequest(BaseModel):
    """Index search request."""
    query: str
    max_results: int = 10


class SearchResponse(BaseModel):
    """Index search response."""
    query: str
    results: List[Dict[str, Any]]


class TeamRequest(BaseModel):
    """Multi-agent team request."""
    config_path: str
    mode: Optional[str] = None  # Override config mode


class TeamResponse(BaseModel):
    """Multi-agent team response."""
    team_name: str
    results: Dict[str, Any]


# API Server Class

class NoraAPIServer:
    """
    NORA REST API server.

    Provides HTTP endpoints for chat, agents, projects, and tools.
    """

    def __init__(
        self,
        config: ConfigManager,
        host: str = "0.0.0.0",
        port: int = 8001
    ):
        """
        Initialize the API server.

        Args:
            config: NORA configuration manager
            host: Host to bind to
            port: Port to bind to
        """
        if not FASTAPI_AVAILABLE:
            raise ImportError(
                "FastAPI not installed. Install with: pip install 'nora-cli[api]'"
            )

        self.config = config
        self.host = host
        self.port = port

        # Initialize components
        self.plugin_loader = PluginLoader()
        self.plugins = self.plugin_loader.load_plugins()
        self.indexer = ProjectIndexer()
        self.chat_client = OllamaChat(
            base_url=config.get_ollama_url(),
            model=config.get_model()
        )

        # Create FastAPI app
        self.app = FastAPI(
            title="NORA API",
            description="REST API for NORA - No Rush on Anything",
            version="0.4.1-beta",
            lifespan=self.lifespan
        )

        # Register routes
        self._register_routes()

        logger.info(f"NORA API server initialized on {host}:{port}")

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Lifespan context manager for startup/shutdown."""
        logger.info("API server starting up")
        yield
        logger.info("API server shutting down")

    def _register_routes(self):
        """Register all API routes."""

        @self.app.get("/")
        async def root():
            """API root endpoint."""
            return {
                "name": "NORA API",
                "version": "0.4.1-beta",
                "endpoints": [
                    "/chat",
                    "/agents",
                    "/agents/{name}",
                    "/projects/index",
                    "/projects/search",
                    "/team"
                ]
            }

        @self.app.post("/chat", response_model=ChatResponse)
        async def chat(request: ChatRequest):
            """
            Send a chat message to Ollama.

            Args:
                request: Chat request with messages

            Returns:
                Chat response
            """
            try:
                model = request.model or self.config.get_model()

                # For non-streaming, we need to capture the response
                # This is a simplified version - full implementation would
                # handle streaming properly
                self.chat_client.chat(
                    messages=request.messages,
                    model=model,
                    stream=False
                )

                return ChatResponse(
                    response="Response captured",  # TODO: Implement proper response capture
                    model=model
                )

            except Exception as e:
                logger.error(f"Chat error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )

        @self.app.get("/agents")
        async def list_agents():
            """
            List all available agents.

            Returns:
                List of agent metadata
            """
            agents = []
            for name, plugin in self.plugins.items():
                agents.append({
                    "name": name,
                    "description": plugin.get("description", ""),
                    "version": plugin.get("version", "unknown"),
                    "type": plugin.get("type", "legacy-function")
                })
            return {"agents": agents}

        @self.app.post("/agents/{agent_name}", response_model=AgentResponse)
        async def run_agent(agent_name: str, request: AgentRequest):
            """
            Run a specific agent.

            Args:
                agent_name: Name of agent to run
                request: Agent execution request

            Returns:
                Agent execution result
            """
            plugin = self.plugins.get(agent_name)
            if not plugin:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Agent not found: {agent_name}"
                )

            try:
                model = request.model or self.config.get_model()

                # Execute agent
                success = self.plugin_loader.run_plugin(
                    name=agent_name,
                    plugins=self.plugins,
                    model=model,
                    chat_fn=self.chat_client.chat
                )

                return AgentResponse(
                    agent_name=agent_name,
                    success=success,
                    output="Agent completed",  # TODO: Capture actual output
                    error=None if success else "Agent execution failed"
                )

            except Exception as e:
                logger.error(f"Agent execution error: {e}", exc_info=True)
                return AgentResponse(
                    agent_name=agent_name,
                    success=False,
                    output=None,
                    error=str(e)
                )

        @self.app.post("/projects/index", response_model=IndexResponse)
        async def index_project(request: IndexRequest):
            """
            Index a project directory.

            Args:
                request: Index request with project path

            Returns:
                Index metadata
            """
            try:
                index_data = self.indexer.index_project(
                    project_path=request.project_path,
                    project_name=request.project_name
                )

                self.indexer.save_index(index_data)

                return IndexResponse(
                    project_name=index_data["project_name"],
                    total_files=index_data["total_files"],
                    total_size=index_data["total_size"]
                )

            except Exception as e:
                logger.error(f"Indexing error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )

        @self.app.post("/projects/search", response_model=SearchResponse)
        async def search_index(request: SearchRequest):
            """
            Search the project index.

            Args:
                request: Search request with query

            Returns:
                Search results
            """
            try:
                results = self.indexer.search(
                    query=request.query,
                    max_results=request.max_results
                )

                return SearchResponse(
                    query=request.query,
                    results=results
                )

            except Exception as e:
                logger.error(f"Search error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )

        @self.app.post("/team", response_model=TeamResponse)
        async def run_team(request: TeamRequest):
            """
            Run a multi-agent team.

            Args:
                request: Team execution request

            Returns:
                Team execution results
            """
            try:
                # Load team config
                team_config = load_team_config(request.config_path)

                # Create orchestrator
                orchestrator = Orchestrator(
                    model=team_config.get("model", self.config.get_model()),
                    call_fn=self.chat_client.chat
                )

                # Build agent tasks
                tasks = []
                for agent_config in team_config["agents"]:
                    agent_name = agent_config["agent"]
                    plugin = self.plugins.get(agent_name)

                    if not plugin:
                        logger.warning(f"Agent not found: {agent_name}")
                        continue

                    task = AgentTask(
                        agent_name=agent_config.get("name", agent_name),
                        agent_instance=plugin,
                        model=team_config.get("model", self.config.get_model()),
                        depends_on=agent_config.get("depends_on", []),
                        config=agent_config.get("config", {})
                    )
                    tasks.append(task)

                # Execute team
                mode = request.mode or team_config["mode"]
                if mode == "sequential":
                    results = orchestrator.run_sequential(tasks)
                else:
                    results = orchestrator.run_parallel(tasks)

                return TeamResponse(
                    team_name=team_config["name"],
                    results=results
                )

            except Exception as e:
                logger.error(f"Team execution error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )

    def run(self):
        """
        Start the API server.

        Runs uvicorn server in blocking mode.
        """
        try:
            import uvicorn
        except ImportError:
            raise ImportError(
                "uvicorn not installed. Install with: pip install 'nora-cli[api]'"
            )

        logger.info(f"Starting NORA API server on http://{self.host}:{self.port}")

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )


def create_server(config: ConfigManager, host: str = "0.0.0.0", port: int = 8001) -> NoraAPIServer:
    """
    Create an API server instance.

    Args:
        config: NORA configuration
        host: Host to bind to
        port: Port to bind to

    Returns:
        NoraAPIServer instance
    """
    return NoraAPIServer(config=config, host=host, port=port)
