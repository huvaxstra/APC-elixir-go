# Module 13 Exercise: Go-to-Elixir Telemetry Bridge

> **What you'll build**: A Go gRPC server that receives agent telemetry, and an Elixir client that sends it.
> **Skills practiced**: Protobuf contracts, gRPC server/client, streaming, cross-language types
> **Time estimate**: 4-5 hours

---

## Learning Objectives

By completing this exercise, you will:
1. Define a protobuf contract that both Go and Elixir understand
2. Implement a Go gRPC server that receives and aggregates metrics
3. Build an Elixir gRPC client that sends agent telemetry
4. Use server-streaming for command relay
5. Handle cross-language type differences

---

## Part 1: Protobuf Contract (45 minutes)

### Starter Code

Save this as `proto/agentbridge/agentbridge.proto`:

```protobuf
// AgentBridge.proto — Contract between Go gateway and Elixir agents
// This file is the single source of truth for both languages.
// Changes here require regeneration on both sides.

syntax = "proto3";

package agentbridge;

option go_package = "github.com/agentic-platform/agentbridge/proto/agentbridge";

// MetricReport — telemetry from an agent to the gateway
// WHY: Agents report periodically so the gateway can aggregate for Prometheus
message MetricReport {
  int64 agent_id = 1;
  string state = 2;
  int64 tasks_completed = 3;
  int64 tasks_failed = 4;
  int64 memory_bytes = 5;
  int64 last_task_duration_us = 6;
  int64 timestamp_ns = 7;
  map<string, string> metadata = 8;
}

// Ack — server acknowledgment of a MetricReport
message Ack {
  bool accepted = 1;
  string reason = 2;
  int64 server_timestamp_ns = 3;
  int64 recommended_interval_ms = 4;
}

// Command — instruction from gateway to agent
message Command {
  int64 command_id = 1;
  string command_type = 2;
  map<string, string> payload = 3;
  int64 deadline_ns = 4;
  string issuer = 5;
}

// Result — agent's response to a Command
message Result {
  int64 command_id = 1;
  bool success = 2;
  string message = 3;
  map<string, string> data = 4;
  int64 timestamp_ns = 5;
}

// AgentBridge — the gRPC service definition
service AgentBridge {
  // Unary RPC: agent sends one report, server acks
  rpc ReportMetrics(MetricReport) returns (Ack);

  // Server-streaming: agent opens stream, server pushes commands
  rpc StreamCommands(Command) returns (stream Result);

  // Bidirectional: both sides stream independently
  rpc BidirectionalStream(stream MetricReport) returns (stream Command);
}
```

### Your Task

1. Generate Go code from this proto file
2. Generate Elixir code from this proto file
3. Verify both generated files contain the same messages

### Hints

- Use `protoc` with `--go_out` and `--go-grpc_out` for Go
- Use `mix grpc.gen` for Elixir (requires `exprotobuf` or `grpc` dependency)
- The Go package option must match your module path
- Proto3 means no required/optional — all fields have zero values when unset

---

## Part 2: Go gRPC Server (1.5 hours)

### Starter Code

Save this as `cmd/bridge-server/main.go`:

```go
package main

import (
	"context"
	"fmt"
	"io"
	"log"
	"net"
	"sync"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/health"
	"google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/status"

	pb "github.com/agentic-platform/agentbridge/proto/agentbridge"
)

// BridgeServer implements the AgentBridge gRPC service.
type BridgeServer struct {
	pb.UnimplementedAgentBridgeServer

	mu      sync.RWMutex
	metrics map[int64]*pb.MetricReport

	subscribers map[int64]chan<- *pb.Command
}

func NewBridgeServer() *BridgeServer {
	return &BridgeServer{
		metrics:     make(map[int64]*pb.MetricReport),
		subscribers: make(map[int64]chan<- *pb.Command),
	}
}

// TODO: Implement ReportMetrics
// Requirements:
// - Validate agent_id is non-zero
// - Store the report in the metrics map (thread-safe)
// - Return Ack with accepted=true and a recommended interval
// - Log the received metrics

func (s *BridgeServer) ReportMetrics(ctx context.Context, in *pb.MetricReport) (*pb.Ack, error) {
	// Your code here

	return nil, status.Errorf(codes.Unimplemented, "not implemented")
}

// TODO: Implement StreamCommands
// Requirements:
// - Read agent_id from the initial command's payload
// - Create a channel for this agent's commands
// - Register the channel in subscribers map
// - Loop: wait for commands on channel or client disconnect
// - Clean up on disconnect (remove from subscribers)
// - Return Result for each command sent

func (s *BridgeServer) StreamCommands(in *pb.Command, stream pb.AgentBridge_StreamCommandsServer) error {
	// Your code here

	return status.Errorf(codes.Unimplemented, "not implemented")
}

// SendCommand pushes a command to a connected agent (internal API).
// This is NOT a gRPC method — it's called by the HTTP API or operator.

func (s *BridgeServer) SendCommand(agentID int64, cmd *pb.Command) error {
	s.mu.RLock()
	ch, ok := s.subscribers[agentID]
	s.mu.RUnlock()

	if !ok {
		return fmt.Errorf("agent %d not connected", agentID)
	}

	// Non-blocking send — drop if full
	select {
	case ch <- cmd:
		return nil
	default:
		return fmt.Errorf("agent %d command queue full", agentID)
	}
}

// TODO: Implement calculateInterval
// Requirements:
// - < 10 agents: return 1000ms
// - < 100 agents: return 5000ms
// - >= 100 agents: return 10000ms

func (s *BridgeServer) calculateInterval() int64 {
	// Your code here

	return 5000
}

func main() {
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	s := grpc.NewServer()
	bridgeServer := NewBridgeServer()
	pb.RegisterAgentBridgeServer(s, bridgeServer)

	// Health check — required for K8s readiness probe
	healthServer := health.NewServer()
	grpc_health_v1.RegisterHealthServer(s, healthServer)
	healthServer.SetServingStatus("agentbridge.AgentBridge",
		grpc_health_v1.HealthCheckResponse_SERVING)

	log.Println("Bridge server listening on :50051")
	if err := s.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}
```

### Your Task

1. Implement `ReportMetrics` — validate, store, and acknowledge
2. Implement `StreamCommands` — handle the command stream lifecycle
3. Implement `calculateInterval` — dynamic reporting frequency
4. Test with `grpcurl`

### Hints

- Use `sync.RWMutex` for thread-safe map access
- `stream.Context().Done()` tells you when the client disconnects
- `defer` cleanup in StreamCommands for the subscribers map entry
- Non-blocking send with `select { case ch <- cmd: ... default: ... }`

---

## Part 3: Elixir gRPC Client (1.5 hours)

### Starter Code

Save this as `lib/agent_bridge/client.ex`:

```elixir
defmodule AgentBridge.Client do
  @moduledoc """
  gRPC client wrapper for the Go AgentBridge gateway.

  Provides simple functions that agents can call to report metrics
  and receive commands. Handles connection management and error recovery.
  """

  use GenServer

  require Logger

  @gateway_endpoint "localhost:50051"

  # Client API

  def start_link(opts) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @doc "Send a MetricReport to the gateway and get an Ack."
  def report_metrics(metrics) do
    GenServer.call(__MODULE__, {:report, metrics}, 10_000)
  end

  @doc "Start receiving commands from the gateway."
  def subscribe_to_commands(agent_id, handler_fn) do
    GenServer.cast(__MODULE__, {:subscribe, agent_id, handler_fn})
  end

  # Server callbacks

  @impl true
  def init(opts) do
    # TODO: Initialize the gRPC channel to the gateway
    # Store the channel in state for reuse
    # COMMON MISTAKE: Creating a new channel per call — expensive!
    {:ok, %{channel: nil, streams: %{}}}
  end

  @impl true
  def handle_call({:report, metrics}, _from, state) do
    # TODO: Build an AgentBridge.MetricReport struct from the metrics map
    # TODO: Send it via the gRPC channel
    # TODO: Return {:ok, ack} or {:error, reason}
    # Hint: Use AgentBridge.MetricReport struct with atom keys
    {:reply, {:error, :not_implemented}, state}
  end

  @impl true
  def handle_cast({:subscribe, agent_id, handler_fn}, state) do
    # TODO: Open a StreamCommands connection to the gateway
    # TODO: Store the stream reference in state.streams
    # TODO: Spawn a task to receive commands and call handler_fn
    {:noreply, state}
  end

  @impl true
  def handle_info({:stream_command, command}, state) do
    # TODO: Forward the command to the appropriate handler
    # WHY: Commands arrive from the stream task, but we process them
    # in the GenServer to maintain state consistency.
    {:noreply, state}
  end
end
```

### Your Task

1. Implement `init/1` — create and store a gRPC channel
2. Implement `handle_call({:report, metrics})` — build protobuf struct and send
3. Implement `handle_cast({:subscribe})` — open stream and spawn receiver
4. Handle stream errors gracefully (connection drops, server restarts)

### Hints

- `GRPC.Channel.new(endpoint, opts)` creates a reusable channel
- `AgentBridge.AgentBridge.Stub.report_metrics(channel, report)` makes the RPC call
- Use `Task.Supervisor.start_child` for the stream receiver — it should be supervised
- `GRPC.Stream.recv(stream)` blocks until a message arrives or the stream closes
- Map atom keys to struct fields: `%AgentBridge.MetricReport{agent_id: metrics.agent_id}`

---

## Part 4: Integration Test (30 minutes)

### Starter Code

Save this as `test/bridge_integration_test.exs`:

```elixir
defmodule AgentBridge.IntegrationTest do
  @moduledoc """
  Integration test for the Go-Elixir gRPC bridge.

  REQUIREMENTS:
  - Go server must be running on localhost:50051
  - Run: cd cmd/bridge-server && go run main.go

  This test verifies the full round-trip: Elixir sends metrics,
  Go acknowledges, Go sends commands, Elixir receives them.
  """

  use ExUnit.Case

  @tag :integration
  test "round-trip metric report and ack" do
    # TODO: Send a MetricReport via AgentBridge.Client
    # TODO: Assert the Ack has accepted=true
    # TODO: Assert the recommended_interval_ms is reasonable
  end

  @tag :integration
  test "command stream receives commands" do
    # TODO: Subscribe to commands via AgentBridge.Client
    # TODO: From Go server, send a command to this agent
    # TODO: Assert the command handler receives it
  end

  @tag :integration
  test "rejected metric report has zero agent_id" do
    # TODO: Send a MetricReport with agent_id=0
    # TODO: Assert the Ack has accepted=false
    # TODO: Assert the reason mentions agent_id
  end
end
```

### Your Task

1. Fill in the test cases with actual gRPC calls
2. Run the Go server in a separate terminal
3. Run the Elixir tests with `mix test --include integration`
4. Verify all three tests pass

---

## Solution

<details>
<summary>Click to reveal solution</summary>

### Go Server: ReportMetrics

```go
func (s *BridgeServer) ReportMetrics(ctx context.Context, in *pb.MetricReport) (*pb.Ack, error) {
	if in.AgentId == 0 {
		return &pb.Ack{
			Accepted: false,
			Reason:   "agent_id must be non-zero",
		}, nil
	}

	s.mu.Lock()
	s.metrics[in.AgentId] = in
	s.mu.Unlock()

	log.Printf("Metrics from agent %d: state=%s, completed=%d, failed=%d",
		in.AgentId, in.State, in.TasksCompleted, in.TasksFailed)

	return &pb.Ack{
		Accepted:            true,
		ServerTimestampNs:   time.Now().UnixNano(),
		RecommendedIntervalMs: s.calculateInterval(),
	}, nil
}
```

### Go Server: StreamCommands

```go
func (s *BridgeServer) StreamCommands(in *pb.Command, stream pb.AgentBridge_StreamCommandsServer) error {
	agentIDStr := in.Payload["agent_id"]
	if agentIDStr == "" {
		return status.Errorf(codes.InvalidArgument, "first command must include agent_id")
	}

	var agentID int64
	fmt.Sscanf(agentIDStr, "%d", &agentID)

	cmdChan := make(chan *pb.Command, 100)
	defer close(cmdChan)

	s.mu.Lock()
	s.subscribers[agentID] = cmdChan
	s.mu.Unlock()

	defer func() {
		s.mu.Lock()
		delete(s.subscribers, agentID)
		s.mu.Unlock()
	}()

	log.Printf("Agent %d connected to command stream", agentID)

	for {
		select {
		case cmd, ok := <-cmdChan:
			if !ok {
				return nil
			}
			result := &pb.Result{
				CommandId:    cmd.CommandId,
				Success:      true,
				Message:      "Command received",
				TimestampNs:  time.Now().UnixNano(),
			}
			if err := stream.Send(result); err != nil {
				return err
			}
		case <-stream.Context().Done():
			log.Printf("Agent %d disconnected", agentID)
			return nil
		}
	}
}
```

### Go Server: calculateInterval

```go
func (s *BridgeServer) calculateInterval() int64 {
	s.mu.RLock()
	count := len(s.metrics)
	s.mu.RUnlock()

	switch {
	case count < 10:
		return 1000
	case count < 100:
		return 5000
	default:
		return 10000
	}
}
```

### Elixir Client: init

```elixir
@impl true
def init(opts) do
  endpoint = Keyword.get(opts, :endpoint, @gateway_endpoint)

  # Create channel once — reuse for all calls
  channel = GRPC.Channel.new(endpoint, [
    adapter: GRPC.Client.Adapter.Gun,
    keepalive: 30_000
  ])

  {:ok, %{channel: channel, streams: %{}}}
end
```

### Elixir Client: report_metrics

```elixir
@impl true
def handle_call({:report, metrics}, _from, %{channel: channel} = state) do
  report = %AgentBridge.MetricReport{
    agent_id: metrics.agent_id,
    state: metrics.state,
    tasks_completed: Map.get(metrics, :tasks_completed, 0),
    tasks_failed: Map.get(metrics, :tasks_failed, 0),
    memory_bytes: Map.get(metrics, :memory_bytes, 0),
    last_task_duration_us: Map.get(metrics, :last_task_duration_us, 0),
    timestamp_ns: System.system_time(:nanosecond),
    metadata: Map.get(metrics, :metadata, %{})
  }

  case AgentBridge.AgentBridge.Stub.report_metrics(channel, report) do
    {:ok, ack} -> {:reply, {:ok, ack}, state}
    {:error, err} -> {:reply, {:error, err}, state}
  end
end
```

### Elixir Client: subscribe_to_commands

```elixir
@impl true
def handle_cast({:subscribe, agent_id, handler_fn}, %{channel: channel} = state) do
  # Open the command stream
  initial_cmd = %AgentBridge.Command{
    command_id: 0,
    command_type: "identify",
    payload: %{"agent_id" => to_string(agent_id)}
  }

  case AgentBridge.AgentBridge.Stub.stream_commands(channel, initial_cmd) do
    {:ok, stream} ->
      # Spawn receiver task
      Task.Supervisor.start_child(AgentBridge.TaskSupervisor, fn ->
        receive_loop(stream, handler_fn)
      end)

      {:noreply, %{state | streams: Map.put(state.streams, agent_id, stream)}}

    {:error, reason} ->
      Logger.error("Failed to open command stream: #{inspect(reason)}")
      {:noreply, state}
  end
end

defp receive_loop(stream, handler_fn) do
  case GRPC.Stream.recv(stream) do
    {:ok, result} ->
      handler_fn.(result)
      receive_loop(stream, handler_fn)

    {:error, :closed} ->
      Logger.info("Command stream closed")

    {:error, reason} ->
      Logger.error("Stream error: #{inspect(reason)}")
  end
end
```

</details>

---

## What's Next

After completing this exercise, continue to [Module 14: Observability Stack](14-observability-stack.md) to add full-stack monitoring to your platform.
