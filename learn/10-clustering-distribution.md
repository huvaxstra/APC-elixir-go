# Module 10: Clustering & Distribution (Week 10)

## What You'll Learn This Module

By the end of this module, you'll understand how to run Elixir across multiple machines:

1. **libcluster** — automatic BEAM node discovery using DNS, Kubernetes, or gossip protocols
2. **Erlang distribution** — the `Node` module, `:rpc.call`, and how nodes communicate
3. **Horde** — distributed process registry and dynamic supervisor
4. **`:pg`** — built-in process groups for lightweight coordination
5. **Partition tolerance** — what happens when the network splits and how it heals

This module transforms your single-node agent system into a multi-node distributed platform. Remote runs their entire 300-person engineering organization on distributed Erlang across Kubernetes. Discord runs BEAM processes across nodes transparently — you can send a message to a process on any node without knowing where it lives.

---

## Why Distribution Matters for Agents

A single BEAM node can run millions of processes. But there are limits:

1. **Memory** — a node has one memory space. If your agents need more RAM than one machine has, you need multiple nodes.
2. **CPU** — BEAM uses all cores on one machine. For more parallelism, you need more machines.
3. **Fault isolation** — if one machine dies, all processes on it die. Distributing across nodes means a hardware failure only takes down a portion of your agents.
4. **Geographic distribution** — agents closer to users respond faster.

Distribution is not optional for production agent platforms. It's the next step after mastering single-node OTP.

---

## The Big Picture: How Erlang Distribution Works

Before diving into libraries, understand what happens under the hood.

Erlang nodes communicate over TCP. When you call `Node.connect(:"other@host")`, the BEAM opens a TCP connection between the two nodes. After that, processes on either node can send messages to processes on the other node — the BEAM handles the network transport transparently.

Think of it like a phone call. Once two BEAM nodes are connected, they can talk. The `Node` module is the phone, `:rpc` is the calling mechanism, and process registries are the phone book.

```
Node A (agent-brain-1@10.0.0.1)  ←→  Node B (agent-brain-2@10.0.0.2)
    │                                       │
    ├─ Process Registry                     ├─ Process Registry
    ├─ Supervisor Tree                      ├─ Supervisor Tree
    └─ ETS Tables                           └─ ETS Tables
```

Each node has its own process registry, supervisor tree, and memory. The BEAM synchronizes process names and messages across nodes.

---

## Pattern 1: libcluster — Automatic Node Discovery

### The Problem

When you start two BEAM nodes, they don't know about each other. You have to manually tell each node the other's name and host. In a dynamic environment like Kubernetes, where nodes come and go, manual configuration is impossible.

### How libcluster Solves It

libcluster automatically discovers and connects BEAM nodes using configurable strategies. It runs in your supervision tree and periodically checks for new nodes using a strategy (DNS, Kubernetes API, gossip, etc.).

### DNS Strategy

The simplest strategy for non-Kubernetes environments. libcluster queries a DNS server and connects to any BEAM nodes it finds.

```elixir
defmodule ClusterSupervisor do
  @moduledoc """
  The cluster supervisor that manages automatic node discovery.

  libcluster runs as a supervisor in your supervision tree.
  It periodically executes the configured strategy to find new nodes
  and connect to them. When nodes leave, libcluster disconnects them.

  Think of libcluster as a receptionist who automatically adds and
  removes people from a meeting room as they arrive and leave.
  """

  def child_spec(_opts) do
    # libcluster expects a list of cluster strategies
    # Each strategy has a name and configuration
    strategies = [
      # Strategy 1: DNS-based discovery
      # This works for any environment with DNS
      # libcluster queries the DNS server for A records matching a pattern
      %Cluster.Strategy.Epmd,
      %Cluster.Strategy.Gossip,
      %Cluster.Strategy.Kubernetes,
      %Cluster.Strategy.DNSPoll,
      %Cluster.Strategy.StaticNodes
    ]

    # libcluster starts its own supervisor with strategies as children
    # Each strategy runs its own polling loop
    %{
      id: Cluster.Supervisor,
      start: {Cluster.Supervisor, :start_link, [[strategies], [name: Cluster.Supervisor]]},
      type: :supervisor
    }
  end
end
```

### Kubernetes Strategy

In Kubernetes, pods are ephemeral — they start, stop, and restart. libcluster's Kubernetes strategy queries the Kubernetes API to find pods with a specific label.

```elixir
defmodule KubernetesCluster do
  @moduledoc """
  Kubernetes-based cluster strategy for libcluster.

  This strategy queries the Kubernetes API server for pods matching
  a label selector. Each pod running your application has a label
  like "app: agent-brain". libcluster finds all pods with that label
  and connects to their BEAM nodes.

  DEEP DIVE: Why Kubernetes labels instead of DNS?
  - DNS requires you to manage DNS records manually
  - Kubernetes labels are automatic — every pod gets them
  - Labels are queryable in real-time via the API
  - No DNS propagation delay
  """

  def strategy_config do
    %Cluster.Strategy.Kubernetes{
      # The Kubernetes API endpoint (usually https://kubernetes.default.svc)
      kubernetes_node_basename: "agent-brain",

      # The label selector to find pods
      # All pods with label "app=agent-brain" will be discovered
      kubernetes_selector: "app=agent-brain",

      # The Kubernetes namespace to search in
      kubernetes_namespace: "production",

      # How often to poll the Kubernetes API (in seconds)
      polling_interval: 5_000,

      # The DNS suffix for the Kubernetes service
      # Pods are reachable at: <pod-ip>.<namespace>.pod.cluster.local
      kubernetes_dns_domain: "cluster.local"
    }
  end
end
```

### Gossip Strategy

Gossip is the simplest strategy for development. Nodes broadcast their presence on a UDP multicast address. Any node listening on that address can discover others.

```elixir
# DEEP DIVE: How gossip works
# 1. Each node broadcasts its name on a multicast address
# 2. Other nodes listening on that address receive the broadcast
# 3. Nodes connect to each other
# 4. No central authority — fully decentralized
#
# Gossip is great for development and small clusters.
# For production with 10+ nodes, use DNS or Kubernetes strategy
# because gossip creates O(n²) network traffic.
#
# COMMON MISTAKE: Using gossip in production with many nodes.
# Each node broadcasts to every other node. With 10 nodes, that's
# 90 messages per broadcast cycle. With 100 nodes, it's 9,900.
# Use DNS or Kubernetes for large clusters.

%Cluster.Strategy.Gossip
```

### Static Nodes (Development)

For local development, you can hardcode node names:

```elixir
# DEEP DIVE: Static nodes is only for development.
# In production, nodes are dynamic — they come and go.
# Hardcoding node names in production means you have to restart
# all nodes when you add or remove one. That's a maintenance nightmare.

%Cluster.Strategy.StaticNodes{
  # List of node names to connect to
  nodes: [
    :"agent-brain-1@127.0.0.1",
    :"agent-brain-2@127.0.0.1",
    :"agent-brain-3@127.0.0.1"
  ]
}
```

---

## Pattern 2: The Node Module

### Basic Node Operations

The `Node` module is built into Erlang. It gives you direct control over distributed BEAM nodes.

```elixir
defmodule NodeInspector do
  @moduledoc """
  Utility module for inspecting and managing BEAM node connections.

  The Node module is built into Erlang — no dependencies needed.
  It gives you three essential operations:
  1. Identify the current node
  2. List connected nodes
  3. Connect/disconnect from other nodes
  """

  # Get the current node's name
  # Returns: atom like :"agent-brain-1@10.0.0.1"
  #
  # DEEP DIVE: The node name format is <name>@<host>.
  # The name is set when you start the BEAM with --sname or --name.
  # --sname uses short names (hostname only): --sname agent-brain-1
  # --name uses fully qualified names: --name agent-brain-1@10.0.0.1
  # Production should always use --name for cross-network communication.
  def current_node do
    Node.self()
  end

  # List all nodes connected to the current node
  # Returns: list of node name atoms
  #
  # This list changes dynamically as nodes connect and disconnect.
  # Don't cache it — always call fresh.
  def connected_nodes do
    Node.list()
  end

  # Connect to another node
  # Returns: :yes if already connected, :pong if connection succeeded, :pang if failed
  #
  # COMMON MISTAKE: Not handling the :pang return.
  # :pang means the other node is unreachable. This happens when:
  # - The node is not started yet
  # - Network is down
  # - Firewall blocks the connection
  # - Node name is wrong
  def connect_to(node_name) do
    case Node.connect(node_name) do
      :yes -> {:already_connected, node_name}
      :pong -> {:connected, node_name}
      :pang -> {:failed, node_name, "node unreachable"}
    end
  end

  # Disconnect from a node
  # Returns: true if disconnected, false if not connected
  #
  # DEEP DIVE: Disconnecting doesn't kill processes on the other node.
  # It just stops communication. The other node's processes keep running
  # but can no longer send messages to processes on this node.
  def disconnect_from(node_name) do
    Node.disconnect(node_name)
  end

  # Check if a node is alive and connected
  # Returns: true or false
  #
  # DEEP DIVE: Node.ping is different from Node.connect.
  # Node.connect establishes a connection.
  # Node.ping checks if a connection is alive.
  # Use ping for health checks, connect for establishing connections.
  def node_alive?(node_name) do
    Node.ping(node_name) == :pong
  end
end
```

### RPC — Remote Procedure Calls

`:rpc` lets you call a function on a remote node as if it were local.

```elixir
defmodule RemoteAgent do
  @moduledoc """
  Module for calling functions on remote BEAM nodes.

  RPC (Remote Procedure Call) lets you execute a function on a remote
  node and get the result back. The BEAM handles the serialization
  and network transport.

  DEEP DIVE: How RPC works under the hood
  1. You call :rpc.call(:"remote@host", Module, :function, [args])
  2. The local BEAM serializes the function and arguments
  3. The serialized data is sent over the TCP connection
  4. The remote BEAM deserializes and executes the function
  5. The result is serialized and sent back
  6. The local BEAM deserializes and returns the result
  #
  # This is different from GenServer.call which uses process messaging.
  # RPC is simpler but less fault-tolerant — if the remote node crashes
  # during execution, your caller may crash too.
  #
  # COMMON MISTAKE: Using RPC for everything.
  # RPC is convenient but dangerous in production:
  # - No backpressure — the remote node can be overwhelmed
  # - No retry — if the call fails, you have to handle it yourself
  # - No supervision — the remote function runs outside your supervision tree
  # Use GenServer.call for critical operations, RPC for convenience.

  # Call a function on a remote node
  # Returns: the function's return value, or {:error, reason}
  def call_remote(node_name, module, function, args) do
    try do
      # :rpc.call is the fundamental RPC operation
      # It returns whatever the remote function returns
      # If the remote node is unreachable, it returns :nodedown
      case :rpc.call(node_name, module, function, args) do
        {:badrpc, reason} ->
          # COMMON MISTAKE: Ignoring :badrpc errors.
          # :badrpc means the call failed. Common reasons:
          # - :nodedown — node is not connected
          # - :timeout — call took too long
          # - :no_module — module doesn't exist on remote node
          # - :no_function — function doesn't exist on remote node
          {:error, reason}

        result ->
          # Call succeeded — return the result
          result
      end
    rescue
      e ->
        {:error, Exception.message(e)}
    end
  end

  # Execute a function on ALL connected nodes
  # This is useful for distributed operations like cache invalidation
  #
  # Returns: list of {node_name, result} tuples
  def broadcast_call(module, function, args) do
    # Get all connected nodes
    nodes = Node.list()

    # Call the function on each node in parallel
    # DEEP DIVE: We use Task.async_stream for parallel execution.
    # This is important because:
    # 1. Slow nodes don't block fast nodes
    # 2. We can set a timeout for the entire operation
    # 3. Failed calls don't crash the broadcaster
    Task.async_stream(nodes, fn node ->
      result = call_remote(node, module, function, args)
      {node, result}
    end, timeout: 5_000, on_timeout: :kill_task)
    |> Enum.to_list()
  end
end
```

---

## Pattern 3: Horde — Distributed Process Registry

### The Problem

In a single BEAM node, `Registry` gives you process name registration. But `Registry` only works locally — a process registered on node A is invisible to node B.

Horde solves this by providing a **distributed process registry**. Processes registered through Horde are visible and reachable from any node in the cluster.

### How Horde Works

Horde has two components:
1. **Horde.Registry** — distributed process name registration
2. **Horde.DynamicSupervisor** — distributed process supervision

Think of Horde as a distributed phone book. When you register a process, Horde writes it in the phone book on ALL nodes. When you look up a process, Horde reads from the local copy of the phone book.

```elixir
defmodule AgentRegistry do
  @moduledoc """
  A distributed process registry for agents.

  Horde.Registry gives each agent a cluster-wide unique name.
  You can find any agent from any node by name.

  DEEP DIVE: Why Horde instead of Erlang's built-in pg2 or :pg?
  - Horde uses a CRDT (Conflict-free Replicated Data Type) for consistency
  - pg2 was deprecated in OTP 23 (replaced by :pg)
  - :pg is built-in but doesn't support distributed nodes
  - Horde works across nodes with automatic conflict resolution
  #
  # COMMON MISTAKE: Using Registry instead of Horde.Registry
  # for distributed systems. Registry only works on one node.
  # If you register a process on node A, node B can't find it.
  # Always use Horde.Registry for distributed applications.

  def child_spec(_opts) do
    %{
      id: __MODULE__,
      start: {Horde.Registry, :start_link, [
        [
          name: __MODULE__,
          # CRDT strategy determines how registry state is synced across nodes
          # DeltaCrdt is the recommended strategy for production
          # It syncs only changes (deltas) instead of the full state
          keys: :unique,
          members: :auto
        ]
      ]},
      type: :supervisor
    }
  end

  # Register a process with a unique name
  # The name must be unique across the entire cluster
  #
  # Returns: :ok or {:error, reason}
  def register_agent(agent_id, pid) do
    # DEEP DIVE: The registration key format matters.
    # We use {:agent, agent_id} as the key because:
    # 1. It's a tuple — Horde supports any term as a key
    # 2. It's namespaced — we can register other things too
    # 3. It's unique — we can't accidentally register two agents with the same ID
    case Horde.Registry.register(__MODULE__, {:agent, agent_id}, pid) do
      {:ok, _} ->
        :ok
      {:error, {:already_registered, existing_pid}} ->
        # COMMON MISTAKE: Not handling :already_registered.
        # This happens when:
        # - You try to register an ID that's already taken
        # - A previous process with the same ID crashed and the registration
        #   is still being cleaned up
        # You should either use the existing PID or wait and retry.
        {:error, {:already_registered, existing_pid}}
    end
  end

  # Look up an agent by ID
  # Returns: {:ok, pid} or :error
  #
  # This works from ANY node in the cluster.
  # Horde handles the distributed lookup automatically.
  def lookup_agent(agent_id) do
    case Horde.Registry.lookup(__MODULE__, {:agent, agent_id}) do
      [{pid, _}] ->
        # Found exactly one process with this ID
        {:ok, pid}
      [] ->
        # No process with this ID is registered
        :error
      multiple ->
        # COMMON MISTAKE: Not handling multiple registrations.
        # This shouldn't happen with :unique keys, but if it does,
        # it means the registry is in an inconsistent state.
        # Take the first one and log a warning.
        {pid, _} = List.first(multiple)
        IO.puts("[AgentRegistry] WARNING: Multiple registrations for #{agent_id}")
        {:ok, pid}
    end
  end

  # Get all registered agents across the cluster
  # Returns: list of {agent_id, pid} tuples
  #
  # DEEP DIVE: This scans the ENTIRE registry.
  # For large registries, this is expensive.
  # Consider using Horde.Registry.select/2 for pattern-based lookups
  # if you only need a subset of agents.
  def all_agents do
    Horde.Registry.select(__MODULE__, [
      # Pattern match on any key that starts with :agent
      {{{:agent, :"$1"}, :"$2", :"$3"}, [], [{{:"$1", :"$3"}}]}
    ])
  end
end
```

### Horde.DynamicSupervisor — Distributed Supervision

```elixir
defmodule AgentSupervisor do
  @moduledoc """
  A distributed supervisor for agents.

  Horde.DynamicSupervisor distributes agent processes across nodes.
  When a node joins the cluster, agents are rebalanced.
  When a node fails, its agents are restarted on surviving nodes.

  DEEP DIVE: How agent redistribution works
  1. Node A starts an agent under Horde.DynamicSupervisor
  2. Horde decides which node should host the agent (usually the node
  #    where the supervisor started it)
  3. If node A dies, Horde detects the death
  4. Horde restarts the agent on node B (or C, whichever is available)
  5. The agent's state is lost (unless you persisted it)
  #
  # COMMON MISTAKE: Assuming agent state survives node death.
  # State is in-memory on the original node. When the node dies,
  # state is gone. You MUST persist state (ETS, database, etc.)
  # if you need it to survive node failure.

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

  # Start a new agent under the distributed supervisor
  # Returns: {:ok, pid} or {:error, reason}
  #
  # The agent will be placed on the least-loaded node automatically.
  # Horde handles the node selection for you.
  def start_agent(agent_id, agent_module, args) do
    child_spec = %{
      id: {agent_module, agent_id},
      start: {agent_module, :start_link, [agent_id | args]},
      restart: :permanent
    }

    case Horde.DynamicSupervisor.start_child(__MODULE__, child_spec) do
      {:ok, pid} ->
        # Register the agent in the distributed registry
        case AgentRegistry.register_agent(agent_id, pid) do
          :ok ->
            {:ok, pid}
          {:error, reason} ->
            # Registration failed — kill the agent to avoid orphaned processes
            # COMMON MISTAKE: Not cleaning up after registration failure.
            # If you start an agent but can't register it, you have an orphan.
            # Orphaned agents consume resources and can't be found by other processes.
            GenServer.stop(pid)
            {:error, {:registration_failed, reason}}
        end

      {:error, reason} ->
        {:error, reason}
    end
  end

  # Stop an agent across the cluster
  # This works even if the agent is on a different node
  def stop_agent(agent_id) do
    case AgentRegistry.lookup_agent(agent_id) do
      {:ok, pid} ->
        # Stop the process — the supervisor will NOT restart it
        # because we use :temporary restart strategy
        GenServer.stop(pid)
        :ok

      :error ->
        {:error, :not_found}
    end
  end
end
```

---

## Pattern 4: `:pg` — Built-in Process Groups

### What Are Process Groups?

Process groups let you organize processes into named groups. Any process can join a group, and all processes in a group can communicate with each other.

Think of it like a group chat. You join a group, and when someone sends a message to the group, everyone in the group receives it.

### `:pg` vs Horde

| Feature | `:pg` | Horde.Registry |
|---|---|---|
| Scope | Local or distributed | Distributed only |
| Registration | By group name | By unique key |
| Use case | Broadcasting to a group | Finding a specific process |
| Overhead | Very low | Higher (CRDT sync) |

Use `:pg` when you need to send a message to ALL processes in a group (broadcast). Use Horde when you need to find ONE specific process (lookup).

```elixir
defmodule AgentGroups do
  @moduledoc """
  Process group management for distributed agents.

  :pg is built into OTP 23+ and provides lightweight process groups.
  Groups can span multiple nodes — perfect for broadcasting messages
  to all agents in a category.

  DEEP DIVE: :pg vs pg2
  - pg2 was removed in OTP 23
  - :pg is the replacement — it's simpler and faster
  - :pg uses ETS for local lookups (very fast)
  - :pg synchronizes group membership across nodes automatically
  #
  # COMMON MISTAKE: Using :pg for unique process registration.
  # :pg groups are for broadcasting — multiple processes can have
  # the same role in a group. For unique registration, use Horde.

  # Start the :pg scope
  # Scopes partition groups — processes in different scopes can't see each other
  def start_link do
    # DEEP DIVE: Why a custom scope?
    # The default scope is :pg. If you use the default scope,
    # your groups might conflict with other libraries that also use :pg.
    # A custom scope isolates your groups.
    :pg.start_link(:agent_groups)
  end

  # Join a process to a group
  # Returns: :ok
  #
  # A process can join multiple groups.
  # A process can join the same group multiple times (idempotent).
  def join_group(group_name, pid \\ self()) do
    :pg.join(:agent_groups, group_name, pid)
  end

  # Leave a process from a group
  # Returns: :ok
  def leave_group(group_name, pid \\ self()) do
    :pg.leave(:agent_groups, group_name, pid)
  end

  # Get all processes in a group
  # Returns: list of pids (may be empty)
  #
  # DEEP DIVE: This returns pids from ALL nodes in the cluster.
  # If node A has processes in the group and node B has processes
  # in the group, this returns all of them.
  def get_members(group_name) do
    :pg.get_members(:agent_groups, group_name)
  end

  # Broadcast a message to all processes in a group
  # This is the primary use case for process groups
  #
  # Returns: :ok
  #
  # DEEP DIVE: Why use :pg for broadcasting instead of GenServer.call?
  # 1. :pg gives you the list of members for free
  # 2. You can broadcast to N processes in parallel
  # 3. No need to know the specific pids in advance
  # 4. Members can join and leave dynamically
  def broadcast_to_group(group_name, message) do
    # Get all members of the group
    members = get_members(group_name)

    # Send the message to each member
    # DEEP DIVE: We use send/2 instead of GenServer.call/2 because:
    # 1. Broadcasting is fire-and-forget — we don't need responses
    # 2. GenServer.call would serialize the broadcasts (one at a time)
    # 3. send/2 is parallel — all members receive the message simultaneously
    Enum.each(members, fn pid ->
      send(pid, {:group_message, group_name, message})
    end)

    :ok
  end

  # Send a message to a random member of a group
  # This is useful for load balancing — distribute work across group members
  #
  # Returns: :ok or {:error, :no_members}
  def send_to_random_member(group_name, message) do
    members = get_members(group_name)

    case members do
      [] ->
        {:error, :no_members}

      members ->
        # Pick a random member
        random_member = Enum.random(members)
        send(random_member, {:group_message, group_name, message})
        :ok
    end
  end
end
```

---

## Pattern 5: Partition Tolerance and Auto-Heal

### What Is a Network Partition?

A network partition is when nodes can't communicate with each other, even though they're both running. It's like a phone line being cut — both people are alive, but they can't talk.

```
Before partition:          During partition:
Node A ←→ Node B          Node A    Node B
  ↕        ↕               ↕         ↕
Agent 1  Agent 2         Agent 1   Agent 2
```

### How BEAM Handles Partitions

The BEAM has a built-in partition detection mechanism. When nodes lose contact with each other, they mark the other node as "suspected down." If the connection isn't restored within a timeout, the node is considered "down."

This is called **auto-heal**: when the partition resolves, nodes automatically reconnect and reconcile their state.

### split_brain Protector

For production, you need a **split-brain protector**. Without it, two nodes can both think they're the primary and make conflicting decisions.

```elixir
defmodule SplitBrainProtector do
  @moduledoc """
  A split-brain protector for distributed agent systems.

  DEEP DIVE: What is split-brain?
  Split-brain occurs when a network partition makes two nodes
  think they're both the "primary." Both nodes accept writes,
  and when the partition heals, you have conflicting data.

  Analogy: Imagine two captains on a ship. The ship splits in half
  during a storm. Each captain thinks they're still in charge.
  When the storm passes and the halves reconnect, the captains
  disagree on what happened.

  The solution: only ONE node can be the primary at any time.
  This is called leader election.

  How it works:
  1. Nodes use a lock (usually in Redis or PostgreSQL) to elect a leader
  2. Only the leader accepts writes
  3. If the leader dies, another node acquires the lock and becomes leader
  4. During a partition, only the node with the lock can be leader
  #
  # COMMON MISTAKE: Not implementing split-brain protection.
  # Without it, a network partition causes data inconsistency.
  # This is the #1 cause of production distributed system failures.

  use GenServer

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  def init(opts) do
    state = %{
      # The lock backend (Redis, PostgreSQL, etc.)
      lock_backend: Keyword.fetch!(opts, :lock_backend),

      # This node's identity
      node_name: Node.self(),

      # Whether this node is currently the leader
      is_leader: false,

      # Lock timeout in milliseconds (how long to hold the lock)
      lock_timeout: Keyword.get(opts, :lock_timeout, 10_000),

      # Check interval in milliseconds (how often to refresh the lock)
      check_interval: Keyword.get(opts, :check_interval, 2_000)
    }

    # Schedule the first leadership check
    send(self(), :check_leadership)

    {:ok, state}
  end

  # Periodic leadership check
  def handle_info(:check_leadership, state) do
    case try_acquire_lock(state) do
      :acquired ->
        # We are the leader
        new_state = %{state | is_leader: true}
        notify_leadership_change(true)
        {:noreply, new_state, state.check_interval}

      :already_held ->
        # We still hold the lock — we're still the leader
        {:noreply, state, state.check_interval}

      :failed ->
        # Someone else has the lock — we're not the leader
        new_state = %{state | is_leader: false}
        notify_leadership_change(false)
        {:noreply, new_state, state.check_interval}
    end
  end

  # Check if this node is the leader
  def leader? do
    GenServer.call(__MODULE__, :leader?)
  end

  def handle_call(:leader?, _from, state) do
    {:reply, state.is_leader, state}
  end

  # Try to acquire or refresh the leadership lock
  # Returns: :acquired, :already_held, or :failed
  defp try_acquire_lock(state) do
    case state.lock_backend.try_lock("leader-lock", state.node_name, state.lock_timeout) do
      true ->
        :acquired
      false ->
        # Check if we already hold it
        case state.lock_backend.get_lock_holder("leader-lock") do
          {:ok, ^state.node_name} ->
            :already_held
          _ ->
            :failed
        end
    end
  end

  # Notify other processes when leadership changes
  defp notify_leadership_change(is_leader) do
    IO.puts("[SplitBrain] Node #{Node.self()} is now #{if is_leader, do: "LEADER", else: "FOLLOWER"}")
  end
end
```

---

## Combining Everything: A Distributed Agent Cluster

Here's how all these patterns work together in a production system:

```elixir
defmodule DistributedAgentPlatform do
  @moduledoc """
  The main application that wires all distributed components together.

  Architecture:
  1. libcluster discovers nodes automatically
  2. Horde.Registry provides distributed process names
  3. Horde.DynamicSupervisor distributes agent processes
  4. :pg provides process groups for broadcasting
  5. SplitBrainProtector ensures only one leader accepts writes

  This architecture scales to hundreds of nodes and handles
  network partitions gracefully.
  """

  use Application

  def start(_type, _args) do
    children = [
      # libcluster for automatic node discovery
      {Cluster.Supervisor, [cluster_config(), [name: Cluster.Supervisor]]},

      # Horde components for distributed processes
      AgentRegistry,
      AgentSupervisor,

      # Process groups for broadcasting
      {AgentGroups, []},

      # Split-brain protection
      {SplitBrainProtector, [
        lock_backend: RedisLockBackend,
        lock_timeout: 10_000,
        check_interval: 2_000
      ]}
    ]

    opts = [strategy: :one_for_one, name: DistributedAgentPlatform.Supervisor]
    Supervisor.start_link(children, opts)
  end

  defp cluster_config do
    [
      %Cluster.Strategy.Kubernetes{
        kubernetes_node_basename: "agent-brain",
        kubernetes_selector: "app=agent-brain",
        kubernetes_namespace: "production",
        polling_interval: 5_000
      }
    ]
  end
end
```

---

## Key Takeaways

1. **libcluster** discovers and connects nodes automatically. Use Kubernetes strategy for production, DNS for non-Kubernetes, gossip for development.

2. **Erlang distribution** gives you transparent cross-node communication. Processes on different nodes can send messages to each other as if they were local.

3. **Horde** provides distributed process registration and supervision. Use it when you need cluster-wide process names and automatic redistribution.

4. **`:pg`** provides lightweight process groups for broadcasting. Use it to send messages to all agents in a category.

5. **Partition tolerance** requires a split-brain protector. Without it, network partitions cause data inconsistency. Always have a leader election mechanism.

---

## What's Next

In Module 11, you'll learn how to manage these distributed agents using Go Kubernetes operators. The operator watches your agent CRDs and ensures the desired state matches the actual state — the Kubernetes way.
