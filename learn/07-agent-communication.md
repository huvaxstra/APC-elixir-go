# Module 7: Agent Communication & Signals

> **Week 7** · Elixir · ~4 hours
>
> Agents don't work in isolation. A research agent might need to hand results to a writing agent.
> A supervisor might need to tell all agents to pause. This module teaches you the communication
> patterns that make multi-agent coordination possible: process messages, PubSub, signal envelopes,
> and directives. Jido uses Signals for agent communication. Sagents broadcasts events via PubSub.
> You'll build both patterns.

---

## The Communication Spectrum

Agent communication exists on a spectrum from simple to complex:

```
Simple ←──────────────────────────────────────────→ Complex

send/2      PubSub       Signal Envelope    Directives
(point-to-point)  (broadcast)    (structured)      (command + data)
```

You'll learn all four, and more importantly, **when to use each one**.

---

## 1. Process Messages: Point-to-Point Communication

The simplest form: one process sends a message directly to another process. This is what `send/2` does.

```elixir
# send/2 puts a message in a process's mailbox.
# The receiving process picks it up with receive or handle_info.
# Think of it like texting someone directly — only they see the message.

defmodule Messenger do
  # send_task/3 sends a task message to a specific agent process.
  # from: PID of the sender (so the agent can reply)
  # to_agent: PID of the target agent
  # task: string describing the task
  def send_task(from, to_agent, task) do
    # send/2 is a built-in Erlang function. It's synchronous in the sense
    # that it adds the message to the mailbox immediately and returns :ok.
    # The message sits in the mailbox until the receiver processes it.
    send(to_agent, {:task, from, task})
    :ok
  end

  # send_task_with_reply/3 adds a reference so the sender can match the reply.
  # WHY: without a reference, if you receive multiple messages, you can't tell
  # which reply belongs to which request.
  def send_task_with_reply(from, to_agent, task) do
    # make_ref/0 creates a unique reference. It's guaranteed to be globally unique.
    ref = make_ref()
    send(to_agent, {:task, from, ref, task})
    # Return the ref so the caller can use it to match the reply.
    ref
  end
end

# On the receiving side (inside a GenServer):
def handle_info({:task, from, task}, state) do
  # Process the task...
  result = "Done: #{task}"

  # Reply to the sender using their PID.
  send(from, {:task_result, result})
  {:noreply, state}
end
```

### When to Use Direct Messages

- **One agent needs to talk to one other agent** (request/reply)
- **You know the PID** of the target process
- **You don't need other processes to see the message**

### When NOT to Use Direct Messages

- **Many agents need the same event** (use PubSub instead)
- **You don't know the PID** (use Registry + PubSub)
- **The sender and receiver are in different nodes** (use PubSub for distribution)

---

## 2. Phoenix.PubSub: Broadcast Communication

PubSub (Publish/Subscribe) is the opposite of direct messaging: one message, many receivers.

```elixir
# PubSub is like a radio station. The broadcaster sends a message on a frequency (topic).
# Anyone tuned into that frequency receives it. The broadcaster doesn't know or care
# who's listening.

defmodule SignalBus do
  @pubsub_name AgenticPlatform.PubSub
  # The PubSub name must match what's configured in your application supervision tree.
  # This is the name passed to {Phoenix.PubSub, name: AgenticPlatform.PubSub}.

  # subscribe/1 subscribes the calling process to a topic.
  # After subscribing, any message broadcast to this topic arrives in handle_info/2.
  def subscribe(topic) do
    Phoenix.PubSub.subscribe(@pubsub_name, topic)
  end

  # broadcast/2 sends a message to ALL processes subscribed to a topic.
  # Returns :ok on success, {:error, reason} on failure.
  # The message is a tuple that receivers pattern-match on.
  def broadcast(topic, message) do
    Phoenix.PubSub.broadcast(@pubsub_name, topic, message)
  end

  # broadcast!/2 is the bang version — raises on error instead of returning {:error, ...}.
  # Use this in fire-and-forget scenarios where you want to fail loudly.
  def broadcast!(topic, message) do
    Phoenix.PubSub.broadcast!(@pubsub_name, topic, message)
  end
end
```

### PubSub Patterns

```elixir
# Pattern 1: Topic per agent type
# All researcher agents subscribe to "research_events".
# When one finds something, all researchers hear about it.
SignalBus.subscribe("research_events")
SignalBus.broadcast("research_events", {:new_finding, "Elixir scales to 2M connections"})

# Pattern 2: Topic per conversation
# All agents in a conversation subscribe to "conversation:42".
# Messages are scoped to that conversation.
SignalBus.subscribe("conversation:42")
SignalBus.broadcast("conversation:42", {:user_message, "What is Elixir?"})

# Pattern 3: Topic per event type
# Different subscribers for different event types.
SignalBus.subscribe("events:task_complete")
SignalBus.subscribe("events:agent_crashed")
```

---

## 3. Signal Envelope: Structured Communication

Raw tuples work, but they're unstructured. A signal envelope is a **standardized message format** that every
agent understands. This is what Jido uses.

```elixir
# Think of a signal envelope like an email. It has:
# - Topic: what this is about (like an email subject line)
# - Source: who sent it (like a return address)
# - Data: the actual content (like the email body)
# - Timestamp: when it was sent (for ordering and debugging)
# - Metadata: extra context (like CC recipients or priority)

defmodule AgentSignal do
  @moduledoc """
  A structured signal envelope for inter-agent communication.

  Every signal in the system has this format. This makes signals
  predictable, debuggable, and composable.
  """

  # Enforce a consistent structure using defstruct.
  # Every AgentSignal has exactly these fields — no more, no less.
  defstruct [
    :topic,       # atom: the signal topic (e.g., :research_complete, :task_assigned)
    :source,      # string: agent_id that sent this signal
    :data,        # map: the signal payload (arbitrary data)
    :timestamp,   # DateTime: when the signal was created
    metadata: %{} # map: extra context (e.g., %{priority: :high, conversation_id: "42"})
  ]

  # new/3 creates a new signal with automatic timestamp.
  # WHY: the caller shouldn't have to remember to set the timestamp.
  # Centralizing creation ensures consistency.
  def new(topic, source, data, metadata \\ %{}) do
    %__MODULE__{
      topic: topic,
      source: source,
      data: data,
      # DateTime.utc_now() gives us the current time in UTC.
      # We use UTC everywhere to avoid timezone bugs.
      timestamp: DateTime.utc_now(),
      metadata: metadata
    }
  end

  # topic_matches?/2 checks if a signal matches a given topic pattern.
  # Supports exact matches and wildcards (e.g., :research_* matches :research_complete).
  def topic_matches?(%__MODULE__{topic: signal_topic}, pattern) when is_atom(pattern) do
    signal_topic == pattern
  end

  def topic_matches?(%__MODULE__{topic: signal_topic}, pattern) when is_binary(pattern) do
    # Convert atom to string for pattern matching.
    # This lets us do things like topic_matches?(signal, "research_*")
    topic_str = Atom.to_string(signal_topic)
    String.starts_with?(topic_str, String.trim_trailing(pattern, "*"))
  end
end
```

### Publishing and Subscribing to Signals

```elixir
defmodule SignalPublisher do
  # publish/1 broadcasts an AgentSignal to its topic.
  # The topic is used as the PubSub topic name.
  # This means subscribers to that topic receive this signal.
  def publish(%AgentSignal{} = signal) do
    # Atom.to_string converts :research_complete to "research_complete".
    # We use this as the PubSub topic so subscribers can filter by topic.
    topic = Atom.to_string(signal.topic)

    Phoenix.PubSub.broadcast(
      AgenticPlatform.PubSub,
      topic,
      {:signal, signal}
    )
  end
end

defmodule SignalSubscriber do
  use GenServer

  # subscribe_to/1 subscribes this process to a specific signal topic.
  def subscribe_to(topic) do
    # Convert atom to string for the PubSub topic name.
    Phoenix.PubSub.subscribe(
      AgenticPlatform.PubSub,
      Atom.to_string(topic)
    )
  end

  # subscribe_to_all/0 subscribes to a wildcard by subscribing to multiple topics.
  # WHY: PubSub doesn't support wildcards natively, so we subscribe to known topics.
  def subscribe_to_all do
    [:task_assigned, :task_complete, :agent_crashed, :research_complete]
    |> Enum.each(&subscribe_to/1)
  end

  # handle_info catches signals arriving from PubSub.
  # We pattern-match on {:signal, %AgentSignal{}} to extract the signal.
  def handle_info({:signal, %AgentSignal{} = signal}, state) do
    # Process the signal based on its topic.
    case signal.topic do
      :task_assigned ->
        IO.puts("Agent #{state.agent_id} received task: #{inspect(signal.data)}")

      :task_complete ->
        IO.puts("Task completed by #{signal.source}: #{inspect(signal.data)}")

      :agent_crashed ->
        IO.puts("Agent #{signal.source} crashed: #{inspect(signal.data)}")

      _ ->
        IO.puts("Unknown signal topic: #{signal.topic}")
    end

    {:noreply, state}
  end
end
```

---

## 4. Directives: What Agents Do When They Receive Signals

A directive is a **command** wrapped in a signal. It tells the receiving agent exactly what to do.
This separates "what happened" (signal) from "what to do about it" (directive).

```elixir
# Think of it like a military chain of command:
# Signal: "Enemy spotted at coordinates X,Y" (information)
# Directive: "Move to coordinates X,Y and engage" (command)

defmodule AgentDirective do
  @moduledoc """
  A directive tells an agent what action to take.
  Directives are sent as signals with a :directive topic.
  """

  @type t :: %__MODULE__{
    command: atom(),
    params: map(),
    source: String.t(),
    priority: :low | :medium | :high | :urgent
  }

  defstruct [
    :command,     # atom: what to do (e.g., :pause, :resume, :process_task, :shutdown)
    :params,      # map: parameters for the command
    :source,      # string: who issued the directive
    :priority,    # atom: urgency level (default :medium)
    issued_at: nil # DateTime: when the directive was issued
  ]

  # new/3 creates a directive with a timestamp.
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

# How agents handle directives:
defmodule DirectiveHandler do
  # handle_directive/2 takes a directive and the current agent state.
  # Returns {:ok, new_state} or {:error, reason}.
  def handle_directive(%AgentDirective{command: :pause}, state) do
    # Pause the agent by changing its status.
    # The agent keeps running but stops processing new tasks.
    {:ok, %{state | status: :paused}}
  end

  def handle_directive(%AgentDirective{command: :resume}, state) do
    {:ok, %{state | status: :active}}
  end

  def handle_directive(%AgentDirective{command: :process_task, params: %{task: task}}, state) do
    # Process the task and update the state.
    result = "Processed: #{task}"
    {:ok, %{state | last_result: result, tasks_completed: state.tasks_completed + 1}}
  end

  def handle_directive(%AgentDirective{command: :shutdown}, state) do
    # Return {:stop, :shutdown} to tell GenServer to terminate.
    # This is different from a crash — it's a graceful shutdown.
    {:stop, :shutdown}
  end

  # Catch-all for unknown commands.
  # Don't crash — log and continue.
  def handle_directive(%AgentDirective{command: unknown}, state) do
    IO.puts("Unknown directive: #{unknown}")
    {:ok, state}
  end
end
```

---

## 5. Coordinating Multiple Agents

Here's how all these pieces fit together in a real multi-agent workflow:

```elixir
defmodule ResearchPipeline do
  # This module coordinates a team of agents:
  # 1. ResearchAgent: finds information
  # 2. WritingAgent: writes articles from research
  # 3. ReviewAgent: reviews articles for quality
  #
  # The flow: Research → Write → Review → Publish

  # start_pipeline/1 kicks off a research pipeline for a given topic.
  def start_pipeline(topic) do
    # Create a signal envelope for the pipeline start.
    signal = AgentSignal.new(:pipeline_start, "coordinator", %{topic: topic})

    # Broadcast to all agents — they decide if they should act on it.
    SignalPublisher.publish(signal)

    # Also send a directive to a specific research agent to start working.
    directive = AgentDirective.new(:process_task, "coordinator", %{
      task: "Research: #{topic}",
      pipeline_id: "pipeline_#{System.unique_integer([:positive])}"
    })

    # Wrap the directive in a signal and publish it.
    directive_signal = AgentSignal.new(:directive, "coordinator", %{
      directive: directive
    })

    SignalPublisher.publish(directive_signal)
  end
end

# An agent that participates in the pipeline:
defmodule ResearchAgent do
  use GenServer

  def init(agent_id) do
    # Subscribe to relevant topics on startup.
    # This agent cares about :pipeline_start and :directive signals.
    SignalSubscriber.subscribe_to(:pipeline_start)
    SignalSubscriber.subscribe_to(:directive)

    {:ok, %{agent_id: agent_id, status: :idle, research: []}}
  end

  # Handle pipeline start signals.
  def handle_info({:signal, %AgentSignal{topic: :pipeline_start} = signal}, state) do
    IO.puts("Pipeline started for topic: #{signal.data.topic}")
    {:noreply, state}
  end

  # Handle directives (commands to do something).
  def handle_info({:signal, %AgentSignal{topic: :directive, data: %{directive: directive}}}, state) do
    # Delegate to the directive handler.
    case DirectiveHandler.handle_directive(directive, state) do
      {:ok, new_state} ->
        {:noreply, new_state}

      {:stop, reason} ->
        {:stop, reason, state}
    end
  end

  # After completing research, broadcast the result.
  def complete_research(state, research_data) do
    # Publish a :research_complete signal so the WritingAgent can pick it up.
    signal = AgentSignal.new(:research_complete, state.agent_id, %{
      research: research_data
    })

    SignalPublisher.publish(signal)

    # Update state with the completed research.
    {:ok, %{state | research: [research_data | state.research]}}
  end
end
```

---

## Common Mistakes

### Mistake 1: Using direct messages for broadcast scenarios

```elixir
# WRONG: Sending to individual PIDs when you want all agents to hear the event.
# You'd need to maintain a list of all agent PIDs and send to each one.
Enum.each(all_agent_pids, fn pid -> send(pid, {:event, data}) end)

# CORRECT: Use PubSub broadcast. All subscribers receive it automatically.
Phoenix.PubSub.broadcast(AgenticPlatform.PubSub, "events", {:event, data})
```

### Mistake 2: Not including timestamp in signals

```elixir
# WRONG: A signal without a timestamp. You can't tell when it was sent,
# which makes debugging order-of-events impossible.
%{topic: :task_complete, source: "agent_1", data: %{}}

# CORRECT: Always include a timestamp in signal envelopes.
AgentSignal.new(:task_complete, "agent_1", %{result: "done"})
# The constructor automatically adds DateTime.utc_now()
```

### Mistake 3: Handling every signal in one giant function

```elixir
# WRONG: A single handle_info that pattern-matches everything.
def handle_info({:signal, signal}, state) do
  case signal.topic do
    :task_complete -> ...
    :agent_crashed -> ...
    :directive -> ...
    # ... 20 more cases
  end
end

# CORRECT: Use multiple handle_info clauses. Elixir picks the first match.
# Each clause handles one signal type. Clean, readable, maintainable.
def handle_info({:signal, %AgentSignal{topic: :task_complete} = sig}, state), do: ...
def handle_info({:signal, %AgentSignal{topic: :agent_crashed} = sig}, state), do: ...
def handle_info({:signal, %AgentSignal{topic: :directive} = sig}, state), do: ...
```

---

## Deep Dive: Why Signals > Raw Messages

Signals provide three things raw messages don't:

1. **Structure**: Every signal has the same shape. You can log it, serialize it, replay it.
2. **Metadata**: Timestamps, source tracking, priority levels — context that raw tuples lack.
3. **Composability**: Signals can carry directives, which carry commands, which carry params.
   This nesting lets you build complex workflows from simple building blocks.

This is the pattern Jido (1,722★) uses for agent communication. The BEAM's process model gives you
isolation and fault tolerance. Signals give you a shared language for agents to coordinate.

---

## Recap

| Pattern | Mechanism | Use case |
|---------|-----------|----------|
| Direct message | `send/2` | One agent → one agent |
| PubSub broadcast | `PubSub.broadcast/3` | One agent → many agents |
| Signal envelope | `%AgentSignal{}` | Structured, debuggable events |
| Directive | `%AgentDirective{}` | Commands wrapped in signals |

---

**Next:** [Module 8: Agent State & Durable Workflows](08-agent-state-durable.md) — Persist agent state and schedule background jobs.
