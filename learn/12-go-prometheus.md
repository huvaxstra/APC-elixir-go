# Module 12: Go Prometheus Exporters (Week 12)

## What You'll Learn This Module

By the end of this module, you'll understand how to instrument Go services with Prometheus metrics:

1. **prometheus/client_golang** — the CNCF standard for Go metrics
2. **Counter, Gauge, Histogram** — the three metric types and when to use each
3. **Labels** — dimensional metrics for filtering and aggregation
4. **RED metrics** — Rate, Errors, Duration — the gold standard for service monitoring
5. **Histogram buckets and quantiles** — understanding latency distributions
6. **HTTP middleware** — automatically instrumenting HTTP handlers

This is how every production Go service is monitored. The Prometheus operator, the Kubernetes metrics server, and every CNCF project use client_golang. If you write Go services, this is essential knowledge.

---

## Why Prometheus?

Prometheus is the standard for cloud-native monitoring. It's a CNCF graduated project (the highest maturity level). Every Kubernetes cluster uses it. Every major cloud provider supports it.

Think of Prometheus as a financial auditor for your service. It periodically checks your service's "books" (metrics endpoint) and records what it finds. When something goes wrong (high error rate, slow latency), you can look at the historical data and find the root cause.

```
Your Service → /metrics endpoint → Prometheus → Grafana Dashboard
     ↑                                          ↓
     └──────── instrumented with ───────────────┘
              client_golang library
```

---

## The Three Metric Types

### Counter — Monotonically Increasing Value

A Counter only goes up. It tracks things like total requests, total errors, total bytes processed. You never decrease a Counter — you create a new one if you need to reset.

Think of a car's odometer. It only goes forward. You can't roll it back. When you sell the car, you don't reset the odometer — you start a new one.

```go
// internal/metrics/counters.go
//
// Counter metrics track cumulative totals.
// They only increase — never decrease.
//
// Use counters for:
// - Total HTTP requests
// - Total errors
// - Total bytes sent/received
// - Total items processed
//
// COMMON MISTAKE: Using a Gauge for cumulative totals.
// A Gauge can go up AND down. A Counter only goes up.
// If you use a Gauge for total requests, you might accidentally
// decrease it, which corrupts your metrics.
//
// DEEP DIVE: Why only go up?
// Counters are designed for rate calculations.
// To get requests per second, Prometheus calculates:
//   rate(total_requests[5m])
// This works because the counter never decreases.
// If the counter could decrease, the rate calculation would
// give negative values, which are meaningless.

package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// Total HTTP requests received
	// This counter increments every time a request arrives.
	// Labels: method (GET, POST, etc.), path (/api/agents), status (200, 404, etc.)
	//
	// DEEP DIVE: promauto.With() registers the metric automatically.
	// Without it, you'd need to call prometheus.Register() manually.
	// promauto is convenient but hides registration errors.
	// For production, consider manual registration for better error handling.
	HTTPRequestTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests",
		},
		[]string{"method", "path", "status"},
	)

	// Total HTTP errors (status >= 500)
	// This counter increments only for server errors.
	// Labels: method, path, error_type
	//
	// COMMON MISTAKE: Not labeling errors by type.
	// Without error_type, you can't distinguish between
	// "database connection failed" and "invalid input."
	// Always label errors by their root cause.
	HTTPErrorsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_errors_total",
			Help: "Total number of HTTP errors (status >= 500)",
		},
		[]string{"method", "path", "error_type"},
	)

	// Total agent invocations
	// This counter increments every time an agent is invoked.
	// Labels: agent_name, model
	AgentInvocationsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "agent_invocations_total",
			Help: "Total number of agent invocations",
		},
		[]string{"agent_name", "model"},
	)

	// Total tokens consumed by agents
	// This counter increments by the number of tokens used.
	// Labels: agent_name, model, token_type (input, output)
	//
	// DEEP DIVE: Why track tokens?
	// AI model costs are proportional to token usage.
	// Tracking tokens lets you:
	// 1. Monitor costs in real-time
	// 2. Detect anomalies (sudden spike in token usage)
	// 3. Optimize prompts (reduce token consumption)
	AgentTokensTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "agent_tokens_total",
			Help: "Total number of tokens consumed by agents",
		},
		[]string{"agent_name", "model", "token_type"},
	)
)
```

### Gauge — Value That Can Go Up or Down

A Gauge is a value that can increase or decrease. It tracks things like current temperature, queue length, memory usage, number of active connections.

Think of a thermostat. The temperature goes up when the heater is on and down when it's off. It can be any value within a range.

```go
// internal/metrics/gauges.go
//
// Gauge metrics track values that can go up AND down.
//
// Use gauges for:
// - Current number of active connections
// - Current queue length
// - Memory usage
// - CPU usage
// - Number of goroutines
// - Current temperature
//
// COMMON MISTAKE: Using a Gauge for rates.
// A Gauge shows the current value, not the rate of change.
// To get the rate of a Gauge, you need to calculate:
//   rate(gauge_value[5m])
// But this is usually wrong — gauges represent snapshots,
// not cumulative totals.
//
// DEEP DIVE: Gauge vs Counter
// Counter: "How many requests have I processed?" (always increasing)
// Gauge: "How many requests am I processing right now?" (fluctuates)
//
// If you're unsure, ask: "Can this value decrease naturally?"
// If yes → Gauge. If no → Counter.

package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// Current number of active agent sessions
	// This gauge increases when a session starts and decreases when it ends.
	// Labels: agent_name
	//
	// DEEP DIVE: Why track active sessions?
	// Because active sessions consume memory and CPU.
	// If active sessions spike, you might need to scale up.
	// If active sessions drop to zero, something might be wrong.
	ActiveSessions = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "agent_active_sessions",
			Help: "Current number of active agent sessions",
		},
		[]string{"agent_name"},
	)

	// Current queue length for agent tasks
	// This gauge shows how many tasks are waiting to be processed.
	// If the queue grows, agents are falling behind.
	// Labels: agent_name, queue_name
	QueueLength = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "agent_queue_length",
			Help: "Current number of tasks in the agent queue",
		},
		[]string{"agent_name", "queue_name"},
	)

	// Memory usage in bytes
	// This gauge shows current memory consumption.
	// Labels: agent_name
	MemoryUsage = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "agent_memory_usage_bytes",
			Help: "Current memory usage in bytes",
		},
		[]string{"agent_name"},
	)

	// Number of goroutines
	// This gauge shows the current goroutine count.
	// A growing goroutine count may indicate a leak.
	//
	// COMMON MISTAKE: Not monitoring goroutine count.
	// Goroutine leaks are common in Go services.
	// A goroutine that blocks forever consumes memory and never releases it.
	// Monitoring goroutine count helps detect leaks early.
	GoroutineCount = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "go_goroutines",
			Help: "Current number of goroutines",
		},
	)

	// Model inference latency in milliseconds
	// This gauge shows the current average latency.
	// Labels: model
	//
	// DEEP DIVE: Why a Gauge for latency instead of Histogram?
	// This is a simplified view. In production, use a Histogram
	// for latency (see next section). This Gauge is useful for
	// quick debugging — "what's the latency RIGHT NOW?"
	CurrentLatency = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "agent_current_latency_ms",
			Help: "Current average inference latency in milliseconds",
		},
		[]string{"model"},
	)
)
```

### Histogram — Distribution of Values

A Histogram tracks the distribution of values. It counts how many values fall into predefined buckets. This lets you calculate percentiles (p50, p95, p99) and averages.

Think of a histogram like a test score distribution. You don't just want the average score — you want to know how many students scored 90-100, 80-89, 70-79, etc. This tells you if most students are doing well or if there's a wide spread.

```go
// internal/metrics/histograms.go
//
// Histogram metrics track the distribution of values.
// They count how many observations fall into predefined buckets.
//
// Use histograms for:
// - Request latency (how long requests take)
// - Response size (how big responses are)
// - Queue wait time (how long items wait in queue)
// - Model inference time (how long AI models take to respond)
//
// DEEP DIVE: How histograms work
// A histogram has buckets. Each bucket has an upper bound.
// When you observe a value, the histogram increments all buckets
// where the upper bound is >= the observed value.
//
// Example with buckets [0.1, 0.5, 1.0, 5.0]:
// - Observation 0.05 → increments bucket 0.1
// - Observation 0.3  → increments buckets 0.1, 0.5
// - Observation 0.8  → increments buckets 0.1, 0.5, 1.0
// - Observation 3.0  → increments buckets 0.1, 0.5, 1.0, 5.0
//
// From these buckets, Prometheus can calculate:
// - p50 (median): the value where 50% of observations are below
// - p95: the value where 95% of observations are below
// - p99: the value where 99% of observations are below
// - average: sum of all observations / count
//
// COMMON MISTAKE: Choosing wrong bucket boundaries.
// If your buckets don't match your data distribution, you get
// inaccurate percentiles. For HTTP latency:
// - Most requests: 10-100ms
// - Slow requests: 100-1000ms
// - Very slow requests: 1000ms+
// Buckets should be: [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]

package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	// HTTP request duration in seconds
	// Buckets: 10ms, 50ms, 100ms, 500ms, 1s, 5s, 10s
	//
	// DEEP DIVE: Why these specific buckets?
	// - 0.01 (10ms): very fast requests (cache hits, simple lookups)
	// - 0.05 (50ms): fast requests (simple API calls)
	// - 0.1 (100ms): normal requests (database queries)
	// - 0.5 (500ms): slow requests (complex queries, external APIs)
	// - 1.0 (1s): very slow requests (timeout threshold)
	// - 5.0 (5s): extremely slow requests (possible bugs)
	// - 10.0 (10s): timeout threshold
	//
	// These buckets cover the typical range of HTTP request durations.
	// If your service has different latency characteristics, adjust accordingly.
	HTTPRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "Duration of HTTP requests in seconds",
			Buckets: []float64{0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0},
		},
		[]string{"method", "path"},
	)

	// HTTP response size in bytes
	// Buckets: 100B, 1KB, 10KB, 100KB, 1MB, 10MB
	HTTPResponseSize = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_response_size_bytes",
			Help:    "Size of HTTP responses in bytes",
			Buckets: []float64{100, 1024, 10240, 102400, 1048576, 10485760},
		},
		[]string{"method", "path"},
	)

	// Agent inference duration in seconds
	// Buckets: 100ms, 500ms, 1s, 2s, 5s, 10s, 30s, 60s
	//
	// DEEP DIVE: Why wider buckets for AI inference?
	// AI model inference is much slower than HTTP requests.
	// A simple prompt might take 100ms.
	// A complex prompt with retrieval might take 5-30s.
	// A very complex prompt might take 60s+.
	// The buckets reflect this wider range.
	AgentInferenceDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "agent_inference_duration_seconds",
			Help:    "Duration of agent inference in seconds",
			Buckets: []float64{0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0},
		},
		[]string{"agent_name", "model"},
	)

	// Agent token count per request
	// Buckets: 10, 50, 100, 500, 1000, 5000, 10000
	//
	// DEEP DIVE: Why track token count as a histogram?
	// Because token count varies widely:
	// - Simple query: 10-50 tokens
	// - Complex query: 100-500 tokens
	// - Long context: 1000-10000 tokens
	// A histogram lets you see the distribution and calculate
	// percentiles (p50, p95, p99 token usage).
	AgentTokenCount = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "agent_token_count",
			Help:    "Number of tokens per agent request",
			Buckets: []float64{10, 50, 100, 500, 1000, 5000, 10000},
		},
		[]string{"agent_name", "model", "token_type"},
	)

	// Database query duration in seconds
	// Buckets: 1ms, 5ms, 10ms, 50ms, 100ms, 500ms, 1s
	DBQueryDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "db_query_duration_seconds",
			Help:    "Duration of database queries in seconds",
			Buckets: []float64{0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0},
		},
		[]string{"operation", "table"},
	)
)
```

---

## RED Metrics — The Gold Standard

RED stands for **Rate**, **Errors**, **Duration**. These three metrics give you complete visibility into your service's health.

- **Rate**: How many requests per second? (Counter → rate)
- **Errors**: How many errors per second? (Counter → rate of errors)
- **Duration**: How long do requests take? (Histogram → percentiles)

Think of RED like a doctor's vital signs:
- **Rate** = heart rate (how fast is the service working?)
- **Errors** = fever (something is wrong)
- **Duration** = blood pressure (is the service stressed?)

```go
// internal/metrics/red.go
//
// RED metrics: Rate, Errors, Duration.
// These three metrics give you complete service visibility.
//
// DEEP DIVE: Why RED instead of just "total requests"?
// Because knowing total requests is not enough.
// You need to know:
// 1. How fast is the service processing? (Rate)
// 2. How often does it fail? (Errors)
// 3. How long does each request take? (Duration)
//
// Together, these tell you:
// - Is the service healthy? (low error rate, normal latency)
// - Is the service overloaded? (high rate, increasing latency)
// - Is the service degraded? (high error rate, or high latency)
//
// COMMON MISTAKE: Only monitoring Rate.
// If you only track requests per second, you miss:
// - Errors (requests succeed but return 500)
// - Latency (requests succeed but take 10 seconds)
// Always track all three RED metrics.

package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
)

// REDCollector provides RED metrics for a service
//
// DEEP DIVE: Why wrap metrics in a struct?
// Because different services have different labels.
// An HTTP service needs method, path, status.
// A gRPC service needs method, code.
// A database needs operation, table.
// The struct pattern lets you customize labels per service.
type REDCollector struct {
	// Rate: requests per second
	requestsTotal *prometheus.CounterVec

	// Errors: error count
	errorsTotal *prometheus.CounterVec

	// Duration: request latency
	requestDuration *prometheus.HistogramVec
}

// NewHTTPRED creates RED metrics for an HTTP service
// Labels: method, path, status
func NewHTTPRED(namespace string) *REDCollector {
	return &REDCollector{
		requestsTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: namespace + "_requests_total",
				Help: "Total number of requests",
			},
			[]string{"method", "path", "status"},
		),
		errorsTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: namespace + "_errors_total",
				Help: "Total number of errors",
			},
			[]string{"method", "path", "error_type"},
		),
		requestDuration: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:    namespace + "_request_duration_seconds",
				Help:    "Request duration in seconds",
				Buckets: []float64{0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0},
			},
			[]string{"method", "path"},
		),
	}
}

// NewAgentRED creates RED metrics for an agent service
// Labels: agent_name, model
func NewAgentRED(namespace string) *REDCollector {
	return &REDCollector{
		requestsTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: namespace + "_invocations_total",
				Help: "Total number of agent invocations",
			},
			[]string{"agent_name", "model"},
		),
		errorsTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: namespace + "_errors_total",
				Help: "Total number of agent errors",
			},
			[]string{"agent_name", "model", "error_type"},
		),
		requestDuration: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:    namespace + "_inference_duration_seconds",
				Help:    "Agent inference duration in seconds",
				Buckets: []float64{0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0},
			},
			[]string{"agent_name", "model"},
		),
	}
}

// RecordRequest records a successful request
// Parameters:
// - labels: map of label names to values
// - duration: how long the request took
//
// COMMON MISTAKE: Forgetting to record duration.
// If you only increment the counter, you can't calculate latency.
// Always record both count and duration.
func (r *REDCollector) RecordRequest(labels prometheus.Labels, duration float64) {
	r.requestsTotal.With(labels).Inc()
	r.requestDuration.With(labels).Observe(duration)
}

// RecordError records a failed request
// Parameters:
// - labels: map of label names to values (include error_type)
// - duration: how long the request took before failing
//
// DEEP DIVE: Why record duration for errors too?
// Because error duration tells you if errors are fast (immediate rejection)
// or slow (timeout after 30 seconds). Slow errors are worse because
// they consume resources while failing.
func (r *REDCollector) RecordError(labels prometheus.Labels, duration float64) {
	r.errorsTotal.With(labels).Inc()
	r.requestDuration.With(labels).Observe(duration)
}

// Describe sends the metric descriptions to the channel
// This is required by the prometheus.Collector interface
func (r *REDCollector) Describe(ch chan<- *prometheus.Desc) {
	r.requestsTotal.Describe(ch)
	r.errorsTotal.Describe(ch)
	r.requestDuration.Describe(ch)
}

// Collect gathers the metric values and sends them to the channel
// This is required by the prometheus.Collector interface
func (r *REDCollector) Collect(ch chan<- prometheus.Metric) {
	r.requestsTotal.Collect(ch)
	r.errorsTotal.Collect(ch)
	r.requestDuration.Collect(ch)
}
```

---

## HTTP Middleware — Automatic Instrumentation

Instead of manually instrumenting every handler, use middleware to automatically track RED metrics for all HTTP requests.

```go
// internal/metrics/middleware.go
//
// HTTP middleware that automatically instruments requests with RED metrics.
// Wrap your handlers with this middleware and all requests are tracked.
//
// DEEP DIVE: Why use middleware instead of manual instrumentation?
// 1. Consistency — every request is tracked the same way
// 2. Completeness — you can't forget to instrument a handler
// 3. Separation of concerns — business logic doesn't know about metrics
// 4. Maintainability — metrics logic is in one place
//
// COMMON MISTAKE: Not wrapping all handlers.
// If you forget to wrap a handler, its metrics are missing.
// This creates blind spots in your monitoring.
// Use a router-level middleware to wrap ALL handlers automatically.

package metrics

import (
	"net/http"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
)

// responseWriter wraps http.ResponseWriter to capture the status code
//
// DEEP DIVE: Why wrap ResponseWriter?
// Because http.ResponseWriter doesn't expose the status code after writing.
// The handler calls WriteHeader(code), but there's no way to read it back.
// By wrapping it, we capture the status code when WriteHeader is called.
//
// COMMON MISTAKE: Not implementing http.Flusher.
// Some middleware (like gzip) calls Flush() on the ResponseWriter.
// If your wrapper doesn't implement Flusher, it panics.
// Always implement Flusher and Hijacker if your wrapper wraps ResponseWriter.
type responseWriter struct {
	http.ResponseWriter
	statusCode int
	written    bool
}

// NewResponseWriter creates a wrapped ResponseWriter
// Default status code is 200 (OK) — in case WriteHeader is never called.
func NewResponseWriter(w http.ResponseWriter) *responseWriter {
	return &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}
}

// WriteHeader captures the status code
// This is called before Write — it sets the HTTP status code.
func (rw *responseWriter) WriteHeader(code int) {
	if !rw.written {
		rw.statusCode = code
		rw.written = true
	}
	rw.ResponseWriter.WriteHeader(code)
}

// Write captures that data was written
// This is called after WriteHeader — it sends the response body.
func (rw *responseWriter) Write(b []byte) (int, error) {
	if !rw.written {
		rw.written = true
	}
	return rw.ResponseWriter.Write(b)
}

// Flush implements http.Flusher
// This is needed for streaming responses and gzip middleware.
func (rw *responseWriter) Flush() {
	if f, ok := rw.ResponseWriter.(http.Flusher); ok {
		f.Flush()
	}
}

// PrometheusMiddleware creates an HTTP middleware that tracks RED metrics
//
// Usage:
//
//	mux := http.NewServeMux()
//	mux.Handle("/api/agents", myHandler)
//
//	// Wrap all handlers with the middleware
//	http.Handle("/", metrics.PrometheusMiddleware(mux))
//
// DEEP DIVE: How the middleware works
// 1. Request arrives at the middleware
// 2. Middleware wraps the ResponseWriter to capture status code
// 3. Middleware records the start time
// 4. Middleware calls the next handler
// 5. When the handler writes the response, the wrapped ResponseWriter
//    captures the status code
// 6. Middleware calculates the duration
// 7. Middleware records the RED metrics
//
// This is transparent to the handler — it doesn't know it's being monitored.
func PrometheusMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Record the start time
		start := time.Now()

		// Wrap the ResponseWriter to capture status code
		rw := NewResponseWriter(w)

		// Call the next handler
		next.ServeHTTP(rw, r)

		// Calculate duration
		duration := time.Since(start).Seconds()

		// Extract labels
		// COMMON MISTAKE: Using the full URL path as a label.
		// If you have /api/agents/123 and /api/agents/456,
		// these are two different label values, creating two time series.
		// With millions of agents, you'd have millions of time series.
		// This is a cardinality explosion — it kills Prometheus performance.
		// Always use route patterns (/api/agents/:id) not actual paths.
		status := strconv.Itoa(rw.statusCode)
		path := r.URL.Path

		// Determine if this is an error
		// DEEP DIVE: What constitutes an error?
		// - 4xx: client errors (not the server's fault)
		// - 5xx: server errors (the server's fault)
		// We track both, but separately. Server errors are more critical.
		if rw.statusCode >= 500 {
			// Server error — record in both requests and errors
			HTTPRequestTotal.With(prometheus.Labels{
				"method": r.Method,
				"path":   path,
				"status": status,
			}).Inc()

			HTTPErrorsTotal.With(prometheus.Labels{
				"method":     r.Method,
				"path":       path,
				"error_type": "server_error",
			}).Inc()

			HTTPRequestDuration.With(prometheus.Labels{
				"method": r.Method,
				"path":   path,
			}).Observe(duration)
		} else if rw.statusCode >= 400 {
			// Client error — record in requests only
			HTTPRequestTotal.With(prometheus.Labels{
				"method": r.Method,
				"path":   path,
				"status": status,
			}).Inc()

			HTTPRequestDuration.With(prometheus.Labels{
				"method": r.Method,
				"path":   path,
			}).Observe(duration)
		} else {
			// Success — record in requests only
			HTTPRequestTotal.With(prometheus.Labels{
				"method": r.Method,
				"path":   path,
				"status": status,
			}).Inc()

			HTTPRequestDuration.With(prometheus.Labels{
				"method": r.Method,
				"path":   path,
			}).Observe(duration)
		}
	})
}
```

---

## Exposing the /metrics Endpoint

Prometheus scrapes your service's `/metrics` endpoint to collect metrics. You need to expose this endpoint using `promhttp.Handler()`.

```go
// internal/metrics/server.go
//
// Sets up the /metrics endpoint for Prometheus scraping.
//
// DEEP DIVE: How Prometheus scraping works
// 1. Prometheus server is configured with your service's URL
// 2. Every 15-30 seconds (configurable), Prometheus makes an HTTP GET
//    to your /metrics endpoint
// 3. Your service responds with all current metrics in text format
// 4. Prometheus parses the response and stores the values
// 5. Prometheus can then query the metrics using PromQL
//
// The metrics endpoint returns a plain text format:
//   # HELP http_requests_total Total number of HTTP requests
//   # TYPE http_requests_total counter
//   http_requests_total{method="GET",path="/api/agents",status="200"} 1234
//   http_requests_total{method="POST",path="/api/agents",status="201"} 567
//
// COMMON MISTAKE: Not registering custom metrics.
// If you create a metric but don't register it, it won't appear
// in the /metrics response. Use prometheus.MustRegister() or
// promauto to ensure registration.

package metrics

import (
	"net/http"

	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// MetricsServer creates an HTTP server for the /metrics endpoint
//
// Usage:
//
//	// Start the metrics server on port 9090
//	go metrics.MetricsServer(":9090")
//
// DEEP DIVE: Why a separate server?
// Because the metrics endpoint should be on a different port than
// your application. Reasons:
// 1. Security — don't expose internal metrics to external traffic
// 2. Performance — metrics scraping shouldn't affect request latency
// 3. Isolation — if your app crashes, the metrics endpoint still works
//    (if it's in the same process, it crashes too)
//
// COMMON MISTAKE: Using the same port for metrics and application.
// If your application is under load, metrics scraping adds overhead.
// If the application crashes, metrics are unavailable.
// Always use a separate port for metrics.
func MetricsServer(addr string) error {
	mux := http.NewServeMux()

	// promhttp.Handler() returns an HTTP handler that serves all
	// registered Prometheus metrics in the default registry.
	//
	// DEEP DIVE: What's in the default registry?
	// All metrics created with promauto.New* are automatically
	// registered in the default registry. promhttp.Handler()
	// serves everything in that registry.
	//
	// If you need custom registries (for multi-tenant scenarios),
	// use promhttp.HandlerFor(registry, promhttp.HandlerOpts{}).
	mux.Handle("/metrics", promhttp.Handler())

	// Add a health check endpoint
	// Prometheus sometimes needs to know if the metrics endpoint is alive
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	// Start the server
	// DEEP DIVE: Why use http.ListenAndServe?
	// Because it handles:
	// - Graceful shutdown on SIGTERM
	// - Connection draining
	// - TLS termination (if configured)
	//
	// COMMON MISTAKE: Not handling server errors.
	// ListenAndServe returns an error if the server can't start.
	// This happens if:
	// - The port is already in use
	// - The address is invalid
	// - Permission denied (ports < 1024 require root)
	return http.ListenAndServe(addr, mux)
}
```

---

## Putting It All Together

Here's how all the pieces fit in a complete Go service:

```go
// cmd/server/main.go
//
// The entry point for an instrumented Go service.
// This shows how to wire up RED metrics, middleware, and the metrics server.

package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"my-service/internal/metrics"

	"github.com/prometheus/client_golang/prometheus"
)

func main() {
	// Create RED metrics for the HTTP service
	redMetrics := metrics.NewHTTPRED("my_service")

	// Create the HTTP mux
	mux := http.NewServeMux()

	// Register handlers
	mux.HandleFunc("/api/agents", func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()

		// Simulate some work
		time.Sleep(10 * time.Millisecond)

		// Record successful request
		redMetrics.RecordRequest(prometheus.Labels{
			"method": r.Method,
			"path":   "/api/agents",
			"status": "200",
		}, time.Since(start).Seconds())

		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"agents": []}`)
	})

	// Wrap all handlers with the metrics middleware
	// This automatically tracks RED metrics for all requests
	handler := metrics.PrometheusMiddleware(mux)

	// Start the metrics server on a separate port
	go func() {
		log.Println("Metrics server starting on :9090")
		if err := metrics.MetricsServer(":9090"); err != nil {
			log.Fatalf("Metrics server failed: %v", err)
		}
	}()

	// Start the main server
	log.Println("Application server starting on :8080")
	if err := http.ListenAndServe(":8080", handler); err != nil {
		log.Fatalf("Application server failed: %v", err)
	}
}
```

---

## Key Takeaways

1. **Counter** only goes up. Use for cumulative totals (total requests, total errors). Calculate rates with `rate()`.

2. **Gauge** goes up and down. Use for current values (active connections, queue length, memory usage).

3. **Histogram** tracks distributions. Use for latency and size. Choose bucket boundaries carefully.

4. **RED metrics** (Rate, Errors, Duration) give you complete service visibility. Always track all three.

5. **Labels** add dimensions to metrics. But avoid high-cardinality labels (user IDs, request IDs) — they create too many time series.

6. **Middleware** automates instrumentation. Wrap all handlers to ensure consistent metrics.

7. **Separate port** for metrics. Don't expose internal metrics on your public port.

---

## What's Next

In Module 13, you'll connect Go and Elixir using gRPC. The protobuf contracts define the interface, and gRPC handles the serialization and transport — the bridge between your infrastructure edge and agent brain.
