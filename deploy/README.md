# Deployment Guide

This guide covers deploying the Hybrid Elixir/Go Agentic Platform from local development to production Kubernetes.

---

## Local Development

### Prerequisites

- Docker Compose
- Go 1.22+
- Elixir 1.16+ / Erlang/OTP 26+

### Quick Start

```bash
# Clone and enter the project
cd agentic-platform

# Start PostgreSQL and Redis
docker compose up -d

# Setup the Elixir application
cd elixir
mix deps.get
mix ecto.setup  # creates DB + seeds + migrations
mix phx.server  # starts Phoenix on http://localhost:4000

# Start the Go gateway (separate terminal)
cd go
go run ./cmd/bridge-server  # gRPC on :50051, HTTP on :8080

# Start observability stack (separate terminal)
docker compose -f docker-compose.observability.yml up -d
# Grafana: http://localhost:3001 (admin/admin)
# Prometheus: http://localhost:9090
# Jaeger: http://localhost:16686
```

### Verify Local Setup

```bash
# Health check
curl http://localhost:4000/healthz

# Prometheus metrics
curl http://localhost:8080/metrics

# LiveDashboard
open http://localhost:4000/dashboard
```

---

## Docker Builds

### Elixir Image

```bash
docker build -t agentic-platform:latest -f elixir/Dockerfile elixir/

# Test locally
docker run --rm -p 4000:4000 \
  -e DATABASE_URL="ecto://postgres:postgres@host.docker.internal/agentic_platform" \
  -e REDIS_URL="redis://host.docker.internal:6379" \
  -e SECRET_KEY_BASE=$(openssl rand -base64 64) \
  agentic-platform:latest
```

### Go Gateway Image

```bash
docker build -t agentic-gateway:latest -f go/Dockerfile go/

# Test locally
docker run --rm -p 50051:50051 -p 8080:8080 agentic-gateway:latest
```

### Tagging for Registry

```bash
# Tag for ECR, Docker Hub, or GCR
docker tag agentic-platform:latest $REGISTRY/agentic-platform:v1.0.0
docker tag agentic-gateway:latest $REGISTRY/agentic-gateway:v1.0.0

# Push
docker push $REGISTRY/agentic-platform:v1.0.0
docker push $REGISTRY/agentic-gateway:v1.0.0
```

---

## Kubernetes Deployment

### Prerequisites

- kubectl configured for your cluster
- Helm 3.x installed

### Deploy with Manifests (Simple)

```bash
# Create namespace
kubectl create namespace agentic

# Create secrets
kubectl create secret generic agentic-platform-secrets \
  --namespace agentic \
  --from-literal=database-url="ecto://user:pass@host:5432/agentic_platform" \
  --from-literal=secret-key-base="$(openssl rand -base64 64)" \
  --from-literal=redis-url="redis://host:6379"

# Apply manifests
kubectl apply -f k8s/ --namespace agentic

# Verify
kubectl get pods -n agentic
kubectl get svc -n agentic
```

### Deploy with Helm (Recommended)

```bash
# Install the chart
helm upgrade --install agentic ./helm \
  -f helm/values-dev.yaml \
  --namespace agentic \
  --create-namespace

# Upgrade for production
helm upgrade agentic ./helm \
  -f helm/values-prod.yaml \
  --set image.elixir.tag=v1.0.0 \
  --set image.gateway.tag=v1.0.0 \
  --namespace agentic-prod

# Rollback if needed
helm rollback agentic 1 --namespace agentic-prod
```

### Health Checks

```bash
# Check pod health
kubectl describe pod -l app=agentic-platform

# View logs
kubectl logs -f deployment/agentic-platform --tail=100

# Port forward for local access
kubectl port-forward svc/agentic-platform 4000:80 -n agentic
```

---

## Terraform Infrastructure

### Prerequisites

- AWS CLI configured
- Terraform 1.7+
- S3 bucket for state locking

### Provision

```bash
cd terraform

# Initialize
terraform init

# Plan (preview changes)
terraform plan -var="environment=dev" -out=tfplan

# Apply (create infrastructure)
terraform apply tfplan

# Output values
terraform output
```

### Environments

| Environment | Command | Config |
|-------------|---------|--------|
| Dev | `terraform plan -var="environment=dev"` | Single NAT, t3.medium, single AZ |
| Staging | `terraform plan -var="environment=staging"` | Single NAT, t3.large, multi-AZ |
| Prod | `terraform plan -var="environment=prod"` | Multi-AZ NAT, r6g.large, Multi-AZ RDS |

### Teardown

```bash
# Destroy all resources (use with caution!)
terraform destroy -var="environment=dev"
```

---

## ArgoCD GitOps

### Setup

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### Application Manifest

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: agentic-platform
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/agentic-platform.git
    targetRevision: HEAD
    path: helm
    helm:
      valueFiles:
        - values-prod.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: agentic-prod
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### Apply

```bash
kubectl apply -f argocd-application.yaml
```

ArgoCD will automatically sync changes pushed to the Git repository.

---

## Troubleshooting

### Pod Not Starting

```bash
# Check events
kubectl describe pod <pod-name> -n agentic

# Common issues:
# - ImagePullBackOff: wrong image tag or registry auth
# - CrashLoopBackOff: check logs with kubectl logs <pod-name>
# - Pending: not enough resources, check node capacity
```

### gRPC Connection Failed

```bash
# Verify the gateway service exists
kubectl get svc agent-gateway -n agentic

# Port forward and test
kubectl port-forward svc/agent-gateway 50051:50051 -n agentic
grpcurl -plaintext localhost:50051 list
```

### Database Connection Failed

```bash
# Verify secrets exist
kubectl get secret agentic-platform-secrets -n agentic

# Check the ConfigMap
kubectl get configmap agentic-platform-config -n agentic -o yaml

# Test connectivity from inside the cluster
kubectl exec -it deployment/agentic-platform -n agentic -- \
  pg_isready -h $DATABASE_HOST -p 5432
```

### OOMKilled

```bash
# Check current memory usage
kubectl top pod -n agentic

# Increase limits in Helm values
helm upgrade agentic ./helm \
  --set resources.elixir.limits.memory=2Gi \
  --namespace agentic
```
