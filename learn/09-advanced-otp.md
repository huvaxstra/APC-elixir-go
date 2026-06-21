# Module 9: Advanced OTP Patterns (Week 9)

## What You'll Learn This Module

By the end of this module, you'll understand four advanced OTP patterns that power production agent systems:

1. **`:gen_statem`** — a state machine behaviour for agents with complex lifecycle transitions
2. **`Task.Supervisor`** — supervised async tasks for fire-and-forget work
3. **`GenStage`** — producer-consumer pipelines with automatic backpressure
4. **`Broadway`** — a high-level data pipeline abstraction built on GenStage

These patterns are not theoretical. Dashbit uses Broadway for event ingestion at scale. Discord uses GenStage-style backpressure to handle millions of messages. Every production agent system needs at least one of these patterns.

---

## The Problem: GenServer Is Not Enough

In Module 4, you learned GenServer as the agent unit. GenServer is excellent for request-response patterns: receive a message, update state, reply. But real agent systems have three problems GenServer does not solve well:

1. **Complex state transitions** — an agent that moves between "idle", "planning", "executing", "reviewing", and "blocked" needs explicit state validation. GenServer gives you `handle_call`/`handle_cast` but no built-in way to say "you cannot go from idle to reviewing without passing through planning first."

2. **Unbounded async work** — spawning tasks with `Task.start_link` works for small loads, but what happens when 10,000 events arrive and your consumer can only process 100/sec? You need backpressure.

3. **Stream processing** — when you need to transform a stream of events through multiple stages (parse → validate → enrich → persist), GenServer forces you to build the pipeline manually.

Advanced OTP patterns solve all three.

---

## Pattern 1: `:gen_statem` — State Machine Behaviour

### What Is a State Machine?

Think of a traffic light. It has three states: red, yellow, green. It transitions between them in a fixed order. You cannot go from red directly to green — you must pass through yellow. A state machine enforces this rule.

An agent is like a traffic light for work. It has states like "idle", "planning", "executing", "reviewing". The state machine enforces that an agent cannot skip the planning step and jump straight to executing.

### `:gen_statem` vs GenServer

GenServer gives you one state variable that you pattern match on in each callback. You *can* build state machines with GenServer, but you have to enforce the rules yourself. `:gen_statem` makes the state machine first-class:

- Each state has its own set of allowed events
- Transitions are explicit and validated
- You get callbacks per state, not per message type

### How `:gen_statem` Works

`:gen_statem` is an Erlang behaviour. You implement callbacks that return what happens next. The key callback is `callback_mode/0` which tells the state machine how to dispatch events.

```elixir
# DEEP DIVE: callback_mode determines how events are dispatched
# :state_functions — one function per state, like GenServer but state-named
# :handle_event_function — one function handles all events, pattern match on state
# We use :state_functions because it maps naturally to agent lifecycles
```

### A Practical Agent State Machine

```elixir
defmodule AgentStateMachine do
  @moduledoc """
  An agent that moves through lifecycle states with explicit transitions.

  States: idle → planning → executing → reviewing → idle (or blocked → idle)
  Each state has its own event handlers — you cannot receive events
  meant for other states.
  """

  use GenStateMachine, restart: :transient

  # The three required callbacks for :gen_statem
  # DEEP DIVE: These tell the BEAM how to dispatch events to your code

  # We choose :state_functions mode — one function per state name
  # This means handle_event/4 is NOT used; instead, each state name
  # becomes a function that handles events for that state
  def callback_mode, do: :state_functions

  # Called when the state machine starts. Returns the initial state.
  # We begin in :idle because no agent starts with work assigned.
  def init(_args) do
    # State data holds the agent's context: current task, results, etc.
    state_data = %{
      task: nil,
      result: nil,
      attempts: 0
    }

    # Return: {:next_state, state_name, state_data}
    # The state machine begins in :idle with empty data
    {:next_state, :idle, state_data}
  end

  # ---
  # STATE: idle
  # An agent in :idle accepts only :assign_work events.
  # It ignores :execute and :review — those are invalid in this state.
  # ---

  # Handle work assignment while idle
  # This is the only valid event in :idle state
  def idle(:cast, {:assign_work, task}, state_data) do
    # Why log? Because state transitions are audit-worthy in production.
    # An agent moving from idle to planning is a significant event.
    IO.puts("[#{inspect(self())}] Idle → Planning: #{task}")

    # Update the state data with the new task
    new_state_data = %{state_data | task: task}

    # Transition to :planning
    # The state machine will now only accept events defined in the planning/4 function
    {:next_state, :planning, new_state_data}
  end

  # Reject any other events in idle — they're programming errors
  def idle(event_type, event_content, state_data) do
    IO.puts("[#{inspect(self())}] Idle: ignoring #{inspect(event_type)} #{inspect(event_content)}")
    :keep_state_and_data
  end

  # ---
  # STATE: planning
  # The agent creates a plan for the assigned work.
  # Valid events: :execute_plan, :cancel
  # ---

  # Execute the plan — move to executing
  def planning(:cast, :execute_plan, state_data) do
    IO.puts("[#{inspect(self())}] Planning → Executing: #{state_data.task}")

    # Start the actual work. We do NOT block here — GenStateMachine
    # returns immediately and the agent is now in :executing state.
    {:next_state, :executing, state_data}
  end

  # Cancel — return to idle
  def planning(:cast, :cancel, state_data) do
    IO.puts("[#{inspect(self())}] Planning → Idle: cancelled #{state_data.task}")

    # Clear the task from state data
    new_state_data = %{state_data | task: nil, result: nil}

    {:next_state, :idle, new_state_data}
  end

  def planning(event_type, event_content, state_data) do
    IO.puts("[#{inspect(self())}] Planning: ignoring #{inspect(event_type)} #{inspect(event_content)}")
    :keep_state_and_data
  end

  # ---
  # STATE: executing
  # The agent is doing the actual work.
  # Valid events: :complete, :fail, :cancel
  # ---

  # Work completed successfully — move to reviewing
  def executing(:cast, {:complete, result}, state_data) do
    IO.puts("[#{inspect(self())}] Executing → Reviewing: #{state_data.task}")

    # Store the result for the reviewing phase
    new_state_data = %{state_data | result: result}

    {:next_state, :reviewing, new_state_data}
  end

  # Work failed — increment attempts and maybe go back to planning
  def executing(:cast, {:fail, reason}, state_data) do
    new_attempts = state_data.attempts + 1

    # COMMON MISTAKE: Not handling the max-attempts case.
    # Without this check, an agent can loop forever between
    # planning and executing if the work always fails.
    if new_attempts >= 3 do
      IO.puts("[#{inspect(self())}] Executing → Blocked: #{reason} (max attempts reached)")
      {:next_state, :blocked, %{state_data | attempts: new_attempts}}
    else
      IO.puts("[#{inspect(self())}] Executing → Planning: retry (#{new_attempts}/3)")
      {:next_state, :planning, %{state_data | attempts: new_attempts}}
    end
  end

  def executing(:cast, :cancel, state_data) do
    IO.puts("[#{inspect(self())}] Executing → Idle: cancelled")
    {:next_state, :idle, %{state_data | task: nil, result: nil, attempts: 0}}
  end

  def executing(event_type, event_content, state_data) do
    IO.puts("[#{inspect(self())}] Executing: ignoring #{inspect(event_type)} #{inspect(event_content)}")
    :keep_state_and_data
  end

  # ---
  # STATE: reviewing
  # The agent reviews its own work before marking it done.
  # Valid events: :approve, :reject
  # ---

  def reviewing(:cast, :approve, state_data) do
    IO.puts("[#{inspect(self())}] Reviewing → Idle: #{state_data.task} done!")

    # Return to idle with a clean slate, but keep the result as history
    new_state_data = %{state_data | task: nil, result: nil, attempts: 0}

    {:next_state, :idle, new_state_data}
  end

  def reviewing(:cast, :reject, state_data) do
    IO.puts("[#{inspect(self())}] Reviewing → Planning: rework needed")

    # Go back to planning with the failed result as context
    {:next_state, :planning, state_data}
  end

  def reviewing(event_type, event_content, state_data) do
    IO.puts("[#{inspect(self())}] Reviewing: ignoring #{inspect(event_type)} #{inspect(event_content)}")
    :keep_state_and_data
  end

  # ---
  # STATE: blocked
  # The agent is stuck and needs human intervention.
  # Valid events: :unblock
  # ---

  def blocked(:cast, :unblock, state_data) do
    IO.puts("[#{inspect(self())}] Blocked → Idle: unblocked")
    {:next_state, :idle, %{state_data | task: nil, result: nil, attempts: 0}}
  end

  def blocked(event_type, event_content, state_data) do
    IO.puts("[#{inspect(self())}] Blocked: ignoring #{inspect(event_type)} #{inspect(event_content)}")
    :keep_state_and_data
  end
end
```

### Using the State Machine

```elixir
# Start the state machine
{:ok, pid} = AgentStateMachine.start_link([])

# Assign work — triggers transition idle → planning
GenStateMachine.cast(pid, {:assign_work, "Analyze market data"})

# Execute the plan — triggers transition planning → executing
GenStateMachine.cast(pid, :execute_plan)

# Complete the work — triggers transition executing → reviewing
GenStateMachine.cast(pid, {:complete, %{revenue: 42_000}})

# Approve — triggers transition reviewing → idle
GenStateMachine.cast(pid, :approve)

# COMMON MISTAKE: Trying to call a state machine with GenServer.call.
# GenStateMachine uses its own cast/call functions.
# GenServer.call(pid, :execute_plan) will NOT work.
```

### When to Use `:gen_statem` vs GenServer

| Use `:gen_statem` when... | Use GenServer when... |
|---|---|
| Agent has 3+ distinct lifecycle states | Agent has simple request-response pattern |
| State transitions must be validated | State changes are unstructured |
| You need per-state event handling | You need a simple key-value store |
| Compliance requires audit trails of transitions | Speed and simplicity matter most |

---

## Pattern 2: `Task.Supervisor` — Supervised Async Tasks

### The Problem with Bare Tasks

```elixir
# COMMON MISTAKE: Using Task.start_link without supervision
# If the task crashes, nothing restarts it. The caller may not even know.
Task.start_link(fn -> dangerous_work() end)
```

`Task.Supervisor` solves this by giving you a dedicated supervisor for async tasks. Tasks spawned under it are monitored and can be restarted if they crash.

### How Task.Supervisor Works

Think of `Task.Supervisor` as a temp agency. You tell the agency "I need someone to do X." The agency assigns a worker, tracks them, and if the worker gets sick, the agency handles it. You never manage workers directly.

```elixir
defmodule TaskPool do
  @moduledoc """
  A supervised task pool for parallel agent work.

  Each agent can spawn tasks under this supervisor for parallel processing.
  If a task crashes, the supervisor catches it and the agent can retry.
  """

  def start_link do
    # Start the Task.Supervisor with a name for easy access
    # :one_for_one restart strategy means each task is independent
    Task.Supervisor.start_link(name: __MODULE__)
  end

  # Spawn a supervised task and return its reference
  # Returns: {:ok, task_ref} or {:error, reason}
  #
  # The task_ref lets you monitor the task's lifecycle.
  # You can receive :DOWN messages when the task completes or crashes.
  def run_task(agent_id, work_fn) do
    # DEEP DIVE: Task.async_nolink is the key function here.
    # Task.async links the task to the caller — if the task crashes,
    # the caller crashes too. Task.async_nolink does NOT link,
    # so the caller survives. The caller monitors instead.
    Task.Supervisor.async_nolink(__MODULE__, fn ->
      # Tag the task with the agent_id for logging and tracing
      Process.put(:agent_id, agent_id)

      try do
        result = work_fn.()
        {:success, result}
      rescue
        e ->
          # Return the error instead of crashing.
          # The supervisor will log it, but the caller gets the error
          # to handle (maybe retry, maybe escalate to a human).
          {:error, Exception.message(e)}
      end
    end)
  end

  # Run multiple tasks in parallel and wait for all results
  # This is useful when an agent needs to gather data from multiple sources.
  #
  # Returns: list of results in the same order as the input tasks
  def run_parallel(agent_id, work_fns) do
    # COMMON MISTAKE: Using Task.async_stream here instead.
    # Task.async_stream is fine for simple cases, but async_nolink
    # under a supervisor gives you crash isolation. If one task crashes,
    # the others continue. async_stream may abort the entire batch.

    tasks = Enum.map(work_fns, fn work_fn ->
      run_task(agent_id, work_fn)
    end)

    # Wait for each task to complete, with a 30-second timeout
    # DEEP DIVE: Why 30 seconds? Because agent tasks should be bounded.
    # An unbounded task that runs forever is a resource leak.
    # If a task needs more than 30 seconds, it should be redesigned
    # as a multi-step workflow, not a single task.
    Enum.map(tasks, fn task ->
      receive do
        {^task, result} ->
          result
        {:DOWN, _ref, :process, _pid, reason} ->
          {:error, "Task crashed: #{inspect(reason)}"}
      after
        30_000 ->
          {:error, "Task timed out after 30 seconds"}
      end
    end)
  end
end
```

### Using Task.Supervisor

```elixir
# Start the task pool
{:ok, _pid} = TaskPool.start_link()

# Spawn a supervised task
{:ok, task_ref} = TaskPool.run_task("agent-1", fn ->
  # Simulate some heavy computation
  :timer.sleep(1_000)
  %{analysis: "Market is bullish", confidence: 0.87}
end)

# The agent can do other work while the task runs
# ...

# When ready, collect the result
receive do
  {^task_ref, {:success, result}} ->
    IO.puts("Task completed: #{inspect(result)}")
  {^task_ref, {:error, reason}} ->
    IO.puts("Task failed: #{reason}")
after
  30_000 ->
    IO.puts("Task timed out")
end
```

---

## Pattern 3: GenStage — Producer-Consumer with Backpressure

### What Is Backpressure?

Imagine a fire hose connected to a small bucket. Water comes in faster than the bucket can hold it. What happens? Water overflows and makes a mess.

This is exactly what happens in software when a fast producer sends events to a slow consumer. Events pile up in memory, the process runs out of memory, and the BEAM kills it.

**Backpressure** is the mechanism where the consumer tells the producer "slow down, I can't handle more right now." The producer stops producing until the consumer signals it's ready for more.

### How GenStage Works

GenStage builds producer-consumer pipelines. Each stage in the pipeline is a GenStage process:

```
Producer → Consumer → Consumer → Consumer
```

The producer generates events. Consumers demand events from the producer. The producer only sends as many events as consumers have demanded. This is automatic backpressure.

Think of it like a restaurant. The kitchen (producer) can only send plates to the waiter (consumer) when the waiter asks for them. If the waiter is busy with other tables, the kitchen holds the plates. No plates pile up on the counter.

### Implementing a GenStage Producer

```elixir
defmodule EventProducer do
  @moduledoc """
  A GenStage producer that generates sensor events.

  In a real system, this might read from a Kafka topic, a file,
  or an HTTP stream. Here we simulate it with a timer.

  The producer generates events on demand — it only produces
  as many events as consumers have requested. This is backpressure.
  """

  use GenStage

  def start_link(opts \\ []) do
    GenStage.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def init(opts) do
    # State holds:
    # - counter: monotonically increasing event ID
    # - demand: how many events consumers have requested
    # - interval: milliseconds between event batches
    state = %{
      counter: 0,
      demand: 0,
      interval: Keyword.get(opts, :interval, 100)
    }

    # Schedule the first event generation
    # DEEP DIVE: Why use :timer.send_interval instead of Process.send_after?
    # send_interval automatically repeats. send_after only fires once.
    # We want continuous event generation, so send_interval is correct.
    :timer.send_interval(state.interval, :generate)

    {:producer, state}
  end

  # Handle demand from consumers.
  # This is the core of backpressure — we track how many events
  # consumers want, and only produce that many.
  def handle_demand(incoming_demand, state) do
    # Accumulate demand. Consumers may demand more than we have ready.
    # We store it and produce events as they become available.
    new_demand = state.demand + incoming_demand

    # Try to satisfy demand immediately if we have pending events
    {events, new_state} = produce_events(new_demand, %{state | demand: new_demand})

    {:noreply, events, new_state}
  end

  # Handle periodic event generation
  def handle_info(:generate, state) do
    # Only produce if there is demand
    # COMMON MISTAKE: Producing events without checking demand.
    # This defeats the purpose of backpressure and can cause
    # memory issues if consumers are slow.
    if state.demand > 0 do
      {events, new_state} = produce_events(1, state)
      {:noreply, events, new_state}
    else
      # No demand right now — wait for consumers to ask
      {:noreply, [], state}
    end
  end

  # Produce events up to the demand limit
  # Returns: {list_of_events, updated_state}
  defp produce_events(0, state) do
    # No demand left — return empty list
    {[], state}
  end

  defp produce_events(remaining_demand, state) do
    # Generate one event
    event = %{
      id: state.counter + 1,
      timestamp: System.system_time(:millisecond),
      sensor_id: "sensor-#{rem(state.counter, 5) + 1}",
      value: :rand.uniform() * 100
    }

    # DEEP DIVE: We only produce ONE event per call.
    # This is deliberate. Producing one event at a time lets us
    # interleave with other messages (like demand updates from consumers).
    # If we produced all events at once, we'd block the process mailbox.

    new_state = %{state |
      counter: state.counter + 1,
      demand: state.demand - 1
    }

    {[event], new_state}
  end
end
```

### Implementing a GenStage Consumer

```elixir
defmodule EventConsumer do
  @moduledoc """
  A GenStage consumer that processes sensor events.

  Each consumer subscribes to a producer (or another consumer
  in a pipeline). It receives events and processes them.

  The consumer controls the flow: it only asks for events
  when it's ready to process them. This is how backpressure
  propagates back to the producer.
  """

  use GenStage

  def start_link(opts) do
    GenStage.start_link(__MODULE__, opts)
  end

  def init(opts) do
    # Subscribe to the producer when we start
    # DEEP DIVE: subscribe_to starts a demand-based subscription.
    # The consumer will demand events from the producer.
    # max_demand defaults to 1000, min_demand to 500.
    # This means: ask for 1000 events, when 500 are processed, ask for 500 more.
    # This keeps a buffer of events flowing, preventing stalls.

    producer = Keyword.get(opts, :producer, EventProducer)

    # COMMON MISTAKE: Forgetting to subscribe.
    # Without a subscription, the consumer never receives events.
    # It sits idle forever, wondering why nothing is happening.
    GenStage.sync_subscribe(self(), to: producer, max_demand: 10, min_demand: 5)

    state = %{
      processed: 0,
      errors: 0,
      name: Keyword.get(opts, :name, "consumer-#{System.unique_integer([:positive])}")
    }

    {:consumer, state}
  end

  # Handle events from the producer
  # This is where the actual work happens.
  def handle_events(events, _from, state) do
    # Process each event
    results = Enum.map(events, fn event ->
      case process_event(event) do
        :ok ->
          :ok
        {:error, reason} ->
          # COMMON MISTAKE: Crashing on a bad event.
          # One bad event should not kill the consumer.
          # Log the error and continue processing.
          IO.puts("[#{state.name}] Error processing event #{event.id}: #{reason}")
          {:error, reason}
      end
    end)

    # Count successes and errors
    successes = Enum.count(results, &(&1 == :ok))
    errors = Enum.count(results, &match?({:error, _}, &1))

    new_state = %{state |
      processed: state.processed + successes,
      errors: state.errors + errors
    }

    # Return :ok to acknowledge all events were processed.
    # The producer will now send more events based on demand.
    {:noreply, [], new_state}
  end

  # Process a single event
  # Returns :ok or {:error, reason}
  defp process_event(event) do
    # Simulate processing time (1-5ms)
    # DEEP DIVE: In production, this would be the actual work:
    # parsing, validation, database writes, API calls, etc.
    # The processing time determines how fast the pipeline runs.
    # A slow process_event means demand accumulates and backpressure
    # slows down the producer.
    processing_time = :rand.uniform(5)
    :timer.sleep(processing_time)

    # Simulate occasional errors (5% failure rate)
    if :rand.uniform() < 0.05 do
      {:error, "Sensor value out of range"}
    else
      :ok
    end
  end
end
```

### Running the Pipeline

```elixir
# Start the producer
{:ok, _} = EventProducer.start_link(interval: 50)

# Start 3 consumers (parallel processing)
consumers = for i <- 1..3 do
  {:ok, pid} = EventConsumer.start_link(
    name: "consumer-#{i}",
    producer: EventProducer
  )
  pid
end

# Let it run for a few seconds
:timer.sleep(5_000)

# Check the results
# Each consumer will have processed hundreds of events
# but none will have crashed, even with the 5% error rate.
# This is the power of backpressure — the producer never
# overwhelms the consumers.
```

---

## Pattern 4: Broadway — High-Level Data Pipeline

### Why Broadway Exists

GenStage gives you the building blocks, but wiring up a complete pipeline (producer → processors → batchers → sinks) requires a lot of boilerplate. Broadway is Dashbit's answer to this: a high-level API that makes data pipelines declarative.

Think of it like this: GenStage is like writing assembly language. Broadway is like writing Python. Same underlying mechanics, but Broadway is much easier to use.

### Broadway Architecture

```
Producer(s) → Processor(s) → Batcher(s) → Consumer(s)
     ↑              ↑              ↑
  (backpressure) (backpressure) (batch processing)
```

- **Producers**: Generate or receive events (Kafka, SQS, HTTP, GenStage)
- **Processors**: Transform and validate events (like middleware)
- **Batchers**: Group events for efficient bulk operations
- **Consumers**: Final step — write to database, send to API, etc.

### Building a Broadway Pipeline

```elixir
defmodule SensorPipeline do
  @moduledoc """
  A Broadway pipeline for processing sensor data.

  This pipeline:
  1. Receives sensor events from a GenStage producer
  2. Validates and enriches each event
  3. Batches events by sensor_id for efficient database writes
  4. Persists events to the database

  Broadway handles backpressure, batching, and error handling.
  You only write the business logic.
  """

  use Broadway

  def start_link(_opts) do
    Broadway.start_link(__MODULE__,
      name: __MODULE__,

      # Producers: where events come from
      # DEEP DIVE: We use Broadway.Producer.GenStage because we have
      # our own GenStage producer. Broadway also supports Kafka, SQS,
      # and custom producers out of the box.
      producer: [
        module: {EventProducer, interval: 50},
        # concurrency: how many producer processes to run
        # For GenStage, 1 is typical. For Kafka, you'd set this
        # to the number of partitions.
        concurrency: 1
      ],

      # Processors: transform events one at a time
      # concurrency: how many processor processes to run
      # More processors = more parallel processing
      processors: [
        default: [
          concurrency: 4,
          # max_demand: how many events each processor asks for
          # This controls backpressure sensitivity
          max_demand: 10,
          min_demand: 5
        ]
      ],

      # Batchers: group events for bulk operations
      # BATCH BY sensor_id — events from the same sensor go in the same batch
      batchers: [
        sensor: [
          # Batch size: collect 50 events before flushing
          # Why 50? Because database bulk inserts are most efficient
          # with 50-100 rows. Too small = many round trips.
          # Too large = long batch processing time.
          batch_size: 50,
          # Batch timeout: if 50 events don't arrive in 2 seconds,
          # flush whatever we have. Prevents events from sitting
          # in the batcher forever during low-traffic periods.
          batch_timeout: 2_000
        ]
      ]
    )
  end

  # ---
  # Processors: transform events
  # ---

  @doc """
  Handle a single event from the producer.

  This function receives one event at a time and must return
  a list of events (possibly empty, possibly more than one).

  Return [] to drop an event. Return [event] to pass it through.
  Return [enriched_event] to transform it. Return [e1, e2] to split.
  """
  @impl true
  def handle_message(_processor, message, _context) do
    # Validate the event
    # COMMON MISTAKE: Not validating events in handle_message.
    # If you pass invalid events to batchers, the batch consumer
    # will crash on the entire batch, not just the bad event.
    # Validate early, fail fast.
    case validate_event(message.data) do
      :ok ->
        # Enrich the event with additional data
        enriched = enrich_event(message.data)

        # Return the message with enriched data
        # Broadway.message/2 updates the message data
        %{message | data: enriched}

      {:error, reason} ->
        # Mark the message as failed
        # Broadway will handle retries according to your configuration
        Broadway.Message.failed(message, reason)
    end
  end

  # Validate a sensor event
  # Returns :ok or {:error, reason}
  defp validate_event(event) do
    cond do
      # Sensor ID must be present and non-empty
      is_nil(event[:sensor_id]) or event[:sensor_id] == "" ->
        {:error, "missing sensor_id"}

      # Value must be a number
      not is_number(event[:value]) ->
        {:error, "value must be a number"}

      # Value must be within valid range (0-100 for temperature sensors)
      event[:value] < 0 or event[:value] > 100 ->
        {:error, "value out of range: #{event[:value]}"}

      # All checks passed
      true ->
        :ok
    end
  end

  # Enrich a sensor event with metadata
  # Returns the enriched event
  defp enrich_event(event) do
    Map.merge(event, %{
      # Add processing timestamp
      processed_at: DateTime.utc_now(),

      # Add a quality score based on the value
      # DEEP DIVE: Quality scoring helps downstream systems
      # prioritize high-confidence data over uncertain data.
      quality_score: calculate_quality(event.value),

      # Add the sensor's location (in production, this would
      # come from a sensor registry lookup)
      location: "warehouse-#{rem(event.sensor_id |> String.replace("sensor-", "") |> String.to_integer(), 3) + 1}"
    })
  end

  # Calculate a quality score for the sensor reading
  # Returns a float between 0.0 and 1.0
  defp calculate_quality(value) do
    # Values closer to the middle of the range (50) are more trustworthy
    # Extreme values (near 0 or 100) are more likely to be outliers
    1.0 - abs(value - 50) / 50
  end

  # ---
  # Batchers: process groups of events
  # ---

  @doc """
  Handle a batch of events.

  Broadway calls this function when:
  - The batch reaches batch_size events, OR
  - The batch_timeout expires with at least 1 event

  All events in the batch have the same batch_key (sensor_id in our case).
  """
  @impl true
  def handle_batch(:sensor, messages, _batch_info, _context) do
    # DEEP DIVE: Why batch by sensor_id?
    # Because database writes for the same sensor can be optimized:
    # - Single row lock per sensor
    # - Batch INSERT with multiple VALUES
    # - Reduced index fragmentation

    # Convert messages to a list of event maps
    events = Enum.map(messages, & &1.data)

    # Group by sensor_id for efficient bulk insert
    grouped = Enum.group_by(events, & &1.sensor_id)

    # Insert each group as a batch
    Enum.each(grouped, fn {sensor_id, sensor_events} ->
      case insert_batch(sensor_id, sensor_events) do
        {:ok, count} ->
          IO.puts("[SensorPipeline] Inserted #{count} events for #{sensor_id}")

        {:error, reason} ->
          # COMMON MISTAKE: Crashing the batch consumer on a single bad batch.
          # If one sensor's batch fails, other sensors' batches should still
          # be processed. Log the error and continue.
          IO.puts("[SensorPipeline] Failed to insert batch for #{sensor_id}: #{reason}")
      end
    end)

    # Return the messages — Broadway tracks their lifecycle
    messages
  end

  # Insert a batch of events into the database
  # Returns {:ok, count} or {:error, reason}
  #
  # In production, this would use Ecto's bulk_insert or
  # a PostgreSQL COPY command for maximum performance.
  defp insert_batch(sensor_id, events) do
    try do
      # Simulate database write (10-50ms depending on batch size)
      # DEEP DIVE: In production, you'd use:
      #   Repo.insert_all(SensorEvent, events)
      # or for PostgreSQL-specific optimization:
      #   Postgrex.query(conn, "COPY sensor_events (...) FROM STDIN", events)
      processing_time = 10 + length(events)
      :timer.sleep(processing_time)

      # COMMON MISTAKE: Not returning the count.
      # Broadway expects this function to return messages,
      # but your logging should include the count for debugging.
      {:ok, length(events)}
    rescue
      e ->
        {:error, Exception.message(e)}
    end
  end
end
```

### Running the Broadway Pipeline

```elixir
# Start the Broadway pipeline
# This starts the producer, processors, and batchers
{:ok, _pid} = SensorPipeline.start_link([])

# The pipeline is now running.
# Events flow: EventProducer → SensorPipeline processors → batcher → handle_batch
#
# Backpressure is automatic:
# - If handle_batch is slow, processors slow down
# - If processors are slow, the producer slows down
# - If the producer can't slow down (external source), events queue
#   in the producer's buffer until memory pressure triggers flow control
```

---

## How These Patterns Fit Together

In a production agentic platform, you might combine all four patterns:

```
Task.Supervisor (spawn async agent tasks)
    ↓
GenStage Producer (receive events from agents)
    ↓
GenStage Consumer (validate and transform events)
    ↓
Broadway Pipeline (batch and persist to database)
    ↓
:gen_statem (agent lifecycle management)
```

The agent itself is a `:gen_statem` — it has clear lifecycle states. It spawns tasks under `Task.Supervisor` for parallel work. Results flow through a `GenStage` pipeline with backpressure. And `Broadway` handles the final persistence step.

---

## Key Takeaways

1. **`:gen_statem`** is for agents with complex lifecycle states. Use it when GenServer's flat state model is too simple.

2. **`Task.Supervisor`** is for supervised async work. Always use `async_nolink` under a supervisor — never bare `Task.start_link`.

3. **`GenStage`** gives you backpressure for free. Producer-consumer pipelines that never overwhelm slow consumers.

4. **`Broadway`** is GenStage without the boilerplate. Use it for data pipelines (Kafka, SQS, HTTP streams).

5. **Backpressure** is the key insight: consumers control the flow rate. This prevents memory overflows and crashes.

---

## What's Next

In Module 10, you'll learn how to run Elixir across multiple machines. Clustering and distribution let your agent platform scale beyond a single server — essential for production deployments.
