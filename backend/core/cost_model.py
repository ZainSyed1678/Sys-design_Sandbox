from typing import Dict, Any, List, Optional

# Default estimated cloud cost per component type per hour (USD)
# Clearly labeled as rough estimates for architectural comparison modeling
DEFAULT_HOURLY_RATES: Dict[str, float] = {
    "client": 0.000,           # External traffic source / no server cost
    "load_balancer": 0.025,    # e.g., AWS Application Load Balancer base hourly rate ($0.0225)
    "api": 0.040,              # e.g., t3.medium / 2 vCPU 4GB RAM compute ($0.0416/hr)
    "database": 0.100,         # e.g., db.t3.medium managed PostgreSQL instance ($0.068 - $0.10/hr)
    "cache": 0.035,            # e.g., cache.t3.medium ElastiCache Redis ($0.034/hr)
    "queue": 0.015,            # e.g., Managed message queue broker partition ($0.015/hr)
    "worker": 0.040,           # e.g., Background compute worker node ($0.040/hr)
    "cdn": 0.020,              # e.g., CloudFront edge distribution base pricing ($0.020/hr)
    "api_gateway": 0.030,      # e.g., AWS API Gateway base hourly equivalent ($0.030/hr)
    "sharded_db": 0.150,       # e.g., Multi-shard distributed database coordinator ($0.150/hr)
    "read_replica": 0.080,     # e.g., Managed read replica instance ($0.080/hr)
    "autoscaler": 0.010,       # e.g., ASG controller / monitoring overhead ($0.010/hr)
    "default": 0.030,          # Fallback generic infrastructure node ($0.030/hr)
}

def estimate_architecture_cost(
    graph: Dict[str, Any],
    custom_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Computes estimated hourly and monthly cost for a system architecture graph.
    All outputs are explicitly flagged with estimate disclaimers.
    """
    rates = dict(DEFAULT_HOURLY_RATES)
    if custom_rates:
        rates.update(custom_rates)

    nodes = graph.get("nodes", [])
    breakdown: Dict[str, Dict[str, Any]] = {}
    total_hourly = 0.0

    for n in nodes:
        data = n.get("data", {})
        ntype = data.get("type", "unknown").lower()
        rate = rates.get(ntype, rates.get("default", 0.030))

        if ntype not in breakdown:
            breakdown[ntype] = {
                "count": 0,
                "unit_rate_hourly": rate,
                "subtotal_hourly": 0.0,
            }

        breakdown[ntype]["count"] += 1
        breakdown[ntype]["subtotal_hourly"] = round(
            breakdown[ntype]["subtotal_hourly"] + rate, 4
        )
        total_hourly += rate

    total_hourly = round(total_hourly, 4)
    total_monthly = round(total_hourly * 730.0, 2)  # 730 average hours per month

    return {
        "disclaimer": "ROUGH_ESTIMATE: Illustrative cloud infrastructure pricing for architectural comparison purposes only.",
        "currency": "USD",
        "total_hourly_cost": total_hourly,
        "total_monthly_cost": total_monthly,
        "node_count": len(nodes),
        "breakdown": breakdown,
    }
