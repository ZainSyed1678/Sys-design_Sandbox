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
