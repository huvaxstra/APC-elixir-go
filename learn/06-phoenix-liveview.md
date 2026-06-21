# Module 6: Phoenix LiveView Dashboard

> **Week 6** · Elixir · ~4 hours
>
> Your agent pool works. But how do you see what's happening? You need a real-time dashboard that shows
> agent status, crashes, and task counts — without writing JavaScript. Phoenix LiveView lets you build
> server-rendered, real-time UIs with zero client-side framework. The server pushes updates to the
> browser over WebSockets. Infra One uses this for fintech dashboards. Marketeam uses it for AI platform
> monitoring. You'll build one for your agents.

---

## Why LiveView (Not React/Vue/Next.js)

| Approach | How it works | Tradeoff |
|----------|-------------|----------|
| React/Vue | Client-side JS renders UI. Server sends JSON via API. | Two codebases. State sync issues. Complex build pipeline. |
| Server-rendered HTML | Server sends full HTML on every interaction. No JS needed. | Full page reload. Slow. Can't do real-time without polling. |
| **Phoenix LiveView** | Server sends initial HTML. Then a persistent WebSocket connection. Server pushes diffs. | One codebase (Elixir). Real-time by default. No JS framework. |

LiveView is **not** a compromise. For dashboards and admin UIs, it's strictly better than the alternatives.
The entire UI logic runs on the BEAM — the same process that manages your agents. No serialization boundary.

---

## Creating a Phoenix Application

```bash
# Create a new Phoenix app with LiveView support.
# --live flag includes LiveView and LiveDashboard by default.
mix phx.new agent_dashboard --live
cd agent_dashboard

# Create the database (we'll need it for agent state persistence later).
mix ecto.create
```

This generates a standard Phoenix app structure:

```
agent_dashboard/
├── lib/
│   ├── agent_dashboard/
│   │   ├── application.ex          # Application supervisor
│   │   ├── repo.ex                 # Ecto database adapter
│   │   └── agent_monitor.ex        # Our agent monitoring module
│   └── agent_dashboard_web/
│       ├── endpoint.ex             # HTTP + WebSocket entry point
│       ├── router.ex               # Route definitions
│       ├── live/
│       │   ├── dashboard_live.ex   # Our LiveView page
│       │   └── dashboard_live.html.heex  # Template
│       └── components/
│           └── layouts/
│               └── app.html.heex   # App layout
└── mix.exs
```

---

## LiveView Lifecycle: mount → handle_event → render

A LiveView is a **server-side process** that maintains a persistent WebSocket connection to the browser.
It has three main callbacks:

### 1. `mount/3` — Initialize State

```elixir
# mount/3 is called ONCE when the LiveView first connects.
# It sets up the initial state (called "assigns") for the page.
# Think of it like a component's constructor.

defmodule AgentDashboardWeb.DashboardLive do
  use AgentDashboardWeb, :live_view
  # use :live_view pulls in Phoenix.LiveView macros and imports.

  # mount/3 params: URL params, session data, socket
  # params: %{"id" => "123"} from the URL like /dashboard/123
  # session: data from the Plug session (e.g., user_id after login)
  # socket: the LiveView socket — this is your connection to the browser
  #
  # Returns: {:ok, socket} where socket has assigns set up.
  def mount(_params, _session, socket) do
    # subscribe/1 listens for PubSub messages on a topic.
    # WHEN an agent publishes an event on "agent_events", this LiveView receives it.
    # This is how server-side events push updates to the browser.
    Phoenix.PubSub.subscribe(AgentDashboard.PubSub, "agent_events")

    # assigns are an IMMUTABLE map stored in the socket.
    # When you call `assign(socket, key, value)`, Phoenix creates a NEW socket.
    # The browser only receives the CHANGED assigns (differential updates).
    {:ok, assign(socket,
      agents: %{},
      # agents: a map of agent_id => agent status data
      # We'll populate this as events come in from the agent pool.
      total_agents: 0,
      total_tasks: 0,
      events: []
      # events: a list of recent events (crashes, starts, task completions)
      # Keeps a rolling log for the dashboard to display.
    )}
  end
end
```

### 2. `handle_event/3` — Respond to User Actions

```elixir
  # handle_event/3 is called when the user interacts with the page.
  # The browser sends events over the WebSocket, and this callback processes them.
  #
  # event: string name of the event (matches phx-click="..." in the template)
  # payload: map of data from the form or button
  # socket: current socket state

  # User clicks "Start Agent" button → this fires.
  def handle_event("start_agent", %{"agent_id" => agent_id, "config" => config_str}, socket) do
    # Parse the config from JSON string to map.
    # Jason.decode!/1 will raise on invalid JSON — we handle that with a rescue block.
    config = case Jason.decode(config_str, keys: :atoms) do
      {:ok, parsed} -> parsed
      {:error, _} -> %{role: "default"}
    end

    # Start the agent through our pool (from Module 5).
    case AgentPool.start_agent(agent_id, config) do
      {:ok, pid} ->
        # Update the socket assigns with the new agent.
        # The browser will receive only the CHANGED assigns (differential update).
        agents = Map.put(socket.assigns.agents, agent_id, %{
          pid: pid,
          status: :running,
          tasks: 0
        })

        # noreply means "don't send a separate event back to the browser."
        # The socket update IS the response — Phoenix pushes the new HTML diff.
        {:noreply, assign(socket,
          agents: agents,
          total_agents: Map.size(agents)
        )}

      {:error, reason} ->
        {:noreply, put_flash(socket, :error, "Failed to start agent: #{inspect(reason)}")}
        # put_flash/2 adds a temporary message that disappears after one page load.
    end
  end

  # User clicks "Stop Agent" button → this fires.
  def handle_event("stop_agent", %{"agent_id" => agent_id}, socket) do
    AgentPool.stop_agent(agent_id)

    agents = Map.delete(socket.assigns.agents, agent_id)
    {:noreply, assign(socket,
      agents: agents,
      total_agents: Map.size(agents)
    )}
  end
```

### 3. `handle_info/2` — Respond to Server-Side Messages

```elixir
  # handle_info/2 catches messages sent to the LiveView process.
  # This is where PubSub events arrive — the bridge between agents and the UI.

  # When an agent completes a task, it publishes an event.
  # This LiveView is subscribed, so it receives the event here.
  def handle_info({:agent_event, event_type, agent_id, data}, socket) do
    # Update the agents map based on the event type.
    new_agents = case event_type do
      :task_complete ->
        # Update the task count for this agent.
        # Map.update/4 safely handles the case where the agent_id doesn't exist yet.
        Map.update(socket.assigns.agents, agent_id, nil, fn agent ->
          %{agent | tasks: agent.tasks + 1}
        end)

      :agent_crashed ->
        # Mark the agent as crashed. The supervisor will restart it,
        # but the UI should show the crash event.
        Map.update(socket.assigns.agents, agent_id, nil, fn agent ->
          %{agent | status: :crashed}
        end)

      _ -> socket.assigns.agents
    end

    # Keep a rolling log of the last 50 events.
    # The pipe operator (|>) passes the result of each function to the next.
    new_event = %{type: event_type, agent: agent_id, data: data, time: DateTime.utc_now()}
    new_events = [new_event | socket.assigns.events] |> Enum.take(50)

    {:noreply, assign(socket, agents: new_agents, events: new_events)}
  end

  # Handle agent_started events from PubSub.
  def handle_info({:agent_started, agent_id, config}, socket) do
    agents = Map.put(socket.assigns.agents, agent_id, %{
      pid: nil,
      status: :running,
      tasks: 0,
      config: config
    })

    {:noreply, assign(socket, agents: agents, total_agents: Map.size(agents))}
  end
end
```

---

## HEEx Templates: Server-Side HTML

HEEx (HTML + Embedded Elixir) is Phoenix's template engine. It looks like HTML but can embed Elixir
expressions with `<%= %>` tags and use LiveView bindings.

```heex
<!-- File: lib/agent_dashboard_web/live/dashboard_live.html.heex -->

<!-- The ~H sigil defines a HEEx template. It's a string with Elixir interpolation. -->
<!-- The outer <div> is the root element of this LiveView. -->
<div class="dashboard">
  <h1>Agent Dashboard</h1>

  <!-- Stats bar showing totals -->
  <div class="stats">
    <span>Total Agents: <%= @total_agents %></span>
    <span>Total Tasks: <%= @total_tasks %></span>
  </div>

  <!-- Agent grid: iterate over the agents map. -->
  <!-- for={ {_id, agent} } destructures each {key, value} pair from the map. -->
  <div class="agent-grid">
    <%= for {agent_id, agent} <- @agents do %>
      <div class={"agent-card #{agent.status}"}>
        <!-- String interpolation in class names: dynamic CSS classes based on status -->
        <h3><%= agent_id %></h3>
        <p>Status: <%= agent.status %></p>
        <p>Tasks: <%= agent.tasks %></p>

        <!-- phx-click binds a click event to a handle_event callback. -->
        <!-- The value attribute sends data with the event. -->
        <button
          phx-click="stop_agent"
          phx-value-agent_id={agent_id}
        >
          Stop Agent
        </button>
      </div>
    <% end %>
  </div>

  <!-- Start agent form -->
  <div class="start-form">
    <h2>Start New Agent</h2>
    <!-- phx-submit fires when the form is submitted, not on every keystroke. -->
    <form phx-submit="start_agent">
      <input type="text" name="agent_id" placeholder="Agent ID" required />
      <input type="text" name="config" placeholder='{"role": "researcher"}' />
      <button type="submit">Start Agent</button>
    </form>
  </div>

  <!-- Event log: show the last 20 events -->
  <div class="event-log">
    <h2>Recent Events</h2>
    <%= for event <- Enum.take(@events, 20) do %>
      <div class="event">
        <span class="time"><%= Calendar.strftime(event.time, "%H:%M:%S") %></span>
        <span class="type"><%= event.type %></span>
        <span class="agent"><%= event.agent %></span>
      </div>
    <% end %>
  </div>
</div>
```

---

## PubSub: Real-Time Updates

The LiveView subscribes to PubSub events in `mount/3`. When an agent publishes an event, the LiveView
receives it in `handle_info/2` and re-renders the page with new data.

```elixir
# On the agent side (in AgentWorker), publish events like this:

defmodule AgentPool.EventPublisher do
  # publish_event/3 broadcasts an event to all subscribers on the "agent_events" topic.
  # Any LiveView subscribed to this topic will receive the event in handle_info/2.
  def publish_event(event_type, agent_id, data \\ %{}) do
    # Phoenix.PubSub.broadcast/3 sends a message to ALL processes subscribed to a topic.
    # WHY: we want every connected dashboard to see the event simultaneously.
    # This is a fan-out pattern: one message, many receivers.
    Phoenix.PubSub.broadcast(
      AgenticPlatform.PubSub,
      "agent_events",
      {:agent_event, event_type, agent_id, data}
    )
  end
end

# From inside an AgentWorker, when a task completes:
def handle_info({:process_task, task}, state) do
  # ... process the task ...

  # Publish the completion event.
  # Every LiveView subscribed to "agent_events" will receive this message.
  Phoenix.PubSub.broadcast(
    AgentDashboard.PubSub,
    "agent_events",
    {:agent_event, :task_complete, state.agent_id, %{task: task}}
  )

  {:noreply, new_state}
end
```

---

## LiveDashboard: Built-in VM Monitoring

Phoenix includes `Phoenix.LiveDashboard` — a real-time monitoring UI for the BEAM VM. It shows:
- Processes (like your agents)
- ETS tables
- Memory usage
- IO and statistics
- Application supervision trees

```elixir
# Add to your router:
defmodule AgentDashboardWeb.Router do
  use AgentDashboardWeb, :router

  pipeline :browser do
    plug :accepts, ["html"]
    plug :fetch_session
    plug :fetch_live_flash
    plug :put_root_layout, html: {AgentDashboardWeb.Layouts, :root}
    plug :protect_from_forgery
    plug :put_secure_browser_headers
  end

  pipeline :api do
    plug :accepts, ["json"]
  end

  scope "/", AgentDashboardWeb do
    pipe_through :browser

    live "/", DashboardLive, :index
  end

  # LiveDashboard gives you a built-in monitoring UI at /dashboard.
  # It shows process count, memory, ETS tables, and your supervision tree.
  # In production, protect this route with authentication!
  import Phoenix.LiveDashboard.Router

  scope "/admin" do
    pipe_through :browser
    live_dashboard "/dashboard", metrics: AgentDashboardWeb.Telemetry
  end
end
```

---

## How LiveView Diffing Works

This is the key insight: **LiveView doesn't re-send the entire page on every update.**

1. User interacts → browser sends event over WebSocket
2. `handle_event` or `handle_info` updates assigns
3. Phoenix calls `render/1` with new assigns
4. Phoenix **diffs** the old HTML against the new HTML
5. Only the **changed parts** are sent over the WebSocket
6. Browser patches the DOM with the minimal changes

This is why LiveView feels like a client-side SPA — updates are instant because only small diffs travel
over the wire. But all the logic runs on the server. No client-side state management needed.

---

## Common Mistakes

### Mistake 1: Mutating assigns directly

```elixir
# WRONG: Modifying the assigns map directly.
# Phoenix can't track changes if you mutate the underlying data structure.
socket.assigns.agents["agent_1"] = %{status: :running}

# CORRECT: Use the assign/3 function to create a NEW socket.
# This triggers Phoenix's change tracking.
socket = assign(socket, agents: Map.put(socket.assigns.agents, "agent_1", %{status: :running}))
```

### Mistake 2: Blocking in handle_info

```elixir
# WRONG: Doing a slow operation in handle_info blocks the entire LiveView.
# No UI updates happen until it finishes.
def handle_info(:fetch_data, socket) do
  data = HTTPoison.get!("https://slow-api.example.com")  # Blocks for 5 seconds!
  {:noreply, assign(socket, data: data)}
end

# CORRECT: Use Task.async for slow operations.
def handle_info(:fetch_data, socket) do
  # Task.async/1 runs the function in a separate process.
  # The result arrives as a {:task_result, ref, result} message.
  Task.async(fn -> HTTPoison.get!("https://slow-api.example.com") end)
  {:noreply, assign(socket, loading: true)}
end

# Handle the result in a separate handle_info clause:
def handle_info({ref, result}, socket) when is_reference(ref) do
  Process.demonitor(ref, [:flush])  # Clean up the monitor
  {:noreply, assign(socket, data: result, loading: false)}
end
```

### Mistake 3: Subscribing in every handle_event

```elixir
# WRONG: Subscribing in every event handler.
# This creates duplicate subscriptions and memory leaks.
def handle_event("click", _, socket) do
  Phoenix.PubSub.subscribe(AgentDashboard.PubSub, "events")
  {:noreply, socket}
end

# CORRECT: Subscribe ONCE in mount/3.
# The subscription persists for the entire LiveView lifecycle.
def mount(_params, _session, socket) do
  Phoenix.PubSub.subscribe(AgentDashboard.PubSub, "agent_events")
  {:ok, socket}
end
```

---

## Deep Dive: LiveView Process Model

Each connected browser tab gets its own **LiveView process** on the server. This means:

- **Isolation**: A crash in one user's dashboard doesn't affect other users
- **State per connection**: Each tab has its own assigns — no shared mutable state
- **BEAM guarantees**: Each LiveView is a supervised process with crash recovery
- **Memory**: Each LiveView uses ~100KB of memory. For 10,000 concurrent connections, that's ~1GB.

The WebSocket connection is maintained by Phoenix.Socket, which runs in the Endpoint supervision tree.
If the WebSocket drops (user closes tab), the LiveView process terminates normally via `terminate/2`.

---

## Recap

| Concept | What it does | Key callback |
|---------|-------------|-------------|
| LiveView | Server-rendered real-time UI | `mount/3`, `render/1` |
| Assigns | Immutable state stored in the socket | `assign(socket, key, value)` |
| handle_event | Responds to user interactions | Click, form submit, keyup |
| handle_info | Responds to server-side messages | PubSub events, Task results |
| PubSub | Broadcasts events to all subscribers | `PubSub.broadcast/3`, `PubSub.subscribe/2` |
| LiveDashboard | Built-in VM monitoring | Import in router |
| HEEx | Server-side HTML templates | `<%= %>` for Elixir, `phx-click` for events |

---

**Next:** [Module 7: Agent Communication & Signals](07-agent-communication.md) — Build an event bus for agent coordination.
