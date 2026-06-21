# Module 11 Exercise: Go K8s Operators

## What You'll Practice

By completing this exercise, you'll build an **Agent CRD operator** that:

1. Defines an Agent CRD with Spec and Status
2. Implements a Reconciler that ensures desired state matches actual state
3. Creates and manages Deployments for each Agent resource
4. Handles deletion with finalizers
5. Supports leader election for high availability

This is a real-world Kubernetes operator — the same pattern used by every CNCF project.

---

## Part 1: CRD Type Definitions

Define the Agent CRD types.

### Starter Code

```go
// internal/config/agent_types.go
//
// Define the Agent CRD types.
// These types are used by controller-runtime to generate
// the CRD YAML and to deserialize Agent resources.

package config

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// AgentSpec defines the desired state of Agent
type AgentSpec struct {
	// TODO: Add Image field (string, required)
	// Hint: +kubebuilder:validation:Required

	// TODO: Add Replicas field (*int32, optional, default 1)
	// Hint: +kubebuilder:validation:Minimum=1
	// Hint: +kubebuilder:validation:Maximum=10
	// Hint: +kubebuilder:default=1

	// TODO: Add Model field (string, required)
	// Hint: +kubebuilder:validation:Enum=gpt-4;gpt-3.5-turbo;claude-3

	// TODO: Add Enabled field (bool, optional, default true)
	// Hint: +kubebuilder:default=true
}

// AgentStatus defines the observed state of Agent
type AgentStatus struct {
	// TODO: Add Phase field (string)
	// Hint: +kubebuilder:validation:Enum=Pending;Running;Failed;Stopped

	// TODO: Add ReadyReplicas field (int32)

	// TODO: Add Message field (string)

	// TODO: Add LastReconciledAt field (*metav1.Time)
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// TODO: Add printcolumn annotations for Phase, Ready, and Age

// Agent is the Schema for the agents API
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

### Hints

1. Use `*int32` for optional numeric fields (allows nil)
2. Use `+kubebuilder:default=value` to set defaults
3. Use `+kubebuilder:validation:Enum=a;b;c` to restrict values
4. Always add `+kubebuilder:subresource:status` to enable the Status subresource

---

## Part 2: The Reconciler

Implement the core reconciliation logic.

### Starter Code

```go
// internal/controller/agent_controller.go
//
// Implement the Reconciler for Agent resources.

package controller

import (
	"context"
	"fmt"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/types"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
	"sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"

	configv1 "github.com/myorg/my-operator/internal/config"
)

const agentFinalizer = "agent.agnt.io/finalizer"

type AgentReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=agnt.io,resources=agents,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=agnt.io,resources=agents/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=agnt.io,resources=agents/finalizers,verbs=update
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete

// TODO: Implement Reconcile method
// Steps:
// 1. Fetch the Agent resource (handle NotFound)
// 2. Handle deletion with finalizers
// 3. Add finalizer if not present
// 4. Reconcile the desired state (create/update Deployment)
// 5. Update Status
//
// COMMON MISTAKE: Not checking if the Agent still exists.
// The Agent may have been deleted between the event and this
// reconciliation. Always check for NotFound errors.

// TODO: Implement buildDeployment method
// Create a Deployment spec from the Agent spec
// Include:
// - Correct replicas
// - Container image
// - Environment variables (AGENT_MODEL, AGENT_NAME)
// - Resource requests and limits
// - Labels for selection

// TODO: Implement needsUpdate method
// Compare Deployment spec with Agent spec
// Return true if they differ
// Compare: replicas, image, model env var

// TODO: Implement handleDeletion method
// Clean up owned resources and remove finalizer
// COMMON MISTAKE: Forgetting to remove the finalizer.
// Without it, the Agent will be stuck in "Terminating" forever.

// TODO: Implement updateStatus method
// Update the Agent's Status subresource
// Set Phase, Message, LastReconciledAt

// TODO: Implement SetupWithManager method
// Register the controller with the manager
// Watch Agent resources and owned Deployments
// Hint: ctrl.NewControllerManagedBy(mgr).For(&configv1.Agent{}).Owns(&appsv1.Deployment{}).Complete(r)
```

### Hints

1. Use `r.Get(ctx, req.NamespacedName, agent)` to fetch the Agent
2. Use `errors.IsNotFound(err)` to check if the resource was deleted
3. Use `controllerutil.AddFinalizer` and `controllerutil.RemoveFinalizer`
4. Use `ctrl.SetControllerReference` to set owner references on Deployments
5. Use `r.Status().Update(ctx, agent)` to update the Status subresource

---

## Part 3: The Manager

Set up the Manager in main.go.

### Starter Code

```go
// cmd/main.go
//
// Set up the Manager and start the operator.

package main

import (
	"flag"
	"os"

	"k8s.io/apimachinery/pkg/runtime"
	utilruntime "k8s.io/apimachinery/pkg/util/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
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
	// TODO: Register schemes
	// Hint: utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	// Hint: utilruntime.Must(configv1.AddToScheme(scheme))
}

func main() {
	// TODO: Parse command-line flags
	// - metricsAddr (default ":8080")
	// - probeAddr (default ":8081")
	// - enableLeaderElection (default false)

	// TODO: Set up logger
	// Hint: ctrl.SetLogger(zap.New(zap.UseDevMode(true)))

	// TODO: Create the Manager
	// Use ctrl.NewManager with:
	// - Scheme
	// - MetricsBindAddress
	// - HealthProbeBindAddress
	// - LeaderElection
	// - LeaderElectionID: "agent-operator-lock"
	//
	// COMMON MISTAKE: Not enabling leader election in production.
	// Without it, all operator instances reconcile simultaneously.

	// TODO: Set up the Agent controller
	// Create AgentReconciler with Client and Scheme
	// Call SetupWithManager

	// TODO: Add health and readiness probes
	// Hint: mgr.AddHealthzRoute("healthz", healthz.Ping)
	// Hint: mgr.AddReadyzRoute("readyz", healthz.Ping)

	// TODO: Start the Manager
	// Hint: mgr.Start(ctrl.SetupSignalHandler())
}
```

### Hints

1. Use `flag.StringVar` to define flags
2. Use `ctrl.NewManager` to create the manager
3. Use `mgr.GetClient()` to get the API client
4. Use `mgr.GetScheme()` to get the scheme
5. Use `mgr.Start(ctrl.SetupSignalHandler())` to start the manager

---

## Part 4: Testing Locally

To test the operator locally without a real cluster:

```bash
# Install kind (Kubernetes in Docker)
go install sigs.k8s.io/kind@latest

# Create a kind cluster
kind create cluster --name agent-test

# Install the CRD
kubectl apply -f config/crd/agents.agnt.io.yaml

# Run the operator locally (outside the cluster)
go run cmd/main.go --kubeconfig=$HOME/.kube/config

# In another terminal, create an Agent resource
kubectl apply -f agent.yaml

# Watch the Agent status
kubectl get agents -w

# Check the Deployment
kubectl get deployments
kubectl get pods
```

---

## Solutions

### Solution: agent_types.go

```go
package config

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

type AgentSpec struct {
	// Image is the container image to run for this agent
	// +kubebuilder:validation:Required
	Image string `json:"image"`

	// Replicas is the number of agent instances to run
	// +kubebuilder:validation:Minimum=1
	// +kubebuilder:validation:Maximum=10
	// +kubebuilder:default=1
	Replicas *int32 `json:"replicas,omitempty"`

	// Model specifies the AI model this agent uses
	// +kubebuilder:validation:Enum=gpt-4;gpt-3.5-turbo;claude-3
	Model string `json:"model"`

	// Enabled determines if the agent should be running
	// +kubebuilder:default=true
	Enabled bool `json:"enabled,omitempty"`
}

type AgentStatus struct {
	// Phase represents the current lifecycle phase
	// +kubebuilder:validation:Enum=Pending;Running;Failed;Stopped
	Phase string `json:"phase,omitempty"`

	// ReadyReplicas is the number of ready instances
	ReadyReplicas int32 `json:"readyReplicas,omitempty"`

	// Message provides a human-readable status message
	Message string `json:"message,omitempty"`

	// LastReconciledAt is the time of the last reconciliation
	LastReconciledAt *metav1.Time `json:"lastReconciledAt,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:printcolumn:name="Phase",type=string,JSONPath=`.status.phase`
// +kubebuilder:printcolumn:name="Ready",type=integer,JSONPath=`.status.readyReplicas`
// +kubebuilder:printcolumn:name="Age",type=date,JSONPath=`.metadata.creationTimestamp`

type Agent struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   AgentSpec   `json:"spec,omitempty"`
	Status AgentStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

type AgentList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []Agent `json:"items"`
}
```

### Solution: agent_controller.go

```go
package controller

import (
	"context"
	"fmt"

	appsv1 "k8s.io/api/apps/v1"
	corev1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
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

type AgentReconciler struct {
	client.Client
	Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=agnt.io,resources=agents,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=agnt.io,resources=agents/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=agnt.io,resources=agents/finalizers,verbs=update
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete

func (r *AgentReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
	logger := log.FromContext(ctx)

	// Step 1: Fetch the Agent resource
	agent := &configv1.Agent{}
	if err := r.Get(ctx, req.NamespacedName, agent); err != nil {
		if errors.IsNotFound(err) {
			logger.Info("Agent not found, may have been deleted")
			return ctrl.Result{}, nil
		}
		return ctrl.Result{}, fmt.Errorf("failed to get Agent: %w", err)
	}

	// Step 2: Handle deletion with finalizers
	if !agent.ObjectMeta.DeletionTimestamp.IsZero() {
		return r.handleDeletion(ctx, agent)
	}

	// Step 3: Add finalizer if not present
	if !controllerutil.ContainsFinalizer(agent, agentFinalizer) {
		controllerutil.AddFinalizer(agent, agentFinalizer)
		if err := r.Update(ctx, agent); err != nil {
			return ctrl.Result{}, fmt.Errorf("failed to add finalizer: %w", err)
		}
	}

	// Step 4: Reconcile the desired state
	if !agent.Spec.Enabled {
		return r.deleteDeployment(ctx, agent)
	}

	deployment := &appsv1.Deployment{}
	err := r.Get(ctx, types.NamespacedName{
		Name:      agent.Name,
		Namespace: agent.Namespace,
	}, deployment)

	if errors.IsNotFound(err) {
		// Create the Deployment
		deployment = r.buildDeployment(agent)
		if err := ctrl.SetControllerReference(agent, deployment, r.Scheme); err != nil {
			return ctrl.Result{}, fmt.Errorf("failed to set owner reference: %w", err)
		}
		if err := r.Create(ctx, deployment); err != nil {
			return ctrl.Result{}, fmt.Errorf("failed to create Deployment: %w", err)
		}
		return ctrl.Result{RequeueAfter: 10 * 1e9}, nil
	} else if err != nil {
		return ctrl.Result{}, fmt.Errorf("failed to get Deployment: %w", err)
	}

	// Update if needed
	if r.needsUpdate(deployment, agent) {
		updated := r.buildDeployment(agent)
		deployment.Spec = updated.Spec
		if err := r.Update(ctx, deployment); err != nil {
			return ctrl.Result{}, fmt.Errorf("failed to update Deployment: %w", err)
		}
		return ctrl.Result{RequeueAfter: 10 * 1e9}, nil
	}

	// Step 5: Update Status
	r.updateStatus(ctx, agent, "Running", "Reconciliation successful")

	return ctrl.Result{}, nil
}

func (r *AgentReconciler) buildDeployment(agent *configv1.Agent) *appsv1.Deployment {
	replicas := int32(1)
	if agent.Spec.Replicas != nil {
		replicas = *agent.Spec.Replicas
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
							Name:  "agent",
							Image: agent.Spec.Image,
							Env: []corev1.EnvVar{
								{Name: "AGENT_MODEL", Value: agent.Spec.Model},
								{Name: "AGENT_NAME", Value: agent.Name},
							},
						},
					},
				},
			},
		},
	}
}

func (r *AgentReconciler) needsUpdate(deployment *appsv1.Deployment, agent *configv1.Agent) bool {
	if deployment.Spec.Replicas == nil || *deployment.Spec.Replicas != *agent.Spec.Replicas {
		return true
	}
	if len(deployment.Spec.Template.Spec.Containers) == 0 {
		return true
	}
	if deployment.Spec.Template.Spec.Containers[0].Image != agent.Spec.Image {
		return true
	}
	return false
}

func (r *AgentReconciler) handleDeletion(ctx context.Context, agent *configv1.Agent) (ctrl.Result, error) {
	if controllerutil.ContainsFinalizer(agent, agentFinalizer) {
		if err := r.deleteDeployment(ctx, agent); err != nil {
			return ctrl.Result{}, err
		}
		controllerutil.RemoveFinalizer(agent, agentFinalizer)
		if err := r.Update(ctx, agent); err != nil {
			return ctrl.Result{}, fmt.Errorf("failed to remove finalizer: %w", err)
		}
	}
	return ctrl.Result{}, nil
}

func (r *AgentReconciler) deleteDeployment(ctx context.Context, agent *configv1.Agent) (ctrl.Result, error) {
	deployment := &appsv1.Deployment{}
	err := r.Get(ctx, types.NamespacedName{
		Name:      agent.Name,
		Namespace: agent.Namespace,
	}, deployment)

	if errors.IsNotFound(err) {
		return ctrl.Result{}, nil
	} else if err != nil {
		return ctrl.Result{}, fmt.Errorf("failed to get Deployment: %w", err)
	}

	if err := r.Delete(ctx, deployment); err != nil {
		return ctrl.Result{}, fmt.Errorf("failed to delete Deployment: %w", err)
	}

	return ctrl.Result{}, nil
}

func (r *AgentReconciler) updateStatus(ctx context.Context, agent *configv1.Agent, phase string, message string) {
	agent.Status.Phase = phase
	agent.Status.Message = message
	now := metav1.Now()
	agent.Status.LastReconciledAt = &now

	if err := r.Status().Update(ctx, agent); err != nil {
		log.FromContext(ctx).Error(err, "failed to update Agent status")
	}
}

func (r *AgentReconciler) SetupWithManager(mgr ctrl.Manager) error {
	return ctrl.NewControllerManagedBy(mgr).
		For(&configv1.Agent{}).
		Owns(&appsv1.Deployment{}).
		Complete(r)
}
```

### Solution: main.go

```go
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
	utilruntime.Must(clientgoscheme.AddToScheme(scheme))
	utilruntime.Must(configv1.AddToScheme(scheme))
}

func main() {
	var metricsAddr string
	var enableLeaderElection bool
	var probeAddr string

	flag.StringVar(&metricsAddr, "metrics-bind-address", ":8080", "The address the metric endpoint binds to.")
	flag.StringVar(&probeAddr, "health-probe-bind-address", ":8081", "The address the probe endpoint binds to.")
	flag.BoolVar(&enableLeaderElection, "leader-elect", false, "Enable leader election for controller manager.")
	flag.Parse()

	ctrl.SetLogger(zap.New(zap.UseDevMode(true)))

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

	if err = (&controller.AgentReconciler{
		Client: mgr.GetClient(),
		Scheme: mgr.GetScheme(),
	}).SetupWithManager(mgr); err != nil {
		setupLog.Error(err, "unable to create controller", "controller", "Agent")
		os.Exit(1)
	}

	if err := mgr.AddHealthzRoute("healthz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up health check")
		os.Exit(1)
	}
	if err := mgr.AddReadyzRoute("readyz", healthz.Ping); err != nil {
		setupLog.Error(err, "unable to set up ready check")
		os.Exit(1)
	}

	setupLog.Info("starting manager")
	if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
		setupLog.Error(err, "problem running manager")
		os.Exit(1)
	}
}
```
