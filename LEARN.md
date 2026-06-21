# Hybrid Elixir/Go Agentic Platform Engineering

> **Start here.** This course takes you from complete beginner to job-ready Agentic Platform Engineer in 16 weeks.

---

## Your Profile

| Field | Value |
|-------|-------|
| Current level | Complete beginner |
| Target level | Job-ready Platform Engineer / Agentic Architect / SRE |
| Languages | Go (infrastructure edge) + Elixir (agent brain) |
| Weekly commitment | 24 hours (≈ 3.5 hrs/day) |
| Prerequisites | None — this course starts from zero |

---

## What You'll Build

By week 16, you'll have built a **complete Agentic Platform** — a real-time, fault-tolerant system where:

- **Elixir/BEAM** runs the agent brain: GenServer agents with state, lifecycle, and crash recovery. Supervision trees for hierarchical fault tolerance. Phoenix LiveView for real-time dashboards. Oban for durable job processing.
- **Go** runs the infrastructure edge: K8s operators via controller-runtime. Prometheus exporters for metrics. CLI tools via cobra. gRPC bridge connecting both runtimes.
- **Together** they form a production-grade platform validated by Discord (12M users), Jido (1,722★), Sagents, Remote, Infra One, and Marketeam.

---

## Curriculum

| Week | Module | Language | What You Learn |
|------|--------|----------|----------------|
| [01](learn/01-go-fundamentals.md) | Go Fundamentals | Go | Variables, types, control flow, functions, structs, interfaces |
| [02](learn/02-go-cli-http.md) | Go CLI & HTTP | Go | cobra CLI, net/http, graceful shutdown, middleware |
| [03](learn/03-elixir-fundamentals.md) | Elixir Fundamentals | Elixir | iex, match operator, pattern matching, pipe, immutability |
| [04](learn/04-otp-genserver.md) | OTP & GenServer | Elixir | GenServer as agent unit, state, messages, lifecycle |
| [05](learn/05-multi-agent-supervision.md) | Multi-Agent Supervision | Elixir | Supervisor, DynamicSupervisor, Registry, parent-child trees |
| [06](learn/06-phoenix-liveview.md) | Phoenix LiveView Dashboard | Elixir | Real-time agent monitoring UI |
| [07](learn/07-agent-communication.md) | Agent Communication & Signals | Elixir | Process messages, PubSub, signal envelopes |
| [08](learn/08-agent-state-durable.md) | Agent State & Durable Workflows | Elixir | ETS, Ecto, Oban jobs, persistence |
| [09](learn/09-advanced-otp.md) | Advanced OTP Patterns | Elixir | :gen_statem, Task.Supervisor, GenStage, Broadway |
| [10](learn/10-clustering-distribution.md) | Clustering & Distribution | Elixir | libcluster, Erlang distribution, Horde |
| [11](learn/11-go-k8s-operators.md) | Go K8s Operators | Go | controller-runtime, reconciler, CRDs |
| [12](learn/12-go-prometheus.md) | Go Prometheus Exporters | Go | client_golang, custom metrics, RED |
| [13](learn/13-grpc-bridge.md) | Bridge: gRPC | Both | protobuf contracts, cross-language types |
| [14](learn/14-observability-stack.md) | Observability Stack | Both | OpenTelemetry, Grafana, LiveDashboard |
| [15](learn/15-production-deployment.md) | Production Deployment | Both | Docker, K8s, Helm, Terraform |
| [16](learn/16-capstone.md) | Capstone: Agentic Platform | Both | Complete platform combining everything |

---

## Learning Outcomes

After completing this course, you will be able to:

1. Build fault-tolerant agent systems using Elixir OTP (GenServer, Supervision trees, DynamicSupervisor)
2. Create real-time dashboards with Phoenix LiveView without JavaScript frameworks
3. Write Go infrastructure tools (K8s operators, Prometheus exporters, CLI tools)
4. Connect Elixir and Go via gRPC with protobuf contracts
5. Deploy a production-grade agentic platform to Kubernetes with Terraform and GitOps

---

## How to Use This Course

1. **Start with setup:** Read [00-setup.md](learn/00-setup.md) to install Go, Elixir, and tools
2. **Follow the order:** Each module builds on the previous — don't skip ahead
3. **Do every exercise:** The exercises are where learning happens
4. **Build the capstone:** Week 16 ties everything together
5. **Start each day with 30 minutes of hands-on coding** before theory

---

## Real-World Proof

This curriculum is built on production-validated patterns:

| Company | What They Proved |
|---------|-----------------|
| **Discord** | 12M concurrent users on Elixir/BEAM, 4 engineers. Go was phased out. |
| **Jido** (1,722★) | "The BEAM is the best runtime for agent systems." GenServer = atomic agent. |
| **Sagents** | Hierarchical agent supervision with parent-child trees. |
| **Remote** | 300 engineers, Elixir monolith, Distributed Erlang across K8s. |
| **Infra One** | Fintech on Elixir/BEAM. Each fund = isolated OTP process tree. |
| **Marketeam.ai** | Pure Elixir AI platform. "Reliability is the BEAM doing what it was designed to do." |
| **Iteration Layer** | TypeScript → Elixir rebuild. "AI infra becomes distributed systems infra faster than you expect." |
| **Alkahest** | Go gateway + Elixir client + gRPC bridge for Temporal workflows. |

---

## Course Structure

```
agentic-platform-course/
  LEARN.md                              ← You are here
  learn/
    00-setup.md                         ← Environment setup
    01-go-fundamentals.md               ← Week 1
    01-go-fundamentals-exercise.md
    02-go-cli-http.md                   ← Week 2
    02-go-cli-http-exercise.md
    03-elixir-fundamentals.md           ← Week 3
    03-elixir-fundamentals-exercise.md
    04-otp-genserver.md                 ← Week 4
    04-otp-genserver-exercise.md
    05-multi-agent-supervision.md       ← Week 5
    05-multi-agent-supervision-exercise.md
    06-phoenix-liveview.md              ← Week 6
    06-phoenix-liveview-exercise.md
    07-agent-communication.md           ← Week 7
    07-agent-communication-exercise.md
    08-agent-state-durable.md           ← Week 8
    08-agent-state-durable-exercise.md
    09-advanced-otp.md                  ← Week 9
    09-advanced-otp-exercise.md
    10-clustering-distribution.md       ← Week 10
    10-clustering-distribution-exercise.md
    11-go-k8s-operators.md              ← Week 11
    11-go-k8s-operators-exercise.md
    12-go-prometheus.md                 ← Week 12
    12-go-prometheus-exercise.md
    13-grpc-bridge.md                   ← Week 13
    13-grpc-bridge-exercise.md
    14-observability-stack.md           ← Week 14
    14-observability-stack-exercise.md
    15-production-deployment.md         ← Week 15
    15-production-deployment-exercise.md
    16-capstone.md                      ← Week 16
  project/
    go/                                 ← Go practice code
    elixir/                             ← Elixir practice code
    bridge/                             ← gRPC bridge code
  capstone/
    src/                                ← Capstone source
    deploy/k8s/                         ← K8s manifests
  setup/
    devcontainer/devcontainer.json      ← VS Code dev container
  deploy/
    k8s/                                ← Production K8s manifests
```

---

## Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Go | 1.26+ | Infrastructure tooling (weeks 1-2, 11-12) |
| Elixir | 1.18+ | Agent brain (weeks 3-10) |
| Erlang/OTP | 27+ | BEAM runtime (installed with Elixir) |
| Docker | 24+ | Containerization (weeks 10+) |
| kubectl | latest | K8s deployment (weeks 11+) |
| Terraform | 1.10+ | Infrastructure as Code (week 13+) |
| VS Code | latest | IDE with Go + Elixir extensions |

See [00-setup.md](learn/00-setup.md) for installation instructions.

---

<p align="center">
  <a href="https://github.com/huvaxstra/AGNT">
    <img src="https://img.shields.io/badge/Powered%20by-AGNT-2563EB?style=for-the-badge&logo=markdown&logoColor=white" alt="Powered by AGNT">
  </a>
</p>

<p align="center">
  <sub>Software Factory for the AI Era · <a href="https://github.com/huvaxstra/AGNT">github.com/huvaxstra/AGNT</a></sub>
</p>
