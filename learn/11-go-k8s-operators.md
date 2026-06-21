# Module 11: Go K8s Operators (Week 11)

## What You'll Learn This Module

By the end of this module, you'll understand how to build Kubernetes operators in Go:

1. **controller-runtime** — the CNCF standard for building Kubernetes controllers
2. **Reconciler** — the core interface that ensures desired state matches actual state
3. **CRDs (Custom Resource Definitions)** — extending the Kubernetes API with your own resources
4. **Manager** — running controllers, webhook servers, and caches
5. **Informers** — watching for resource changes in real-time
6. **Leader election** — ensuring only one operator instance is active

This is how every production Kubernetes operator is built. The etcd operator, the Prometheus operator, the ArgoCD operator — they all use controller-runtime. If you need to manage custom resources in Kubernetes, this is the way.

---

## What Is a Kubernetes Operator?

A Kubernetes operator is a custom controller that manages custom resources. It watches for changes to resources and takes action to ensure the actual state matches the desired state.

Think of it like a thermostat. You set the desired temperature (desired state). The thermostat monitors the actual temperature (actual state). If they don't match, the thermostat turns on the heater or AC (reconciliation).

```
You set: 72°F (desired state)
Actual: 68°F (actual state)
Thermostat turns on heater → actual becomes 72°F (reconciled)
```

In Kubernetes terms:
- You create a CRD (Custom Resource Definition) that defines your resource type
- You create instances of that resource (desired state)
- The operator watches for changes and makes the cluster match the desired state

---

## Project Structure

Every controller-runtime project follows the same structure:

```
my-operator/
  cmd/
    main.go                    # Entry point — starts the manager
  internal/
    controller/
      agent_controller.go      # Reconciler implementation
    config/
      agent_types.go           # CRD type definitions
  config/
    crd/
      agent_crd.yaml           # CRD YAML for Kubernetes
    rbac/
      role.yaml                # RBAC permissions
      role_binding.yaml        # RBAC binding
    manager/
      manager.yaml             # Deployment manifest
  go.mod
  go.sum
```

### Why This Structure?

- `cmd/main.go` — the entry point. Separate from business logic.
- `internal/controller/` — private package. Other packages can't import it.
- `internal/config/` — CRD type definitions. Separated from controller logic.
- `config/` — Kubernetes manifests. YAML files for deploying the operator.
- This structure follows Go conventions: internal packages are private, and the entry point is minimal.

---

## Part 1: CRD Type Definitions

### What Is a CRD?

A CRD (Custom Resource Definition) extends the Kubernetes API. Kubernetes has built-in resources like Pods, Services, Deployments. A CRD lets you create your own resource type — like `Agent` — and Kubernetes treats it as a first-class citizen.

Think of a CRD as a database schema. It defines what fields an `Agent` resource has, what types they are, and what values are valid. Once you create the CRD, you can create `Agent` resources just like you create `Pod` resources.

```go
// internal/config/agent_types.go
//
// This file defines the CRD types for the Agent resource.
// These types are used by controller-runtime to generate
// the CRD YAML and to deserialize Agent resources from the API server.
//
// DEEP DIVE: Why separate types from controller logic?
// Because the types are shared between:
// 1. The controller (watches and reconciles Agents)
// 2. The webhook server (validates and mutates Agents)
// 3. The CRD generator (produces the YAML schema)
// If types were in the controller, you'd have circular dependencies.

package config

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// AgentSpec defines the desired state of Agent
// This is what the user specifies when creating an Agent resource.
//
// DEEP DIVE: The Spec vs Status pattern
// Spec = what the user WANTS (desired state)
// Status = what the system HAS (actual state)
// The controller's job is to make Status match Spec.
// This separation is a Kubernetes convention — all resources follow it.
type AgentSpec struct {
	// Image is the container image to run for this agent
	// +kubebuilder:validation:Required
	// +kubebuilder:validation:Pattern=`^[\w.-]+/[\w.-]+:[\w.-]+$`
	Image string `json:"image"`

	// Replicas is the number of agent instances to run
	// +kubebuilder:validation:Minimum=1
	// +kubebuilder:validation:Maximum=10
	// +kubebuilder:default=1
	Replicas *int32 `json:"replicas,omitempty"`

	// Model specifies the AI model this agent uses
	// +kubebuilder:validation:Enum=gpt-4;gpt-3.5-turbo;claude-3;llama-3
	Model string `json:"model"`

	// Resources defines CPU and memory requirements
	Resources AgentResources `json:"resources,omitempty"`

	// Enabled determines if the agent should be running
	// +kubebuilder:default=true
	Enabled bool `json:"enabled,omitempty"`
}

// AgentResources defines resource requirements for the agent
// These map directly to Kubernetes resource requests and limits.
type AgentResources struct {
	// CPU request (e.g., "100m" = 0.1 CPU cores)
	// +kubebuilder:validation:Pattern=`^\d+(m)?$`
	CPURequest string `json:"cpuRequest,omitempty"`

	// Memory request (e.g., "128Mi")
	// +kubebuilder:validation:Pattern=`^\d+(Mi|Gi)?$`
	MemoryRequest string `json:"memoryRequest,omitempty"`

	// CPU limit (e.g., "500m" = 0.5 CPU cores)
	CPULimit string `json:"cpuLimit,omitempty"`

	// Memory limit (e.g., "512Mi")
	MemoryLimit string `json:"memoryLimit,omitempty"`
}

// AgentStatus defines the observed state of Agent
// This is what the controller writes after reconciling.
//
// COMMON MISTAKE: Writing Status from outside the controller.
// Only the controller should update Status. Other components
// should read Status but never write it. If you need to update
// Status from outside, send a message to the controller.
type AgentStatus struct {
	// Phase represents the current lifecycle phase of the agent
	// +kubebuilder:validation:Enum=Pending;Running;Failed;Stopped
	Phase string `json:"phase,omitempty"`

	// ReadyReplicas is the number of agent instances that are ready
	ReadyReplicas int32 `json:"readyReplicas,omitempty"`

	// Conditions represent the latest available observations
	// of the agent's state
	Conditions []metav1.Condition `json:"conditions,omitempty"`

	// LastReconciledAt is the time of the last successful reconciliation
	LastReconciledAt *metav1.Time `json:"lastReconciledAt,omitempty"`

	// Message provides a human-readable status message
	Message string `json:"message,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Phase",type=string,JSONPath=`.status.phase`
// +kubebuilder:printcolumn:name="Ready",type=integer,JSONPath=`.status.readyReplicas`
// +kubebuilder:printcolumn:name="Age",type=date,JSONPath=`.metadata.creationTimestamp`

// Agent is the Schema for the agents API
//
// DEEP DIVE: The +kubebuilder comments are annotations that tell
// the code generator how to produce the CRD YAML. They specify:
// - +kubebuilder:object:root=true — this is a root type (not embedded)
// - +kubebuilder:subresource:status — enable the /status subresource
// - +kubebuilder:printcolumn — add columns to `kubectl get agents`
//
// COMMON MISTAKE: Forgetting +kubebuilder:subresource:status.
// Without it, you can't update Status separately from Spec.
// This means a Status update also triggers a Spec update, which
// triggers another reconciliation — an infinite loop.
type Agent struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   AgentSpec   `json:"spec,omitempty"`
	Status AgentStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

// AgentList contains a list of Agent
type AgentList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []Agent `json:"items"`
}
```

---

## Part 2: The Reconciler

### What Is Reconciliation?

Reconciliation is the core loop of every Kubernetes controller. It works like this:

1. Something changes (a resource is created, updated, or deleted)
2. The controller notices the change
3. The controller calls `Reconcile()` to fix the discrepancy
4. The controller updates the Status

The `Reconcile` function is idempotent — calling it multiple times with the same input produces the same result. This is critical because Kubernetes may deliver the same event multiple times.

Think of reconciliation like a doctor's visit. The patient (resource) has a desired state (healthy) and an actual state (sick). The doctor (reconciler) examines the patient and prescribes treatment to make the actual state match the desired state.

```go
// internal/controller/agent_controller.go
//
// This file implements the Reconciler for Agent resources.
// The Reconciler watches for Agent resources and ensures
// the actual state matches the desired state.
//
// DEEP DIVE: Why is Reconcile called with a Request, not the full Object?
// Because Kubernetes delivers events as "something changed for this object."
// The Request contains the Name and Namespace of the changed object.
// The controller then fetches the full object from the API server.
// This design means:
// 1. The controller always sees the latest version of the object
// 2. The controller doesn't need to handle stale caches
// 3. The reconciliation logic is always working with fresh data

package controller

import (
	"context"
	"fmt"
	"time"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
	"sigs.k8s.io/controller-runtime/pkg/log"

	configv1 "github.com/myorg/my-operator/internal/config"
)

const agentFinalizer = "agent.agnt.io/finalizer"

// AgentReconciler reconciles Agent objects
//
// The reconciler holds references to the API client and the scheme.
// These are injected by the manager when the controller is started.
//
// COMMON MISTAKE: Storing state in the reconciler struct.
// The reconciler struct should NOT hold state between reconciliations.
// Each reconciliation must be independent. If you store state,
// you'll have bugs when reconciliations overlap or retry.
type AgentReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=agnt.io,resources=agents,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=agnt.io,resources=agents/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=agnt.io,resources=agents/finalizers,verbs=update
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=core,resources=pods,verbs=get;list;watch

// Reconcile is the main reconciliation loop.
//
// It is called when:
// 1. An Agent resource is created
// 2. An Agent resource is updated
// 3. An Agent resource is deleted
// 4. A owned resource (Deployment, Pod) changes
// 5. The controller restarts (full resync)
//
// Parameters:
// - ctx: context for cancellation and deadlines
// - req: contains the Name and Namespace of the changed Agent
//
// Returns:
// - Result: whether to requeue and when
// - error: if reconciliation failed (causes automatic requeue)
//
// DEEP DIVE: The reconcile loop should be idempotent.
// This means calling Reconcile multiple times with the same
// Agent produces the same result. Kubernetes may deliver the
// same event multiple times, and the controller may restart
// and re-process old events. Idempotency prevents duplicate work.
func (r *AgentReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	// Get a logger scoped to this reconciliation
	// The logger automatically includes the Agent name and namespace
	logger := log.FromContext(ctx)

	// Step 1: Fetch the Agent resource
	// COMMON MISTAKE: Not checking if the Agent still exists.
	// The Agent may have been deleted between the event and this
	// reconciliation. Always check for NotFound errors.
	agent := &configv1.Agent{}
	if err := r.Get(ctx, req.NamespacedName, agent); err != nil {
		if errors.IsNotFound(err) {
			// Agent was deleted — nothing to reconcile
			// The finalizer handler will clean up owned resources
			logger.Info("Agent not found, may have been deleted")
			return ctrl.Result{}, nil
		}
		// Unexpected error — requeue with backoff
		return ctrl.Result{}, fmt.Errorf("failed to get Agent: %w", err)
	}

	// Step 2: Handle deletion with finalizers
	// DEEP DIVE: Why finalizers?
	// When you delete a Kubernetes resource, it's marked for deletion
	// but not actually removed until all finalizers are cleared.
	// This gives the controller a chance to clean up owned resources
	// (Deployments, Services, etc.) before the Agent is gone.
	// Without finalizers, deleting an Agent would orphan its Deployment.
	if !agent.ObjectMeta.DeletionTimestamp.IsZero() {
		return r.handleDeletion(ctx, agent)
	}

	// Step 3: Add finalizer if not present
	// COMMON MISTAKE: Adding the finalizer AFTER creating resources.
	// If the controller crashes between creating resources and adding
	// the finalizer, the Agent can be deleted without cleanup.
	// Always add the finalizer FIRST.
	if !controllerutil.ContainsFinalizer(agent, agentFinalizer) {
		controllerutil.AddFinalizer(agent, agentFinalizer)
		if err := r.Update(ctx, agent); err != nil {
			return ctrl.Result{}, fmt.Errorf("failed to add finalizer: %w", err)
		}
	}

	// Step 4: Reconcile the desired state
	result, err := r.reconcileAgent(ctx, agent)
	if err != nil {
		// Update Status to reflect the error
		// DEEP DIVE: Always update Status on error.
		// If you don't, the Status shows "Running" when the agent
		// is actually failing. Users see stale Status and don't
		// know there's a problem.
		r.updateStatus(ctx, agent, "Failed", err.Error())
		return ctrl.Result{RequeueAfter: 30 * time.Second}, nil
	}

	// Step 5: Update Status to reflect success
	r.updateStatus(ctx, agent, "Running", "Reconciliation successful")

	return result, nil
}

// reconcileAgent performs the actual reconciliation work.
// It ensures the Agent's Deployment exists and matches the desired state.
func (r *AgentReconciler) reconcileAgent(ctx context.Context, agent *configv1.Agent) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	// If the agent is disabled, ensure the Deployment is deleted
	if !agent.Spec.Enabled {
		logger.Info("Agent is disabled, ensuring Deployment is removed")
		return r.deleteDeployment(ctx, agent)
	}

	// Fetch or create the Deployment
	deployment := &appsv1.Deployment{}
	err := r.Get(ctx, types.NamespacedName{
		Name:      agent.Name,
		Namespace: agent.Namespace,
	}, deployment)

	if errors.IsNotFound(err) {
		// Deployment doesn't exist — create it
		logger.Info("Creating Deployment for Agent", "agent", agent.Name)
		deployment = r.buildDeployment(agent)
		if err := ctrl.SetControllerReference(agent, deployment, r.Scheme); err != nil {
			return ctrl.Result{}, fmt.Errorf("failed to set owner reference: %w", err)
		}
		if err := r.Create(ctx, deployment); err != nil {
			return ctrl.Result{}, fmt.Errorf("failed to create Deployment: %w", err)
		}
		// Requeue to check if the Deployment becomes ready
		return ctrl.Result{RequeueAfter: 10 * time.Second}, nil
	} else if err != nil {
		return ctrl.Result{}, fmt.Errorf("failed to get Deployment: %w", err)
	}

	// Deployment exists — check if it needs updating
	// COMMON MISTAKE: Not checking if the Deployment spec matches.
	// If you always create the Deployment, you'll get a conflict error.
	// If you never update it, changes to the Agent spec are ignored.
	// Always compare the current Deployment spec with the desired spec.
	if r.needsUpdate(deployment, agent) {
		logger.Info("Updating Deployment for Agent", "agent", agent.Name)
		updated := r.buildDeployment(agent)
		deployment.Spec = updated.Spec
		if err := r.Update(ctx, deployment); err != nil {
			return ctrl.Result{}, fmt.Errorf("failed to update Deployment: %w", err)}
		return ctrl.Result{RequeueAfter: 10 * time.Second}, nil
	}

	// Check if the Deployment is ready
	if deployment.Status.ReadyReplicas == *agent.Spec.Replicas {
		logger.Info("Agent is ready", "agent", agent.Name)
		return ctrl.Result{}, nil
	}

	// Deployment is not ready yet — requeue to check later
	logger.Info("Deployment not ready, requeuing", "agent", agent.Name,
		"ready", deployment.Status.ReadyReplicas,
		"desired", *agent.Spec.Replicas)
	return ctrl.Result{RequeueAfter: 10 * time.Second}, nil
}

// buildDeployment creates a Deployment spec from the Agent spec.
// This is where the desired state is translated into Kubernetes resources.
//
// DEEP DIVE: Why build a Deployment instead of a Pod directly?
// Deployments provide:
// - Automatic restart on failure
- Rolling updates for zero-downtime deployments
// - Replica management
// - Version history and rollback
// Pods are ephemeral — Deployments are the production choice.
func (r *AgentReconciler) buildDeployment(agent *configv1.Agent) *appsv1.Deployment {
	// Set default replicas if not specified
	replicas := int32(1)
	if agent.Spec.Replicas != nil {
		replicas = *agent.Spec.Replicas
	}

	// Build resource requirements
	resources := corev1.ResourceRequirements{}
	if agent.Spec.Resources.CPURequest != "" || agent.Spec.Resources.MemoryRequest != "" {
		resources.Requests = corev1.ResourceList{}
		if agent.Spec.Resources.CPURequest != "" {
			resources.Requests[corev1.ResourceCPU] = resource.MustParse(agent.Spec.Resources.CPURequest)
		}
		if agent.Spec.Resources.MemoryRequest != "" {
			resources.Requests[corev1.ResourceMemory] = resource.MustParse(agent.Spec.Resources.MemoryRequest)
		}
	}
	if agent.Spec.Resources.CPULimit != "" || agent.Spec.Resources.MemoryLimit != "" {
		resources.Limits = corev1.ResourceList{}
		if agent.Spec.Resources.CPULimit != "" {
			resources.Limits[corev1.ResourceCPU] = resource.MustParse(agent.Spec.Resources.CPULimit)
		}
		if agent.Spec.Resources.MemoryLimit != "" {
			resources.Limits[corev1.ResourceMemory] = resource.MustParse(agent.Spec.Resources.MemoryLimit)
		}
	}

	return &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      agent.Name,
			Namespace: agent.Namespace,
			Labels: map[string]string{
				"app.kubernetes.io/name":       "agent",
				"app.kubernetes.io/instance":   agent.Name,
				"app.kubernetes.io/managed-by": "agent-operator",
			},
		},
		Spec: appsv1.DeploymentSpec{
			Replicas: &replicas,
			Selector: &metav1.LabelSelector{
				MatchLabels: map[string]string{
					"app.kubernetes.io/name":     "agent",
					"app.kubernetes.io/instance": agent.Name,
				},
			},
			Template: corev1.PodTemplateSpec{
				ObjectMeta: metav1.ObjectMeta{
					Labels: map[string]string{
						"app.kubernetes.io/name":     "agent",
						"app.kubernetes.io/instance": agent.Name,
					},
				},
				Spec: corev1.PodSpec{
					Containers: []corev1.Container{
						{
							Name:      "agent",
							Image:     agent.Spec.Image,
							Resources: resources,
							Env: []corev1.EnvVar{
								{
									Name:  "AGENT_MODEL",
									Value: agent.Spec.Model,
								},
								{
									Name:  "AGENT_NAME",
									Value: agent.Name,
								},
							},
						},
					},
				},
			},
		},
	}
}

// needsUpdate checks if the Deployment needs to be updated.
// Returns true if the Deployment spec doesn't match the Agent spec.
//
// COMMON MISTAKE: Comparing entire Deployment objects.
// This is fragile — Kubernetes adds fields like ResourceVersion
// and UID that change on every update. Compare only the fields
// you care about (image, replicas, resources).
func (r *AgentReconciler) needsUpdate(deployment *appsv1.Deployment, agent *configv1.Agent) bool {
	// Check if replicas match
	if deployment.Spec.Replicas == nil || *deployment.Spec.Replicas != *agent.Spec.Replicas {
		return true
	}

	// Check if image matches
	if len(deployment.Spec.Template.Spec.Containers) == 0 {
		return true
	}
	if deployment.Spec.Template.Spec.Containers[0].Image != agent.Spec.Image {
		return true
	}

	// Check if model env var matches
	for _, env := range deployment.Spec.Template.Spec.Containers[0].Env {
		if env.Name == "AGENT_MODEL" && env.Value != agent.Spec.Model {
			return true
		}
	}

	return false
}

// deleteDeployment removes the Deployment owned by this Agent.
// Returns a Result that doesn't requeue (the Agent is being deleted).
func (r *AgentReconciler) deleteDeployment(ctx context.Context, agent *configv1.Agent) (ctrl.Result, error) {
	deployment := &appsv1.Deployment{}
	err := r.Get(ctx, types.NamespacedName{
		Name:      agent.Name,
		Namespace: agent.Namespace,
	}, deployment)

	if errors.IsNotFound(err) {
		// Deployment already deleted — nothing to do
		return ctrl.Result{}, nil
	} else if err != nil {
		return ctrl.Result{}, fmt.Errorf("failed to get Deployment for deletion: %w", err)
	}

	if err := r.Delete(ctx, deployment); err != nil {
		return ctrl.Result{}, fmt.Errorf("failed to delete Deployment: %w", err)
	}

	return ctrl.Result{}, nil
}

// handleDeletion cleans up owned resources when an Agent is deleted.
// This is called when the Agent has a deletion timestamp.
func (r *AgentReconciler) handleDeletion(ctx context.Context, agent *configv1.Agent) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	// Check if the finalizer is present
	if controllerutil.ContainsFinalizer(agent, agentFinalizer) {
		// Clean up owned resources
		if err := r.deleteDeployment(ctx, agent); err != nil {
			return ctrl.Result{}, fmt.Errorf("failed to delete Deployment during deletion: %w", err)
		}

		// Remove the finalizer to allow deletion to proceed
		// COMMON MISTAKE: Forgetting to remove the finalizer.
		// Without removing it, the Agent will be stuck in "Terminating"
		// state forever. Kubernetes waits for all finalizers to be
		// cleared before actually deleting the resource.
		controllerutil.RemoveFinalizer(agent, agentFinalizer)
		if err := r.Update(ctx, agent); err != nil {
			return ctrl.Result{}, fmt.Errorf("failed to remove finalizer: %w", err)
		}
	}

	logger.Info("Agent deletion handled successfully", "agent", agent.Name)
	return ctrl.Result{}, nil
}

// updateStatus updates the Agent's Status subresource.
// This is called after every reconciliation to reflect the current state.
//
// DEEP DIVE: Why use the Status subresource?
// Kubernetes separates Spec (desired state) from Status (actual state).
// Updating Status doesn't trigger another reconciliation (with the
// /status subresource). This prevents infinite reconciliation loops.
func (r *AgentReconciler) updateStatus(ctx context.Context, agent *configv1.Agent, phase string, message string) {
	agent.Status.Phase = phase
	agent.Status.Message = message
	now := metav1.Now()
	agent.Status.LastReconciledAt = &now

	if err := r.Status().Update(ctx, agent); err != nil {
		log.FromContext(ctx).Error(err, "failed to update Agent status")
	}
}

// SetupWithManager registers the controller with the manager.
// This is called from main.go to wire up the controller.
func (r *AgentReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&configv1.Agent{}).
		Owns(&appsv1.Deployment{}).
		Complete(r)
}
```

---

## Part 3: The Manager

### What Is the Manager?

The Manager is the entry point for controller-runtime. It:
1. Starts all controllers
2. Runs the webhook server (if configured)
3. Manages the informer cache (watches resources)
4. Handles graceful shutdown
5. Coordinates leader election

Think of the Manager as the conductor of an orchestra. It doesn't play any instrument, but it coordinates all the musicians (controllers) and ensures they play in harmony.

```go
// cmd/main.go
//
// The entry point for the operator.
// This file is minimal — it just sets up the Manager and starts it.
//
// DEEP DIVE: Why is main.go so short?
// Because all the logic lives in the controller and config packages.
// main.go only handles:
// 1. Parsing command-line flags
// 2. Setting up the Manager
// 3. Registering controllers
// 4. Starting the Manager
// This separation makes the operator testable — you can test
// the controller without running the full Manager.

package main

import (
	"flag"
	"os"

	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	_ "k8s.io/client-go/plugin/pkg/client/auth"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/healthz"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"
	metricsserver "sigs.k8s.io/controller-runtime/pkg/metrics/server"

	configv1 "github.com/myorg/my-operator/internal/config"
	"github.com/myorg/my-operator/internal/controller"
)

var (
	scheme   = runtime.NewScheme()
	setupLog = ctrl.Log.WithName("setup")
)

func init() {
	// Register all the types the operator needs to work with
	// DEEP DIVE: The scheme is a registry of all known types.
	// When the API server returns a resource, the scheme knows
	// how to deserialize it into the correct Go struct.
	// clientgoscheme adds all built-in Kubernetes types (Pods, Deployments, etc.)
	// configv1 adds our custom Agent type.
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(configv1.AddToScheme(scheme))
}

func main() {
	// Parse command-line flags
	var metricsAddr string
	var enableLeaderElection bool
	var probeAddr string

	flag.StringVar(&metricsAddr, "metrics-bind-address", ":8080", "The address the metric endpoint binds to.")
	flag.StringVar(&probeAddr, "health-probe-bind-address", ":8081", "The address the probe endpoint binds to.")
	flag.BoolVar(&enableLeaderElection, "leader-elect", false,
		"Enable leader election for controller manager.")
	flag.Parse()

	// Set up the logger
	// DEEP DIVE: Zap is the recommended logger for controller-runtime.
	// It's fast, structured, and handles JSON output for production.
	// For development, use the development flag for human-readable output.
	ctrl.SetLogger(zap.New(zap.UseDevMode(true)))

	// Create the Manager
	// DEEP DIVE: The Manager configuration options:
	// - Scheme: registry of all known types
	// - MetricsBindAddress: where to expose Prometheus metrics
	// - ProbeBindAddress: where to expose health/readiness probes
	// - LeaderElection: ensure only one instance is active
	// - LeaderElectionNamespace: where to store the leader lock
	//
	// COMMON MISTAKE: Not enabling leader election in production.
	// Without it, all operator instances try to reconcile simultaneously.
	// This causes duplicate work and potential conflicts.
	// Always enable leader election when running multiple replicas.
	mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
		Scheme: scheme,
		Metrics: metricsserver.Options{
			BindAddress: metricsAddr,
		},
		HealthProbeBindAddress: probeAddr,
		LeaderElection:         enableLeaderElection,
		LeaderElectionID:       "agent-operator-lock",
	})
	if err != nil {
		setupLog.Error(err, "unable to start manager")
		os.Exit(1)
	}

	// Set up the Agent controller
	// DEEP DIVE: SetupWithManager registers the controller with the Manager.
	// The Manager will:
	// 1. Create an informer that watches Agent resources
	// 2. Create an informer that watches Deployments (owned by Agents)
	// 3. Start the reconcile loop when changes are detected
	// 4. Handle graceful shutdown when the operator is stopped
	if err = (&controller.AgentReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "unable to create controller", "controller", "Agent")
		os.Exit(1)
	}

	// Add health and readiness probes
	// DEEP DIVE: Kubernetes uses probes to check if your operator is healthy.
	// - Healthz: is the operator running?
	// - Readyz: is the operator ready to serve requests?
	// If the operator fails health checks, Kubernetes restarts it.
	if err := mgr.AddHealthzRoute("healthz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up health check")
		os.Exit(1)
	}
	if err := mgr.AddReadyzRoute("readyz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up ready check")
		os.Exit(1)
	}

	// Start the Manager
	// This blocks until the operator receives a shutdown signal (SIGTERM, SIGINT).
	// The Manager handles graceful shutdown of all controllers.
	setupLog.Info("starting manager")
	if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		setupLog.Error(err, "problem running manager")
		os.Exit(1)
	}
}
```

---

## Part 4: Informers — How Kubernetes Watches Work

### The Watch Mechanism

Informers are how Kubernetes watches for resource changes. Instead of polling the API server (which would be slow and wasteful), informers maintain a local cache that's updated in real-time via watches.

Think of it like a news subscription. Instead of checking the news website every minute (polling), you subscribe and get notifications when something new happens (watching).

```
API Server → Watch → Informer → Local Cache → Controller
    ↑                                        ↓
    └──────────── Reconcile ←──────────── Event
```

### How Informers Work

1. **List**: On startup, the informer lists ALL resources of a type
2. **Watch**: After listing, the informer opens a watch connection
3. **Cache**: The informer maintains a local cache of all resources
4. **Event**: When a resource changes, the informer fires an event
5. **Reconcile**: The controller's reconcile function is called

```go
// DEEP DIVE: Informer lifecycle
//
// 1. Manager starts the informer
// 2. Informer does a full LIST of all Agent resources
// 3. Informer opens a WATCH connection to the API server
// 4. API server sends events (ADDED, MODIFIED, DELETED) as they happen
// 5. Informer updates its local cache
// 6. Informer fires the event handler (EnqueueRequestForObject)
// 7. The event handler adds the changed object's key to the work queue
// 8. The controller's Reconcile function is called with the key
// 9. Reconcile fetches the object from the cache (not the API server)
//
// COMMON MISTAKE: Fetching from the API server instead of the cache.
// The cache is up-to-date and much faster. The API server is a
// bottleneck. Use r.Get() which reads from the cache, not direct
// API calls which hit the server.
//
// DEEP DIVE: Why is the cache important?
// Without the cache, every reconciliation would need to call the
// API server to get the current state. With thousands of resources,
// this would overload the API server. The cache reduces API server
// load by 99% or more.
```

---

## Part 5: Leader Election

### Why Leader Election?

When you deploy an operator to Kubernetes, you might run multiple replicas for high availability. But you don't want all replicas reconciling simultaneously — that causes duplicate work and potential conflicts.

Leader election ensures only ONE replica is active at a time. The others are standby — ready to take over if the leader dies.

Think of it like a sports team. You have multiple players, but only one is the captain. The captain makes decisions. If the captain gets injured, another player becomes captain.

```go
// DEEP DIVE: How leader election works
//
// 1. The operator starts and tries to acquire a lock
// 2. The lock is stored in a ConfigMap in the kube-system namespace
// 3. The first operator to acquire the lock becomes the leader
// 4. The leader starts all controllers
// 5. Other operators wait and periodically try to acquire the lock
// 6. If the leader dies (pod crash, node failure), the lock expires
// 7. Another operator acquires the lock and becomes the new leader
// 8. The new leader starts all controllers
//
// COMMON MISTAKE: Not using leader election in production.
// Without it, multiple operator instances reconcile simultaneously.
// This causes:
// - Duplicate work (wasted CPU)
// - Race conditions (two operators modifying the same resource)
// - Inconsistent state (different operators see different versions)
//
// DEEP DIVE: Lock duration vs check interval
// - Lease duration: how long the lock is held (default: 15 seconds)
// - Renew deadline: how often the leader renews the lock (default: 10 seconds)
// - Retry period: how often standbys try to acquire the lock (default: 2 seconds)
//
// If the leader crashes, the lock expires after (Lease duration - Renew deadline).
// With defaults, that's 5 seconds. During those 5 seconds, no reconciliation
// happens. This is the trade-off: faster failover vs more frequent lock renewals.
```

---

## Part 6: Using the Operator

### Create the CRD

```bash
# Generate the CRD YAML from the Go types
make generate
make manifests

# Apply the CRD to your cluster
kubectl apply -f config/crd/agents.agnt.io.yaml
```

### Deploy the Operator

```bash
# Build and push the operator image
make docker-build IMG=my-registry/agent-operator:v1
make docker-push IMG=my-registry/agent-operator:v1

# Deploy to Kubernetes
make deploy IMG=my-registry/agent-operator:v1
```

### Create an Agent Resource

```yaml
# agent.yaml
apiVersion: agnt.io/v1
kind: Agent
metadata:
  name: sensor-agent-1
  namespace: default
spec:
  image: my-registry/agent:latest
  replicas: 3
  model: gpt-4
  enabled: true
  resources:
    cpuRequest: "100m"
    memoryRequest: "128Mi"
    cpuLimit: "500m"
    memoryLimit: "512Mi"
```

```bash
# Apply the Agent resource
kubectl apply -f agent.yaml

# Watch the Agent status
kubectl get agents -w

# Check the Deployment created by the operator
kubectl get deployments
kubectl get pods -l app.kubernetes.io/name=agent
```

---

## Key Takeaways

1. **controller-runtime** is the CNCF standard. Every production K8s operator uses it. Learn it once, use it everywhere.

2. **Reconciler** is the core interface. It's called when something changes and must be idempotent. Always check for errors and update Status.

3. **CRDs** extend the Kubernetes API. Use the Spec/Status pattern — Spec for desired state, Status for actual state.

4. **Manager** runs everything. It handles controllers, webhooks, caches, and leader election. main.go should be minimal.

5. **Informers** provide real-time watches with local caching. Don't poll the API server — use the cache.

6. **Leader election** ensures only one operator instance is active. Always enable it in production.

---

## What's Next

In Module 12, you'll learn how to instrument your Go services with Prometheus metrics. The RED metrics pattern (Rate, Errors, Duration) gives you observability into your operator's performance.
