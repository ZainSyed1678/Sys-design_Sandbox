import pytest
from core.analyzer import Analyzer

def test_analyzer_detects_overloaded_component():
    analyzer = Analyzer()
    components = {
        "api_1": {
            "type": "api",
            "healthy": True,
            "dropped": 15,
            "completed": 100,
            "active": 10,
            "capacity": 10
        }
    }
    metrics = {"completed": 100, "failed": 0, "dropped": 15}
    
    result = analyzer.analyze(components, metrics)
    
    assert len(result["warnings"]) > 0
    assert any("dropped 15 requests" in w for w in result["warnings"])
    assert any("Increase concurrency capacity of 'api_1'" in r for r in result["recommendations"])
    assert any(f["rule_id"] == "CAPACITY_SATURATION" for f in result["findings"])

def test_analyzer_detects_queue_overflow():
    analyzer = Analyzer()
    components = {
        "queue_1": {
            "type": "queue",
            "healthy": True,
            "dropped": 0,
            "completed": 50,
            "queue_depth": 850,
            "max_depth": 1000
        }
    }
    metrics = {"completed": 50, "failed": 0, "dropped": 0}
    
    result = analyzer.analyze(components, metrics)
    
    assert any("buffer threshold exceeded" in w for w in result["warnings"])
    assert any("Scale worker concurrency" in r for r in result["recommendations"])
    assert any(f["rule_id"] == "QUEUE_OVERFLOW" for f in result["findings"])

def test_analyzer_detects_dead_component():
    analyzer = Analyzer()
    components = {
        "db_1": {
            "type": "database",
            "healthy": False,
            "dropped": 5,
            "completed": 10
        }
    }
    metrics = {"completed": 10, "failed": 0, "dropped": 5}
    
    result = analyzer.analyze(components, metrics)
    
    assert any("has failed" in w for w in result["warnings"])
    assert any(f["rule_id"] == "NODE_FAILED" and f["severity"] == "CRITICAL" for f in result["findings"])

def test_analyzer_detects_retry_amplification():
    analyzer = Analyzer()
    components = {
        "client_1": {
            "type": "client",
            "healthy": True,
            "sent": 100,
            "total_attempts": 280,
            "retry_count": 180,
        }
    }
    result = analyzer.analyze(components, {"time": 10.0})
    findings = [f for f in result["findings"] if f["rule_id"] == "RETRY_AMPLIFICATION"]
    assert len(findings) == 1
    assert findings[0]["severity"] == "HIGH"
    assert findings[0]["evidence"]["amplification_factor"] == 2.8

def test_analyzer_detects_missing_timeouts():
    analyzer = Analyzer()
    components = {
        "api_srv": {
            "type": "api",
            "healthy": True,
            "has_downstream": True,
            "timeout": None,
        }
    }
    result = analyzer.analyze(components, {"time": 5.0})
    findings = [f for f in result["findings"] if f["rule_id"] == "MISSING_TIMEOUT"]
    assert len(findings) == 1
    assert findings[0]["severity"] == "MEDIUM"

def test_analyzer_detects_no_circuit_breaker():
    analyzer = Analyzer()
    components = {
        "api_srv": {
            "type": "api",
            "healthy": True,
            "has_downstream": True,
            "circuit_breaker": None,
        }
    }
    result = analyzer.analyze(components, {"time": 5.0})
    findings = [f for f in result["findings"] if f["rule_id"] == "NO_CIRCUIT_BREAKER"]
    assert len(findings) == 1

def test_analyzer_detects_cache_stampede_risk():
    analyzer = Analyzer()
    components = {
        "redis_cache": {
            "type": "cache",
            "healthy": True,
            "is_warming_up": True,
            "effective_hit_rate": 0.15,
            "hit_rate": 0.85,
            "misses": 80,
        }
    }
    result = analyzer.analyze(components, {"time": 2.0})
    findings = [f for f in result["findings"] if f["rule_id"] == "CACHE_STAMPEDE_RISK"]
    assert len(findings) == 1
    assert findings[0]["severity"] == "HIGH"

def test_analyzer_detects_hot_shard():
    analyzer = Analyzer()
    components = {
        "user_db_cluster": {
            "type": "sharded_database",
            "healthy": True,
            "routed_counts": {
                "shard_0": 20,
                "shard_1": 150,  # Hot shard!
                "shard_2": 25,
            }
        }
    }
    result = analyzer.analyze(components, {"time": 10.0})
    findings = [f for f in result["findings"] if f["rule_id"] == "HOT_SHARD"]
    assert len(findings) == 1
    assert findings[0]["evidence"]["hot_shard"] == "shard_1"

def test_analyzer_detects_replication_lag():
    analyzer = Analyzer()
    components = {
        "postgres_cluster": {
            "type": "read_replica",
            "healthy": True,
            "replication_lag": 0.45,  # High lag
        }
    }
    result = analyzer.analyze(components, {"time": 10.0})
    findings = [f for f in result["findings"] if f["rule_id"] == "REPLICATION_LAG"]
    assert len(findings) == 1
    assert findings[0]["evidence"]["replication_lag"] == 0.45

def test_analyzer_detects_single_point_of_failure():
    analyzer = Analyzer()
    components = {
        "primary_db": {
            "type": "database",
            "healthy": True,
            "concurrency": 1,
            "replica_count": 0,
        }
    }
    result = analyzer.analyze(components, {"time": 10.0})
    findings = [f for f in result["findings"] if f["rule_id"] == "SINGLE_POINT_OF_FAILURE"]
    assert len(findings) == 1
    assert findings[0]["severity"] == "HIGH"
