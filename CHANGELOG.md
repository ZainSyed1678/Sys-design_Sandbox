# Changelog

All notable changes to the **Sys-design_Sandbox** simulator are documented here.

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
