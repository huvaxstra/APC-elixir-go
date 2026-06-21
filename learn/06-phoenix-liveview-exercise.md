# Module 6 Exercise: Real-Time Agent Monitoring UI

> **Estimated time:** 2 hours
>
> Build a Phoenix LiveView dashboard that shows your agent pool status in real time.
> Agents publish events, and the dashboard updates instantly — no page reloads, no JavaScript.

---

## Setup

```bash
mix phx.new agent_dashboard --live
cd agent_dashboard
mix ecto.create
```

---

## Part 1: The Event Publisher

Before the dashboard can show agent events, agents need to publish them.

**File: `lib/agent_dashboard/agent_event_publisher.ex`**

```elixir
defmodule AgentDashboard.AgentEventPublisher do
  # STARTER CODE:
  # Implement a module that broadcasts agent events via PubSub.

  # 1. topic/0
  #    - Returns the PubSub topic string: "agent_events"
  #    - HINT: def topic, do: "agent_events"

  # 2. broadcast/3
  #    - Takes event_type (atom), agent_id (string), data (map, default %{})
  #    - Calls Phoenix.PubSub.broadcast with the topic and a tuple message
  #    - The message format should be: {:agent_event, event_type, agent_id, data}
  #    - Returns the result of broadcast (usually :ok)
  #    - HINT: Use your app's PubSub name: AgentDashboard.PubSub

  # 3. subscribe/0
  #    - Subscribes the calling process to the agent_events topic
  #    - Calls Phoenix.PubSub.subscribe(AgentDashboard.PubSub, topic())
  #    - Returns :ok
end
```

---

## Part 2: The Dashboard LiveView

**File: `lib/agent_dashboard_web/live/dashboard_live.ex`**

```elixir
defmodule AgentDashboardWeb.DashboardLive do
  use AgentDashboardWeb, :live_view

  # STARTER CODE:
  # Implement the LiveView lifecycle.

  # 1. mount/3
  #    - Subscribe to "agent_events" via AgentEventPublisher.subscribe()
  #    - Set initial assigns:
  #      - agents: %{} (map of agent_id => %{status, tasks, config})
  #      - total_agents: 0
  #      - total_tasks: 0
  #      - events: [] (list of recent events, max 50)
  #    - Return {:ok, socket}
  #    - HINT: socket = assign(socket, agents: %{}, ...)

  # 2. handle_event("start_agent", %{"agent_id" => id, "config" => config_str}, socket)
  #    - Parse config from JSON (use Jason.decode with keys: :atoms)
  #    - Start agent via AgentPool.start_agent(id, config) — import your pool from Module 5
  #    - On success: update assigns with new agent, broadcast :agent_started event
  #    - On error: use put_flash to show error message
  #    - Return {:noreply, socket}

  # 3. handle_event("stop_agent", %{"agent_id" => id}, socket)
  #    - Stop agent via AgentPool.stop_agent(id)
  #    - Remove from assigns.agents
  #    - Return {:noreply, socket}

  # 4. handle_info({:agent_event, event_type, agent_id, data}, socket)
  #    - Update assigns based on event_type:
  #      :task_complete -> increment tasks for that agent
  #      :agent_crashed -> mark agent status as :crashed
  #      :agent_started -> add agent to assigns
  #    - Prepend event to assigns.events, take last 50
  #    - Return {:noreply, socket}
end
```

---

## Part 3: The HEEx Template

**File: `lib/agent_dashboard_web/live/dashboard_live.html.heex`**

```heex
<!-- STARTER CODE:
     Build the dashboard template with these sections.
     Each section has a hint for what HTML/LiveView bindings to use.
-->

<!-- Section 1: Header with stats -->
<!-- Show total_agents and total_tasks in a stats bar -->
<!-- HINT: <div class="stats"> with <%= @total_agents %> and <%= @total_tasks %> -->

<!-- Section 2: Agent grid -->
<!-- Iterate over @agents with a for loop -->
<!-- Each agent card shows: agent_id, status, tasks_completed -->
<!-- Each card has a "Stop" button with phx-click="stop_agent" -->
<!-- HINT: for={ {_id, agent} <- @agents } to destructure the map -->

<!-- Section 3: Start agent form -->
<!-- A form with phx-submit="start_agent" -->
<!-- Inputs: agent_id (text), config (text, placeholder='{"role":"researcher"}') -->
<!-- Submit button -->
<!-- HINT: <form phx-submit="start_agent"> with name="agent_id" and name="config" -->

<!-- Section 4: Event log -->
<!-- Show last 20 events from @events -->
<!-- Each event shows: time, type, agent_id -->
<!-- HINT: for event <- Enum.take(@events, 20) do -->
```

---

## Part 4: Router Configuration

**File: `lib/agent_dashboard_web/router.ex`**

```elixir
# STARTER CODE:
# Add the LiveDashboard route to your router.
#
# 1. Import LiveDashboard.Router inside the router module:
#    import Phoenix.LiveDashboard.Router
#
# 2. Add a scope for /admin with the dashboard:
#    scope "/admin" do
#      pipe_through :browser
#      live_dashboard "/dashboard", metrics: AgentDashboardWeb.Telemetry
#    end
#
# 3. Make sure the root route points to DashboardLive:
#    live "/", DashboardLive, :index
```

---

## Part 5: Test It

Start the server and test:

```bash
mix phx.server
```

Visit `http://localhost:4000` for the dashboard. Visit `http://localhost:4000/admin/dashboard` for LiveDashboard.

### Manual Tests

1. Open the dashboard in two browser tabs
2. Start an agent in tab 1 — it should appear in both tabs
3. Start another agent — both tabs update
4. Stop an agent — it disappears from both tabs
5. Click LiveDashboard — see the supervision tree and process count

---

## Hints

<details>
<summary>Hint 1: PubSub message format</summary>

The PubSub broadcast sends a tuple that arrives in `handle_info`:

```elixir
# Sending side:
Phoenix.PubSub.broadcast(AgentDashboard.PubSub, "agent_events", {:agent_event, :task_complete, "agent_1", %{}})

# Receiving side:
def handle_info({:agent_event, event_type, agent_id, data}, socket) do
  # event_type = :task_complete
  # agent_id = "agent_1"
  # data = %{}
end
```
</details>

<details>
<summary>Hint 2: Map update pattern</summary>

To update a nested value in the agents map:

```elixir
# Increment task count for a specific agent:
new_agents = Map.update(socket.assigns.agents, agent_id, nil, fn agent ->
  %{agent | tasks: agent.tasks + 1}
end)
```

The third argument (`nil`) is the default if the key doesn't exist.
</details>

<details>
<summary>Hint 3: HEEx bindings</summary>

LiveView bindings use `phx-*` attributes:

```html
<!-- Click event: -->
<button phx-click="stop_agent" phx-value-agent_id={agent_id}>Stop</button>

<!-- Form submission: -->
<form phx-submit="start_agent">
  <input name="agent_id" />
</form>

<!-- Elixir expressions: -->
<%= for {id, agent} <- @agents do %>
  <p><%= agent.status %></p>
<% end %>
```
</details>

---

## Solution

<details>
<summary>Click to reveal the complete solution</summary>

### `lib/agent_dashboard/agent_event_publisher.ex`

```elixir
defmodule AgentDashboard.AgentEventPublisher do
  @moduledoc """
  Publishes agent events to Phoenix.PubSub.
  Any process (LiveView, GenServer, Task) can subscribe to receive these events.
  """

  # topic/0 returns the PubSub topic string.
  # All publishers and subscribers must use the SAME topic string.
  def topic, do: "agent_events"

  # broadcast/3 sends an event to all subscribers.
  # event_type: atom (:task_complete, :agent_crashed, :agent_started)
  # agent_id: string identifying the agent
  # data: map with additional context (default: empty map)
  def broadcast(event_type, agent_id, data \\ %{}) do
    # Phoenix.PubSub.broadcast/3 sends to ALL processes subscribed to the topic.
    # The message is a tuple that subscribers pattern-match on in handle_info.
    Phoenix.PubSub.broadcast(
      AgentDashboard.PubSub,
      topic(),
      {:agent_event, event_type, agent_id, data}
    )
  end

  # subscribe/0 subscribes the calling process to agent events.
  # Call this in mount/3 to receive events in handle_info/2.
  def subscribe do
    Phoenix.PubSub.subscribe(AgentDashboard.PubSub, topic())
  end
end
```

### `lib/agent_dashboard_web/live/dashboard_live.ex`

```elixir
defmodule AgentDashboardWeb.DashboardLive do
  use AgentDashboardWeb, :live_view

  # mount/3 initializes the LiveView state and subscribes to events.
  # Called once when the browser connects.
  def mount(_params, _session, socket) do
    # Subscribe to agent events. Every event published to "agent_events"
    # will arrive in handle_info/2 below.
    AgentDashboard.AgentEventPublisher.subscribe()

    {:ok, assign(socket,
      agents: %{},
      total_agents: 0,
      total_tasks: 0,
      events: []
    )}
  end

  # handle_event for the "Start Agent" form submission.
  # Parses config from JSON and starts an agent via DynamicSupervisor.
  def handle_event("start_agent", %{"agent_id" => agent_id, "config" => config_str}, socket) do
    # Parse JSON config. keys: :atoms converts string keys to atoms.
    config = case Jason.decode(config_str, keys: :atoms) do
      {:ok, parsed} -> parsed
      {:error, _} -> %{role: "default"}
    end

    case AgentPool.start_agent(agent_id, config) do
      {:ok, pid} ->
        # Add the new agent to our assigns.
        agents = Map.put(socket.assigns.agents, agent_id, %{
          status: :running,
          tasks: 0,
          config: config,
          pid: pid
        })

        # Broadcast the event so other LiveViews see it too.
        AgentDashboard.AgentEventPublisher.broadcast(:agent_started, agent_id, config)

        {:noreply, assign(socket,
          agents: agents,
          total_agents: Map.size(agents)
        )}

      {:error, reason} ->
        # put_flash adds a temporary message shown once, then removed.
        {:noreply, put_flash(socket, :error, "Failed to start: #{inspect(reason)}")}
    end
  end

  # handle_event for stopping an agent.
  def handle_event("stop_agent", %{"agent_id" => agent_id}, socket) do
    AgentPool.stop_agent(agent_id)

    agents = Map.delete(socket.assigns.agents, agent_id)
    AgentDashboard.AgentEventPublisher.broadcast(:agent_stopped, agent_id)

    {:noreply, assign(socket,
      agents: agents,
      total_agents: Map.size(agents)
    )}
  end

  # handle_info catches PubSub events from the agent pool.
  # This is the real-time bridge between agents and the UI.
  def handle_info({:agent_event, event_type, agent_id, data}, socket) do
    # Update agents based on event type.
    new_agents = case event_type do
      :task_complete ->
        Map.update(socket.assigns.agents, agent_id, nil, fn agent ->
          %{agent | tasks: agent.tasks + 1}
        end)

      :agent_crashed ->
        Map.update(socket.assigns.agents, agent_id, nil, fn agent ->
          %{agent | status: :crashed}
        end)

      :agent_started ->
        Map.put(socket.assigns.agents, agent_id, %{
          status: :running,
          tasks: 0,
          config: data
        })

      :agent_stopped ->
        Map.delete(socket.assigns.agents, agent_id)

      _ -> socket.assigns.agents
    end

    # Track total tasks across all agents.
    total_tasks = new_agents
    |> Map.values()
    |> Enum.map(& &1.tasks)
    |> Enum.sum()

    # Keep last 50 events. prepend then take.
    new_event = %{type: event_type, agent: agent_id, data: data, time: DateTime.utc_now()}
    new_events = [new_event | socket.assigns.events] |> Enum.take(50)

    {:noreply, assign(socket,
      agents: new_agents,
      total_agents: Map.size(new_agents),
      total_tasks: total_tasks,
      events: new_events
    )}
  end
end
```

### `lib/agent_dashboard_web/live/dashboard_live.html.heex`

```heex
<div class="max-w-6xl mx-auto p-6">
  <h1 class="text-3xl font-bold mb-6">Agent Dashboard</h1>

  <!-- Stats bar -->
  <div class="grid grid-cols-2 gap-4 mb-8">
    <div class="bg-blue-50 p-4 rounded-lg">
      <div class="text-sm text-blue-600">Total Agents</div>
      <div class="text-2xl font-bold"><%= @total_agents %></div>
    </div>
    <div class="bg-green-50 p-4 rounded-lg">
      <div class="text-sm text-green-600">Total Tasks Completed</div>
      <div class="text-2xl font-bold"><%= @total_tasks %></div>
    </div>
  </div>

  <!-- Agent grid -->
  <div class="mb-8">
    <h2 class="text-xl font-semibold mb-4">Active Agents</h2>
    <div class="grid grid-cols-3 gap-4">
      <%= for {agent_id, agent} <- @agents do %>
        <div class={"border rounded-lg p-4 #{if agent.status == :crashed, do: "border-red-300 bg-red-50", else: "border-gray-200"}"}>
          <h3 class="font-mono font-bold"><%= agent_id %></h3>
          <p class="text-sm mt-1">
            Status:
            <span class={"font-semibold #{if agent.status == :crashed, do: "text-red-600", else: "text-green-600"}"}>
              <%= agent.status %>
            </span>
          </p>
          <p class="text-sm">Tasks: <%= agent.tasks %></p>
          <p class="text-sm text-gray-500">Role: <%= Map.get(agent.config, :role, "unknown") %></p>
          <button
            phx-click="stop_agent"
            phx-value-agent_id={agent_id}
            class="mt-3 px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600"
          >
            Stop
          </button>
        </div>
      <% end %>
    </div>
  </div>

  <!-- Start agent form -->
  <div class="mb-8">
    <h2 class="text-xl font-semibold mb-4">Start New Agent</h2>
    <form phx-submit="start_agent" class="flex gap-4 items-end">
      <div>
        <label class="block text-sm mb-1">Agent ID</label>
        <input
          type="text"
          name="agent_id"
          placeholder="agent_42"
          required
          class="border rounded px-3 py-2"
        />
      </div>
      <div>
        <label class="block text-sm mb-1">Config (JSON)</label>
        <input
          type="text"
          name="config"
          placeholder='{"role": "researcher"}'
          class="border rounded px-3 py-2 w-64"
        />
      </div>
      <button type="submit" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
        Start Agent
      </button>
    </form>
  </div>

  <!-- Event log -->
  <div>
    <h2 class="text-xl font-semibold mb-4">Recent Events</h2>
    <div class="border rounded-lg divide-y">
      <%= for event <- Enum.take(@events, 20) do %>
        <div class="px-4 py-2 flex gap-4 text-sm">
          <span class="font-mono text-gray-500 w-20">
            <%= Calendar.strftime(event.time, "%H:%M:%S") %>
          </span>
          <span class={"font-semibold w-32 #{case event.type do
            :task_complete -> "text-green-600"
            :agent_crashed -> "text-red-600"
            :agent_started -> "text-blue-600"
            _ -> "text-gray-600"
          end}"}>
            <%= event.type %>
          </span>
          <span class="font-mono"><%= event.agent %></span>
        </div>
      <% end %>
    </div>
  </div>
</div>
```

### Router addition

```elixir
# Add to lib/agent_dashboard_web/router.ex:

import Phoenix.LiveDashboard.Router

scope "/admin" do
  pipe_through :browser
  live_dashboard "/dashboard", metrics: AgentDashboardWeb.Telemetry
end
```

</details>

---

## What You've Built

- **EventPublisher**: Broadcasts agent events via PubSub
- **DashboardLive**: A real-time LiveView that shows agent status, task counts, and events
- **HEEx Template**: Server-rendered HTML with LiveView bindings
- **LiveDashboard**: Built-in VM monitoring at `/admin/dashboard`

When an agent starts, crashes, or completes a task, every connected dashboard updates instantly.
No polling. No JavaScript. Just WebSockets and the BEAM.

**Next:** [Module 7: Agent Communication & Signals](07-agent-communication.md)
