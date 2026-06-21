# Module 7 Exercise: Event Bus for Agent Coordination

> **Estimated time:** 2 hours
>
> Build a signal-based event bus that lets agents communicate through structured signals.
> You'll implement the signal envelope, a PubSub-backed event bus, and directive handling.

---

## Setup

Create a new Mix project:

```bash
mix new signal_bus --sup
cd signal_bus
```

Add `jason` to `mix.exs` deps (for JSON serialization of signals):

```elixir
defp deps do
  [
    {:jason, "~> 1.4"}
  ]
end
```

Run `mix deps.get`.

---

## Part 1: The Signal Envelope

**File: `lib/signal_bus/agent_signal.ex`**

```elixir
defmodule SignalBus.AgentSignal do
  @moduledoc """
  A structured signal envelope for inter-agent communication.

  Every signal has: topic, source, data, timestamp, and metadata.
  This makes signals predictable, debuggable, and composable.
  """

  # STARTER CODE:
  # Implement the AgentSignal struct and helper functions.

  # 1. defstruct with fields:
  #    - :topic (atom)
  #    - :source (string)
  #    - :data (map)
  #    - :timestamp (DateTime)
  #    - metadata: %{} (map, default empty)
  #    HINT: defstruct [:topic, :source, :data, :timestamp, metadata: %{}]

  # 2. new/4
  #    - Takes topic (atom), source (string), data (map), metadata (map, default %{})
  #    - Returns a struct with DateTime.utc_now() as timestamp
  #    - HINT: %__MODULE__{topic: topic, source: source, data: data, timestamp: DateTime.utc_now(), metadata: metadata}

  # 3. to_json/1
  #    - Takes a signal struct
  #    - Converts to JSON string using Jason.encode!
  #    - HINT: Jason.encode!(%{topic: Atom.to_string(signal.topic), ...})

  # 4. from_json/1
  #    - Takes a JSON string
  #    - Parses back to a struct using Jason.decode!
  #    - Convert "topic" string back to atom with String.to_existing_atom/1
  #    - HINT: Use Jason.decode! then build the struct manually

  # 5. topic_matches?/2
  #    - Takes a signal and a pattern (atom or string)
  #    - For atoms: direct equality check
  #    - For strings ending in "*": check if signal topic starts with the prefix
  #    - HINT: Atom.to_string(signal.topic) |> String.starts_with?(prefix)
end
```

---

## Part 2: The Directive

**File: `lib/signal_bus/agent_directive.ex`**

```elixir
defmodule SignalBus.AgentDirective do
  @moduledoc """
  A directive is a command wrapped in a signal.
  It tells an agent what action to take.
  """

  # STARTER CODE:

  # 1. defstruct with fields:
  #    - :command (atom)
  #    - :params (map)
  #    - :source (string)
  #    - :priority (:low | :medium | :high | :urgent)
  #    - issued_at: nil (DateTime)

  # 2. new/4
  #    - Takes command (atom), source (string), params (map, default %{}), priority (atom, default :medium)
  #    - Returns a struct with issued_at set to DateTime.utc_now()
end
```

---

## Part 3: The Event Bus

**File: `lib/signal_bus/event_bus.ex`**

```elixir
defmodule SignalBus.EventBus do
  @moduledoc """
  PubSub-backed event bus for agent communication.
  Wraps Phoenix.PubSub with signal-specific functions.
  """

  # STARTER CODE:

  # 1. subscribe/1
  #    - Takes a topic (atom)
  #    - Converts to string and subscribes via Phoenix.PubSub
  #    - HINT: Phoenix.PubSub.subscribe(SignalBus.PubSub, Atom.to_string(topic))

  # 2. unsubscribe/1
  #    - Takes a topic (atom)
  #    - Unsubscribes from the topic
  #    - HINT: Phoenix.PubSub.unsubscribe(SignalBus.PubSub, Atom.to_string(topic))

  # 3. publish/1
  #    - Takes an AgentSignal struct
  #    - Broadcasts it on its topic
  #    - HINT: Phoenix.PubSub.broadcast(SignalBus.PubSub, Atom.to_string(signal.topic), {:signal, signal})

  # 4. publish_directive/1
  #    - Takes an AgentDirective struct
  #    - Wraps it in an AgentSignal with topic :directive
  #    - Publishes the signal
  #    - HINT: signal = AgentSignal.new(:directive, directive.source, %{directive: directive})
  #           publish(signal)

  # 5. publish_all/1
  #    - Takes a list of signals
  #    - Publishes each one
  #    - HINT: Enum.each(signals, &publish/1)
end
```

---

## Part 4: Directive Handler

**File: `lib/signal_bus/directive_handler.ex`**

```elixir
defmodule SignalBus.DirectiveHandler do
  @moduledoc """
  Handles directives by pattern-matching on the command.
  Returns {:ok, new_state} or {:stop, reason}.
  """

  # STARTER CODE:

  # Implement handle_directive/2 for these commands:

  # 1. :pause
  #    - Set state status to :paused
  #    - Return {:ok, new_state}

  # 2. :resume
  #    - Set state status to :active
  #    - Return {:ok, new_state}

  # 3. :process_task
  #    - Extract task from directive.params.task
  #    - Increment state.tasks_completed
  #    - Store result in state.last_result
  #    - Return {:ok, new_state}

  # 4. :shutdown
  #    - Return {:stop, :shutdown}

  # 5. Catch-all for unknown commands
  #    - Return {:ok, state} (don't crash)
end
```

---

## Part 5: Test It

```elixir
# File: test/signal_bus_test.exs

defmodule SignalBusTest do
  use ExUnit.Case

  # Helper to start the PubSub for tests.
  setup do
    # Start PubSub if not already running.
    {:ok, _} = Phoenix.PubSub.Supervisor.start_link(name: SignalBus.PubSub)
    :ok
  end

  test "signal creation and serialization" do
    # 1. Create a signal
    #    signal = SignalBus.AgentSignal.new(:task_complete, "agent_1", %{result: "done"})
    #    assert signal.topic == :task_complete
    #    assert signal.source == "agent_1"
    #    assert signal.timestamp != nil

    # 2. Serialize to JSON and back
    #    json = SignalBus.AgentSignal.to_json(signal)
    #    restored = SignalBus.AgentSignal.from_json(json)
    #    assert restored.topic == :task_complete
    #    assert restored.source == "agent_1"
  end

  test "pubsub publish and subscribe" do
    # 1. Subscribe to a topic
    #    SignalBus.EventBus.subscribe(:test_topic)

    # 2. Publish a signal
    #    signal = SignalBus.AgentSignal.new(:test_topic, "coordinator", %{msg: "hello"})
    #    SignalBus.EventBus.publish(signal)

    # 3. Receive the signal
    #    assert_receive {:signal, received_signal}
    #    assert received_signal.source == "coordinator"
    #    assert received_signal.data.msg == "hello"
  end

  test "directive handling" do
    # 1. Create a directive
    #    directive = SignalBus.AgentDirective.new(:process_task, "coordinator", %{task: "research"})

    # 2. Handle it
    #    state = %{status: :active, tasks_completed: 0, last_result: nil}
    #    {:ok, new_state} = SignalBus.DirectiveHandler.handle_directive(directive, state)

    # 3. Verify state changed
    #    assert new_state.tasks_completed == 1
    #    assert new_state.last_result == "Processed: research"

    # 4. Test shutdown directive
    #    shutdown = SignalBus.AgentDirective.new(:shutdown, "coordinator")
    #    assert {:stop, :shutdown} = SignalBus.DirectiveHandler.handle_directive(shutdown, state)
  end

  test "publish_directive wraps in signal" do
    # 1. Create a directive and publish it
    #    directive = SignalBus.AgentDirective.new(:pause, "supervisor")
    #    SignalBus.EventBus.subscribe(:directive)
    #    SignalBus.EventBus.publish_directive(directive)

    # 2. Receive the wrapped signal
    #    assert_receive {:signal, signal}
    #    assert signal.topic == :directive
    #    assert signal.data.directive.command == :pause
  end
end
```

---

## Hints

<details>
<summary>Hint 1: JSON serialization</summary>

To convert a struct to JSON, manually build a map with string keys:

```elixir
def to_json(signal) do
  Jason.encode!(%{
    "topic" => Atom.to_string(signal.topic),
    "source" => signal.source,
    "data" => signal.data,
    "timestamp" => DateTime.to_iso8601(signal.timestamp),
    "metadata" => signal.metadata
  })
end
```

To parse back:

```elixir
def from_json(json) do
  map = Jason.decode!(json)
  %__MODULE__{
    topic: String.to_existing_atom(map["topic"]),
    source: map["source"],
    data: map["data"],
    timestamp: DateTime.from_iso8601!(map["timestamp"]),
    metadata: map["metadata"] || %{}
  }
end
```
</details>

<details>
<summary>Hint 2: PubSub topic naming</summary>

PubSub topics are strings. Convert atoms to strings for the topic:

```elixir
# Subscribe:
Phoenix.PubSub.subscribe(SignalBus.PubSub, Atom.to_string(topic))

# Broadcast:
Phoenix.PubSub.broadcast(SignalBus.PubSub, Atom.to_string(signal.topic), {:signal, signal})
```

The subscriber receives `{:signal, signal}` in `handle_info/2`.
</details>

<details>
<summary>Hint 3: Directive handler pattern</summary>

Use multiple function clauses with pattern matching:

```elixir
def handle_directive(%AgentDirective{command: :pause}, state) do
  {:ok, %{state | status: :paused}}
end

def handle_directive(%AgentDirective{command: :shutdown}, state) do
  {:stop, :shutdown}
end

# Catch-all (must be last):
def handle_directive(%AgentDirective{command: _unknown}, state) do
  {:ok, state}
end
```

Elixir tries each clause in order. The first match wins.
</details>

---

## Solution

<details>
<summary>Click to reveal the complete solution</summary>

### `lib/signal_bus/agent_signal.ex`

```elixir
defmodule SignalBus.AgentSignal do
  @moduledoc """
  A structured signal envelope for inter-agent communication.

  Every signal in the system has exactly this shape:
  topic, source, data, timestamp, metadata.
  This makes signals predictable, debuggable, and composable.
  """

  # defstruct defines the fields and their defaults.
  # Fields without a default MUST be provided when creating the struct.
  defstruct [
    :topic,
    :source,
    :data,
    :timestamp,
    metadata: %{}
  ]

  # new/4 creates a signal with an automatic timestamp.
  # The caller provides topic, source, data, and optional metadata.
  # We auto-generate the timestamp so every signal is time-stamped.
  def new(topic, source, data, metadata \\ %{}) do
    %__MODULE__{
      topic: topic,
      source: source,
      data: data,
      # DateTime.utc_now() returns the current UTC time.
      # We always use UTC to avoid timezone-related bugs.
      timestamp: DateTime.utc_now(),
      metadata: metadata
    }
  end

  # to_json/1 converts a signal to a JSON string.
  # We convert atoms to strings because JSON doesn't have atoms.
  def to_json(%__MODULE__{} = signal) do
    Jason.encode!(%{
      "topic" => Atom.to_string(signal.topic),
      "source" => signal.source,
      "data" => signal.data,
      "timestamp" => DateTime.to_iso8601(signal.timestamp),
      "metadata" => signal.metadata
    })
  end

  # from_json/1 parses a JSON string back into a signal struct.
  # String.to_existing_atom/1 converts a string to an atom, but only if
  # the atom already exists. This prevents atom table exhaustion.
  def from_json(json) do
    map = Jason.decode!(json)

    %__MODULE__{
      topic: String.to_existing_atom(map["topic"]),
      source: map["source"],
      data: map["data"],
      timestamp: DateTime.from_iso8601!(map["timestamp"]),
      metadata: map["metadata"] || %{}
    }
  end

  # topic_matches?/2 checks if a signal matches a topic pattern.
  # Supports exact atom matches and wildcard string prefixes.
  def topic_matches?(%__MODULE__{topic: signal_topic}, pattern) when is_atom(pattern) do
    signal_topic == pattern
  end

  def topic_matches?(%__MODULE__{topic: signal_topic}, pattern) when is_binary(pattern) do
    topic_str = Atom.to_string(signal_topic)

    if String.ends_with?(pattern, "*") do
      prefix = String.trim_trailing(pattern, "*")
      String.starts_with?(topic_str, prefix)
    else
      topic_str == pattern
    end
  end
end
```

### `lib/signal_bus/agent_directive.ex`

```elixir
defmodule SignalBus.AgentDirective do
  @moduledoc """
  A directive is a command wrapped in a signal.
  It tells the receiving agent exactly what action to take.
  """

  defstruct [
    :command,
    :params,
    :source,
    :priority,
    issued_at: nil
  ]

  # new/4 creates a directive with an automatic timestamp.
  # command: atom describing what to do (:pause, :resume, :process_task, :shutdown)
  # source: string identifying who issued the directive
  # params: map with command-specific parameters
  # priority: urgency level, default :medium
  def new(command, source, params \\ %{}, priority \\ :medium) do
    %__MODULE__{
      command: command,
      params: params,
      source: source,
      priority: priority,
      issued_at: DateTime.utc_now()
    }
  end
end
```

### `lib/signal_bus/event_bus.ex`

```elixir
defmodule SignalBus.EventBus do
  @moduledoc """
  PubSub-backed event bus for agent communication.
  Wraps Phoenix.PubSub with signal-specific convenience functions.
  """

  @pubsub_name SignalBus.PubSub
  # This must match the name in your application supervision tree.

  # subscribe/1 subscribes the calling process to a topic.
  # After subscribing, signals published to this topic arrive in handle_info/2.
  def subscribe(topic) do
    Phoenix.PubSub.subscribe(@pubsub_name, Atom.to_string(topic))
  end

  # unsubscribe/1 removes the subscription.
  # Useful when an agent no longer needs to hear about certain events.
  def unsubscribe(topic) do
    Phoenix.PubSub.unsubscribe(@pubsub_name, Atom.to_string(topic))
  end

  # publish/1 broadcasts an AgentSignal to all subscribers of its topic.
  # The signal arrives as {:signal, signal} in the subscriber's handle_info/2.
  def publish(%SignalBus.AgentSignal{} = signal) do
    Phoenix.PubSub.broadcast(
      @pubsub_name,
      Atom.to_string(signal.topic),
      {:signal, signal}
    )
  end

  # publish_directive/1 wraps a directive in a signal and publishes it.
  # The directive is nested in the signal's data field.
  # Subscribers to :directive topic receive the wrapped signal.
  def publish_directive(%SignalBus.AgentDirective{} = directive) do
    signal = SignalBus.AgentSignal.new(
      :directive,
      directive.source,
      %{directive: directive}
    )
    publish(signal)
  end

  # publish_all/1 publishes a list of signals.
  # Convenience for batch publishing (e.g., when emitting multiple events at once).
  def publish_all(signals) do
    Enum.each(signals, &publish/1)
  end
end
```

### `lib/signal_bus/directive_handler.ex`

```elixir
defmodule SignalBus.DirectiveHandler do
  @moduledoc """
  Handles directives by pattern-matching on the command.
  Each command clause is a separate function head.
  Returns {:ok, new_state} or {:stop, reason}.
  """

  # :pause command — puts the agent in paused state.
  # The agent stays alive but stops processing tasks.
  def handle_directive(%SignalBus.AgentDirective{command: :pause}, state) do
    {:ok, %{state | status: :paused}}
  end

  # :resume command — puts the agent back to active.
  def handle_directive(%SignalBus.AgentDirective{command: :resume}, state) do
    {:ok, %{state | status: :active}}
  end

  # :process_task command — processes the task and updates state.
  # The task text comes from directive.params.task.
  def handle_directive(
    %SignalBus.AgentDirective{command: :process_task, params: %{task: task}},
    state
  ) do
    new_state = %{
      state
      | tasks_completed: state.tasks_completed + 1,
        last_result: "Processed: #{task}"
    }

    {:ok, new_state}
  end

  # :shutdown command — gracefully terminates the agent.
  # {:stop, :shutdown} tells GenServer to call terminate/2 and exit.
  def handle_directive(%SignalBus.AgentDirective{command: :shutdown}, _state) do
    {:stop, :shutdown}
  end

  # Catch-all: unknown commands are logged but don't crash the agent.
  # WHY: in a multi-agent system, you might receive commands from different
  # versions of the system. Crashing on unknown commands is too aggressive.
  def handle_directive(%SignalBus.AgentDirective{command: unknown}, state) do
    IO.puts("Warning: Unknown directive command: #{inspect(unknown)}")
    {:ok, state}
  end
end
```

### `lib/signal_bus/application.ex`

```elixir
defmodule SignalBus.Application do
  use Application

  def start(_type, _args) do
    children = [
      # PubSub must start before any subscriber or publisher.
      # This is the message bus that all signals flow through.
      {Phoenix.PubSub, name: SignalBus.PubSub}
    ]

    Supervisor.start_link(children, strategy: :one_for_one, name: SignalBus.Supervisor)
  end
end
```

### `mix.exs` deps addition

```elixir
defp deps do
  [
    {:jason, "~> 1.4"},
    {:phoenix_pubsub, "~> 2.1"}
  ]
end
```

</details>

---

## What You've Built

- **AgentSignal**: A structured signal envelope with topic, source, data, timestamp, metadata
- **AgentDirective**: A command wrapped in a signal (pause, resume, process_task, shutdown)
- **EventBus**: A PubSub-backed event bus with subscribe/publish/publish_directive
- **DirectiveHandler**: Pattern-matched command handler with graceful shutdown support

Signals give your agents a shared language. Directives give them commands. PubSub gives them reach.
Together, they form the communication backbone of a multi-agent system.

**Next:** [Module 8: Agent State & Durable Workflows](08-agent-state-durable.md)
