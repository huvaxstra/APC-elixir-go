# Module 2 Exercise: Health-Check CLI + API

> **Goal**: Build a CLI tool with Cobra that starts an HTTP server with health endpoints.
> This exercise reinforces CLI frameworks, HTTP handlers, middleware, and graceful shutdown.

---

## Starter Code

```go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/spf13/cobra"
)

// HealthResponse is the JSON response for health endpoints.
type HealthResponse struct {
    Status    string `json:"status"`
    Timestamp string `json:"timestamp"`
    Uptime    string `json:"uptime,omitempty"`
}

// Server holds the state for our HTTP server.
type Server struct {
    StartTime time.Time
    Mux       *http.ServeMux
}

// NewServer creates a new server instance with routes registered.
func NewServer() *Server {
    s := &Server{
        StartTime: time.Now(),
        Mux:       http.NewServeMux(),
    }
    s.registerRoutes()
    return s
}

// registerRoutes sets up the HTTP endpoints.
// TODO: Register handlers for /healthz and /readyz
func (s *Server) registerRoutes() {
    // TODO: Use s.Mux.HandleFunc to register:
    //   "/healthz" → s.healthHandler
    //   "/readyz"  → s.readinessHandler
}

// healthHandler responds with liveness status.
// Returns HTTP 200 if the server is running.
// TODO: Implement this method on Server.
// It should:
//   1. Create a HealthResponse with Status="alive" and current Timestamp
//   2. Set Content-Type header to "application/json"
//   3. Encode the response as JSON using json.NewEncoder(w).Encode()
func (s *Server) healthHandler(w http.ResponseWriter, r *http.Request) {
    // TODO: Implement
}

// readinessHandler responds with readiness status.
// Returns HTTP 200 if ready, HTTP 503 if not.
// TODO: Implement this method on Server.
// It should:
//   1. Check if uptime is > 0 (server has been running)
//   2. If ready: Status="ready", calculate Uptime as time.Since(s.StartTime)
//   3. If not ready: Status="not_ready", return HTTP 503
//   4. Set Content-Type and encode as JSON
func (s *Server) readinessHandler(w http.ResponseWriter, r *http.Request) {
    // TODO: Implement
}

// LoggingMiddleware logs each request with method, path, and duration.
// It wraps an http.Handler and adds logging behavior.
// TODO: Implement this function.
// It should return a new http.HandlerFunc that:
//   1. Records start time
//   2. Calls next.ServeHTTP(w, r)
//   3. Prints: [HH:MM:SS] METHOD /path (duration)
func LoggingMiddleware(next http.Handler) http.Handler {
    // TODO: Implement
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // TODO: Implement the logging logic
    })
}

// RecoveryMiddleware catches panics and returns HTTP 500.
// Without this, a panic in any handler crashes the entire server.
// TODO: Implement this function.
// It should return a new http.HandlerFunc that:
//   1. defers a recover() function
//   2. If recover() catches a panic, prints the error and returns 500
//   3. Calls next.ServeHTTP(w, r) in the normal path
func RecoveryMiddleware(next http.Handler) http.Handler {
    // TODO: Implement
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // TODO: Implement the recovery logic
    })
}

// buildCLI creates the Cobra command structure.
// TODO: Implement this function.
// It should create:
//   1. A rootCmd with Use="healthcheck" and Short="Service health monitoring tool"
//   2. A serveCmd with:
//      - Use="serve", Short="Start the health check server"
//      - Flags: --port (int, default 8080), --host (string, default "0.0.0.0")
//      - Run function that creates a server and starts it
//   3. A checkCmd with:
//      - Use="check <url>", Short="Check health of a remote service"
//      - Args: cobra.ExactArgs(1)
//      - Run function that makes an HTTP GET to the URL and prints status
func buildCLI() *cobra.Command {
    // TODO: Implement
    return nil
}

func main() {
    cmd := buildCLI()
    if err := cmd.Execute(); err != nil {
        os.Exit(1)
    }
}
```

---

## Hints

### Hint 1: Registering routes
Use `s.Mux.HandleFunc("/healthz", s.healthHandler)`. The pattern must start with `/`.

### Hint 2: JSON response
Use `json.NewEncoder(w).Encode(data)` — it handles serialization and writes to the response writer. Set the header first: `w.Header().Set("Content-Type", "application/json")`.

### Hint 3: Middleware pattern
A middleware returns `http.HandlerFunc(func(w, r) { ... next.ServeHTTP(w, r) ... })`. The key is that it wraps the next handler.

### Hint 4: Cobra structure
Create `rootCmd := &cobra.Command{Use: "healthcheck", ...}`, then `serveCmd := &cobra.Command{Use: "serve", ...}`, then `rootCmd.AddCommand(serveCmd)`.

### Hint 5: Graceful shutdown
Use `signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)` to get a context that cancels on Ctrl+C.

### Hint 6: Common mistakes
- Don't forget `w.Header().Set("Content-Type", "application/json")` before writing the response
- Don't forget to check `r.Method` if you want to restrict HTTP methods
- Don't forget `defer r.Body.Close()` if you read from the request body

---

## Solution

```go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/spf13/cobra"
)

// HealthResponse is the JSON response for health endpoints.
type HealthResponse struct {
    Status    string `json:"status"`
    Timestamp string `json:"timestamp"`
    Uptime    string `json:"uptime,omitempty"`
}

// Server holds the state for our HTTP server.
type Server struct {
    StartTime time.Time
    Mux       *http.ServeMux
}

// NewServer creates a new server instance with routes registered.
func NewServer() *Server {
    s := &Server{
        StartTime: time.Now(),
        Mux:       http.NewServeMux(),
    }
    s.registerRoutes()
    return s
}

// registerRoutes sets up the HTTP endpoints.
// Routes are registered on the Mux before the server starts.
func (s *Server) registerRoutes() {
    s.Mux.HandleFunc("/healthz", s.healthHandler)
    s.Mux.HandleFunc("/readyz", s.readinessHandler)
}

// healthHandler responds with liveness status.
// This is the simplest check — just confirms the server is running.
// Kubernetes uses this to decide whether to restart a pod.
func (s *Server) healthHandler(w http.ResponseWriter, r *http.Request) {
    // COMMON MISTAKE: Forgetting to set Content-Type before writing
    // If you set it after WriteHeader, it has no effect
    w.Header().Set("Content-Type", "application/json")

    resp := HealthResponse{
        Status:    "alive",
        Timestamp: time.Now().Format(time.RFC3339),
    }

    // json.NewEncoder handles serialization and writes to the response
    if err := json.NewEncoder(w).Encode(resp); err != nil {
        // This should never fail for a simple struct, but handle it anyway
        http.Error(w, "Failed to encode response", http.StatusInternalServerError)
    }
}

// readinessHandler responds with readiness status.
// This checks whether the server can handle requests.
// Returns 503 if not ready — load balancers stop sending traffic.
func (s *Server) readinessHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")

    uptime := time.Since(s.StartTime)

    // DEEP DIVE: Why check uptime > 0?
    // In production, readiness checks verify database connections,
    // cache availability, and other dependencies. Here we simulate
    // that by checking if the server has been running for > 0 seconds.
    // A real readiness check might ping the database:
    //   if err := db.Ping(); err != nil { ready = false }
    if uptime > 0 {
        resp := HealthResponse{
            Status:    "ready",
            Timestamp: time.Now().Format(time.RFC3339),
            Uptime:    uptime.Truncate(time.Second).String(),
        }
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(resp)
    } else {
        resp := HealthResponse{
            Status:    "not_ready",
            Timestamp: time.Now().Format(time.RFC3339),
        }
        w.WriteHeader(http.StatusServiceUnavailable)
        json.NewEncoder(w).Encode(resp)
    }
}

// LoggingMiddleware logs each request with method, path, and duration.
// This wraps the next handler and adds logging behavior.
// Think of it like a security camera at the entrance — every request
// is recorded as it passes through.
func LoggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Record start time
        start := time.Now()

        // Pass request to the next handler
        next.ServeHTTP(w, r)

        // Log after handler completes
        duration := time.Since(start)
        fmt.Printf("[%s] %s %s (%v)\n",
            time.Now().Format("15:04:05"),
            r.Method,
            r.URL.Path,
            duration,
        )
    })
}

// RecoveryMiddleware catches panics and returns HTTP 500.
// Without this, a panic in any handler crashes the entire server.
// This is like a safety net under a tightrope walker — if they fall,
// the net catches them instead of hitting the ground.
func RecoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // defer + recover is Go's panic recovery mechanism
        // It runs when the goroutine panics, catching the panic value
        defer func() {
            if err := recover(); err != nil {
                fmt.Printf("PANIC recovered: %v\n", err)
                http.Error(w, "Internal Server Error", http.StatusInternalServerError)
            }
        }()

        // Call the next handler — if it panics, recover() catches it
        next.ServeHTTP(w, r)
    })
}

// buildCLI creates the Cobra command structure.
// Cobra organizes CLI tools into hierarchical commands.
// Think of it like a tree: root → serve, root → check.
func buildCLI() *cobra.Command {
    var port int
    var host string

    // Root command — runs when no subcommand is given
    rootCmd := &cobra.Command{
        Use:   "healthcheck",
        Short: "Service health monitoring tool",
        Long:  "A CLI tool for monitoring service health with HTTP endpoints.",
        Run: func(cmd *cobra.Command, args []string) {
            fmt.Println("Healthcheck CLI — use 'serve' to start server, 'check' to test a service")
        },
    }

    // Serve command — starts the HTTP server
    serveCmd := &cobra.Command{
        Use:   "serve",
        Short: "Start the health check server",
        Long:  "Starts an HTTP server exposing /healthz and /readyz endpoints.",
        RunE: func(cmd *cobra.Command, args []string) error {
            addr := fmt.Sprintf("%s:%d", host, port)
            return runServer(addr)
        },
    }

    // Check command — tests a remote service
    checkCmd := &cobra.Command{
        Use:   "check <url>",
        Short: "Check health of a remote service",
        Long:  "Makes an HTTP GET request to the given URL and reports status.",
        Args:  cobra.ExactArgs(1),
        RunE: func(cmd *cobra.Command, args []string) error {
            url := args[0]

            // Create client with timeout
            client := &http.Client{Timeout: 5 * time.Second}

            fmt.Printf("Checking %s...\n", url)
            resp, err := client.Get(url)
            if err != nil {
                return fmt.Errorf("health check failed: %w", err)
            }
            defer resp.Body.Close()

            // Decode the response
            var health HealthResponse
            if err := json.NewDecoder(resp.Body).Decode(&health); err != nil {
                return fmt.Errorf("failed to parse response: %w", err)
            }

            // Print result
            if resp.StatusCode == http.StatusOK {
                fmt.Printf("✓ Status: %s\n", health.Status)
            } else {
                fmt.Printf("✗ Status: %s (HTTP %d)\n", health.Status, resp.StatusCode)
            }

            if health.Uptime != "" {
                fmt.Printf("  Uptime: %s\n", health.Uptime)
            }

            return nil
        },
    }

    // Add flags to serve command
    serveCmd.Flags().IntVarP(&port, "port", "p", 8080, "Port to listen on")
    serveCmd.Flags().StringVarP(&host, "host", "H", "0.0.0.0", "Host to bind to")

    // Register subcommands
    rootCmd.AddCommand(serveCmd)
    rootCmd.AddCommand(checkCmd)

    return rootCmd
}

// runServer starts the HTTP server with graceful shutdown.
// It listens for SIGINT (Ctrl+C) and SIGTERM (docker stop)
// and waits for active connections to finish before exiting.
func runServer(addr string) error {
    server := NewServer()

    // Apply middleware chain
    // Order matters: Recovery wraps everything (outermost),
    // then Logging, then the actual handler (innermost)
    var handler http.Handler = server.Mux
    handler = LoggingMiddleware(handler)
    handler = RecoveryMiddleware(handler)

    httpServer := &http.Server{
        Addr:         addr,
        Handler:      handler,
        ReadTimeout:  10 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  60 * time.Second,
    }

    // Create context that cancels on OS signals
    ctx, stop := signal.NotifyContext(context.Background(),
        os.Interrupt, syscall.SIGTERM,
    )
    defer stop()

    // Start server in background
    errChan := make(chan error, 1)
    go func() {
        fmt.Printf("Server starting on %s\n", addr)
        fmt.Printf("  Health:   http://%s/healthz\n", addr)
        fmt.Printf("  Ready:    http://%s/readyz\n", addr)
        fmt.Println("Press Ctrl+C to stop")
        if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            errChan <- err
        }
        close(errChan)
    }()

    // Wait for signal or error
    select {
    case <-ctx.Done():
        fmt.Println("\nShutting down gracefully...")
        shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
        defer cancel()
        if err := httpServer.Shutdown(shutdownCtx); err != nil {
            return fmt.Errorf("shutdown error: %w", err)
        }
        fmt.Println("Server stopped")
        return nil
    case err := <-errChan:
        return fmt.Errorf("server error: %w", err)
    }
}

func main() {
    cmd := buildCLI()
    if err := cmd.Execute(); err != nil {
        os.Exit(1)
    }
}
```

---

## Test Cases

```bash
# Build the tool
go build -o healthcheck .

# Start the server (runs in foreground, Ctrl+C to stop)
./healthcheck serve --port 8080

# In another terminal — check liveness
curl http://localhost:8080/healthz
# Expected: {"status":"alive","timestamp":"2025-01-15T10:30:00Z"}

# Check readiness
curl http://localhost:8080/readyz
# Expected: {"status":"ready","timestamp":"...","uptime":"5s"}

# Use the check command
./healthcheck check http://localhost:8080/healthz
# Expected: ✓ Status: alive

# Test graceful shutdown — start server, then Ctrl+C
./healthcheck serve
# Should print "Shutting down gracefully..." and "Server stopped"
```

---

## Extension Challenges

1. **Add middleware**: Implement a `CORSMiddleware` that adds `Access-Control-Allow-Origin: *` header.
2. **Add metrics endpoint**: Create `/metrics` that returns request count and average response time.
3. **Add config flags**: Add `--log-level` flag that controls verbose output.

---

**Next**: [Module 3 — Elixir Fundamentals](03-elixir-fundamentals.md)
