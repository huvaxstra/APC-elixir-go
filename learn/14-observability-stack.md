# Module 14: Observability Stack (Week 14)

## What You'll Learn This Module

By the end of this module, you'll understand how to monitor a hybrid Elixir/Go system:

1. **OpenTelemetry SDKs** — instrument Go and Elixir code with traces, metrics, and logs
2. **Grafana** — build dashboards that visualize your platform's health
3. **Loki** — aggregate and query logs from both languages
4. **Phoenix LiveDashboard** — real-time Elixir-specific monitoring
5. **:telemetry** — the Elixir instrumentation library that powers LiveDashboard and OpenTelemetry

Observability is not monitoring. Monitoring tells you something is wrong. Observability tells you *why*. When an agent crashes at 3 AM, you need to trace the request from the Go gateway through gRPC to the Elixir agent, see the exact error, and understand the system state at that moment.

---

## The Problem: You Can't Fix What You Can't See

You've built agents (Elixir), infrastructure (Go), and a bridge (gRPC). But you're flying blind. When something breaks, you have to SSH into servers, grep through log files, and guess. You need:

1. **Metrics** — what is the system doing right now? (CPU, memory, request rates, error rates)
2. **Traces** — what happened during this specific request? (end-to-end journey through services)
3. **Logs** — what did each component record? (detailed events for debugging)

These three pillars are the foundation of observability.

---

## The Big Picture: Full-Stack Observability

```
┌─────────────────────────────────────────────────────────────┐
│                       Grafana                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Metrics   │  │Logs      │  │Traces    │  │LiveDash  │  │
│  │Dashboard │  │Explorer  │  │Jaeger    │  │(Elixir)  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       │              │              │              │        │
└───────┼──────────────┼──────────────┼──────────────┼────────┘
        │              │              │              │
   ┌────▼────┐    ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
   │Prometheus│    │  Loki   │   │  Jaeger  │   │ Phoenix │
   │(metrics)│    │ (logs)  │   │(traces) │   │LiveDash │
   └────┬────┘    └────┬────┘   └────┬────┘   └────┬────┘
        │              │              │              │
┌───────┼──────────────┼──────────────┼──────────────┼────────┐
│       │    Elixir BEAM + Go Services                │        │
│  ┌────▼─────────────────────────────────────────┐   │        │
│  │ OpenTelemetry SDK (traces + metrics + logs)  │   │        │
│  │ :telemetry (Elixir hooks)                    │   │        │
│  └──────────────────────────────────────────────┘   │        │
└─────────────────────────────────────────────────────┘
```

---

## Pattern 1: :telemetry — Elixir's Instrumentation Library

### What Is :telemetry?

Think of :telemetry as a set of hooks installed throughout your Elixir application. When something happens (a request arrives, a GenServer processes a message, a database query runs), the hook fires an event with measurements and metadata.

:telemetry doesn't *do* anything with the events. It just fires them. You attach handlers that decide what to do — send to Prometheus, log to Loki, or trace to Jaeger.

### How :telemetry Events Work

```elixir
# DEEP DIVE: :telemetry event anatomy
#
# Every event has three parts:
# 1. Event name — a list of atoms like [:my_app, :request, :start]
# 2. Measurements — numeric data (duration, count, size)
# 3. Metadata — contextual data (user_id, agent_id, endpoint)
#
# Think of it like a car's dashboard:
# - Event name: "engine started"
# - Measurements: RPM=3000, temperature=180, oil_pressure=40
# - Metadata: driver=john, destination=office, time=08:30
#
# The dashboard (Grafana) displays measurements.
# The GPS (Jaeger) uses metadata for tracing.
# The logbook (Loki) records everything.

# Fire a custom telemetry event
:telemetry.execute(
  # Event name — hierarchical, dot-separated via atoms
  [:agentic_platform, :agent, :task_completed],

  # Measurements — numeric values for dashboards
  %{
    duration_us: 150_000,           # how long the task took
    memory_delta_bytes: 1024,       # memory change
    tasks_total: 42                 # running count
  },

  # Metadata — context for tracing and filtering
  %{
    agent_id: 42,                   # which agent
    agent_state: "executing",       # state at the time
    task_type: "code_review",       # what kind of task
    node: Node.self()               # which BEAM node
  }
)
```

### Attaching Handlers

```elixir
defmodule AgenticPlatform.Telemetry do
  @moduledoc """
  Telemetry event handlers for the agentic platform.

  This module attaches handlers to :telemetry events. Each handler
  transforms raw events into metrics (Prometheus), logs (Loki), or
  traces (Jaeger).
  """

  require Logger

  @doc """
  Attaches all telemetry handlers. Call this in your Application.start/2.
  """
  def setup do
    # Attach a handler for agent task completion
    # WHY: We want to track task duration and success rate in Prometheus
    :telemetry.attach(
      "agentic-platform-agent-metrics",    # unique handler ID
      [:agentic_platform, :agent, :task_completed],  # event to listen to
      &handle_agent_task/4,                # callback function
      %{                                   # handler config (passed as 4th arg)
        prometheus_registry: :default
      }
    )

    # Attach a handler for gRPC call duration
    :telemetry.attach(
      "agentic-platform-grpc-metrics",
      [:agentic_platform, :grpc, :call],
      &handle_grpc_call/4,
      %{}
    )

    # Attach a handler for supervisor restarts
    :telemetry.attach(
      "agentic-platform-supervisor-restarts",
      [:agentic_platform, :supervisor, :restart],
      &handle_supervisor_restart/4,
      %{}
    )
  end

  # Handler callback for agent task completion.
  #
  # WHY: This function is called every time an agent completes a task.
  # It updates Prometheus metrics so Grafana can display them.
  #
  # PARAMETERS:
  #   - event_name: the telemetry event that fired
  #   - measurements: numeric data (duration, count, etc.)
  #   - metadata: contextual data (agent_id, task_type, etc.)
  #   - config: handler configuration (passed during attach)
  defp handle_agent_task(event_name, measurements, metadata, config) do
    # Update Prometheus counter for total tasks
    # WHY: Counter only goes up — we track total tasks completed
    Prometheus.Counter.inc(
      name: :agentic_agent_tasks_total,
      labels: %{
        agent_id: metadata.agent_id,
        task_type: metadata.task_type
      }
    )

    # Update Prometheus histogram for task duration
    # WHY: Histogram lets us calculate p50, p95, p99 latencies in Grafana
    Prometheus.Histogram.observe(
      name: :agentic_agent_task_duration_us,
      value: measurements.duration_us,
      labels: %{
        agent_id: metadata.agent_id
      }
    )

    # Log the event for Loki
    # WHY: Structured logging lets Loki index and search by any field
    Logger.info("Task completed",
      agent_id: metadata.agent_id,
      task_type: metadata.task_type,
      duration_us: measurements.duration_us,
      node: metadata.node
    )
  end

  defp handle_grpc_call(_event_name, measurements, metadata, _config) do
    # Track gRPC call duration by method
    Prometheus.Histogram.observe(
      name: :agentic_grpc_call_duration_us,
      value: measurements.duration_us,
      labels: %{
        method: metadata.method,
        status: metadata.status
      }
    )
  end

  defp handle_supervisor_restart(_event_name, measurements, metadata, _config) do
    # Track supervisor restarts — high restart counts indicate problems
    Prometheus.Counter.inc(
      name: :agentic_supervisor_restarts_total,
      labels: %{
        supervisor: metadata.supervisor,
        reason: metadata.reason
      }
    )

    # Warning log for supervisor restarts
    Logger.warning("Supervisor restart",
      supervisor: metadata.supervisor,
      reason: metadata.reason,
      count: measurements.count
    )
  end
end
```

### Instrumenting a GenServer with :telemetry

```elixir
defmodule AgenticPlatform.Agent do
  @moduledoc """
  An agent GenServer instrumented with :telemetry.

  Every operation (init, handle_call, handle_cast, handle_info)
  emits telemetry events so we can track performance and errors.
  """

  use GenServer

  require Logger

  # Client API

  def start_link(opts) do
    # Emit a telemetry event when the agent starts
    # WHY: We track agent startup time to detect slow initialization
    :telemetry.span(
      [:agentic_platform, :agent, :init],
      %{agent_id: opts[:agent_id]},
      fn ->
        result = GenServer.start_link(__MODULE__, opts,
          name: {:via, Registry, {__MODULE__, opts[:agent_id]}}
        )
        {result, %{}}
      end
    )
  end

  # Server callbacks

  @impl true
  def init(opts) do
    agent_id = Keyword.fetch!(opts, :agent_id)

    # Emit telemetry event for init duration
    :telemetry.execute(
      [:agentic_platform, :agent, :started],
      %{system_time: System.system_time()},
      %{agent_id: agent_id}
    )

    {:ok, %{
      agent_id: agent_id,
      state: "idle",
      tasks_completed: 0,
      tasks_failed: 0
    }}
  end

  @impl true
  def handle_call({:execute_task, task}, _from, state) do
    # :telemetry.span wraps a function and measures its duration
    # WHY: This automatically tracks how long the task takes
    # and whether it succeeds or fails.
    {result, _span_metadata} = :telemetry.span(
      [:agentic_platform, :agent, :task],
      %{agent_id: state.agent_id, task_type: task.type},
      fn ->
        # Simulate task execution
        outcome = execute_task_internal(task)

        # Emit additional event with measurements
        :telemetry.execute(
          [:agentic_platform, :agent, :task_completed],
          %{
            duration_us: System.monotonic_time(:microsecond),
            memory_delta_bytes: :erlang.memory(:total)
          },
          %{
            agent_id: state.agent_id,
            task_type: task.type,
            success: outcome == :ok
          }
        )

        {outcome, %{}}
      end
    )

    case result do
      :ok ->
        new_state = %{state |
          tasks_completed: state.tasks_completed + 1,
          state: "idle"
        }
        {:reply, :ok, new_state}

      {:error, reason} ->
        new_state = %{state |
          tasks_failed: state.tasks_failed + 1,
          state: "idle"
        }
        {:reply, {:error, reason}, new_state}
    end
  end

  defp execute_task_internal(task) do
    # Simulate work — in production, this calls the actual task logic
    Process.sleep(Enum.random(10..100))
    :ok
  end
end
```

---

## Pattern 2: OpenTelemetry in Go

### Go OpenTelemetry Setup

```go
package main

import (
	"context"
	"log"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.24.0"
)

// InitTracer sets up OpenTelemetry tracing for the Go service.
//
// WHY: Traces let you follow a request from the Go gateway through gRPC
// to the Elixir agent and back. Without traces, you're guessing where
// a request failed.
//
// PARAMETERS:
//   - ctx: context for the initialization (cancelled on shutdown)
//   - serviceName: name of this service in traces (e.g., "agent-gateway")
//
// RETURNS:
//   - shutdown function: call this on app shutdown to flush remaining traces
//   - error: initialization failure
func InitTracer(ctx context.Context, serviceName string) (func(), error) {
	// Create an OTLP gRPC exporter
	// WHY: OTLP is the OpenTelemetry Protocol. The exporter sends traces
	// to a collector (Jaeger, Tempo, etc.) via gRPC.
	exporter, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithEndpoint("localhost:4317"),
		otlptracegrpc.WithInsecure(),
	)
	if err != nil {
		return nil, err
	}

	// Create a resource that identifies this service
	// WHY: Every trace needs to know which service produced it.
	// Without this, you can't distinguish gateway traces from agent traces.
	res, err := resource.Merge(
		resource.Default(),
		resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceName(serviceName),
			semconv.ServiceVersion("1.0.0"),
			attribute.String("environment", "development"),
		),
	)
	if err != nil {
		return nil, err
	}

	// Create the trace provider
	// DEEP DIVE: The trace provider is the factory for tracers.
	// Each service gets one provider. The provider manages sampling,
	// export batching, and resource attribution.
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
		// Sample 100% of traces in dev, 10% in prod
		// WHY: In production, tracing every request is expensive.
		// Sampling 10% gives you representative data without the cost.
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
	)

	// Set as the global trace provider
	otel.SetTracerProvider(tp)

	// Return a shutdown function that flushes pending traces
	// COMMON MISTAKE: Forgetting to flush on shutdown — you lose the last batch of traces
	shutdown := func() {
		if err := tp.Shutdown(ctx); err != nil {
			log.Printf("Trace provider shutdown error: %v", err)
		}
	}

	return shutdown, nil
}

// TraceReportMetrics adds a span to the ReportMetrics gRPC call.
//
// WHY: When a metric report arrives, we want to trace its journey
// through the gateway. This span shows how long validation, storage,
// and acknowledgment took.
//
// PARAMETERS:
//   - ctx: parent context (from gRPC interceptors)
//   - agentID: the reporting agent's ID
//   - state: the agent's current state
//
// RETURNS:
//   - context.Context: child context with the new span
func TraceReportMetrics(ctx context.Context, agentID int64, state string) context.Context {
	// Get a tracer for this package
	// DEEP DIVE: Tracers are scoped by name. Using the package name
	// ensures all spans from this package are grouped together.
	tracer := otel.Tracer("agentic-platform/gateway")

	// Start a new span
	ctx, span := tracer.Start(ctx, "ReportMetrics",
		trace.WithAttributes(
			attribute.Int64("agent.id", agentID),
			attribute.String("agent.state", state),
		),
	)
	// The span ends when this function returns
	// WHY: Deferring span.End() ensures the span is always closed,
	// even if the function panics.
	defer span.End()

	return ctx
}
```

---

## Pattern 3: Grafana Dashboards

### Dashboard Architecture

```yaml
# grafana/dashboard-agents.yaml — Agent Overview Dashboard
# WHY: This file is provisioned automatically by Grafana. No manual import needed.

apiVersion: 1

providers:
  - name: "Agentic Platform"
    orgId: 1
    folder: "Agentic Platform"
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: false
```

### Key Panels for Agent Monitoring

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Platform Overview                     │
├───────────────┬───────────────┬───────────────┬─────────────┤
│  Active Agents│  Tasks/sec    │  Error Rate   │  P99 Latency│
│     42        │    12.5       │   0.3%        │   150ms     │
├───────────────┴───────────────┴───────────────┴─────────────┤
│  Task Duration Over Time (time series)                      │
│  ────────────────────────────────────────────────────────   │
│  ────── p50 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─     │
│  ─ ─ ─ p95 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─     │
│  ──────── p99 ── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─     │
├───────────────────────┬─────────────────────────────────────┤
│  Agent State Breakdown│  Supervisor Restarts (last 24h)     │
│  ┌─────────────────┐  │  ┌─────────────────────────────┐   │
│  │ Idle    ▓▓▓▓▓▓▓ │  │  │ AgentSupervisor: 2          │   │
│  │ Exec  ▓▓▓        │  │  │ TaskSupervisor: 0           │   │
│  │ Block ▓          │  │  │ BridgeSupervisor: 1         │   │
│  │ Plan  ▓▓         │  │  └─────────────────────────────┘   │
│  └─────────────────┘  │                                     │
└───────────────────────┴─────────────────────────────────────┘
```

### Prometheus Query Examples for Grafana

```promql
# Active agents — count of agents in any state
count(agentic_agent_tasks_total) by (agent_id)

# Task success rate — tasks completed / (completed + failed)
rate(agentic_agent_tasks_total[5m])
/
(rate(agentic_agent_tasks_total[5m]) + rate(agentic_agent_tasks_failed_total[5m]))

# P99 task latency
histogram_quantile(0.99, rate(agentic_agent_task_duration_us_bucket[5m]))

# Agent memory usage
agentic_agent_memory_bytes

# gRPC call error rate
rate(agentic_grpc_call_duration_us_count{status!="OK"}[5m])
/
rate(agentic_grpc_call_duration_us_count[5m])

# Supervisor restart rate — high values indicate instability
rate(agentic_supervisor_restarts_total[1h])
```

---

## Pattern 4: Phoenix LiveDashboard

### What LiveDashboard Shows

Phoenix LiveDashboard is a real-time monitoring dashboard built into Phoenix. It shows:

1. **OS Data** — memory usage, CPU utilization, process count
2. **ETS Tables** — which ETS tables exist and how much memory they use
3. **Processes** — all running processes, their memory, and message queues
4. **Applications** — which OTP applications are running
5. **PubSub** — PubSub connections and message rates
6. **Requests** — live request tracing (if using Phoenix)

### Enabling LiveDashboard

```elixir
# In your router.ex
defmodule AgenticPlatformWeb.Router do
  use AgenticPlatformWeb, :router

  # ... other routes ...

  # LiveDashboard — only in dev and test
  # COMMON MISTAKE: Leaving LiveDashboard enabled in production.
  # It exposes internal process information — a security risk.
  if Application.compile_env(:agentic_platform, :dev_routes) do
    import Phoenix.LiveDashboard.Router

    scope "/admin" do
      pipe_through :browser
      live_dashboard "/dashboard", metrics: AgenticPlatformWeb.Telemetry
    end
  end
end
```

### Custom LiveDashboard Metrics

```elixir
defmodule AgenticPlatformWeb.Telemetry do
  @moduledoc """
  Telemetry definitions for Phoenix LiveDashboard.

  LiveDashboard reads these metric definitions to build its
  real-time charts. Each metric is a Prometheus metric type
  with a display configuration.
  """

  use Supervisor
  import Telemetry.Metrics

  def start_link(arg) do
    Supervisor.start_link(__MODULE__, arg, name: __MODULE__)
  end

  @impl true
  def init(_arg) do
    children = [
      # Telemetry poller — periodically emits system metrics
      # WHY: LiveDashboard needs periodic events to update its charts.
      # The poller emits [:agentic_platform, :vm, :memory] every 1 second.
      {:telemetry_poller, measurements: periodic_measurements(), period: 1_000}
    ]

    Supervisor.init(children, strategy: :one_for_one)
  end

  def metrics do
    [
      # Phoenix metrics
      summary("phoenix.endpoint.start.system_time",
        unit: {:native, :millisecond}
      ),
      summary("phoenix.endpoint.stop.duration",
        unit: {:native, :millisecond}
      ),
      summary("phoenix.router_dispatch.stop.duration",
        tags: [:route],
        unit: {:native, :millisecond}
      ),

      # Agent metrics
      summary("agentic_platform.agent.task.duration",
        unit: {:native, :microsecond}
      ),
      counter("agentic_platform.agent.tasks.completed"),
      counter("agentic_platform.agent.tasks.failed"),

      # VM metrics — BEAM internal metrics
      summary("vm.memory.total", unit: {:byte, :megabyte}),
      summary("vm.total_run_queue_lengths.total"),
      summary("vm.total_run_queue_lengths.cpu"),
      summary("vm.total_run_queue_lengths.io")
    ]
  end

  defp periodic_measurements do
    [
      # Custom measurement that runs every poller tick
      # WHY: This adds agent-specific data to LiveDashboard
      {__MODULE__, :measure_agents, []}
    ]
  end

  @doc """
  Custom measurement function called by the telemetry poller.
  Returns measurements for the LiveDashboard VM panel.
  """
  def measure_agents do
    # Count active agents via Registry
    agent_count = Registry.count(AgenticPlatform.AgentRegistry)

    %{
      active_agents: agent_count
    }
  end
end
```

---

## Pattern 5: Docker Compose for Observability Stack

### docker-compose.observability.yml

```yaml
# docker-compose.observability.yml — Full observability stack
#
# WHY: This runs all observability tools locally for development.
# In production, these would be separate K8s deployments.

version: "3.8"

services:
  # Prometheus — scrapes metrics from Go and Elixir
  prometheus:
    image: prom/prometheus:latest
    container_name: agentic-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.retention.time=15d"
    # WHY: 15-day retention is enough for development. Production uses 30-90 days.

  # Grafana — dashboards and visualization
  grafana:
    image: grafana/grafana:latest
    container_name: agentic-grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/var/lib/grafana/dashboards
      - ./grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      - prometheus
      - loki

  # Loki — log aggregation
  loki:
    image: grafana/loki:latest
    container_name: agentic-loki
    ports:
      - "3100:3100"
    volumes:
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml

  # Promtail — log shipper (sends logs to Loki)
  promtail:
    image: grafana/promtail:latest
    container_name: agentic-promtail
    volumes:
      - ./promtail/promtail.yml:/etc/promtail/config.yml
      - /var/log:/var/log:ro
    command: -config.file=/etc/promtail/config.yml
    depends_on:
      - loki

  # Jaeger — distributed tracing
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: agentic-jaeger
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC receiver
      - "4318:4318"    # OTLP HTTP receiver
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    # WHY: all-in-one is fine for development. Production uses separate
    # collector, query, and storage components.

volumes:
  prometheus_data:
  grafana_data:
  loki_data:
```

### Prometheus Configuration

```yaml
# prometheus/prometheus.yml — Scrape configuration
#
# WHY: Prometheus polls (scrapes) targets at regular intervals.
# You must tell it where your Go and Elixir services are.

global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Scrape the Go gateway's Prometheus endpoint
  - job_name: "go-gateway"
    static_configs:
      - targets: ["host.docker.internal:8080"]
    # WHY: host.docker.internal reaches the host machine from inside Docker.
    # The Go gateway exposes /metrics on port 8080.

  # Scrape the Elixir application's Prometheus endpoint
  - job_name: "elixir-agents"
    static_configs:
      - targets: ["host.docker.internal:4000"]
    # WHY: Phoenix exposes /metrics if you add prometheus_plugs.

  # Scrape Prometheus itself (meta-monitoring)
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
```

### Elixir Prometheus Integration

```elixir
# In mix.exs, add the dependency:
# {:prometheus_plugs, "~> 1.0"}
# {:prometheusExporter, "~> 1.0"}

defmodule AgenticPlatformWeb.Endpoint do
  use Phoenix.Endpoint, otp_app: :agentic_platform

  # ... other plugs ...

  # Prometheus metrics endpoint
  # WHY: Prometheus scrapes this HTTP endpoint to collect metrics.
  # The plug automatically exposes BEAM VM metrics and custom metrics.
  plug Prometheus.PlugExporter
end
```

---

## Pattern 6: Structured Logging for Loki

### Elixir Structured Logging

```elixir
defmodule AgenticPlatform.Agent do
  require Logger

  def handle_task(task) do
    # Structured logging — every field is searchable in Loki
    # WHY: Loki indexes labels, not full text. Structured fields become
    # labels that you can filter by in Grafana's Log Explorer.
    Logger.info("Processing task",
      agent_id: 42,
      task_type: task.type,
      task_id: task.id,
      priority: task.priority
    )

    case execute(task) do
      {:ok, result} ->
        Logger.info("Task completed",
          agent_id: 42,
          task_id: task.id,
          duration_ms: result.duration_ms
        )

      {:error, reason} ->
        # Error logs get a stack trace automatically
        # COMMON MISTAKE: Using Logger.error without structured fields.
        # Unstructured logs are hard to search in Loki.
        Logger.error("Task failed",
          agent_id: 42,
          task_id: task.id,
          error: reason
        )
    end
  end
end
```

### Go Structured Logging

```go
package main

import (
	"log/slog"
)

func processTask(task Task) error {
	// Structured logging with slog (Go 1.21+)
	// WHY: slog is the standard library structured logger.
	// It outputs JSON that Loki can parse and index.
	slog.Info("Processing task",
		slog.Int64("agent_id", 42),
		slog.String("task_type", task.Type),
		slog.String("task_id", task.ID),
		slog.Int("priority", task.Priority),
	)

	// Common mistake: using fmt.Println instead of slog
	// fmt.Println outputs to stdout without structure.
	// Loki can't parse unstructured text reliably.

	err := executeTask(task)
	if err != nil {
		slog.Error("Task failed",
			slog.Int64("agent_id", 42),
			slog.String("task_id", task.ID),
			slog.String("error", err.Error()),
		)
		return err
	}

	return nil
}
```

### Loki LogQL Queries

```
# Find all errors from agent 42
{job="elixir-agents"} | json | agent_id="42" | level="error"

# Find slow tasks (> 1 second)
{job="elixir-agents"} | json | duration_ms > 1000

# Find all gRPC call failures
{job="go-gateway"} | json | status!="OK"

# Count errors per agent in the last hour
sum(count_over_time({job="elixir-agents"} | json | level="error" [1h])) by (agent_id)
```

---

## Wiring It Together

### Application Startup

```elixir
defmodule AgenticPlatform.Application do
  use Application

  @impl true
  def start(_type, _args) do
    # Setup telemetry handlers FIRST — before any other process starts
    # WHY: If a process starts before handlers are attached, you miss
    # its initialization events.
    AgenticPlatform.Telemetry.setup()

    children = [
      # Telemetry supervisor (poller + metrics)
      AgenticPlatformWeb.Telemetry,

      # Prometheus metrics endpoint
      {Prometheus.Metrics, []},

      # ... other children ...
    ]

    opts = [strategy: :one_for_one, name: AgenticPlatform.Supervisor]
    Supervisor.start_link(children, opts)
  end
end
```

### Starting the Observability Stack

```bash
# Start the full observability stack
docker compose -f docker-compose.observability.yml up -d

# Verify all services are running
docker compose -f docker-compose.observability.yml ps

# Access the UIs:
# Grafana:        http://localhost:3001 (admin/admin)
# Prometheus:     http://localhost:9090
# Jaeger:         http://localhost:16686
# Loki:           http://localhost:3100/ready

# Start your application
cd agentic_platform
mix phx.server

# Open LiveDashboard at http://localhost:4000/dashboard
```

---

## What's Next

Your platform now has full-stack observability. Continue to [Module 15: Production Deployment](15-production-deployment.md) to deploy everything to Kubernetes.
