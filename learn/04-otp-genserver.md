# Module 4: OTP & GenServer (Week 4)

## Learning Objectives

By the end of this module, you will:
- Understand GenServer as the atomic unit of an agent
- Implement start_link, init, handle_call, handle_cast
- Use supervisors for automatic crash recovery
- Build a stateful agent with heartbeat
- Understand why Discord and Jido use this pattern

## 1. The Process Model

Before GenServer, understand what a process is in Elixir:

```elixir
# A process is lightweight, isolated, and concurrent
# Processes communicate via messages — no shared memory

# Spawn a new process
pid = spawn(fn ->
  receive do
    {:hello, sender} ->
      send(sender, {:world, self()})
  end
end)

# Send a message to the process
send(pid, {:hello, self()})

# Receive the response
receive do
  {:world, from} -> IO.puts("Got response from #{inspect(from)}")
after
  1000 -> IO.puts("Timeout!")
end

# DEEP DIVE: Why processes?
# - Isolation: One process crashing doesn't affect others
# - Concurrency: Millions of processes can run simultaneously
# - Distribution: Processes can span multiple machines
# - No locks: Messages are copied, not shared

# COMMON MISTAKE: Using processes directly
# Raw processes are low-level — use GenServer for state management
# GenServer handles the boilerplate (timeouts, state passing, etc.)
```

## 2. GenServer: The State Machine

GenServer is a generic server — a process that:
1. Holds state
2. Receives messages
3. Responds to requests
4. Can be supervised and restarted

Think of it as a **mailbox with memory**.

### The Simplest GenServer

```elixir
defmodule WeatherAgent do
  @moduledoc """
  A simple weather agent that stores the latest reading.

  This demonstrates the MINIMUM GenServer structure:
  - start_link/1: How to start the process
  - init/1: How to initialize state
  - handle_call/3: How to handle synchronous requests
  - handle_cast/2: How to handle fire-and-forget messages
  """

  use GenServer

  # ============================================================
  # Client API (what other code calls)
  # ============================================================

  @doc """
  Starts the agent under a supervisor.

  ## Options

  * `:name` - Registered name for the process
  * `:initial_city` - City to monitor initially

  ## Examples

      iex> WeatherAgent.start_link(name: :weather, initial_city: "Seattle")
      {:ok, #PID<0.123.0>}

  """
  def start_link(opts \\ []) do
    # GenServer.start_link/2 starts the process and links it to the caller
    # If the caller crashes, this process crashes too (for supervision)
    name = Keyword.get(opts, :name, __MODULE__)

    GenServer.start_link(__MODULE__, opts, name: name)
  end

  @doc """
  Gets the current weather reading.

  This is a SYNCHRONOUS call — it blocks until the agent responds.

  Returns {:ok, reading} or {:error, reason}.
  """
  def get_reading(agent \\ __MODULE__) do
    # GenServer.call/2 sends a message and waits for a response
    # This is like calling a function — it blocks
    GenServer.call(agent, :get_reading)
  end

  @doc """
  Updates the weather reading.

  This is ASYNCHRONOUS — it returns immediately.
  """
  def update_reading(agent \\ __MODULE__, reading) do
    # GenServer.cast/2 sends a message without waiting
    # This is like sending a letter — no reply expected
    GenServer.cast(agent, {:update, reading})
  end

  @doc """
  Gets the agent's status information.

  Returns a map with metadata about the agent.
  """
  def status(agent \\ __MODULE__) do
    GenServer.call(agent, :status)
  end

  # ============================================================
  # Server Callbacks (what the process runs)
  # ============================================================

  @doc """
  Initializes the agent with starting state.

  Called once when the process starts.
  Returns {:ok, initial_state} or {:stop, reason}.
  """
  def init(opts) do
    initial_city = Keyword.get(opts, :initial_city, "Unknown")

    # The state is a map — it can hold anything
    # This state is passed to every subsequent callback
    initial_state = %{
      city: initial_city,
      temperature: nil,
      condition: nil,
      humidity: nil,
      last_updated: nil,
      update_count: 0
    }

    IO.puts("WeatherAgent initialized for #{initial_city}")

    {:ok, initial_state}
  end

  @doc """
  Handles synchronous requests (call).

  The client blocks until this returns.

  Callback receives:
  - request: The message sent by GenServer.call
  - from: {caller_pid, reference}
  - state: Current state

  Returns {:reply, response, new_state}
  """
  def handle_call(:get_reading, _from, state) do
    reading = %{
      city: state.city,
      temperature: state.temperature,
      condition: state.condition,
      humidity: state.humidity,
      last_updated: state.last_updated
    }

    # {:reply, response, new_state}
    # The response is sent back to the caller
    # The new_state replaces the old state
    {:reply, {:ok, reading}, state}
  end

  def handle_call(:status, _from, state) do
    status = %{
      city: state.city,
      update_count: state.update_count,
      has_data: state.temperature != nil
    }

    {:reply, status, state}
  end

  @doc """
  Handles asynchronous requests (cast).

  The client does NOT block — it continues immediately.

  Callback receives:
  - request: The message sent by GenServer.cast
  - state: Current state

  Returns {:noreply, new_state}
  """
  def handle_cast({:update, reading}, state) do
    # Update the state with the new reading
    new_state = %{
      state |
      temperature: reading.temperature,
      condition: reading.condition,
      humidity: reading.humidity,
      last_updated: DateTime.utc_now(),
      update_count: state.update_count + 1
    }

    IO.puts("Updated #{state.city}: #{reading.temperature}°F")

    # {:noreply, new_state}
    # No response to client — just update state
    {:noreply, new_state}
  end

  @doc """
  Handles code reloading (hot code upgrade).

  Called when the module is recompiled while the process is running.
  """
  def code_change(old_state) do
    # Migrate old state to new format if needed
    # For now, just return the state as-is
    {:ok, old_state}
  end
end
```

### Using the GenServer

```elixir
defmodule WeatherDemo do
  def run do
    # Start the agent
    {:ok, agent} = WeatherAgent.start_link(
      name: :demo_weather,
      initial_city: "Seattle"
    )

    # Check initial status
    IO.inspect(WeatherAgent.status(agent), label: "Initial status")

    # Update with new reading (async — returns immediately)
    WeatherAgent.update_reading(agent, %{
      temperature: 55.0,
      condition: "Rain",
      humidity: 80.0
    })

    # Give it a moment to process
    Process.sleep(100)

    # Get the reading (sync — blocks until response)
    case WeatherAgent.get_reading(agent) do
      {:ok, reading} ->
        IO.puts("Current: #{reading.city} - #{reading.temperature}°F")

      {:error, reason} ->
        IO.puts("Error: #{reason}")
    end

    # Check status after update
    IO.inspect(WeatherAgent.status(agent), label: "After update")

    # Stop the agent gracefully
    GenServer.stop(agent)
  end
end
```

## 3. The Heartbeat Pattern

Agents often need to do periodic work (health checks, metrics, cleanup). The heartbeat pattern handles this.

```elixir
defmodule HeartbeatAgent do
  @moduledoc """
  An agent with a heartbeat timer.

  Demonstrates:
  - Periodic messages using Process.send_after
  - State tracking for health checks
  - Crash recovery via supervisor
  """

  use GenServer

  # Heartbeat interval (30 seconds)
  @heartbeat_interval 30_000

  # Client API

  def start_link(opts \\ []) do
    name = Keyword.get(opts, :name, __MODULE__)
    GenServer.start_link(__MODULE__, opts, name: name)
  end

  def get_status(agent \\ __MODULE__) do
    GenServer.call(agent, :status)
  end

  def stop(agent \\ __MODULE__) do
    GenServer.stop(agent, :normal)
  end

  # Server Callbacks

  def init(opts) do
    interval = Keyword.get(opts, :interval, @heartbeat_interval)

    # Schedule the first heartbeat
    # Process.send_after sends a message after a delay
    # This is how we create periodic behavior
    Process.send_after(self(), :heartbeat, interval)

    state = %{
      interval: interval,
      heartbeat_count: 0,
      last_heartbeat: nil,
      status: :running
    }

    {:ok, state}
  end

  def handle_call(:status, _from, state) do
    status = %{
      status: state.status,
      heartbeat_count: state.heartbeat_count,
      last_heartbeat: state.last_heartbeat,
      uptime: calculate_uptime(state)
    }

    {:reply, status, state}
  end

  @doc """
  Handles the heartbeat message.

  This is called periodically by Process.send_after.
  """
  def handle_info(:heartbeat, state) do
    # Do periodic work here
    IO.puts("Heartbeat #{state.heartbeat_count + 1}: #{DateTime.utc_now()}")

    # Update state
    new_state = %{
      state |
      heartbeat_count: state.heartbeat_count + 1,
      last_heartbeat: DateTime.utc_now()
    }

    # Schedule the next heartbeat
    # COMMON MISTAKE: Forgetting to reschedule
    # Without this, you only get ONE heartbeat
    Process.send_after(self(), :heartbeat, state.interval)

    {:noreply, new_state}
  end

  def handle_info(msg, state) do
    # Handle unexpected messages
    IO.puts("Unexpected message: #{inspect(msg)}")
    {:noreply, state}
  end

  defp calculate_uptime(state) do
    case state.last_heartbeat do
      nil -> "Not started"
      last ->
        diff = DateTime.diff(DateTime.utc_now(), last, :second)
        "#{diff} seconds since last heartbeat"
    end
  end
end
```

## 4. Supervisors: Crash Recovery

Supervisors are processes that monitor other processes and restart them when they crash.

```elixir
defmodule Weather.Supervisor do
  @moduledoc """
  Supervises weather agents.

  The supervisor ensures agents are always running.
  If an agent crashes, it's automatically restarted.

  This is the "let it crash" philosophy:
  - Don't handle every error
  - Let the process crash
  - The supervisor restarts it with fresh state
  """

  use Supervisor

  def start_link(opts \\ []) do
    # Start the supervisor
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(opts) do
    # Define child processes to supervise
    children = [
      # WeatherAgent with initial configuration
      {WeatherAgent, Keyword.get(opts, :weather_opts, [])},

      # HeartbeatAgent with 30-second interval
      {HeartbeatAgent, Keyword.get(opts, :heartbeat_opts, [])}
    ]

    # Supervisor strategies:
    # :one_for_one - Restart only the failed child
    # :one_for_all - Restart all children if one fails
    # :rest_for_one - Restart the failed child and all children started after it

    # COMMON MISTAKE: Wrong strategy for your use case
    # :one_for_one is usually correct for independent processes
    # :one_for_all is for tightly coupled processes
    Supervisor.init(children, strategy: :one_for_one)
  end
end

# Usage
defmodule Weather.Application do
  use Application

  @impl true
  def start(_type, _args) do
    # Start the supervision tree
    children = [
      Weather.Supervisor
    ]

    # Supervisor.start_link starts the tree and monitors all children
    opts = [strategy: :one_for_one, name: Weather.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
```

## 5. Named Processes with via_tuple

In distributed systems, you need to find processes by name, not just PID.

```elixir
defmodule Weather.NamedAgent do
  @moduledoc """
  An agent that registers with a human-readable name.

  Uses via_tuple for named process registration.
  This is essential for distributed systems where PIDs change.
  """

  use GenServer

  # Client API

  def start_link(name) do
    # Register the process with a name
    # The name is global — can be found from any process
    GenServer.start_link(__MODULE__, name, name: {:via, Registry, {WeatherRegistry, name}})
  end

  def get_reading(name) do
    # Find the process by name
    # COMMON MISTAKE: Not handling process not found
    case Registry.lookup(WeatherRegistry, name) do
      [{pid, _}] ->
        GenServer.call(pid, :get_reading)

      [] ->
        {:error, :not_found}
    end
  end

  # Server Callbacks

  def init(name) do
    state = %{
      name: name,
      temperature: nil,
      last_updated: nil
    }

    IO.puts("NamedAgent '#{name}' started")
    {:ok, state}
  end

  def handle_call(:get_reading, _from, state) do
    {:reply, {:ok, state}, state}
  end
end

# Start a registry for named processes
defmodule Weather.Registry do
  use Registry

  def start_link(_opts) do
    Registry.start_link(keys: :unique, name: __MODULE__)
  end
end
```

## 6. Real-World Pattern: Agent with Heartbeat

This is how Discord and Jido implement agents:

```elixir
defmodule Agent.Heartbeat do
  @moduledoc """
  A production-grade agent with heartbeat and health monitoring.

  This pattern is used by:
  - Discord for WebSocket connection agents
  - Jido for autonomous agent processes
  - Kubernetes for pod health checks

  Key features:
  - Periodic heartbeat to prove liveness
  - State tracking for health checks
  - Graceful shutdown
  - Crash recovery via supervisor
  """

  use GenServer

  require Logger

  @heartbeat_interval 30_000  # 30 seconds
  @health_check_timeout 5_000 # 5 seconds

  # Client API

  def start_link(opts \\ []) do
    name = Keyword.fetch!(opts, :name)
    GenServer.start_link(__MODULE__, opts, name: name)
  end

  def health_check(agent, timeout \\ @health_check_timeout) do
    try do
      GenServer.call(agent, :health_check, timeout)
    catch
      :exit, _ -> {:error, :timeout}
    end
  end

  def stop(agent) do
    GenServer.stop(agent, :shutdown)
  end

  # Server Callbacks

  @impl true
  def init(opts) do
    name = Keyword.fetch!(opts, :name)
    interval = Keyword.get(opts, :heartbeat_interval, @heartbeat_interval)

    # Schedule first heartbeat
    Process.send_after(self(), :heartbeat, interval)

    state = %{
      name: name,
      interval: interval,
      heartbeat_count: 0,
      last_heartbeat: nil,
      status: :initializing,
      started_at: DateTime.utc_now(),
      errors: []
    }

    Logger.info("Agent '#{name}' started")

    {:ok, state}
  end

  @impl true
  def handle_call(:health_check, _from, state) do
    health = %{
      status: state.status,
      heartbeat_count: state.heartbeat_count,
      last_heartbeat: state.last_heartbeat,
      uptime_seconds: DateTime.diff(DateTime.utc_now(), state.started_at),
      error_count: length(state.errors)
    }

    # Determine overall health
    status = cond do
      state.status == :error -> :unhealthy
      state.heartbeat_count == 0 -> :starting
      state.last_heartbeat == nil -> :degraded
      true -> :healthy
    end

    {:reply, %{health | status: status}, state}
  end

  @impl true
  def handle_info(:heartbeat, state) do
    # Perform heartbeat work
    # In real agents: send ping, check connections, update metrics
    Logger.debug("Heartbeat #{state.heartbeat_count + 1}")

    new_state = %{state |
      heartbeat_count: state.heartbeat_count + 1,
      last_heartbeat: DateTime.utc_now(),
      status: :running
    }

    # Schedule next heartbeat
    Process.send_after(self(), :heartbeat, state.interval)

    {:noreply, new_state}
  end

  @impl true
  def handle_info(:check_health, state) do
    # Internal health check
    # Could check database, network, etc.
    {:noreply, state}
  end

  @impl true
  def terminate(reason, state) do
    Logger.info("Agent '#{state.name}' stopping: #{inspect(reason)}")
    :ok
  end
end
```

## 7. Complete Example: Weather Monitoring System

```elixir
defmodule Weather.Monitor do
  @moduledoc """
  A complete weather monitoring system with:
  - Multiple named agents
  - Supervisor for crash recovery
  - Heartbeat for health monitoring
  - REST API for querying
  """

  use GenServer

  # Client API

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def register_station(name, config) do
    GenServer.call(__MODULE__, {:register, name, config})
  end

  def get_station(name) do
    GenServer.call(__MODULE__, {:get, name})
  end

  def list_stations do
    GenServer.call(__MODULE__, :list)
  end

  # Server Callbacks

  def init(_opts) do
    state = %{
      stations: %{},
      last_heartbeat: DateTime.utc_now()
    }

    # Start heartbeat
    Process.send_after(self(), :heartbeat, 30_000)

    {:ok, state}
  end

  def handle_call({:register, name, config}, _from, state) do
    # Start a new agent for this station
    case Weather.NamedAgent.start_link(name) do
      {:ok, _pid} ->
        new_stations = Map.put(state.stations, name, config)
        {:reply, :ok, %{state | stations: new_stations}}

      {:error, reason} ->
        {:reply, {:error, reason}, state}
    end
  end

  def handle_call({:get, name}, _from, state) do
    case Map.get(state.stations, name) do
      nil -> {:reply, {:error, :not_found}, state}
      config -> {:reply, {:ok, config}, state}
    end
  end

  def handle_call(:list, _from, state) do
    {:reply, Map.keys(state.stations), state}
  end

  def handle_info(:heartbeat, state) do
    # Periodic maintenance
    Logger.debug("Monitor heartbeat")

    Process.send_after(self(), :heartbeat, 30_000)

    {:noreply, %{state | last_heartbeat: DateTime.utc_now()}}
  end
end
```

## Summary

| Concept | Key Point | Common Mistake |
|---------|-----------|----------------|
| GenServer | Stateful process with callbacks | Using raw processes |
| start_link | Starts and links to caller | Not using under supervisor |
| init | Returns {:ok, state} | Blocking in init |
| handle_call | Synchronous request-reply | Long-running operations |
| handle_cast | Fire-and-forget | Expecting response |
| Supervisor | Automatic crash recovery | Wrong strategy |
| Heartbeat | Periodic health checks | Forgetting to reschedule |

## Next Steps

- Exercise 4: Build a stateful agent with heartbeat
- Exercise 4: Implement supervisor for crash recovery
- Exercise 4: Add health check endpoints

---

## Exercise: Stateful Agent with Heartbeat

### Starter Code

```elixir
defmodule Agent.Heartbeat do
  @moduledoc """
  TODO: Build a stateful agent with heartbeat monitoring.

  This agent should:
  - Track state across messages
  - Send periodic heartbeats
  - Report health status
  - Handle crashes gracefully
  """

  use GenServer

  # ============================================================
  # PART 1: Client API
  # ============================================================

  @doc """
  TODO: Start the agent with a name and optional interval.

  Options:
  - name: Required. The agent's registered name.
  - heartbeat_interval: Optional. Default 30_000ms.

  Returns {:ok, pid} or {:error, reason}.
  """
  def start_link(opts) do
    # Your code here
    # Use GenServer.start_link/3 with Registry for named processes

  end

  @doc """
  TODO: Get the agent's current status.

  Returns a map with:
  - status: :healthy | :degraded | :unhealthy
  - heartbeat_count: integer
  - last_heartbeat: DateTime.t() | nil
  - uptime_seconds: integer
  """
  def status(agent) do
    # Your code here
    # Use GenServer.call/2 for synchronous request

  end

  @doc """
  TODO: Send a heartbeat manually.

  This triggers the same logic as the automatic heartbeat.
  """
  def heartbeat(agent) do
    # Your code here
    # Use GenServer.cast/2 for fire-and-forget

  end

  @doc """
  TODO: Stop the agent gracefully.
  """
  def stop(agent) do
    # Your code here
    # Use GenServer.stop/3 with :normal reason

  end

  # ============================================================
  # PART 2: Server Callbacks
  # ============================================================

  @doc """
  TODO: Initialize the agent state.

  Should:
  - Store the agent's name
  - Initialize heartbeat_count to 0
  - Set last_heartbeat to nil
  - Set status to :initializing
  - Schedule first heartbeat
  """
  def init(opts) do
    # Your code here

  end

  @doc """
  TODO: Handle status request.

  Should return a map with current status information.
  """
  def handle_call(:status, _from, state) do
    # Your code here

  end

  @doc """
  TODO: Handle heartbeat trigger.

  Should:
  - Increment heartbeat_count
  - Update last_heartbeat to now
  - Set status to :running
  - Schedule next heartbeat
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
end
```

### Hints

1. **start_link**: Use `GenServer.start_link(__MODULE__, opts, name: name)`
2. **init**: Use `Process.send_after(self(), :heartbeat, interval)` to schedule
3. **handle_call**: Return `{:reply, response, new_state}`
4. **handle_cast**: Return `{:noreply, new_state}`
5. **handle_info**: Return `{:noreply, new_state}`

### Solution

<details>
<summary>Click to reveal solution</summary>

```elixir
defmodule Agent.Heartbeat do
  @moduledoc """
  A stateful agent with heartbeat monitoring.
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

  def heartbeat(agent) do
    GenServer.cast(agent, :heartbeat)
  end

  def stop(agent) do
    GenServer.stop(agent, :normal)
  end

  # Server Callbacks

  @impl true
  def init(opts) do
    name = Keyword.fetch!(opts, :name)
    interval = Keyword.get(opts, :heartbeat_interval, @default_interval)

    # Schedule first heartbeat
    Process.send_after(self(), :heartbeat, interval)

    state = %{
      name: name,
      interval: interval,
      heartbeat_count: 0,
      last_heartbeat: nil,
      status: :initializing,
      started_at: DateTime.utc_now()
    }

    Logger.info("Agent '#{name}' started")
    {:ok, state}
  end

  @impl true
  def handle_call(:status, _from, state) do
    health_status = cond do
      state.status == :error -> :unhealthy
      state.heartbeat_count == 0 -> :starting
      state.last_heartbeat == nil -> :degraded
      true -> :healthy
    end

    status = %{
      status: health_status,
      heartbeat_count: state.heartbeat_count,
      last_heartbeat: state.last_heartbeat,
      uptime_seconds: DateTime.diff(DateTime.utc_now(), state.started_at)
    }

    {:reply, status, state}
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

  defp process_heartbeat(state) do
    Logger.debug("Heartbeat #{state.heartbeat_count + 1}")

    # Schedule next heartbeat
    Process.send_after(self(), :heartbeat, state.interval)

    %{state |
      heartbeat_count: state.heartbeat_count + 1,
      last_heartbeat: DateTime.utc_now(),
      status: :running
    }
  end
end
```

</details>

## Common Mistakes to Avoid

1. **Not using supervisors**: Always put GenServers under a supervisor
2. **Forgetting to reschedule heartbeats**: Process.send_after only fires once
3. **Blocking in init**: Keep init fast — don't make HTTP calls
4. **Using call for fire-and-forget**: Use cast when you don't need a response
5. **Not handling terminate**: Clean up resources in terminate/2

## Extension Challenges

1. **Add metrics tracking**: Count messages, track response times
2. **Add persistence**: Save state to disk on heartbeat
3. **Add distributed support**: Use Swarm for process migration
4. **Add REST API**: HTTP endpoints to query agent status

## Deep Dive: Why GenServer?

GenServer solves the hardest problems in concurrent programming:

1. **State management**: State is isolated in the process — no race conditions
2. **Crash recovery**: Supervisors restart failed processes automatically
3. **Distribution**: Processes can span multiple machines
4. **Scalability**: Millions of lightweight processes

This is why:
- **Discord** uses GenServer for every WebSocket connection
- **Jido** uses GenServer for every autonomous agent
- **Phoenix** uses GenServer for every channel connection

---

## Quiz

1. What's the difference between `call` and `cast`?
   - Answer: Call is synchronous (waits for response), cast is async (fire-and-forget)

2. What does `{:reply, response, new_state}` return?
   - Answer: Sends response to caller, updates state

3. Why use supervisors?
   - Answer: Automatic crash recovery — failed processes are restarted

4. What's the heartbeat pattern?
   - Answer: Periodic messages using Process.send_after for health monitoring

5. Why use named processes?
   - Answer: Find processes by name instead of PID — essential for distribution

---

## Resources

- [GenServer Documentation](https://hexdocs.pm/elixir/GenServer.html)
- [OTP in Elixir](https://elixir-lang.org/getting-started/mix-otp/agents.html)
- [Supervision Trees](https://elixir-lang.org/getting-started/mix-otp/supervisor-and-application.html)

---

## Course Complete!

You've learned:
- **Module 1**: Go fundamentals (types, structs, interfaces)
- **Module 2**: Go CLI & HTTP (Cobra, net/http, middleware)
- **Module 3**: Elixir fundamentals (pattern matching, pipes, immutability)
- **Module 4**: OTP & GenServer (stateful processes, supervisors)

Next steps:
1. Build a hybrid Elixir/Go application
2. Explore Phoenix LiveView for real-time UIs
3. Deploy with Kubernetes and observe with Prometheus
