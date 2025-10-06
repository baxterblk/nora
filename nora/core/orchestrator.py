"""
NORA Multi-Agent Orchestrator

Coordinates execution of multiple agents with shared memory and message passing.
Supports both sequential and parallel execution modes.
"""

import logging
import threading
import queue
import time
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class SharedMemory:
    """
    Thread-safe shared memory store for agent communication.

    Provides key-value storage with atomic operations and message passing.
    """

    def __init__(self):
        """Initialize shared memory with thread lock."""
        self._store: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._message_queue: queue.Queue = queue.Queue()
        logger.debug("SharedMemory initialized")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from shared memory.

        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist

        Returns:
            Value or default
        """
        with self._lock:
            return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a value in shared memory.

        Args:
            key: Key to set
            value: Value to store
        """
        with self._lock:
            self._store[key] = value
            logger.debug(f"SharedMemory: Set {key} = {value}")

    def update(self, updates: Dict[str, Any]) -> None:
        """
        Update multiple keys atomically.

        Args:
            updates: Dictionary of key-value pairs to update
        """
        with self._lock:
            self._store.update(updates)
            logger.debug(f"SharedMemory: Updated {len(updates)} keys")

    def get_all(self) -> Dict[str, Any]:
        """
        Get a copy of all shared memory.

        Returns:
            Dictionary of all key-value pairs
        """
        with self._lock:
            return self._store.copy()

    def post_message(self, sender: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Post a message for other agents to consume.

        Args:
            sender: Agent name sending the message
            message: Message content
            data: Optional data payload
        """
        msg = {
            "sender": sender,
            "message": message,
            "data": data or {},
            "timestamp": time.time()
        }
        self._message_queue.put(msg)
        logger.debug(f"Message posted by {sender}: {message}")

    def get_messages(self, timeout: float = 0.1) -> List[Dict[str, Any]]:
        """
        Get all pending messages.

        Args:
            timeout: Timeout in seconds for queue.get()

        Returns:
            List of message dictionaries
        """
        messages = []
        try:
            while True:
                msg = self._message_queue.get(timeout=timeout)
                messages.append(msg)
        except queue.Empty:
            pass
        return messages


class AgentTask:
    """
    Represents a single agent task in the orchestration.
    """

    def __init__(
        self,
        agent_name: str,
        agent_instance: Any,
        model: str,
        depends_on: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an agent task.

        Args:
            agent_name: Name of the agent
            agent_instance: Agent instance or plugin dict
            model: Model to use for this agent
            depends_on: List of agent names this task depends on
            config: Optional agent-specific configuration
        """
        self.agent_name = agent_name
        self.agent_instance = agent_instance
        self.model = model
        self.depends_on = depends_on or []
        self.config = config or {}
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[Exception] = None
        self.completed = False

    def __repr__(self):
        return f"AgentTask(agent={self.agent_name}, depends_on={self.depends_on}, completed={self.completed})"


class Orchestrator:
    """
    Multi-agent orchestrator with support for sequential and parallel execution.
    """

    def __init__(
        self,
        model: str,
        call_fn: Callable,
        max_workers: int = 4
    ):
        """
        Initialize the orchestrator.

        Args:
            model: Default model to use for agents
            call_fn: Ollama chat function
            max_workers: Maximum parallel workers
        """
        self.model = model
        self.call_fn = call_fn
        self.max_workers = max_workers
        self.shared_memory = SharedMemory()
        logger.info(f"Orchestrator initialized with max_workers={max_workers}")

    def run_sequential(self, tasks: List[AgentTask]) -> Dict[str, Any]:
        """
        Run agents sequentially in order.

        Args:
            tasks: List of agent tasks

        Returns:
            Results dictionary with agent outputs
        """
        logger.info(f"Running {len(tasks)} agents sequentially")
        results = {}

        for task in tasks:
            logger.info(f"Executing agent: {task.agent_name}")

            try:
                # Prepare context with shared memory
                context = self.shared_memory.get_all()
                context.update({"agent_name": task.agent_name, "config": task.config})

                # Execute agent
                result = self._execute_agent(task, context)

                # Store result
                task.result = result
                task.completed = True
                results[task.agent_name] = result

                # Check if agent failed (for legacy agents that return error dict)
                if result.get("success") is False and "error" in result:
                    task.error = result["error"]
                    logger.error(f"Agent {task.agent_name} failed: {result['error']}")
                else:
                    logger.info(f"Agent {task.agent_name} completed successfully")

                # Update shared memory with context updates
                if "context_updates" in result:
                    self.shared_memory.update(result["context_updates"])

            except Exception as e:
                logger.error(f"Agent {task.agent_name} failed: {e}", exc_info=True)
                task.error = str(e)
                task.completed = True
                results[task.agent_name] = {"success": False, "error": str(e)}

        return results

    def run_parallel(self, tasks: List[AgentTask]) -> Dict[str, Any]:
        """
        Run agents in parallel with dependency resolution.

        Args:
            tasks: List of agent tasks

        Returns:
            Results dictionary with agent outputs
        """
        logger.info(f"Running {len(tasks)} agents in parallel")
        results = {}
        pending_tasks = {task.agent_name: task for task in tasks}
        completed = set()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while pending_tasks:
                # Find tasks ready to run (dependencies satisfied)
                ready_tasks = [
                    task for task in pending_tasks.values()
                    if all(dep in completed for dep in task.depends_on)
                ]

                if not ready_tasks:
                    logger.error("Deadlock detected: No tasks ready to run")
                    break

                # Submit ready tasks
                futures = {}
                for task in ready_tasks:
                    future = executor.submit(self._run_task_parallel, task)
                    futures[future] = task
                    del pending_tasks[task.agent_name]

                # Wait for completion
                for future in as_completed(futures):
                    task = futures[future]
                    try:
                        result = future.result()
                        results[task.agent_name] = result
                        completed.add(task.agent_name)
                        logger.info(f"Agent {task.agent_name} completed")
                    except Exception as e:
                        logger.error(f"Agent {task.agent_name} failed: {e}")
                        results[task.agent_name] = {"success": False, "error": str(e)}
                        completed.add(task.agent_name)

        return results

    def _run_task_parallel(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute a single task (called in thread pool).

        Args:
            task: Agent task to execute

        Returns:
            Result dictionary
        """
        try:
            # Prepare context
            context = self.shared_memory.get_all()
            context.update({"agent_name": task.agent_name, "config": task.config})

            # Execute agent
            result = self._execute_agent(task, context)

            # Update shared memory
            if "context_updates" in result:
                self.shared_memory.update(result["context_updates"])

            task.result = result
            task.completed = True
            return result

        except Exception as e:
            task.error = e
            task.completed = True
            raise

    def _execute_agent(self, task: AgentTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an agent with given context.

        Args:
            task: Agent task
            context: Execution context

        Returns:
            Result dictionary

        Raises:
            Exception: If agent execution fails
        """
        agent = task.agent_instance

        # Check if class-based agent (v0.4.0+)
        if isinstance(agent, dict) and agent.get("type") == "class-based-agent":
            instance = agent["instance"]

            # Call lifecycle hooks
            instance.on_start(context)

            try:
                result = instance.run(
                    context=context,
                    model=task.model,
                    call_fn=self.call_fn,
                    tools=None  # TODO: Pass tools when tool system is ready
                )
                instance.on_complete(result, context)
                return result

            except Exception as e:
                instance.on_error(e, context)
                raise

        # Legacy function-based agent
        elif isinstance(agent, dict) and "run" in agent:
            # Legacy agents don't return structured results
            # Wrap in try/except and return success/failure
            try:
                agent["run"](task.model, self.call_fn)
                return {"success": True, "output": "Legacy agent completed"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        else:
            raise ValueError(f"Invalid agent type: {type(agent)}")


def load_team_config(config_path: str) -> Dict[str, Any]:
    """
    Load a team configuration from YAML file.

    Args:
        config_path: Path to team config YAML

    Returns:
        Team configuration dictionary

    Example config format:
        name: code-review-team
        mode: sequential  # or parallel
        model: deepseek-coder:6.7b
        agents:
          - name: analyzer
            agent: code_analyzer
            config:
              depth: 3
          - name: reviewer
            agent: code_reviewer
            depends_on: [analyzer]
          - name: tester
            agent: test_generator
            depends_on: [reviewer]
    """
    import yaml
    import pathlib

    path = pathlib.Path(config_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Team config not found: {config_path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    # Validate required keys
    required = ["name", "mode", "agents"]
    for key in required:
        if key not in config:
            raise ValueError(f"Team config missing required key: {key}")

    # Validate mode
    if config["mode"] not in ["sequential", "parallel"]:
        raise ValueError(f"Invalid mode: {config['mode']}")

    logger.info(f"Loaded team config: {config['name']}")
    return config
