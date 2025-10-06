# Multi-Agent Teams Guide

## Overview

NORA v0.4.0 introduces multi-agent orchestration, allowing you to coordinate multiple AI agents working together on complex tasks. Agents can share memory, pass messages, and execute either sequentially or in parallel.

## Quick Start

### 1. Create a Team Configuration

Create a YAML file defining your team:

```yaml
# team-config.yaml
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
  - name: tester
    agent: test_generator
    depends_on: [reviewer]
```

### 2. Run the Team

```bash
nora agent --team team-config.yaml
```

Output:
```
ℹ Loading team config: team-config.yaml
ℹ Running team: code-review-team (3 agents)
✓ Team execution completed
  ✓ analyzer: Success
  ✓ reviewer: Success
  ✓ tester: Success
```

## Team Configuration Reference

### Required Fields

```yaml
name: string              # Team name
mode: sequential|parallel # Execution mode
agents: array             # List of agents
```

### Optional Fields

```yaml
model: string             # Default model (can be overridden per-agent)
```

### Agent Configuration

Each agent in the team can specify:

```yaml
- name: string           # Unique name for this agent instance
  agent: string          # Plugin name to execute
  depends_on: array      # List of agent names (dependencies)
  config: object         # Agent-specific configuration
  model: string          # Override team model for this agent
```

## Execution Modes

### Sequential Mode

Agents execute one after another in the order defined:

```yaml
name: sequential-team
mode: sequential
agents:
  - name: step1
    agent: data_loader
  - name: step2
    agent: data_processor
  - name: step3
    agent: data_analyzer
```

**Flow:**
```
step1 → step2 → step3
```

**Use cases:**
- Linear pipelines
- Data processing workflows
- Step-by-step analysis

### Parallel Mode

Agents execute concurrently, respecting dependencies:

```yaml
name: parallel-team
mode: parallel
agents:
  - name: parser
    agent: code_parser
  - name: linter
    agent: code_linter
  - name: analyzer
    agent: code_analyzer
    depends_on: [parser]
  - name: reviewer
    agent: code_reviewer
    depends_on: [linter, analyzer]
```

**Flow:**
```
parser ─┐
        ├──→ analyzer ─┐
linter ─┘              ├──→ reviewer
```

**Use cases:**
- Independent tasks
- Parallel data processing
- Complex dependency graphs

## Shared Memory & Message Passing

Agents can communicate via shared memory and message queues.

### Shared Memory

Agents can read/write shared key-value pairs:

```python
from nora.core import Agent

class WriterAgent(Agent):
    def run(self, context, model, call_fn, tools=None):
        # Write to shared memory
        return {
            "success": True,
            "output": "Data written",
            "context_updates": {
                "shared_data": "Hello from writer!"
            }
        }

class ReaderAgent(Agent):
    def run(self, context, model, call_fn, tools=None):
        # Read from shared memory
        data = context.get("shared_data", "No data")
        return {"success": True, "output": f"Read: {data}"}
```

### Message Passing

Agents can post messages to a queue:

```python
# In orchestrator internals
shared_memory.post_message("agent1", "Task complete", {"status": "done"})

# Other agents can consume messages
messages = shared_memory.get_messages()
for msg in messages:
    print(f"{msg['sender']}: {msg['message']}")
```

## Example Team Configurations

### 1. Code Review Team

Sequential pipeline for code review:

```yaml
name: code-review
mode: sequential
model: deepseek-coder:6.7b
agents:
  - name: syntax-checker
    agent: syntax_analyzer
    config:
      strict: true

  - name: style-checker
    agent: style_analyzer
    config:
      style_guide: pep8

  - name: security-checker
    agent: security_analyzer
    config:
      severity: high

  - name: report-generator
    agent: report_writer
```

**Run:**
```bash
nora agent --team code-review.yaml
```

### 2. Data Processing Team

Parallel processing with dependencies:

```yaml
name: data-pipeline
mode: parallel
model: llama3.2:3b
agents:
  - name: fetch-api
    agent: api_fetcher
    config:
      endpoint: https://api.example.com/data

  - name: fetch-db
    agent: db_fetcher
    config:
      table: users

  - name: merge-data
    agent: data_merger
    depends_on: [fetch-api, fetch-db]

  - name: transform
    agent: data_transformer
    depends_on: [merge-data]

  - name: validate
    agent: data_validator
    depends_on: [transform]

  - name: export
    agent: data_exporter
    depends_on: [validate]
```

**Run:**
```bash
nora agent --team data-pipeline.yaml
```

### 3. Research Team

Multiple researchers working in parallel:

```yaml
name: research-team
mode: parallel
model: deepseek-coder:6.7b
agents:
  - name: web-researcher
    agent: web_searcher
    config:
      max_results: 10

  - name: doc-researcher
    agent: document_analyzer
    config:
      sources: [papers, docs]

  - name: code-researcher
    agent: code_analyzer
    config:
      repos: [github, gitlab]

  - name: synthesizer
    agent: report_synthesizer
    depends_on: [web-researcher, doc-researcher, code-researcher]
```

### 4. Bug Hunting Team

Find and fix bugs collaboratively:

```yaml
name: bug-hunters
mode: sequential
agents:
  - name: detector
    agent: bug_detector
    config:
      patterns: [null_deref, race_condition, memory_leak]

  - name: analyzer
    agent: bug_analyzer
    config:
      depth: 5

  - name: fixer
    agent: bug_fixer
    config:
      auto_fix: true

  - name: tester
    agent: test_runner
    config:
      test_suite: all
```

## Creating Team-Compatible Agents

### Class-Based Agent (Recommended)

```python
from nora.core import Agent

class TeamAgent(Agent):
    def metadata(self):
        return {
            "name": "team-agent",
            "description": "Agent designed for team workflows",
            "version": "1.0.0",
            "capabilities": ["analysis", "collaboration"]
        }

    def run(self, context, model, call_fn, tools=None):
        # Access configuration from team YAML
        config = context.get("config", {})
        agent_name = context.get("agent_name", "unknown")

        # Read from shared context
        previous_result = context.get("previous_result")

        # Do work with LLM
        messages = [
            {"role": "user", "content": f"Analyze: {previous_result}"}
        ]
        call_fn(messages, model=model, stream=False)

        # Return result and update shared context
        return {
            "success": True,
            "output": "Analysis complete",
            "context_updates": {
                "analysis_result": "Detailed findings..."
            }
        }

    def on_start(self, context):
        print(f"Agent {context['agent_name']} starting...")

    def on_complete(self, result, context):
        print(f"Agent completed successfully")

    def on_error(self, error, context):
        print(f"Agent failed: {error}")
```

### Legacy Function-Based Agent

```python
def register():
    def run(model, call_fn):
        # Legacy agents don't receive context
        # Limited team integration
        messages = [{"role": "user", "content": "Hello"}]
        call_fn(messages, model=model, stream=True)

    return {
        "name": "legacy-agent",
        "description": "Legacy function-based agent",
        "run": run
    }
```

**Note:** Class-based agents are recommended for team workflows as they receive context and can update shared memory.

## Orchestrator Programmatic API

For advanced use cases, use the Orchestrator directly:

```python
from nora.core.orchestrator import Orchestrator, AgentTask
from nora.core import ConfigManager, OllamaChat, PluginLoader

# Setup
config = ConfigManager()
chat_client = OllamaChat(config.get_ollama_url(), config.get_model())
plugin_loader = PluginLoader()
plugins = plugin_loader.load_plugins()

# Create orchestrator
orchestrator = Orchestrator(
    model="deepseek-coder:6.7b",
    call_fn=chat_client.chat,
    max_workers=4
)

# Define tasks
tasks = [
    AgentTask(
        agent_name="analyzer",
        agent_instance=plugins["analyzer"],
        model="deepseek-coder:6.7b",
        depends_on=[],
        config={"depth": 3}
    ),
    AgentTask(
        agent_name="reviewer",
        agent_instance=plugins["reviewer"],
        model="deepseek-coder:6.7b",
        depends_on=["analyzer"],
        config={"strict": True}
    ),
]

# Execute
results = orchestrator.run_sequential(tasks)

# Access results
for agent_name, result in results.items():
    print(f"{agent_name}: {result['success']}")

# Access shared memory
shared_data = orchestrator.shared_memory.get_all()
```

## Best Practices

### 1. Design for Idempotency

Agents should produce the same result given the same input:

```python
def run(self, context, model, call_fn, tools=None):
    input_hash = hashlib.md5(str(context).encode()).hexdigest()

    # Check cache
    if input_hash in cache:
        return cache[input_hash]

    # Compute result
    result = do_work()

    # Cache for next time
    cache[input_hash] = result
    return result
```

### 2. Use Descriptive Names

```yaml
agents:
  - name: fetch-user-data        # Good: Clear and specific
    agent: data_fetcher

  - name: step1                   # Bad: Generic
    agent: data_fetcher
```

### 3. Handle Failures Gracefully

```python
def run(self, context, model, call_fn, tools=None):
    try:
        result = risky_operation()
        return {"success": True, "output": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 4. Document Dependencies

```yaml
agents:
  - name: analyzer
    agent: code_analyzer
    # No dependencies - runs first

  - name: reviewer
    agent: code_reviewer
    depends_on: [analyzer]  # Waits for analyzer
```

### 5. Use Config for Parameterization

```yaml
agents:
  - name: linter
    agent: code_linter
    config:
      rules: strict
      max_line_length: 100
      ignore_patterns: [test_*.py]
```

Then access in agent:

```python
def run(self, context, model, call_fn, tools=None):
    config = context.get("config", {})
    rules = config.get("rules", "standard")
    max_line_length = config.get("max_line_length", 80)
```

## Troubleshooting

### Issue: Deadlock in Parallel Mode

**Symptom:** Team hangs indefinitely

**Cause:** Circular dependencies

```yaml
# BAD: Circular dependency
agents:
  - name: a
    agent: agent_a
    depends_on: [b]
  - name: b
    agent: agent_b
    depends_on: [a]
```

**Solution:** Remove circular dependencies

### Issue: Agent Not Found

**Symptom:** "Agent not found: xyz"

**Cause:** Agent plugin doesn't exist

**Solution:**
1. Check plugin name matches file: `nora/plugins/xyz.py`
2. Verify plugin has `register()` function
3. Run `nora agents` to list available agents

### Issue: Shared Memory Not Updating

**Symptom:** Agents don't see each other's data

**Cause:** Not using `context_updates` in return value

**Solution:**
```python
# BAD: Direct shared memory access (doesn't work)
shared_memory.set("key", "value")

# GOOD: Return context_updates
return {
    "success": True,
    "context_updates": {"key": "value"}
}
```

### Issue: Agent Execution Order Wrong

**Symptom:** Agents run in unexpected order

**Cause:** In parallel mode, order depends on dependencies, not definition order

**Solution:** Use sequential mode or add explicit dependencies:

```yaml
mode: parallel
agents:
  - name: first
    agent: agent_1

  - name: second
    agent: agent_2
    depends_on: [first]  # Explicit ordering
```

## Performance Tips

### 1. Use Parallel Mode for Independent Tasks

```yaml
# SLOW: Sequential (5 minutes total)
mode: sequential
agents: [task1, task2, task3, task4, task5]

# FAST: Parallel (1 minute total if all independent)
mode: parallel
agents: [task1, task2, task3, task4, task5]
```

### 2. Limit Max Workers

```python
# For CPU-intensive tasks
orchestrator = Orchestrator(model=model, call_fn=chat_fn, max_workers=2)

# For I/O-bound tasks
orchestrator = Orchestrator(model=model, call_fn=chat_fn, max_workers=8)
```

### 3. Avoid Heavy Shared Memory Usage

```python
# BAD: Storing large data in shared memory
context_updates = {"large_dataset": huge_list}

# GOOD: Store references or summaries
context_updates = {
    "dataset_path": "/tmp/data.json",
    "dataset_size": 1000000,
    "dataset_summary": "1M records..."
}
```

## Future Features (Roadmap)

Planned enhancements for v0.5.0+:

- **Agent Templates**: Pre-built team configurations
- **Conditional Execution**: Run agents based on previous results
- **Loop Support**: Repeat agents until condition met
- **Error Recovery**: Automatic retry and fallback strategies
- **Monitoring UI**: Real-time team execution visualization
- **Remote Agents**: Agents running on different machines
- **Resource Limits**: CPU/memory constraints per agent

See [ROADMAP.md](../ROADMAP.md) for details.

---

**Next Steps:**
- Create your first team: `nora project new my-team-agent`
- Try example configs in `examples/teams/`
- Read [Overview.md](./Overview.md) for architecture
- Check [Agents.md](./Agents.md) for agent development
