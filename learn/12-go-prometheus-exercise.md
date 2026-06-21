# Module 12 Exercise: Go Prometheus Exporters

## What You'll Practice

By completing this exercise, you'll build an **instrumented Go service** with:

1. Counter, Gauge, and Histogram metrics
2. RED metrics (Rate, Errors, Duration)
3. Labels for dimensional metrics
4. HTTP middleware for automatic instrumentation
5. A `/metrics` endpoint for Prometheus scraping

This is a production-grade metrics setup — the same pattern used by every CNCF project.

---

## Part 1: Counter Metrics

Implement counters for tracking cumulative totals.

### Starter Code

```go
// internal/metrics/counters_test.go
//
// Test your counter implementations.
// Run with: go test ./internal/metrics/ -v

package metrics

import (
	"testing"

	"github.com/prometheus/client_golang/prometheus"
	dto "github.com/prometheus/client_model/go"
)

// TODO: Create a CounterVec for tracking HTTP requests
// Name: "test_http_requests_total"
// Help: "Total number of HTTP requests"
// Labels: method, status

// TODO: Create a CounterVec for tracking errors
// Name: "test_errors_total"
// Help: "Total number of errors"
// Labels: error_type

// TestCounterIncrement verifies a counter increments correctly
func TestCounterIncrement(t *testing.T) {
	// TODO: Create a new counter
	// Hint: prometheus.NewCounterVec(...)

	// TODO: Increment the counter with labels
	// Hint: counter.With(prometheus.Labels{"method": "GET", "status": "200"}).Inc()

	// TODO: Verify the counter value is 1
	// Hint: Use prometheus.ToFloat64(counter.With(...))
}

// TestCounterMultipleIncrements verifies multiple increments
func TestCounterMultipleIncrements(t *testing.T) {
	// TODO: Increment the counter 5 times with the same labels
	// TODO: Verify the counter value is 5
}

// TestCounterDifferentLabels verifies different label combinations
func TestCounterDifferentLabels(t *testing.T) {
	// TODO: Increment with method=GET, status=200
	// TODO: Increment with method=POST, status=201
	// TODO: Verify each combination has its own counter value
	//
	// COMMON MISTAKE: Assuming labels share counters.
	// Each unique label combination is a separate time series.
	// {method="GET", status="200"} and {method="POST", status="201"}
	// are two different counters.
}
```

### Hints

1. Use `prometheus.NewCounterVec(opts, labelNames)` to create a counter
2. Use `counter.With(prometheus.Labels{...}).Inc()` to increment
3. Use `prometheus.ToFloat64(counter.With(...))` to read the value
4. Each unique label combination is a separate time series

---

## Part 2: Gauge Metrics

Implement gauges for tracking current values.

### Starter Code

```go
// internal/metrics/gauges_test.go

package metrics

import (
	"testing"

	"github.com/prometheus/client_golang/prometheus"
)

// TODO: Create a GaugeVec for tracking active sessions
// Name: "test_active_sessions"
// Help: "Current number of active sessions"
// Labels: service_name

// TestGaugeSet verifies a gauge can be set to any value
func TestGaugeSet(t *testing.T) {
	// TODO: Create a new gauge
	// TODO: Set the gauge to 10
	// TODO: Verify the value is 10
}

// TestGaugeIncrementDecrement verifies gauge can go up and down
func TestGaugeIncrementDecrement(t *testing.T) {
	// TODO: Set gauge to 5
	// TODO: Increment by 3 (should be 8)
	// TODO: Decrement by 2 (should be 6)
	// TODO: Verify the value is 6
	//
	// DEEP DIVE: Gauge vs Counter
	// Gauge: can go up AND down (active sessions, queue length)
	// Counter: only goes up (total requests, total errors)
	//
	// COMMON MISTAKE: Using Dec() on a Counter.
	// Counters don't have a Dec() method.
	// If you need to decrease, you're using the wrong metric type.
}

// TestGaugeMultipleServices verifies separate gauges per label
func TestGaugeMultipleServices(t *testing.T) {
	// TODO: Set gauge for service_name="api" to 10
	// TODO: Set gauge for service_name="worker" to 5
	// TODO: Verify each service has its own value
}
```

### Hints

1. Use `prometheus.NewGaugeVec(opts, labelNames)` to create a gauge
2. Use `gauge.With(...).Set(value)` to set the value
3. Use `gauge.With(...).Inc()` and `gauge.With(...).Dec()` to increment/decrement
4. Use `prometheus.ToFloat64(gauge.With(...))` to read the value

---

## Part 3: Histogram Metrics

Implement histograms for tracking distributions.

### Starter Code

```go
// internal/metrics/histograms_test.go

package metrics

import (
	"testing"

	"github.com/prometheus/client_golang/prometheus"
)

// TODO: Create a HistogramVec for tracking request duration
// Name: "test_request_duration_seconds"
// Help: "Request duration in seconds"
// Buckets: 0.01, 0.05, 0.1, 0.5, 1.0
// Labels: endpoint

// TestHistogramObserve verifies observations are recorded
func TestHistogramObserve(t *testing.T) {
	// TODO: Create a new histogram
	// TODO: Observe a value of 0.05
	// TODO: Verify the count is 1
	// Hint: Use prometheus.ToFloat64(histogram.With(...)) for the sum
	// Hint: Use histogram.With(...).(prometheus.Metric) for the count
}

// TestHistogramMultipleObservations verifies multiple observations
func TestHistogramMultipleObservations(t *testing.T) {
	// TODO: Observe 0.01, 0.05, 0.1, 0.5, 1.0
	// TODO: Verify the count is 5
	// TODO: Verify the sum is 1.66
}

// TestHistogramDifferentEndpoints verifies separate histograms per label
func TestHistogramDifferentEndpoints(t *testing.T) {
	// TODO: Observe 0.1 for endpoint="/api/agents"
	// TODO: Observe 0.5 for endpoint="/api/models"
	// TODO: Verify each endpoint has its own histogram
	//
	// DEEP DIVE: How to read histogram values
	// The histogram exposes:
	// - _count: total number of observations
	// - _sum: sum of all observations
	// - _bucket{le="X"}: count of observations <= X
	//
	// To calculate average: _sum / _count
	// To calculate p50: find the bucket where _count/2 falls
	// To calculate p95: find the bucket where _count*0.95 falls
}
```

### Hints

1. Use `prometheus.NewHistogramVec(opts, labelNames)` to create a histogram
2. Use `histogram.With(...).Observe(value)` to record a value
3. Use `prometheus.ToFloat64(histogram.With(...))` to get the sum
4. Buckets are cumulative — each bucket includes all smaller values

---

## Part 4: RED Metrics Collector

Build a complete RED metrics collector.

### Starter Code

```go
// internal/metrics/red_test.go

package metrics

import (
	"testing"

	"github.com/prometheus/client_golang/prometheus"
)

// TODO: Implement NewTestRED function
// Create a REDCollector with:
// - requestsTotal: CounterVec with name "test_requests_total", labels: method, path, status
// - errorsTotal: CounterVec with name "test_errors_total", labels: method, path, error_type
// - requestDuration: HistogramVec with name "test_request_duration_seconds", buckets: 0.01, 0.1, 1.0

// TestREDSuccessfulRequest verifies successful request recording
func TestREDSuccessfulRequest(t *testing.T) {
	// TODO: Create a RED collector
	// TODO: Record a successful request (method=GET, path=/api, status=200)
	// TODO: Verify requests_total incremented
	// TODO: Verify errors_total did NOT increment
	// TODO: Verify request_duration recorded
}

// TestREDErrorRequest verifies error recording
func TestREDErrorRequest(t *testing.T) {
	// TODO: Create a RED collector
	// TODO: Record an error request (method=POST, path=/api, error_type=timeout)
	// TODO: Verify errors_total incremented
	// TODO: Verify request_duration recorded (errors have duration too!)
	//
	// COMMON MISTAKE: Not recording duration for errors.
	// Error duration tells you if errors are fast (immediate rejection)
	// or slow (timeout after 30 seconds). Always record duration.
}

// TestREDMultipleRequests verifies multiple request recording
func TestREDMultipleRequests(t *testing.T) {
	// TODO: Record 3 successful requests and 1 error
	// TODO: Verify requests_total is 4 (all requests)
	// TODO: Verify errors_total is 1 (only errors)
	//
	// DEEP DIVE: Why count all requests, not just successes?
	// Because Rate = total_requests / time.
	// If you only count successes, your Rate is wrong.
	// Rate should include all requests (successes + errors).
	// Error Rate = errors / total_requests.
}
```

### Hints

1. Create a struct with CounterVec and HistogramVec fields
2. Implement `RecordRequest` for successful requests
3. Implement `RecordError` for failed requests
4. Both methods should update the request duration histogram

---

## Part 5: HTTP Middleware

Build middleware that automatically instruments HTTP requests.

### Starter Code

```go
// internal/metrics/middleware_test.go

package metrics

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

// TestMiddlewareCapturesStatus verifies status code capture
func TestMiddlewareCapturesStatus(t *testing.T) {
	// TODO: Create a handler that returns 200
	// TODO: Wrap it with PrometheusMiddleware
	// TODO: Make a request
	// TODO: Verify the response status is 200
	//
	// Hint: Use httptest.NewRecorder() to capture the response
	// Hint: Use httptest.NewRequest() to create a request
}

// TestMiddlewareCaptures404 verifies 404 capture
func TestMiddlewareCaptures404(t *testing.T) {
	// TODO: Create a handler that returns 404
	// TODO: Wrap it with PrometheusMiddleware
	// TODO: Make a request
	// TODO: Verify the response status is 404
}

// TestMiddlewareCaptures500 verifies 500 capture
func TestMiddlewareCaptures500(t *testing.T) {
	// TODO: Create a handler that returns 500
	// TODO: Wrap it with PrometheusMiddleware
	// TODO: Make a request
	// TODO: Verify the response status is 500
	//
	// COMMON MISTAKE: Not testing error status codes.
	// Your middleware must handle 4xx and 5xx correctly.
	// If it doesn't, you won't see errors in your metrics.
}

// TestMiddlewareRecordsDuration verifies duration recording
func TestMiddlewareRecordsDuration(t *testing.T) {
	// TODO: Create a handler that sleeps for 10ms
	// TODO: Wrap it with PrometheusMiddleware
	// TODO: Make a request
	// TODO: Verify the duration was recorded (approximately 10ms)
	//
	// DEEP DIVE: How to verify duration
	// You can't check the exact duration (it depends on system load).
	// Instead, check that the duration is > 0 and < 1 second.
	// Or check the histogram sum is approximately correct.
}

// TestMiddlewareDifferentPaths verifies path-based separation
func TestMiddlewareDifferentPaths(t *testing.T) {
	// TODO: Create handlers for /api/agents and /api/models
	// TODO: Make requests to each
	// TODO: Verify each path has its own metrics
	//
	// COMMON MISTAKE: Using actual URLs as labels.
	// /api/agents/123 and /api/agents/456 are different labels.
	// This creates cardinality explosion — millions of time series.
	// Always use route patterns (/api/agents/:id) not actual paths.
}
```

### Hints

1. Use `httptest.NewRecorder()` to create a response recorder
2. Use `httptest.NewRequest("GET", "/path", nil)` to create a request
3. Call `middleware.ServeHTTP(recorder, request)` to test the middleware
4. Check `recorder.Code` for the status code

---

## Part 6: Metrics Server

Set up the `/metrics` endpoint.

### Starter Code

```go
// internal/metrics/server_test.go

package metrics

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

// TestMetricsEndpoint verifies /metrics returns data
func TestMetricsEndpoint(t *testing.T) {
	// TODO: Create a test HTTP server with the metrics handler
	// Hint: Use httptest.NewServer with promhttp.Handler()

	// TODO: Make a GET request to /metrics

	// TODO: Verify the response status is 200

	// TODO: Verify the response contains metric names
	// Hint: Check if body contains "http_requests_total" or similar

	// COMMON MISTAKE: Not registering metrics before testing.
	// If you don't register any metrics, /metrics returns empty.
	// Always register at least one metric before testing the endpoint.
}

// TestMetricsEndpointFormat verifies the response format
func TestMetricsEndpointFormat(t *testing.T) {
	// TODO: Register a test counter
	// TODO: Increment it
	// TODO: Scrape /metrics
	// TODO: Verify the response contains:
	//   - # HELP (help text)
	//   - # TYPE (metric type)
	//   - metric_name{labels} value
}

// TestHealthEndpoint verifies /health returns OK
func TestHealthEndpoint(t *testing.T) {
	// TODO: Create a test HTTP server with the health handler
	// TODO: Make a GET request to /health
	// TODO: Verify the response status is 200
	// TODO: Verify the response body is "OK"
}
```

### Hints

1. Use `httptest.NewServer(handler)` to create a test server
2. Use `http.Get(server.URL + "/metrics")` to make requests
3. Read the response body with `io.ReadAll(resp.Body)`
4. Check the body contains expected metric names

---

## Part 7: Integration — Instrumented Go Service

Wire everything into a complete instrumented service.

### Starter Code

```go
// cmd/server/main.go
//
// Build a complete instrumented Go service.
// This combines all the pieces from the previous parts.

package main

import (
	// TODO: Import necessary packages
	// - "net/http"
	// - "log"
	// - "time"
	// - "my-service/internal/metrics"
	// - "github.com/prometheus/client_golang/prometheus"
)

func main() {
	// TODO: Create RED metrics for the HTTP service
	// Use metrics.NewHTTPRED("agent_service")

	// TODO: Create the HTTP mux
	// Register these handlers:
	// - GET /api/agents → returns list of agents
	// - POST /api/agents → creates an agent
	// - GET /api/agents/:id → returns a specific agent

	// TODO: Wrap all handlers with PrometheusMiddleware

	// TODO: Start the metrics server on :9090
	// Hint: go metrics.MetricsServer(":9090")

	// TODO: Start the main server on :8080

	// COMMON MISTAKE: Starting the metrics server on the same port.
	// Metrics should be on a separate port (9090) from the application (8080).
	// This prevents external traffic from hitting the metrics endpoint
	// and prevents metrics scraping from affecting request latency.
}

// TODO: Implement the agent handler
// - Parse the request
// - Simulate some work (time.Sleep)
// - Record RED metrics
// - Return JSON response
//
// DEEP DIVE: Handler structure
// 1. Record start time
// 2. Do the work
// 3. Calculate duration
// 4. Record metrics (success or error)
// 5. Write response
//
// COMMON MISTAKE: Not recording duration on error.
// If the handler fails, you still need to record the duration.
// Otherwise, your latency metrics are biased toward successes.
```

### Hints

1. Use `metrics.NewHTTPRED("service_name")` to create RED metrics
2. Use `metrics.PrometheusMiddleware(handler)` to wrap handlers
3. Use `go metrics.MetricsServer(":9090")` for the metrics server
4. Record both success and error metrics in handlers

---

## Solutions

### Solution: Counters Test

```go
package metrics

import (
	"testing"

	"github.com/prometheus/client_golang/prometheus"
)

func TestCounterIncrement(t *testing.T) {
	counter := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "test_http_requests_total",
			Help: "Total number of HTTP requests",
		},
		[]string{"method", "status"},
	)

	counter.With(prometheus.Labels{"method": "GET", "status": "200"}).Inc()

	value := prometheus.ToFloat64(counter.With(prometheus.Labels{"method": "GET", "status": "200"}))
	if value != 1 {
		t.Errorf("Expected counter value 1, got %f", value)
	}
}

func TestCounterMultipleIncrements(t *testing.T) {
	counter := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "test_counter_multi",
			Help: "Test counter",
		},
		[]string{"key"},
	)

	for i := 0; i < 5; i++ {
		counter.With(prometheus.Labels{"key": "value"}).Inc()
	}

	value := prometheus.ToFloat64(counter.With(prometheus.Labels{"key": "value"}))
	if value != 5 {
		t.Errorf("Expected counter value 5, got %f", value)
	}
}

func TestCounterDifferentLabels(t *testing.T) {
	counter := prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "test_counter_labels",
			Help: "Test counter",
		},
		[]string{"method", "status"},
	)

	counter.With(prometheus.Labels{"method": "GET", "status": "200"}).Inc()
	counter.With(prometheus.Labels{"method": "POST", "status": "201"}).Inc()

	getValue := prometheus.ToFloat64(counter.With(prometheus.Labels{"method": "GET", "status": "200"}))
	postValue := prometheus.ToFloat64(counter.With(prometheus.Labels{"method": "POST", "status": "201"}))

	if getValue != 1 {
		t.Errorf("Expected GET counter 1, got %f", getValue)
	}
	if postValue != 1 {
		t.Errorf("Expected POST counter 1, got %f", postValue)
	}
}
```

### Solution: Gauges Test

```go
package metrics

import (
	"testing"

	"github.com/prometheus/client_golang/prometheus"
)

func TestGaugeSet(t *testing.T) {
	gauge := prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "test_active_sessions",
			Help: "Current number of active sessions",
		},
		[]string{"service_name"},
	)

	gauge.With(prometheus.Labels{"service_name": "api"}).Set(10)

	value := prometheus.ToFloat64(gauge.With(prometheus.Labels{"service_name": "api"}))
	if value != 10 {
		t.Errorf("Expected gauge value 10, got %f", value)
	}
}

func TestGaugeIncrementDecrement(t *testing.T) {
	gauge := prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "test_gauge_inc_dec",
			Help: "Test gauge",
		},
		[]string{"key"},
	)

	gauge.With(prometheus.Labels{"key": "value"}).Set(5)
	gauge.With(prometheus.Labels{"key": "value"}).Add(3)
	gauge.With(prometheus.Labels{"key": "value"}).Sub(2)

	value := prometheus.ToFloat64(gauge.With(prometheus.Labels{"key": "value"}))
	if value != 6 {
		t.Errorf("Expected gauge value 6, got %f", value)
	}
}

func TestGaugeMultipleServices(t *testing.T) {
	gauge := prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "test_gauge_services",
			Help: "Test gauge",
		},
		[]string{"service_name"},
	)

	gauge.With(prometheus.Labels{"service_name": "api"}).Set(10)
	gauge.With(prometheus.Labels{"service_name": "worker"}).Set(5)

	apiValue := prometheus.ToFloat64(gauge.With(prometheus.Labels{"service_name": "api"}))
	workerValue := prometheus.ToFloat64(gauge.With(prometheus.Labels{"service_name": "worker"}))

	if apiValue != 10 {
		t.Errorf("Expected api gauge 10, got %f", apiValue)
	}
	if workerValue != 5 {
		t.Errorf("Expected worker gauge 5, got %f", workerValue)
	}
}
```

### Solution: Histograms Test

```go
package metrics

import (
	"testing"

	"github.com/prometheus/client_golang/prometheus"
)

func TestHistogramObserve(t *testing.T) {
	histogram := prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "test_request_duration",
			Help:    "Request duration",
			Buckets: []float64{0.01, 0.05, 0.1, 0.5, 1.0},
		},
		[]string{"endpoint"},
	)

	histogram.With(prometheus.Labels{"endpoint": "/api"}).Observe(0.05)

	sum := prometheus.ToFloat64(histogram.With(prometheus.Labels{"endpoint": "/api"}))
	if sum != 0.05 {
		t.Errorf("Expected histogram sum 0.05, got %f", sum)
	}
}

func TestHistogramMultipleObservations(t *testing.T) {
	histogram := prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "test_histogram_multi",
			Help:    "Test histogram",
			Buckets: []float64{0.01, 0.05, 0.1, 0.5, 1.0},
		},
		[]string{"endpoint"},
	)

	values := []float64{0.01, 0.05, 0.1, 0.5, 1.0}
	for _, v := range values {
		histogram.With(prometheus.Labels{"endpoint": "/api"}).Observe(v)
	}

	sum := prometheus.ToFloat64(histogram.With(prometheus.Labels{"endpoint": "/api"}))
	expectedSum := 1.66
	if sum != expectedSum {
		t.Errorf("Expected histogram sum %f, got %f", expectedSum, sum)
	}
}

func TestHistogramDifferentEndpoints(t *testing.T) {
	histogram := prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "test_histogram_endpoints",
			Help:    "Test histogram",
			Buckets: []float64{0.01, 0.05, 0.1, 0.5, 1.0},
		},
		[]string{"endpoint"},
	)

	histogram.With(prometheus.Labels{"endpoint": "/api/agents"}).Observe(0.1)
	histogram.With(prometheus.Labels{"endpoint": "/api/models"}).Observe(0.5)

	agentsSum := prometheus.ToFloat64(histogram.With(prometheus.Labels{"endpoint": "/api/agents"}))
	modelsSum := prometheus.ToFloat64(histogram.With(prometheus.Labels{"endpoint": "/api/models"}))

	if agentsSum != 0.1 {
		t.Errorf("Expected agents histogram sum 0.1, got %f", agentsSum)
	}
	if modelsSum != 0.5 {
		t.Errorf("Expected models histogram sum 0.5, got %f", modelsSum)
	}
}
```

### Solution: RED Metrics Test

```go
package metrics

import (
	"testing"

	"github.com/prometheus/client_golang/prometheus"
)

type testREDCollector struct {
	requestsTotal  *prometheus.CounterVec
	errorsTotal    *prometheus.CounterVec
	requestDuration *prometheus.HistogramVec
}

func newTestRED() *testREDCollector {
	return &testREDCollector{
		requestsTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "test_requests_total",
				Help: "Total requests",
			},
			[]string{"method", "path", "status"},
		),
		errorsTotal: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "test_errors_total",
				Help: "Total errors",
			},
			[]string{"method", "path", "error_type"},
		),
		requestDuration: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:    "test_request_duration_seconds",
				Help:    "Request duration",
				Buckets: []float64{0.01, 0.1, 1.0},
			},
			[]string{"method", "path"},
		),
	}
}

func (r *testREDCollector) recordRequest(labels prometheus.Labels, duration float64) {
	r.requestsTotal.With(labels).Inc()
	r.requestDuration.With(labels).Observe(duration)
}

func (r *testREDCollector) recordError(labels prometheus.Labels, duration float64) {
	r.errorsTotal.With(labels).Inc()
	r.requestDuration.With(labels).Observe(duration)
}

func TestREDSuccessfulRequest(t *testing.T) {
	red := newTestRED()

	red.recordRequest(prometheus.Labels{
		"method": "GET",
		"path":   "/api",
		"status": "200",
	}, 0.1)

	requestsValue := prometheus.ToFloat64(red.requestsTotal.With(prometheus.Labels{
		"method": "GET", "path": "/api", "status": "200",
	}))
	if requestsValue != 1 {
		t.Errorf("Expected requests_total 1, got %f", requestsValue)
	}
}

func TestREDErrorRequest(t *testing.T) {
	red := newTestRED()

	red.recordError(prometheus.Labels{
		"method":     "POST",
		"path":       "/api",
		"error_type": "timeout",
	}, 30.0)

	errorsValue := prometheus.ToFloat64(red.errorsTotal.With(prometheus.Labels{
		"method": "POST", "path": "/api", "error_type": "timeout",
	}))
	if errorsValue != 1 {
		t.Errorf("Expected errors_total 1, got %f", errorsValue)
	}
}

func TestREDMultipleRequests(t *testing.T) {
	red := newTestRED()

	for i := 0; i < 3; i++ {
		red.recordRequest(prometheus.Labels{
			"method": "GET", "path": "/api", "status": "200",
		}, 0.1)
	}

	red.recordError(prometheus.Labels{
		"method": "POST", "path": "/api", "error_type": "timeout",
	}, 5.0)

	totalRequests := prometheus.ToFloat64(red.requestsTotal.With(prometheus.Labels{
		"method": "GET", "path": "/api", "status": "200",
	}))
	totalErrors := prometheus.ToFloat64(red.errorsTotal.With(prometheus.Labels{
		"method": "POST", "path": "/api", "error_type": "timeout",
	}))

	if totalRequests != 3 {
		t.Errorf("Expected requests_total 3, got %f", totalRequests)
	}
	if totalErrors != 1 {
		t.Errorf("Expected errors_total 1, got %f", totalErrors)
	}
}
```

### Solution: Middleware Test

```go
package metrics

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestMiddlewareCapturesStatus(t *testing.T) {
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	middleware := PrometheusMiddleware(handler)

	req := httptest.NewRequest("GET", "/api/test", nil)
	rec := httptest.NewRecorder()

	middleware.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rec.Code)
	}
}

func TestMiddlewareCaptures404(t *testing.T) {
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	})

	middleware := PrometheusMiddleware(handler)

	req := httptest.NewRequest("GET", "/nonexistent", nil)
	rec := httptest.NewRecorder()

	middleware.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", rec.Code)
	}
}

func TestMiddlewareCaptures500(t *testing.T) {
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	})

	middleware := PrometheusMiddleware(handler)

	req := httptest.NewRequest("GET", "/api/error", nil)
	rec := httptest.NewRecorder()

	middleware.ServeHTTP(rec, req)

	if rec.Code != http.StatusInternalServerError {
		t.Errorf("Expected status 500, got %d", rec.Code)
	}
}

func TestMiddlewareRecordsDuration(t *testing.T) {
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(10 * time.Millisecond)
		w.WriteHeader(http.StatusOK)
	})

	middleware := PrometheusMiddleware(handler)

	req := httptest.NewRequest("GET", "/api/slow", nil)
	rec := httptest.NewRecorder()

	start := time.Now()
	middleware.ServeHTTP(rec, req)
	duration := time.Since(start)

	if duration < 10*time.Millisecond {
		t.Errorf("Expected duration >= 10ms, got %v", duration)
	}
}
```

### Solution: Server Test

```go
package metrics

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

func TestMetricsEndpoint(t *testing.T) {
	// Register a test metric
	counter := prometheus.NewCounter(prometheus.CounterOpts{
		Name: "test_metric_for_endpoint",
		Help: "Test metric",
	})
	prometheus.MustRegister(counter)
	counter.Inc()

	// Create test server
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	server := httptest.NewServer(mux)
	defer server.Close()

	// Make request
	resp, err := http.Get(server.URL + "/metrics")
	if err != nil {
		t.Fatalf("Failed to get /metrics: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	if !strings.Contains(string(body), "test_metric_for_endpoint") {
		t.Error("Response should contain test metric name")
	}
}

func TestHealthEndpoint(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})
	server := httptest.NewServer(mux)
	defer server.Close()

	resp, err := http.Get(server.URL + "/health")
	if err != nil {
		t.Fatalf("Failed to get /health: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	body, _ := io.ReadAll(resp.Body)
	if string(body) != "OK" {
		t.Errorf("Expected body 'OK', got '%s'", string(body))
	}
}
```
