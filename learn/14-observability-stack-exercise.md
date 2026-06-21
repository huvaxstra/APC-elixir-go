# Module 14 Exercise: Full-Stack Observability

> **What you'll build**: Instrument Go and Elixir services with OpenTelemetry, Prometheus metrics, and structured logging for Grafana + Loki.
> **Skills practiced**: :telemetry hooks, OpenTelemetry SDK, Prometheus metrics, structured logging, Grafana dashboards
> **Time estimate**: 4-5 hours

---

## Learning Objectives

By completing this exercise, you will:
1. Attach :telemetry handlers to Elixir GenServer events
2. Instrument Go gRPC handlers with OpenTelemetry spans
3. Expose Prometheus metrics from both services
4. Write structured logs parseable by Loki
5. Build a Grafana dashboard that visualizes your platform

---

## Part 1: Elixir Telemetry Instrumentation (1 hour)

### Starter Code

Save this as `lib/agentic_platform/telemetry.ex`:

```elixir
defmodule AgenticPlatform.Telemetry do
  @moduledoc """
  Telemetry event handlers for the agentic platform.

  This module attaches handlers to :telemetry events emitted by
  GenServers, supervisors, and the gRPC bridge. Each handler
  transforms events into Prometheus metrics or structured logs.
  """

  require Logger

  @doc "Attaches all telemetry handlers. Call in Application.start/2."
  def setup do
    # TODO: Attach a handler for agent task completion
    # Event name: [:agentic_platform, :agent, :task_completed]
    # Handler function: &handle_agent_task/4
    #
    # Hint: Use :telemetry.attach/4 with a unique handler ID string

    # TODO: Attach a handler for supervisor restarts
    # Event name: [:agentic_platform, :supervisor, :restart]
    # Handler function: &handle_supervisor_restart/4
  end

  @doc "Emits a telemetry event when an agent completes a task."
  def emit_task_completed(agent_id, task_type, duration_us) do
    # TODO: Execute a telemetry event with:
    # - Event name: [:agentic_platform, :agent, :task_completed]
    # - Measurements: %{duration_us: duration_us}
    # - Metadata: %{agent_id: agent_id, task_type: task_type}
  end

  @doc "Emits a telemetry span that measures a function's duration."
  def span_task(agent_id, task_type, fun) do
    # TODO: Use :telemetry.span/3 to wrap fun.0 and measure its duration.
    # The span should emit events:
    # - [:agentic_platform, :agent, :task, :start] on entry
    # - [:agentic_platform, :agent, :task, :stop] on success
    # - [:agentic_platform, :agent, :task, :exception] on failure
    #
    # Metadata should include: agent_id, task_type
  end

  # TODO: Implement handle_agent_task/4
  # This callback receives telemetry events and:
  # 1. Increments a Prometheus counter for total tasks
  # 2. Records a Prometheus histogram for task duration
  # 3. Logs a structured message for Loki
  defp handle_agent_task(event_name, measurements, metadata, config) do
    # Your code here
    :ok
  end

  # TODO: Implement handle_supervisor_restart/4
  # This callback:
  # 1. Increments a Prometheus counter for restarts
  # 2. Logs a warning with supervisor name and reason
  defp handle_supervisor_restart(_event_name, measurements, metadata, _config) do
    # Your code here
    :ok
  end
end
```

### Your Task

1. Implement `setup/0` — attach handlers for agent tasks and supervisor restarts
2. Implement `emit_task_completed/3` — fire telemetry events
3. Implement `span_task/3` — wrap functions with telemetry spans
4. Implement `handle_agent_task/4` — update Prometheus metrics and log
5. Implement `handle_supervisor_restart/4` — track restarts

### Hints

- `:telemetry.attach(handler_id, event_name, handler_fn, config)` attaches a handler
- `:telemetry.execute(event_name, measurements, metadata)` fires an event
- `:telemetry.span(event_name, metadata, fun)` wraps a function with duration tracking
- Handler callbacks receive 4 arguments: event_name, measurements, metadata, config
- Use `Prometheus.Counter.inc(name: :metric_name, labels: %{key: value})` for counters
- Use `Prometheus.Histogram.observe(name: :metric_name, value: value)` for histograms

---

## Part 2: Go OpenTelemetry Spans (1 hour)

### Starter Code

Save this as `internal/telemetry/tracing.go`:

```go
package telemetry

import (
	"context"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

// InitTracer sets up OpenTelemetry tracing.
// TODO: Implement the following:
// 1. Create an OTLP gRPC exporter pointing to localhost:4317
// 2. Create a resource with service name and version
// 3. Create a TracerProvider with the exporter and resource
// 4. Set it as the global provider
// 5. Return a shutdown function and nil error
func InitTracer(ctx context.Context, serviceName string) (func(), error) {
	// Your code here

	return func() {}, nil
}

// TraceReportMetrics adds a span to the ReportMetrics gRPC call.
// TODO: Implement the following:
// 1. Get a tracer for "agentic-platform/gateway"
// 2. Start a span named "ReportMetrics" with agent.id and agent.state attributes
// 3. Return the new context (caller will defer span.End())
func TraceReportMetrics(ctx context.Context, agentID int64, state string) context.Context {
	// Your code here

	return ctx
}

// TraceStreamCommands adds a span to the StreamCommands gRPC call.
// TODO: Implement similarly to TraceReportMetrics
// Span name: "StreamCommands"
// Attributes: agent.id
func TraceStreamCommands(ctx context.Context, agentID int64) context.Context {
	// Your code here

	return ctx
}
```

### Your Task

1. Implement `InitTracer` — set up OTLP export to Jaeger
2. Implement `TraceReportMetrics` — create spans for metric reports
3. Implement `TraceStreamCommands` — create spans for command streams

### Hints

- `otlptracegrpc.New(ctx, otlptracegrpc.WithEndpoint("localhost:4317"))` creates the exporter
- `otel.Tracer("package/name")` gets a named tracer
- `tracer.Start(ctx, "span_name", trace.WithAttributes(...))` starts a span
- Always `defer span.End()` immediately after starting
- Use `attribute.Int64("key", value)` for span attributes

---

## Part 3: Structured Logging (45 minutes)

### Starter Code

Save this as `lib/agentic_platform/logger.ex`:

```elixir
defmodule AgenticPlatform.StructuredLogger do
  @moduledoc """
  Structured logging helpers for the agentic platform.

  All log messages include structured fields that Loki can
  index and search. Never use bare Logger.info("message") —
  always include context fields.
  """

  require Logger

  @doc "Logs a task event with full context."
  def log_task_event(event, agent_id, task_id, opts \\ []) do
    # TODO: Use Logger.info/2 or Logger.error/2 with structured metadata:
    # - event: the event type (e.g., "started", "completed", "failed")
    # - agent_id: the agent's ID
    # - task_id: the task's unique identifier
    # - All keys from opts (duration_ms, error, task_type, etc.)
    #
    # Example output (JSON):
    # {"message":"Task completed","event":"completed","agent_id":42,"task_id":"abc-123","duration_ms":150}
  end

  @doc "Logs a gRPC bridge event."
  def log_bridge_event(event, direction, agent_id, opts \\ []) do
    # TODO: Log with structured fields:
    # - event: "send", "receive", "error", "timeout"
    # - direction: "inbound" (Elixir→Go) or "outbound" (Go→Elixir)
    # - agent_id: the agent involved
    # - All keys from opts
  end
end
```

Save this as `internal/logging/logger.go`:

```go
package logging

import (
	"log/slog"
)

// LogTaskEvent logs a task event with structured fields.
// TODO: Implement using slog.Info or slog.Error with structured attributes:
//   - "event": event type string
//   - "agent_id": agent ID
//   - "task_id": task identifier
//   - Additional key-value pairs from the attrs parameter
func LogTaskEvent(event string, agentID int64, taskID string, attrs map[string]string) {
	// Your code here
}

// LogBridgeEvent logs a gRPC bridge event.
// TODO: Implement with slog using:
//   - "event": event type
//   - "direction": "inbound" or "outbound"
//   - "agent_id": agent ID
func LogBridgeEvent(event string, direction string, agentID int64, attrs map[string]string) {
	// Your code here
}
```

### Your Task

1. Implement Elixir `log_task_event/4` with structured Logger metadata
2. Implement Elixir `log_bridge_event/4` with structured Logger metadata
3. Implement Go `LogTaskEvent` with slog structured attributes
4. Implement Go `LogBridgeEvent` with slog structured attributes

### Hints

- Elixir: `Logger.info("message", key: value, key2: value2)` — use keyword list
- Go: `slog.Info("message", "key", value, "key2", value2)` — alternating key-value pairs
- Always include the event name, agent_id, and task_id as the minimum fields
- Never use `IO.puts` or `fmt.Println` — they produce unstructured output

---

## Part 4: Integration Test (30 minutes)

### Starter Code

Save this as `test/telemetry_test.exs`:

```elixir
defmodule AgenticPlatform.TelemetryTest do
  use ExUnit.Case

  # These tests verify that telemetry events are emitted correctly.
  # They don't require a running Prometheus — they just verify the
  # events fire with the right measurements and metadata.

  setup do
    # Attach a test handler that captures events
    test_pid = self()

    handler_id = "test-handler-#{System.unique_integer([:positive])}"

    :telemetry.attach(
      handler_id,
      [:agentic_platform, :agent, :task_completed],
      fn _event, measurements, metadata, _config ->
        send(test_pid, {:telemetry_event, measurements, metadata})
      end,
      %{}
    )

    on_exit(fn ->
      :telemetry.detach(handler_id)
    end)

    %{handler_id: handler_id}
  end

  test "task completed event fires with correct measurements" do
    # TODO: Emit a task completed event using AgenticPlatform.Telemetry
    # Assert you receive {:telemetry_event, measurements, metadata}
    # Assert measurements.duration_us is a positive integer
    # Assert metadata.agent_id is 42
    # Assert metadata.task_type is "code_review"
  end

  test "span_task measures function duration" do
    # TODO: Use AgenticPlatform.Telemetry.span_task/3 to wrap a function
    # The function should sleep for 50ms
    # Assert the function returns the expected value
    # Assert a telemetry span event was emitted
  end
end
```

### Your Task

1. Fill in the test assertions for task completed events
2. Fill in the test for span_task duration measurement
3. Run with `mix test test/telemetry_test.exs`
4. Verify all tests pass

---

## Solution

<details>
<summary>Click to reveal solution</summary>

### Elixir Telemetry: setup/0

```elixir
def setup do
  :telemetry.attach(
    "agentic-platform-agent-tasks",
    [:agentic_platform, :agent, :task_completed],
    &handle_agent_task/4,
    %{}
  )

  :telemetry.attach(
    "agentic-platform-supervisor-restarts",
    [:agentic_platform, :supervisor, :restart],
    &handle_supervisor_restart/4,
    %{}
  )
end
```

### Elixir Telemetry: emit_task_completed/3

```elixir
def emit_task_completed(agent_id, task_type, duration_us) do
  :telemetry.execute(
    [:agentic_platform, :agent, :task_completed],
    %{duration_us: duration_us},
    %{agent_id: agent_id, task_type: task_type}
  )
end
```

### Elixir Telemetry: span_task/3

```elixir
def span_task(agent_id, task_type, fun) do
  :telemetry.span(
    [:agentic_platform, :agent, :task],
    %{agent_id: agent_id, task_type: task_type},
    fn ->
      result = fun.()
      {result, %{}}
    end
  )
end
```

### Elixir Telemetry: handle_agent_task/4

```elixir
defp handle_agent_task(_event_name, measurements, metadata, _config) do
  Prometheus.Counter.inc(
    name: :agentic_agent_tasks_total,
    labels: %{agent_id: metadata.agent_id, task_type: metadata.task_type}
  )

  Prometheus.Histogram.observe(
    name: :agentic_agent_task_duration_us,
    value: measurements.duration_us,
    labels: %{agent_id: metadata.agent_id}
  )

  Logger.info("Task completed",
    agent_id: metadata.agent_id,
    task_type: metadata.task_type,
    duration_us: measurements.duration_us
  )
end
```

### Elixir Telemetry: handle_supervisor_restart/4

```elixir
defp handle_supervisor_restart(_event_name, _measurements, metadata, _config) do
  Prometheus.Counter.inc(
    name: :agentic_supervisor_restarts_total,
    labels: %{supervisor: metadata.supervisor}
  )

  Logger.warning("Supervisor restart",
    supervisor: metadata.supervisor,
    reason: metadata.reason
  )
end
```

### Go Telemetry: InitTracer

```go
func InitTracer(ctx context.Context, serviceName string) (func(), error) {
	exporter, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithEndpoint("localhost:4317"),
		otlptracegrpc.WithInsecure(),
	)
	if err != nil {
		return nil, err
	}

	res, err := resource.Merge(
		resource.Default(),
		resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceName(serviceName),
		),
	)
	if err != nil {
		return nil, err
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
	)

	otel.SetTracerProvider(tp)

	shutdown := func() {
		tp.Shutdown(ctx)
	}

	return shutdown, nil
}
```

### Go Telemetry: TraceReportMetrics

```go
func TraceReportMetrics(ctx context.Context, agentID int64, state string) context.Context {
	tracer := otel.Tracer("agentic-platform/gateway")
	ctx, span := tracer.Start(ctx, "ReportMetrics",
		trace.WithAttributes(
			attribute.Int64("agent.id", agentID),
			attribute.String("agent.state", state),
		),
	)
	defer span.End()
	return ctx
}
```

### Go Logging: LogTaskEvent

```go
func LogTaskEvent(event string, agentID int64, taskID string, attrs map[string]string) {
	args := []any{
		slog.String("event", event),
		slog.Int64("agent_id", agentID),
		slog.String("task_id", taskID),
	}
	for k, v := range attrs {
		args = append(args, slog.String(k, v))
	}

	if event == "failed" || event == "error" {
		slog.Error("Task event", args...)
	} else {
		slog.Info("Task event", args...)
	}
}
```

### Go Logging: LogBridgeEvent

```go
func LogBridgeEvent(event string, direction string, agentID int64, attrs map[string]string) {
	args := []any{
		slog.String("event", event),
		slog.String("direction", direction),
		slog.Int64("agent_id", agentID),
	}
	for k, v := range attrs {
		args = append(args, slog.String(k, v))
	}

	if event == "error" || event == "timeout" {
		slog.Error("Bridge event", args...)
	} else {
		slog.Info("Bridge event", args...)
	}
}
```

### Elixir Test: task completed event

```elixir
test "task completed event fires with correct measurements" do
  AgenticPlatform.Telemetry.emit_task_completed(42, "code_review", 150_000)

  assert_receive {:telemetry_event, measurements, metadata}, 1_000
  assert is_integer(measurements.duration_us)
  assert measurements.duration_us > 0
  assert metadata.agent_id == 42
  assert metadata.task_type == "code_review"
end
```

### Elixir Test: span_task

```elixir
test "span_task measures function duration" do
  result = AgenticPlatform.Telemetry.span_task(42, "test", fn ->
    Process.sleep(50)
    :done
  end)

  assert result == :done
end
```

</details>

---

## What's Next

After completing this exercise, continue to [Module 15: Production Deployment](15-production-deployment.md) to deploy your platform to Kubernetes.
