from typing import Dict, Any, List, Optional

class Analyzer:
    """
    Evidence-based Bottleneck and Architectural Flaw Analyzer.
    Evaluates topology, runtime component metrics, and system-wide state
    to produce deterministic findings with measurable evidence and severities.
    """
    def analyze(
        self,
        components: Dict[str, Dict[str, Any]],
        metrics: Dict[str, Any],
        time_window: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        warnings: List[str] = []
        recommendations: List[str] = []
        findings: List[Dict[str, Any]] = []

        window = time_window or [0.0, metrics.get("time", 0.0)]

        for cid, state in components.items():
            comp_type = state.get("type", "unknown")

            # 1. Capacity Saturation / Dropped Requests Rule
            dropped = state.get("dropped", 0)
            if dropped > 0:
                msg = f"Node '{cid}' dropped {dropped} requests due to capacity saturation."
                rec = f"Increase concurrency capacity of '{cid}', or scale dependent services."
                warnings.append(msg)
                recommendations.append(rec)
                findings.append({
                    "rule_id": "CAPACITY_SATURATION",
                    "severity": "HIGH",
                    "node_id": cid,
                    "time_window": window,
                    "title": f"Node '{cid}' Saturated",
                    "message": msg,
                    "evidence": {
                        "dropped": dropped,
                        "active": state.get("active", 0),
                        "capacity": state.get("capacity", state.get("concurrency", 0)),
                        "utilization": state.get("utilization", 0.0),
                    },
                    "recommendation": rec,
                })

            # 2. Queue Backpressure Rule
            if "queue_depth" in state:
                depth = state["queue_depth"]
                max_d = state.get("max_depth", state.get("max_queue_depth", 1000))
                if max_d and depth > max_d * 0.8:
                    msg = f"Message Queue '{cid}' buffer threshold exceeded ({depth}/{max_d})."
                    rec = f"Scale worker concurrency or add worker nodes for queue '{cid}'."
                    warnings.append(msg)
                    recommendations.append(rec)
                    findings.append({
                        "rule_id": "QUEUE_OVERFLOW",
                        "severity": "HIGH",
                        "node_id": cid,
                        "time_window": window,
                        "title": f"Buffer Overflow on Queue '{cid}'",
                        "message": msg,
                        "evidence": {
                            "queue_depth": depth,
                            "max_depth": max_d,
                            "occupancy_ratio": round(depth / max_d, 4),
                        },
                        "recommendation": rec,
                    })

            # 3. Node Health / Crash Rule
            if not state.get("healthy", True):
                msg = f"Node '{cid}' has failed."
                rec = f"Restore node '{cid}' or deploy redundant failover replicas."
                warnings.append(msg)
                recommendations.append(rec)
                findings.append({
                    "rule_id": "NODE_FAILED",
                    "severity": "CRITICAL",
                    "node_id": cid,
                    "time_window": window,
                    "title": f"Component Failure: '{cid}' Offline",
                    "message": msg,
                    "evidence": {"healthy": False, "failed_count": state.get("failed", 1)},
                    "recommendation": rec,
                })

            # 4. Retry Storm Amplification Rule
            total_attempts = state.get("total_attempts", 0)
            sent = state.get("sent", 0)
            if sent > 0 and (total_attempts / sent) > 1.4:
                ratio = round(total_attempts / sent, 2)
                msg = f"Client '{cid}' is experiencing a retry storm (amplification factor: {ratio}x)."
                rec = f"Configure a Circuit Breaker or enable a retry budget ratio on '{cid}'."
                warnings.append(msg)
                recommendations.append(rec)
                findings.append({
                    "rule_id": "RETRY_AMPLIFICATION",
                    "severity": "HIGH",
                    "node_id": cid,
                    "time_window": window,
                    "title": f"Retry Amplification Storm on '{cid}'",
                    "message": msg,
                    "evidence": {
                        "sent": sent,
                        "total_attempts": total_attempts,
                        "retry_count": state.get("retry_count", 0),
                        "amplification_factor": ratio,
                    },
                    "recommendation": rec,
                })

            # 5. Missing Timeouts Rule
            if state.get("has_downstream", False) and state.get("timeout") is None:
                msg = f"Node '{cid}' makes downstream calls without an explicit timeout."
                rec = f"Configure a request timeout on '{cid}' to prevent unbounded worker thread blocking."
                warnings.append(msg)
                recommendations.append(rec)
                findings.append({
                    "rule_id": "MISSING_TIMEOUT",
                    "severity": "MEDIUM",
                    "node_id": cid,
                    "time_window": window,
                    "title": f"Missing Downstream Timeout on '{cid}'",
                    "message": msg,
                    "evidence": {"timeout": None},
                    "recommendation": rec,
                })

            # 6. No Circuit Breaker on Dependency Rule
            if state.get("has_downstream", False) and not state.get("circuit_breaker"):
                msg = f"Node '{cid}' calls dependencies without a Circuit Breaker."
                rec = f"Equip downstream calls from '{cid}' with a Circuit Breaker to prevent cascading collapse."
                warnings.append(msg)
                recommendations.append(rec)
                findings.append({
                    "rule_id": "NO_CIRCUIT_BREAKER",
                    "severity": "MEDIUM",
                    "node_id": cid,
                    "time_window": window,
                    "title": f"Unprotected Dependency on '{cid}'",
                    "message": msg,
                    "evidence": {"circuit_breaker_enabled": False},
                    "recommendation": rec,
                })

            # 7. Cache Stampede Risk Rule
            if state.get("is_warming_up", False) or (state.get("misses", 0) > 20 and state.get("effective_hit_rate", 1.0) < 0.3):
                msg = f"Cache '{cid}' is cold or warming up, presenting a critical Cache Stampede risk."
                rec = f"Implement cache pre-warming, probabilistic early expiration (XFetch), or mutex locking."
                warnings.append(msg)
                recommendations.append(rec)
                findings.append({
                    "rule_id": "CACHE_STAMPEDE_RISK",
                    "severity": "HIGH",
                    "node_id": cid,
                    "time_window": window,
                    "title": f"Cache Stampede Risk on '{cid}'",
                    "message": msg,
                    "evidence": {
                        "effective_hit_rate": state.get("effective_hit_rate", 0.0),
                        "nominal_hit_rate": state.get("hit_rate", 0.8),
                        "misses": state.get("misses", 0),
                        "is_warming_up": state.get("is_warming_up", False),
                    },
                    "recommendation": rec,
                })

            # 8. Hot Shard Rule
            routed_counts = state.get("routed_counts", {})
            if len(routed_counts) > 1:
                vals = list(routed_counts.values())
                avg_val = sum(vals) / len(vals)
                max_val = max(vals)
                if avg_val > 10 and max_val > 2.0 * avg_val:
                    hot_id = max(routed_counts, key=routed_counts.get)
                    msg = f"Sharded Database '{cid}' has a hot shard '{hot_id}' receiving {max_val} requests (average: {avg_val:.1f})."
                    rec = f"Salt the shard key or choose a higher-cardinality partition key on '{cid}'."
                    warnings.append(msg)
                    recommendations.append(rec)
                    findings.append({
                        "rule_id": "HOT_SHARD",
                        "severity": "HIGH",
                        "node_id": cid,
                        "time_window": window,
                        "title": f"Data Skew / Hot Shard on '{cid}'",
                        "message": msg,
                        "evidence": {
                            "hot_shard": hot_id,
                            "hot_shard_requests": max_val,
                            "average_requests": round(avg_val, 1),
                            "skew_ratio": round(max_val / avg_val, 2),
                        },
                        "recommendation": rec,
                    })

            # 9. Replication Lag Rule
            repl_lag = state.get("replication_lag", 0.0)
            if repl_lag >= 0.20:
                msg = f"Replication lag on database '{cid}' is high ({repl_lag}s)."
                rec = f"Optimize batch sizes or direct read-after-write critical paths to the primary database."
                warnings.append(msg)
                recommendations.append(rec)
                findings.append({
                    "rule_id": "REPLICATION_LAG",
                    "severity": "MEDIUM",
                    "node_id": cid,
                    "time_window": window,
                    "title": f"Elevated Replication Lag on '{cid}'",
                    "message": msg,
                    "evidence": {"replication_lag": repl_lag, "threshold": 0.20},
                    "recommendation": rec,
                })

            # 10. Single Point of Failure (SPOF) Rule
            if comp_type in ("api", "database") and state.get("concurrency", state.get("capacity", 1)) == 1 and state.get("replica_count", 0) == 0:
                msg = f"Node '{cid}' is a Single Point of Failure (SPOF) with concurrency=1 and no redundant replicas."
                rec = f"Deploy redundant instances or configure failover replicas for '{cid}'."
                warnings.append(msg)
                recommendations.append(rec)
                findings.append({
                    "rule_id": "SINGLE_POINT_OF_FAILURE",
                    "severity": "HIGH",
                    "node_id": cid,
                    "time_window": window,
                    "title": f"Single Point of Failure: '{cid}'",
                    "message": msg,
                    "evidence": {"concurrency": 1, "replica_count": 0},
                    "recommendation": rec,
                })

        return {
            "warnings": warnings,
            "recommendations": sorted(list(set(recommendations))),
            "findings": findings,
        }

analyzer = Analyzer()
