<p align="center">
  <a href="https://github.com/huvaxstra/AGNT">
    <img src="https://img.shields.io/badge/Powered%20by-AGNT-2563EB?style=for-the-badge&logo=markdown&logoColor=white" alt="Powered by AGNT">
  </a>
</p>

<h1 align="center">APC-elixir-go — Hybrid Elixir/Go Agentic Platform Engineering</h1>

<p align="center">
  <strong>From complete beginner to job-ready Agentic Platform Engineer in 16 weeks.</strong><br>
  Elixir for the agent brain. Go for the infrastructure edge.<br>
  Built on patterns validated by Discord, Jido, and Remote.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Weeks-16-38bdf8?style=flat-square" alt="16 Weeks">
  <img src="https://img.shields.io/badge/Elixir-70%25-a78bfa?style=flat-square" alt="70% Elixir">
  <img src="https://img.shields.io/badge/Go-30%25-38bdf8?style=flat-square" alt="30% Go">
  <img src="https://img.shields.io/badge/Hours-24%2Fweek-34d399?style=flat-square" alt="24h/week">
  <img src="https://img.shields.io/badge/Level-Beginner%20→%20Job%20Ready-fbbf24?style=flat-square" alt="Beginner to Job Ready">
</p>

---

## What You'll Build

By week 16, you'll have built a **complete Agentic Platform** — a real-time, fault-tolerant system where:

- **Elixir/BEAM** runs the agent brain: GenServer agents with state, lifecycle, and crash recovery. Supervision trees for hierarchical fault tolerance. Phoenix LiveView for real-time dashboards. Oban for durable job processing.
- **Go** runs the infrastructure edge: K8s operators via controller-runtime. Prometheus exporters for metrics. CLI tools via cobra. gRPC bridge connecting both runtimes.
- **Together** they form a production-grade platform validated by Discord (12M users), Jido (1,722★), Sagents, Remote, Infra One, and Marketeam.

## Curriculum

| Week | Module | Language | What You Learn |
|------|--------|----------|----------------|
| [01](html/01-go-fundamentals.html) | Go Fundamentals | Go | Variables, types, control flow, functions, structs, interfaces |
| [02](html/02-go-cli-http.html) | Go CLI & HTTP | Go | cobra CLI, net/http, graceful shutdown, middleware |
| [03](html/03-elixir-fundamentals.html) | Elixir Fundamentals | Elixir | Pattern matching, pipe operator, immutability, Enum |
| [04](html/04-otp-genserver.html) | OTP & GenServer | Elixir | Agent unit, state, messages, lifecycle |
| [05](html/05-multi-agent-supervision.html) | Multi-Agent Supervision | Elixir | Supervisor, DynamicSupervisor, Registry, parent-child trees |
| [06](html/06-phoenix-liveview.html) | Phoenix LiveView Dashboard | Elixir | Real-time agent monitoring UI |
| [07](html/07-agent-communication.html) | Agent Communication & Signals | Elixir | Process messages, PubSub, signal envelopes |
| [08](html/08-agent-state-durable.html) | Agent State & Durable Workflows | Elixir | ETS, Ecto, Oban jobs, persistence |
| [09](html/09-advanced-otp.html) | Advanced OTP Patterns | Elixir | gen_statem, Task.Supervisor, GenStage, Broadway |
| [10](html/10-clustering-distribution.html) | Clustering & Distribution | Elixir | libcluster, Erlang distribution, Horde |
| [11](html/11-go-k8s-operators.html) | Go K8s Operators | Go | controller-runtime, reconciler, CRDs |
| [12](html/12-go-prometheus.html) | Go Prometheus Exporters | Go | client_golang, custom metrics, RED |
| [13](html/13-grpc-bridge.html) | Bridge: gRPC | Both | Protobuf contracts, cross-language types |
| [14](html/14-observability-stack.html) | Observability Stack | Both | OpenTelemetry, Grafana, LiveDashboard |
| [15](html/15-production-deployment.html) | Production Deployment | Both | Docker, K8s, Helm, Terraform |
| [16](html/16-capstone.html) | Capstone: Agentic Platform | Both | Complete platform combining everything |

## Quick Start

```bash
# Install Go
wget https://go.dev/dl/go1.26.4.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.26.4.linux-amd64.tar.gz

# Install Elixir + Erlang (via asdf)
asdf plugin add erlang elixir
asdf install erlang 27.3.4
asdf install elixir 1.18.4-otp-27

# Open the course
cd agentic-platform-course
python3 -m http.server 8080
# Open http://localhost:8080
```

## Real-World Proof

Every concept in this course is used in production at scale:

| Company | What They Proved |
|---------|-----------------|
| **Discord** | 12M concurrent users on Elixir/BEAM. 4 engineers. Go phased out. |
| **Jido** (1,722★) | "The BEAM is the best runtime for agent systems." GenServer = atomic agent. |
| **Remote** | 300 engineers, Elixir monolith, Distributed Erlang across K8s. |
| **Infra One** | Fintech on BEAM. Each fund = isolated OTP process tree. |
| **Marketeam.ai** | Pure Elixir AI platform. "Reliability is the BEAM doing what it was designed to do." |
| **Alkahest** | Go gateway + Elixir client + gRPC bridge. The exact architecture you'll build. |

## What You'll Master

- **OTP (GenServer + Supervision)** — the foundation of every agent
- **Phoenix + LiveView** — real-time dashboards without JavaScript
- **Go K8s Operators** — controller-runtime, CRDs, reconciler
- **Go Prometheus Exporters** — client_golang, RED metrics
- **gRPC Bridge** — protobuf contracts connecting Elixir and Go
- **libcluster** — multi-node BEAM clustering
- **OpenTelemetry** — full-stack observability
- **Docker + K8s + Terraform** — production deployment

## Course Structure

```
agentic-platform-course/
  index.html                              ← Start here
  LEARN.md                                ← Course overview
  html/                                   ← 17 interactive HTML modules
    00-setup.html
    01-go-fundamentals.html
    ...
    16-capstone.html
  learn/                                  ← 32 markdown files (theory + exercises)
    01-go-fundamentals.md
    01-go-fundamentals-exercise.md
    ...
  css/styles.css                          ← Dark theme, animations, glass morphism
  js/app.js                               ← Scroll animations, progress tracking
  scripts/md2html.py                      ← Markdown → HTML converter
```

## Features

- **Dark theme** with animated gradient background and floating particles
- **Glass morphism** cards with hover glow effects
- **Scroll-triggered** fade-in animations (Intersection Observer)
- **Syntax highlighting** for Go, Elixir, Bash, Protobuf, YAML, SQL
- **Copy-to-clipboard** on every code block
- **Collapsible** exercise solutions
- **Reading progress** bar
- **Week-by-week** navigation
- **Responsive** design (mobile → desktop)
- **`prefers-reduced-motion`** respected

## License

Free to use. Built with [AGNT](https://github.com/huvaxstra/AGNT) — Software Factory for the AI Era.

---

<p align="center">
  <a href="https://github.com/huvaxstra/AGNT">
    <img src="https://img.shields.io/badge/Powered%20by-AGNT-2563EB?style=for-the-badge&logo=markdown&logoColor=white" alt="Powered by AGNT">
  </a>
</p>

<p align="center">
  <sub>Software Factory for the AI Era · <a href="https://github.com/huvaxstra/AGNT">github.com/huvaxstra/AGNT</a></sub>
</p>
