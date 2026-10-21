from typing import Dict, Any, List

class Analyzer:
    def analyze(self, components: Dict[str, Dict[str, Any]], metrics: Dict[str, Any]) -> Dict[str, List[str]]:
        warnings = []
        recommendations = []
        
        for cid, state in components.items():
            # Check dropped requests
            dropped = state.get("dropped", 0)
            if dropped > 0:
                warnings.append(f"Node '{cid}' dropped {dropped} requests due to capacity saturation.")
                recommendations.append(f"Increase concurrency capacity of '{cid}', or scale dependent services.")
                
            # Check queue backpressure
            if "queue_depth" in state:
                depth = state["queue_depth"]
                max_d = state["max_depth"]
                if depth > max_d * 0.8:
                    warnings.append(f"Message Queue '{cid}' buffer threshold exceeded ({depth}/{max_d}).")
                    recommendations.append(f"Scale worker concurrency or add worker nodes for queue '{cid}'.")
                    
            # Check node health
            if not state.get("healthy", True):
                warnings.append(f"Node '{cid}' has failed.")
                recommendations.append(f"Restore node '{cid}' or deploy redundant failover replicas.")
                
        return {
            "warnings": warnings,
            "recommendations": sorted(list(set(recommendations)))
        }

analyzer = Analyzer()
