# System Design Simulator — Comprehensive Audit (Phase 0)

**Date:** 2026-10-21  
**Repository:** `Sys-design_Sandbox`  
**Target:** Production-grade system design simulator & sandbox

---

## 1. Codebase Structure & Component Mapping

### 1.1 Backend Architecture
- **Web Layer:**
  - `backend/app.py`: Flask entrypoint. Initializes CORS, SocketIO, registers blueprints (`architecture_bp`, `simulation_bp`), exposes `/api/health`.
  - `backend/extensions.py`: Central `SocketIO(cors_allowed_origins="*", async_mode='threading')`.
  - `backend/api/architecture.py`: `/api/architecture/validate` — Basic validation (non-empty nodes, client presence check).
  - `backend/api/simulation_api.py`: REST routes for simulation lifecycle (`/start`, `/<sim_id>/stop`, `/<sim_id>/status`, `/<sim_id>/inject`).
- **Core Orchestration:**
  - `backend/core/simulation_manager.py`: `SimulationManager` singleton storing `SimulationInstance` objects in an in-memory dictionary. Builds component graph, manages background execution thread (`threading.Thread`), steps virtual time by 0.5 units, and emits WebSocket events every 0.5s real time.
  - `backend/core/analyzer.py`: `Analyzer` singleton with rule-based heuristics evaluating drops, queue saturation, and dead components.
- **Discrete Event Simulation Engine (Decoupled):**
  - `backend/simulation/engine.py`: Standalone `SimulationEngine` utilizing Python's `heapq` for priority-queue-based event scheduling. Tracks `self.time`, registered components, and high-level counters (`completed`, `failed`, `dropped`).
  - `backend/simulation/events.py`: `EventType` enum (`REQUEST_ARRIVED`, `REQUEST_COMPLETED`, `REQUEST_FAILED`, `COMPONENT_FAILED`, `COMPONENT_RECOVERED`, `TRAFFIC_CHANGED`) and dataclass `Event` ordered by timestamp.
  - `backend/simulation/components.py`: Component abstractions:
    - `BaseComponent`: Health tracking, drop/completion counters.
    - `Client`: Constant rate request generator (`rate_per_sec`).
    - `LoadBalancer`: Round-robin router across backend target IDs.
    - `APIServer`: Concurrency capacity limit, static latency, optional database delegate.
    - `Database`: Transaction capacity limit, static latency.
    - `Cache`: Pseudo-random hit rate check, forwarding misses to DB or completing hits.
    - `MessageQueue`: FIFO queue with `max_depth` and worker dispatch logic.
    - `Worker`: Pull-based queue consumer with capacity and latency.

### 1.2 Frontend Architecture
- **Stack:** React 18, Vite, TypeScript, React Flow 11, Socket.io-client 4.
- **State & Layout:**
  - `frontend/src/App.tsx`: Global navigation header, mode state (`'hld' | 'lld'`), and tutorial modal.
  - `frontend/src/Canvas.tsx`: High-Level Design (HLD) canvas with React Flow. Manages node/edge graphs, simulation ID, node selection, Socket.io metrics listener, toolbar component insertion, and chaos injection actions.
  - `frontend/src/nodes/InfrastructureNode.tsx`: Custom React Flow node with utilization gauge, drop count, queue depth, and metrics display.
  - `frontend/src/LLDCanvas.tsx`: Low-Level Design (LLD) canvas with React Flow. Palettes for Class, Interface, Service, Repository, Controller, Pattern.
  - `frontend/src/nodes/LLDNode.tsx`: UML compartment node rendering stereotypes, attributes with access modifiers, and methods.
  - `frontend/src/components/LLDSpecificationsPanel.tsx`: Interactive specifications inspector; code generator rendering TypeScript and Python class/interface skeletons.

---

## 2. Infrastructure & Persistence Audit (PostgreSQL & Redis)

- **Docker Compose (`docker-compose.yml`):**
  - Defines `postgres:15-alpine` (`db`, port 5432).
  - Defines `redis:7-alpine` (`redis`, port 6379).
  - Supplies `DATABASE_URL` and `REDIS_URL` environment variables to `backend`.
- **Python Dependencies (`backend/requirements.txt`):**
  - Lists `psycopg2-binary==2.9.9`, `SQLAlchemy==2.0.23`, `redis==5.0.1`.
- **Actual Usage:**
  - **Zero lines of application code use PostgreSQL or Redis.**
  - Neither module is imported anywhere in `backend/app.py`, `backend/core/`, `backend/api/`, or `backend/simulation/`.
  - All architecture data and simulation state exist strictly in Python process memory (`sim_manager.simulations`).
  - **Verdict:** PostgreSQL and Redis are currently zombie dependencies. PostgreSQL should be activated in Phase 6 for design persistence and sharing, or pruned until needed. Redis is completely unused.

---

## 3. Virtual Time vs. Wall-Clock Streaming Mapping

- **Loop Implementation (`backend/core/simulation_manager.py:85-108`):**
  ```python
  while not self._stop_event.is_set():
      step_until = self.engine.time + 0.5
      self.engine.run(until=step_until)
      states = self.engine.get_component_states()
      analysis = analyzer.analyze(states, self.engine.metrics)
      socketio.emit('METRICS_UPDATE', {...})
      time.sleep(0.5)
  ```
- **Virtual Time vs Real Time:**
  - Fixed 1:1 mapping: 0.5 virtual time units per 0.5 wall-clock seconds.
  - Fixed 2 Hz broadcast frequency (every 500 ms).
- **Shortcomings:**
  - No simulation speed multiplier (e.g., 0.25x, 1x, 5x, 50x, 100x).
  - No pause, resume, step-forward, or rewind capabilities.
  - If a large queue of events takes >0.5s to process in `run()`, virtual time lags behind wall clock with no backpressure control.

---

## 4. Multi-Tenant Isolation, Lifecycle & Resource Limits

- **Session Isolation:**
  - **Fails isolation:** `socketio.emit()` broadcasts globally to all connected clients without rooms. Any browser connected to `http://localhost:3001` receives events from any other user's simulation.
  - In `frontend/src/Canvas.tsx`: `if (data.sim_id === simId || !simId)` allows cross-session leakage if `simId` is not yet set in local state.
- **Thread Lifecycle on Disconnect:**
  - **Fails cleanup:** There is no `@socketio.on('disconnect')` handler.
  - If a user closes the browser tab while a simulation is running, the background Python worker thread runs indefinitely.
- **Resource Limits:**
  - **Unbounded Simulation Count:** No cap on concurrent simulation threads in `sim_manager.simulations`. An attacker or multiple tabs can spawn unlimited threads leading to server thread exhaustion.
  - **Unbounded Duration:** Simulations run forever until explicitly stopped via `/stop`.
  - **Unbounded Event & Heap Size:** No limit on maximum events in `SimulationEngine.events`.
  - **Unbounded Graph Size:** No validation limit on the number of nodes or edges passed to `/start`.

---

## 5. Topology Validation Analysis

- **Current Validation (`backend/api/architecture.py`):**
  - Only verifies that `nodes` is non-empty and at least one node has `data.type == 'client'`.
  - This validation is not even invoked before `/api/simulation/start` runs!
- **Missing Validations:**
  - **Cycles:** Circular references (e.g. A -> B -> A) cause infinite event generation loops, creating runaway memory leaks in `engine.events`.
  - **Disconnected / Orphan Nodes:** Unconnected nodes sit idle; clients with no target assign target `"none"`, silently dropping requests at the engine level.
  - **Invalid Edges:** No validation on directional constraints (e.g. Database -> Client or Queue -> Load Balancer are accepted without error).
  - **Missing Downstream Endpoints:** APIServer with `db_id=None` handles requests standalone without checking if user intended a database connection.

---

## 6. Repository Hygiene, Dead Code & Inconsistencies

- **Jokey / Unprofessional Terminology:**
  - UI labels: "Start Fast Magic", "Kill Box", "Fix Box", "Delete Box", "Grog Analysis", "How to use Cave", "Ugh! I understand".
  - Code/Messages: "Grog is awake!", "Grog say: Bad Math!", "Brain is dead. Cannot start math.", "Grog broke building graph", "rocks".
  - Secrets: `'caveman-secret'`.
- **Typo in Topics / Documentation:**
  - Topic typo note: `"destributed-systems"` -> `"distributed-systems"`.
- **Dead Code:**
  - `TUTORIAL_TEXT` and `showTutorial` duplicated in `Canvas.tsx` (now handled in `App.tsx`).
  - `/api/architecture/validate` is dead code since frontend calls `/api/simulation/start` directly.
- **Untested Modules:**
  - `backend/app.py`: 0% test coverage.
  - `backend/api/*`: 0% test coverage for API endpoints.
  - `backend/core/simulation_manager.py`: 0% test coverage for lifecycle/threading.
  - `backend/simulation/components.py`: `Cache`, `MessageQueue`, `Worker`, `LoadBalancer`, `Database` have zero unit tests.
  - Frontend: 0 automated tests.
- **Hard-Coded Paths & Configurations:**
  - Frontend hard-codes `http://localhost:5000` in `Canvas.tsx` for both HTTP fetch and Socket.io.
  - Ports are hardcoded: backend (5000), frontend (3001). No `.env.example` file.
  - No `Makefile` for standard development tasks (`make up`, `make down`, `make test`, `make lint`).
  - Missing formal `LICENSE` file in repository root.
