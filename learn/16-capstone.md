# Module 16: Capstone — Agentic Platform

> **Week 16 · Final Project**
> Build a complete Agentic Platform combining Elixir agent brain + Go infrastructure edge + gRPC bridge + Kubernetes deployment.

---

## Learning Objectives

By the end of this capstone, you will have:
- Built a production-grade agentic platform with real-time agent monitoring
- Implemented multi-agent supervision with hierarchical fault tolerance
- Connected Elixir and Go via gRPC with protobuf contracts
- Deployed the entire platform to Kubernetes with Terraform and Helm
- Created a portfolio project that proves job-readiness

---

## Architecture Overview

```
                         Elixir BEAM Cluster
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Supervisor   │    │  Supervisor   │    │  Supervisor   │  │
│  │(agent pool)   │    │(job queue)    │    │(dashboard)    │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │           │
│  ┌──────┴───────┐    ┌──────┴───────┐    ┌──────┴───────┐  │
│  │   Agent A    │◄──►│   Agent B    │◄──►│   Agent C    │  │
│  │  GenServer   │    │  GenServer   │    │  GenServer   │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │           │
│         └─────────┬─────────┴─────────┬─────────┘           │
│                   │                   │                     │
│             libcluster           Phoenix PubSub             │
│          (node discovery)       (agent events)              │
│                   │                                         │
│                   │ gRPC (protobuf contracts)               │
├───────────────────┴─────────────────────────────────────────┤
│                                                             │
│   ┌──────────────────────┐   ┌────────────────────────┐    │
│   │  Go K8s Operator     │   │  Go Prometheus Exporter │    │
│   │  (controller-runtime)│   │  (client_golang)        │    │
│   └──────────────────────┘   └────────────────────────┘    │
│                                                             │
│   ┌──────────────────────┐                                  │
│   │  Go CLI Tool         │                                  │
│   │  (cobra/viper)       │                                  │
│   └──────────────────────┘                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

| Component | Language | What It Does | Inspired By |
|-----------|----------|-------------|-------------|
| Agent BEAM cluster | Elixir | OTP supervision managing 1000+ agent processes | Discord, Jido |
| Multi-agent hierarchy | Elixir | Parent agents supervise child sub-agents | Sagents, Infra One |
| Agent dashboard | Elixir | Phoenix LiveView real-time monitoring UI | Marketeam |
| Durable jobs | Elixir | Oban workers for alert processing | Iteration Layer |
| Clustering | Elixir | libcluster multi-node BEAM | Remote |
| K8s operator | Go | controller-runtime CRD reconciliation | CNCF standard |
| Prometheus exporter | Go | client_golang infrastructure metrics | CNCF standard |
| CLI tool | Go | cobra single-binary management | Industry standard |
| gRPC bridge | Both | Protobuf contracts connecting runtimes | Alkahest, Spawn |
| Observability | Both | OpenTelemetry + Grafana + LiveDashboard | Marketeam |

---

## Implementation Order

**Elixir first, Go after.** The agent brain is the core — Go infra is added once agents work.

### Phase 1: Agent Core (Days 1-3)

```
project/elixir/
  agent_platform/
    lib/
      agent_platform/
        application.ex          ← Supervision tree root
        agent/
          gen_agent.ex          ← GenServer agent (Week 4)
          agent_supervisor.ex   ← DynamicSupervisor (Week 5)
          agent_registry.ex     ← Registry for discovery (Week 5)
        communication/
          signal_bus.ex         ← PubSub event bus (Week 7)
          signal.ex             ← Signal envelope struct (Week 7)
        persistence/
          agent_state.ex        ← Ecto schema (Week 8)
          repo.ex               ← Database repo
        jobs/
          alert_worker.ex       ← Oban worker (Week 8)
          health_check.ex       ← Periodic health check
    priv/repo/migrations/
      001_create_agents.sql
    mix.exs
    config/
      config.exs
      runtime.exs
```

**What to build:**
1. `GenAgent` — GenServer with state (id, status, metrics, heartbeat)
2. `AgentSupervisor` — DynamicSupervisor starting agents on demand
3. `AgentRegistry` — Name-based process discovery
4. `SignalBus` — PubSub broadcast for agent events
5. `AgentState` — Ecto schema for durable persistence
6. `AlertWorker` — Oban job processing alerts

### Phase 2: Dashboard (Days 4-5)

```
project/elixir/
  agent_platform/
    lib/
      agent_platform_web/
        live/
          dashboard_live.ex     ← LiveView dashboard
          agent_live.ex         ← Individual agent view
        components/
          dashboard.html.heex   ← Dashboard template
          agent_card.html.heex  ← Agent card component
          metrics_chart.html.heex ← Metrics display
        endpoint.ex
        router.ex
```

**What to build:**
1. `DashboardLive` — Real-time agent overview (counts, status, alerts)
2. `AgentLive` — Individual agent detail view
3. PubSub subscription for live updates
4. LiveDashboard integration for VM metrics

### Phase 3: Go Infrastructure (Days 6-8)

```
project/go/
  operator/
    main.go                    ← K8s operator entry point
    controllers/
      agent_controller.go      ← Reconciler for Agent CRD
    api/
      v1/
        agent_types.go         ← CRD type definitions
    go.mod
  exporter/
    main.go                    ← Prometheus exporter entry point
    metrics/
      agent_metrics.go         ← Custom agent metrics
    go.mod
  cli/
    cmd/
      root.go                  ← Cobra root command
      agents.go                ← Agent management commands
      status.go                ← Platform status command
    main.go
    go.mod
```

**What to build:**
1. **K8s Operator** — Watches Agent CRD, reconciles desired state
2. **Prometheus Exporter** — Exposes agent metrics at /metrics
3. **CLI Tool** — `agentctl list`, `agentctl status`, `agentctl create`

### Phase 4: Bridge (Days 9-10)

```
project/bridge/
  proto/
    agent_bridge.proto         ← Protobuf contract
  go/
    server/
      bridge_server.go         ← Go gRPC server
    go.mod
  elixir/
    lib/
      agent_platform/
        bridge/
          grpc_client.ex       ← Elixir gRPC client
```

**What to build:**
1. `agent_bridge.proto` — Shared protobuf contract
2. Go gRPC server — Reports infrastructure metrics to Elixir
3. Elixir gRPC client — Receives metrics, commands Go services

### Phase 5: Deploy (Days 11-12)

```
deploy/
  docker/
    Dockerfile.elixir           ← Multi-stage Elixir build
    Dockerfile.go               ← Multi-stage Go build
  k8s/
    namespace.yaml
    deployment-elixir.yaml
    deployment-operator.yaml
    deployment-exporter.yaml
    service-elixir.yaml
    service-exporter.yaml
    configmap.yaml
    secret.yaml
  helm/
    agent-platform/
      Chart.yaml
      values.yaml
      templates/
  terraform/
    main.tf
    variables.tf
    outputs.tf
```

**What to build:**
1. Dockerfiles (multi-stage for both Elixir and Go)
2. K8s manifests for all services
3. Helm chart for parameterized deployment
4. Terraform modules for cluster provisioning

### Phase 6: Tests & Polish (Days 13-14)

```
project/elixir/agent_platform/test/
  agent_platform/
    agent/
      gen_agent_test.exs
      agent_supervisor_test.exs
    communication/
      signal_bus_test.exs
    persistence/
      agent_state_test.exs
    web/
      dashboard_live_test.exs

project/go/operator/*_test.go
project/go/exporter/*_test.go
project/go/cli/*_test.go
```

**What to build:**
1. ExUnit tests for all Elixir modules
2. go test for all Go modules
3. Integration tests for gRPC bridge
4. LiveView tests for dashboard

---

## How Each Week's Concepts Are Used

| Week | Concept | Where in Capstone |
|------|---------|-------------------|
| 1 | Go Fundamentals | All Go code: variables, structs, interfaces |
| 2 | Go CLI & HTTP | CLI tool (cobra), health check endpoints |
| 3 | Elixir Fundamentals | All Elixir code: pattern matching, pipes |
| 4 | OTP & GenServer | GenAgent — the core agent unit |
| 5 | Multi-Agent Supervision | AgentSupervisor, AgentRegistry |
| 6 | Phoenix LiveView | DashboardLive, AgentLive |
| 7 | Agent Communication | SignalBus, signal envelopes |
| 8 | Agent State & Oban | AgentState (Ecto), AlertWorker (Oban) |
| 9 | Advanced OTP | Oban as Broadway-like pipeline |
| 10 | Clustering | libcluster multi-node agent cluster |
| 11 | Go K8s Operators | Agent CRD operator |
| 12 | Go Prometheus | Agent metrics exporter |
| 13 | gRPC Bridge | protobuf contracts, Go↔Elixir bridge |
| 14 | Observability | OpenTelemetry, Grafana, LiveDashboard |
| 15 | Deployment | Docker, K8s, Helm, Terraform |

---

## Testing Strategy

### Elixir Tests (ExUnit)

```elixir
# test/agent_platform/agent/gen_agent_test.exs
defmodule AgentPlatform.Agent.GenAgentTest do
  use ExUnit.Case

  alias AgentPlatform.Agent.GenAgent

  test "agent starts with initial state" do
    {:ok, pid} = GenAgent.start_link(id: "test-001")
    state = GenAgent.get_state(pid)
    assert state.id == "test-001"
    assert state.status == :initializing
  end

  test "agent transitions status" do
    {:ok, pid} = GenAgent.start_link(id: "test-002")
    :ok = GenAgent.update_status(pid, :running)
    state = GenAgent.get_state(pid)
    assert state.status == :running
  end

  test "agent reports heartbeat" do
    {:ok, pid} = GenAgent.start_link(id: "test-003")
    state = GenAgent.get_state(pid)
    assert %DateTime{} = state.heartbeat
  end
end
```

### Go Tests

```go
// operator/controllers/agent_controller_test.go
func TestAgentReconciler(t *testing.T) {
    reconciler := &AgentReconciler{Client: fakeClient}
    req := ctrl.Request{NamespacedName: types.NamespacedName{
        Name: "test-agent", Namespace: "default",
    }}
    result, err := reconciler.Reconcile(context.Background(), req)
    assert.NoError(t, err)
    assert.Equal(t, ctrl.Result{}, result)
}
```

---

## Deployment Steps

```bash
# 1. Build Docker images
docker build -t agent-platform:elixir -f deploy/docker/Dockerfile.elixir .
docker build -t agent-platform:operator -f deploy/docker/Dockerfile.go .

# 2. Push to registry
docker push registry.example.com/agent-platform:elixir
docker push registry.example.com/agent-platform:operator

# 3. Deploy with Helm
helm install agent-platform deploy/helm/agent-platform \
  --set image.elixir.tag=latest \
  --set image.operator.tag=latest

# 4. Verify
kubectl get pods -n agent-platform
kubectl port-forward svc/agent-platform 4000:4000
# Open http://localhost:4000/dashboard
```

---

## Success Criteria

- [ ] 1000+ agent processes running under supervision
- [ ] Dashboard shows real-time agent status (updates < 100ms)
- [ ] Agent crash → automatic restart within 1 second
- [ ] gRPC bridge passes metrics from Go to Elixir
- [ ] Prometheus exporter serves /metrics with agent data
- [ ] CLI tool can list, create, and inspect agents
- [ ] All tests pass (ExUnit + go test)
- [ ] Deployed to K8s with Terraform provisioned cluster
- [ ] Observability: traces, metrics, logs visible in Grafana

---

## Portfolio Presentation

When presenting this capstone:

1. **Show the architecture diagram** — explain Elixir/Go split
2. **Demo the dashboard** — real-time agent monitoring
3. **Kill an agent** — show automatic restart via supervision
4. **Show the CLI** — create and manage agents from terminal
5. **Show Grafana** — traces and metrics flowing
6. **Explain the gRPC bridge** — how the two runtimes communicate
7. **Reference production companies** — Discord, Jido, Remote, Infra One

This project proves you can build production-grade agentic platforms with fault tolerance, real-time monitoring, and polyglot infrastructure.
