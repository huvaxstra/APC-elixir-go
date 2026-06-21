# Module 0: Environment Setup

> **What you'll set up**: Complete development environment for Go, Elixir, Docker, Kubernetes, and Terraform.
> **What you'll verify**: Smoke tests for every tool, Docker Compose for PostgreSQL + Redis.
> **Time estimate**: 2-3 hours

---

## Why Setup First

Every module in this course assumes these tools are installed and working. A broken environment wastes hours of debugging. This module ensures every tool is installed, versioned, and verified before you write a single line of code.

---

## 1.1 Required Tools

| Tool | Minimum Version | Purpose |
|------|----------------|---------|
| Go | 1.26+ | Infrastructure edge (K8s operators, Prometheus, CLI, gRPC) |
| Erlang/OTP | 27+ | BEAM runtime for Elixir |
| Elixir | 1.18+ | Agent brain (GenServer, Phoenix, Oban) |
| Docker | 24+ | Container builds, local services |
| kubectl | 1.32+ | Kubernetes cluster interaction |
| Terraform | 1.10+ | Infrastructure as Code |
| VS Code | latest | IDE with Go + Elixir extensions |

---

## 1.2 Install Go

### Linux (Debian/Ubuntu)

```bash
# Download Go 1.26 binary
# WHY: Official binary is the simplest install method
wget https://go.dev/dl/go1.26.4.linux-amd64.tar.gz

# Remove any previous Go install and extract new one
# COMMON MISTAKE: Forgetting to remove old version first — causes PATH conflicts
sudo rm -rf /usr/local/go
sudo tar -C /usr/local -xzf go1.26.4.linux-amd64.tar.gz

# Add Go to PATH for current session
# DEEP DIVE: Go binaries go to $HOME/go/bin, which must be on PATH
export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin

# Persist across sessions
echo 'export PATH=$PATH:/usr/local/go/bin:$HOME/go/bin' >> ~/.bashrc
```

### macOS

```bash
# Homebrew is the simplest path on macOS
brew install go
```

### Verify

```bash
# This should print go1.22.x or higher
go version

# GOPATH is where Go stores downloaded modules and binaries
# WHY: You need to know this for troubleshooting module issues
go env GOPATH
go env GOROOT
```

---

## 1.3 Install Erlang/OTP and Elixir

### Linux (Debian/Ubuntu)

```bash
# Install Erlang/OTP 27+ — the BEAM virtual machine
# DEEP DIVE: Erlang and Elixir are separate installs. Elixir compiles to Erlang bytecode.
# You MUST have Erlang installed first.

# Add Erlang Solutions repo for latest versions
wget https://packages.erlang-solutions.com/erlang-solutions_2.0_all.deb
sudo dpkg -i erlang-solutions_2.0_all.deb
sudo apt-get update

# Install Erlang OTP 27
sudo apt-get install -y erlang

# Install Elixir 1.18+ (includes mix, iex, elixir)
sudo apt-get install -y elixir

# Install hex and rebar — Elixir's package manager and build tool
# WHY: mix will prompt you to install these anyway, but doing it now avoids interruptions
mix local.hex --force
mix local.rebar --force
```

### macOS

```bash
# ASDF is the recommended version manager for Erlang + Elixir
# WHY: Version managers let you switch between project-specific versions
brew install asdf

# Add plugins
asdf plugin add erlang
asdf plugin add elixir

# Install specific versions
asdf install erlang 27.3.4
asdf install elixir 1.18.4-otp-27

# Set global versions
asdf global erlang 27.3.4
asdf global elixir 1.18.4-otp-27

# Install hex and rebar
mix local.hex --force
mix local.rebar --force
```

### Verify

```bash
# Erlang — should print OTP 27+
erl -eval 'erlang:display(erlang:system_info(otp_release)), halt().' -noshell

# Elixir — should print 1.16.x
elixir --version

# Interactive Elixir shell — try a simple expression
iex -e 'IO.puts("Elixir is working: #{System.version()}")'
```

---

## 1.4 Install Docker

### Linux

```bash
# Install Docker Engine (not Docker Desktop on Linux)
# WHY: Docker Desktop is for macOS/Windows. Linux uses Docker Engine directly.
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to the docker group so you don't need sudo
# COMMON MISTAKE: Forgetting this — every docker command will need sudo
sudo usermod -aG docker $USER

# Log out and back in for group change to take effect
# Then verify:
docker --version
docker compose version
```

### macOS

```bash
# Download Docker Desktop from https://www.docker.com/products/docker-desktop/
# Install and launch — it includes docker and docker compose
```

### Verify

```bash
# Docker version — should be 24+
docker --version

# Docker Compose version — should be v2.x
docker compose version

# Run hello-world to confirm Docker daemon is running
docker run hello-world
```

---

## 1.5 Install kubectl

```bash
# Linux — official binary
curl -LO "https://dl.k8s.io/release/v1.32.0/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# macOS
brew install kubectl

# Verify — shows client version (server version requires a cluster)
kubectl version --client
```

---

## 1.6 Install Terraform

```bash
# Linux — HashiCorp APT repository
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# macOS
brew install terraform

# Verify — should be 1.7+
terraform --version
```

---

## 1.7 VS Code Extensions

Install these extensions for the best development experience:

### Go Extensions

```
# Install via command line
code --install-extension golang.go
# Includes: Go language server (gopls), debugger, test runner, linter
```

### Elixir Extensions

```
# Install via command line
code --install-extension elixir-tools.elixir-tools
code --install-extension JakeBecker.elixir-ls
# Elixir Tools: Mix tasks, project creation
# ElixirLS: Language server with autocomplete, go-to-definition, dialyzer
```

### Useful Extras

```
code --install-extension ms-azuretools.vscode-docker
code --install-extension hashicorp.terraform
code --install-extension ms-kubernetes-tools.vscode-kubernetes-tools
```

---

## 1.8 Local Services: PostgreSQL + Redis

The capstone platform needs PostgreSQL (agent state persistence) and Redis (Oban job queue). Use Docker Compose to run both locally.

### Docker Compose File

Save this as `docker-compose.yml` in your project root:

```yaml
# docker-compose.yml — Local development services
# WHY: PostgreSQL for Ecto/Oban persistence, Redis for Oban job queue
# These match what the capstone K8s deployment will use in production

version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    # ALPINE: smaller image, faster pulls, same functionality
    container_name: agentic-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: agentic_platform
    ports:
      - "5432:5432"
    # WHY: Volume persists data across container restarts
    volumes:
      - postgres_data:/var/lib/postgresql/data
    # WHY: Health check ensures Postgres is ready before apps connect
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: agentic-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    # WHY: Redis needs AOF persistence for Oban job durability
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

### Start Services

```bash
# Start both services in the background
docker compose up -d

# Verify both are healthy
docker compose ps

# Expected output: both services show "healthy" status
# NAME                STATUS
# agentic-postgres    running (healthy)
# agentic-redis       running (healthy)
```

### Connect to PostgreSQL

```bash
# Connect to the database to verify it works
psql -h localhost -U postgres -d agentic_platform
# Password: postgres

# You're in the psql shell — run a quick test
SELECT version();

# Exit psql
\q
```

### Connect to Redis

```bash
# Connect to Redis CLI
redis-cli

# Test the connection
PING
# Expected: PONG

# Exit Redis CLI
exit
```

### Stop Services

```bash
# Stop but keep data (volumes persist)
docker compose down

# Stop AND delete all data (fresh start)
docker compose down -v
```

---

## 1.9 Smoke Tests

Run these commands to verify every tool works correctly. Every command should produce output without errors.

### Go Smoke Test

```bash
# Create a temp directory and run a Go program
mkdir -p /tmp/smoke-test && cd /tmp/smoke-test

# Initialize a Go module
go mod init smoke-test

# Write a tiny program
cat > main.go << 'EOF'
package main

import "fmt"

func main() {
    fmt.Println("Go smoke test passed")
}
EOF

# Build and run
go run main.go
# Expected: "Go smoke test passed"

# Clean up
rm -rf /tmp/smoke-test
```

### Elixir Smoke Test

```bash
# Create a temp Mix project
cd /tmp
mix new smoke_test --module SmokeTest
cd smoke_test

# Compile — should produce no warnings
mix compile

# Run the project
mix run -e 'IO.puts("Elixir smoke test passed")'
# Expected: "Elixir smoke test passed"

# Clean up
rm -rf /tmp/smoke_test
```

### Docker Smoke Test

```bash
# Run a lightweight container that prints a message
docker run --rm alpine echo "Docker smoke test passed"
# Expected: "Docker smoke test passed"
```

### kubectl Smoke Test

```bash
# This will fail to connect (no cluster) but should print the client version
kubectl version --client
# Expected: prints client version without errors
```

### Terraform Smoke Test

```bash
# Create a temp directory and run terraform init
mkdir -p /tmp/tf-smoke && cd /tmp/tf-smoke

# Write a minimal Terraform config
cat > main.tf << 'EOF'
terraform {
  required_version = ">= 1.10.0"
}

output "smoke_test" {
  value = "Terraform smoke test passed"
}
EOF

# Initialize — downloads providers if needed
terraform init
# Expected: "Terraform has been successfully initialized!"

# Validate the config
terraform validate
# Expected: "Success! The configuration is valid."

# Clean up
rm -rf /tmp/tf-smoke
```

---

## 1.10 Quick Reference

### Common Commands

| Task | Go | Elixir |
|------|-----|--------|
| Create project | `go mod init name` | `mix new name` |
| Build | `go build` | `mix compile` |
| Run | `go run main.go` | `mix run -e 'code'` |
| Test | `go test ./...` | `mix test` |
| Format | `gofmt -w .` | `mix format` |
| Lint | `golangci-lint run` | `mix credo` |
| Dependencies | `go mod tidy` | `mix deps.get` |

### Port Assignments

| Service | Port | Notes |
|---------|------|-------|
| PostgreSQL | 5432 | `localhost:5432` |
| Redis | 6379 | `localhost:6379` |
| Phoenix (dev) | 4000 | `localhost:4000` |
| Phoenix LiveDashboard | 4000/dashboard | Requires dev mode |
| Prometheus | 9090 | When running exporter |
| gRPC | 50051 | Go bridge server |

---

## What's Next

Your environment is ready. Continue to [Module 1: Go Fundamentals](01-go-fundamentals.md) to start building.
