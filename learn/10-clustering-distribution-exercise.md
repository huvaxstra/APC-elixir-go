# Module 10 Exercise: Clustering & Distribution

## What You'll Practice

By completing this exercise, you'll build a **multi-node agent cluster** that:

1. Auto-discovers nodes using libcluster
2. Registers agents with Horde.Registry
3. Distributes agents across nodes with Horde.DynamicSupervisor
4. Broadcasts messages to agent groups with :pg
5. Handles network partitions with split-brain protection

This is a production-grade distributed system — the same architecture used by Remote (300 engineers on distributed Erlang).

---

## Part 1: Node Discovery with libcluster

Configure automatic node discovery for a local development cluster.

### Starter Code

```elixir
defmodule ClusterConfig do
  @moduledoc """
  Configuration for the local development cluster.

  This module provides the libcluster strategy configuration
  for discovering other BEAM nodes on the same machine.
  """

  # TODO: Implement development_config/0
  # Return a list containing a StaticNodes strategy
  # Include these node names:
  #   :"agent-1@127.0.0.1"
  #   :"agent-2@127.0.0.1"
  #   :"agent-3@127.0.0.1"
  #
  # DEEP DIVE: StaticNodes is only for development.
  # In production, use Kubernetes or DNS strategy.
  # For this exercise, we use StaticNodes because we're
  # running multiple nodes on one machine.

  # TODO: Implement production_config/0
  # Return a list containing a Kubernetes strategy
  # Use these settings:
  #   kubernetes_node_basename: "agent-brain"
  #   kubernetes_selector: "app=agent-brain"
  #   kubernetes_namespace: "default"
  #   polling_interval: 5_000

  # COMMON MISTAKE: Forgetting to set kubernetes_namespace.
  # Without it, libcluster searches ALL namespaces and may
  # discover nodes from other applications.
end
```

### Hints

1. `Cluster.Strategy.StaticNodes` takes a `:nodes` keyword with a list of atoms
2. `Cluster.Strategy.Kubernetes` takes Kubernetes API configuration
3. Node names must include the host — use `:"name@127.0.0.1"` for local
4. Start each node with `--sname agent-1` (or `--name agent-1@127.0.0.1` for full names)

---

## Part 2: Distributed Process Registry with Horde

Build a distributed registry for agent processes.

### Starter Code

```elixir
defmodule DistributedAgentRegistry do
  @moduledoc """
  A distributed process registry for agents using Horde.

  Horde.Registry provides cluster-wide process names.
  Register an agent on node A, find it on node B.
  """

  # TODO: Implement child_spec/1
  # Return a child spec for Horde.Registry
  # Use name: __MODULE__, keys: :unique, members: :auto

  # TODO: Implement register/2
  # Parameters: agent_id (string), pid
  # Returns: :ok or {:error, reason}
  #
  # Use Horde.Registry.register/3 with key {:agent, agent_id}
  # COMMON MISTAKE: Not handling {:error, {:already_registered, pid}}.
  # This happens when an agent with the same ID is already registered.
  # Return the existing pid in this case.

  # TODO: Implement lookup/1
  # Parameters: agent_id (string)
  # Returns: {:ok, pid} or :error
  #
  # Use Horde.Registry.lookup/2 with key {:agent, agent_id}
  # Returns a list of {pid, metadata} tuples — extract the pid

  # TODO: Implement all_agents/0
  # Returns: list of {agent_id, pid} tuples
  #
  # Use Horde.Registry.select/2 to match all keys starting with :agent
  # Hint: Pattern is {{{:agent, :"$1"}, :"$2", :"$3"}, [], [{{:"$1", :"$3"}}]}

  # TODO: Implement count/0
  # Returns: integer count of registered agents
  #
  # Use all_agents/0 and count the results
end
```

### Hints

1. `Horde.Registry.register(scope, key, metadata)` registers a process
2. `Horde.Registry.lookup(scope, key)` returns `[{pid, metadata}]`
3. `Horde.Registry.select(scope, match_spec)` is for pattern-based lookups
4. Handle `{:error, {:already_registered, pid}}` — it's not a fatal error

---

## Part 3: Distributed Supervisor with Horde

Build a distributed supervisor that places agents across nodes.

### Starter Code

```elixir
defmodule DistributedAgentSupervisor do
  @moduledoc """
  A distributed supervisor for agents using Horde.

  Horde.DynamicSupervisor distributes agent processes across nodes.
  When a node joins, agents are rebalanced.
  When a node fails, agents are restarted on surviving nodes.
  """

  # TODO: Implement child_spec/1
  # Return a child spec for Horde.DynamicSupervisor
  # Use name: __MODULE__, strategy: :one_for_one, members: :auto

  # TODO: Implement start_agent/3
  # Parameters: agent_id, agent_module, args
  # Returns: {:ok, pid} or {:error, reason}
  #
  # Steps:
  #   1. Build a child spec for the agent
  #   2. Start the child under Horde.DynamicSupervisor
  #   3. Register the agent in DistributedAgentRegistry
  #   4. If registration fails, stop the agent (prevent orphans)
  #
  # COMMON MISTAKE: Not cleaning up after registration failure.
  # If you start an agent but can't register it, you have an orphan.
  # Orphaned agents consume resources and can't be found.

  # TODO: Implement stop_agent/1
  # Parameters: agent_id
  # Returns: :ok or {:error, :not_found}
  #
  # Steps:
  #   1. Look up the agent in DistributedAgentRegistry
  #   2. If found, stop the process with GenServer.stop/1
  #   3. If not found, return {:error, :not_found}

  # TODO: Implement list_agents/0
  # Returns: list of {agent_id, pid, node} tuples
  #
  # Use DistributedAgentRegistry.all_agents/0
  # For each agent, also get the node it's running on with node/1
end
```

### Hints

1. `Horde.DynamicSupervisor.start_child(supervisor, child_spec)` starts a child
2. Child spec format: `%{id: unique_id, start: {module, :start_link, args}}`
3. `GenServer.stop(pid)` stops a process without restarting it
4. `node(pid)` returns the node where a process is running

---

## Part 4: Process Groups with :pg

Build a process group system for broadcasting messages to agent categories.

### Starter Code

```elixir
defmodule AgentGroupManager do
  @moduledoc """
  Process group management for distributed agents.

  :pg provides lightweight process groups for broadcasting.
  Join a group, send a message, all members receive it.
  """

  # TODO: Implement start_link/0
  # Start :pg with a custom scope :agent_groups
  # Hint: :pg.start_link(:agent_groups)

  # TODO: Implement join/2
  # Parameters: group_name (atom), pid (default: self())
  # Returns: :ok
  #
  # Use :pg.join(:agent_groups, group_name, pid)
  # DEEP DIVE: A process can join multiple groups.
  # A process can join the same group multiple times (idempotent).

  # TODO: Implement leave/2
  # Parameters: group_name (atom), pid (default: self())
  # Returns: :ok
  #
  # Use :pg.leave(:agent_groups, group_name, pid)

  # TODO: Implement members/1
  # Parameters: group_name (atom)
  # Returns: list of pids (may be empty)
  #
  # Use :pg.get_members(:agent_groups, group_name)

  # TODO: Implement broadcast/2
  # Parameters: group_name (atom), message (any)
  # Returns: :ok
  #
  # Get all members with members/1
  # Send message to each member with send/2
  # Use tuple format: {:group_msg, group_name, message}
  #
  # COMMON MISTAKE: Using GenServer.call for broadcasting.
  # GenServer.call serializes — one member at a time.
  # send/2 is parallel — all members receive simultaneously.

  # TODO: Implement send_to_random/2
  # Parameters: group_name (atom), message (any)
  # Returns: :ok or {:error, :no_members}
  #
  # Get members, pick a random one with Enum.random/1
  # Send the message to that member

  # TODO: Implement group_size/1
  # Parameters: group_name (atom)
  # Returns: integer count of members
end
```

### Hints

1. `:pg.join(scope, group_name, pid)` joins a group
2. `:pg.get_members(scope, group_name)` returns all member pids
3. `send(pid, message)` sends a message to a process
4. `Enum.random(list)` picks a random element from a list

---

## Part 5: Integration — Distributed Agent Platform

Wire all components into a working distributed system.

### Starter Code

```elixir
defmodule DistributedAgentPlatform do
  @moduledoc """
  The main application that wires all distributed components together.

  Start order:
  1. Cluster.Supervisor (node discovery)
  2. DistributedAgentRegistry (process names)
  3. DistributedAgentSupervisor (process supervision)
  4. AgentGroupManager (process groups)
  """

  use Application

  def start(_type, _args) do
    children = [
      # TODO: Add Cluster.Supervisor
      # Pass ClusterConfig.development_config() as the strategies
      # Hint: {Cluster.Supervisor, [strategies, [name: Cluster.Supervisor]]}

      # TODO: Add DistributedAgentRegistry
      # Hint: Just the module name — child_spec is defined

      # TODO: Add DistributedAgentSupervisor
      # Hint: Just the module name — child_spec is defined

      # TODO: Add AgentGroupManager
      # Hint: Just the module name — child_spec is defined
    ]

    opts = [strategy: :one_for_one, name: DistributedAgentPlatform.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
```

### Hints

1. Start order matters — Cluster.Supervisor must start before Horde components
2. Horde.Registry and Horde.DynamicSupervisor need to be started before use
3. AgentGroupManager can start at any time — it's independent
4. Test by starting 2 nodes and verifying agent discovery

---

## Part 6: Testing Distribution Locally

To test distributed Elixir locally, start multiple nodes in separate terminals:

```bash
# Terminal 1: Start node 1
iex --sname agent-1 --cookie my_secret_cookie

# Terminal 2: Start node 2
iex --sname agent-2 --cookie my_secret_cookie

# Terminal 3: Start node 3
iex --sname agent-3 --cookie my_secret_cookie
```

Then in each terminal:

```elixir
# Terminal 1 (agent-1):
Node.connect(:"agent-2@127.0.0.1")
Node.connect(:"agent-3@127.0.0.1")
# Start the platform application
{:ok, _} = DistributedAgentPlatform.start(:normal, [])
```

```elixir
# Terminal 2 (agent-2):
Node.connect(:"agent-1@127.0.0.1")
Node.connect(:"agent-3@127.0.0.1")
# Start the platform application
{:ok, _} = DistributedAgentPlatform.start(:normal, [])
```

Verify distribution works:

```elixir
# On agent-1:
{:ok, pid} = DistributedAgentSupervisor.start_agent("sensor-1", SensorAgent, [])
IO.puts("Agent started on: #{node(pid)}")

# On agent-2:
{:ok, found_pid} = DistributedAgentRegistry.lookup("sensor-1")
IO.puts("Found agent on: #{node(found_pid)}")
# Should print: Found agent on: agent-1@127.0.0.1
```

---

## Solutions

### Solution: ClusterConfig

```elixir
defmodule ClusterConfig do
  @moduledoc """
  Configuration for the local development cluster.
  """

  def development_config do
    [
      %Cluster.Strategy.StaticNodes{
        nodes: [
          :"agent-1@127.0.0.1",
          :"agent-2@127.0.0.1",
          :"agent-3@127.0.0.1"
        ]
      }
    ]
  end

  def production_config do
    [
      %Cluster.Strategy.Kubernetes{
        kubernetes_node_basename: "agent-brain",
        kubernetes_selector: "app=agent-brain",
        kubernetes_namespace: "default",
        polling_interval: 5_000
      }
    ]
  end
end
```

### Solution: DistributedAgentRegistry

```elixir
defmodule DistributedAgentRegistry do
  @moduledoc """
  A distributed process registry for agents using Horde.
  """

  def child_spec(_opts) do
    %{
      id: __MODULE__,
      start: {Horde.Registry, :start_link, [
        [
          name: __MODULE__,
          keys: :unique,
          members: :auto
        ]
      ]},
      type: :supervisor
    }
  end

  def register(agent_id, pid) do
    case Horde.Registry.register(__MODULE__, {:agent, agent_id}, pid) do
      {:ok, _} ->
        :ok
      {:error, {:already_registered, existing_pid}} ->
        {:error, {:already_registered, existing_pid}}
    end
  end

  def lookup(agent_id) do
    case Horde.Registry.lookup(__MODULE__, {:agent, agent_id}) do
      [{pid, _}] -> {:ok, pid}
      [] -> :error
    end
  end

  def all_agents do
    Horde.Registry.select(__MODULE__, [
      {{{:agent, :"$1"}, :"$2", :"$3"}, [], [{{:"$1", :"$3"}}]}
    ])
  end

  def count do
    length(all_agents())
  end
end
```

### Solution: DistributedAgentSupervisor

```elixir
defmodule DistributedAgentSupervisor do
  @moduledoc """
  A distributed supervisor for agents using Horde.
  """

  def child_spec(_opts) do
    %{
      id: __MODULE__,
      start: {Horde.DynamicSupervisor, :start_link, [
        [
          name: __MODULE__,
          strategy: :one_for_one,
          members: :auto
        ]
      ]},
      type: :supervisor
    }
  end

  def start_agent(agent_id, agent_module, args) do
    child_spec = %{
      id: {agent_module, agent_id},
      start: {agent_module, :start_link, [agent_id | args]},
      restart: :temporary
    }

    case Horde.DynamicSupervisor.start_child(__MODULE__, child_spec) do
      {:ok, pid} ->
        case DistributedAgentRegistry.register(agent_id, pid) do
          :ok ->
            {:ok, pid}
          {:error, reason} ->
            GenServer.stop(pid)
            {:error, {:registration_failed, reason}}
        end
      {:error, reason} ->
        {:error, reason}
    end
  end

  def stop_agent(agent_id) do
    case DistributedAgentRegistry.lookup(agent_id) do
      {:ok, pid} ->
        GenServer.stop(pid)
        :ok
      :error ->
        {:error, :not_found}
    end
  end

  def list_agents do
    DistributedAgentRegistry.all_agents()
    |> Enum.map(fn {agent_id, pid} ->
      {agent_id, pid, node(pid)}
    end)
  end
end
```

### Solution: AgentGroupManager

```elixir
defmodule AgentGroupManager do
  @moduledoc """
  Process group management for distributed agents.
  """

  def start_link do
    :pg.start_link(:agent_groups)
  end

  def child_spec(_opts) do
    %{
      id: __MODULE__,
      start: {__MODULE__, :start_link, []},
      type: :worker
    }
  end

  def join(group_name, pid \\ self()) do
    :pg.join(:agent_groups, group_name, pid)
  end

  def leave(group_name, pid \\ self()) do
    :pg.leave(:agent_groups, group_name, pid)
  end

  def members(group_name) do
    :pg.get_members(:agent_groups, group_name)
  end

  def broadcast(group_name, message) do
    members(group_name)
    |> Enum.each(fn pid ->
      send(pid, {:group_msg, group_name, message})
    end)
    :ok
  end

  def send_to_random(group_name, message) do
    case members(group_name) do
      [] ->
        {:error, :no_members}
      members ->
        random_member = Enum.random(members)
        send(random_member, {:group_msg, group_name, message})
        :ok
    end
  end

  def group_size(group_name) do
    length(members(group_name))
  end
end
```

### Solution: DistributedAgentPlatform

```elixir
defmodule DistributedAgentPlatform do
  @moduledoc """
  The main application that wires all distributed components together.
  """

  use Application

  def start(_type, _args) do
    children = [
      # Cluster discovery must start first — other components may depend on it
      {Cluster.Supervisor, [ClusterConfig.development_config(), [name: Cluster.Supervisor]]},

      # Distributed process registry
      DistributedAgentRegistry,

      # Distributed supervisor
      DistributedAgentSupervisor,

      # Process groups
      AgentGroupManager
    ]

    opts = [strategy: :one_for_one, name: DistributedAgentPlatform.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
```
