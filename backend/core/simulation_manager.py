import uuid
import threading
import time
from enum import Enum
from typing import Dict, Any, Optional

from simulation.engine import SimulationEngine
from simulation.components import Client, LoadBalancer, APIServer, Database
from simulation.events import Event, EventType

class SimState(Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class SimulationInstance:
    def __init__(self, sim_id: str, graph: Dict[str, Any]):
        self.sim_id = sim_id
        self.graph = graph
        self.state = SimState.CREATED
        self.engine = SimulationEngine()
        self.thread = None
        self._stop_event = threading.Event()
        
    def build(self):
        try:
            nodes = self.graph.get("nodes", [])
            edges = self.graph.get("edges", [])
            
            node_map = {n["id"]: n for n in nodes}
            adj = {}
            for e in edges:
                src = e["source"]
                tgt = e["target"]
                if src not in adj: adj[src] = []
                adj[src].append(tgt)
                
            for n in nodes:
                nid = n["id"]
                ntype = n["data"].get("type", "unknown")
                targets = adj.get(nid, [])
                
                if ntype == "client":
                    target_id = targets[0] if targets else "none"
                    comp = Client(nid, target_id, rate_per_sec=10)
                    self.engine.register_component(comp)
                    self.engine.schedule(Event(time=0.0, type=EventType.REQUEST_ARRIVED, target_id=nid))
                elif ntype == "load_balancer":
                    comp = LoadBalancer(nid, backend_ids=targets)
                    self.engine.register_component(comp)
                elif ntype == "api":
                    db_id = targets[0] if targets else None
                    comp = APIServer(nid, capacity=10, latency=0.1, db_id=db_id)
                    self.engine.register_component(comp)
                elif ntype == "database":
                    comp = Database(nid, capacity=5, latency=0.2)
                    self.engine.register_component(comp)
            self.state = SimState.CREATED
        except Exception as e:
            print("Failed building graph:", e)
            self.state = SimState.FAILED

    def _run_loop(self):
        self.state = SimState.RUNNING
        
        while not self._stop_event.is_set():
            step_until = self.engine.time + 0.5
            self.engine.run(until=step_until)
            time.sleep(0.5)
            
        self.state = SimState.STOPPED

    def start(self):
        if self.state in [SimState.RUNNING, SimState.FAILED]:
            return
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if self.state == SimState.RUNNING:
            self._stop_event.set()
            if self.thread:
                self.thread.join(timeout=2.0)
            self.state = SimState.STOPPED

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "sim_time": self.engine.time,
            "metrics": self.engine.metrics,
            "components": self.engine.get_component_states()
        }

class SimulationManager:
    def __init__(self):
        self.simulations: Dict[str, SimulationInstance] = {}

    def create_simulation(self, graph: Dict[str, Any]) -> str:
        sim_id = str(uuid.uuid4())
        instance = SimulationInstance(sim_id, graph)
        instance.build()
        self.simulations[sim_id] = instance
        return sim_id

    def get_simulation(self, sim_id: str) -> Optional[SimulationInstance]:
        return self.simulations.get(sim_id)

sim_manager = SimulationManager()
