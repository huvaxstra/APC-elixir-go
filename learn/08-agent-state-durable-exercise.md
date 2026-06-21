# Module 8 Exercise: Durable Agent with Persistence

> **Estimated time:** 2 hours
>
> Build an agent that persists its state across crashes and restarts.
> You'll use ETS for fast reads, Ecto + Postgres for durable writes, and Oban for background jobs.

---

## Setup

Create a new Mix project with Ecto and Oban:

```bash
mix new durable_agent --sup
cd durable_agent
mix ecto.create
```

Add dependencies to `mix.exs`:

```elixir
defp deps do
  [
    {:ecto_sql, "~> 3.11"},
    {:postgrex, "~> 0.18"},
    {:oban, "~> 2.17"},
    {:jason, "~> 1.4"}
  ]
end
```

Run `mix deps.get`.

---

## Part 1: The ETS State Store

**File: `lib/durable_agent/state_store.ex`**

```elixir
defmodule DurableAgent.StateStore do
  # STARTER CODE:
  # Implement an ETS-backed state store using Agent as the owner process.

  # 1. start_link/1
  #    - Creates an ETS table with :named_table, :set, :public, :read_concurrency
  #    - Uses Agent.start_link to own the table
  #    - HINT: Agent.start_link(fn -> :ets.new(__MODULE__, [...]) end, name: __MODULE__)

  # 2. put/2
  #    - Takes a key (any term) and a value (any term)
  #    - Inserts into the ETS table
  #    - Returns :true
  #    - HINT: :ets.insert(__MODULE__, {key, value})

  # 3. get/1
  #    - Takes a key
  #    - Returns {:ok, value} if found, :error if not found
  #    - HINT: case :ets.lookup(__MODULE__, key) do [{^key, v}] -> {:ok, v}; [] -> :error end

  # 4. delete/1
  #    - Takes a key
  #    - Removes it from the table
  #    - Returns :true
  #    - HINT: :ets.delete(__MODULE__, key)

  # 5. get_all/0
  #    - Returns all key-value pairs as a map
  #    - HINT: :ets.tab2list(__MODULE__) |> Map.new()
end
```

---

## Part 2: The Ecto Schema and Changeset

**File: `lib/durable_agent/repo.ex`**

```elixir
defmodule DurableAgent.Repo do
  use Ecto.Repo,
    otp_app: :durable_agent,
    adapter: Ecto.Adapters.Postgres
end
```

**File: `lib/durable_agent/agent_record.ex`**

```elixir
defmodule DurableAgent.AgentRecord do
  use Ecto.Schema

  # STARTER CODE:
  # Define a schema for the "agents" table with these fields:
  #   - agent_id: :string
  #   - status: :string
  #   - config: :map
  #   - tasks_completed: :integer, default: 0
  #   - last_error: :string
  #   - timestamps()
  #
  # Then implement:

  # 1. insert_changeset/1
  #    - Takes attrs map
  #    - Casts agent_id, status, config, tasks_completed, last_error
  #    - Validates required: [:agent_id, :status]
  #    - Validates length of agent_id: min: 1, max: 255
  #    - Adds unique_constraint on :agent_id
  #    - HINT: %__MODULE__{} |> Ecto.Changeset.cast(attrs, [...]) |> Ecto.Changeset.validate_required([...])

  # 2. update_changeset/2
  #    - Takes an existing struct and attrs map
  #    - Casts status, config, tasks_completed, last_error
  #    - HINT: agent |> Ecto.Changeset.cast(attrs, [...])
end
```

---

## Part 3: The Agents Context

**File: `lib/durable_agent/agents.ex`**

```elixir
defmodule DurableAgent.Agents do
  alias DurableAgent.Repo
  alias DurableAgent.AgentRecord

  # STARTER CODE:

  # 1. create_agent/1
  #    - Takes attrs map
  #    - Creates a new AgentRecord with insert_changeset
  #    - Inserts into Repo
  #    - Returns {:ok, record} or {:error, changeset}
  #    - HINT: %AgentRecord{} |> AgentRecord.insert_changeset(attrs) |> Repo.insert()

  # 2. get_agent/1
  #    - Takes agent_id string
  #    - Finds by agent_id field
  #    - Returns {:ok, record} or {:error, :not_found}
  #    - HINT: Repo.get_by(AgentRecord, agent_id: agent_id)

  # 3. update_agent_status/2
  #    - Takes agent_id and status string
  #    - If agent exists, update it. If not, create it.
  #    - Returns {:ok, record} or {:error, changeset}
  #    - HINT: case get_agent(agent_id) do {:ok, r} -> update; {:error, _} -> create end

  # 4. list_agents/0
  #    - Returns all agent records
  #    - HINT: Repo.all(AgentRecord)

  # 5. delete_agent/1
  #    - Takes agent_id
  #    - Finds and deletes the record
  #    - Returns {:ok, record} or {:error, reason}
  #    - HINT: case get_agent(agent_id) do {:ok, r} -> Repo.delete(r); error -> error end
end
```

---

## Part 4: The Durable State Module

**File: `lib/durable_agent/durable_state.ex`**

```elixir
defmodule DurableAgent.DurableState do
  # STARTER CODE:
  # This module combines ETS (fast reads) with Ecto (durable writes).

  # 1. save_agent_state/2
  #    - Takes agent_id and state map (e.g., %{status: "running", tasks: 5})
  #    - Writes to ETS first: StateStore.put({:agent_state, agent_id}, state)
  #    - Then writes to Postgres: Agents.update_agent_status(agent_id, state.status)
  #    - Returns :ok
  #    - HINT: Write to ETS, then to Postgres. ETS for speed, Postgres for durability.

  # 2. get_agent_state/1
  #    - Takes agent_id
  #    - Tries ETS first (fast path)
  #    - If ETS miss, loads from Postgres and rebuilds ETS entry
  #    - Returns {:ok, state_map} or {:error, :not_found}
  #    - HINT: case StateStore.get({:agent_state, agent_id}) do {:ok, s} -> {:ok, s}; :error -> load_from_db end

  # 3. restore_all_agents/0
  #    - Loads all agents from Postgres
  #    - Rebuilds the ETS cache for each one
  #    - Returns :ok
  #    - HINT: Agents.list_agents() |> Enum.each(fn r -> StateStore.put(...) end)
end
```

---

## Part 5: The Oban Worker

**File: `lib/durable_agent/workers/agent_task_worker.ex`**

```elixir
defmodule DurableAgent.Workers.AgentTaskWorker do
  use Oban.Worker, queue: :agent_tasks, max_attempts: 3

  # STARTER CODE:

  # 1. perform/1
  #    - Receives an Oban.Job struct with args %{"agent_id" => ..., "task" => ...}
  #    - Calls a process_task/2 helper function
  #    - On success: update agent status in DB, broadcast event, return :ok
  #    - On failure: raise an error to trigger Oban retry
  #    - HINT: match on %Oban.Job{args: %{"agent_id" => id, "task" => task}}

  # 2. process_task/2 (private)
  #    - Takes agent_id and task string
  #    - Simulates work with Process.sleep(100)
  #    - Returns {:ok, result_string}
  #    - HINT: {:ok, "Result: #{task}"}
end
```

---

## Part 6: The Application Supervisor

**File: `lib/durable_agent/application.ex`**

```elixir
defmodule DurableAgent.Application do
  use Application

  # STARTER CODE:
  # Define the supervision tree with these children (in order):
  #   1. DurableAgent.Repo (Ecto)
  #   2. DurableAgent.StateStore (ETS via Agent)
  #   3. {Oban, Application.fetch_env!(:durable_agent, Oban)}
  #
  # After starting, call DurableAgent.DurableState.restore_all_agents()
  #
  # HINT: Supervisor.start_link(children, strategy: :one_for_one)
end
```

---

## Part 7: Test It

```elixir
# File: test/durable_agent_test.exs

defmodule DurableAgentTest do
  use ExUnit.Case

  # 1. Test ETS state store
  test "ETS operations work" do
    # Put a value
    # StateStore.put(:test_key, %{status: "running"})
    # assert {:ok, %{status: "running"}} = StateStore.get(:test_key)

    # Delete it
    # StateStore.delete(:test_key)
    # assert :error = StateStore.get(:test_key)
  end

  # 2. Test Ecto CRUD
  test "agent CRUD through Ecto" do
    # Create
    # {:ok, agent} = Agents.create_agent(%{agent_id: "test_1", status: "running"})
    # assert agent.agent_id == "test_1"

    # Read
    # {:ok, found} = Agents.get_agent("test_1")
    # assert found.status == "running"

    # Update
    # {:ok, updated} = Agents.update_agent_status("test_1", "completed")
    # assert updated.status == "completed"

    # Delete
    # {:ok, _} = Agents.delete_agent("test_1")
    # assert {:error, :not_found} = Agents.get_agent("test_1")
  end

  # 3. Test durable state (ETS + Ecto)
  test "save and retrieve agent state" do
    # Save state
    # DurableState.save_agent_state("dur_1", %{status: "active", tasks: 3})

    # Read from ETS (fast path)
    # {:ok, state} = DurableState.get_agent_state("dur_1")
    # assert state.status == "active"
    # assert state.tasks == 3
  end

  # 4. Test Oban job enqueuing
  test "enqueue and process agent task" do
    # Enqueue a job
    # {:ok, job} = DurableAgent.JobScheduler.enqueue_task("oban_1", "research topic")

    # Verify it's in the database
    # assert job.id != nil
    # assert job.args["agent_id"] == "oban_1"
  end
end
```

---

## Hints

<details>
<summary>Hint 1: ETS table creation</summary>

```elixir
Agent.start_link(
  fn ->
    :ets.new(__MODULE__, [
      :named_table,   # Table is registered by module name
      :set,           # One value per key
      :public,        # Any process can read/write
      :read_concurrency  # Optimized for concurrent reads
    ])
  end,
  name: __MODULE__
)
```

The `Agent` process owns the ETS table. As long as the Agent is alive, the table persists.

</details>

<details>
<summary>Hint 2: Ecto changeset pattern</summary>

```elixir
# Insert changeset:
def insert_changeset(attrs) do
  %__MODULE__{}
  |> Ecto.Changeset.cast(attrs, [:agent_id, :status, :config, :tasks_completed, :last_error])
  |> Ecto.Changeset.validate_required([:agent_id, :status])
  |> Ecto.Changeset.validate_length(:agent_id, min: 1, max: 255)
  |> Ecto.Changeset.unique_constraint(:agent_id)
end

# Update changeset:
def update_changeset(%__MODULE__{} = agent, attrs) do
  agent
  |> Ecto.Changeset.cast(attrs, [:status, :config, :tasks_completed, :last_error])
end
```

`cast/3` converts string keys to atoms and filters to only the specified fields. `validate_required/2` ensures mandatory fields are present. `unique_constraint/2` maps to the database index.

</details>

<details>
<summary>Hint 3: Oban worker pattern</summary>

```elixir
def perform(%Oban.Job{args: %{"agent_id" => agent_id, "task" => task}}) do
  # Process the task...
  result = "Done: #{task}"

  # Update DB and broadcast
  Agents.update_agent_status(agent_id, "completed")
  Phoenix.PubSub.broadcast(DurableAgent.PubSub, "agent_events",
    {:agent_event, :task_complete, agent_id, %{result: result}})

  # Return :ok on success (Oban marks job as "completed")
  :ok
rescue
  e ->
    # Raising triggers Oban's retry with exponential backoff
    raise "Task failed: #{inspect(e)}"
end
```

Return `:ok` for success. Raise an exception for retryable failures. Return `{:cancel, reason}` for permanent failures that should NOT be retried.

</details>

---

## Solution

<details>
<summary>Click to reveal the complete solution</summary>

### `lib/durable_agent/state_store.ex`

```elixir
defmodule DurableAgent.StateStore do
  use Agent

  def start_link(_opts) do
    # Create the ETS table owned by this Agent process.
    # The table persists as long as the Agent is alive.
    Agent.start_link(
      fn ->
        :ets.new(__MODULE__, [
          :named_table,
          :set,
          :public,
          :read_concurrency
        ])
      end,
      name: __MODULE__
    )
  end

  def put(key, value) do
    :ets.insert(__MODULE__, {key, value})
  end

  def get(key) do
    case :ets.lookup(__MODULE__, key) do
      [{^key, value}] -> {:ok, value}
      [] -> :error
    end
  end

  def delete(key) do
    :ets.delete(__MODULE__, key)
  end

  def get_all do
    :ets.tab2list(__MODULE__)
    |> Map.new()
  end
end
```

### `lib/durable_agent/agent_record.ex`

```elixir
defmodule DurableAgent.AgentRecord do
  use Ecto.Schema

  schema "agents" do
    field :agent_id, :string
    field :status, :string
    field :config, :map
    field :tasks_completed, :integer, default: 0
    field :last_error, :string
    timestamps()
  end

  def insert_changeset(attrs) do
    %__MODULE__{}
    |> Ecto.Changeset.cast(attrs, [:agent_id, :status, :config, :tasks_completed, :last_error])
    |> Ecto.Changeset.validate_required([:agent_id, :status])
    |> Ecto.Changeset.validate_length(:agent_id, min: 1, max: 255)
    |> Ecto.Changeset.unique_constraint(:agent_id)
  end

  def update_changeset(%__MODULE__{} = agent, attrs) do
    agent
    |> Ecto.Changeset.cast(attrs, [:status, :config, :tasks_completed, :last_error])
  end
end
```

### `lib/durable_agent/agents.ex`

```elixir
defmodule DurableAgent.Agents do
  alias DurableAgent.Repo
  alias DurableAgent.AgentRecord

  def create_agent(attrs) do
    %AgentRecord{}
    |> AgentRecord.insert_changeset(attrs)
    |> Repo.insert()
  end

  def get_agent(agent_id) do
    case Repo.get_by(AgentRecord, agent_id: agent_id) do
      nil -> {:error, :not_found}
      record -> {:ok, record}
    end
  end

  def update_agent_status(agent_id, status) do
    case get_agent(agent_id) do
      {:ok, record} ->
        record
        |> AgentRecord.update_changeset(%{status: status})
        |> Repo.update()

      {:error, :not_found} ->
        create_agent(%{agent_id: agent_id, status: status})
    end
  end

  def list_agents do
    Repo.all(AgentRecord)
  end

  def delete_agent(agent_id) do
    case get_agent(agent_id) do
      {:ok, record} -> Repo.delete(record)
      {:error, _} = error -> error
    end
  end
end
```

### `lib/durable_agent/durable_state.ex`

```elixir
defmodule DurableAgent.DurableState do
  alias DurableAgent.StateStore
  alias DurableAgent.Agents

  def save_agent_state(agent_id, state) do
    # Write to ETS first (fast path for reads).
    StateStore.put({:agent_state, agent_id}, state)

    # Write to Postgres (durable persistence).
    Agents.update_agent_status(agent_id, state.status)

    :ok
  end

  def get_agent_state(agent_id) do
    case StateStore.get({:agent_state, agent_id}) do
      {:ok, state} ->
        # ETS hit — return immediately (microseconds).
        {:ok, state}

      :error ->
        # ETS miss — load from Postgres (milliseconds).
        case Agents.get_agent(agent_id) do
          {:ok, record} ->
            state = %{status: record.status, tasks: record.tasks_completed}
            # Rebuild ETS entry for future fast reads.
            StateStore.put({:agent_state, agent_id}, state)
            {:ok, state}

          {:error, _} = error ->
            error
        end
    end
  end

  def restore_all_agents do
    Agents.list_agents()
    |> Enum.each(fn record ->
      state = %{status: record.status, tasks: record.tasks_completed}
      StateStore.put({:agent_state, record.agent_id}, state)
    end)

    :ok
  end
end
```

### `lib/durable_agent/workers/agent_task_worker.ex`

```elixir
defmodule DurableAgent.Workers.AgentTaskWorker do
  use Oban.Worker, queue: :agent_tasks, max_attempts: 3

  def perform(%Oban.Job{args: %{"agent_id" => agent_id, "task" => task}}) do
    IO.puts("Worker processing task for #{agent_id}: #{task}")

    case process_task(agent_id, task) do
      {:ok, result} ->
        # Update status in Postgres.
        DurableAgent.Agents.update_agent_status(agent_id, "completed")

        # Save state to ETS + Postgres.
        DurableAgent.DurableState.save_agent_state(agent_id, %{
          status: "completed",
          tasks: 1
        })

        # Broadcast to dashboard.
        Phoenix.PubSub.broadcast(
          DurableAgent.PubSub,
          "agent_events",
          {:agent_event, :task_complete, agent_id, %{result: result}}
        )

        :ok

      {:error, reason} ->
        # Update error in Postgres for debugging.
        DurableAgent.Agents.update_agent_status(agent_id, "failed")

        # Raise to trigger Oban retry with exponential backoff.
        raise "Task failed: #{reason}"
    end
  end

  defp process_task(agent_id, task) do
    Process.sleep(100)
    {:ok, "Result: #{task}"}
  end
end
```

### `lib/durable_agent/application.ex`

```elixir
defmodule DurableAgent.Application do
  use Application

  def start(_type, _args) do
    children = [
      # Database — must start first (other modules depend on it).
      DurableAgent.Repo,

      # ETS state store — fast reads for agent state.
      DurableAgent.StateStore,

      # Oban — background job processing with Postgres persistence.
      {Oban, Application.fetch_env!(:durable_agent, Oban)}
    ]

    # Start the supervision tree.
    result = Supervisor.start_link(children, strategy: :one_for_one, name: DurableAgent.Supervisor)

    # Restore ETS from Postgres after supervision tree is up.
    # WHY: ETS tables are empty on fresh start. Postgres has the durable data.
    DurableAgent.DurableState.restore_all_agents()

    result
  end
end
```

### `priv/repo/migrations/001_create_agents.exs`

```elixir
defmodule DurableAgent.Repo.Migrations.CreateAgents do
  use Ecto.Migration

  def change do
    create table(:agents) do
      add :agent_id, :string, null: false
      add :status, :string, null: false
      add :config, :map
      add :tasks_completed, :integer, default: 0
      add :last_error, :string

      timestamps()
    end

    # Unique index on agent_id prevents duplicate agents.
    create unique_index(:agents, [:agent_id])
  end
end
```

### `config/config.exs` (Oban config)

```elixir
config :durable_agent, Oban,
  repo: DurableAgent.Repo,
  plugins: [
    {Oban.Plugins.Pruner, max_age: 3600 * 24 * 7}
  ],
  queues: [
    agent_tasks: 10
  ]
```

</details>

---

## What You've Built

- **StateStore**: ETS-backed fast-read state store using Agent as the owner process
- **AgentRecord**: Ecto schema + changesets for durable Postgres persistence
- **Agents context**: CRUD operations for agent records (create, read, update, delete)
- **DurableState**: Two-layer pattern combining ETS (fast) with Ecto (durable)
- **AgentTaskWorker**: Oban worker with automatic retries and exponential backoff
- **Application supervision tree**: Ties everything together with proper startup order

Your agent now survives crashes (Oban retries), node restarts (Postgres persistence), and provides
fast reads (ETS cache). The two-layer pattern ensures your dashboard reads from ETS (microseconds)
while Postgres ensures nothing is lost.

**Next:** [Module 9: Advanced OTP Patterns](09-advanced-otp.md) — GenServer, Task, and advanced supervision trees.
