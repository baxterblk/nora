"""
Tests for NORA Multi-Agent Orchestrator

Tests SharedMemory, AgentTask, Orchestrator, and team execution modes.
"""

import pytest
import time
import tempfile
import pathlib
from unittest.mock import Mock, MagicMock
from nora.core.orchestrator import SharedMemory, AgentTask, Orchestrator, load_team_config


class TestSharedMemory:
    """Tests for SharedMemory class."""

    def test_init(self):
        """Test SharedMemory initialization."""
        memory = SharedMemory()
        assert memory.get_all() == {}

    def test_get_set(self):
        """Test basic get/set operations."""
        memory = SharedMemory()

        memory.set("key1", "value1")
        assert memory.get("key1") == "value1"

        memory.set("key2", 42)
        assert memory.get("key2") == 42

    def test_get_default(self):
        """Test get with default value."""
        memory = SharedMemory()
        assert memory.get("nonexistent", "default") == "default"

    def test_update(self):
        """Test atomic update operation."""
        memory = SharedMemory()

        memory.update({
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        })

        assert memory.get("key1") == "value1"
        assert memory.get("key2") == "value2"
        assert memory.get("key3") == "value3"

    def test_get_all(self):
        """Test get_all returns a copy."""
        memory = SharedMemory()
        memory.set("key1", "value1")
        memory.set("key2", "value2")

        all_data = memory.get_all()
        assert all_data == {"key1": "value1", "key2": "value2"}

        # Modify returned dict shouldn't affect memory
        all_data["key3"] = "value3"
        assert memory.get("key3") is None

    def test_post_message(self):
        """Test message posting."""
        memory = SharedMemory()

        memory.post_message("agent1", "Hello from agent1", {"data": "test"})

        messages = memory.get_messages()
        assert len(messages) == 1
        assert messages[0]["sender"] == "agent1"
        assert messages[0]["message"] == "Hello from agent1"
        assert messages[0]["data"]["data"] == "test"
        assert "timestamp" in messages[0]

    def test_get_messages_empty_queue(self):
        """Test get_messages on empty queue."""
        memory = SharedMemory()
        messages = memory.get_messages(timeout=0.01)
        assert messages == []

    def test_multiple_messages(self):
        """Test multiple message posting and retrieval."""
        memory = SharedMemory()

        memory.post_message("agent1", "Message 1")
        memory.post_message("agent2", "Message 2")
        memory.post_message("agent3", "Message 3")

        messages = memory.get_messages()
        assert len(messages) == 3
        assert messages[0]["sender"] == "agent1"
        assert messages[1]["sender"] == "agent2"
        assert messages[2]["sender"] == "agent3"

    def test_thread_safety(self):
        """Test thread-safe operations."""
        import threading

        memory = SharedMemory()
        errors = []

        def worker(worker_id):
            try:
                for i in range(100):
                    memory.set(f"worker_{worker_id}_key_{i}", i)
                    value = memory.get(f"worker_{worker_id}_key_{i}")
                    assert value == i
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestAgentTask:
    """Tests for AgentTask class."""

    def test_init(self):
        """Test AgentTask initialization."""
        agent = Mock()
        task = AgentTask(
            agent_name="test-agent",
            agent_instance=agent,
            model="test-model",
            depends_on=["agent1", "agent2"],
            config={"key": "value"}
        )

        assert task.agent_name == "test-agent"
        assert task.agent_instance == agent
        assert task.model == "test-model"
        assert task.depends_on == ["agent1", "agent2"]
        assert task.config == {"key": "value"}
        assert task.result is None
        assert task.error is None
        assert task.completed is False

    def test_init_defaults(self):
        """Test AgentTask initialization with defaults."""
        agent = Mock()
        task = AgentTask(
            agent_name="test-agent",
            agent_instance=agent,
            model="test-model"
        )

        assert task.depends_on == []
        assert task.config == {}

    def test_repr(self):
        """Test AgentTask string representation."""
        agent = Mock()
        task = AgentTask(
            agent_name="test-agent",
            agent_instance=agent,
            model="test-model",
            depends_on=["dep1"]
        )

        repr_str = repr(task)
        assert "test-agent" in repr_str
        assert "dep1" in repr_str
        assert "completed=False" in repr_str


class TestOrchestrator:
    """Tests for Orchestrator class."""

    def test_init(self):
        """Test Orchestrator initialization."""
        call_fn = Mock()
        orchestrator = Orchestrator(
            model="test-model",
            call_fn=call_fn,
            max_workers=4
        )

        assert orchestrator.model == "test-model"
        assert orchestrator.call_fn == call_fn
        assert orchestrator.max_workers == 4
        assert isinstance(orchestrator.shared_memory, SharedMemory)

    def test_sequential_single_agent(self):
        """Test sequential execution with single agent."""
        call_fn = Mock()
        orchestrator = Orchestrator(model="test-model", call_fn=call_fn)

        # Mock agent (legacy function-based)
        agent = {
            "name": "test-agent",
            "type": "legacy-function",
            "run": Mock()
        }

        task = AgentTask(
            agent_name="test-agent",
            agent_instance=agent,
            model="test-model"
        )

        results = orchestrator.run_sequential([task])

        assert "test-agent" in results
        assert results["test-agent"]["success"] is True
        assert task.completed is True

    def test_sequential_multiple_agents(self):
        """Test sequential execution with multiple agents."""
        call_fn = Mock()
        orchestrator = Orchestrator(model="test-model", call_fn=call_fn)

        # Create three mock agents
        agents = []
        tasks = []
        for i in range(3):
            agent = {
                "name": f"agent-{i}",
                "type": "legacy-function",
                "run": Mock()
            }
            agents.append(agent)

            task = AgentTask(
                agent_name=f"agent-{i}",
                agent_instance=agent,
                model="test-model"
            )
            tasks.append(task)

        results = orchestrator.run_sequential(tasks)

        assert len(results) == 3
        for i in range(3):
            assert f"agent-{i}" in results
            assert results[f"agent-{i}"]["success"] is True
            assert tasks[i].completed is True

    def test_sequential_agent_failure(self):
        """Test sequential execution with failing agent."""
        call_fn = Mock()
        orchestrator = Orchestrator(model="test-model", call_fn=call_fn)

        # Mock agent that raises exception
        agent = {
            "name": "failing-agent",
            "type": "legacy-function",
            "run": Mock(side_effect=RuntimeError("Agent failed"))
        }

        task = AgentTask(
            agent_name="failing-agent",
            agent_instance=agent,
            model="test-model"
        )

        results = orchestrator.run_sequential([task])

        assert "failing-agent" in results
        assert results["failing-agent"]["success"] is False
        assert "Agent failed" in results["failing-agent"]["error"]
        assert task.completed is True
        assert task.error is not None

    def test_sequential_with_class_based_agent(self):
        """Test sequential execution with class-based agent."""
        call_fn = Mock()
        orchestrator = Orchestrator(model="test-model", call_fn=call_fn)

        # Mock class-based agent
        mock_instance = Mock()
        mock_instance.run.return_value = {
            "success": True,
            "output": "Test output",
            "context_updates": {"updated_key": "updated_value"}
        }
        mock_instance.on_start = Mock()
        mock_instance.on_complete = Mock()

        agent = {
            "name": "class-agent",
            "type": "class-based-agent",
            "instance": mock_instance
        }

        task = AgentTask(
            agent_name="class-agent",
            agent_instance=agent,
            model="test-model"
        )

        results = orchestrator.run_sequential([task])

        assert results["class-agent"]["success"] is True
        assert results["class-agent"]["output"] == "Test output"

        # Verify lifecycle hooks called
        mock_instance.on_start.assert_called_once()
        mock_instance.on_complete.assert_called_once()

        # Verify shared memory updated
        assert orchestrator.shared_memory.get("updated_key") == "updated_value"

    def test_parallel_execution(self):
        """Test parallel execution with independent agents."""
        call_fn = Mock()
        orchestrator = Orchestrator(model="test-model", call_fn=call_fn, max_workers=2)

        # Create multiple independent agents
        tasks = []
        for i in range(3):
            agent = {
                "name": f"agent-{i}",
                "type": "legacy-function",
                "run": Mock()
            }

            task = AgentTask(
                agent_name=f"agent-{i}",
                agent_instance=agent,
                model="test-model"
            )
            tasks.append(task)

        results = orchestrator.run_parallel(tasks)

        assert len(results) == 3
        for i in range(3):
            assert f"agent-{i}" in results
            assert results[f"agent-{i}"]["success"] is True

    def test_parallel_with_dependencies(self):
        """Test parallel execution with dependencies."""
        call_fn = Mock()
        orchestrator = Orchestrator(model="test-model", call_fn=call_fn, max_workers=2)

        # Create agents with dependency chain: agent-0 -> agent-1 -> agent-2
        tasks = []
        for i in range(3):
            agent = {
                "name": f"agent-{i}",
                "type": "legacy-function",
                "run": Mock()
            }

            depends_on = [f"agent-{i-1}"] if i > 0 else []

            task = AgentTask(
                agent_name=f"agent-{i}",
                agent_instance=agent,
                model="test-model",
                depends_on=depends_on
            )
            tasks.append(task)

        results = orchestrator.run_parallel(tasks)

        assert len(results) == 3
        for i in range(3):
            assert f"agent-{i}" in results


class TestLoadTeamConfig:
    """Tests for load_team_config function."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid team config."""
        config_content = """
name: test-team
mode: sequential
model: test-model
agents:
  - name: agent1
    agent: test_agent_1
  - name: agent2
    agent: test_agent_2
    depends_on: [agent1]
"""
        config_file = tmp_path / "team.yaml"
        config_file.write_text(config_content)

        config = load_team_config(str(config_file))

        assert config["name"] == "test-team"
        assert config["mode"] == "sequential"
        assert config["model"] == "test-model"
        assert len(config["agents"]) == 2
        assert config["agents"][0]["name"] == "agent1"
        assert config["agents"][1]["depends_on"] == ["agent1"]

    def test_load_nonexistent_file(self):
        """Test loading non-existent config file."""
        with pytest.raises(FileNotFoundError):
            load_team_config("/nonexistent/path/team.yaml")

    def test_load_missing_required_keys(self, tmp_path):
        """Test loading config with missing required keys."""
        config_content = """
name: test-team
# missing mode and agents
"""
        config_file = tmp_path / "team.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="missing required key"):
            load_team_config(str(config_file))

    def test_load_invalid_mode(self, tmp_path):
        """Test loading config with invalid mode."""
        config_content = """
name: test-team
mode: invalid_mode
agents:
  - name: agent1
    agent: test_agent
"""
        config_file = tmp_path / "team.yaml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="Invalid mode"):
            load_team_config(str(config_file))

    def test_load_parallel_mode(self, tmp_path):
        """Test loading config with parallel mode."""
        config_content = """
name: parallel-team
mode: parallel
agents:
  - name: agent1
    agent: test_agent_1
  - name: agent2
    agent: test_agent_2
  - name: agent3
    agent: test_agent_3
    depends_on: [agent1, agent2]
"""
        config_file = tmp_path / "team.yaml"
        config_file.write_text(config_content)

        config = load_team_config(str(config_file))

        assert config["mode"] == "parallel"
        assert len(config["agents"]) == 3
        assert config["agents"][2]["depends_on"] == ["agent1", "agent2"]


class TestOrchestratorIntegration:
    """Integration tests for full orchestration scenarios."""

    def test_context_sharing_between_agents(self):
        """Test that agents can share context via shared memory."""
        call_fn = Mock()
        orchestrator = Orchestrator(model="test-model", call_fn=call_fn)

        # First agent writes to shared memory
        mock_instance_1 = Mock()
        mock_instance_1.run.return_value = {
            "success": True,
            "output": "Agent 1 output",
            "context_updates": {"shared_data": "from_agent_1"}
        }
        mock_instance_1.on_start = Mock()
        mock_instance_1.on_complete = Mock()

        agent_1 = {
            "name": "writer-agent",
            "type": "class-based-agent",
            "instance": mock_instance_1
        }

        # Second agent reads from shared memory
        mock_instance_2 = Mock()

        def agent_2_run(context, model, call_fn, tools=None):
            # Verify it receives the shared data
            assert context.get("shared_data") == "from_agent_1"
            return {"success": True, "output": "Agent 2 output"}

        mock_instance_2.run.side_effect = agent_2_run
        mock_instance_2.on_start = Mock()
        mock_instance_2.on_complete = Mock()

        agent_2 = {
            "name": "reader-agent",
            "type": "class-based-agent",
            "instance": mock_instance_2
        }

        task_1 = AgentTask("writer-agent", agent_1, "test-model")
        task_2 = AgentTask("reader-agent", agent_2, "test-model")

        results = orchestrator.run_sequential([task_1, task_2])

        assert results["writer-agent"]["success"] is True
        assert results["reader-agent"]["success"] is True

        # Verify both agents were called
        mock_instance_1.run.assert_called_once()
        mock_instance_2.run.assert_called_once()
