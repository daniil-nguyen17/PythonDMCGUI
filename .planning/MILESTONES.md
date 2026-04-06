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

