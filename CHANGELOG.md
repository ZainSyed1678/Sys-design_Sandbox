# Changelog

All notable changes to the **Sys-design_Sandbox** simulator are documented here.

## [Phase 4 — Richer Components and Traffic] - 2026-10-21

### Completed
- **Advanced Load Balancing Strategies (`backend/simulation/load_balancer.py`):**
  - Implemented `round_robin`, `least_connections`, `weighted`, `random`, and `consistent_hashing`.
  - Built `ConsistentHashRing` with virtual nodes to minimize rehash key movement.
- **New Distributed Infrastructure Components (`backend/simulation/rich_components.py`):**
  - **`ReadReplicaDatabase`:** Read/Write splitting directing writes to primary and reads to replicas with asynchronous replication lag.
  - **`ShardedDatabase`:** Deterministic MD5 hash partitioning distributing data across database shards.
  - **`CDN`:** Edge cache layer with high hit rates and low latency, routing misses to origin.
  - **`APIGateway`:** Path-prefix request routing and token bucket rate limiting.
  - **`AutoscalingGroup`:** Automatic capacity scaling triggered by utilization thresholds with configurable startup delay and cooldowns.
- **Cache Lifecycle & Stampede Modeling (`backend/simulation/cache_model.py`):**
  - Fixed-capacity LRU eviction queue and TTL key expiration.
  - Cold-start restart period modeling cache stampede onto downstream databases.
- **Realistic Traffic Profiles (`backend/simulation/traffic.py`):**
  - Configurable traffic patterns: `CONSTANT`, `POISSON`, `RAMP`, `STEP_SPIKE`, `DIURNAL_SINE`, and `BURSTY` (on/off cycles).
- **Unit Test Suite (`backend/tests/test_rich_components.py`):**
  - Added 12 comprehensive unit tests covering all 5 load balancer strategies, read replicas, sharding, CDN, API gateways, autoscaling, cache eviction/TTL, and traffic patterns.

## [Phase 3 — Failure Modeling (Retries, Timeouts, Circuit Breakers)] - 2026-10-21

### Completed
- **Resilience Engine & Policies (`backend/simulation/resilience.py`):**
  - **Circuit Breaker:** Implemented three-state state machine (`CLOSED`, `OPEN`, `HALF_OPEN`) with configurable failure threshold, recovery timeout, half-open probe concurrency, and success threshold.
  - **Token Bucket Rate Limiting / Load Shedding:** Continuous token accumulation based on elapsed virtual time, burst capacity, and refill rate.
  - **Retry Policy:** Configurable max attempts, fixed/exponential backoff, seeded uniform full jitter via engine PRNG, and optional retry budget ratio.
- **Richer Failure Modes:**
  - **Partial Degradation:** Dynamic latency multiplier (`COMPONENT_DEGRADED`, `COMPONENT_RESTORED`) scaling component execution durations.
  - **Intermittent Failures:** Configurable failure probability $p \in [0, 1]$ evaluated via seeded PRNG.
  - **Network Partitions:** Selective bidirectional edge partitions (`NETWORK_PARTITION`, `NETWORK_REPAIR`) in `SimulationEngine`, severing communication between specific node pairs while maintaining broader network reachability.
- **Component Resilience Integration:**
  - **`Client`:** Configurable request timeouts (`REQUEST_TIMEOUT`), retry scheduling (`RETRY_ATTEMPT`), retry budget enforcement, and optional circuit breaker protection.
  - **`APIServer`:** Circuit breaker protection for downstream dependencies (fast-failing with zero delay when OPEN), downstream timeouts, and load shedding via token buckets.
  - **`Database` & Workers:** Support for degradation multipliers, token bucket admission, and network partition checks.
- **Comprehensive Resilience Test Suite (`backend/tests/test_resilience.py`):**
  - Verified retry storm load amplification during database outage (amplification factor $> 1.5\times$).
  - Verified circuit breaker tripping OPEN, fast-failing traffic, preventing queue saturation, and recovering to CLOSED.
  - Verified retry budget strictly capping retry attempts during sustained outages.
  - Verified timeouts without retries dropping degraded requests with amplification factor strictly equal to 1.0.
  - Verified token bucket load shedding and burst rate limits.
  - Verified component latency degradation and selective network partition isolation.

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
