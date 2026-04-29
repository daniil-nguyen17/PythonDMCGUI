---
gsd_state_version: 1.0
milestone: v4.1
milestone_name: Security, Polish & Code Health
status: active
stopped_at: Roadmap created — Phase 30 ready to plan
last_updated: "2026-04-28T00:00:00.000Z"
last_activity: 2026-04-28 — v4.1 roadmap written, 6 phases defined (30-35)
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-28)

**Core value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.
**Current focus:** v4.1 — Phase 30: Codebase Audit

## Current Position

```
Milestone : v4.1 Security, Polish & Code Health
Phase     : 30 of 35 (Codebase Audit)
Plan      : —
Status    : Ready to plan
Progress  : [░░░░░░░░░░] 0%
```

Last activity: 2026-04-28 — v4.1 roadmap created (Phases 30-35), 18 requirements mapped

## v4.1 Phase Map

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 30 | Codebase Audit | AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04 | Not started |
| 31 | Bug Fixes and UI Polish | FIX-03, FIX-04, FIX-05, UI-01, UI-02 | Not started |
| 32 | Per-Machine Parameters | PARAM-01, PARAM-02 | Not started |
| 33 | Licensing Core | LIC-01, LIC-02, LIC-03, LIC-04 | Not started |
| 34 | Pi Cython Protection | PROT-01, PROT-03 | Not started |
| 35 | Windows PyArmor Protection | PROT-02, PROT-03 | Not started |

Note: PROT-03 (controller.py exclusion) is a constraint that applies to both Phase 34 and Phase 35.

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
v1.0-v4.0 phase-level decisions archived in `.planning/milestones/` and prior STATE.md sessions.

Decisions affecting v4.1 work:
- Audit before protecting — don't compile dead code into .so (Phase 30 gates 34 and 35)
- Vulture requires Kivy _REGISTRY allowlist to avoid false positives on screen class names
- MAC address rejected as Pi fingerprint — use /proc/cpuinfo Serial only (USB NIC changes cause lockout)
- PyArmor pack + PyInstaller 6 is broken — use two-step: obfuscate first, then PyInstaller reads obfuscated tree
- controller.py excluded from all compilation/obfuscation targets (gclib ctypes boundary — silent failure risk)
- ARM .so files are Python-version-locked — pin Python version in install.sh before Phase 34
- License check inserts into main.py pre-Kivy block (after setup_logging(), before _detect_preset())
- Online activation/revocation server is out of scope — air-gapped factory, offline JSON license only

### Open Questions (from research)

- PyArmor paid license cost — verify before starting Phase 35
- Convex machine parameter specifications — needed for Phase 32 (PARAM-01)
- Windows 11 build version on field machines — determines `wmic` vs PowerShell fingerprint path (Phase 33)
- Pi Python version pinning — confirm exact version on target Bookworm build before Phase 34

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 35 (PyArmor) gated on paid license purchase — confirm before planning
- Convex param specs not yet provided — Phase 32 blocked until customer sign-off on DMC variable names

## Session Continuity

Last session: 2026-04-28
Stopped at: v4.1 roadmap created, files written
Resume file: None
Next action: `/gsd:plan-phase 30` — Codebase Audit
