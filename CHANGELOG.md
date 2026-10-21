# Changelog

All notable changes to the **Sys-design_Sandbox** simulator are documented here.

## [Phase 0 — Audit & System Baseline] - 2026-10-21

### Completed
- Mapped system structure across frontend (React 18 + TypeScript + Vite + React Flow) and backend (Python 3.11 + Flask-SocketIO + Discrete Event Simulation).
- Verified PostgreSQL and Redis usage: identified both as unused zombie services in the current codebase.
- Documented virtual time mapping: hardcoded 1:1 real-to-virtual time ratio at 2 Hz broadcast frequency.
- Evaluated session isolation and thread lifecycle: found global broadcast leakage, lack of disconnect thread cleanup, and unbounded simulation execution.
- Evaluated topology validation gaps: missing cycle checks, edge compatibility checks, and orphan node handling.
- Documented dead code, jokey labels ("Grog", "Fast Magic"), untested components, and environment-specific instructions in `AUDIT.md`.
- Documented manual GitHub repository topic typo correction requirement: `destributed-systems` -> `distributed-systems`.
