# Module 9 Exercise: Advanced OTP Patterns

## What You'll Practice

By completing this exercise, you'll build a **stream processing pipeline** that combines all four advanced OTP patterns:

1. A `:gen_statem` agent that processes sensor data through lifecycle states
2. A `Task.Supervisor` for parallel data validation
3. A `GenStage` producer-consumer pipeline with backpressure
4. A `Broadway` pipeline for batch persistence

This is a real-world scenario: IoT sensor data processing with automatic flow control.

---

## Part 1: Sensor Agent State Machine

Build a `:gen_statem` agent that manages sensor data processing through these states:

- **idle** → waiting for sensor data
- **validating** → checking data integrity
- **processing** → transforming the data
- **persisting** → writing to database
- **error** → handling failures (max 3 retries)

### Starter Code

```elixir
defmodule SensorAgent do
  @moduledoc """
  A sensor data processing agent with explicit lifecycle states.

  Transitions: idle → validating → processing → persisting → idle
  Error path: any state → error → idle (after 3 retries)
  """

  use GenStateMachine

  # TODO: Implement callback_mode/0
  # Hint: We want one function per state name

  # TODO: Implement init/1
  # Hint: Start in :idle with %{
  #   sensor_data: nil,
  #   retries: 0,
  #   result: nil
  # }

  # TODO: Implement idle/3
  # Valid events: {:cast, {:receive_data, data}}
  # Should transition to :validating
  # Hint: Update state data with the sensor data

  # TODO: Implement validating/3
  # Valid events: {:cast, :data_valid}, {:cast, {:data_invalid, reason}}
  # If valid: transition to :processing
  # If invalid: transition to :error with increment retry
  # Hint: Check for nil sensor_id or value < 0 or value > 100

  # TODO: Implement processing/3
  # Valid events: {:cast, {:processed, result}}, {:cast, {:process_failed, reason}}
  # If success: transition to :persisting with the result
  # If failure: transition to :error

  # TODO: Implement persisting/3
  # Valid events: {:cast, :persisted}, {:cast, {:persist_failed, reason}}
  # If success: transition to :idle (clear data)
  # If failure: transition to :error

  # TODO: Implement error/3
  # Valid events: {:cast, :retry}
  # If retries < 3: transition to :validating (reset retries)
  # If retries >= 3: transition to :idle (give up)
  # Hint: Return {:next_state, :idle, %{state_data | sensor_data: nil, retries: 0}}

  # COMMON MISTAKE: Forgetting to handle unknown events in each state.
  # Every state MUST have a catch-all clause that returns :keep_state_and_data
  # Otherwise, unexpected events will crash the state machine.
end
```

### Hints

1. Remember that `:gen_statem` callbacks return tuples like `{:next_state, new_state, data}`
2. Use `:keep_state_and_data` to stay in the current state without changing data
3. Each state function takes `(event_type, event_content, state_data)`
4. Pattern match on `{:cast, event}` to handle cast events

### What to Test

After implementing, start the agent and verify:
- Receiving valid data transitions through all states
- Invalid data triggers error state
- 3 failures in a row stop retries
- Successful processing returns to idle

---

## Part 2: Parallel Validation with Task.Supervisor

Build a task pool that validates multiple sensor readings in parallel.

### Starter Code

```elixir
defmodule SensorValidationPool do
  @moduledoc """
  A supervised task pool for parallel sensor data validation.
  """

  # TODO: Implement start_link/0
  # Start a Task.Supervisor with name: __MODULE__

  # TODO: Implement validate_sensor/2
  # Parameters: sensor_id, data
  # Returns: {:ok, task_ref}
  #
  # Use Task.Supervisor.async_nolink to spawn a supervised task
  # The task should:
  #   1. Check that sensor_id is a string starting with "sensor-"
  #   2. Check that data has :value key
  #   3. Check that value is between 0 and 100
  #   4. Return {:valid, sensor_id} or {:invalid, sensor_id, reason}

  # TODO: Implement validate_batch/2
  # Parameters: sensor_id, list_of_data
  # Returns: list of results
  #
  # Use validate_sensor/2 for each data point
  # Wait for all results with a 10-second timeout
  # Hint: Use receive with after: 10_000
end
```

### Hints

1. `Task.Supervisor.async_nolink` returns a task struct — match on `{^task, result}` in receive
2. Always handle `:DOWN` messages — the task may crash
3. Use `Process.put/2` inside the task to tag it with the sensor_id
4. Set a timeout — don't wait forever for a stuck task

---

## Part 3: GenStage Pipeline with Backpressure

Build a producer-consumer pipeline for sensor data transformation.

### Starter Code

```elixir
defmodule SensorProducer do
  @moduledoc """
  A GenStage producer that generates simulated sensor readings.
  """

  use GenStage

  def start_link(opts \\ []) do
    GenStage.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def init(opts) do
    state = %{
      counter: 0,
      demand: 0,
      interval: Keyword.get(opts, :interval, 100)
    }

    # TODO: Schedule periodic event generation
    # Hint: Use :timer.send_interval/2

    {:producer, state}
  end

  # TODO: Implement handle_demand/2
  # Accumulate demand and try to produce events
  # Hint: Call produce_events/2

  # TODO: Implement handle_info/2 for :generate
  # Only produce if demand > 0

  # TODO: Implement produce_events/2 (private)
  # Generate one event per call (not all at once!)
  # Event format: %{id, timestamp, sensor_id, value}
  # Decrease demand by 1 for each event produced
end

defmodule SensorTransformer do
  @moduledoc """
  A GenStage consumer that transforms sensor readings.
  """

  use GenStage

  def start_link(opts) do
    GenStage.start_link(__MODULE__, opts)
  end

  def init(opts) do
    # TODO: Subscribe to SensorProducer
    # Hint: GenStage.sync_subscribe(self(), to: SensorProducer, max_demand: 10)

    state = %{
      transformed: 0,
      name: Keyword.get(opts, :name, "transformer")
    }

    {:consumer, state}
  end

  # TODO: Implement handle_events/3
  # For each event:
  #   1. Convert value to Fahrenheit (value * 1.8 + 32)
  #   2. Add :fahrenheit key
  #   3. Add :transformed_at timestamp
  # Return {:noreply, [], new_state}

  # COMMON MISTAKE: Not returning {:noreply, [], state}.
  # Consumers return an empty list — they don't produce events.
end
```

### Hints

1. Producers return `{:noreply, events, state}` — events is a list
2. Consumers return `{:noreply, [], state}` — empty list (they consume, don't produce)
3. Check demand before producing — this is the backpressure mechanism
4. Only produce ONE event per produce_events call (interleave with other messages)

---

## Part 4: Broadway Batch Pipeline

Build a Broadway pipeline that batches sensor data by sensor_id.

### Starter Code

```elixir
defmodule SensorBroadway do
  @moduledoc """
  A Broadway pipeline for batched sensor data persistence.
  """

  use Broadway

  def start_link(_opts) do
    Broadway.start_link(__MODULE__,
      name: __MODULE__,

      producer: [
        module: {SensorProducer, [interval: 50]},
        concurrency: 1
      ],

      processors: [
        default: [
          concurrency: 2,
          max_demand: 10,
          min_demand: 5
        ]
      ],

      batchers: [
        sensor: [
          # TODO: Set batch_size to 25
          # TODO: Set batch_timeout to 3_000
        ]
      ]
    )
  end

  # TODO: Implement handle_message/3
  # Validate the event:
  #   - sensor_id must be present
  #   - value must be a number between 0 and 100
  # Enrich with processed_at timestamp
  # Return %{message | data: enriched_event}
  # On validation failure: Broadway.Message.failed(message, reason)

  # COMMON MISTAKE: Not calling Broadway.Message.failed/2 for invalid events.
  # If you return the invalid event, the batch consumer will crash.

  # TODO: Implement handle_batch/4
  # Group events by sensor_id
  # Insert each group (simulate with IO.puts)
  # Return messages

  defp validate_event(event) do
    # TODO: Implement validation
    # Check sensor_id is present and is a string
    # Check value is a number between 0 and 100
    # Return :ok or {:error, reason}
  end

  defp enrich_event(event) do
    # TODO: Add processed_at: DateTime.utc_now()
    # Add quality_score: 1.0 - abs(event.value - 50) / 50
  end
end
```

### Hints

1. `handle_message` receives one message at a time — validate and transform
2. `handle_batch` receives a list of messages — group and batch insert
3. Use `Broadway.Message.failed/2` to mark bad messages (don't crash)
4. Return the messages list from `handle_batch` — Broadway tracks them

---

## Part 5: Integration — Putting It All Together

Wire all four components into a working system:

### Starter Code

```elixir
defmodule SensorPlatform do
  @moduledoc """
  The main application module that wires all components together.

  Start order:
  1. Task.Supervisor (for parallel validation)
  2. SensorAgent (state machine)
  3. SensorProducer (GenStage producer)
  4. SensorTransformer (GenStage consumer)
  5. SensorBroadway (batch pipeline)
  """

  use Application

  def start(_type, _args) do
    children = [
      # TODO: Add each component as a child
      # Start Task.Supervisor first (other components depend on it)
      # Then SensorAgent
      # Then SensorProducer
      # Then SensorTransformer
      # Then SensorBroadway
    ]

    opts = [strategy: :one_for_one, name: SensorPlatform.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
```

### Hints

1. Start order matters — components that depend on others must start first
2. Use `worker` or `supervisor` specs in the children list
3. Test by sending events to the SensorAgent and watching the pipeline

---

## Bonus Challenge

Add a **monitoring dashboard** that tracks:
- Events processed per second
- Error rate
- Backpressure indicator (demand vs supply)
- Agent state distribution

Hint: Use GenServer to track metrics, and a periodic timer to log them.

---

## Solutions

### Solution: SensorAgent State Machine

```elixir
defmodule SensorAgent do
  @moduledoc """
  A sensor data processing agent with explicit lifecycle states.

  Transitions: idle → validating → processing → persisting → idle
  Error path: any state → error → idle (after 3 retries)
  """

  use GenStateMachine

  # We use :state_functions mode — one function per state name
  # This makes the state machine easy to read and debug
  def callback_mode, do: :state_functions

  # Initialize the state machine in :idle state
  def init(_args) do
    state_data = %{
      sensor_data: nil,
      retries: 0,
      result: nil
    }
    {:next_state, :idle, state_data}
  end

  # STATE: idle
  # Only accept new sensor data in this state
  def idle(:cast, {:receive_data, data}, state_data) do
    new_state_data = %{state_data | sensor_data: data}
    {:next_state, :validating, new_state_data}
  end

  # Reject any other events in idle
  def idle(_event_type, _event_content, _state_data) do
    :keep_state_and_data
  end

  # STATE: validating
  # Check data integrity before processing
  def validating(:cast, :data_valid, state_data) do
    {:next_state, :processing, state_data}
  end

  # Validation failed — go to error state
  def validating(:cast, {:data_invalid, reason}, state_data) do
    new_retries = state_data.retries + 1
    new_state_data = %{state_data | retries: new_retries}
    {:next_state, :error, new_state_data}
  end

  # Reject any other events in validating
  def validating(_event_type, _event_content, _state_data) do
    :keep_state_and_data
  end

  # STATE: processing
  # Transform the sensor data
  def processing(:cast, {:processed, result}, state_data) do
    new_state_data = %{state_data | result: result}
    {:next_state, :persisting, new_state_data}
  end

  # Processing failed
  def processing(:cast, {:process_failed, _reason}, state_data) do
    new_retries = state_data.retries + 1
    new_state_data = %{state_data | retries: new_retries}
    {:next_state, :error, new_state_data}
  end

  # Reject any other events in processing
  def processing(_event_type, _event_content, _state_data) do
    :keep_state_and_data
  end

  # STATE: persisting
  # Write to database
  def persisting(:cast, :persisted, state_data) do
    # Success — clear everything and return to idle
    new_state_data = %{state_data | sensor_data: nil, retries: 0, result: nil}
    {:next_state, :idle, new_state_data}
  end

  # Persistence failed
  def persisting(:cast, {:persist_failed, _reason}, state_data) do
    new_retries = state_data.retries + 1
    new_state_data = %{state_data | retries: new_retries}
    {:next_state, :error, new_state_data}
  end

  # Reject any other events in persisting
  def persisting(_event_type, _event_content, _state_data) do
    :keep_state_and_data
  end

  # STATE: error
  # Handle retries and give up after max attempts
  def error(:cast, :retry, state_data) do
    if state_data.retries < 3 do
      # Retry — go back to validating (not idle)
      {:next_state, :validating, state_data}
    else
      # Max retries reached — give up and return to idle
      new_state_data = %{state_data | sensor_data: nil, retries: 0, result: nil}
      {:next_state, :idle, new_state_data}
    end
  end

  # Reject any other events in error
  def error(_event_type, _event_content, _state_data) do
    :keep_state_and_data
  end
end
```

### Solution: SensorValidationPool

```elixir
defmodule SensorValidationPool do
  @moduledoc """
  A supervised task pool for parallel sensor data validation.
  """

  def start_link do
    Task.Supervisor.start_link(name: __MODULE__)
  end

  def validate_sensor(sensor_id, data) do
    task = Task.Supervisor.async_nolink(__MODULE__, fn ->
      # Tag the task with the sensor_id for debugging
      Process.put(:sensor_id, sensor_id)

      # Validation step 1: sensor_id format
      if not is_binary(sensor_id) or not String.starts_with?(sensor_id, "sensor-") do
        {:invalid, sensor_id, "sensor_id must start with 'sensor-'"}
      # Validation step 2: data must have :value key
      else
        case data do
          %{value: value} when is_number(value) ->
            # Validation step 3: value range
            if value >= 0 and value <= 100 do
              {:valid, sensor_id}
            else
              {:invalid, sensor_id, "value out of range: #{value}"}
            end
          _ ->
            {:invalid, sensor_id, "data must have a numeric :value key"}
        end
      end
    end)

    {:ok, task.ref}
  end

  def validate_batch(sensor_id, data_list) do
    # Spawn a validation task for each data point
    tasks = Enum.map(data_list, fn data ->
      validate_sensor(sensor_id, data)
    end)

    # Wait for all results
    Enum.map(tasks, fn {:ok, ref} ->
      receive do
        {^ref, result} ->
          result
        {:DOWN, ^ref, :process, _pid, reason} ->
          {:error, "Task crashed: #{inspect(reason)}"}
      after
        10_000 ->
          {:error, "Validation timed out"}
      end
    end)
  end
end
```

### Solution: SensorProducer

```elixir
defmodule SensorProducer do
  @moduledoc """
  A GenStage producer that generates simulated sensor readings.
  """

  use GenStage

  def start_link(opts \\ []) do
    GenStage.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def init(opts) do
    state = %{
      counter: 0,
      demand: 0,
      interval: Keyword.get(opts, :interval, 100)
    }

    # Schedule periodic event generation
    # send_interval automatically repeats every interval milliseconds
    :timer.send_interval(state.interval, :generate)

    {:producer, state}
  end

  # Accumulate demand from consumers
  # When consumers are ready, they demand events. We store the demand
  # and produce events when they become available.
  def handle_demand(incoming_demand, state) do
    new_demand = state.demand + incoming_demand
    {events, new_state} = produce_events(new_demand, %{state | demand: new_demand})
    {:noreply, events, new_state}
  end

  # Generate events periodically
  def handle_info(:generate, state) do
    if state.demand > 0 do
      {events, new_state} = produce_events(1, state)
      {:noreply, events, new_state}
    else
      # No demand — wait for consumers
      {:noreply, [], state}
    end
  end

  # Produce events one at a time
  # This interleaves with other messages (demand updates, etc.)
  defp produce_events(0, state) do
    {[], state}
  end

  defp produce_events(remaining_demand, state) do
    event = %{
      id: state.counter + 1,
      timestamp: System.system_time(:millisecond),
      sensor_id: "sensor-#{rem(state.counter, 5) + 1}",
      value: :rand.uniform() * 100
    }

    new_state = %{state |
      counter: state.counter + 1,
      demand: state.demand - 1
    }

    {[event], new_state}
  end
end
```

### Solution: SensorTransformer

```elixir
defmodule SensorTransformer do
  @moduledoc """
  A GenStage consumer that transforms sensor readings.
  """

  use GenStage

  def start_link(opts) do
    GenStage.start_link(__MODULE__, opts)
  end

  def init(opts) do
    # Subscribe to the producer when we start
    # max_demand: ask for 10 events at a time
    # min_demand: when 5 are processed, ask for 5 more
    GenStage.sync_subscribe(self(), to: SensorProducer, max_demand: 10, min_demand: 5)

    state = %{
      transformed: 0,
      name: Keyword.get(opts, :name, "transformer")
    }

    {:consumer, state}
  end

  # Handle events from the producer
  def handle_events(events, _from, state) do
    # Transform each event
    transformed = Enum.map(events, fn event ->
      %{
        id: event.id,
        timestamp: event.timestamp,
        sensor_id: event.sensor_id,
        value: event.value,
        # Convert Celsius to Fahrenheit
        fahrenheit: event.value * 1.8 + 32,
        transformed_at: DateTime.utc_now()
      }
    end)

    # Log the transformation
    IO.puts("[#{state.name}] Transformed #{length(transformed)} events")

    # Return empty list — consumers don't produce events
    {:noreply, [], %{state | transformed: state.transformed + length(transformed)}}
  end
end
```

### Solution: SensorBroadway

```elixir
defmodule SensorBroadway do
  @moduledoc """
  A Broadway pipeline for batched sensor data persistence.
  """

  use Broadway

  def start_link(_opts) do
    Broadway.start_link(__MODULE__,
      name: __MODULE__,

      producer: [
        module: {SensorProducer, [interval: 50]},
        concurrency: 1
      ],

      processors: [
        default: [
          concurrency: 2,
          max_demand: 10,
          min_demand: 5
        ]
      ],

      batchers: [
        sensor: [
          batch_size: 25,
          batch_timeout: 3_000
        ]
      ]
    )
  end

  # Handle a single event
  @impl true
  def handle_message(_processor, message, _context) do
    case validate_event(message.data) do
      :ok ->
        enriched = enrich_event(message.data)
        %{message | data: enriched}

      {:error, reason} ->
        # Mark the message as failed — Broadway handles retries
        Broadway.Message.failed(message, reason)
    end
  end

  # Handle a batch of events
  @impl true
  def handle_batch(:sensor, messages, _batch_info, _context) do
    # Group events by sensor_id for efficient bulk insert
    events = Enum.map(messages, & &1.data)
    grouped = Enum.group_by(events, & &1.sensor_id)

    # Insert each group
    Enum.each(grouped, fn {sensor_id, sensor_events} ->
      IO.puts("[SensorBroadway] Inserted #{length(sensor_events)} events for #{sensor_id}")
    end)

    # Return messages — Broadway tracks their lifecycle
    messages
  end

  # Validate a sensor event
  defp validate_event(event) do
    cond do
      is_nil(event[:sensor_id]) or event[:sensor_id] == "" ->
        {:error, "missing sensor_id"}

      not is_number(event[:value]) ->
        {:error, "value must be a number"}

      event[:value] < 0 or event[:value] > 100 ->
        {:error, "value out of range: #{event[:value]}"}

      true ->
        :ok
    end
  end

  # Enrich a sensor event with metadata
  defp enrich_event(event) do
    Map.merge(event, %{
      processed_at: DateTime.utc_now(),
      quality_score: 1.0 - abs(event.value - 50) / 50
    })
  end
end
```

### Solution: SensorPlatform

```elixir
defmodule SensorPlatform do
  @moduledoc """
  The main application module that wires all components together.

  Start order:
  1. Task.Supervisor (other components may use it)
  2. SensorProducer (GenStage producer — must start before consumers)
  3. SensorTransformer (GenStage consumer — subscribes to producer)
  4. SensorBroadway (has its own producer, independent)
  5. SensorAgent (state machine, independent)
  """

  use Application

  def start(_type, _args) do
    children = [
      # Task.Supervisor for parallel validation tasks
      {Task.Supervisor, name: SensorValidationPool},

      # GenStage producer — must start before consumers
      {SensorProducer, [interval: 50]},

      # GenStage consumer — subscribes to SensorProducer
      {SensorTransformer, [name: "transformer-1"]},

      # Broadway pipeline — has its own producer
      SensorBroadway,

      # Agent state machine — independent component
      SensorAgent
    ]

    opts = [strategy: :one_for_one, name: SensorPlatform.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
```
