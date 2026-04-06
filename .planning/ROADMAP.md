# Roadmap: DMC Grinding GUI

## Milestones

- ✅ **v1.0 MVP** — Phases 1-7 (shipped 2026-04-06) | Phase 8 deferred
- 🚧 **v1.1 Deployment** — Phase 8: Pi Kiosk (pending hardware validation)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-7) — SHIPPED 2026-04-06</summary>

- [x] **Phase 1: Auth and Navigation** — PIN login, three-tier roles, tab bar (4/4 plans, completed 2026-04-04)
- [x] **Phase 2: RUN Page** — Cycle controls, live axis positions, E-STOP, Knife Grind Adjustment (4/4 plans, completed 2026-04-04)
- [x] **Phase 3: Live Matplotlib Plot** — Embedded A/B position plot at 5 Hz (1/1 plan, completed 2026-04-04)
- [x] **Phase 4: Axes Setup and Parameters** — Unified jog/teach screen and grouped parameter editor (3/3 plans, completed 2026-04-04)
- [x] **Phase 5: CSV Profile System** — Import/export with machine-type validation and diff preview (3/3 plans, completed 2026-04-04)
- [x] **Phase 6: Machine-Type Differentiation** — Flat Grind, Convex Grind, Serration Grind support (3/3 plans, completed 2026-04-04)
- [x] **Phase 7: Admin and User Management** — Admin CRUD screen for users, PINs, and roles (2/2 plans, completed 2026-04-06)

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### 🚧 v1.1 Deployment (In Progress)

- [ ] **Phase 8: Pi Kiosk and Deployment** — Kiosk lockout, systemd autostart, SD card packaging

### Phase 8: Pi Kiosk and Deployment
**Goal**: The app boots automatically on a Raspberry Pi into a locked-down kiosk with no path for operators to reach the desktop, and installs from an SD card
**Depends on**: Phase 6 (complete)
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05
**Status**: Deferred — awaiting hardware validation of Phases 1-7 on real DMC controller
**Success Criteria** (what must be TRUE):
  1. Raspberry Pi boots directly into the app with no desktop, browser, or file manager accessible to the operator
  2. There is no keyboard shortcut, swipe, or tap sequence that exits the app without Setup or Admin credentials
  3. App restarts automatically if it crashes (systemd Restart=always)
  4. A technician can deploy the app to a new Pi by writing an SD card image and inserting it — no pip install or internet connection required
  5. The same codebase runs as a standard window on Windows 11 with no kiosk behavior
**Plans**: TBD (context captured in `08-CONTEXT.md`)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Auth and Navigation | v1.0 | 4/4 | Complete | 2026-04-04 |
| 2. RUN Page | v1.0 | 4/4 | Complete | 2026-04-04 |
| 3. Live Matplotlib Plot | v1.0 | 1/1 | Complete | 2026-04-04 |
| 4. Axes Setup and Parameters | v1.0 | 3/3 | Complete | 2026-04-04 |
| 5. CSV Profile System | v1.0 | 3/3 | Complete | 2026-04-04 |
| 6. Machine-Type Differentiation | v1.0 | 3/3 | Complete | 2026-04-04 |
| 7. Admin and User Management | v1.0 | 2/2 | Complete | 2026-04-06 |
| 8. Pi Kiosk and Deployment | v1.1 | 0/TBD | Deferred | - |
