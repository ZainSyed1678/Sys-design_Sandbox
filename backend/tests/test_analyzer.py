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
    assert any("dropped 15 rocks" in w for w in result["warnings"])
    assert any("Make capacity of 'api_1' bigger" in r for r in result["recommendations"])

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
    
    assert any("is very full" in w for w in result["warnings"])
    assert any("Add more Workers" in r for r in result["recommendations"])

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
    
    assert any("is dead" in w for w in result["warnings"])
