# Discrete-Event Simulation Engine Validation Report

**Generated:** 2026-10-21 12:13:57Z  
**Methodology:** Automated verification of the discrete-event simulation engine against closed-form queueing theory results, Little's Law, and stochastic overload models.

## Summary of Results

| Category | Metric | Analytic Formula | Theoretical | Simulated | Relative Error | Sample Size | Status |
|:---------|:-------|:-----------------|:------------|:----------|:---------------|:------------|:-------|
| M/M/1 Queue | Mean Time in System (W) | `1 / (mu - lambda)` | 0.5000 s | 0.5094 s | 1.88% | 23,997 reqs | **PASS** |
| M/M/1 Queue | Server Utilization (rho) | `lambda / mu` | 0.8000 | 0.7975 | 0.31% | 23,997 reqs | **PASS** |
| M/M/1 Queue | Mean Wait in Queue (W_q) | `lambda / (mu * (mu - lambda))` | 0.4000 s | 0.4097 s | 2.42% | 23,997 reqs | **PASS** |
| M/M/c Queue | Erlang C Mean Queue Wait (W_q) | `C(c, r) / (c*mu - lambda)` | 0.0889 s | 0.0868 s | 2.34% | 29,979 reqs | **PASS** |
| M/M/c Queue | Mean Time in System (W) | `W_q + 1 / mu` | 0.2889 s | 0.2868 s | 0.72% | 29,979 reqs | **PASS** |
| M/M/c Queue | Multi-Server Utilization (rho) | `lambda / (c * mu)` | 0.6667 | 0.6662 | 0.07% | 29,979 reqs | **PASS** |
| Little's Law: M/M/1 (c=1, exp) | System Occupancy (L) | `lambda_eff * W` | 2.7827 | 2.7853 | 0.09% | 14,997 reqs | **PASS** |
| Little's Law: M/M/3 (c=3, exp) | System Occupancy (L) | `lambda_eff * W` | 4.2001 | 4.2005 | 0.01% | 27,091 reqs | **PASS** |
| Little's Law: M/D/1 (c=1, const) | System Occupancy (L) | `lambda_eff * W` | 1.3371 | 1.3372 | 0.01% | 15,988 reqs | **PASS** |
| Overload (M/M/1/K) | Drop Rate (Blocking Prob P_b) | `(1-rho)*rho^K / (1-rho^(K+1))` | 50.79% | 50.64% | 0.31% | 39,940 arrivals | **PASS** |
| PRNG Determinism | Bit-for-Bit Parity (Seed=42) | `Deterministic PRNG stream` | Identical | Identical (100% match) | 0.00% | 1,434 events | **PASS** |

## Tolerance Justifications & Theoretical Formulations

### 1. M/M/1 Queue
- **Formulas**:
  - Mean time in system: $$W = \frac{1}{\mu - \lambda}$$
  - Server utilization: $$\rho = \frac{\lambda}{\mu}$$
  - Mean queue wait time: $$W_q = \frac{\lambda}{\mu(\mu - \lambda)}$$
- **Parameters**: $$\lambda = 8.0$$ req/s, $$\mu = 10.0$$ req/s, $$T = 3000.0$$ s virtual time.
- **Tolerances**: Under the Central Limit Theorem for sample size $$N > 20,000$$, stochastic variance yields relative error within 3% of theoretical values.

### 2. M/M/c Multi-Server Queue (Erlang C)
- **Formulas**:
  - Erlang C queuing probability: $$C(c, r) = \frac{\frac{r^c}{c!(1 - \rho)}}{\sum_{k=0}^{c-1} \frac{r^k}{k!} + \frac{r^c}{c!(1 - \rho)}}$$ where $$r = \frac{\lambda}{\mu}$$ and $$\rho = \frac{r}{c}$$.
  - Mean queue wait time: $$W_q = \frac{C(c, r)}{c\mu - \lambda}$$
  - Mean time in system: $$W = W_q + \frac{1}{\mu}$$
- **Parameters**: $$c = 3$$, $$\lambda = 10.0$$ req/s, $$\mu = 5.0$$ req/s per worker.
- **Tolerances**: With $$N > 25,000$$ requests, measured waiting times and utilization match Erlang C within 3% relative error.

### 3. Little's Law ($L = \lambda W$)
- **Formulation**: In any ergodic system, the time-average number of requests in the system ($$L$$) equals the effective throughput ($$\lambda_{\text{eff}}$$) multiplied by the mean time spent in the system ($$W$$).
- **Validation**: Verified across exponential single-server, exponential multi-server, and deterministic (constant) service time queues.
- **Tolerances**: Exact area-integral accumulation yields $$< 0.1\%$$ relative error.

### 4. Overload with Bounded Queue ($M/M/1/K$)
- **Formulation**: For an overloaded queue ($$\rho = \lambda / \mu > 1$$) with finite capacity $$K = c + \text{max\_queue}$$, the drop rate equals the blocking probability:
  $$P_b = \frac{(1 - \rho)\rho^K}{1 - \rho^{K+1}}$$
- **Parameters**: $$\lambda = 20.0$$, $$\mu = 10.0$$ ($$\rho = 2.0$$), $$c = 1$$, $$\text{max\_queue} = 4$$ ($$K = 5$$).
- **Theoretical Blocking**: $$P_b = \frac{(1-2) \cdot 2^5}{1 - 2^6} = \frac{32}{63} \approx 50.7937\%$$.
- **Tolerances**: Converges within 1.5% relative error over 40,000 arrivals.

### 5. Seeded PRNG Determinism
- Independent simulation runs with identical seeds (`seed=42`) produce 100% bit-for-bit identical latency vectors, throughput, and event timestamps.
- Varying the seed guarantees divergent stochastic realizations.