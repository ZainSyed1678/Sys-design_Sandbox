# System Design Simulator

An interactive, real-time distributed system design sandbox where engineers visually design, simulate, stress-test, and analyze software architectures.

The platform provides dual-mode modeling:
- **High-Level System Design (HLD):** Visual infrastructure composition, discrete-event queueing simulation, live WebSockets streaming, chaos fault injection, and automated bottleneck analysis.
- **Low-Level System Design (LLD):** Object-oriented UML component modeling, contracts, specifications editing, and real-time TypeScript & Python code generation.

---

## Key Features

### 1. High-Level System Design (HLD) Simulator
- **Interactive Visual Canvas:** Drag, connect, and configure infrastructure components using React Flow.
- **Components Supported:**
  - **Client:** Configurable request generation rates (requests/sec).
  - **Load Balancer:** Round-robin request distribution across backend endpoints.
  - **API Server:** Concurrency capacity limits and processing latency.
  - **Database:** Processing latency and connection limits.
  - **Cache:** Hit/miss ratio simulation (e.g. 80% hit rate) and low-latency responses.
  - **Message Queue:** FIFO buffer with queue depth limits and backpressure tracking.
  - **Worker:** Asynchronous queue consumers processing background jobs.
- **Discrete Event Simulation Engine:**
  - Fully decoupled engine using a priority queue (`heapq`) and simulated virtual time.
  - Deterministic replay support via seedable pseudorandom generation.
- **Real-Time Streaming:**
  - Live metric broadcasts over WebSockets (`Flask-SocketIO`).
  - Visual node indicators: active requests, capacity utilization gauges, completed requests, and dropped requests.
- **Chaos Engineering & Failure Injection:**
  - Fail or recover individual components live during simulation.
  - Observe cascading downstream failures (e.g., database failure causing upstream API queue saturation and request drops).
- **Architecture Analysis Engine:**
  - Real-time heuristic evaluation of component utilization and topology.
  - Detects overloaded nodes, queue overflows, single points of failure, and dead dependencies.
  - Emits actionable architectural remediation recommendations.

### 2. Low-Level System Design (LLD) Studio
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
│  │  - Metrics & Gauges     │ │ - Spec Drawer / Code │  │
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
│  │ Architecture Analyzer (Deterministic Rule Engine) │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, React Flow, Socket.io-client |
| **Backend** | Python 3.11, Flask, Flask-SocketIO, Werkzeug, Pydantic |
| **Simulation** | Discrete Event Simulation (`heapq`), Seeded PRNG |
| **Infrastructure** | Docker, Docker Compose, PostgreSQL 15, Redis 7 |
| **Testing** | Pytest |

---

## Getting Started

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- Alternatively: Node.js 18+ and Python 3.11+ for local development

### Configuration
Copy the sample environment file:
```bash
cp .env.example .env
```
Default ports:
- Frontend: `3001`
- Backend API: `5000`

### Quick Start with Docker
```bash
# Build and run all services
make up

# View logs
docker compose logs -f

# Shut down services
make down
```

### Access the Application
- **Frontend UI:** [http://localhost:3001](http://localhost:3001)
- **Backend API Health Check:** [http://localhost:5000/api/health](http://localhost:5000/api/health)

---

## Development Workflow (Makefile)

A standard `Makefile` is provided for common development tasks:

```bash
make help          # Show available targets
make up            # Start Docker Compose services
make down          # Stop Docker Compose services
make test          # Run backend unit test suite
make lint          # Run backend code linter
make dev-backend   # Run Flask backend locally
make dev-frontend  # Run Vite frontend dev server locally
```

---

## How to Use

### Simulating a Distributed Outage (HLD)
1. Open `http://localhost:3001` (defaults to **High Level System Design**).
2. Click **+ Client**, **+ API Server**, and **+ Database** from the left toolbar.
3. Connect `Client` ➔ `API Server` ➔ `Database` by dragging between handles.
4. Click **Start Simulation** to begin traffic flow.
5. Click the **Database** node to select it, then click **Fail Node** in the top toolbar.
6. Observe the cascading failure:
   - The Database stops processing requests.
   - The API Server's active concurrency capacity saturates.
   - The API Server begins dropping requests (`Drop` counter climbs).
   - The **Architecture Analysis** panel flags the failure and provides actionable remediation steps.
7. Click **Recover Node** to restore the Database and observe system throughput recovery.

### Modeling Code Contracts (LLD)
1. Click **🧩 Low Level System Design** in the top-right mode switcher.
2. Click **+ Interface** to create `IUserService` and **+ Service** to create `UserService`.
3. Connect `UserService` to `IUserService` (`implements`).
4. Click `UserService` to open the **Specifications Drawer** on the right.
5. Add fields (e.g. `- userRepo: IUserRepository`) and methods (e.g. `+ findById(id: string): User`).
6. Switch to the **Code Preview** tab to inspect the generated TypeScript or Python skeleton.

---

## Running Tests

Run the test suite using `make test` or directly via `pytest`:

```bash
pytest backend/tests/
```

Current test suite covers:
- `test_engine_basic_flow`: End-to-end event dispatching and throughput.
- `test_api_drop_requests`: Concurrency capacity thresholds and drop behavior.
- `test_component_failure_and_recovery`: Chaos failure and recovery mechanics.
- `test_deterministic_engine_seed`: Seed reproducibility verification.
- `test_analyzer_detects_overloaded_component`: Saturated node detection.
- `test_analyzer_detects_queue_overflow`: Queue depth and backpressure threshold alerts.
- `test_analyzer_detects_dead_component`: Health tracking alerts.

---

## Repository Settings & Manual Maintenance

### GitHub Topics (Manual Configuration in GitHub Repo Settings)
Please ensure the repository topics on GitHub are configured with the following tags:
- `system-design`
- `distributed-systems` (corrected from typo `destributed-systems`)
- `discrete-event-simulation`
- `react`
- `typescript`
- `python`
- `flask`
- `software-architecture`

### Repository Renaming
- Target repository name: `system-design-simulator` (currently `Sys-design_Sandbox`).
- Please perform this rename manually via GitHub Repository Settings ➔ General ➔ Repository Name.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
