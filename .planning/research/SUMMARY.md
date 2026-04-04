# Project Research Summary

**Project:** DMC Grinding GUI — Milestone additions
**Domain:** Industrial touchscreen HMI — knife grinding machine control (CNC-adjacent)
**Researched:** 2026-04-04
**Confidence:** HIGH (codebase analysis + established industrial HMI domain knowledge)

## Executive Summary

This is an industrial machine control GUI running on a Raspberry Pi touchscreen, built with Python/Kivy/gclib to control a Galil motion controller for knife grinding machines. The codebase already has a solid, well-structured foundation: a proven `jobs.submit` / `Clock.schedule_once` threading pattern, a pub/sub `MachineState`, and a dark theme with axis color coding. The milestone adds PIN-based role authentication (Operator/Setup/Admin), live matplotlib position plotting, CSV profile import/export, tab navigation, and Raspberry Pi kiosk deployment. All of these must integrate cleanly with the existing patterns rather than replace them.

The recommended approach is stdlib-first: only `matplotlib>=3.8,<4` needs to be added to `pyproject.toml`. Authentication uses Python's `hashlib` + `sqlite3`, CSV I/O uses the `csv` module, and routing uses the existing Kivy `ScreenManager`. The key architectural additions are an `AuthManager` class, a `PinOverlay` modal, a `TabBar` replacing the current ActionBar spinner, and a unified `RunScreen` with embedded matplotlib canvas. Three machine types (4-Axis Flat, 4-Axis Convex, 3-Axis Serration) are handled by a `MachineConfig` dict and machine-type-aware screen rendering rather than separate full screen sets.

The highest-risk areas are (1) matplotlib thread safety — plot draws must never happen on the background job thread, only via `Clock.schedule_once` callbacks — and (2) CSV profile safety — loading a profile mid-cycle can move the machine unexpectedly. Both risks are well-understood and have clear prevention patterns. A secondary risk is Raspberry Pi OS Bookworm's Wayland/X11 transition, which requires deployment-time verification before kiosk mode can be finalized.

---

## Key Findings

### Recommended Stack

The existing stack (Python >=3.10, Kivy >=2.2.0, gclib system install, stdlib threading + `kivy.clock.Clock`) is a hard constraint — all new additions must fit within it. The only PyPI addition required is `matplotlib>=3.8,<4`, which ships with `FigureCanvasKivyAgg` as its Kivy backend and embeds directly as a Kivy Widget. Every other new capability (auth, CSV, routing, kiosk) is pure stdlib or OS-level configuration. Libraries like bcrypt, pandas, TinyDB, pyqtgraph, and kivy_garden.graph were explicitly evaluated and rejected as over-engineered or incompatible.

**Core technologies:**
- `matplotlib>=3.8,<4` (only new PyPI dep): live A/B position plot — `FigureCanvasKivyAgg` embeds as a Kivy Widget; `canvas.draw_idle()` batches redraws safely on the main thread
- `hashlib` + `sqlite3` (stdlib): PIN hashing + user store — SHA-256 with per-user salt in a SQLite file at `~/.dmcgui/users.db`; ACID-safe on power loss
- `csv` + `pathlib` (stdlib): profile import/export — two-column format with `#` comment metadata; human-readable and Excel-compatible
- `enum.Enum` (stdlib): `MachineType` and `Role` constants — prevents string typos across the codebase
- `systemd` user service (Pi OS): kiosk autostart — `Restart=always`, clean logging; superior to crontab or rc.local
- Kivy `ScreenManager` (existing): machine-type routing — no external routing library needed

### Expected Features

**Must have (table stakes):**
- PIN-based login with role selection (Operator/Setup/Admin) — touchscreen numpad overlay, no keyboard required
- Three-tier access control with session auto-lock after inactivity timeout
- Big-button RUN page: Start, Pause, Go to Rest, E-STOP (always reachable, every screen)
- Live axis position display (~10 Hz poll, A/B/C/D labels)
- Cycle status and progress feedback (status dot + progress bar)
- Operation log / event ticker (already in `MachineState.messages`, needs wiring to UI)
- Axis jog controls for all four axes (unified screen, sidebar axis selection)
- Teach point capture surfaced on unified Axes Setup screen
- Grouped parameter editing (Geometry, Feedrates, Calibration, Positions, Safety cards)
- Per-machine-type screen sets (Flat/Convex/Serration have different axis counts)
- Persistent dark theme with axis color coding (A=orange, B=purple, C=cyan, D=yellow)
- Touch-friendly targets throughout (44dp minimum, enforced in KV review)

**Should have (differentiators):**
- Live matplotlib A/B position plot — top-down view, confirms grind path in real time
- CSV profile import/export — save and reload knife setups; eliminates re-entry for repeat jobs
- Tab navigation bar replacing ActionBar + Spinner — faster, larger targets, always-visible structure
- Diagnostics tab — raw controller responses, command history, array read-on-demand
- Kiosk mode (Pi) — operators cannot exit to desktop; systemd autostart with restart-on-crash
- SD card deployment — technician swaps card rather than running pip install
- Input validation with inline red highlighting — already partially implemented, needs standardization

**Defer (v2+):**
- Multi-language UI, cloud sync, web dashboard, REST API, undo/redo, animated transitions, fine-grained permissions beyond three roles — explicitly identified as anti-features for this use case

### Architecture Approach

The architecture extends the existing layered model without breaking it. `MachineState` gains three new fields (`role`, `user_id`, `machine_type`). A new `AuthManager` handles PIN validation and writes role to state. A new `PinOverlay` (Kivy `ModalView`) floats above the `ScreenManager` so auth does not pollute navigation history. The existing ActionBar + Spinner nav is replaced by a `TabBar` widget that subscribes to state and shows/hides tabs based on role. All new screens follow the established pattern: subscribe to `MachineState` in `on_pre_enter`, unsubscribe in `on_leave`, never call each other directly, never call gclib outside `jobs.submit()`.

**Major components:**
1. `AuthManager` — PIN validation, role assignment to `MachineState`; in-memory dict, no hashing required per project scope
2. `PinOverlay` (ModalView) — modal PIN entry floated above all screens; callback-based so caller decides what happens on success
3. `TabBar` — replaces ActionBar+Spinner; role-to-tab visibility matrix; triggers `PinOverlay` for restricted tabs
4. `MachineConfig` — static dict mapping machine type string to axis list and DMC array names; drives which screen variants are shown
5. `RunScreen` — live matplotlib A/B plot + cycle controls; embeds `FigureCanvasKivyAgg` in `on_kv_post`; all plot updates in main-thread state subscriber
6. `ProfileManager` — `import_csv(path)` / `export_csv(path)`; all array I/O via `jobs.submit()`; machine-type validation before any writes
7. Kiosk configuration — systemd service + X11 session setup; Pi-specific `Config.set` in `main.py` before any Window import

### Critical Pitfalls

1. **Matplotlib draws from background thread** — `canvas.draw()` / `ax.plot()` called from `jobs.submit()` thread causes SIGABRT on Pi. Prevention: update data in background, post a `Clock.schedule_once` callback, all matplotlib calls happen on main thread only. Establish this pattern on the first matplotlib commit.

2. **Matplotlib full redraw blocks E-STOP responsiveness** — `canvas.draw()` at 10+ Hz takes 30–120 ms on Pi 4, making touch feel frozen. Prevention: use `canvas.draw_idle()` or blit animation (`line.set_data()` + `canvas.blit()`); rate-limit plot updates to 5–10 Hz; benchmark on Pi before sign-off.

3. **CSV profile load mid-cycle corrupts machine state** — `download_array` takes effect immediately on the Galil controller; loading a profile while the machine is in motion moves axes unexpectedly. Prevention: gate import behind (1) Setup role AND (2) `state.running == False`; show confirmation dialog with profile diff before committing writes.

4. **Auth state stored on Screen object, lost on navigation** — Kivy can destroy/recreate screens on transition; role stored as `self.current_role` silently resets. Prevention: store all auth state in `MachineState` exclusively; re-lock timeout is a Clock callback on `MachineState`, not on any Screen.

5. **`RestPnt` array semantic collision between two screens** — `axisDSetup.py` and `parameters_setup.py` both read/write `RestPnt[0..2]` with different semantic meanings. CSV export will make this ambiguity portable and destructive. Prevention: rename to `DAxisPnt` before any CSV work begins — this is a hard pre-requisite.

---

## Implications for Roadmap

Based on the dependency graph from ARCHITECTURE.md and the pitfall warnings from PITFALLS.md, the natural phase structure is:

### Phase 1: Foundation — Auth, Role Model, Tab Navigation
**Rationale:** Every other feature depends on role being in `MachineState`. PIN auth must be built and solid before any role-gated UI element is created; building UI first and bolting auth on after is the classic way to introduce auth bypasses. Tab navigation must also be in place so new screens have a home.
**Delivers:** `AuthManager`, `Role` enum, `PinOverlay` ModalView, `TabBar` replacing ActionBar+Spinner, `MachineState` extended with `role`/`user_id`/`machine_type`, `require_role` decorator
**Addresses:** PIN login, three-tier access, session auto-lock, tab navigation differentiator
**Avoids:** Pitfall 3 (auth state in Screen), Pitfall 7 (hidden buttons still tappable)

### Phase 2: RUN Page — Cycle Controls and Live Position
**Rationale:** This is what makes the machine usable for operators. The poll loop is already scaffolded in `main.py` but commented out — enabling it unlocks live position labels, the event log, and the plot. Cycle controls (Start/Pause/Rest/E-STOP) are the primary operator workflow. E-STOP must be wired globally before this phase is done.
**Delivers:** `RunScreen` with cycle controls, E-STOP in persistent tab footer, live position labels, operation log wired to `MachineState.messages`, poll loop re-enabled at ~10 Hz
**Addresses:** Big-button RUN page, live axis display, cycle status, operation log, E-STOP at all times
**Avoids:** Pitfall 11 (controller None before injection — BaseScreen guard established here)

### Phase 3: Live Matplotlib Plot
**Rationale:** Depends on Phase 2's poll loop delivering `state.pos` reliably. Separate phase because matplotlib integration has the highest technical risk and deserves isolated focus. Benchmark on Pi hardware before merging.
**Delivers:** `FigureCanvasKivyAgg` embedded in `RunScreen`, rolling 500-point A/B position buffer, `canvas.draw_idle()` pattern, Pi performance validation
**Addresses:** Live position plot differentiator
**Avoids:** Pitfall 1 (matplotlib off main thread), Pitfall 2 (redraw blocking E-STOP), Pitfall 14 (canvas size mismatch on resize)
**Uses:** `matplotlib>=3.8,<4` (only new dependency)

### Phase 4: Axes Setup and Parameters — Setup Personnel Tools
**Rationale:** Can run in parallel with Phase 3 since there is no cross-dependency. Unifies the fragmented jog/teach screens. Also resolves the `RestPnt` semantic collision (Pitfall 9) as a pre-requisite to Phase 5.
**Delivers:** Unified `AxesSetupScreen` (sidebar axis selection, jog controls, teach capture for all 4 axes), grouped `ParametersScreen` (card layout per function group), `RestPnt` renamed to `DAxisPnt`, all controller reads moved to `jobs.submit()`
**Addresses:** Axis jog controls, teach point capture, grouped parameter editing
**Avoids:** Pitfall 9 (RestPnt collision), Pitfall 10 (main-thread controller reads)

### Phase 5: CSV Profile System
**Rationale:** Requires Phase 4 to be complete (parameter groups defined, `DAxisPnt` collision resolved) and Phase 1 auth to be solid (Setup-role gate). All-or-nothing import, machine-type validation, and cycle-running safety interlock must be part of the initial implementation.
**Delivers:** `ProfileManager` with `import_csv` / `export_csv`, machine-type header row validation, confirmation dialog with diff preview, `jobs.submit()` for all array I/O, CSV format with `#` metadata header
**Addresses:** CSV profile import/export differentiator, profile metadata
**Avoids:** Pitfall 4 (overwrite during cycle), Pitfall 8 (wrong machine type), Pitfall 10 (main thread freeze)

### Phase 6: Machine-Type Differentiation
**Rationale:** All shared screen infrastructure must exist (Phases 1–5) before machine-type variants can be built. The serration screen already exists; Flat and Convex need their own `RunScreen` and `AxesSetupScreen` variants, or machine-type-aware conditional rendering in the shared classes.
**Delivers:** `MachineConfig` dict, `MachineType` enum, machine-type-aware `TabBar` and `RunScreen`, Flat/Convex screen variants confirmed working alongside existing Serration screen
**Addresses:** Per-machine-type screen sets (table stakes)

### Phase 7: Admin and Diagnostics
**Rationale:** Requires Phase 1 auth infrastructure to be solid. Lower operational priority than the run loop. Admin user management and the diagnostics terminal are useful but not blocking for daily machine operation.
**Delivers:** Admin user management screen (create/delete users, reset PINs), Diagnostics tab (scrollable terminal, raw command entry for Setup role, array read on demand), PIN file with `chmod 600` hardening
**Addresses:** Admin role functionality, Diagnostics differentiator
**Avoids:** Pitfall 12 (world-readable PIN file)

### Phase 8: Pi Kiosk Packaging and SD Card Deployment
**Rationale:** Last phase — packaging after features are stable. Requires real Pi hardware testing; cannot be validated from mockups alone. Kiosk lockout must be verified with actual operator interaction testing.
**Delivers:** systemd service unit, X11 session kiosk lockout (keyboard shortcut disablement, no desktop access), `Config.set` kiosk fullscreen in `main.py` top block, offline wheelhouse for SD card deployment, deployment documentation
**Addresses:** Kiosk mode differentiator, SD card deployment differentiator
**Avoids:** Pitfall 5 (fullscreen != locked desktop), Pitfall 13 (Config.set order)

### Phase Ordering Rationale

- Phase 1 before everything: auth state in `MachineState` is the shared foundation; building role-gated UI before this causes rewrites
- Phase 2 before Phase 3: poll loop must be stable and delivering `state.pos` before the plot can consume it
- Phase 4 before Phase 5: `DAxisPnt` rename is a hard pre-requisite for CSV correctness; cannot be done after profiles are in use
- Phase 6 after Phases 1–5: machine-type variants require all shared screen infrastructure to exist first
- Phase 8 last: kiosk is deployment configuration; features must be stable before locking down the OS

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Matplotlib):** Requires hands-on Pi performance benchmarking to confirm whether `draw_idle()` alone is sufficient or whether blit animation is needed. Also needs version confirmation of `FigureCanvasKivyAgg` API against the matplotlib 3.x release available at implementation time.
- **Phase 8 (Pi Kiosk):** Raspberry Pi OS Bookworm's Wayland/X11 transition is in flux. The exact lockout procedure depends on the Pi OS version at deploy time. Needs research against the actual Pi hardware image before implementation.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Auth):** stdlib sqlite3 + hashlib + ModalView — all well-documented, high-confidence patterns
- **Phase 2 (RUN Page):** Kivy Screen patterns are established; poll loop already scaffolded
- **Phase 5 (CSV):** stdlib csv module + jobs.submit pattern — no new patterns required
- **Phase 7 (Admin/Diagnostics):** Standard Kivy CRUD screen; no novel patterns

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Codebase inspection confirms existing constraints; only matplotlib is new. Verify latest 3.x stable and `FigureCanvasKivyAgg` availability before pinning. |
| Features | HIGH | Based on direct codebase analysis + approved mockups + ISA-101 HMI standards. Feature list is grounded in actual project artifacts. |
| Architecture | HIGH | Directly derived from existing codebase patterns. All new components extend proven patterns already in `setup.py`, `app_state.py`, `jobs.py`. |
| Pitfalls | HIGH (critical), MEDIUM (Pi-specific) | Critical pitfalls (matplotlib threading, CSV safety, auth state) are HIGH confidence from codebase analysis. Pi kiosk lockout is MEDIUM — depends on OS version at deploy time. |

**Overall confidence:** HIGH

### Gaps to Address

- **matplotlib `FigureCanvasKivyAgg` version compatibility:** The correct import path is `matplotlib.backends.backend_kivyagg` (not `kivy_garden.matplotlib`). Confirm this is present in the matplotlib 3.x version available on the Pi at implementation time. Run `pip index versions matplotlib` and test the import before committing to the integration approach.
- **Raspberry Pi OS version:** Kiosk lockout procedure differs between Pi OS Bookworm (Wayland default) and Pi OS Legacy (X11). The exact WM lockout config cannot be finalized without knowing the target Pi OS image. Resolve this at the start of Phase 8.
- **gclib poll rate ceiling:** Research capped polling at 10–20 Hz based on gclib single-handle constraint. The exact safe poll rate depends on what other commands are in flight (array uploads, DMC program execution). Establish empirically on the target Pi + controller before finalizing the poll interval in Phase 2.
- **`RestPnt` semantic fix scope:** The rename from `RestPnt` to `DAxisPnt` in `axisDSetup.py` may require corresponding changes in the DMC controller program itself (if the program references array names directly). Confirm scope with controller program before Phase 4 begins.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `src/dmccodegui/main.py`, `app_state.py`, `controller.py`, `utils/jobs.py`, all screen and KV files
- Project artifacts: `.planning/PROJECT.md`, `mockups/run_page.html`, `mockups/axes_setup.html`, `mockups/params_setup.html`
- Python stdlib documentation: `sqlite3`, `csv`, `hashlib`, `pathlib`, `enum` (training data, HIGH)
- Kivy ModalView and ScreenManager API (training data, HIGH — stable APIs)
- Galil gclib single-handle thread safety constraint (Galil documentation + codebase evidence, HIGH)
- ISA-101 HMI design standard, industrial HMI access control conventions (training data, HIGH)

### Secondary (MEDIUM confidence)
- matplotlib `FigureCanvasKivyAgg` / `backend_kivyagg` integration pattern (training data, MEDIUM — verify version at implementation time)
- `canvas.draw_idle()` Pi performance characteristics (Kivy community knowledge, MEDIUM — benchmark required)
- Raspberry Pi OS Bookworm systemd service + kiosk configuration (training data, MEDIUM — verify against target Pi OS image)

### Tertiary (LOW confidence / needs validation)
- `kivy_matplotlib_backend` import order constraints (training data, LOW — verify with current package at integration time)
- Blit animation speedup on Pi vs full redraw (community reports, LOW — benchmark required on target hardware)

---
*Research completed: 2026-04-04*
*Ready for roadmap: yes*
