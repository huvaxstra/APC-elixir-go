# Module 5: Multi-Agent Supervision

<!-- FILE PURPOSE: Theory module teaching OTP supervision trees, DynamicSupervisor, Registry, and :via tuples.
     WHAT YOU'LL LEARN:
     - Why supervision trees are the backbone of fault-tolerant Elixir systems
     - The three supervision strategies and when to use each one
     - How DynamicSupervisor enables runtime agent creation/destruction
     - How Registry provides process discovery by human-readable names
     - How :via tuples connect GenServer registration to Registry
     - The parallel between OTP supervision and Kubernetes (same guarantees, 1000x faster)
     REAL-WORLD CONTEXT: Discord serves 12M users with 4 engineers using this exact pattern.
     Sagents uses hierarchical supervision trees for agent lifecycle management.
-->

> **Week 5** · Elixir · ~4 hours
>
> You already know how to build a single agent with GenServer. But real platforms need hundreds of agents
> running simultaneously, crashing independently, and recovering without taking down the system. This module
> teaches you the OTP supervision tree — the architecture that lets Discord serve 12 million users with 4 engineers.

---

## Why Supervision Matters

<!-- ANALOGY: Think of a supervision tree like a company org chart.
     Each employee (agent) has a manager (supervisor).
     If an employee gets sick (crashes), their manager handles it.
     The CEO never micromanages individual employees — they trust middle management.
-->

In technical terms: supervision trees give you **fault isolation at the process level** — the same guarantee
Kubernetes gives you at the container level, but thousands of times faster because processes are microseconds
to start, not seconds.

---

## Supervisor Strategies

A supervisor decides **how** to restart children when one crashes. There are three strategies, each solving
a different failure pattern.

### Strategy 1: `:one_for_one`

<!-- WHEN TO USE: Each child is independent. When one crashes, only that child restarts.
     ANALOGY: An apartment building where if one tenant's fridge breaks, only that apartment gets a new fridge.
     The other tenants are unaffected.
-->

```elixir
# A supervisor managing 3 independent data collection agents.
# If the Twitter scraper crashes, the Reddit scraper and email reader keep running.
# This is the most common strategy — use it when children don't depend on each other.

defmodule DataCollectionSupervisor do
  use Supervisor

  # start_link/1 starts the supervisor and links it to the calling process.
  # If the caller dies, the supervisor dies too — that's the "link" part.
  def start_link(_opts) do
    Supervisor.start_link(__MODULE__, :ok, name: __MODULE__)
  end

  # init/1 is called by Supervisor.start_link. It returns {:ok, {sup_flags, child_specs}}.
  # The supervisor processes this tuple and starts each child in order.
  def init(:ok) do
    children = [
      # Each child spec tells the supervisor: what module, what args, what restart strategy.
      {TwitterScraper, []},
      {RedditScraper, []},
      {EmailReader, []}
    ]

    # :one_for_one means: restart ONLY the crashed child. Others keep running.
    # Restart: :permanent means always restart. :temporary means never restart.
    # :transient means restart only on abnormal exit (not normal :normal exit).
    Supervisor.init(children, strategy: :one_for_one)
  end
end
```

### Strategy 2: `:one_for_all`

<!-- WHEN TO USE: When children share state or depend on each other.
     ANALOGY: A band where if the drummer quits, everyone takes a break
     because the band can't perform without a full lineup.
     The singer can't sing without rhythm.
-->

```elixir
defmodule PipelineSupervisor do
  use Supervisor

  def start_link(_opts) do
    Supervisor.start_link(__MODULE__, :ok, name: __MODULE__)
  end

  def init(:ok) do
    children = [
      {DataFetcher, []},
      {DataTransformer, []},
      {DataLoader, []}
    ]

    # :one_for_all: if DataFetcher crashes, Transformer and Loader restart too.
    # WHY: because Transformer expects output FROM Fetcher. If Fetcher crashes mid-batch,
    # Transformer's state is inconsistent. Restarting all three ensures a clean slate.
    Supervisor.init(children, strategy: :one_for_all)
  end
end
```

### Strategy 3: `:rest_for_one`

<!-- WHEN TO USE: Dependencies flow in one direction (like an assembly line).
     ANALOGY: A factory assembly line. If the stamping machine breaks, everything downstream
     (painting, packaging) needs to restart because they received incomplete products.
     But the raw material intake (started first) keeps running fine.
-->

```elixir
defmodule OrderPipeline do
  use Supervisor

  def start_link(_opts) do
    Supervisor.start_link(__MODULE__, :ok, name: __MODULE__)
  end

  def init(:ok) do
    children = [
      {InventoryTracker, []},      # Started first — independent
      {OrderValidator, []},         # Depends on InventoryTracker
      {PaymentProcessor, []},       # Depends on OrderValidator
      {ShippingManager, []}         # Depends on PaymentProcessor
    ]

    # :rest_for_one: if OrderValidator crashes, PaymentProcessor and ShippingManager restart.
    # InventoryTracker keeps running because it was started BEFORE the crashed child.
    # WHY: This is smarter than :one_for_all when only some children depend on each other.
    Supervisor.init(children, strategy: :rest_for_one)
  end
end
```

### Choosing the Right Strategy

| Strategy | When to use | Example |
|----------|-------------|---------|
| `:one_for_one` | Children are independent | Multiple data scrapers |
| `:one_for_all` | Children share state | Pipeline with shared buffer |
| `:rest_for_one` | Dependencies flow in one direction | Assembly line processing |

<!-- COMMON MISTAKE: Choosing :one_for_all when you mean :rest_for_one.
     :one_for_all restarts EVERYTHING when one child crashes. :rest_for_one only restarts
     the crashed child and those started AFTER it. If your dependencies are linear,
     :rest_for_one is more efficient because healthy upstream children keep running.
-->

---

## DynamicSupervisor: Runtime Agent Management

Static supervisors (like above) have a fixed list of children defined at startup. But agents in an agentic
platform need to be created and destroyed at runtime — a user starts a conversation, spawns an agent, and
that agent disappears when the conversation ends.

`DynamicSupervisor` is the answer. It starts with zero children and lets you add/remove children dynamically.

<!-- ANALOGY: Think of DynamicSupervisor as a temporary staffing agency.
     You tell them "I need 5 workers" and they hire them.
     You tell them "worker #3 is done" and they let them go.
     Unlike a static supervisor, there's no pre-defined roster.
-->

```elixir
defmodule AgentPool do
  # start_link/1 is the public API. It starts a DynamicSupervisor that can manage
  # an unbounded number of child processes, each started on demand.
  def start_link(_opts) do
    # DynamicSupervisor.start_link/1 starts a supervisor with NO children.
    # children are added later via start_child.
    DynamicSupervisor.start_link(
      # name: gives the process a registered name so you can find it by atom.
      name: __MODULE__,
      # strategy: :one_for_one is the ONLY strategy DynamicSupervisor supports.
      # WHY: because DynamicSupervisor manages individual processes, not a fixed tree.
      strategy: :one_for_one,
      # max_children: hard limit on concurrent children. Prevents resource exhaustion.
      # Set this based on your system's memory and CPU capacity.
      max_children: 100
    )
  end

  # start_agent/2 creates a new child process under the DynamicSupervisor.
  # agent_id: unique identifier for this agent (used for later lookup/removal).
  # config: agent-specific configuration passed to the child's start_link.
  def start_agent(agent_id, config) do
    # DynamicSupervisor.start_child/3 takes the supervisor name, a child spec,
    # and returns {:ok, pid} or {:error, reason}.
    # WHY DynamicSupervisor and not Supervisor: because agents are created at runtime,
    # not at system boot. A static supervisor requires all children at init time.
    DynamicSupervisor.start_child(
      __MODULE__,
      # A child spec is a map describing HOW to start the child process.
      # id: unique identifier (prevents duplicate specs).
      # start: {module, function, args} — the MFA tuple to call.
      # restart: :permanent means always restart (agents should persist).
      %{
        id: AgentWorker,
        start: {AgentWorker, :start_link, [agent_id, config]},
        restart: :permanent
      }
    )
  end

  # stop_agent/1 terminates a specific child by its agent_id.
  # Returns :ok if found and terminated, {:error, :not_found} otherwise.
  def stop_agent(agent_id) do
    # We need to find the PID first by looking it up in the registry.
    # This is where Registry comes in — see the next section.
    case Registry.lookup(AgentRegistry, agent_id) do
      [{pid, _}] ->
        # DynamicSupervisor.terminate_child/2 gracefully stops the child.
        # The supervisor then handles cleanup (if the child has a terminate callback).
        DynamicSupervisor.terminate_child(__MODULE__, pid)
      [] ->
        {:error, :not_found}
    end
  end
end
```

---

## Registry: Process Discovery by Name

When you start 100 agents, how do you find agent #42? You don't store PIDs in a list — PIDs change on
restart. Instead, you use `Registry` to map a human-readable name to whatever PID is currently running.

<!-- ANALOGY: Think of Registry like a phone book.
     "Call Alice" → gets you Alice's current phone number.
     If Alice changes her number, the phone book updates.
     You never need to know the actual number.
     This is the same pattern DNS uses: domain name → IP address.
-->

```elixir
# Registry is an ETS-backed process registry. ETS means it's fast — O(1) lookups
# in a concurrent table. No GenServer bottleneck for name resolution.

defmodule AgentRegistry do
  use Registry

  # start_link/1 starts the registry as part of a supervision tree.
  # keys: :unique means each key can only map to ONE process.
  #         :duplicate would allow multiple processes with the same key (pub/sub pattern).
  # partitions: number of ETS tables used internally. More partitions = more concurrency
  #   for high-throughput registries. 1 is fine for most cases.
  def start_link(_opts) do
    Registry.start_link(
      name: __MODULE__,
      keys: :unique,
      partitions: 1
    )
  end
end
```

### :via Tuples: Registering Through Registry

To register a GenServer process through Registry, pass the `:via` option when starting it.
This tells GenServer: "don't use the default registration, use Registry instead."

<!-- DEEP DIVE: The :via tuple is {Registry, AgentRegistry, "agent_42"} which means:
     "Register me in AgentRegistry under the key 'agent_42'."
     The :via mechanism is generic — you can implement your own registry module
     and pass it as {MyRegistry, name, key}. Registry is the most common implementation.
-->

```elixir
defmodule AgentWorker do
  use GenServer

  # start_link/2 is called by the DynamicSupervisor child spec.
  # The :via tuple in the name option tells GenServer to register via Registry.
  def start_link(agent_id, config) do
    GenServer.start_link(
      __MODULE__,
      {agent_id, config},
      # :via tuples let any process register itself through a custom registry.
      # The third element is the key used for lookup in the registry.
      name: {:via, Registry, {AgentRegistry, agent_id, %{} }}
    )
  end

  # init/1 is called after start_link. It sets the initial agent state.
  def init({agent_id, config}) do
    # {:ok, state} tells GenServer "I'm ready" with initial state.
    # If we returned :ignore or {:stop, reason}, the child would fail to start.
    {:ok, %{agent_id: agent_id, config: config, messages_processed: 0}}
  end

  # handle_info/2 catches messages sent via send/2 (not via GenServer.call/cast).
  # This is where external processes can talk to our agent directly.
  def handle_info({:process_task, task}, state) do
    # Update the state with the new message count.
    # Remember: state is immutable in Elixir. This creates a NEW map, not modifying the old one.
    new_state = %{state | messages_processed: state.messages_processed + 1}

    # Send a reply back to whoever sent us the task.
    # self() gives us the PID of THIS process (the agent).
    send(state.caller, {:task_complete, task, self()})

    {:noreply, new_state}
  end

  # handle_info with a catch-all clause ensures we don't crash on unexpected messages.
  # WHY: in a supervision tree, crashing means restarting. We want to be resilient.
  def handle_info(_unknown_message, state) do
    {:noreply, state}
  end
end
```

---

## Parent-Child Agent Hierarchies

Real agentic systems have **supervisor trees** — supervisors supervising supervisors, forming a hierarchy
that mirrors the problem domain.

```
Application Supervisor
├── AgentPoolSupervisor (DynamicSupervisor)
│   ├── AgentWorker (user conversation agent)
│   ├── AgentWorker (research agent)
│   └── AgentWorker (code review agent)
├── PubSub Supervisor
│   └── Phoenix.PubSub
└── WebSupervisor
    └── Endpoint
```

<!-- DEEP DIVE: The supervision tree mirrors the PROBLEM DOMAIN, not the code structure.
     If your agents are organized by function (research, writing, review),
     your supervision tree should reflect that. If they're organized by user,
     the tree should group by user. This makes crash recovery semantically meaningful.
-->

```elixir
# The application callback ties everything together into one supervision tree.
# This is the "root" supervisor that starts all other supervisors.

defmodule AgenticPlatform.Application do
  use Application

  # start/2 is called by the Erlang VM when the application boots.
  # type is :normal for standard startup, :takeover for hot code loading.
  # _type and _args are part of the OTP application callback spec.
  def start(_type, _args) do
    children = [
      # Registry must start first because other processes register in it.
      # The registry is itself supervised — if it crashes, it restarts.
      AgentRegistry,

      # DynamicSupervisor for runtime agent management.
      # This is the "agent pool" — agents are created/destroyed here.
      AgentPool,

      # PubSub for inter-agent communication (covered in Module 7).
      # This is Phoenix.PubSub — a distributed message bus.
      {Phoenix.PubSub, name: AgenticPlatform.PubSub},

      # Phoenix Endpoint for the web dashboard (covered in Module 6).
      AgenticPlatformWeb.Endpoint
    ]

    # Supervisor.start_link/2 starts the root supervisor.
    # strategy: :one_for_one is standard for application supervisors.
    # If the Endpoint crashes, it doesn't take down the AgentPool.
    Supervisor.start_link(children, strategy: :one_for_one, name: AgenticPlatform.Supervisor)
  end
end
```

---

## The Key Insight: OTP is K8s for Processes

This is the most important concept in this module:

| Kubernetes | OTP Supervisor |
|------------|----------------|
| Container | Process |
| Pod | Supervised child |
| Deployment | Supervisor |
| Cluster | BEAM node |
| Horizontal scaling | DynamicSupervisor + Registry |
| Health checks | Heartbeat monitoring |
| Restart policy | restart: :permanent |

**At the process level, OTP gives you the same guarantees K8s gives at the container level — but thousands
of times faster.** A process starts in microseconds. A container starts in seconds. A supervisor can restart
50 children in the time it takes Kubernetes to detect a single pod failure.

This is why Discord runs on Elixir: they needed to manage millions of concurrent connections, each isolated
as a process, with automatic crash recovery. Kubernetes would be too slow and too expensive for that scale.

---

## Common Mistakes

### COMMON MISTAKE 1: Not linking children to their supervisor

```elixir
# WRONG: Starting a process outside the supervision tree.
# If it crashes, nobody knows. No restart. No monitoring. It just dies.
# You've created an orphan process with no safety net.

spawn(fn -> AgentWorker.start_link("agent_1", %{}) end)

# CORRECT: Always start processes through the supervisor.
# The supervisor monitors the child and restarts it on crash.
DynamicSupervisor.start_child(AgentPool, %{
  id: AgentWorker,
  start: {AgentWorker, :start_link, ["agent_1", %{}]}
})
```

### COMMON MISTAKE 2: Using `:one_for_all` when you mean `:rest_for_one`

```elixir
# WRONG: Restarting ALL children when only downstream ones are affected.
# This wastes resources and disrupts healthy children.
Supervisor.init(children, strategy: :one_for_all)

# CORRECT: Use :rest_for_one when dependencies flow in one direction.
# Only restart the crashed child and those that depend on it.
Supervisor.init(children, strategy: :rest_for_one)
```

### COMMON MISTAKE 3: Forgetting max_children on DynamicSupervisor

```elixir
# WRONG: No limit on children. A runaway process could spawn thousands of agents
# and exhaust system memory. This is a denial-of-service waiting to happen.
DynamicSupervisor.start_link(strategy: :one_for_one)

# CORRECT: Always set a reasonable limit based on your system's capacity.
DynamicSupervisor.start_link(strategy: :one_for_one, max_children: 500)
```

### COMMON MISTAKE 4: Starting Registry after processes that need it

```elixir
# WRONG: Starting DynamicSupervisor before Registry.
# Agents try to register in a Registry that doesn't exist yet — they crash.
children = [
  AgentPool,           # Tries to register agents...
  AgentRegistry        # ...but Registry isn't started yet!
]

# CORRECT: Registry MUST start first. Order matters in supervision trees.
children = [
  AgentRegistry,       # Registry starts first — empty but ready.
  AgentPool            # DynamicSupervisor starts second — agents can register.
]
```

---

## DEEP DIVE: How Restart Strategies Actually Work

When a child crashes, the supervisor receives an EXIT signal (because they're linked). The supervisor then:

1. **Logs the crash** — you'll see it in `iex` or your logs
2. **Looks up the child spec** — finds the restart configuration
3. **Applies the strategy** — decides which children to restart
4. **Terminates affected children** — sends them EXIT signals
5. **Starts children in order** — calls their start functions again
6. **Resets crash count** — the crash counter resets after 5 seconds of stability

The crash counter matters: if a child crashes more than `max_restarts` times (default 3) within
`max_seconds` (default 5 seconds), the supervisor itself crashes and propagates up the tree.
This prevents infinite crash loops from consuming resources.

```elixir
# You can customize these thresholds:
Supervisor.init(children,
  strategy: :one_for_one,
  max_restarts: 5,    # Allow 5 restarts before giving up
  max_seconds: 10     # Within a 10-second window
)
```

<!-- DEEP DIVE: Why does the supervisor crash instead of just giving up on the child?
     Because the supervisor's PARENT needs to know something is fundamentally wrong.
     If a supervisor can't keep its children alive, it's a systemic problem.
     The parent supervisor can then try a different strategy (e.g., restart the whole subtree).
     This is the "let it crash" philosophy — failures propagate up until someone can handle them.
-->

---

## Recap

| Concept | What it does | When to use |
|---------|-------------|-------------|
| Supervisor | Manages child processes with restart strategies | Always — every process should be supervised |
| `:one_for_one` | Restart only the crashed child | Independent processes |
| `:one_for_one` | Restart all children | Shared state between children |
| `:rest_for_one` | Restart crashed + downstream | Linear dependencies |
| DynamicSupervisor | Add/remove children at runtime | Agent pools, user sessions |
| Registry | Name-to-PID mapping | Finding agents by ID |
| `:via` tuple | Register process through Registry | Any named process in a pool |

---

**Next:** [Module 6: Phoenix LiveView Dashboard](06-phoenix-liveview.md) — Build a real-time monitoring UI for your agents.
