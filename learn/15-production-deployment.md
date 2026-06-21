# Module 15: Production Deployment (Week 15)

## What You'll Learn This Module

By the end of this module, you'll understand how to deploy a hybrid Elixir/Go platform to production:

1. **Docker multi-stage builds** — create minimal, secure container images
2. **Kubernetes manifests** — deployments, services, configmaps, probes
3. **Helm charts** — template-based K8s configuration with value overrides
4. **ConfigMaps and Secrets** — externalize configuration from container images
5. **Health probes** — liveness, readiness, and startup probes for K8s
6. **Terraform** — provision cloud infrastructure as code

Production deployment is where software meets reality. Your code works on your laptop. But can it survive a rolling update? Can it recover from a node failure? Can a new developer deploy it with one command?

---

## The Problem: Dev ≠ Production

In development, you run `mix phx.server` and `go run main.go`. In production, you need:

1. **Containers** — consistent runtime environment across machines
2. **Orchestration** — automatic restarts, scaling, load balancing
3. **Configuration** — secrets and config outside the container image
4. **Health checks** — K8s knows when your app is ready to receive traffic
5. **Infrastructure** — cloud accounts, networks, DNS, certificates

This module builds each layer, from Docker to Terraform.

---

## The Big Picture: Deployment Stack

```
┌─────────────────────────────────────────────────────────┐
│                    Terraform                             │
│  Provisions: VPC, subnets, EKS cluster, RDS, ElastiCache│
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                    Helm Chart                            │
│  Templates: Deployment, Service, ConfigMap, Ingress      │
│  Values: replicas, resources, image tags                 │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                  Kubernetes                              │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ Elixir Pod (x3)  │  │ Go Gateway Pod (x2)│           │
│  │ Phoenix + Oban   │  │ gRPC + Prometheus  │           │
│  └──────────────────┘  └──────────────────┘             │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │ PostgreSQL (RDS) │  │ Redis (ElastiCache)│           │
│  └──────────────────┘  └──────────────────┘             │
└─────────────────────────────────────────────────────────┘
```

---

## Pattern 1: Docker Multi-Stage Builds

### Why Multi-Stage?

A Docker image with Go compiler, Elixir build tools, and all dev dependencies is 2GB+. A production image needs only the compiled binary and runtime. Multi-stage builds let you build in one stage and copy only the output to a minimal final stage.

### Elixir Dockerfile

```dockerfile
# Dockerfile — Elixir Phoenix Application (multi-stage)
#
# Stage 1: Build — includes Elixir, Erlang, Node.js, hex, rebar
# Stage 2: Runtime — includes only Erlang runtime and compiled app
#
# WHY: Final image is ~100MB instead of ~1.5GB. Smaller images = faster pulls,
# less attack surface, faster deployments.

# ============================================================
# Stage 1: Build
# ============================================================
FROM hexpm/elixir:1.18.4-erlang-27.3.4-debian-bookworm-20240612 AS build

# Install build dependencies
# WHY: Debian slim images don't include build tools by default
RUN apt-get update -y && apt-get install -y build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory for the build
WORKDIR /app

# Install hex and rebar — Elixir's package manager and build tool
# WHY: These must be installed before mix deps.get
RUN mix local.hex --force && mix local.rebar --force

# Copy mix files first — Docker layer caching
# WHY: If mix.exs and mix.lock haven't changed, Docker reuses this layer.
# Only source code changes trigger a full rebuild. This cuts build time from
# 5 minutes to 30 seconds on small changes.
COPY mix.exs mix.lock ./

# Fetch dependencies
RUN mix deps.get --only prod

# Copy application source
COPY config config
COPY lib lib
COPY priv priv
COPY assets assets

# Compile the application
# COMMON MISTAKE: Forgetting MIX_ENV=prod — you'll get dev-mode code
ENV MIX_ENV=prod
RUN mix compile

# Build assets (if using esbuild/tailwind)
COPY assets/package.json assets/package-lock.json assets/
RUN cd assets && npm ci
RUN mix assets.deploy

# Create a release
# WHY: Mix releases bundle the app, its dependencies, and the Erlang runtime
# into a single directory. This is what we copy to the runtime stage.
RUN mix release

# ============================================================
# Stage 2: Runtime
# ============================================================
FROM debian:bookworm-slim AS runtime

# Install runtime dependencies only
# WHY: No compilers, no build tools, no git. Just the libraries the
# compiled BEAM needs at runtime.
RUN apt-get update -y && apt-get install -y libstdc++6 openssl libncurses5 locales \
    && rm -rf /var/lib/apt/lists/*

# Set the locale — BEAM requires it
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Create a non-root user
# COMMON MISTAKE: Running as root — if the app is compromised, the attacker
# has full container access. Always run as a non-root user.
RUN useradd --create-home app
WORKDIR /home/app

# Copy the release from the build stage
# WHY: We only copy the _build directory — not source code, not compilers,
# not node_modules. This is the smallest possible deployment artifact.
COPY --from=build --chown=app:app /app/_build/prod/rel/agentic_platform ./

# Switch to non-root user
USER app

# Expose the Phoenix port
EXPOSE 4000

# Health check — K8s uses this to determine if the pod is ready
# WHY: Without a health check, K8s might route traffic to a pod that's
# still starting up. The probe ensures the app is fully initialized.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:4000/healthz || exit 1

# Start the application
# WHY: Use exec form (not shell form) so BEAM gets PID 1 and handles
# signals correctly. Without exec, Docker's shell process gets PID 1
# and BEAM doesn't receive SIGTERM on shutdown.
CMD ["bin/agentic_platform", "start"]
```

### Go Dockerfile

```dockerfile
# Dockerfile — Go AgentBridge Gateway (multi-stage)
#
# Stage 1: Build — includes Go compiler
# Stage 2: Runtime — scratch or distroless image

# ============================================================
# Stage 1: Build
# ============================================================
FROM golang:1.26-bookworm AS build

WORKDIR /app

# Copy go.mod and go.sum first — Docker layer caching
# WHY: Same layer caching strategy as Elixir. Dependencies change
# less often than source code.
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY cmd/ cmd/
COPY internal/ internal/
COPY proto/ proto/

# Build the binary
# WHY: CGO_ENABLED=0 creates a static binary — no C library dependencies.
# This is critical for the next stage (scratch image).
# COMMON MISTAKE: Forgetting CGO_ENABLED=0 — the binary will fail to run
# in a scratch container because it can't find libc.
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o bridge-server ./cmd/bridge-server

# ============================================================
# Stage 2: Runtime
# ============================================================
# Scratch is an empty image — the smallest possible container
# WHY: Our Go binary is statically linked. It needs nothing else.
# No shell, no utilities, no attack surface.
FROM scratch

# Copy the binary from the build stage
COPY --from=build /app/bridge-server /bridge-server

# Copy CA certificates for TLS connections
# WHY: Without these, the binary can't make HTTPS requests to external services.
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

EXPOSE 50051 8080

# Health check endpoint
# COMMON MISTAKE: Using scratch means no curl for HEALTHCHECK.
# K8s uses a different mechanism (HTTP GET probe) — this is just Docker-level.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD ["/bridge-server", "--healthcheck"] || exit 1

ENTRYPOINT ["/bridge-server"]
```

### Building and Testing

```bash
# Build the Elixir image
docker build -t agentic-platform:latest -f Dockerfile.elixir .

# Build the Go image
docker build -t agentic-gateway:latest -f Dockerfile.go .

# Test the Elixir image
docker run --rm -p 4000:4000 \
  -e DATABASE_URL="ecto://postgres:postgres@host.docker.internal/agentic_platform" \
  -e REDIS_URL="redis://host.docker.internal:6379" \
  agentic-platform:latest

# Test the Go image
docker run --rm -p 50051:50051 -p 8080:8080 agentic-gateway:latest
```

---

## Pattern 2: Kubernetes Manifests

### Deployment

```yaml
# k8s/deployment.yaml — Elixir deployment
# WHY: Deployment manages replica sets. It ensures N pods are running
# and handles rolling updates without downtime.

apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentic-platform
  labels:
    app: agentic-platform
    component: agent-brain
spec:
  # 3 replicas for high availability
  # WHY: 3 replicas survive 1 node failure with no downtime.
  # Pod anti-affinity ensures they're on different nodes.
  replicas: 3

  # Rolling update strategy
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # allow 1 extra pod during update
      maxUnavailable: 0   # never reduce below 3 during update
      # WHY: maxUnavailable: 0 ensures zero downtime. At worst,
      # you briefly have 4 pods (3 old + 1 new).

  selector:
    matchLabels:
      app: agentic-platform

  template:
    metadata:
      labels:
        app: agentic-platform
        component: agent-brain
    spec:
      # Pod anti-affinity — don't put all pods on the same node
      # WHY: If one node dies, you lose at most 1 replica, not all 3.
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: agentic-platform
                topologyKey: kubernetes.io/hostname

      containers:
        - name: agentic-platform
          image: agentic-platform:latest
          ports:
            - containerPort: 4000
              name: http
            - containerPort: 4364
              name: dist

          # Environment variables from ConfigMap
          envFrom:
            - configMapRef:
                name: agentic-platform-config

          # Secrets from K8s Secrets
          # COMMON MISTAKE: Putting secrets in ConfigMaps — they're not encrypted.
          # ConfigMaps are base64-encoded, not encrypted. Use Secrets for passwords.
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: agentic-platform-secrets
                  key: database-url
            - name: SECRET_KEY_BASE
              valueFrom:
                secretKeyRef:
                  name: agentic-platform-secrets
                  key: secret-key-base
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: agentic-platform-secrets
                  key: redis-url

          # Resource limits — prevent one pod from consuming all node resources
          # WHY: Without limits, a memory leak in one pod can OOM-kill other pods
          # on the same node. Limits are your safety net.
          resources:
            requests:
              cpu: "250m"      # 0.25 CPU cores
              memory: "512Mi"  # 512 MB
            limits:
              cpu: "1000m"     # 1 CPU core
              memory: "1Gi"    # 1 GB

          # Liveness probe — is the process alive?
          # WHY: If the BEAM VM hangs (deadlock, infinite loop), K8s needs
          # to know so it can restart the pod. Without liveness probes,
          # a hung pod continues receiving traffic.
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3

          # Readiness probe — is the pod ready to receive traffic?
          # WHY: During startup, the pod shouldn't receive traffic yet.
          # Readiness tells K8s "I'm ready" only after the app is fully
          # initialized (DB connected, telemetry started, etc.)
          readinessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3

          # Startup probe — for slow-starting applications
          # WHY: BEAM takes time to compile and start. Without a startup probe,
          # the liveness probe might kill the pod before it's ready.
          # K8s only checks liveness/readiness AFTER the startup probe succeeds.
          startupProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 30  # 30 * 5s = 150s max startup time

      # Termination grace period — time to finish in-flight requests
      # WHY: When K8s decides to stop a pod, it sends SIGTERM.
      # The BEAM needs time to finish processing, flush logs, and close connections.
      terminationGracePeriodSeconds: 60
```

### Service

```yaml
# k8s/service.yaml — Load balancer for the Elixir app
# WHY: A Service provides a stable DNS name and IP that routes to pods.
# Without a Service, pods have ephemeral IPs that change on restart.

apiVersion: v1
kind: Service
metadata:
  name: agentic-platform
  labels:
    app: agentic-platform
spec:
  type: ClusterIP
  # WHY: ClusterIP is internal-only. Use Ingress for external access.
  # ClusterIP is the safest default — no accidental public exposure.

  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP
    - name: dist
      port: 4364
      targetPort: dist
      protocol: TCP
      # WHY: Port 4364 is the BEAM distribution port. Elixir nodes
      # need this to communicate with each other across pods.

  selector:
    app: agentic-platform
```

### ConfigMap

```yaml
# k8s/configmap.yaml — Non-sensitive configuration
# WHY: ConfigMaps separate config from code. You can change config
# without rebuilding the Docker image. ConfigMaps are visible to
# anyone with K8s read access — never put secrets here.

apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-platform-config
  labels:
    app: agentic-platform
data:
  # Phoenix configuration
  PHOENIX_ENV: "prod"
  PHOENIX_HOST: "0.0.0.0"
  PHOENIX_PORT: "4000"
  PHOENIX_SERVER: "true"

  # Elixir distribution
  RELEASE_DISTRIBUTION: "name"
  RELEASE_NODE: "agentic-platform@agentic-platform.agentic-platform.svc.cluster.local"
  # WHY: K8s DNS resolves this to the pod's ClusterIP. Elixir nodes
  # use this to find each other across pods.

  # Logging
  LOG_LEVEL: "info"
  ERL_AFLAGS: "-proto_dist inet_tcp"

  # Telemetry
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://jaeger-collector.telemetry.svc.cluster.local:4317"
  PROMETHEUS_PORT: "9090"
```

### Go Gateway Deployment

```yaml
# k8s/go-gateway-deployment.yaml — Go AgentBridge Gateway
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-gateway
  labels:
    app: agent-gateway
    component: infrastructure
spec:
  replicas: 2
  selector:
    matchLabels:
      app: agent-gateway
  template:
    metadata:
      labels:
        app: agent-gateway
    spec:
      containers:
        - name: agent-gateway
          image: agentic-gateway:latest
          ports:
            - containerPort: 50051
              name: grpc
            - containerPort: 8080
              name: http
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "256Mi"
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 3
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: agent-gateway
spec:
  type: ClusterIP
  ports:
    - name: grpc
      port: 50051
      targetPort: grpc
    - name: http
      port: 8080
      targetPort: http
  selector:
    app: agent-gateway
```

---

## Pattern 3: Helm Charts

### Why Helm?

Kubernetes YAML is verbose. A production deployment has 50+ lines per resource. Helm templates these resources with variables. You override values per environment (dev, staging, prod) without copying YAML files.

### Chart Structure

```
agentic-platform-chart/
├── Chart.yaml          # Chart metadata
├── values.yaml         # Default values (overridden per environment)
├── values-dev.yaml     # Dev overrides
├── values-prod.yaml    # Production overrides
└── templates/
    ├── _helpers.tpl    # Template helpers
    ├── deployment.yaml
    ├── service.yaml
    ├── configmap.yaml
    ├── ingress.yaml
    └── hpa.yaml        # Horizontal Pod Autoscaler
```

### values.yaml

```yaml
# values.yaml — Default Helm values
# WHY: These are sensible defaults. Override per environment in values-{env}.yaml.

replicaCount:
  elixir: 3
  gateway: 2

image:
  elixir:
    repository: agentic-platform
    tag: "latest"
    pullPolicy: IfNotPresent
  gateway:
    repository: agentic-gateway
    tag: "latest"
    pullPolicy: IfNotPresent

service:
  elixir:
    type: ClusterIP
    port: 80
  gateway:
    type: ClusterIP
    grpcPort: 50051
    httpPort: 8080

resources:
  elixir:
    requests:
      cpu: "250m"
      memory: "512Mi"
    limits:
      cpu: "1000m"
      memory: "1Gi"
  gateway:
    requests:
      cpu: "100m"
      memory: "128Mi"
    limits:
      cpu: "500m"
      memory: "256Mi"

# Database connection — overridden by secrets
database:
  host: "postgres.default.svc.cluster.local"
  port: 5432
  name: "agentic_platform"

redis:
  host: "redis.default.svc.cluster.local"
  port: 6379

# Health check configuration
healthCheck:
  liveness:
    initialDelaySeconds: 30
    periodSeconds: 10
  readiness:
    initialDelaySeconds: 10
    periodSeconds: 5
  startup:
    initialDelaySeconds: 10
    periodSeconds: 5
    failureThreshold: 30

# Autoscaling
autoscaling:
  enabled: false
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

### values-prod.yaml

```yaml
# values-prod.yaml — Production overrides
replicaCount:
  elixir: 5
  gateway: 3

resources:
  elixir:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "2000m"
      memory: "2Gi"
  gateway:
    requests:
      cpu: "200m"
      memory: "256Mi"
    limits:
      cpu: "1000m"
      memory: "512Mi"

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20
  targetCPUUtilizationPercentage: 60

# Production uses specific image tags, never "latest"
image:
  elixir:
    tag: "v1.2.3"
    pullPolicy: Always
  gateway:
    tag: "v1.2.3"
    pullPolicy: Always
```

### Helm Commands

```bash
# Install the chart in dev
helm install agentic ./agentic-platform-chart \
  -f agentic-platform-chart/values-dev.yaml \
  --namespace agentic-dev

# Upgrade to a new version in production
helm upgrade agentic ./agentic-platform-chart \
  -f agentic-platform-chart/values-prod.yaml \
  --set image.elixir.tag=v1.3.0 \
  --set image.gateway.tag=v1.3.0 \
  --namespace agentic-prod

# Rollback if something goes wrong
helm rollback agentic 1 --namespace agentic-prod

# List all releases
helm list --all-namespaces
```

---

## Pattern 4: Terraform Infrastructure

### Why Terraform?

Kubernetes runs your containers, but who creates the Kubernetes cluster? Who provisions the database, the cache, the networking? Terraform manages cloud infrastructure declaratively.

### main.tf

```hcl
# main.tf — Terraform configuration for the Agentic Platform
#
# WHY: Terraform creates cloud resources (VPC, EKS, RDS, ElastiCache)
# that Kubernetes runs on. Without Terraform, you'd manually click
# through the AWS console — slow, error-prone, and impossible to version.

terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state storage — critical for team collaboration
  # WHY: Local state means only one person can run Terraform at a time.
  # S3 backend lets the team share state with locking.
  backend "s3" {
    bucket         = "agentic-platform-tfstate"
    key            = "prod/terraform.tfstate"
    region         = "us-west-2"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

# Provider configuration
provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "agentic-platform"
}

# ============================================================
# VPC — isolated network for the platform
# ============================================================
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.0"

  name = "${var.cluster_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "prod"
  # WHY: Single NAT gateway in dev saves $32/month. Three NAT gateways
  # in prod for high availability.

  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Environment = var.environment
    Project     = "agentic-platform"
  }
}

# ============================================================
# EKS — managed Kubernetes cluster
# ============================================================
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.30"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Managed node groups
  eks_managed_node_groups = {
    # General workloads — Elixir agents, Go gateway
    general = {
      desired_size = 3
      min_size     = 2
      max_size     = 10

      instance_types = ["t3.large"]
      # WHY: t3.large has 2 vCPU and 8GB RAM — enough for BEAM + Go processes.

      labels = {
        role = "general"
      }
    }

    # Monitoring — Prometheus, Grafana, Loki
    monitoring = {
      desired_size = 2
      min_size     = 1
      max_size     = 3

      instance_types = ["t3.medium"]

      labels = {
        role = "monitoring"
      }
    }
  }

  tags = {
    Environment = var.environment
    Project     = "agentic-platform"
  }
}

# ============================================================
# RDS — managed PostgreSQL
# ============================================================
module "postgres" {
  source  = "terraform-aws-modules/rds/aws"
  version = "6.4"

  identifier = "${var.cluster_name}-postgres"

  engine         = "postgres"
  engine_version = "16.2"
  instance_class = var.environment == "prod" ? "db.r6g.large" : "db.t3.medium"

  allocated_storage     = 50
  max_allocated_storage = 200
  # WHY: max_allocated_storage enables autoscaling. When the database
  # fills up, RDS automatically increases storage up to 200GB.

  db_name  = "agentic_platform"
  username = "agentic_admin"
  # COMMON MISTAKE: Using "postgres" as the username. It's the first thing
  # attackers try. Use a non-obvious name.

  password = var.db_password
  # WHY: This variable should come from a .tfvars file or environment variable.
  # NEVER commit passwords to version control.

  port = 5432

  multi_az               = var.environment == "prod"
  # WHY: Multi-AZ creates a standby replica in another availability zone.
  # If the primary fails, RDS automatically fails over to the standby.

  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [module.vpc.default_security_group_id]

  backup_retention_period = var.environment == "prod" ? 30 : 7
  # WHY: 30 days of backups in prod lets you recover from accidental
  # deletion up to a month later.

  tags = {
    Environment = var.environment
    Project     = "agentic-platform"
  }
}

# ============================================================
# ElastiCache — managed Redis
# ============================================================
module "redis" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "1.3"

  replication_group_id = "${var.cluster_name}-redis"
  description          = "Redis for Oban job queue and caching"

  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.environment == "prod" ? "cache.r6g.large" : "cache.t3.medium"
  num_cache_clusters   = var.environment == "prod" ? 2 : 1
  # WHY: 2 clusters in prod for automatic failover.

  port = 6379

  subnet_group_name  = module.vpc.elasticache_subnet_group_name
  security_group_ids = [module.vpc.default_security_group_id]

  tags = {
    Environment = var.environment
    Project     = "agentic-platform"
  }
}

# ============================================================
# Outputs — values needed by Helm
# ============================================================
output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = module.eks.cluster_endpoint
}

output "postgres_endpoint" {
  description = "RDS endpoint"
  value       = module.postgres.db_instance_endpoint
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.redis.elasticache_replication_group_primary_endpoint_address
}
```

### Terraform Commands

```bash
# Initialize — download providers and modules
terraform init

# Plan — preview changes without applying
terraform plan -var="environment=dev"

# Apply — create the infrastructure
terraform apply -var="environment=dev"

# Destroy — tear down everything (use carefully!)
terraform destroy -var="environment=dev"
```

---

## Pattern 5: Health Probe Deep Dive

### Why Three Probes?

K8s has three types of health probes, each solving a different problem:

```
Pod Startup Timeline:
│
├─ Container starts
│  ├─ BEAM VM boots (~5s)
│  ├─ Elixir compiles (~30s in prod with precompiled)
│  ├─ OTP applications start (~10s)
│  ├─ Database migrations run (~5s)
│  ├─ Telemetry setup (~1s)
│  └─ App ready to serve traffic
│
├─ Startup probe: "Are you done starting?"
│  └─ K8s only checks liveness/readiness AFTER this succeeds
│
├─ Liveness probe: "Is the process alive?"
│  └─ If this fails, K8s restarts the pod
│
└─ Readiness probe: "Can you handle traffic?"
   └─ If this fails, K8s removes the pod from the Service
```

### Health Endpoint Implementation

```elixir
defmodule AgenticPlatformWeb.HealthController do
  use Phoenix.Controller

  # Liveness check — is the BEAM VM alive?
  # WHY: This should always succeed unless the VM is deadlocked.
  # Don't check external dependencies here — a database outage shouldn't
  # restart every pod.
  def healthz(conn, _params) do
    send_resp(conn, 200, "ok")
  end

  # Readiness check — is the app ready to serve traffic?
  # WHY: This checks external dependencies. If the database is unreachable,
  # the pod shouldn't receive traffic even if the BEAM is alive.
  def readyz(conn, _params) do
    checks = [
      check_database(),
      check_redis(),
      check_telemetry()
    ]

    if Enum.all?(checks, &match?({:ok, _}, &1)) do
      send_resp(conn, 200, "ready")
    else
      failures = Enum.filter(checks, &match?({:error, _}, &1))
      json(conn, %{status: "not ready", failures: failures})
    end
  end

  defp check_database do
    try do
      Ecto.Adapters.SQL.query!(AgenticPlatform.Repo, "SELECT 1", [])
      {:ok, :database}
    rescue
      e -> {:error, {:database, Exception.message(e)}}
    end
  end

  defp check_redis do
    try do
      Redix.command!(AgenticPlatform.Redis, ["PING"])
      {:ok, :redis}
    rescue
      e -> {:error, {:redis, Exception.message(e)}}
    end
  end

  defp check_telemetry do
    # Check if telemetry handlers are attached
    if Process.whereis(:telemetry_handler_registry) do
      {:ok, :telemetry}
    else
      {:error, {:telemetry, "handler registry not started"}}
    end
  end
end
```

---

## Deployment Sequence

```bash
# Step 1: Provision infrastructure
cd terraform
terraform init
terraform apply -var="environment=prod"

# Step 2: Configure kubectl
aws eks update-kubeconfig --name agentic-platform --region us-west-2

# Step 3: Create secrets
kubectl create secret generic agentic-platform-secrets \
  --from-literal=database-url="ecto://agentic_admin:PASSWORD@RDS_ENDPOINT/agentic_platform" \
  --from-literal=secret-key-base="LONG_RANDOM_STRING" \
  --from-literal=redis-url="redis://REDIS_ENDPOINT:6379"

# Step 4: Deploy with Helm
cd ../agentic-platform-chart
helm upgrade --install agentic . \
  -f values-prod.yaml \
  --namespace agentic-prod \
  --create-namespace

# Step 5: Verify
kubectl get pods -n agentic-prod
kubectl get svc -n agentic-prod
kubectl logs -f deployment/agentic-platform -n agentic-prod
```

---

## What's Next

Your platform is deployed to production. Continue to [Module 16: Capstone](16-capstone.md) to bring everything together.
