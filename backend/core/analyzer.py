from typing import Dict, Any, List

class Analyzer:
    def analyze(self, components: Dict[str, Dict[str, Any]], metrics: Dict[str, Any]) -> Dict[str, List[str]]:
        warnings = []
        recommendations = []
        
        # Count types for SPOF
        types_count = {}
        
        for cid, state in components.items():
            ctype = state.get("type", "unknown")
            types_count[ctype] = types_count.get(ctype, 0) + 1
            
            # Check drops
            dropped = state.get("dropped", 0)
            if dropped > 0:
                warnings.append(f"Box '{cid}' dropped {dropped} rocks!")
                recommendations.append(f"Make capacity of '{cid}' bigger, or fix boxes it talks to.")
                
            # Check queue
            if "queue_depth" in state:
                depth = state["queue_depth"]
                max_d = state["max_depth"]
                if depth > max_d * 0.8:
                    warnings.append(f"Queue '{cid}' is very full! ({depth}/{max_d})")
                    recommendations.append(f"Add more Workers for '{cid}' to smash rocks faster.")
                    
            # Check health
            if not state.get("healthy", True):
                warnings.append(f"Box '{cid}' is dead!")
                
        # Check SPOF (very simple caveman rule)
        # We don't know the types perfectly because components.py state doesn't have it, 
        # so we look at class name or just assume if only 1 thing has capacity, it's SPOF.
        # Actually, let's look at active/capacity. If any box is single, warn.
        
        return {
            "warnings": warnings,
            "recommendations": list(set(recommendations))
        }

analyzer = Analyzer()
