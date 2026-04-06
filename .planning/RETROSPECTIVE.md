# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-04-06
**Phases:** 7 (of 8; Phase 8 deferred) | **Plans:** 20 | **Commits:** 160

### What Was Built
- PIN-based auth system with 3-tier roles, touchscreen numpad overlay, idle auto-lock
- Full operator RUN page with cycle controls, live axis positions, E-STOP, Knife Grind Adjustment
- Live matplotlib A/B position plot at 5 Hz with rolling 750-point buffer
- Unified Axes Setup (jog/teach/quick actions) and grouped Parameters editor
- CSV profile import/export with machine-type validation and diff preview
- Machine-type differentiation — all screens adapt to Flat/Convex/Serration Grind
- Admin user management screen with CRUD overlay

### What Worked
- Phase-by-phase execution with context/research/plan/execute pipeline kept scope tight
- TDD approach for pure Python modules (AuthManager, CSV engine, machine_config) caught bugs early
- Verification checkpoints at end of each phase caught visual/functional issues before moving on
- Separating plot clock (5 Hz) from poll clock (10 Hz) solved E-STOP responsiveness concern upfront
- Machine config registry pattern made Phase 6 screen adaptation clean and extensible

### What Was Inefficient
- Phase 1 Plan 04 (visual verification) was separate from execution — could have been integrated into Plan 03
- Some SUMMARY.md files lacked one-liner fields, requiring manual extraction at milestone close
- Convex/Serration parameter definitions are stubs pending real DMC variable lists from customer — tech debt carried forward

### Patterns Established
- Config.set calls at top of main.py before any Kivy imports (Pitfall 13 prevention)
- Background thread pool for controller I/O, Clock.schedule_once for UI thread callbacks
- machine_config._REGISTRY keyed by type string with plug-in param_defs
- AuthManager plain JSON with plain-text PINs (acceptable per project scope)
- ModalView overlays for PIN entry, user editing, and confirmations
- Role-gated TabBar with dynamic tab visibility on auth change

### Key Lessons
1. Deferring Pi kiosk (Phase 8) until after hardware validation was the right call — testing features on real hardware before locking down the OS prevents debugging friction
2. The verification checkpoint pattern (human-in-the-loop at each phase end) catches issues that automated tests miss, especially visual layout problems
3. kivy_matplotlib_widget was a better choice than raw FigureCanvasKivyAgg for the live plot — provided MatplotFigure with touch mode control out of the box

### Cost Observations
- Model mix: predominantly opus for planning/execution, sonnet for research agents
- Notable: Phases 2-7 executed rapidly after Phase 1 established the app shell pattern

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Commits | Phases | Key Change |
|-----------|---------|--------|------------|
| v1.0 | 160 | 7 | Established GSD pipeline: context → research → plan → execute → verify |

### Cumulative Quality

| Milestone | Test LOC | Source LOC | Ratio |
|-----------|----------|------------|-------|
| v1.0 | 2,013 | 13,412 | 15% |
