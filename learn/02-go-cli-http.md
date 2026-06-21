# Module 2: Go CLI & HTTP

> **What you'll learn**: Building CLI tools with Cobra, HTTP servers with net/http, middleware patterns, and graceful shutdown.
> By the end of this module you'll build a health-check CLI + API server.

---

## 1. Cobra — The CLI Framework

Cobra powers kubectl, Hugo, GitHub CLI, and thousands of other Go tools. It turns the mess of `os.Args` parsing into clean, hierarchical commands.

### Why Cobra?

```go
// WITHOUT Cobra — manual arg parsing is painful
func main() {
    if len(os.Args) < 2 {
        fmt.Println("Usage: app <command>")
        os.Exit(1)
    }

    switch os.Args[1] {
    case "serve":
        if len(os.Args) > 2 && os.Args[2] == "--port" {
            // parse port from os.Args[3]
            // what about --host? --timeout? --verbose?
            // this gets out of hand fast
        }
    case "check":
        // ...
    }
}
```

Cobra handles all of this — flags, subcommands, help text, completion, validation.

### Basic Cobra structure

```go
package main

import (
    "fmt"
    "os"

    "github.com/spf13/cobra"
)

// rootCmd is the base command. It runs when no subcommand is given.
var rootCmd = &cobra.Command{
    Use:   "healthcheck",
    Short: "A health monitoring CLI tool",
    Long: `Healthcheck is a tool for monitoring service health.
It provides commands to check individual services
and run comprehensive health audits.`,
    // Run is called when no subcommand is specified
    Run: func(cmd *cobra.Command, args []string) {
        fmt.Println("Healthcheck CLI — use --help to see commands")
    },
}

// serveCmd starts the health check API server
var serveCmd = &cobra.Command{
    Use:   "serve",
    Short: "Start the health check API server",
    Long:  "Starts an HTTP server that exposes health endpoints for monitoring.",
    // Args validates the number of positional arguments
    Args: cobra.NoArgs, // This command takes no arguments
    Run: func(cmd *cobra.Command, args []string) {
        // Get flag values with cmd.Flags().GetXxx()
        port, _ := cmd.Flags().GetInt("port")
        host, _ := cmd.Flags().GetString("host")
        verbose, _ := cmd.Flags().GetBool("verbose")

        fmt.Printf("Starting server on %s:%d\n", host, port)
        if verbose {
            fmt.Println("Verbose logging enabled")
        }
        // Server startup would go here
    },
}

// checkCmd checks health of a specific service
var checkCmd = &cobra.Command{
    Use:   "check <service-name>",
    Short: "Check health of a specific service",
    Long:  "Performs a health check against a named service and reports status.",
    // Args uses cobra.ExactArgs to require exactly 1 argument
    Args: cobra.ExactArgs(1),
    Run: func(cmd *cobra.Command, args []string) {
        serviceName := args[0]
        timeout, _ := cmd.Flags().GetDuration("timeout")

        fmt.Printf("Checking %s (timeout: %v)...\n", serviceName, timeout)
        // Health check logic would go here
        fmt.Printf("✓ %s is healthy\n", serviceName)
    },
}

func init() {
    // Register serve command as a subcommand of root
    rootCmd.AddCommand(serveCmd)

    // Register check command as a subcommand of root
    rootCmd.AddCommand(checkCmd)

    // Add flags to serve command
    // PersistentFlags persist across subcommands
    // Flags only persist within this command
    serveCmd.Flags().IntP("port", "p", 8080, "Port to listen on")
    serveCmd.Flags().StringP("host", "H", "0.0.0.0", "Host to bind to")
    serveCmd.Flags().BoolP("verbose", "v", false, "Enable verbose logging")

    // Add flags to check command
    checkCmd.Flags().DurationP("timeout", "t", 5*time.Second, "Health check timeout")
}

func main() {
    // Execute the root command — Cobra handles everything
    if err := rootCmd.Execute(); err != nil {
        // Cobra prints the error and usage automatically
        os.Exit(1)
    }
}
```

### Cobra flag types

```go
// String flag
cmd.Flags().String("name", "default", "Description")

// Int flag
cmd.Flags().Int("port", 8080, "Port number")

// Bool flag
cmd.Flags().Bool("verbose", false, "Enable verbose mode")

// Duration flag
cmd.Flags().Duration("timeout", 5*time.Second, "Request timeout")

// StringSlice flag — can be specified multiple times
cmd.Flags().StringSlice("service", []string{}, "Service names to check")

// The P variants add shorthand flags:
cmd.Flags().StringP("name", "n", "default", "Description")
// Now both --name and -n work
```

---

## 2. net/http — The Server

Go's standard library HTTP server is production-ready. No framework needed for basic use.

### Handler pattern

```go
// An http.HandlerFunc is any function with this signature:
// func(w http.ResponseWriter, r *http.Request)

// The Handler interface requires one method:
// ServeHTTP(http.ResponseWriter, *http.Request)
// Any struct with this method satisfies the interface.

func healthHandler(w http.ResponseWriter, r *http.Request) {
    // Only allow GET requests
    // COMMON MISTAKE: Forgetting to check the HTTP method
    if r.Method != http.MethodGet {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }

    // Set the response content type
    w.Header().Set("Content-Type", "application/json")

    // Write the response
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"status":"healthy"}`))
}

func readinessHandler(w http.ResponseWriter, r *http.Request) {
    // Readiness checks are more complex — verify dependencies
    // For example: database connection, cache availability, etc.
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"status":"ready","checks":{"database":"ok","cache":"ok"}}`))
}
```

### http.ServeMux — routing

```go
// ServeMux is Go's built-in router
mux := http.NewServeMux()

// Register handlers for specific paths
mux.HandleFunc("/healthz", healthHandler)      // Liveness check
mux.HandleFunc("/readyz", readinessHandler)    // Readiness check
mux.HandleFunc("/api/status", statusHandler)   // API endpoint

// Pattern matching:
// "/healthz"     — exact match
// "/api/"        — matches /api/ and everything under it (prefix)
// "/"            — matches everything (catch-all)

// DEEP DIVE: ServeMux vs third-party routers
// For simple APIs, ServeMux is fine. For complex routing with
// path parameters (/users/:id), middleware chains, or method-based
// routing, you'd use chi, gorilla/mux, or gin. But start simple.
```

---

## 3. Middleware — The Layered Onion

Middleware wraps handlers like layers of an onion. Each layer can modify the request before it reaches the handler, or modify the response after the handler finishes.

```go
// Middleware is a function that takes a handler and returns a new handler.
// Think of it as a wrapper: request comes in → middleware does something →
// passes to next handler → response goes out → middleware does something else.

type Middleware func(http.Handler) http.Handler

// Logging middleware — logs every request
func LoggingMiddleware(next http.Handler) http.Handler {
    // http.HandlerFunc adapts our function to the Handler interface
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Record start time
        start := time.Now()

        // Wrap ResponseWriter to capture the status code
        // DEEP DIVE: ResponseWriter.Write sets status to 200 by default.
        // To capture the actual status, we need a wrapper that intercepts
        // the WriteHeader call.
        wrapped := &statusResponseWriter{ResponseWriter: w, statusCode: http.StatusOK}

        // Call the next handler in the chain
        next.ServeHTTP(wrapped, r)

        // Log after the handler completes
        duration := time.Since(start)
        fmt.Printf("[%s] %s %s → %d (%v)\n",
            time.Now().Format("15:04:05"),
            r.Method,
            r.URL.Path,
            wrapped.statusCode,
            duration,
        )
    })
}

// statusResponseWriter wraps http.ResponseWriter to capture the status code
type statusResponseWriter struct {
    http.ResponseWriter
    statusCode int
}

// WriteHeader intercepts the status code before it's sent
func (w *statusResponseWriter) WriteHeader(code int) {
    w.statusCode = code
    w.ResponseWriter.WriteHeader(code)
}

// Recovery middleware — catches panics and returns 500
// This is critical in production — a panic in one request
// should not crash the entire server.
func RecoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if err := recover(); err != nil {
                // recover() catches the panic value
                fmt.Printf("PANIC: %v\n", err)
                http.Error(w, "Internal Server Error", http.StatusInternalServerError)
            }
        }()

        // Call next handler — if it panics, recover() catches it
        next.ServeHTTP(w, r)
    })
}

// RequestID middleware — adds a unique ID to each request
func RequestIDMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Generate a unique ID (simplified — real apps use UUID)
        requestID := fmt.Sprintf("req-%d", time.Now().UnixNano())

        // Add to response header
        w.Header().Set("X-Request-ID", requestID)

        // Add to request context so downstream handlers can use it
        ctx := context.WithValue(r.Context(), "request_id", requestID)
        r = r.WithContext(ctx)

        next.ServeHTTP(w, r)
    })
}
```

### Applying middleware

```go
// Middleware is applied in reverse order — the LAST one added
// runs FIRST when a request comes in.

// Request flow: Recovery → Logging → RequestID → Handler

mux := http.NewServeMux()
mux.HandleFunc("/healthz", healthHandler)
mux.HandleFunc("/readyz", readinessHandler)

// Chain: Recovery wraps everything, then Logging, then RequestID
var handler http.Handler = mux
handler = RequestIDMiddleware(handler)  // innermost
handler = LoggingMiddleware(handler)    // middle
handler = RecoveryMiddleware(handler)   // outermost — catches panics from all
```

---

## 4. Graceful Shutdown

When you stop a server, you don't want to kill active connections abruptly. Graceful shutdown waits for in-flight requests to complete.

```go
// signal.NotifyContext listens for OS signals and returns a context
// that is cancelled when the signal is received.
//
// Why context? Because Go uses contexts for cancellation propagation.
// When the context is cancelled, all operations using it stop.

func runServer(addr string) error {
    mux := http.NewServeMux()
    mux.HandleFunc("/healthz", healthHandler)
    mux.HandleFunc("/readyz", readinessHandler)

    server := &http.Server{
        Addr:    addr,
        Handler: mux,
        // Timeout prevents slow clients from holding connections forever
        ReadTimeout:  10 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  60 * time.Second,
    }

    // Create a context that cancels on SIGINT (Ctrl+C) or SIGTERM (docker stop)
    ctx, stop := signal.NotifyContext(context.Background(),
        os.Interrupt,
        syscall.SIGTERM,
    )
    defer stop()

    // Channel to receive server errors
    errChan := make(chan error, 1)

    // Start server in a goroutine
    go func() {
        fmt.Printf("Server starting on %s\n", addr)
        if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            errChan <- err
        }
        close(errChan)
    }()

    // Block until signal or server error
    select {
    case <-ctx.Done():
        // Signal received — start graceful shutdown
        fmt.Println("\nShutting down gracefully...")

        // Create a timeout context for the shutdown itself
        shutdownCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
        defer cancel()

        // server.Shutdown waits for active connections to finish
        if err := server.Shutdown(shutdownCtx); err != nil {
            return fmt.Errorf("shutdown error: %w", err)
        }
        fmt.Println("Server stopped")

    case err := <-errChan:
        return fmt.Errorf("server error: %w", err)
    }

    return nil
}
```

### Why graceful shutdown matters

```
Without graceful shutdown:
  Request comes in → Ctrl+C → Request dies → Data loss

With graceful shutdown:
  Request comes in → Ctrl+C → Server stops accepting new requests
  → Waits for active request to finish → Clean exit
```

**COMMON MISTAKE**: Forgetting to set timeouts on `http.Server`. Without them, slow clients can hold connections open indefinitely, eventually exhausting server resources.

---

## 5. Health Check Endpoints

```go
// /healthz — Liveness probe
// "Is the server running?" — answers yes/no, no deep checks.
// Kubernetes calls this to know if it should restart the pod.
func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusOK)
    w.Write([]byte(`{"status":"alive"}`))
}

// /readyz — Readiness probe
// "Can the server handle requests?" — checks dependencies.
// Kubernetes uses this to decide whether to route traffic.
func readinessHandler(w http.ResponseWriter, r *http.Request) {
    // Check each dependency
    checks := map[string]string{}

    // Check database
    if err := db.Ping(); err != nil {
        checks["database"] = "error: " + err.Error()
    } else {
        checks["database"] = "ok"
    }

    // Check cache
    if err := cache.Ping(); err != nil {
        checks["cache"] = "error: " + err.Error()
    } else {
        checks["cache"] = "ok"
    }

    // Determine overall status
    allOK := true
    for _, status := range checks {
        if status != "ok" {
            allOK = false
            break
        }
    }

    w.Header().Set("Content-Type", "application/json")
    if allOK {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte(`{"status":"ready"}`))
    } else {
        w.WriteHeader(http.StatusServiceUnavailable)
        // DEEP DIVE: Returning 503 tells load balancers to stop
        // sending traffic to this instance until it recovers.
        resp, _ := json.Marshal(map[string]interface{}{
            "status": "not_ready",
            "checks": checks,
        })
        w.Write(resp)
    }
}
```

---

## 6. Putting It Together — Full Server

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
)

type StatusResponse struct {
    Status    string            `json:"status"`
    Checks    map[string]string `json:"checks,omitempty"`
    Timestamp string            `json:"timestamp"`
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
    resp := StatusResponse{
        Status:    "alive",
        Timestamp: time.Now().Format(time.RFC3339),
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}

func readinessHandler(w http.ResponseWriter, r *http.Request) {
    checks := map[string]string{
        "database": "ok",
        "cache":    "ok",
    }

    resp := StatusResponse{
        Status:    "ready",
        Checks:    checks,
        Timestamp: time.Now().Format(time.RFC3339),
    }
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}

func loggingMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        start := time.Now()
        next.ServeHTTP(w, r)
        fmt.Printf("[%s] %s %s (%v)\n",
            time.Now().Format("15:04:05"),
            r.Method, r.URL.Path,
            time.Since(start),
        )
    })
}

func recoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if err := recover(); err != nil {
                fmt.Printf("PANIC: %v\n", err)
                http.Error(w, "Internal Server Error", http.StatusInternalServerError)
            }
        }()
        next.ServeHTTP(w, r)
    })
}

func runServer(addr string) error {
    mux := http.NewServeMux()
    mux.HandleFunc("/healthz", healthHandler)
    mux.HandleFunc("/readyz", readinessHandler)

    var handler http.Handler = mux
    handler = loggingMiddleware(handler)
    handler = recoveryMiddleware(handler)

    server := &http.Server{
        Addr:         addr,
        Handler:      handler,
        ReadTimeout:  10 * time.Second,
        WriteTimeout: 10 * time.Second,
        IdleTimeout:  60 * time.Second,
    }

    ctx, stop := signal.NotifyContext(context.Background(),
        os.Interrupt, syscall.SIGTERM,
    )
    defer stop()

    errChan := make(chan error, 1)
    go func() {
        fmt.Printf("Server starting on %s\n", addr)
        if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            errChan <- err
        }
        close(errChan)
    }()

    select {
    case <-ctx.Done():
        fmt.Println("\nShutting down...")
        shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
        defer cancel()
        return server.Shutdown(shutdownCtx)
    case err := <-errChan:
        return err
    }
}

func main() {
    addr := ":8080"
    if err := runServer(addr); err != nil {
        fmt.Fprintf(os.Stderr, "Server error: %v\n", err)
        os.Exit(1)
    }
}
```

---

## Key Takeaways

1. **Cobra**: CLI framework with subcommands, flags, and help. Use `cobra.Command` for each command.
2. **Handlers**: `func(http.ResponseWriter, *http.Request)` — the fundamental unit of HTTP.
3. **ServeMux**: Basic routing. Exact match (`/healthz`), prefix match (`/api/`), catch-all (`/`).
4. **Middleware**: `func(http.Handler) http.Handler` — wraps handlers for logging, recovery, auth.
5. **Graceful shutdown**: `signal.NotifyContext` + `server.Shutdown` — clean exit on SIGTERM/SIGINT.
6. **Health checks**: `/healthz` (liveness) and `/readyz` (readiness) — essential for production.

---

**Next**: [Module 2 Exercise](02-go-cli-http-exercise.md) — Build a health-check CLI + API.
