SRE
# 🌋 Cloud-Native Kubernetes Chaos Engineering & Resiliency Lab

A production-ready, automated continuous resilience framework designed to systematically inject operational failure modes (compute exhaustion, network degradation, state eviction) into live Kubernetes clusters using LitmusChaos primitives, evaluate impact against architectural SLO thresholds via PromQL telemetry hooks, and generate deterministic compliance reports.

---

## 🏗️ Chaos Engineering Architecture

The framework implements a programmatic **Steady-State Hypothesis** validation model. It programmatically isolates failure domains, monitors downstream system recovery behaviors, and maps results to actionable metrics:

* **Experiment Orchestrator:** Python 3 (Thread-safe subprocess execution layer with custom exception containment).
* **Fault Injection Primitives:** LitmusChaos CRDs (`ChaosEngine`, `ChaosExperiment` custom resources).
* **Telemetry Telemetry Feedback Loop:** Prometheus TSDB scraping specialized namespace infrastructure metrics.
* **Workload Layer:** Isolated targets executing under explicit Horizontal Pod Autoscaler (HPA) validation contracts.

---

## 📉 Automated Experiments & Core Hypotheses

The automation runner systematically deploys four specialized architectural failure modes, testing cluster behavior against real-world degradation states:

| Experiment Name | Chaos Mechanism | Target Component | Success Criteria (SLO Target) | Steady-State Hypothesis |
| :--- | :--- | :--- | :--- | :--- |
| **`pod-delete`** | Instant execution pod eviction | ReplicaSet / Deployment | Error Rate less than 1.0% | K8s control loops immediately reschedule instances; traffic transitions seamlessly. |
| **`network-latency`** | Inject 200ms transit delays | Pod Network Namespace | p99 Response less than 1.0s | Upstream HTTP client connection pooling and timeout configurations absorb transit drops. |
| **`cpu-hog`** | Core resource exhaustion (80%) | Container cgroups limit | Error Rate less than 1.0% | Target HPA identifies resource breach and triggers scale-up behaviors within 120s. |
| **`network-loss`** | 10% packet drops across routing | Virtual Ethernet Interfaces | Error Rate less than 0.5% | Resilient application retry mechanisms and circuit-breakers handle raw package loss. |

---

## 🛠️ Resilient System Software Engineering Standards Applied

To ensure this framework can run continuously as an out-of-band automated validation suite (e.g., via a GitOps delivery workflow or weekly cron execution loop), the following software engineering paradigms were implemented:

* **🛡️ Subprocess Failure Domain Containment:** The script isolates the execution of `kubectl` host commands. If the cluster control plane is temporarily unreachable or throws permissions drops, the application handles errors gracefully instead of executing a blind panic.
* **🎯 Dynamically Isolated Configuration Matrix:** Replaced rigid, hardcoded string architectures with flexible environment variable mappings (`PROMETHEUS_URL`, `TARGET_NAMESPACE`), making the test suite universally portable across staging, sandbox, and integration environments.
* **🪵 Standardized Ingestible Logging Logs:** Built entirely using standard thread-safe Python `logging` formatters streaming directly to `stdout`. This facilitates clean ingestion for modern centralized observability platforms.
* **⏱️ Precise Microsecond Windows:** Uses strict `datetime.utcnow()` differential delta computations rather than primitive integer counters, tracking system stabilization times down to exact microsecond metrics.

---

## 🚀 Getting Started & Staging Execution

### 1. Requirements
* Kubernetes Cluster (minikube, EKS, GKE) with the LitmusChaos Operator installed.
* Python 3.8+ with local Docker platform desktop utilities.

### 2. Sandbox Testing Isolation
Execute the validation suite cleanly inside an isolated container workspace to bypass local path mapping edge-cases on host systems:

```bash
MSYS_NO_PATHCONV=1 docker run --rm \
  -v "$PWD":/app \
  -w /app \



export PROMETHEUS_URL="[http://prometheus-k8s.monitoring.svc.cluster.local:9090](http://prometheus-k8s.monitoring.svc.cluster.local:9090)"
export TARGET_NAMESPACE="production-payment-processing"



.
├── .gitignore                      # Enforces clean version tracking hygiene
├── README.md                       # Core System Architectural Manual
├── requirements.txt                # System dependency configuration targets
├── experiments/
│   ├── cpu-hog.yaml                # Resource depletion attack definitions
│   ├── network-latency.yaml        # Network transport latency parameters
│   ├── network-loss.yaml           # Structural network drop declarations
│   └── pod-delete.yaml             # Pod eviction engine manifests
└── scripts/
    └── chaos_runner.py             # Main resilient automated execution tracker
  --network="host" \
  python:3.10-slim \
  bash -c "pip install -r requirements.txt && python scripts/chaos_runner.py"
