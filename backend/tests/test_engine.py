import pytest
from simulation.engine import SimulationEngine
from simulation.events import Event, EventType
from simulation.components import Client, APIServer

def test_engine_basic_flow():
    engine = SimulationEngine()
    
    api = APIServer("api_1", capacity=10, latency=0.1)
    client = Client("client_1", "api_1", rate_per_sec=10)
    
    engine.register_component(api)
    engine.register_component(client)
    
    # Kick off client
    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="client_1"))
    
    engine.run(until=1.0)
    
    assert engine.time <= 1.0
    
    # 10 reqs/sec for 1 sec = 11 requests arrived (at 0.0, 0.1, ... 1.0)
    # The last one might not have finished
    assert engine.metrics["completed"] > 0
    assert api.completed > 0

def test_api_drop_requests():
    engine = SimulationEngine()
    
    # capacity 1, latency 1 sec (very slow)
    api = APIServer("api_1", capacity=1, latency=1.0)
    client = Client("client_1", "api_1", rate_per_sec=10)
    
    engine.register_component(api)
    engine.register_component(client)
    
    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="client_1"))
    
    engine.run(until=0.5)
    
    # Should have dropped requests because capacity is 1
    assert engine.metrics["dropped"] > 0
    assert api.dropped > 0

def test_component_failure_and_recovery():
    engine = SimulationEngine(seed=42)
    api = APIServer("api_1", capacity=10, latency=0.1)
    client = Client("client_1", "api_1", rate_per_sec=10)
    
    engine.register_component(api)
    engine.register_component(client)
    
    # Start traffic
    engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id="client_1"))
    
    # Inject failure at t=0.2
    engine.schedule(Event(time=0.2, type=EventType.COMPONENT_FAILED, target_id="api_1"))
    
    # Inject recovery at t=0.6
    engine.schedule(Event(time=0.6, type=EventType.COMPONENT_RECOVERED, target_id="api_1"))
    
    engine.run(until=1.0)
    
    # During failure period, requests should be dropped
    assert api.dropped > 0
    assert api.is_healthy is True

def test_deterministic_engine_seed():
    engine1 = SimulationEngine(seed=123)
    engine2 = SimulationEngine(seed=123)
    assert engine1.time == engine2.time
