# Changelog

All notable changes to the **Sys-design_Sandbox** simulator are documented here.

## [Phase 2 — Simulation Correctness and Validation] - 2026-10-21

### Completed
- **Stochastic Service & Arrival Models:**
  - Implemented `Distribution` and `DistributionType` (`backend/simulation/distributions.py`) supporting `constant`, `exponential`, `lognormal`, and `poisson` distributions.
  - Parameterized service times and arrival processes to be driven exclusively by seeded PRNG (`random.Random(seed)`).
- **Explicit Multi-Server Queueing:**
  - Implemented explicit queueing mechanics across server components (`APIServer`, `Database`, `Worker`): concurrency $c \ge 1$ workers, bounded/unbounded waiting queue, FIFO dispatching, and queue overflow dropping.
  - Added continuous area-integral accumulation (`area_busy`, `area_queue`, `area_system`) for exact server utilization ($\rho = \frac{\int \text{active}(t) dt}{c \cdot T}$), time-average queue length ($L_q$), and system occupancy ($L$).
- **Deterministic Latency & Metrics Tracking:**
  - Replaced nondeterministic `uuid.uuid4()` with sequential request generation (`req_{comp}_{id}`).
  - Added total ordering and deterministic tie-breaking in `Event` via sequential `event_id` and priority.
  - Implemented end-to-end and per-hop latency tracking recording arrival, queue wait, service execution, and exit.
  - Implemented percentiles computation: p50, p95, p99, mean, max, throughput, and drop rate.
  - Added fixed-size time window aggregation (`time_window_size = 1.0s`) for time series history.
- **Automated Analytic Queueing Validation Suite:**
  - Created `backend/tests/test_queueing.py` with rigorous tolerance justification:
    - $M/M/1$: Verified mean time in system $W = 1/(\mu - \lambda)$ and utilization $\rho = \lambda/\mu$ (1.88% and 0.31% relative error).
    - $M/M/c$: Verified Erlang C mean waiting time $W_q = \frac{C(c, r)}{c\mu - \lambda}$ and system time $W$ (2.34% and 0.72% relative error).
    - Little's Law: Verified $L = \lambda_{\text{eff}} W$ across single-server, multi-server, and deterministic queues ($< 0.1\%$ relative error).
    - Overload: Verified $M/M/1/K$ drop rate convergence to closed-form blocking probability $P_b = \frac{(1-\rho)\rho^K}{1-\rho^{K+1}}$ (0.31% relative error).
    - Determinism: Verified bit-for-bit identical latency and metrics traces across runs with identical seed.
- **Validation Script & Reporting:**
  - Created `scripts/validate_engine.py` to run automated verification and generate `docs/validation.md`.
  - Added `make validate` target to `Makefile`.
  - Updated `README.md` to link to `docs/validation.md` and quote verified empirical metrics.

## [Phase 1 — Professional Labels & Repo Hygiene] - 2026-10-21

### Completed
- Renamed all jokey/caveman text across frontend and backend ("Start Fast Magic" -> "Start Simulation", "Kill Box" -> "Fail Node", "Fix Box" -> "Recover Node", "Delete Box" -> "Delete Node", "Grog Analysis" -> "Architecture Analysis").
- Replaced jokey API responses and exceptions with professional, clear error messaging.
- Added MIT `LICENSE` file.
- Created root `Makefile` with standard targets (`make up`, `make down`, `make test`, `make lint`, `make dev-backend`, `make dev-frontend`).
- Created `.env.example` and parameterized ports, CORS origins, and API base URLs in `app.py`, `vite.config.ts`, `Canvas.tsx`, and `docker-compose.yml`.
- Standardized package naming (`sys-design-simulator-frontend` in `package.json`).
- Updated `README.md`: removed environment-specific instructions (e.g. "Inside WSL"), documented architecture, features, configuration, Makefile commands, and manual GitHub topics/rename steps.
- Noted manual GitHub repository maintenance actions:
  - Topic typo fix: change `destributed-systems` to `distributed-systems`.
  - Repository rename: rename `Sys-design_Sandbox` to `system-design-simulator`.

## [Phase 0 — Audit & System Baseline] - 2026-10-21

### Completed
- Mapped system structure across frontend (React 18 + TypeScript + Vite + React Flow) and backend (Python 3.11 + Flask-SocketIO + Discrete Event Simulation).
- Verified PostgreSQL and Redis usage: identified both as unused zombie services in the current codebase.
- Documented virtual time mapping: hardcoded 1:1 real-to-virtual time ratio at 2 Hz broadcast frequency.
- Evaluated session isolation and thread lifecycle: found global broadcast leakage, lack of disconnect thread cleanup, and unbounded simulation execution.
- Evaluated topology validation gaps: missing cycle checks, edge compatibility checks, and orphan node handling.
- Documented dead code, jokey labels ("Grog", "Fast Magic"), untested components, and environment-specific instructions in `AUDIT.md`.
- Documented manual GitHub repository topic typo correction requirement: `destributed-systems` -> `distributed-systems`.
