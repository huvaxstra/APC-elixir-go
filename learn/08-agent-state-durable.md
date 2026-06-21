# Module 8: Agent State & Durable Workflows

> **Week 8** · Elixir · ~4 hours
>
> Your agents work in memory. If the node crashes, all state vanishes. This module teaches you how to make
> agent state survive crashes, restarts, and even node failures. You'll use ETS for fast in-memory state,
> Ecto + Postgres for durable persistence, and Oban for background jobs with retries. Iteration Layer uses
> Elixir for durable workflows. Infra One persists agent state in Postgres. You'll build both patterns.

---

## Why Durable State Matters

An agent that forgets everything on restart is like a doctor who loses their memory after lunch. Every
patient (task) starts from scratch. The patient history (state) is gone. The diagnosis (context) is lost.

Durable state solves three problems:
1. **Crash recovery** — restart with the state you had before the crash
2. **Node restart** — survive the entire machine going down
3. **Work distribution** — share state across multiple nodes in a cluster

---

## 1. ETS: Fast In-Memory State

ETS (Erlang Term Storage) is a concurrent, in-memory key-value store built into the BEAM. Think of it as
a **bulletin board** that any process can read from and write to — no GenServer bottleneck.

### Why ETS Instead of GenServer State?

| Approach | Speed | Concurrent reads | Survives process crash |
|----------|-------|-------------------|----------------------|
| GenServer state | Fast | Serial (one at a time) | No — dies with the process |
| ETS table | Fast (microseconds) | Parallel (many at once) | Yes — owned by owner process, not the reader |

ETS is ideal for read-heavy state that many agents need to access simultaneously: agent status maps,
configuration caches, shared counters.

```elixir
defmodule AgentStateStore do
  # use Agent ensures this module is supervised and linked to the application.
  # We use Agent because it's the simplest way to own an ETS table.
  use Agent

  # start_link/1 creates the ETS table and starts the owning process.
  # The table persists as long as this process is alive.
  # WHY Agent: ETS tables are owned by the process that created them.
  # If that process dies, the table dies too. Agent keeps it alive.
  def start_link(_opts) do
    # :named_table gives the table a registered name so other processes can find it.
    # :set means one key per row (like a HashMap). :bag allows duplicate keys.
    # :public means any process can read AND write. :protected means only the owner writes.
    # :read_concurrent optimizes for concurrent reads — multiple processes read simultaneously.
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

  # put/2 writes a key-value pair to the ETS table.
  # This is O(1) — constant time regardless of table size.
  # The value can be ANY Erlang/Elixir term (atoms, maps, lists, structs).
  def put(key, value) do
    # :ets.insert/2 replaces the value if the key already exists.
    # It returns :true always — there's no error case for inserts.
    :ets.insert(__MODULE__, {key, value})
  end

  # get/1 reads a value by key.
  # Returns {:ok, value} if found, :error if not found.
  # This is O(1) — hash table lookup, not a list scan.
  def get(key) do
    case :ets.lookup(__MODULE__, key) do
      [{^key, value}] -> {:ok, value}
      [] -> :error
    end
  end

  # get_all/0 returns all key-value pairs as a map.
  # Use sparingly — this reads the entire table.
  # Good for debugging or snapshotting state.
  def get_all do
    :ets.tab2list(__MODULE__)
    |> Map.new()
  end

  # delete/1 removes a key from the table.
  # Returns :true always.
  def delete(key) do
    :ets.delete(__MODULE__, key)
  end

  # update_counter/3 atomically increments a numeric value.
  # WHY atomic: multiple processes can call this simultaneously without race conditions.
  # The BEAM guarantees the increment is atomic — no lost updates.
  # Default_value is the starting value if the key doesn't exist yet.
  def update_counter(key, increment, default_value \\ 0) do
    :ets.update_counter(__MODULE__, key, increment, {key, default_value})
  end
end
```

### ETS for Agent Status Tracking

```elixir
defmodule AgentStatusTracker do
  # This module uses ETS to track all agent statuses.
  # Agents write their status. The dashboard reads it.
  # No GenServer bottleneck — concurrent reads from the dashboard.

  # update_status/2 writes an agent's current status to ETS.
  # agent_id: string identifying the agent
  # status: map like %{status: :running, tasks: 5, started_at: ~U[2025-01-01 00:00:00Z]}
  def update_status(agent_id, status) do
    # Store with a :status prefix to namespace the key.
    # This prevents collisions with other data in the same table.
    AgentStateStore.put({:status, agent_id}, status)
  end

  # get_status/1 reads a single agent's status.
  # Returns {:ok, status_map} or :error.
  def get_status(agent_id) do
    AgentStateStore.get({:status, agent_id})
  end

  # get_all_statuses/0 returns every agent's status as a map.
  # The dashboard calls this on mount to populate the initial view.
  def get_all_statuses do
    AgentStateStore.get_all()
    |> Enum.filter(fn {{key, _value}, _v} -> match?({:status, _}, key) end)
    |> Map.new(fn {{:status, agent_id}, status} -> {agent_id, status} end)
  end

  # remove_agent/1 deletes an agent's status from ETS.
  # Called when an agent is stopped or crashes.
  def remove_agent(agent_id) do
    AgentStateStore.delete({:status, agent_id})
  end
end
```

---

## 2. `:persistent_term`: Global Persistent State

`:persistent_term` is a per-process dictionary that survives GenServer restarts. Unlike ETS, it's not
shared across processes — it's a private scratchpad for one process.

Think of it like a **sticky note** on your monitor. If your computer restarts, the note is gone.
But if just the application crashes and restarts, the note is still there.

```elixir
defmodule AgentConfigCache do
  # This module caches agent configuration in :persistent_term.
  # WHY: configuration rarely changes but is read constantly.
  # Reading from :persistent_term is a single map lookup — faster than ETS or GenServer.call.

  # put/2 stores a configuration term.
  # The key is an atom — each agent config gets its own key.
  # Any process can call this, but only the process that created
  # the term can update it (BEAM guarantee).
  def put(key, value) do
    # :persistent_term.put/2 stores the value globally.
    # All processes can read it. Only the caller can write.
    :persistent_term.put(key, value)
  end

  # get/1 retrieves a configuration term.
  # Returns the term directly (no {:ok, term} wrapper).
  # Raises KeyError if the key doesn't exist.
  # Use get/2 with a default to avoid the raise.
  def get(key, default \\ nil) do
    # :persistent_term.get/2 returns the term or the default.
    # This is O(1) — direct memory access, no copying.
    :persistent_term.get(key, default)
  end

  # delete/1 removes a term from the persistent store.
  # Only needed when you want to free memory.
  def delete(key) do
    :persistent_term.erase(key)
  end
end

# Usage:
# AgentConfigCache.put(:agent_researcher_config, %{model: "gpt-4", temperature: 0.7})
# AgentConfigCache.get(:agent_researcher_config)
# => %{model: "gpt-4", temperature: 0.7}
```

---

## 3. Ecto + Postgres: Durable Persistence

ETS and `:persistent_term` are in-memory — they die with the node. For state that must survive
node restarts, you need a database. Ecto is Elixir's database toolkit.

Think of Ecto as a **bank vault**. Your money (data) is safe even if the bank (node) catches fire.
You put money in with a deposit slip (changeset) and take it out with a withdrawal slip (query).

### Schema Definition

```elixir
defmodule AgenticPlatform.Repo do
  # Ecto.Repo is the entry point for all database operations.
  # It wraps the Postgres driver (Postgrex) and provides query functions.
  use Ecto.Repo,
    otp_app: :agentic_platform,
    adapter: Ecto.Adapters.Postgres
end

defmodule AgenticPlatform.Agents.AgentRecord do
  use Ecto.Schema

  # schema/2 defines the database table mapping.
  # "agents" is the table name. The schema maps Elixir structs to database rows.
  # timestamps() adds inserted_at and updated_at fields automatically.
  schema "agents" do
    field :agent_id, :string
    field :status, :string
    field :config, :map
    field :tasks_completed, :integer, default: 0
    field :last_error, :string
    timestamps()
  end
end
```

### Changesets for Validation

```elixir
defmodule AgenticPlatform.Agents.AgentRecord do
  # ... schema from above ...

  # A changeset is a data structure that holds:
  # 1. The original data
  # 2. The changes to apply
  # 3. Validation errors (if any)
  #
  # WHY changesets: they separate "what to change" from "whether it's valid".
  # You can validate without writing, and write only valid data.

  # insert_changeset/2 creates a changeset for new records.
  # Required fields: agent_id, status.
  # Optional fields: config, tasks_completed, last_error.
  def insert_changeset(attrs) do
    %__MODULE__{}
    |> Ecto.Changeset.cast(attrs, [:agent_id, :status, :config, :tasks_completed, :last_error])
    |> Ecto.Changeset.validate_required([:agent_id, :status])
    # validate_length prevents empty or excessively long agent IDs.
    # WHY: agent IDs are used as keys in ETS, PubSub topics, and URLs.
    # Malformed IDs cause cascading failures.
    |> Ecto.Changeset.validate_length(:agent_id, min: 1, max: 255)
    # unique_constraint prevents duplicate agent IDs in the database.
    # The database index enforces this at the storage level.
    |> Ecto.Changeset.unique_constraint(:agent_id)
  end

  # update_changeset/2 creates a changeset for existing records.
  # Takes the existing struct and the new attributes.
  # Only the provided fields are updated — others are left unchanged.
  def update_changeset(%__MODULE__{} = agent, attrs) do
    agent
    |> Ecto.Changeset.cast(attrs, [:status, :config, :tasks_completed, :last_error])
  end
end
```

### CRUD Operations

```elixir
defmodule AgenticPlatform.Agents do
  alias AgenticPlatform.Repo
  alias AgenticPlatform.Agents.AgentRecord

  # create_agent/1 inserts a new agent record into Postgres.
  # Returns {:ok, record} on success, {:error, changeset} on validation failure.
  # The changeset validation happens BEFORE the database write.
  def create_agent(attrs) do
    # |> is the pipe operator: passes the result of each function to the next.
    # AgentRecord.insert_changeset(attrs) creates the changeset.
    # Repo.insert(changeset) writes it to the database.
    %AgentRecord{}
    |> AgentRecord.insert_changeset(attrs)
    |> Repo.insert()
  end

  # get_agent/1 finds an agent by its agent_id string.
  # Returns {:ok, record} or {:error, :not_found}.
  def get_agent(agent_id) do
    # Repo.get_by/2 queries by a specific field.
    # Returns nil if not found, so we convert to {:error, :not_found}.
    case Repo.get_by(AgentRecord, agent_id: agent_id) do
      nil -> {:error, :not_found}
      record -> {:ok, record}
    end
  end

  # update_agent_status/2 updates an agent's status in the database.
  # This is called after every task completion, crash, or status change.
  # Returns {:ok, updated_record} or {:error, changeset}.
  def update_agent_status(agent_id, status) do
    case get_agent(agent_id) do
      {:ok, record} ->
        # update_changeset applies only the status change.
        # Repo.update writes the changeset to the database.
        record
        |> AgentRecord.update_changeset(%{status: status})
        |> Repo.update()

      {:error, :not_found} ->
        # Agent doesn't exist yet — create it.
        # WHY: agents can send status updates before their creation record is written.
        # This ensures we never lose status updates.
        create_agent(%{agent_id: agent_id, status: status})
    end
  end

  # list_agents/0 returns all agent records from the database.
  # Used by the dashboard to populate its initial state.
  def list_agents do
    # Repo.all/1 executes the query and returns a list of structs.
    # No arguments means "select all from agents".
    Repo.all(AgentRecord)
  end

  # delete_agent/1 removes an agent from the database.
  # Called when an agent is stopped by the user.
  def delete_agent(agent_id) do
    case get_agent(agent_id) do
      {:ok, record} -> Repo.delete(record)
      {:error, _} = error -> error
    end
  end
end
```

---

## 4. Oban: Background Jobs with Retries

Oban is a background job processing library for Elixir. It uses Postgres as its job queue — no Redis,
no additional infrastructure. Think of Oban as a **mail room** for your application: jobs go in the queue,
workers pick them up, process them, and retry if they fail.

### Why Oban Over Task.async?

| Approach | Survives crash? | Retries? | Scheduled? | Observable? |
|----------|----------------|----------|------------|-------------|
| `Task.async` | No — dies with process | No | No | No |
| `GenServer` cast | No — dies with process | Manual | No | Manual |
| **Oban job** | Yes — persisted in Postgres | Automatic (configurable) | Yes (cron, scheduled) | Yes (ObanWeb dashboard) |

### Defining a Worker

```elixir
defmodule AgenticPlatform.Workers.AgentTaskWorker do
  use Oban.Worker,
    # queue: which processing queue this worker uses.
    # Different queues can have different concurrency limits.
    queue: :agent_tasks,
    # max_attempts: how many times Oban retries a failed job before giving up.
    # Each retry uses exponential backoff (1s, 4s, 16s, ...).
    max_attempts: 3

  # perform/1 is called when Oban picks up the job.
  # args is the map of arguments passed when the job was enqueued.
  # Returns :ok on success, {:cancel, reason} to stop retries, or raises to retry.
  def perform(%Oban.Job{args: %{"agent_id" => agent_id, "task" => task}}) do
    # Log the task start for debugging.
    IO.puts("Worker starting task for #{agent_id}: #{task}")

    # Perform the actual work.
    # In a real system, this might call an LLM, run code, or make an API call.
    case process_agent_task(agent_id, task) do
      {:ok, result} ->
        # Update the agent's status in the database.
        AgenticPlatform.Agents.update_agent_status(agent_id, "completed")

        # Broadcast the result to the LiveView dashboard.
        Phoenix.PubSub.broadcast(
          AgenticPlatform.PubSub,
          "agent_events",
          {:agent_event, :task_complete, agent_id, %{result: result}}
        )

        # Return :ok to tell Oban the job succeeded.
        # Oban marks the job as "completed" and removes it from the queue.
        :ok

      {:error, reason} ->
        # Raise an error to trigger Oban's retry mechanism.
        # WHY raise and not {:cancel, reason}: we want Oban to retry.
        # {:cancel, reason} stops ALL retries — use it for permanent failures.
        # Raising allows Oban to apply exponential backoff between retries.
        raise "Task failed: #{reason}"
    end
  end

  # process_agent_task/2 is the actual work function.
  # In production, this would call your LLM or run your agent logic.
  defp process_agent_task(agent_id, task) do
    # Simulate work with a small delay.
    Process.sleep(100)
    {:ok, "Result for: #{task}"}
  end
end
```

### Enqueuing Jobs

```elixir
defmodule AgenticPlatform.JobScheduler do
  # enqueue_task/2 adds a job to the Oban queue.
  # agent_id: which agent should process this task
  # task: the task description
  #
  # Returns {:ok, %Oban.Job{}} with the job's ID.
  # The job is persisted to Postgres — it survives node restarts.
  def enqueue_task(agent_id, task) do
    # Oban.Job.new/2 creates a job struct (not yet in the queue).
    # Oban.insert/1 writes it to Postgres and makes it available for workers.
    #
    # "agent_id" and "task" must be JSON-serializable (no atoms, no PIDs, no tuples).
    # WHY: Oban stores jobs in Postgres as JSON. Only simple types survive serialization.
    %{agent_id: agent_id, task: task}
    |> AgenticPlatform.Workers.AgentTaskWorker.new()
    |> Oban.insert()
  end

  # schedule_task/3 enqueues a job to run at a specific time.
  # Useful for delayed execution: "process this task in 5 minutes".
  def schedule_task(agent_id, task, run_at) do
    %{agent_id: agent_id, task: task}
    |> AgenticPlatform.Workers.AgentTaskWorker.new(scheduled_at: run_at)
    |> Oban.insert()
  end

  # cancel_job/1 removes a pending job from the queue.
  # Only works for jobs that haven't started processing yet.
  # If the job is already running, it continues to completion.
  def cancel_job(job_id) do
    case AgenticPlatform.Repo.get(Oban.Job, job_id) do
      nil -> {:error, :not_found}
      job -> AgenticPlatform.Repo.delete(job)
    end
  end
end
```

### Oban Configuration

```elixir
# In config/config.exs or config/prod.exs:

config :agentic_platform, Oban,
  repo: AgenticPlatform.Repo,
  plugins: [
    # Stager: checks for scheduled jobs every second.
    # Without this, scheduled jobs never run.
    {Oban.Plugins.Pruner, max_age: 3600 * 24 * 7},
    # Pruner: removes completed/failed jobs older than 7 days.
    # Keeps the database from growing unbounded.
    {Oban.Plugins.Cron, crontab: [
      # Example: run a cleanup job every hour.
      # {"0 * * * *", AgenticPlatform.Workers.CleanupWorker}
    ]}
  ],
  queues: [
    # agent_tasks queue: up to 10 concurrent workers.
    # WHY 10: each worker might call an LLM (network I/O), so we can handle more than CPU cores.
    agent_tasks: 10,
    # default queue: standard concurrency for generic jobs.
    default: 5
  ]
```

---

## 5. Combining ETS + Ecto: The Two-Layer Pattern

Production agentic systems use both ETS (fast reads) and Ecto (durable writes). The pattern:

1. **Write to ETS first** — instant, in-memory update for fast reads
2. **Write to Postgres** — durable persistence that survives restarts
3. **On restart, load from Postgres into ETS** — restores the fast-read layer

```elixir
defmodule AgenticPlatform.DurableAgentState do
  # This module combines ETS (fast) with Postgres (durable).
  # Every write goes to both. Every read comes from ETS.
  # On restart, ETS is rebuilt from Postgres.

  # save_agent_state/2 writes to ETS and Postgres simultaneously.
  # ETS gives instant reads. Postgres gives crash recovery.
  def save_agent_state(agent_id, state) do
    # Write to ETS first — this is the fast path.
    AgentStateStore.put({:agent_state, agent_id}, state)

    # Write to Postgres — this is the durable path.
    # We use update_agent_status which handles the "upsert" logic
    # (insert if new, update if existing).
    AgenticPlatform.Agents.update_agent_status(agent_id, state.status)
  end

  # get_agent_state/1 reads from ETS (fast path).
  # If ETS is empty (after restart), falls back to Postgres.
  def get_agent_state(agent_id) do
    case AgentStateStore.get({:agent_state, agent_id}) do
      {:ok, state} ->
        # ETS hit — return immediately (microseconds).
        {:ok, state}

      :error ->
        # ETS miss — load from Postgres (milliseconds).
        # This happens after a node restart when ETS is empty.
        case AgenticPlatform.Agents.get_agent(agent_id) do
          {:ok, record} ->
            # Rebuild the ETS entry so future reads are fast again.
            state = %{status: record.status, tasks: record.tasks_completed}
            AgentStateStore.put({:agent_state, agent_id}, state)
            {:ok, record}

          {:error, _} = error ->
            error
        end
    end
  end

  # restore_all_agents/0 rebuilds the ETS cache from Postgres.
  # Called during application startup (in start/2 of the Application module).
  def restore_all_agents do
    AgenticPlatform.Agents.list_agents()
    |> Enum.each(fn record ->
      state = %{status: record.status, tasks: record.tasks_completed}
      AgentStateStore.put({:agent_state, record.agent_id}, state)
    end)
  end
end
```

---

## 6. Application Startup: Tying It Together

```elixir
defmodule AgenticPlatform.Application do
  use Application

  def start(_type, _args) do
    children = [
      # Database connection pool — must start before anything that uses Ecto.
      AgenticPlatform.Repo,

      # ETS-backed state store — fast reads for agent status.
      AgentStateStore,

      # Registry for agent process discovery (from Module 5).
      AgenticPlatform.AgentRegistry,

      # DynamicSupervisor for runtime agent management (from Module 5).
      AgenticPlatform.AgentPool,

      # Oban for background job processing.
      # Jobs persist in Postgres — they survive restarts.
      {Oban, Application.fetch_env!(:agentic_platform, Oban)},

      # Phoenix PubSub for real-time events.
      {Phoenix.PubSub, name: AgenticPlatform.PubSub},

      # Phoenix Endpoint for the web dashboard (from Module 6).
      AgenticPlatformWeb.Endpoint
    ]

    # Start the supervision tree.
    Supervisor.start_link(children, strategy: :one_for_one, name: AgenticPlatform.Supervisor)
  end

  # after_start/0 is called AFTER the supervision tree is up.
  # We use it to restore ETS state from Postgres.
  def after_start do
    # Rebuild the ETS cache from durable storage.
    # WHY: ETS tables are empty on a fresh start. Postgres has the durable data.
    AgenticPlatform.DurableAgentState.restore_all_agents()
  end
end
```

---

## Common Mistakes

### Mistake 1: Using `:persistent_term` for shared state

```elixir
# WRONG: :persistent_term is per-process. If two GenServers write to the same key,
# the last write wins and the first write is silently lost.
:persistent_term.put(:agent_config, %{model: "gpt-4"})  # Process A writes
:persistent_term.put(:agent_config, %{model: "gpt-3"})  # Process B overwrites!

# CORRECT: Use ETS for shared state. ETS supports concurrent writes safely.
AgentStateStore.put(:agent_config, %{model: "gpt-4"})
```

### Mistake 2: Storing non-serializable terms in Oban jobs

```elixir
# WRONG: Atoms, PIDs, and tuples can't be serialized to JSON.
# Oban stores jobs as JSON in Postgres — these values will crash the worker.
%{agent_pid: self(), ref: make_ref(), status: :running}

# CORRECT: Use only JSON-safe types: strings, numbers, maps, lists.
%{agent_id: "agent_42", task: "research Elixir"}
```

### Mistake 3: Not restoring ETS from Postgres on startup

```elixir
# WRONG: Starting the application and assuming ETS has data.
# ETS is in-memory — it's empty on every fresh start.
def start(_type, _args) do
  # ... start children ...
  # ETS is empty! All agent states are gone!
end

# CORRECT: Restore ETS from Postgres after the supervision tree starts.
def start(_type, _args) do
  children = [...]
  result = Supervisor.start_link(children, strategy: :one_for_one)
  AgenticPlatform.DurableAgentState.restore_all_agents()
  result
end
```

---

## Deep Dive: Why Postgres for Oban (Not Redis)

Many background job libraries (Sidekiq, Celery) use Redis. Oban uses Postgres. Here's why:

1. **ACID guarantees** — job creation is atomic with your application state. No "job created but data not committed" race conditions.
2. **No additional infrastructure** — you already have Postgres for Ecto. One fewer service to manage.
3. **Queryable** — `SELECT * FROM oban_jobs WHERE state = 'completed' AND inserted_at > '2025-01-01'` gives you full SQL power.
4. **Durable** — Postgres writes to disk. Redis writes to memory (with optional disk persistence that's not ACID).
5. **No data loss on crash** — Oban jobs survive node restarts because they're in Postgres, not memory.

The tradeoff: Postgres is slower than Redis for pure queue operations (~1ms vs ~0.1ms). But for most
applications, the reliability and operational simplicity outweigh the latency difference.

---

## Recap

| Technology | Speed | Durability | Use case |
|-----------|-------|------------|----------|
| ETS | Microseconds | No (in-memory) | Fast reads, shared state, caching |
| `:persistent_term` | Nanoseconds | No (per-process) | Single-process config cache |
| Ecto + Postgres | Milliseconds | Yes (on disk) | Durable persistence, queries |
| Oban + Postgres | Milliseconds | Yes (on disk) | Background jobs, retries, scheduling |

**The two-layer pattern**: ETS for speed, Postgres for durability. ETS is rebuilt from Postgres on startup.

---

**Next:** [Module 9: Advanced OTP Patterns](09-advanced-otp.md) — GenServer, Task, and advanced supervision trees.
