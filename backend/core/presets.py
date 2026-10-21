from typing import Dict, Any, List, Optional

SCENARIO_PRESETS: Dict[str, Dict[str, Any]] = {
    "url_shortener": {
        "id": "url_shortener",
        "title": "URL Shortener (Read-Heavy Cache-Aside)",
        "description": "A high-throughput URL shortening service (like Bitly). Serves 95% of reads directly from an in-memory cache, shielding the relational database.",
        "guided_steps": [
            "1. Start the simulation with baseline traffic (50 req/s).",
            "2. Observe how the Cache node absorbs ~95% of traffic with low latency (<10ms).",
            "3. Select the Cache node and click 'Fail Node' to simulate a cache cluster outage.",
            "4. Observe the immediate spillover: 100% of read traffic saturates the Database, causing latency spikes and request drops.",
            "5. Click 'Recover Node' and watch traffic stabilize as the cache resumes serving requests.",
        ],
        "expected_outcome": "Demonstrates cache-aside protection: the primary database cannot sustain full raw read traffic alone without caching.",
        "traffic_pattern": {"pattern_type": "constant", "base_rate": 50.0},
        "graph": {
            "nodes": [
                {"id": "client_1", "data": {"type": "client", "label": "Web Clients", "rate_per_sec": 50.0}},
                {"id": "lb_1", "data": {"type": "load_balancer", "label": "ALB", "strategy": "round_robin"}},
                {"id": "api_1", "data": {"type": "api", "label": "API Server 1", "concurrency": 20, "latency": 0.02}},
                {"id": "api_2", "data": {"type": "api", "label": "API Server 2", "concurrency": 20, "latency": 0.02}},
                {"id": "cache_1", "data": {"type": "cache", "label": "Redis Cache", "hit_rate": 0.95, "latency": 0.002}},
                {"id": "db_1", "data": {"type": "database", "label": "PostgreSQL", "concurrency": 5, "latency": 0.08, "max_queue_depth": 30}},
            ],
            "edges": [
                {"id": "e1", "source": "client_1", "target": "lb_1"},
                {"id": "e2", "source": "lb_1", "target": "api_1"},
                {"id": "e3", "source": "lb_1", "target": "api_2"},
                {"id": "e4", "source": "api_1", "target": "cache_1"},
                {"id": "e5", "source": "api_2", "target": "cache_1"},
                {"id": "e6", "source": "cache_1", "target": "db_1"},
            ],
        },
    },

    "social_timeline": {
        "id": "social_timeline",
        "title": "Social Timeline (Asynchronous Feed Fanout)",
        "description": "Models a social media timeline feed generator. Asynchronous message queues decouple user post ingestion from expensive timeline fanout workers.",
        "guided_steps": [
            "1. Start simulation to observe bursty post ingestion (on/off bursts).",
            "2. Note how the Message Queue buffers sudden spikes, preventing worker process saturation.",
            "3. Observe background workers steadily consuming jobs from the queue at a sustainable rate.",
            "4. Notice how reads query the Read Replica Database without interfering with primary writes.",
        ],
        "expected_outcome": "Demonstrates queue decoupling: temporary spikes in user post creation buffer safely in the queue without overwhelming the database.",
        "traffic_pattern": {"pattern_type": "bursty", "base_rate": 10.0, "peak_rate": 40.0, "burst_on_duration": 3.0, "burst_off_duration": 4.0},
        "graph": {
            "nodes": [
                {"id": "client_users", "data": {"type": "client", "label": "Mobile Users", "rate_per_sec": 25.0}},
                {"id": "api_gw", "data": {"type": "api", "label": "API Gateway", "concurrency": 30, "latency": 0.01}},
                {"id": "mq_fanout", "data": {"type": "queue", "label": "Kafka / SQS", "max_depth": 500}},
                {"id": "worker_1", "data": {"type": "worker", "label": "Fanout Worker 1", "concurrency": 5, "latency": 0.05}},
                {"id": "worker_2", "data": {"type": "worker", "label": "Fanout Worker 2", "concurrency": 5, "latency": 0.05}},
                {"id": "db_replica", "data": {"type": "database", "label": "Timeline Store", "concurrency": 10, "latency": 0.03}},
            ],
            "edges": [
                {"id": "e1", "source": "client_users", "target": "api_gw"},
                {"id": "e2", "source": "api_gw", "target": "mq_fanout"},
                {"id": "e3", "source": "mq_fanout", "target": "worker_1"},
                {"id": "e4", "source": "mq_fanout", "target": "worker_2"},
                {"id": "e5", "source": "worker_1", "target": "db_replica"},
                {"id": "e6", "source": "worker_2", "target": "db_replica"},
            ],
        },
    },

    "black_friday_spike": {
        "id": "black_friday_spike",
        "title": "Black Friday Spike (Autoscaling under Pressure)",
        "description": "Simulates an abrupt 5x traffic spike (e.g. flash sale kickoff). Demonstrates how Autoscaling Groups absorb traffic surges by provisioning capacity dynamically.",
        "guided_steps": [
            "1. Start the simulation. Observe smooth operation under baseline traffic (15 req/s).",
            "2. At virtual time t=5.0s, the traffic profile spikes 5x to 80 req/s.",
            "3. Observe initial queue buildup and rising utilization.",
            "4. Notice the Autoscaling Group detecting sustained >75% utilization and scaling concurrency up from 2 to 8.",
            "5. Observe queue depth recovering back to healthy levels once scaled instances come online.",
        ],
        "expected_outcome": "Demonstrates elastic scaling: autoscaling absorbs sudden demand spikes, preventing permanent request dropping.",
        "traffic_pattern": {"pattern_type": "step_spike", "base_rate": 15.0, "peak_rate": 80.0, "spike_start": 4.0, "spike_end": 12.0},
        "graph": {
            "nodes": [
                {"id": "shoppers", "data": {"type": "client", "label": "Shoppers", "rate_per_sec": 40.0}},
                {"id": "lb_store", "data": {"type": "load_balancer", "label": "Cloud LB", "strategy": "least_connections"}},
                {"id": "api_checkout", "data": {"type": "api", "label": "Checkout Service", "concurrency": 4, "latency": 0.04, "max_queue_depth": 100}},
                {"id": "db_orders", "data": {"type": "database", "label": "Orders DB", "concurrency": 15, "latency": 0.02}},
            ],
            "edges": [
                {"id": "e1", "source": "shoppers", "target": "lb_store"},
                {"id": "e2", "source": "lb_store", "target": "api_checkout"},
                {"id": "e3", "source": "api_checkout", "target": "db_orders"},
            ],
        },
    },

    "cache_stampede": {
        "id": "cache_stampede",
        "title": "Cache Stampede (Cold-Start Failover Thundering Herd)",
        "description": "Simulates a cold cache restart under heavy concurrent traffic. When a cold cache comes online with 0% hit rate, concurrent requests stampede directly to the database.",
        "guided_steps": [
            "1. Start simulation with heavy concurrent read traffic (40 req/s).",
            "2. Click the Cache node and click 'Fail Node' at t=1.0s, then click 'Recover Node' at t=2.0s.",
            "3. Notice that upon recovery, the cache is completely cold (0% effective hit rate, 8s warmup duration).",
            "4. Observe the 'thundering herd': 100% of concurrent requests bypass the cold cache and stampede into the Database.",
            "5. The Database concurrency (2) saturates immediately, its queue overflows, and requests drop heavily until cache warms up.",
        ],
        "expected_outcome": "Demonstrates the thundering herd problem: recovering a cache cold without pre-warming causes database collapse.",
        "traffic_pattern": {"pattern_type": "constant", "base_rate": 40.0},
        "graph": {
            "nodes": [
                {"id": "client_stampede", "data": {"type": "client", "label": "API Consumers", "rate_per_sec": 40.0}},
                {"id": "api_server", "data": {"type": "api", "label": "Gateway API", "concurrency": 20, "latency": 0.01}},
                {"id": "cache_cold", "data": {"type": "cache", "label": "Cold Cache", "hit_rate": 0.85, "latency": 0.005, "warmup_duration": 8.0}},
                {"id": "db_bottleneck", "data": {"type": "database", "label": "Fragile DB", "concurrency": 2, "latency": 0.1, "max_queue_depth": 15}},
            ],
            "edges": [
                {"id": "e1", "source": "client_stampede", "target": "api_server"},
                {"id": "e2", "source": "api_server", "target": "cache_cold"},
                {"id": "e3", "source": "cache_cold", "target": "db_bottleneck"},
            ],
        },
    },
}

def get_all_presets() -> List[Dict[str, Any]]:
    """Return catalog of all available scenario presets."""
    return list(SCENARIO_PRESETS.values())

def get_preset_by_id(preset_id: str) -> Optional[Dict[str, Any]]:
    """Return specific preset by ID."""
    return SCENARIO_PRESETS.get(preset_id)
