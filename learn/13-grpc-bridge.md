# Module 13: Bridge: gRPC (Week 13)

## What You'll Learn This Module

By the end of this module, you'll understand how to connect Go and Elixir through gRPC:

1. **Protobuf contracts** — define shared message types that both languages understand
2. **gRPC server in Go** — implement the AgentBridge service that receives telemetry
3. **gRPC client in Elixir** — send agent metrics to the Go gateway using protobuf
4. **Streaming** — bidirectional streams for real-time command-response flows
5. **Cross-language types** — how protobuf maps to Go structs and Elixir structs

gRPC is the bridge between the Go infrastructure edge and the Elixir agent brain. Alkahest uses exactly this pattern: a Go gateway handles Prometheus scraping, K8s API calls, and external integrations, while Elixir runs the agent logic. They communicate over gRPC with protobuf contracts.

---

## The Problem: Two Languages, One System

You've built Go infrastructure tools (Modules 1, 2, 11, 12) and Elixir agent systems (Modules 3-10). But they're isolated. The Go K8s operator doesn't know what the Elixir agents are doing. The Elixir agents can't trigger Go infrastructure operations.

You need a contract — a shared language that both sides speak. gRPC is that contract.

### Why Not REST?

REST works fine for simple request-response. But agent platforms need:

1. **Streaming** — agents send continuous telemetry, not one-off requests
2. **Type safety** — a typo in a JSON field name causes runtime errors, not compile errors
3. **Performance** — protobuf serialization is 5-10x faster than JSON
4. **Code generation** — both Go and Elixir get type-safe clients from one contract

REST is the postal service. gRPC is the phone line — always on, always typed.

---

## The Big Picture: AgentBridge Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Elixir Agent Brain                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Agent A  │  │ Agent B  │  │ Agent C  │             │
│  │ (GenSrv) │  │ (GenSrv) │  │ (GenSrv) │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │              │              │                    │
│       └──────────────┼──────────────┘                   │
│                      │                                  │
│              AgentBridgeClient                          │
│              (gRPC client)                              │
└──────────────────────┼──────────────────────────────────┘
                       │
                  gRPC (protobuf)
                       │
┌──────────────────────┼──────────────────────────────────┐
│              Go Gateway (gRPC Server)                   │
│              AgentBridge Service                         │
│       ┌──────────────┼──────────────┐                   │
│       │              │              │                    │
│  ┌────▼─────┐  ┌─────▼────┐  ┌─────▼────┐             │
│  │Metrics   │  │Command   │  │Health    │             │
│  │Collector │  │Relay     │  │Checker   │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
```

---

## Pattern 1: Protobuf Contracts

### What Is a Protobuf Contract?

Think of a protobuf contract as a bilingual dictionary. It defines words (messages) and grammar (services) that both Go and Elixir understand. When you change the contract, both sides get compile-time errors if they don't adapt.

The `.proto` file is the single source of truth. From it, you generate:
- Go structs and server stubs
- Elixir structs and client stubs

### AgentBridge.proto

```protobuf
// AgentBridge.proto — The contract between Go gateway and Elixir agents
//
// WHY: This file is the single source of truth. Both Go and Elixir
// generate code from it. If you change a field here, both sides
// get compile errors until they adapt. This is the safety net.
//
// Proto3 syntax means: no required/optional keywords, all fields
// have zero values when unset, and you can't check "was this field set?"
// without using wrapper messages.

syntax = "proto3";

// The package name becomes the Go package and Elixir module namespace
// DEEP DIVE: In Go, this becomes the generated package name.
// In Elixir, dots become underscores: agent_bridge
package agentbridge;

// gRPC requires proto3 — no way around it
option go_package = "github.com/agentic-platform/agentbridge";
option java_multiple_files = true;

// ============================================================
// MESSAGES — the vocabulary of our contract
// ============================================================

// MetricReport is the telemetry payload an agent sends to the gateway.
//
// WHY: Every agent periodically reports what it's doing — tasks completed,
// errors encountered, resource usage. The gateway aggregates these for
// Prometheus scraping.
//
// COMMON MISTAKE: Don't use int32 for IDs — use int64. Agent IDs
// can grow large in production, and int32 overflows at ~2 billion.
message MetricReport {
  // Unique agent identifier — survives restarts, assigned by Registry
  int64 agent_id = 1;

  // The agent's current state: idle, planning, executing, reviewing, blocked
  // WHY: String instead of enum — allows adding new states without
  // breaking the protobuf contract. Enums require recompilation.
  string state = 2;

  // Number of tasks completed since last report
  int64 tasks_completed = 3;

  // Number of tasks that failed (includes retries)
  int64 tasks_failed = 4;

  // Current memory usage in bytes
  int64 memory_bytes = 5;

  // Duration of the last task in microseconds
  // WHY: Microseconds because task durations range from milliseconds
  // to seconds, and we need sub-millisecond precision for short tasks.
  int64 last_task_duration_us = 6;

  // Timestamp when this report was created (Unix epoch, nanoseconds)
  int64 timestamp_ns = 7;

  // Optional metadata — key-value pairs for custom metrics
  // DEEP DIVE: map<string, string> is protobuf's way of allowing
  // extensible data without changing the message schema. The gateway
  // passes these through to Prometheus as labels.
  map<string, string> metadata = 8;
}

// Ack is the server's acknowledgment of a MetricReport.
//
// WHY: Agents need to know their telemetry was received. Without acks,
// agents might buffer unbounded data if the gateway is down.
message Ack {
  // Whether the report was accepted (true) or rejected (false)
  bool accepted = 1;

  // Human-readable reason if rejected (empty string if accepted)
  string reason = 2;

  // Server timestamp when the ack was generated
  int64 server_timestamp_ns = 3;

  // Recommended reporting interval in milliseconds
  // WHY: Server can dynamically adjust reporting frequency based on load.
  // If the gateway is overwhelmed, it can tell agents to report less often.
  int64 recommended_interval_ms = 4;
}

// Command is an instruction the gateway sends to an agent.
//
// WHY: The gateway isn't just a metrics collector — it can also relay
// commands from operators or external systems to agents. This creates
// a bidirectional control channel.
message Command {
  // Unique command identifier — used for deduplication
  int64 command_id = 1;

  // The command type: "restart", "reconfigure", "pause", "resume", "stop"
  string command_type = 2;

  // Command-specific payload as key-value pairs
  // WHY: Flexible payload avoids defining a new message type for
  // every possible command. The agent interprets based on command_type.
  map<string, string> payload = 3;

  // Deadline in nanoseconds — if the agent doesn't complete by this time,
  // the command is considered failed
  int64 deadline_ns = 4;

  // Who issued this command (operator name, automated system, etc.)
  string issuer = 5;
}

// Result is the agent's response to a Command.
//
// WHY: Every command must produce a result. The gateway needs this
// to report command outcomes to the operator that issued it.
message Result {
  // The command_id this result corresponds to
  int64 command_id = 1;

  // Whether the command succeeded
  bool success = 2;

  // Human-readable description of what happened
  string message = 3;

  // Result-specific data as key-value pairs
  map<string, string> data = 4;

  // Timestamp when the result was generated
  int64 timestamp_ns = 5;
}

// ============================================================
// SERVICES — the grammar of our contract
// ============================================================

// AgentBridge is the service definition for the Go-Elixir bridge.
//
// WHY: Service definitions tell gRPC what methods exist and what
// their request/response types are. Both Go server and Elixir client
// implement this contract.
service AgentBridge {
  // ReportMetrics is a unary RPC — one request, one response.
  //
  // WHY: Agent sends a batch of metrics, server acknowledges.
  // Simple, reliable, easy to retry on failure.
  rpc ReportMetrics(MetricReport) returns (Ack);

  // StreamCommands is a server-streaming RPC — client sends one request,
  // server sends a stream of responses.
  //
  // WHY: The gateway can push commands to agents at any time.
  // The agent establishes the stream once, then receives commands
  // as they arrive. This avoids the agent polling for commands.
  rpc StreamCommands(Command) returns (stream Result);

  // BidirectionalStream is a bidirectional streaming RPC — both sides
  // send streams independently.
  //
  // WHY: For real-time telemetry with real-time command relay.
  // The agent sends MetricReports continuously while receiving
  // Commands simultaneously. This is the highest-performance mode.
  rpc BidirectionalStream(stream MetricReport) returns (stream Command);
}
```

### Proto3 vs Proto2

```protobuf
// DEEP DIVE: Why proto3?
//
// Proto2 has required/optional keywords. Proto3 removed them.
// In proto3:
//   - All fields are optional by default
//   - Zero values (0, "", false, []) mean "unset"
//   - You cannot distinguish "field set to 0" from "field not set"
//
// If you need to distinguish zero from unset, use wrapper types:
import "google/protobuf/wrappers.proto";
message Config {
  google.protobuf.Int64Value timeout_ms = 1; // nil means unset, 0 means zero
}
//
// For our AgentBridge, proto3 is sufficient because:
//   - Agent IDs are always positive (0 means invalid)
//   - Timestamps are always positive
//   - We can use empty string for "no reason" instead of distinguishing unset
```

---

## Pattern 2: gRPC Server in Go

### Generate Go Code from Proto

```bash
# Install protoc (the protobuf compiler)
# Linux:
sudo apt-get install -y protobuf-compiler
# macOS:
brew install protobuf

# Install Go gRPC plugins
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# Generate Go code from the proto file
# WHY: protoc reads .proto and generates .pb.go files with types + gRPC stubs
protoc --go_out=. --go_opt=paths=source_relative \
       --go-grpc_out=. --go-grpc_opt=paths=source_relative \
       agentbridge/agentbridge.proto
```

### Go Server Implementation

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
	"google.golang.org/grpc/status"

	pb "github.com/agentic-platform/agentbridge"
)

// AgentBridgeServer implements the AgentBridge gRPC service.
//
// WHY: This server runs in the Go gateway process. It receives telemetry
// from Elixir agents and relays commands back to them. The gateway
// aggregates metrics for Prometheus scraping.
type AgentBridgeServer struct {
	pb.UnimplementedAgentBridgeServer

	// mu protects concurrent access to metrics map
	// WHY: Multiple agents call ReportMetrics concurrently — we need
	// a mutex to prevent data races on the metrics map.
	mu sync.RWMutex

	// metrics stores the latest MetricReport per agent
	// KEY: agent_id, VALUE: the most recent MetricReport
	metrics map[int64]*pb.MetricReport

	// commandSubscribers tracks active command streams
	// WHY: When StreamCommands is called, we store the send function here
	// so the gateway can push commands to agents at any time.
	commandSubscribers map[int64]chan<- *pb.Command
}

// NewAgentBridgeServer creates a new server instance.
//
// WHY: Constructor pattern ensures the maps are initialized.
// COMMON MISTAKE: Forgetting to initialize maps — causes nil map panic
// on first write.
func NewAgentBridgeServer() *AgentBridgeServer {
	return &AgentBridgeServer{
		metrics:           make(map[int64]*pb.MetricReport),
		commandSubscribers: make(map[int64]chan<- *pb.Command),
	}
}

// ReportMetrics handles unary metric reports from agents.
//
// WHY: Unary RPC is the simplest pattern — agent sends one report,
// server acknowledges. Used for periodic telemetry that doesn't need streaming.
//
// PARAMETERS:
//   - ctx: request context, cancelled if client disconnects or deadline exceeded
//   - in: the MetricReport sent by the agent
//
// RETURNS:
//   - *pb.Ack: acknowledgment with acceptance status and recommended interval
//   - error: gRPC error if something goes wrong
func (s *AgentBridgeServer) ReportMetrics(
	ctx context.Context,
	in *pb.MetricReport,
) (*pb.Ack, error) {
	// Validate the incoming report
	// WHY: Reject bad data at the boundary. Letting invalid metrics
	// into the system causes wrong alerts and bad dashboards.
	if in.AgentId == 0 {
		return &pb.Ack{
			Accepted: false,
			Reason:   "agent_id must be non-zero",
		}, nil
	}

	// Lock for writing — multiple agents report concurrently
	s.mu.Lock()
	s.metrics[in.AgentId] = in
	s.mu.Unlock()

	log.Printf("Received metrics from agent %d: state=%s, completed=%d, failed=%d",
		in.AgentId, in.State, in.TasksCompleted, in.TasksFailed)

	// Calculate recommended interval based on current load
	// WHY: If we're receiving too many reports, ask agents to slow down.
	// If load is light, ask them to report more frequently.
	interval := s.calculateInterval()

	return &pb.Ack{
		Accepted:            true,
		RecommendedIntervalMs: interval,
		ServerTimestampNs:   time.Now().UnixNano(),
	}, nil
}

// StreamCommands implements server-streaming RPC.
//
// WHY: The agent opens one connection and receives a stream of commands.
// This is more efficient than the agent polling for commands — lower
// latency, less network overhead.
//
// PARAMETERS:
//   - in: the initial Command (used for agent identification)
//   - stream: server-side stream to send Results back
//
// RETURNS:
//   - error: gRPC error or nil on clean close
func (s *AgentBridgeServer) StreamCommands(
	in *pb.Command,
	stream pb.AgentBridge_StreamCommandsServer,
) error {
	// Extract agent ID from the initial command payload
	// WHY: The first command identifies which agent is listening.
	agentID := in.Payload["agent_id"]
	if agentID == "" {
		return status.Errorf(codes.InvalidArgument, "first command must include agent_id in payload")
	}

	// Parse agent ID — in production, use strconv.ParseInt
	var id int64
	fmt.Sscanf(agentID, "%d", &id)

	// Create a channel for this agent's command queue
	// DEEP DIVE: Channels are Go's concurrency primitive. One channel per agent
	// ensures commands for agent A don't leak to agent B.
	cmdChan := make(chan *pb.Command, 100) // buffered: 100 commands max
	defer close(cmdChan)

	// Register this agent's command channel
	s.mu.Lock()
	s.commandSubscribers[id] = cmdChan
	s.mu.Unlock()

	// Unregister on disconnect
	defer func() {
		s.mu.Lock()
		delete(s.commandSubscribers, id)
		s.mu.Unlock()
	}()

	log.Printf("Agent %d started command stream", id)

	// Block until client disconnects or context is cancelled
	// WHY: This goroutine stays alive as long as the agent is connected.
	// When the agent disconnects, the context is cancelled and we return.
	for {
		select {
		case cmd, ok := <-cmdChan:
			if !ok {
				return nil // channel closed — clean shutdown
			}
			// Send the command to the agent via the stream
			if err := stream.Send(cmd); err != nil {
				log.Printf("Failed to send command to agent %d: %v", id, err)
				return err
			}
		case <-stream.Context().Done():
			// Client disconnected — clean up
			log.Printf("Agent %d disconnected", id)
			return stream.Context().Err()
		}
	}
}

// SendCommand pushes a command to a connected agent.
//
// WHY: External systems (K8s operator, CLI) call this to send commands
// to agents. It's not a gRPC method — it's an internal API used by
// the gateway's HTTP endpoints.
//
// PARAMETERS:
//   - agentID: target agent
//   - cmd: the command to send
//
// RETURNS:
//   - error: nil if sent, error if agent not connected
func (s *AgentBridgeServer) SendCommand(agentID int64, cmd *pb.Command) error {
	s.mu.RLock()
	ch, exists := s.commandSubscribers[agentID]
	s.mu.RUnlock()

	if !exists {
		return fmt.Errorf("agent %d not connected", agentID)
	}

	// Non-blocking send — if the channel is full, drop the command
	// WHY: Blocking would stall the gateway. Better to drop and let
	// the operator retry than to block all other agents.
	select {
	case ch <- cmd:
		return nil
	default:
		return fmt.Errorf("agent %d command queue full", agentID)
	}
}

// calculateInterval dynamically adjusts reporting frequency.
//
// WHY: Under heavy load, thousands of agents reporting every second
// overwhelms the gateway. This function recommends longer intervals
// when the agent count is high.
//
// RETURNS:
//   - int64: recommended reporting interval in milliseconds
func (s *AgentBridgeServer) calculateInterval() int64 {
	s.mu.RLock()
	count := len(s.metrics)
	s.mu.RUnlock()

	switch {
	case count < 10:
		return 1000 // 1 second — light load, report frequently
	case count < 100:
		return 5000 // 5 seconds — moderate load
	default:
		return 10000 // 10 seconds — heavy load, reduce reporting
	}
}

func main() {
	// Listen on port 50051 — the standard gRPC port
	// WHY: 50051 is the conventional gRPC port. Using a standard port
	// makes firewall rules and service discovery simpler.
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	// Create gRPC server with default options
	// DEEP DIVE: grpc.NewServer() without options uses:
	//   - No TLS (fine for dev, mandatory for prod)
	//   - No interceptors (we'll add logging interceptors in production)
	//   - Default max message size (4MB)
	s := grpc.NewServer()

	// Register our service implementation
	pb.RegisterAgentBridgeServer(s, NewAgentBridgeServer())

	log.Println("AgentBridge gRPC server listening on :50051")
	if err := s.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}
```

---

## Pattern 3: gRPC Client in Elixir

### Generate Elixir Code from Proto

```bash
# Install protoc (if not already installed)
# Then install the Elixir protobuf library
mix new agent_bridge
cd agent_bridge

# Add dependencies to mix.exs
# (see code below for the mix.exs additions)

# Get dependencies
mix deps.get

# Generate Elixir structs and client from the proto file
# WHY: This produces modules like AgentBridge.MetricReport, AgentBridge.Ack, etc.
mix grpc.gen --paths=../proto --out=lib
```

### Elixir Client Implementation

```elixir
defmodule AgentBridge.Client do
  @moduledoc """
  gRPC client for communicating with the Go AgentBridge gateway.

  This module wraps the generated gRPC client with a simpler API
  that Elixir agents can call directly.

  ## Why a Wrapper?

  The generated gRPC client requires channel management, connection
  options, and error handling. This module hides that complexity
  behind simple functions like `report_metrics/1`.

  ## Usage

      # In an agent's GenServer
      AgentBridge.Client.report_metrics(%{
        agent_id: 42,
        state: "executing",
        tasks_completed: 10,
        tasks_failed: 1,
        memory_bytes: 1_048_576,
        last_task_duration_us: 150_000,
        metadata: %{"project" => "agentic-platform"}
      })
  """

  # The gateway's gRPC endpoint
  # WHY: In production, this comes from environment variables or service discovery.
  # For dev, localhost is fine.
  @gateway_endpoint "localhost:50051"

  # Default channel options
  # DEEP DIVE: gRPC channels are long-lived connections. The :adapter option
  # specifies which HTTP/2 library to use. Gun is the recommended Elixir adapter.
  @channel_opts [
    adapter: GRPC.Client.Adapter.Gun,
    # Keep the connection alive with periodic pings
    keepalive: 30_000,
    # Max message size — must match the server's limit
    max_receive_message_length: 4_194_304
  ]

  @doc """
  Reports agent metrics to the Go gateway.

  Sends a MetricReport and receives an Ack. If the gateway is down,
  returns an error tuple instead of crashing — agents must be resilient
  to gateway failures.

  ## Parameters

    - metrics: map with keys matching the MetricReport proto message

  ## Returns

    - `{:ok, ack}` — successful report with server acknowledgment
    - `{:error, reason}` — connection failure or rejection

  ## Edge Cases

    - Gateway unreachable: returns `{:error, :gateway_unreachable}`
    - Invalid agent_id (0): returns `{:error, :invalid_agent_id}`
    - Gateway overloaded: returns `{:ok, ack}` with longer interval
  """
  @spec report_metrics(map()) :: {:ok, map()} | {:error, atom()}
  def report_metrics(metrics) do
    # Validate required fields before sending
    # WHY: Failing fast with a clear error is better than sending bad data
    # and getting a confusing gRPC error back.
    case validate_metrics(metrics) do
      :ok ->
        # Build the protobuf message from the map
        # WHY: Using keyword list conversion because the generated protobuf
        # structs expect atom keys, not string keys from a map.
        report = %AgentBridge.MetricReport{
          agent_id: metrics.agent_id,
          state: metrics.state,
          tasks_completed: metrics[:tasks_completed] || 0,
          tasks_failed: metrics[:tasks_failed] || 0,
          memory_bytes: metrics[:memory_bytes] || 0,
          last_task_duration_us: metrics[:last_task_duration_us] || 0,
          timestamp_ns: System.system_time(:nanosecond),
          metadata: metrics[:metadata] || %{}
        }

        # Open a channel and make the RPC call
        # COMMON MISTAKE: Creating a new channel for every call.
        # Channels should be reused — create once, call many times.
        # In production, use a pool or a persistent connection.
        channel = GRPC.Channel.new(@gateway_endpoint, @channel_opts)

        case AgentBridge.AgentBridge.Stub.report_metrics(channel, report) do
          {:ok, ack} ->
            {:ok, ack}

          {:error, status} ->
            Logger.warning("gRPC report failed: #{inspect(status)}")
            {:error, :rpc_failed}
        end

      {:error, _} = err ->
        err
    end
  end

  @doc """
  Starts a bidirectional stream for real-time command relay.

  This function spawns a process that continuously sends MetricReports
  and receives Commands from the gateway. Commands are forwarded to
  the calling agent's PID.

  ## Parameters

    - agent_id: the agent's unique identifier
    - report_fun: zero-arity function that returns the current MetricReport
    - command_handler: function that handles incoming Commands

  ## Returns

    - `{:ok, pid}` — the streaming process PID
    - `{:error, reason}` — connection failure
  """
  @spec start_command_stream(integer(), (-> map()), (map() -> any())) ::
          {:ok, pid()} | {:error, atom()}
  def start_command_stream(agent_id, report_fun, command_handler) do
    channel = GRPC.Channel.new(@gateway_endpoint, @channel_opts)

    # Spawn a supervised process for the stream
    # WHY: If the stream process crashes, the supervisor restarts it.
    # The stream is long-lived — it must survive individual failures.
    Task.Supervisor.start_child(AgentBridge.TaskSupervisor, fn ->
      stream_commands_loop(channel, agent_id, report_fun, command_handler)
    end)
  end

  # Internal: runs the bidirectional stream loop.
  #
  # DEEP DIVE: Bidirectional streaming creates two independent streams:
  #   - Client → Server: MetricReports (we send)
  #   - Server → Client: Commands (we receive)
  # Both streams operate concurrently within a single HTTP/2 connection.
  defp stream_commands_loop(channel, agent_id, report_fun, command_handler) do
    # Create a stream — this opens the bidirectional channel
    case AgentBridge.AgentBridge.Stub.bidirectional_stream(channel) do
      {:ok, stream} ->
        # Spawn a sender and receiver concurrently
        sender_task =
          Task.async(fn ->
            stream_sender(stream, report_fun)
          end)

        receiver_task =
          Task.async(fn ->
            stream_receiver(stream, agent_id, command_handler)
          end)

        # Wait for both to complete (or one to fail)
        # WHY: If either side fails, we tear down the whole stream
        # and let the supervisor restart it.
        Task.await(sender_task)
        Task.await(receiver_task)

      {:error, reason} ->
        Logger.error("Failed to open bidirectional stream: #{inspect(reason)}")
        # COMMON MISTAKE: Not retrying here. In production, add exponential
        # backoff before the supervisor restarts the process.
        :timer.sleep(1_000)
        stream_commands_loop(channel, agent_id, report_fun, command_handler)
    end
  end

  # Sends MetricReports on a schedule via the stream.
  #
  # WHY: This loop sends reports at the interval recommended by the server.
  # It reads the recommended_interval_ms from the last Ack to adjust dynamically.
  defp stream_sender(stream, report_fun) do
    metrics = report_fun.()

    report = %AgentBridge.MetricReport{
      agent_id: metrics.agent_id,
      state: metrics.state,
      tasks_completed: metrics[:tasks_completed] || 0,
      tasks_failed: metrics[:tasks_failed] || 0,
      memory_bytes: metrics[:memory_bytes] || 0,
      last_task_duration_us: metrics[:last_task_duration_us] || 0,
      timestamp_ns: System.system_time(:nanosecond),
      metadata: metrics[:metadata] || %{}
    }

    GRPC.Stream.send(stream, report)

    # Sleep for the default interval, then send again
    # DEEP DIVE: In production, you'd parse the Ack's recommended_interval_ms
    # and use that instead of a fixed 5 seconds.
    Process.sleep(5_000)
    stream_sender(stream, report_fun)
  end

  # Receives Commands from the stream and dispatches them.
  #
  # WHY: Each command must be handled independently. The command_handler
  # function is provided by the agent — this module doesn't know what
  # commands look like internally.
  defp stream_receiver(stream, agent_id, command_handler) do
    case GRPC.Stream.recv(stream) do
      {:ok, command} ->
        # Handle the command asynchronously
        # WHY: We don't want to block the stream while processing a command.
        # Spawn a task so the stream can continue receiving.
        Task.start(fn ->
          command_handler.(command)
        end)

        stream_receiver(stream, agent_id, command_handler)

      {:error, :closed} ->
        Logger.info("Command stream closed by server")
        :ok

      {:error, reason} ->
        Logger.error("Stream receive error: #{inspect(reason)}")
        {:error, reason}
    end
  end

  # Validates the metrics map before sending.
  #
  # WHY: Catching validation errors locally gives clearer error messages
  # than waiting for a gRPC UNAVAILABLE or INVALID_ARGUMENT response.
  defp validate_metrics(metrics) do
    cond do
      not is_map_key(metrics, :agent_id) ->
        {:error, :missing_agent_id}

      metrics.agent_id == 0 ->
        {:error, :invalid_agent_id}

      not is_map_key(metrics, :state) ->
        {:error, :missing_state}

      true ->
        :ok
    end
  end
end
```

---

## Pattern 4: Streaming Patterns

### When to Use Each Pattern

| Pattern | Use Case | Latency | Complexity |
|---------|----------|---------|------------|
| Unary | Periodic telemetry reports | Medium | Low |
| Server-streaming | Gateway pushes commands | Low | Medium |
| Bidirectional | Real-time bidirectional control | Lowest | High |

### Stream Lifecycle

```
Agent A                          Go Gateway
  │                                  │
  │──── ReportMetrics ──────────────>│  Unary: report, get ack
  │<─── Ack (interval=5000ms) ──────│
  │                                  │
  │──── StreamCommands ─────────────>│  Server-streaming: open
  │<──── Command (restart) ─────────│  Server pushes commands
  │──── Result (success) ──────────>│
  │<──── Command (reconfigure) ─────│
  │──── Result (success) ──────────>│
  │<──── Command (stop) ────────────│
  │                                  │
  │──── BidirectionalStream ────────>│  Bidirectional: open
  │──── MetricReport ──────────────>│  Client sends continuously
  │<──── Command (pause) ───────────│  Server sends concurrently
  │──── MetricReport ──────────────>│
  │──── Result (paused) ───────────>│
```

### Error Handling in Streams

```go
// Go server: handle stream errors gracefully
func (s *AgentBridgeServer) BidirectionalStream(
	stream pb.AgentBridge_BidirectionalStreamServer,
) error {
	for {
		// Receive the next MetricReport from the agent
		report, err := stream.Recv()
		if err == io.EOF {
			// Agent closed the stream cleanly
			log.Println("Agent closed stream")
			return nil
		}
		if err != nil {
			// Network error or agent crashed
			// WHY: We don't return an error here — the stream is already broken.
			// Log and return nil to signal a clean server-side shutdown.
			log.Printf("Stream error: %v", err)
			return nil
		}

		// Process the report and send back a command if needed
		if s.shouldSendCommand(report) {
			cmd := s.buildCommand(report)
			if err := stream.Send(cmd); err != nil {
				log.Printf("Failed to send command: %v", err)
				return nil
			}
		}
	}
}
```

```elixir
# Elixir client: handle stream errors gracefully
defp stream_receiver(stream, agent_id, command_handler) do
  case GRPC.Stream.recv(stream) do
    {:ok, command} ->
      # Process command in a separate task
      # WHY: Never block the stream receiver — it must stay responsive
      Task.start(fn -> command_handler.(command) end)
      stream_receiver(stream, agent_id, command_handler)

    {:error, :closed} ->
      # Server closed the stream — this is normal during shutdown
      Logger.info("Stream closed by server (graceful shutdown)")
      :ok

    {:error, %{code: :unavailable}} ->
      # Server is unreachable — let the supervisor handle restart
      # COMMON MISTAKE: Catching this and retrying manually. The supervisor
      # already handles restarts with backoff. Don't fight the supervisor.
      Logger.warning("Server unavailable, supervisor will restart")
      {:error, :unavailable}

    {:error, reason} ->
      Logger.error("Unexpected stream error: #{inspect(reason)}")
      {:error, reason}
  end
end
```

---

## Pattern 5: Cross-Language Type Mapping

### How Protobuf Types Map

| Protobuf | Go | Elixir |
|----------|-----|--------|
| int32 | int32 | integer() |
| int64 | int64 | integer() |
| float | float32 | float() |
| double | float64 | float() |
| string | string | binary() |
| bool | bool | boolean() |
| bytes | []byte | binary() |
| map<K,V> | map[K]V | %{optional(K) => V} |
| repeated T | []T | [T] |
| message | struct | struct |

### Common Type Gotchas

```go
// DEEP DIVE: Go int64 vs protobuf int64
//
// In Go, int64 is a 64-bit signed integer.
// In protobuf, int64 is a variable-length encoding (Varint).
// The Go generated code handles the conversion automatically.
//
// BUT: JSON marshaling of int64 uses strings ("123" not 123) to avoid
// JavaScript precision loss. If you ever marshal protobuf to JSON,
// watch for string-wrapped numbers.
type MetricReport struct {
	AgentId          int64             `protobuf:"varint,1,opt,name=agent_id,json=agentId,proto3" json:"agent_id,omitempty"`
	TasksCompleted   int64             `protobuf:"varint,3,opt,name=tasks_completed,json=tasksCompleted,proto3" json:"tasks_completed,omitempty"`
	Metadata         map[string]string `protobuf:"bytes,8,rep,name=metadata,proto3" json:"metadata,omitempty" protobuf_key:"bytes,1,opt,name=key,proto3" protobuf_val:"bytes,2,opt,name=value,proto3"`
}
```

```elixir
# DEEP DIVE: Elixir atoms vs protobuf strings
#
# Protobuf maps use strings for keys. Elixir maps commonly use atoms.
# The generated protobuf code handles the conversion, but you need
# to be careful when building maps manually.
#
# WRONG: %{agent_id: 42} — atom key, won't serialize correctly
# RIGHT: %{"agent_id" => 42} — string key, matches protobuf
#
# The generated structs use atom keys internally:
%AgentBridge.MetricReport{
  agent_id: 42,        # atom key in struct, but protobuf uses varint encoding
  state: "executing",  # string in protobuf, binary in Elixir
  metadata: %{"key" => "value"}  # map with string keys
}
```

---

## Integration: Wiring It All Together

### Go Gateway main.go

```go
package main

import (
	"log"
	"net"
	"net/http"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"google.golang.org/grpc"
	"google.golang.org/grpc/health"
	"google.golang.org/grpc/health/grpc_health_v1"

	pb "github.com/agentic-platform/agentbridge"
)

func main() {
	// Start gRPC server for agent communication
	go startGRPCServer()

	// Start HTTP server for Prometheus metrics
	// WHY: Prometheus scrapes HTTP, not gRPC. We need both servers.
	startHTTPServer()
}

func startGRPCServer() {
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	s := grpc.NewServer()

	// Register the AgentBridge service
	bridgeServer := NewAgentBridgeServer()
	pb.RegisterAgentBridgeServer(s, bridgeServer)

	// Register health check service
	// WHY: K8s uses health checks to determine if the pod is ready.
	// Without this, K8s might route traffic to an unready pod.
	healthServer := health.NewServer()
	grpc_health_v1.RegisterHealthServer(s, healthServer)
	healthServer.SetServingStatus("agentbridge.AgentBridge", grpc_health_v1.HealthCheckResponse_SERVING)

	log.Println("gRPC server listening on :50051")
	if err := s.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}

func startHTTPServer() {
	// Prometheus metrics endpoint
	// WHY: Prometheus scrapes /metrics every 15 seconds.
	// This endpoint exposes all registered metrics.
	http.Handle("/metrics", promhttp.Handler())

	// Health check endpoint for K8s
	http.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})

	log.Println("HTTP server listening on :8080")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatalf("HTTP server failed: %v", err)
	}
}
```

### Elixir Agent Integration

```elixir
defmodule AgenticPlatform.Agent do
  @moduledoc """
  An agent that reports metrics to the Go gateway via gRPC.

  This GenServer runs as a child of the agent supervisor.
  It periodically sends MetricReports and handles Commands
  received through the bidirectional stream.
  """

  use GenServer

  require Logger

  # Client API

  def start_link(opts) do
    agent_id = Keyword.fetch!(opts, :agent_id)
    GenServer.start_link(__MODULE__, opts, name: {:via, Registry, {AgenticPlatform.AgentRegistry, agent_id}})
  end

  # Server callbacks

  @impl true
  def init(opts) do
    agent_id = Keyword.fetch!(opts, :agent_id)

    # Start the bidirectional stream to the Go gateway
    # WHY: The stream is started once during init. If it fails,
    # the supervisor restarts the whole GenServer.
    {:ok, stream_pid} = AgentBridge.Client.start_command_stream(
      agent_id,
      fn -> get_current_metrics(agent_id) end,
      &handle_command/1
    )

    {:ok, %{
      agent_id: agent_id,
      state: "idle",
      tasks_completed: 0,
      tasks_failed: 0,
      memory_bytes: 0,
      stream_pid: stream_pid
    }}
  end

  @impl true
  def handle_cast({:task_completed, duration_us}, state) do
    # Update local metrics
    new_state = %{state |
      tasks_completed: state.tasks_completed + 1,
      state: "idle"
    }

    # Report immediately to the gateway
    # WHY: Don't wait for the next periodic report — important state changes
    # should be reported immediately for accurate dashboards.
    Task.start(fn ->
      AgentBridge.Client.report_metrics(%{
        agent_id: state.agent_id,
        state: "idle",
        tasks_completed: new_state.tasks_completed,
        tasks_failed: new_state.tasks_failed,
        memory_bytes: :erlang.memory(:total),
        last_task_duration_us: duration_us
      })
    end)

    {:noreply, new_state}
  end

  @impl true
  def handle_info({:command, command}, state) do
    # Handle commands from the Go gateway
    Logger.info("Received command: #{command.command_type}")

    case command.command_type do
      "pause" ->
        {:noreply, %{state | state: "paused"}}

      "resume" ->
        {:noreply, %{state | state: "idle"}}

      "stop" ->
        {:stop, :normal, state}

      _ ->
        Logger.warning("Unknown command type: #{command.command_type}")
        {:noreply, state}
    end
  end

  defp get_current_metrics(agent_id) do
    %{
      agent_id: agent_id,
      state: "idle",
      tasks_completed: 0,
      tasks_failed: 0,
      memory_bytes: :erlang.memory(:total),
      metadata: %{"node" => to_string(Node.self())}
    }
  end

  defp handle_command(command) do
    # Forward command to the GenServer
    # WHY: We're in a Task process, not the GenServer. We need to send
    # the command to the GenServer so it can update its state safely.
    GenServer.cast(__MODULE__, {:command, command})
  end
end
```

---

## Testing the Bridge

### Start the Go Server

```bash
# Terminal 1: Start the Go gRPC server
cd go-gateway
go run main.go
# Expected: "AgentBridge gRPC server listening on :50051"
# Expected: "HTTP server listening on :8080"
```

### Test with Elixir Client

```bash
# Terminal 2: Start the Elixir application
cd agent_bridge
iex -S mix

# Send a test metric report
iex> AgentBridge.Client.report_metrics(%{
  agent_id: 42,
  state: "executing",
  tasks_completed: 5,
  tasks_failed: 0,
  memory_bytes: 1_048_576,
  metadata: %{"project" => "agentic-platform"}
})
# Expected: {:ok, %{accepted: true, recommended_interval_ms: 1000, ...}}

# Check the Go server logs — you should see:
# "Received metrics from agent 42: state=executing, completed=5, failed=0"
```

### Test with grpcurl (CLI)

```bash
# grpcurl is a CLI tool for testing gRPC services
# Install: go install github.com/fullstorydev/grpcurl/cmd/grpcurl@latest

# List available services
grpcurl -plaintext localhost:50051 list
# Expected: agentbridge.AgentBridge

# List methods in AgentBridge
grpcurl -plaintext localhost:50051 list agentbridge.AgentBridge
# Expected: ReportMetrics, StreamCommands, BidirectionalStream

# Send a test metric report
grpcurl -plaintext -d '{"agent_id": 42, "state": "idle", "tasks_completed": 10}' \
  localhost:50051 agentbridge.AgentBridge/ReportMetrics
```

---

## Common Mistakes

1. **Creating a new gRPC channel per call** — channels are expensive to create. Reuse them.
2. **Not handling io.EOF in streams** — the stream closing is normal, not an error.
3. **Blocking in stream callbacks** — always spawn tasks for command handling.
4. **Using proto2 syntax** — proto3 is required for gRPC. Proto2 won't compile.
5. **Mixing int32 and int64** — agent IDs and timestamps should always be int64.

---

## What's Next

Your Go gateway and Elixir agents can now communicate through gRPC. Continue to [Module 14: Observability Stack](14-observability-stack.md) to add full-stack monitoring.
