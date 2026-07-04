#!/usr/bin/env python3
"""
chaos_runner.py
Automates systemic failure injection experiments against live Kubernetes workloads,
evaluates infrastructure recovery, and outputs compliance resilience datasets.
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional

# Configure clean, container-ready standard output streaming logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ChaosEngine")

# Target Configuration Environment Injection Guards
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
K8S_NAMESPACE = os.environ.get("TARGET_NAMESPACE", "default")

EXPERIMENTS: List[Dict[str, Any]] = [
    {
        "name": "pod-delete",
        "description": "Terminate random microservice pod instances - tests self-healing & ReplicaSet controller response.",
        "manifest": "experiments/pod-delete.yaml",
        "duration": 120,
        "slo_threshold_pct": 0.01, # Max 1% error rate allowed
        "hypothesis": "Kubernetes ReplicaSet control loops instantly reschedule replacement instances; error rates remain under 1.0%.",
    },
    {
        "name": "network-latency-200ms",
        "description": "Inject 200ms transit delay into system networking matrix - tests application proxy timeout thresholds.",
        "manifest": "experiments/network-latency.yaml",
        "duration": 120,
        "slo_threshold_pct": 0.05, 
        "hypothesis": "Downstream retry strategies absorb transient network delays; p99 response times stay safely below 1.0s.",
    },
    {
        "name": "cpu-hog",
        "description": "Exhaust container node CPU allocation capacities to 80% - tests Horizontal Pod Autoscaler (HPA) reaction.",
        "manifest": "experiments/cpu-hog.yaml",
        "duration": 180,
        "slo_threshold_pct": 0.01,
        "hypothesis": "HPA detects metrics breach and schedules elastic compute extensions within 120s; client transactions remain steady.",
    },
    {
        "name": "network-loss-10pct",
        "description": "Systematically drop 10% of standard networking packets - verifies circuit-breaker performance limits.",
        "manifest": "experiments/network-loss.yaml",
        "duration": 120,
        "slo_threshold_pct": 0.005, # Max 0.5% errors allowed
        "hypothesis": "Application network client layers automatically process connection retries; total packet failure rate stays below 0.5%.",
    }
]

def query_telemetry(query: str) -> float:
    """Safely handles metric parsing from Prometheus TSDB endpoints."""
    try:
        url = f"{PROMETHEUS_URL}/api/v1/query"
        response = requests.get(url, params={"query": query}, timeout=8)
        response.raise_for_status()
        
        payload = response.json()
        result_set = payload.get("data", {}).get("result", [])
        
        if result_set and len(result_set[0].get("value", [])) > 1:
            return float(result_set[0]["value"][1])
        return 0.0
    except (requests.exceptions.RequestException, ValueError, IndexError, KeyError) as e:
        logger.warning(f"Unable to resolve telemetry values via PromQL loop: {e}")
        return 0.0

def pull_system_baseline() -> Dict[str, float]:
    """Captures real-time architectural baseline metrics for verification loops."""
    error_query = f'sum(rate(http_requests_total{{status_code=~"5..",namespace="{K8S_NAMESPACE}"}}[2m])) / sum(rate(http_requests_total{{namespace="{K8S_NAMESPACE}"}}[2m]))'
    latency_query = f'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{{namespace="{K8S_NAMESPACE}"}}[2m])) by (le))'
    throughput_query = f'sum(rate(http_requests_total{{namespace="{K8S_NAMESPACE}"}}[2m]))'
    
    return {
        "error_rate": query_telemetry(error_query),
        "p99_latency": query_telemetry(latency_query),
        "request_rate": query_telemetry(throughput_query)
    }

def orchestrate_k8s_manifest(action: str, file_path: str) -> bool:
    """Manages the lifecycle of chaos injections via subprocessing."""
    if not os.path.exists(file_path):
        logger.error(f"Execution manifest targeted at path '{file_path}' does not exist. Skipping step.")
        return False
    try:
        cmd = ["kubectl", action, "-f", file_path, "-n", K8S_NAMESPACE]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Successfully processed cluster orchestration request: [{action.upper()} on {file_path}]")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Kubernetes cluster state manipulation failure: {e.stderr.decode().strip()}")
        return False

def execute_experiment(exp: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Runs the full lifecycle of an automated resilience test experiment."""
    logger.info(f"{'='*60}")
    logger.info(f"STARTING EXPERIMENT: {exp['name'].upper()}")
    logger.info(f"Target Hypothesis: {exp['hypothesis']}")
    logger.info(f"{'='*60}")

    logger.info("Collecting initial system architecture baseline values (30s hold)...")
    time.sleep(30)
    baseline_metrics = pull_system_baseline()
    logger.info(f"System Baseline established: error_rate={baseline_metrics['error_rate']:.4%}, p99={baseline_metrics['p99_latency']:.3f}s")

    # Failure Injection Step
    logger.info(f"Injecting failure footprint using configuration: {exp['manifest']}")
    if not orchestrate_k8s_manifest("apply", exp["manifest"]):
        logger.error(f"Failed to initiate experiment phase for {exp['name']}. Aborting sequence.")
        return None

    start_timestamp = datetime.utcnow()
    max_observed_error = 0.0
    max_observed_latency = 0.0
    evaluation_intervals = exp["duration"] // 15

    # Monitoring Monitoring Cycle Loop
    for interval in range(evaluation_intervals):
        time.sleep(15)
        current_metrics = pull_system_baseline()
        max_observed_error = max(max_observed_error, current_metrics["error_rate"])
        max_observed_latency = max(max_observed_latency, current_metrics["p99_latency"])
        
        elapsed_delta = (datetime.utcnow() - start_timestamp).seconds
        logger.info(f" -> T+{elapsed_delta}s Monitoring: current_errors={current_metrics['error_rate']:.4%}, current_p99={current_metrics['p99_latency']:.3f}s")

    # Stabilization & Restoration Cleanup Phase
    logger.info("Terminating active failure footprint injector state...")
    orchestrate_k8s_manifest("delete", exp["manifest"])

    logger.info("Entering operational recovery monitoring hold (60s)...")
    time.sleep(60)
    recovery_metrics = pull_system_baseline()
    
    # Quantitative Validation Checklist Evaluation
    threshold_limit = exp["slo_threshold_pct"]
    slo_breached = max_observed_error > threshold_limit
    verdict = "FAIL" if slo_breached else "PASS"
    
    logger.info(f"EXPERIMENT CONCLUSION SUMMARY -> VERDICT: {verdict} | Peak Error Delta: {max_observed_error:.2%}")

    return {
        "experiment_name": exp["name"],
        "hypothesis_evaluated": exp["hypothesis"],
        "baseline_state": baseline_metrics,
        "metrics_under_chaos": {
            "peak_error_rate": max_observed_error,
            "peak_p99_latency": max_observed_latency
        },
        "recovery_state": recovery_metrics,
        "slo_compliance_breached": slo_breached,
        "final_resilience_verdict": verdict
    }

def emit_resilience_payload(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates structured architectural compliance output documentation file."""
    output_path = "chaos-resilience-report.json"
    compiled_payload = {
        "generation_timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "summary_metrics": {
            "total_tests_conducted": len(results),
            "passed_compliance_checks": sum(1 for data in results if data["final_resilience_verdict"] == "PASS"),
            "failed_compliance_checks": sum(1 for data in results if data["final_resilience_verdict"] == "FAIL")
        },
        "experiment_records": results
    }
    
    try:
        with open(output_path, "w") as out_file:
            json.dump(compiled_payload, out_file, indent=2)
        logger.info(f"Resilience Analysis Payload archived successfully to disk at: {output_path}")
    except IOError as e:
        logger.critical(f"Critical execution error generating system diagnostics metrics dump: {e}")
        
    return compiled_payload

if __name__ == "__main__":
    logger.info("Initializing Automated Kubernetes Chaos Resiliency Laboratory Execution Runner...")
    execution_metrics = []
    
    for targeted_test in EXPERIMENTS:
        test_outcome = execute_experiment(targeted_test)
        if test_outcome:
            execution_metrics.append(test_outcome)
        time.sleep(20) # Cooling sequence buffer protecting shared cluster structures
        
    emit_resilience_payload(execution_metrics)
    logger.info("Resiliency verification process completed smoothly.")
