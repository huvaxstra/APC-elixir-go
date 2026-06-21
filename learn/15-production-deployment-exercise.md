# Module 15 Exercise: Deploy to Kubernetes

> **What you'll build**: Docker images, K8s manifests, Helm chart, and Terraform config for the hybrid platform.
> **Skills practiced**: Docker multi-stage, K8s deployments, Helm templating, Terraform provisioning
> **Time estimate**: 4-5 hours

---

## Learning Objectives

By completing this exercise, you will:
1. Write Docker multi-stage builds for Go and Elixir
2. Create K8s manifests with health probes and resource limits
3. Build a Helm chart with environment-specific value overrides
4. Write Terraform to provision a VPC and EKS cluster
5. Deploy the full stack with one command

---

## Part 1: Docker Multi-Stage Builds (1 hour)

### Starter Code — Elixir

Save this as `Dockerfile.elixir`:

```dockerfile
# Elixir multi-stage Dockerfile
# Stage 1: Build
# Stage 2: Runtime

# TODO: Complete the build stage
# Requirements:
# - Use hexpm/elixir:1.18.4-erlang-27.3.4-debian-bookworm as base
# - Install build-essential, git, curl
# - Install hex and rebar
# - Copy mix.exs and mix.lock FIRST (layer caching)
# - Run mix deps.get --only prod
# - Copy config, lib, priv, assets directories
# - Set MIX_ENV=prod
# - Run mix compile
# - Run mix release

# TODO: Complete the runtime stage
# Requirements:
# - Use debian:bookworm-slim as base
# - Install libstdc++6, openssl, libncurses5
# - Set locale (LANG=en_US.UTF-8)
# - Create non-root user "app"
# --chown=app:app
# - Copy release from build stage
# - USER app
# - EXPOSE 4000
# - Health check with curl
# - CMD ["bin/agentic_platform", "start"]
```

### Starter Code — Go

Save this as `Dockerfile.go`:

```dockerfile
# Go multi-stage Dockerfile
# Stage 1: Build
# Stage 2: Runtime (scratch)

# TODO: Complete the build stage
# Requirements:
# - Use golang:1.26-bookworm as base
# - Copy go.mod and go.sum FIRST (layer caching)
# - Run go mod download
# - Copy cmd/, internal/, proto/ directories
# - Build with CGO_ENABLED=0 GOOS=linux
# - Output binary to /bridge-server

# TODO: Complete the runtime stage
# Requirements:
# - Use scratch as base
# - Copy binary from build stage
# - Copy CA certificates from build stage (/etc/ssl/certs/ca-certificates.crt)
# - EXPOSE 50051 8080
# - ENTRYPOINT ["/bridge-server"]
```

### Your Task

1. Complete both Dockerfiles with the requirements above
2. Build and test both images locally
3. Verify the Elixir image runs and responds on port 4000
4. Verify the Go image runs and responds on ports 50051 and 8080

### Hints

- Docker layer caching: copy dependency files first, source code second
- CGO_ENABLED=0 is critical for scratch images
- Always use `exec` form for CMD and ENTRYPOINT (JSON array, not string)
- Non-root users prevent privilege escalation attacks

---

## Part 2: Kubernetes Manifests (1.5 hours)

### Starter Code — Elixir Deployment

Save this as `k8s/elixir-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentic-platform
  labels:
    app: agentic-platform
spec:
  # TODO: Set replicas to 3
  replicas: 0

  # TODO: Define rolling update strategy
  # Requirements:
  # - type: RollingUpdate
  # - maxSurge: 1
  # - maxUnavailable: 0

  selector:
    matchLabels:
      app: agentic-platform

  template:
    metadata:
      labels:
        app: agentic-platform
    spec:
      # TODO: Add pod anti-affinity to spread pods across nodes
      # Hint: Use preferredDuringSchedulingIgnoredDuringExecution
      # with topologyKey: kubernetes.io/hostname

      containers:
        - name: agentic-platform
          image: agentic-platform:latest
          ports:
            - containerPort: 4000
              name: http

          # TODO: Add envFrom for ConfigMap
          # ConfigMap name: agentic-platform-config

          # TODO: Add env vars from Secrets
          # Required secrets:
          # - DATABASE_URL from secretKeyRef
          # - SECRET_KEY_BASE from secretKeyRef
          # - REDIS_URL from secretKeyRef

          # TODO: Add resource requests and limits
          # requests: cpu=250m, memory=512Mi
          # limits: cpu=1000m, memory=1Gi

          # TODO: Add liveness probe
          # HTTP GET /healthz on port "http"
          # initialDelaySeconds: 30, periodSeconds: 10

          # TODO: Add readiness probe
          # HTTP GET /healthz on port "http"
          # initialDelaySeconds: 10, periodSeconds: 5

          # TODO: Add startup probe
          # HTTP GET /healthz on port "http"
          # failureThreshold: 30, periodSeconds: 5

      # TODO: Set terminationGracePeriodSeconds to 60
```

### Starter Code — Service

Save this as `k8s/elixir-service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: agentic-platform
  labels:
    app: agentic-platform
spec:
  # TODO: Set type to ClusterIP
  type: ""

  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP

  selector:
    app: agentic-platform
```

### Starter Code — ConfigMap

Save this as `k8s/configmap.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-platform-config
  labels:
    app: agentic-platform
data:
  # TODO: Add these configuration keys:
  # PHOENIX_ENV: "prod"
  # PHOENIX_HOST: "0.0.0.0"
  # PHOENIX_PORT: "4000"
  # PHOENIX_SERVER: "true"
  # LOG_LEVEL: "info"
```

### Your Task

1. Complete all three K8s manifests with the requirements above
2. Apply them to a local K8s cluster (minikube or kind)
3. Verify pods start and pass health checks
4. Verify the Service routes traffic to pods

### Hints

- `kubectl apply -f k8s/` applies all manifests at once
- `kubectl get pods -w` watches pod status in real-time
- `kubectl describe pod <name>` shows events and probe results
- `kubectl logs <pod-name>` shows application logs
- `kubectl port-forward svc/agentic-platform 4000:80` forwards traffic locally

---

## Part 3: Helm Chart (1 hour)

### Starter Code — Chart.yaml

Save this as `chart/Chart.yaml`:

```yaml
apiVersion: v2
name: agentic-platform
description: Hybrid Elixir/Go Agentic Platform
type: application
version: 0.1.0
appVersion: "1.0.0"
```

### Starter Code — values.yaml

Save this as `chart/values.yaml`:

```yaml
# Default values — overridden per environment

replicaCount:
  # TODO: Set elixir: 3, gateway: 2

image:
  elixir:
    # TODO: Set repository: agentic-platform, tag: "latest"
  gateway:
    # TODO: Set repository: agentic-gateway, tag: "latest"

resources:
  elixir:
    requests:
      cpu: "250m"
      memory: "512Mi"
    limits:
      # TODO: Set cpu: "1000m", memory: "1Gi"

autoscaling:
  enabled: false
  minReplicas: 3
  maxReplicas: 10
```

### Starter Code — Template

Save this as `chart/templates/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-agentic-platform
  labels:
    app: agentic-platform
spec:
  # TODO: Use Helm templating for replicas
  # Hint: {{ .Values.replicaCount.elixir }}
  replicas: 1

  selector:
    matchLabels:
      app: agentic-platform

  template:
    metadata:
      labels:
        app: agentic-platform
    spec:
      containers:
        - name: agentic-platform
          # TODO: Template the image
          # Hint: {{ .Values.image.elixir.repository }}:{{ .Values.image.elixir.tag }}
          image: agentic-platform:latest
          ports:
            - containerPort: 4000

          # TODO: Template resource limits
          resources:
            {}
```

### Your Task

1. Complete the Helm values and template with the requirements above
2. Create a `values-prod.yaml` with production overrides (5 replicas, higher resources, autoscaling enabled)
3. Install the chart with `helm install agentic ./chart`
4. Upgrade with production values: `helm upgrade agentic ./chart -f chart/values-prod.yaml`
5. Verify the upgrade changes replica count and resource limits

### Hints

- Helm template syntax: `{{ .Values.replicaCount.elixir }}`
- Conditional blocks: `{{ if .Values.autoscaling.enabled }}...{{ end }}`
- `helm template ./chart` renders templates locally without installing
- `helm diff upgrade` shows what would change before applying

---

## Part 4: Terraform (1 hour)

### Starter Code

Save this as `terraform/main.tf`:

```hcl
terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  # TODO: Set region from variable
  region = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

# TODO: Create a VPC module
# Requirements:
# - CIDR: 10.0.0.0/16
# - 3 private subnets (10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24)
# - 3 public subnets (10.0.101.0/24, 10.0.102.0/24, 10.0.103.0/24)
# - Enable NAT gateway
# - Enable DNS hostnames

# TODO: Create an EKS cluster
# Requirements:
# - Cluster name: agentic-platform
# - Kubernetes version: 1.32
# - VPC from the VPC module
# - One node group with instance type t3.large

# Outputs
# TODO: Output the EKS cluster endpoint
# TODO: Output the VPC ID
```

### Your Task

1. Complete the Terraform config with VPC and EKS resources
2. Run `terraform init` to download providers
3. Run `terraform plan` to preview changes
4. Run `terraform apply` to create infrastructure (if you have AWS credentials)
5. Verify with `terraform output`

### Hints

- Use `terraform-aws-modules/vpc/aws` for the VPC
- Use `terraform-aws-modules/eks/aws` for EKS
- `terraform plan -var="environment=dev"` previews without applying
- `terraform destroy -var="environment=dev"` tears everything down

---

## Solution

<details>
<summary>Click to reveal solution</summary>

### Elixir Dockerfile — Build Stage

```dockerfile
FROM hexpm/elixir:1.18.4-erlang-27.3.4-debian-bookworm-20240612 AS build

RUN apt-get update -y && apt-get install -y build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mix local.hex --force && mix local.rebar --force

COPY mix.exs mix.lock ./
RUN mix deps.get --only prod

COPY config config
COPY lib lib
COPY priv priv
COPY assets assets

ENV MIX_ENV=prod
RUN mix compile

COPY assets/package.json assets/package-lock.json assets/
RUN cd assets && npm ci
RUN mix assets.deploy

RUN mix release
```

### Elixir Dockerfile — Runtime Stage

```dockerfile
FROM debian:bookworm-slim AS runtime

RUN apt-get update -y && apt-get install -y libstdc++6 openssl libncurses5 locales \
    && rm -rf /var/lib/apt/lists/*

RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN useradd --create-home app
WORKDIR /home/app

COPY --from=build --chown=app:app /app/_build/prod/rel/agentic_platform ./

USER app
EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:4000/healthz || exit 1

CMD ["bin/agentic_platform", "start"]
```

### Go Dockerfile — Build Stage

```dockerfile
FROM golang:1.26-bookworm AS build

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY cmd/ cmd/
COPY internal/ internal/
COPY proto/ proto/

RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o bridge-server ./cmd/bridge-server
```

### Go Dockerfile — Runtime Stage

```dockerfile
FROM scratch

COPY --from=build /app/bridge-server /bridge-server
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

EXPOSE 50051 8080

ENTRYPOINT ["/bridge-server"]
```

### K8s Deployment (completed)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentic-platform
  labels:
    app: agentic-platform
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: agentic-platform
  template:
    metadata:
      labels:
        app: agentic-platform
    spec:
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
          envFrom:
            - configMapRef:
                name: agentic-platform-config
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
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "1Gi"
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 10
            periodSeconds: 5
            failureThreshold: 30
      terminationGracePeriodSeconds: 60
```

### K8s Service (completed)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: agentic-platform
  labels:
    app: agentic-platform
spec:
  type: ClusterIP
  ports:
    - name: http
      port: 80
      targetPort: http
      protocol: TCP
  selector:
    app: agentic-platform
```

### K8s ConfigMap (completed)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-platform-config
  labels:
    app: agentic-platform
data:
  PHOENIX_ENV: "prod"
  PHOENIX_HOST: "0.0.0.0"
  PHOENIX_PORT: "4000"
  PHOENIX_SERVER: "true"
  LOG_LEVEL: "info"
```

### Helm values.yaml (completed)

```yaml
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

resources:
  elixir:
    requests:
      cpu: "250m"
      memory: "512Mi"
    limits:
      cpu: "1000m"
      memory: "1Gi"

autoscaling:
  enabled: false
  minReplicas: 3
  maxReplicas: 10
```

### Helm values-prod.yaml (completed)

```yaml
replicaCount:
  elixir: 5
  gateway: 3

image:
  elixir:
    tag: "v1.0.0"
    pullPolicy: Always
  gateway:
    tag: "v1.0.0"
    pullPolicy: Always

resources:
  elixir:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "2000m"
      memory: "2Gi"

autoscaling:
  enabled: true
  minReplicas: 5
  maxReplicas: 20
```

### Terraform (completed)

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.0"

  name = "agentic-platform-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-west-2a", "us-west-2b", "us-west-2c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = var.environment != "prod"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Environment = var.environment
    Project     = "agentic-platform"
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.0"

  cluster_name    = "agentic-platform"
  cluster_version = "1.30"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    general = {
      desired_size   = 3
      min_size       = 2
      max_size       = 10
      instance_types = ["t3.large"]
    }
  }

  tags = {
    Environment = var.environment
    Project     = "agentic-platform"
  }
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "vpc_id" {
  value = module.vpc.vpc_id
}
```

</details>

---

## What's Next

After completing this exercise, continue to [Module 16: Capstone](16-capstone.md) to bring everything together into a complete platform.
