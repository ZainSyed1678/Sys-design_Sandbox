# System Design Simulator & Sandbox (HLD & LLD)

An interactive, real-time distributed system design sandbox where engineers visually design, simulate, stress-test, and analyze software architectures. 

The platform supports both **High-Level System Design (HLD)** (distributed infrastructure, discrete-event simulation, chaos injection, bottleneck analysis) and **Low-Level System Design (LLD)** (UML object-oriented modeling, class specifications, and real-time code generation).

---

## Key Features

### 🌐 1. High-Level System Design (HLD) Simulator
- **Interactive Visual Canvas:** Drag, connect, and configure infrastructure components using React Flow.
- **Components Supported:**
  - **Client:** Configurable request generation rates (req/sec).
  - **Load Balancer:** Round-robin request routing across backend targets.
  - **API Server:** Configurable concurrency capacity and processing latency.
  - **Database:** Disk/transaction processing latency with connection limits.
  - **Cache:** Configurable hit/miss ratio (e.g. 80% hit rate) and low latency lookups.
  - **Message Queue:** Buffer depth thresholds and backpressure control.
  - **Worker:** Asynchronous queue consumers handling background jobs.
- **Discrete Event Simulation Engine:**
  - Standalone engine decoupled from the web framework, using a priority queue (`heapq`) and simulated virtual time.
  - Deterministic replay support via seedable pseudorandom generation.
- **Real-Time Streaming:**
  - Live metric broadcasts over WebSockets (`Flask-SocketIO`).
  - Visual node indicators: real-time active requests, capacity utilization bars, completed requests, and dropped requests.
- **Chaos Engineering & Failure Injection:**
  - Kill or recover individual components live during simulation.
  - Observe cascading downstream failures (e.g., database failure causing API server connection saturation and request drops).
- **Deterministic Bottleneck Analysis Engine:**
  - Analyzes component metrics and graph topology in real time.
  - Detects overloaded nodes, queue overflows, single points of failure (SPOF), and dead downstream dependencies.
  - Emits actionable architectural recommendations.

### 🧩 2. Low-Level System Design (LLD) Studio
- **Dual-Mode Switcher:** Seamlessly toggle between High-Level Design (HLD) and Low-Level Design (LLD) without losing canvas state.
- **Object-Oriented Building Blocks:**
  - `Class` (concrete & abstract classes)
  - `Interface` (API contracts & abstract method definitions)
  - `Service` (domain business logic layer)
  - `Repository` (data access layer)
  - `Controller` (request handling / entrypoint layer)
  - `Design Pattern` (Strategy, Observer, Factory, Singleton, etc.)
- **Interactive Specifications Drawer:**
  - Define and edit typed attributes with visibility modifiers (`+` public, `-` private, `#` protected).
  - Define method signatures, parameters, and return types.
- **Real-Time Code Generation:**
  - Automatically translates UML class diagrams into syntax-highlighted **TypeScript** and **Python** class skeletons.
- **Relationship Modeling:**
  - Connect components to express `implements`, `extends`, `depends on`, and `uses` relationships.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│             Frontend (React 18 + TypeScript)           │
│  ┌─────────────────────────┐ ┌──────────────────────┐  │
│  │    HLD Canvas (ReactFlow)│ │   LLD Canvas (React) │  │
│  │  - Infrastructure Nodes │ │ - UML Class Nodes    │  │
│  │  - Metrics & Chaos Bars │ │ - Spec Drawer / Code │  │
│  └────────────▲────────────┘ └──────────────────────┘  │
└───────────────┼────────────────────────────────────────┘
                │ HTTP API & WebSockets (Socket.IO)
┌───────────────▼────────────────────────────────────────┐
│             Backend (Python 3.11 / Flask)              │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Flask Application & REST API (/api/simulation)    │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ SimulationManager (Thread & Lifecycle Controller)│  │
│  ├──────────────────────────────────────────────────┤  │
│  │ Discrete Event Engine (Priority Queue / Sim Time) │  │
│  ├──────────────────────────────────────────────────┤  │
│  │ Bottleneck Analyzer (Deterministic Rules Engine)  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, React Flow, Socket.io-client |
| **Backend** | Python 3.11, Flask, Flask-SocketIO, Werkzeug, Pydantic |
| **Simulation** | Discrete Event Simulation (`heapq`), Deterministic PRNG |
| **Infrastructure** | Docker, Docker Compose, PostgreSQL 15, Redis 7 |
| **Testing** | Pytest |

---

## Getting Started

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Git

### 1. Clone & Run with Docker Compose
```bash
git clone https://github.com/ZainSyed1678/Sys-design_Sandbox.git
cd Sys-design_Sandbox

# Build and start all services
docker-compose up --build -d
```

### 2. Access the Application
- **Frontend Canvas:** [http://localhost:3001](http://localhost:3001)
- **Backend API Health Check:** [http://localhost:5000/api/health](http://localhost:5000/api/health)

---

## How to Use

### Simulating a Distributed Outage (HLD)
1. Navigate to `http://localhost:3001` (default is **High Level System Design**).
2. Click **+ Client**, **+ API Server**, and **+ Database** from the left toolbar.
3. Connect `Client` ➔ `API Server` ➔ `Database` by dragging between handles.
4. Click **Start Fast Magic** to initiate traffic generation.
5. Click the **Database** node to select it, then click **Kill Box** in the top toolbar.
6. Observe the cascading failure:
   - The Database stops responding.
   - The API Server's active capacity saturates.
   - The API Server begins dropping requests (`Drop` count climbs).
   - The **Grog Analysis** panel flags the outage and provides remediation advice.
7. Click **Fix Box** to restore the Database and observe system recovery.

### Modeling Code Contracts (LLD)
1. In the top right corner, switch to **🧩 Low Level System Design**.
2. Click **+ Interface** to create `IUserService` and **+ Service** to create `UserService`.
3. Connect `UserService` to `IUserService` (implements).
4. Click `UserService` to open the **Specifications Drawer** on the right.
5. Add fields (e.g. `- userRepo: IUserRepository`) and methods (e.g. `+ findById(id: string): User`).
6. Switch to the **Code Preview** tab to inspect the generated TypeScript or Python skeleton.

---

## Running Tests

Backend unit tests cover the discrete event simulation engine, component failure/recovery cycles, seed determinism, and bottleneck analysis rules:

```bash
# Inside WSL / Linux or Docker backend container:
pytest backend/tests/
```

Test suite includes:
- `test_engine_basic_flow`: End-to-end event dispatching and throughput.
- `test_api_drop_requests`: Capacity threshold and request drop behavior.
- `test_component_failure_and_recovery`: Chaos failure and restoration mechanics.
- `test_deterministic_engine_seed`: Seed reproducibility verification.
- `test_analyzer_detects_overloaded_component`: Bottleneck detection for saturated nodes.
- `test_analyzer_detects_queue_overflow`: Backpressure and queue depth threshold detection.
- `test_analyzer_detects_dead_component`: Health tracking alerts.

---

## Project Roadmap

- [x] **Phase 0:** Project scaffolding & containerized dev environment.
- [x] **Phase 1:** Visual architecture canvas (React Flow).
- [x] **Phase 2:** Discrete event simulation engine MVP.
- [x] **Phase 3:** Threaded simulation manager & lifecycle API.
- [x] **Phase 4:** Real-time WebSockets streaming & live metric gauges.
- [x] **Phase 5:** Advanced components (Cache, Message Queue, Worker).
- [x] **Phase 6:** Chaos engineering, failure injection & deterministic seeding.
- [x] **Phase 7:** Deterministic bottleneck analysis & recommendation engine.
- [x] **LLD Studio:** Low-level object-oriented design & live code generator.
- [ ] **Phase 8:** AI System Design Mentor (LLM-guided architectural trade-off feedback).
- [ ] **Phase 9:** Production hardening (WSGI/Gunicorn, Nginx reverse proxy).
- [ ] **Phase 10:** Cloud deployment & CI/CD automation.

---

## License
MIT License. Created for interactive systems engineering and software architecture education.
