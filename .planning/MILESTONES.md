# Milestones

## v1.0 MVP (Shipped: 2026-04-06)

**Phases:** 7 of 8 complete (Phase 8 deferred) | **Plans:** 20 | **Commits:** 160 | **LOC:** 13,412 src + 2,013 test
**Timeline:** 2025-08-14 → 2026-04-06
**Git range:** `3717416..007a76a`

**Key accomplishments:**
1. PIN-based auth with 3-tier roles (Operator/Setup/Admin), touchscreen numpad overlay, idle auto-lock
2. Full RUN page with cycle controls, live axis positions at 10 Hz, E-STOP, Knife Grind Adjustment bar chart
3. Live matplotlib A/B position plot at 5 Hz with rolling 750-point buffer, touch interaction disabled for E-STOP safety
4. Unified Axes Setup (jog/teach/quick actions) and grouped Parameters editor with validation and dirty tracking
5. CSV profile import/export with machine-type validation, diff preview, and cycle safety interlock
6. Machine-type differentiation — all screens adapt to Flat Grind, Convex Grind, or Serration Grind
7. Admin user management screen with CRUD overlay for names, PINs, and roles

**Known Gaps:**
- DEPLOY-01 through DEPLOY-05: Pi kiosk mode, SD card deployment, operator lockout — deferred to v1.1 pending hardware validation

---

## v2.0 Flat Grind Integration (Shipped: 2026-04-07)

**Phases:** 9 (Phase 9-17) | **Plans:** 17 | **Commits:** ~30
**Timeline:** 2026-04-06 → 2026-04-07
**Git range:** `007a76a..HEAD`

**Key accomplishments:**
1. DMC Foundation — HMI trigger variables (hmiGrnd, hmiSetp, hmiMore, hmiLess, hmiNewS, hmiHome, hmiJog, hmiCalc), dmc_vars.py constants, hmiState at every state boundary
2. State Polling — 10 Hz controller poll, MachineState subscription, knife count, disconnect detection
3. E-STOP Safety — Priority stop via submit_urgent(), motion gate on all buttons, RECOVER flow
4. Run Page Wiring — Start Grind, Go To Rest, Go To Start, More/Less Stone, New Session, live plot during grind
5. Setup Loop — Enter/exit setup mode, home, jog, teach rest/start points, parameter write + recalc
6. State-Driven UI — Button enable/disable from hmiState, status labels, setup badge, tab gating
7. Gap closures — Stone Compensation card (Phase 15), ProfilesScreen setup fix (Phase 16), poll reset fix (Phase 17)

**Key decisions:**
- HMI one-shot variable pattern (default=1, send 0 to trigger, reset to 1)
- No XQ direct calls except recover() XQ #AUTO
- Single gclib handle serialized through jobs FIFO worker
- BV only on explicit user save
- E-STOP uses submit_urgent(), never queued

**Known Gaps:**
- Hardware validation pending on real DMC controller for all phases
- Phase 8 (Pi kiosk) still deferred

---

