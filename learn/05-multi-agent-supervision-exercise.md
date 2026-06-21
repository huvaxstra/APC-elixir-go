# Module 5 Exercise: Agent Pool with Auto-Restart

> **Estimated time:** 2 hours
>
> Build a supervised agent pool where agents can be started, stopped, and automatically restarted when they crash.
> You'll use DynamicSupervisor, Registry, and GenServer together.

---

## Setup

Create a new Mix project:

```bash
mix new agent_pool --sup
cd agent_pool
```

The `--sup` flag generates an application supervisor automatically.

---

## Part 1: The Agent Worker

Each agent manages a task (like processing a user's request). The agent tracks its state and processes messages.

**File: `lib/agent_pool/agent_worker.ex`**

```elixir
defmodule AgentPool.AgentWorker do
  use GenServer

  # STARTER CODE:
  # Implement the following functions.
  # Each function has hints below it.

  # --- Public API ---

  # 1. start_link/2
  #    - Takes agent_id (string) and config (map)
  #    - Registers via Registry using :via tuple
  #    - HINT: name: {:via, Registry, {AgentPool.AgentRegistry, agent_id, %{}}}

  # 2. process_task/2
  #    - Takes agent_id and task (string)
  #    - Sends a message to the agent process (use Registry.lookup to find PID)
  #    - Returns {:ok, pid} or {:error, :not_found}
  #    - HINT: Registry.lookup returns [{pid, _}] or []

  # --- Callbacks ---

  # 3. init/1
  #    - Receives {agent_id, config}
  #    - Returns {:ok, initial_state}
  #    - State should track: agent_id, config, tasks_completed, started_at

  # 4. handle_info/2
  #    - Handles {:process_task, task} messages
  #    - Increments tasks_completed counter
  #    - Returns {:noreply, new_state}
  #    - HINT: Use Map.update to increment the counter

  # 5. handle_info/2 catch-all
  #    - Handles any unknown message
  #    - Returns {:noreply, state} (don't crash on unknown messages)

  # 6. handle_call(:get_status, _from, state)
  #    - Returns the agent's current status as a map
  #    - Include: agent_id, tasks_completed, uptime (computed from started_at)

  # 7. terminate/2
  #    - Called when the agent shuts down
  #    - Log the shutdown reason
  #    - HINT: Use Logger.info("Agent #{state.agent_id} shutting down: #{reason}")
end
```

---

## Part 2: The Registry

**File: `lib/agent_pool/agent_registry.ex`**

```elixir
defmodule AgentPool.AgentRegistry do
  # STARTER CODE:
  # Implement the Registry using use Registry.
  #
  # HINT: You need exactly 3 lines:
  #   1. use Registry, keys: :unique, name: __MODULE__
  #   2. def start_link(_opts), do: Registry.start_link(__MODULE__)
  #   3. def child_spec(_opts), do: %{id: __MODULE__, start: {__MODULE__, :start_link, []}, type: :supervisor}
end
```

---

## Part 3: The Agent Pool (DynamicSupervisor)

**File: `lib/agent_pool/agent_pool.ex`**

```elixir
defmodule AgentPool.AgentPool do
  # STARTER CODE:
  # Implement the DynamicSupervisor.

  # 1. start_link/1
  #    - Start a DynamicSupervisor with name: __MODULE__, strategy: :one_for_one
  #    - HINT: DynamicSupervisor.start_link(name: __MODULE__, strategy: :one_for_one)

  # 2. start_agent/2
  #    - Takes agent_id (string) and config (map)
  #    - Uses DynamicSupervisor.start_child to add an AgentWorker
  #    - The child spec should have:
  #      - id: AgentWorker
  #      - start: {AgentWorker, :start_link, [agent_id, config]}
  #      - restart: :permanent
  #    - Returns {:ok, pid} or {:error, reason}

  # 3. stop_agent/1
  #    - Takes agent_id
  #    - Looks up the PID via Registry.lookup
  #    - Calls DynamicSupervisor.terminate_child to stop it
  #    - Returns :ok or {:error, :not_found}
end
```

---

## Part 4: The Application Supervisor

**File: `lib/agent_pool/application.ex`** (replace the generated one)

```elixir
defmodule AgentPool.Application do
  use Application

  # STARTER CODE:
  # Define the supervision tree.
  #
  # Children should start in this order:
  #   1. AgentPool.AgentRegistry
  #   2. AgentPool.AgentPool (DynamicSupervisor)
  #
  # HINT: Use Supervisor.start_link with strategy: :one_for_one
  #
  # The order matters: Registry must start BEFORE DynamicSupervisor
  # because agents register in the Registry when they start.
end
```

---

## Part 5: Test It

Create a test script at `test/agent_pool_test.exs`:

```elixir
defmodule AgentPoolTest do
  use ExUnit.Case

  test "starts and stops agents" do
    # 1. Start an agent
    #    HINT: {:ok, pid} = AgentPool.start_agent("test_1", %{role: :researcher})
    #    assert is_pid(pid)

    # 2. Verify the agent is registered
    #    HINT: [{^pid, _}] = Registry.lookup(AgentPool.AgentRegistry, "test_1")

    # 3. Process a task
    #    HINT: {:ok, _} = AgentPool.process_task("test_1", "research topic X")

    # 4. Check agent status
    #    HINT: GenServer.call(pid, :get_status)
    #    assert status.tasks_completed == 1

    # 5. Stop the agent
    #    HINT: :ok = AgentPool.stop_agent("test_1")

    # 6. Verify it's gone
    #    HINT: [] = Registry.lookup(AgentPool.AgentRegistry, "test_1")
  end

  test "agent restarts after crash" do
    # 1. Start an agent
    #    {:ok, pid} = AgentPool.start_agent("crasher", %{})

    # 2. Kill it (simulate a crash)
    #    Process.exit(pid, :kill)
    #    :timer.sleep(100)  # Give supervisor time to restart

    # 3. Verify a NEW PID exists for the same agent_id
    #    HINT: [{new_pid, _}] = Registry.lookup(AgentPool.AgentRegistry, "crasher")
    #    assert new_pid != pid  # The PID changed — it was restarted!
  end
end
```

---

## Hints

<details>
<summary>Hint 1: The :via tuple syntax</summary>

The `:via` tuple for Registry is: `{:via, Registry, {RegistryName, key, value}}`.

The `value` is metadata stored with the registration — usually `%{}`.

Example: `name: {:via, Registry, {AgentPool.AgentRegistry, "agent_1", %{}}}`
</details>

<details>
<summary>Hint 2: Finding a PID from agent_id</summary>

```elixir
case Registry.lookup(AgentPool.AgentRegistry, agent_id) do
  [{pid, _}] -> pid
  [] -> nil
end
```

`Registry.lookup/2` returns a list of `{pid, value}` tuples. With `:unique` keys, there's at most one.
</details>

<details>
<summary>Hint 3: The child spec map</summary>

```elixir
%{
  id: AgentWorker,
  start: {AgentWorker, :start_link, [agent_id, config]},
  restart: :permanent
}
```

The `start` key is an MFA tuple (Module, Function, Arguments). DynamicSupervisor calls `apply(M, F, A)` to start the child.
</details>

---

## Solution

<details>
<summary>Click to reveal the complete solution</summary>

### `lib/agent_pool/agent_worker.ex`

```elixir
defmodule AgentPool.AgentWorker do
  use GenServer
  require Logger

  # Public API

  # start_link/2 starts the agent and registers it in the Registry.
  # The :via tuple lets us look up agents by ID instead of storing PIDs.
  def start_link(agent_id, config) do
    GenServer.start_link(
      __MODULE__,
      {agent_id, config},
      # Register via Registry so we can find this agent by agent_id later.
      # WHY: PIDs change on restart, but the agent_id stays the same.
      name: {:via, Registry, {AgentPool.AgentRegistry, agent_id, %{}}}
    )
  end

  # process_task/2 sends a task to an agent by looking up its PID.
  # Returns {:ok, pid} if the agent exists, {:error, :not_found} otherwise.
  def process_task(agent_id, task) do
    case Registry.lookup(AgentPool.AgentRegistry, agent_id) do
      [{pid, _}] ->
        # send/2 is asynchronous — we don't wait for a response.
        # WHY async: we want to fire-and-forget. The agent processes the task independently.
        send(pid, {:process_task, task})
        {:ok, pid}

      [] ->
        {:error, :not_found}
    end
  end

  # Callbacks

  # init/1 sets up the agent's initial state.
  # The agent_id is its identity, config is task-specific settings.
  def init({agent_id, config}) do
    Logger.info("Agent #{agent_id} starting with config: #{inspect(config)}")

    {:ok, %{
      agent_id: agent_id,
      config: config,
      tasks_completed: 0,
      started_at: System.system_time(:second)
    }}
  end

  # handle_info for task processing.
  # Each task increments the counter. In a real system, this would call
  # an LLM, run code, or perform some computation.
  def handle_info({:process_task, task}, state) do
    Logger.info("Agent #{state.agent_id} processing: #{task}")

    # Map.update/4 safely increments a counter, defaulting to 0 if the key is missing.
    new_state = Map.update(state, :tasks_completed, 1, &(&1 + 1))

    {:noreply, new_state}
  end

  # Catch-all: don't crash on unexpected messages.
  # WHY: in a supervision tree, crashing triggers a restart cycle.
  # Logging unknown messages helps with debugging without killing the process.
  def handle_info(unknown, state) do
    Logger.warning("Agent #{state.agent_id} received unknown message: #{inspect(unknown)}")
    {:noreply, state}
  end

  # handle_call for status queries.
  # synchronous call that returns the agent's current state.
  def handle_call(:get_status, _from, state) do
    # Compute uptime from the start timestamp.
    # WHY: we store started_at in init, not the duration, so it stays accurate.
    uptime = System.system_time(:second) - state.started_at

    status = %{
      agent_id: state.agent_id,
      tasks_completed: state.tasks_completed,
      uptime_seconds: uptime
    }

    {:reply, status, state}
  end

  # Called when the agent is being shut down (by supervisor or terminate_child).
  # Log it so we can see restarts in the logs.
  def terminate(reason, state) do
    Logger.info("Agent #{state.agent_id} terminated: #{inspect(reason)}")
    :ok
  end
end
```

### `lib/agent_pool/agent_registry.ex`

```elixir
defmodule AgentPool.AgentRegistry do
  use Registry, keys: :unique, name: __MODULE__

  # Registry manages name-to-PID mappings in a concurrent ETS table.
  # We define start_link and child_spec so it can be used in a supervision tree.

  def start_link(_opts) do
    Registry.start_link(__MODULE__)
  end

  def child_spec(_opts) do
    %{
      id: __MODULE__,
      start: {__MODULE__, :start_link, []},
      type: :supervisor
    }
  end
end
```

### `lib/agent_pool/agent_pool.ex`

```elixir
defmodule AgentPool.AgentPool do
  use DynamicSupervisor

  # start_link/1 starts the DynamicSupervisor with the given options.
  # The name option lets other processes find this supervisor by atom.
  def start_link(_opts) do
    DynamicSupervisor.start_link(
      __MODULE__,
      :ok,
      name: __MODULE__
    )
  end

  # init/1 configures the DynamicSupervisor.
  # :one_for_one is the only strategy available.
  # max_children prevents runaway agent creation from exhausting memory.
  def init(:ok) do
    DynamicSupervisor.init(strategy: :one_for_one)
  end

  # start_agent/2 adds a new AgentWorker to the pool.
  # Returns {:ok, pid} if successful, {:error, reason} if not.
  def start_agent(agent_id, config) do
    DynamicSupervisor.start_child(__MODULE__, %{
      id: AgentWorker,
      start: {AgentWorker, :start_link, [agent_id, config]},
      # :permanent means the supervisor ALWAYS restarts this child on crash.
      # WHY: agents are long-lived and should persist across failures.
      restart: :permanent
    })
  end

  # stop_agent/1 gracefully terminates a specific agent.
  # Looks up the PID via Registry, then tells DynamicSupervisor to stop it.
  def stop_agent(agent_id) do
    case Registry.lookup(AgentPool.AgentRegistry, agent_id) do
      [{pid, _}] ->
        DynamicSupervisor.terminate_child(__MODULE__, pid)

      [] ->
        {:error, :not_found}
    end
  end
end
```

### `lib/agent_pool/application.ex`

```elixir
defmodule AgentPool.Application do
  use Application

  # start/2 is called by the Erlang VM when the application boots.
  # Children are started in order — Registry MUST come before AgentPool.
  def start(_type, _args) do
    children = [
      # Registry starts first because agents register in it when they start.
      AgentPool.AgentRegistry,
      # DynamicSupervisor starts second — it manages runtime agent processes.
      AgentPool.AgentPool
    ]

    # :one_for_one: if one supervisor crashes, the other keeps running.
    Supervisor.start_link(children, strategy: :one_for_one, name: AgentPool.Supervisor)
  end
end
```

</details>

---

## What You've Built

- **AgentWorker**: A GenServer that represents a single agent with state and message handling
- **AgentRegistry**: A process registry for finding agents by ID
- **AgentPool**: A DynamicSupervisor that manages agent lifecycle at runtime
- **Application**: A supervision tree tying it all together

When an agent crashes, the supervisor automatically restarts it. When you need to find an agent, you use its
ID through the Registry instead of storing PIDs. This is the foundation every production agentic system builds on.

**Next:** [Module 6: Phoenix LiveView Dashboard](06-phoenix-liveview.md)
