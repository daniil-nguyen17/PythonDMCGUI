---
gsd_state_version: 1.0
milestone: v4.1
milestone_name: Security, Polish & Code Health
status: unknown
stopped_at: Completed 31-03-PLAN.md (Phase 31 fully complete)
last_updated: "2026-05-05T02:06:37.950Z"
last_activity: 2026-05-04 — Phase 31 complete (3/3 plans — field bugs fixed, UI spacing tokens standardized, touch targets remediated)
progress:
  total_phases: 28
  completed_phases: 8
  total_plans: 18
  completed_plans: 18
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-28)

**Core value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.
**Current focus:** v4.1 — Phase 31: Bug Fixes and UI Polish

## Current Position

```
Milestone : v4.1 Security, Polish & Code Health
Phase     : 31 of 35 (Bug Fixes and UI Polish)
Plan      : 03 of 03 complete
Status    : Phase complete
Progress  : [██████████] 100%
```

Last activity: 2026-05-04 — Phase 31 complete (3/3 plans — field bugs fixed, UI spacing tokens standardized, touch targets remediated)

## v4.1 Phase Map

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 30 | Codebase Audit | AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04 | Complete (3/3 plans) |
| 31 | Bug Fixes and UI Polish | FIX-03, FIX-04, FIX-05, UI-01, UI-02 | Complete (3/3 plans) |
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
- [Phase 30]: N rules excluded from ruff select — naming convention changes deferred to Plan 02
- [Phase 30]: Vulture allowlist auto-generated from KV file parsing, not hand-maintained
- [Phase 30]: Kivy deferred imports use targeted noqa E402 rather than blanket file-level ignore
- [Phase 30 Plan 02]: Exception class aliases retained (ControllerNotReady = ControllerNotReadyError) for backward-compat; internal code uses Error-suffixed primary name
- [Phase 30 Plan 02]: N-rules applied across all 5 affected files, not just controller.py — ruff revealed violations in main.py, base.py, convex/run.py, flat_grind/run.py
- [Phase 30 Plan 03]: Use ast.iter_child_nodes (not ast.walk) to avoid flagging inner closures as requiring docstrings
- [Phase 30 Plan 03]: Kivy on_* callbacks treated as public — require docstrings regardless of _ prefix convention
- [Phase 30 Plan 03]: Non-obvious private threshold set at >15 body lines (not >10) to avoid over-flagging trivial helpers
- [Phase 31 Plan 02]: Kept _classify_resolution() signature for API stability despite always returning '15inch'
- [Phase 31 Plan 02]: Spacing token scale locked at 4/8/12/16/24dp for all shared KV padding/spacing
- [Phase 31]: GL backend log runs on ALL platforms (not just Windows) — logs 'default (platform gl)' on Linux
- [Phase 31]: Platform guard fully removed from start() — _loop already handles --direct flag per-platform
- [Phase 31 Plan 03]: Delta-C panel height increased to accommodate 44dp buttons; bComp size_hint_x: 0.2 kept (verified > 44dp via parent width)
- [Phase 31 Plan 03]: Token-scale enforcement complete project-wide — all 21 KV files use only 4/8/12/16/24dp for padding/spacing

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

Last session: 2026-05-04T06:15:00.000Z
Stopped at: Completed 31-03-PLAN.md (Phase 31 fully complete)
Resume file: None
Next action: Begin Phase 32 planning (Per-Machine Parameters)
