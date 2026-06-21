# Exercise 4: Stateful Agent with Heartbeat (OTP & GenServer)

## Learning Objectives

By completing this exercise, you will:
- Implement a GenServer with proper client/server separation
- Use handle_call for synchronous requests
- Use handle_cast for fire-and-forget messages
- Implement the heartbeat pattern with Process.send_after
- Build crash recovery with supervisors

## Scenario

You're building a stateful agent for a distributed monitoring system. The agent must:
1. Track its own state across messages
2. Send periodic heartbeats to prove liveness
3. Report health status to supervisors
4. Handle crashes gracefully with automatic restart

## Starter Code

```elixir
defmodule Monitoring.Agent do
  @moduledoc """
  TODO: A stateful monitoring agent with heartbeat.

  This agent demonstrates:
  - GenServer pattern (call, cast, info)
  - Heartbeat for periodic health checks
  - State management across messages
  - Graceful shutdown

  Usage:
      {:ok, agent} = Monitoring.Agent.start_link(name: :cpu_monitor)
      Monitoring.Agent.status(agent)
      Monitoring.Agent.stop(agent)
  """

  use GenServer

  require Logger

  # ============================================================
  # PART 1: Client API
  # ============================================================

  @doc """
  TODO: Start the agent with configuration.

  Options:
  - name: Required atom. Registered process name.
  - interval: Optional integer. Heartbeat interval in ms (default: 30_000).
  - thresholds: Optional map. Alert thresholds for metrics.

  Returns {:ok, pid} or {:error, reason}.
  """
  def start_link(opts) do
    # Your code here
    # GenServer.start_link(__MODULE__, opts, name: name)

  end

  @doc """
  TODO: Get the agent's current health status.

  Returns a map:
  %{
    status: :healthy | :degraded | :unhealthy,
    heartbeat_count: integer,
    last_heartbeat: DateTime.t() | nil,
    metrics: map(),
    uptime_seconds: integer
  }
  """
  def status(agent) do
    # Your code here
    # GenServer.call(agent, :status)

  end

  @doc """
  TODO: Report a metric value.

  Metrics are stored in state and included in health status.

  ## Examples

      iex> Monitoring.Agent.report_metric(agent, :cpu_usage, 85.5)
      :ok

  """
  def report_metric(agent, metric_name, value) do
    # Your code here
    # GenServer.cast(agent, {:report_metric, metric_name, value})

  end

  @doc """
  TODO: Get all metrics.
  """
  def get_metrics(agent) do
    # Your code here
    # GenServer.call(agent, :get_metrics)

  end

  @doc """
  TODO: Trigger a heartbeat manually (for testing).
  """
  def trigger_heartbeat(agent) do
    # Your code here
    # GenServer.cast(agent, :heartbeat)

  end

  @doc """
  TODO: Stop the agent gracefully.
  """
  def stop(agent) do
    # Your code here
    # GenServer.stop(agent, :shutdown)

  end

  # ============================================================
  # PART 2: Server Callbacks
  # ============================================================

  @doc """
  TODO: Initialize the agent state.

  State should contain:
  - name: atom
  - interval: integer (ms)
  - heartbeat_count: integer (start at 0)
  - last_heartbeat: DateTime.t() | nil
  - status: atom (:initializing, :running, :degraded, :unhealthy)
  - metrics: map (metric_name => %{value, last_updated})
  - started_at: DateTime.t()
  """
  def init(opts) do
    # Your code here

  end

  @doc """
  TODO: Handle :status call.

  Return current health status map.
  """
  def handle_call(:status, _from, state) do
    # Your code here

  end

  @doc """
  TODO: Handle :get_metrics call.

  Return all stored metrics.
  """
  def handle_call(:get_metrics, _from, state) do
    # Your code here

  end

  @doc """
  TODO: Handle {:report_metric, name, value} cast.

  Store the metric with timestamp.
  """
  def handle_cast({:report_metric, name, value}, state) do
    # Your code here

  end

  @doc """
  TODO: Handle :heartbeat cast.

  Update heartbeat count and timestamp.
  """
  def handle_cast(:heartbeat, state) do
    # Your code here

  end

  @doc """
  TODO: Handle :heartbeat info (from Process.send_after).

  Same as heartbeat cast, but also reschedule.
  """
  def handle_info(:heartbeat, state) do
    # Your code here

  end

  @doc """
  TODO: Handle unexpected messages.
  """
  def handle_info(msg, state) do
    # Your code here

  end

  @doc """
  TODO: Clean up on shutdown.
  """
  def terminate(reason, state) do
    # Your code here

  end

  # ============================================================
  # PART 3: Helper Functions
  # ============================================================

  @doc """
  TODO: Process a heartbeat (shared logic for cast and info).

  Should:
  1. Increment heartbeat_count
  2. Update last_heartbeat to DateTime.utc_now()
  3. Set status to :running
  4. Log the heartbeat
  """
  defp process_heartbeat(state) do
    # Your code here

  end

  @doc """
  TODO: Check if any metrics exceed thresholds.

  Returns :healthy, :degraded, or :unhealthy based on thresholds.
  """
  defp check_health(state) do
    # Your code here

  end
end
```

## Hints

### Part 1: Client API
- Use `GenServer.start_link/3` with `name: name` for registration
- Use `GenServer.call/2` for synchronous requests (blocks until response)
- Use `GenServer.cast/2` for fire-and-forget (returns immediately)
- Use `GenServer.stop/3` with `:shutdown` for graceful termination

### Part 2: Server Callbacks
- `init/1` must return `{:ok, state}` — don't block here
- `handle_call/3` must return `{:reply, response, new_state}`
- `handle_cast/2` must return `{:noreply, new_state}`
- `handle_info/2` must return `{:noreply, new_state}`
- Use `Process.send_after(self(), :heartbeat, interval)` to schedule

### Part 3: Helper Functions
- Use pattern matching to check thresholds
- Return atoms for status (:healthy, :degraded, :unhealthy)
- Log with `Logger.debug/info/warning/error`

## Test Cases

```elixir
# Start an agent
{:ok, agent} = Monitoring.Agent.start_link(
  name: :test_agent,
  interval: 1000,  # 1 second for testing
  thresholds: %{cpu: 90.0, memory: 85.0}
)

# Check initial status
status = Monitoring.Agent.status(agent)
status.status == :initializing
status.heartbeat_count == 0
status.last_heartbeat == nil

# Report metrics
Monitoring.Agent.report_metric(agent, :cpu_usage, 75.0)
Monitoring.Agent.report_metric(agent, :memory_usage, 60.0)

# Get metrics
metrics = Monitoring.Agent.get_metrics(agent)
metrics[:cpu_usage].value == 75.0

# Wait for heartbeat
Process.sleep(1100)

# Check status after heartbeat
status = Monitoring.Agent.status(agent)
status.status == :running
status.heartbeat_count == 1
status.last_heartbeat != nil

# Report high metric
Monitoring.Agent.report_metric(agent, :cpu_usage, 95.0)

# Check health (should be unhealthy)
status = Monitoring.Agent.status(agent)
status.status == :unhealthy

# Stop the agent
Monitoring.Agent.stop(agent)
```

## Solution

<details>
<summary>Click to reveal solution</summary>

```elixir
defmodule Monitoring.Agent do
  @moduledoc """
  A stateful monitoring agent with heartbeat.
  """

  use GenServer

  require Logger

  @default_interval 30_000

  # Client API

  def start_link(opts) do
    name = Keyword.fetch!(opts, :name)
    GenServer.start_link(__MODULE__, opts, name: name)
  end

  def status(agent) do
    GenServer.call(agent, :status)
  end

  def report_metric(agent, metric_name, value) do
    GenServer.cast(agent, {:report_metric, metric_name, value})
  end

  def get_metrics(agent) do
    GenServer.call(agent, :get_metrics)
  end

  def trigger_heartbeat(agent) do
    GenServer.cast(agent, :heartbeat)
  end

  def stop(agent) do
    GenServer.stop(agent, :shutdown)
  end

  # Server Callbacks

  @impl true
  def init(opts) do
    name = Keyword.fetch!(opts, :name)
    interval = Keyword.get(opts, :interval, @default_interval)
    thresholds = Keyword.get(opts, :thresholds, %{})

    # Schedule first heartbeat
    Process.send_after(self(), :heartbeat, interval)

    state = %{
      name: name,
      interval: interval,
      thresholds: thresholds,
      heartbeat_count: 0,
      last_heartbeat: nil,
      status: :initializing,
      metrics: %{},
      started_at: DateTime.utc_now()
    }

    Logger.info("Agent '#{name}' started with interval #{interval}ms")
    {:ok, state}
  end

  @impl true
  def handle_call(:status, _from, state) do
    health_status = check_health(state)

    status = %{
      status: health_status,
      heartbeat_count: state.heartbeat_count,
      last_heartbeat: state.last_heartbeat,
      metrics: Map.new(state.metrics, fn {k, v} -> {k, v.value} end),
      uptime_seconds: DateTime.diff(DateTime.utc_now(), state.started_at)
    }

    {:reply, status, state}
  end

  @impl true
  def handle_call(:get_metrics, _from, state) do
    {:reply, state.metrics, state}
  end

  @impl true
  def handle_cast({:report_metric, name, value}, state) do
    metrics = Map.put(state.metrics, name, %{
      value: value,
      last_updated: DateTime.utc_now()
    })

    Logger.debug("Metric #{name}: #{value}")
    {:noreply, %{state | metrics: metrics}}
  end

  @impl true
  def handle_cast(:heartbeat, state) do
    new_state = process_heartbeat(state)
    {:noreply, new_state}
  end

  @impl true
  def handle_info(:heartbeat, state) do
    new_state = process_heartbeat(state)
    {:noreply, new_state}
  end

  @impl true
  def handle_info(msg, state) do
    Logger.warning("Unexpected message: #{inspect(msg)}")
    {:noreply, state}
  end

  @impl true
  def terminate(reason, state) do
    Logger.info("Agent '#{state.name}' stopping: #{inspect(reason)}")
    :ok
  end

  # Helper Functions

  defp process_heartbeat(state) do
    Logger.debug("Heartbeat #{state.heartbeat_count + 1} from '#{state.name}'")

    # Schedule next heartbeat
    Process.send_after(self(), :heartbeat, state.interval)

    %{state |
      heartbeat_count: state.heartbeat_count + 1,
      last_heartbeat: DateTime.utc_now(),
      status: :running
    }
  end

  defp check_health(state) do
    # Check if any metrics exceed thresholds
    exceeded = Enum.any?(state.metrics, fn {metric, data} ->
      threshold = Map.get(state.thresholds, metric)
      threshold != nil and data.value > threshold
    end)

    cond do
      state.status == :error -> :unhealthy
      state.heartbeat_count == 0 -> :initializing
      state.last_heartbeat == nil -> :degraded
      exceeded -> :unhealthy
      true -> :healthy
    end
  end
end
```

</details>

## Common Mistakes to Avoid

1. **Not scheduling next heartbeat**: `Process.send_after` only fires once
2. **Blocking in init**: Keep init fast — no HTTP calls or file I/O
3. **Using call for fire-and-forget**: Use cast when you don't need a response
4. **Forgetting terminate**: Clean up resources in terminate/2
5. **Not handling unexpected messages**: Always have a catch-all handle_info

## Extension Challenges

1. **Add persistence**: Save metrics to ETS or DETS for crash recovery
2. **Add alerts**: Send notifications when thresholds are exceeded
3. **Add distributed support**: Use Swarm for process migration
4. **Add REST API**: HTTP endpoints to query agent status
5. **Add metrics export**: Prometheus-compatible metrics endpoint

## Deep Dive: Supervisor Tree

In production, agents live under supervisors:

```elixir
defmodule Monitoring.Supervisor do
  use Supervisor

  def start_link(opts) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(opts) do
    agents = Keyword.get(opts, :agents, [])

    children = Enum.map(agents, fn agent_opts ->
      %{
        id: agent_opts[:name],
        start: {Monitoring.Agent, :start_link, [agent_opts]},
        restart: :permanent,  # Always restart
        shutdown: 5000,       # 5 seconds to stop
        type: :worker
      }
    end)

    Supervisor.init(children, strategy: :one_for_one)
  end
end

# Usage
{:ok, _} = Monitoring.Supervisor.start_link(agents: [
  [name: :cpu_monitor, interval: 5000],
  [name: :memory_monitor, interval: 10000],
  [name: :disk_monitor, interval: 30000]
])
```

The supervisor ensures:
- **Automatic restart**: If an agent crashes, it's restarted
- **Ordered startup**: Agents start in the order listed
- **Graceful shutdown**: Agents are stopped in reverse order

---

## Grading Checklist

- [ ] start_link accepts name and interval options
- [ ] start_link registers the process by name
- [ ] status returns health map with all required fields
- [ ] report_metric stores metric with timestamp
- [ ] get_metrics returns all stored metrics
- [ ] trigger_heartbeat triggers heartbeat manually
- [ ] stop terminates gracefully
- [ ] init schedules first heartbeat
- [ ] init returns {:ok, state} with all required fields
- [ ] handle_call(:status) returns health status
- [ ] handle_call(:get_metrics) returns metrics map
- [ ] handle_cast({:report_metric, ...}) stores metric
- [ ] handle_cast(:heartbeat) updates heartbeat count
- [ ] handle_info(:heartbeat) reschedules next heartbeat
- [ ] handle_info(msg) logs unexpected messages
- [ ] terminate logs shutdown reason
- [ ] process_heartbeat increments count and updates timestamp
- [ ] check_health evaluates thresholds correctly

---

## Course Complete!

Congratulations! You've completed all 4 modules:

1. **Go Fundamentals**: Types, structs, interfaces, error handling
2. **Go CLI & HTTP**: Cobra, net/http, middleware, graceful shutdown
3. **Elixir Fundamentals**: Pattern matching, pipes, immutability
4. **OTP & GenServer**: Stateful processes, heartbeats, supervisors

### What You've Built

- Module 1: CLI weather tool
- Module 2: Health-check API with middleware
- Module 3: Data processing pipeline
- Module 4: Stateful agent with heartbeat

### Next Steps

1. **Build a hybrid application**: Elixir frontend + Go backend
2. **Explore Phoenix LiveView**: Real-time UIs without JavaScript
3. **Deploy with Kubernetes**: Use the health checks you built
4. **Add observability**: Prometheus metrics, OpenTelemetry tracing

### Resources

- [Elixir Getting Started](https://elixir-lang.org/getting-started/introduction.html)
- [Go by Example](https://gobyexample.com/)
- [Phoenix Framework](https://www.phoenixframework.org/)
- [OTP Documentation](https://hexdocs.pm/elixir/otp-and-its-applications.html)
