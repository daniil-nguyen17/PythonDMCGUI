# Project Research Summary

**Project:** DMC Grinding GUI — v2.0 HMI-Controller Integration
**Domain:** Industrial HMI-to-controller wiring, Kivy GUI + Galil DMC state machine
**Researched:** 2026-04-06
**Confidence:** HIGH

## Executive Summary

This project is a v2.0 wiring pass on an existing, shipped v1.0 GUI: connecting real buttons to a real Galil DMC controller running a 4-Axes Flat Grind cycle. The v1.0 codebase is well-structured — the `jobs.submit` / `Clock.schedule_once` threading model is solid, all screens exist, and polling loops are already scaffolded. The work is entirely gclib command patterns and DMC program modifications. No new libraries, no new screens. The entire integration lives in the gap between the existing stub calls (`XQ #CYCLE`) and the correct DMC state machine entries (`hmiGrnd=0`, `hmiState` polling, proper `ST ABCD` + `HX` stop sequence).

The recommended approach is a foundation-first, read-before-write build order: add HMI variable constants and extend `MachineState` with DMC state fields, then validate the state poll path before wiring any action buttons. The DMC program must be modified as a hard prerequisite — HMI trigger variables cannot be tested without the OR conditions present in the `.dmc` file. The most architecturally significant addition is the `hmiState` variable in the DMC program, which replaces the unreliable Python-side `cycle_running` flag as the source of truth for machine state.

The primary risks are safety-oriented: E-STOP must not be queued behind normal `jobs.submit` calls, physical button + HMI double-trigger must be defended against on the DMC side, and jog commands must not compete with the DMC's own `#SETUP` loop motion. All three risks are preventable with known patterns documented in the research. An additional correctness risk is the existing array name mismatch (`StartPnt` vs `startPt`, `RestPnt` vs `restPt`) which must be resolved before any save operation is validated on real hardware.

---

## Key Findings

### Recommended Stack

No new libraries are required for v2.0. The full stack — Python 3.10+, Kivy 2.2+, gclib (system install), matplotlib — is unchanged. The work is entirely within the existing `jobs.submit` / `GCommand` / `Clock.schedule_once` model already established in v1.0.

The critical gclib patterns for v2.0 are: semicolon-batched `MG` reads for multi-variable polls in one round-trip, the one-shot trigger pattern (`varName=0` to fire, DMC resets to `1` immediately on block entry), and `BV` only on explicit user save (never polling, never automatic — it takes ~2 seconds).

**Core technologies:**
- **gclib (system install, 2.4.1):** Galil controller comms — `cmd()`, `upload_array()`, `download_array()`; all calls serialized through the single `jobs` FIFO worker
- **`threading` / `kivy.clock.Clock`:** Off-thread I/O pattern already in place; gclib never touches the Kivy main thread
- **KV language + Kivy screens:** Layouts exist; v2.0 adds only `on_release` bindings and reactive property updates from polled state

The gclib thread-safety claim in 2.4.0+ is marked MEDIUM confidence due to ambiguous documentation. The existing single-handle serialization via `jobs` must be preserved regardless — it is the safe default.

### Expected Features

The v1.0 build shipped PIN auth, tab navigation, live plot scaffold, axes setup UI, parameter cards, CSV profiles, and user management. All of those are done. v2.0 is purely wiring the existing UI to the real controller.

**Must have (v2.0 table stakes):**
- Array name mismatch fix (`StartPnt` / `RestPnt` vs `startPt` / `restPt`) — blocker for all save operations
- Start Grind wired to `XQ #GRIND` (replace `XQ #CYCLE` stub)
- Go To Rest wired to `XQ #GOREST` (replace `XQ #REST` stub)
- Go To Start button added and wired to `XQ #GOSTR`
- Stop motion sending `ST ABCD` + `HX` (both commands; `HX` halts program, `ST` decelerates axes)
- Live position labels connected to real controller (remove `_show_disconnected()` override in `on_pre_enter`)
- More Stone / Less Stone buttons wired to `XQ #MOREGRI` / `XQ #LESSGRI`
- New Session button wired to `XQ #NEWSESS` (Setup role gate + two-step confirmation)
- Homing button on Axes Setup wired to `XQ #HOME` (Setup role gate)
- Parameters screen write path wired (`controller.cmd("fdA=50")` pattern)
- Jog step buttons confirmed to move real axes (PA relative + BG)

**Should have (v2.x after flat grind validation):**
- HMI one-shot variable pattern in DMC code (`hmiGrnd`, `hmiSetp`, `hmiMore` etc.) — add after `XQ` wiring validated; enables OR-with-physical-buttons
- `hmiState` variable in DMC + polling in HMI — replaces Python `cycle_running` as authoritative state
- Setup mode badge / Run tab disable when setup active
- Knife count display (`ctSesKni`, `knfSess`) on Run page
- Position readout in engineering units (mm / degrees via CPM conversion)
- Graceful reconnect loop in background thread
- Varcalc trigger from HMI Parameters screen

**Defer to v3.0+:**
- Serration Grind integration (same pattern, different subroutine names)
- Convex Grind integration
- Array name validation helper before every upload/download

### Architecture Approach

The v2.0 architecture adds a thin `hmi/` package (two files: `dmc_vars.py` constants and `commands.py` service) on top of the existing layer cake. The `GalilController` gets two convenience methods (`write_hmi_var` / `read_hmi_var`). `MachineState` gains `dmc_state: int` and `dmc_loop: str`. All screen files are modified only at their action handlers and `_do_poll` extensions — structural layouts and KV files remain untouched.

**Major components:**
1. **`GalilController` (controller.py)** — sole owner of all gclib calls; add `write_hmi_var()` / `read_hmi_var()` wrappers
2. **`hmi/dmc_vars.py`** (NEW, ~30 lines) — string constants for all HMI variable names and state codes; prevents 8-char name typos across screens
3. **`hmi/commands.py` / `HMICommandService`** (NEW, ~40 lines) — `trigger()` fire-and-forget + `trigger_and_wait()` for modal blocking flows only
4. **`MachineState` (app_state.py)** — add `dmc_state: int`; screens subscribe for button enable/disable
5. **`RunScreen._do_poll()`** — extend the existing 10 Hz background poll to also read `hmiState`; one round-trip per tick, no second clock
6. **`jobs` (utils/jobs.py)** — add `submit_urgent()` for E-STOP priority prepend; otherwise unchanged
7. **DMC program (`4 Axis Stainless grind.dmc`)** — hard prerequisite: add `hmiGrnd..hmiCalc` variables with default=1 in `#PARAMS`, OR conditions in `#WtAtRt`, `hmiState` assignments at subroutine boundaries

### Critical Pitfalls

1. **HMI + physical button double-trigger (Pitfall 1)** — Send each HMI trigger variable exactly once per user tap; disable the button immediately (optimistic lock); DMC must reset the variable as the FIRST line inside the triggered block, not after motion completes. Never send from a polling callback.

2. **Sending motion commands during active grind cycle (Pitfall 2)** — Gate ALL HMI trigger sends on polled `hmiState` (controller-authoritative state), not on Python `cycle_running`. The Python flag is a guess; `hmiState` is the truth.

3. **E-STOP queued behind normal jobs (Pitfall 3 + 4)** — E-STOP must not wait in the FIFO queue behind a 500 ms array upload. Implement `jobs.submit_urgent()` (prepend to queue) so E-STOP has < 100 ms latency with no shared-handle threading risk. Never implement E-STOP as a trigger variable — use `AB` directly.

4. **State desynchronization after physical E-STOP / limit switch (Pitfall 5)** — `cycle_running` on the Python side can stay `True` after a hardware stop event the HMI never saw. Mitigation: `_do_poll` reads `_XQ` and `hmiState`; any poll showing `_XQ == 0` while `cycle_running == True` resets state and surfaces a banner.

5. **Jog during DMC `#SETUP` mode competing with `#WheelJg` (Pitfall 6)** — HMI jog must not send direct `PR/BG` while the DMC is in its own `#WheelJg` loop. Safest protocol: HMI jog uses `hmiJog=0` trigger so the DMC handles motion internally. Direct `PR/BG` only if `_XQ == 0` (no DMC thread running).

Additional high-priority pitfalls: gclib connection not closed on app crash (add `atexit.register(controller.disconnect)`), queue saturation from multiple per-screen poll clocks (consolidate to one global poll), reading `hmiState` before DMC `#AUTO` completes (extend `wait_for_ready()` to verify HMI vars are initialized), and excessive `BV` calls wearing flash (call `BV` only on explicit user save).

---

## Implications for Roadmap

Based on the combined research, the build decomposes into six phases with clear dependency gates.

### Phase 1: Foundation — Constants, State Fields, DMC Program Modification

**Rationale:** Nothing else in the integration can be tested without this. The DMC program OR conditions must be present before any HMI trigger variable has any effect on the controller. Constants prevent 8-char name typos. State fields in `MachineState` are needed by every subsequent phase.

**Delivers:** `hmi/dmc_vars.py`, `write_hmi_var()` / `read_hmi_var()` on `GalilController`, `dmc_state` field on `MachineState`, updated `.dmc` file with `hmiGrnd..hmiCalc` variables (default=1), OR conditions in `#WtAtRt`, `hmiState` assignments at subroutine boundaries, `atexit` / `SIGTERM` handler for `GClose`.

**Addresses:** Array name mismatch fix (resolve `StartPnt` vs `startPt`), HMI variable naming constants, connection cleanup on crash (Pitfall 8).

**Avoids:** Inline string literals for variable names (Pitfall anti-pattern), undefined variable `?` responses at connect time (Pitfall 10).

**Research flag:** Standard patterns — no additional research needed.

---

### Phase 2: State Poll — Read Path Validation

**Rationale:** Read before write. Validate that `hmiState`, `_XQ`, and axis positions can be polled correctly from the real controller before any button triggers are wired. This phase produces the authoritative controller state that all subsequent phases depend on.

**Delivers:** Extended `RunScreen._do_poll()` reading `hmiState` + axis positions in a single batched `MG` call, `MachineState.dmc_state` updated from poll, `wait_for_ready()` extended to verify HMI vars initialized, validated 10 Hz position labels on RunScreen.

**Addresses:** Live position labels from controller (remove `_show_disconnected()` override), state desync prevention (Pitfall 5), HMI variable initialization check (Pitfall 10).

**Avoids:** Multiple per-screen poll clocks (Pitfall 9) — consolidate to single poll here, not duplicated per screen.

**Research flag:** Standard patterns — well-documented poll extension; no research needed.

---

### Phase 3: E-STOP Priority and Connection Resilience

**Rationale:** E-STOP must be validated on hardware before motion commands are wired. Testing E-STOP after Start Grind is already wired means testing safety on top of an unknown motion baseline. Validate the safety path first.

**Delivers:** `jobs.submit_urgent()` (prepend-to-queue for priority), E-STOP confirmed to halt motion within 200 ms even during a large array operation, E-STOP visible from every screen (persistent tab bar / status bar), `atexit` + `SIGTERM` handler for clean `GClose`.

**Addresses:** E-STOP queuing hazard (Pitfall 3), gclib concurrent access on E-STOP path (Pitfall 4), E-STOP only on one screen (Safety Mistakes table).

**Avoids:** E-STOP implemented as a trigger variable (must use `AB`), `jobs.submit()` path for E-STOP.

**Research flag:** Needs hardware validation — if dual-handle approach is chosen over priority queue, verify Galil DMC firmware supports two concurrent `GOpen` TCP connections. MEDIUM confidence.

---

### Phase 4: RunScreen Action Button Wiring (Main Loop)

**Rationale:** RunScreen buttons are the operator's primary interface and the critical path for machine operation. Wire these before setup loop buttons. Start with direct `XQ` calls (immediate validation on real hardware), then migrate to HMI one-shot variable pattern after DMC OR conditions are confirmed working.

**Delivers:** Start Grind (`hmiGrnd=0` after DMC OR conditions validated), Go To Rest (`XQ #GOREST`), Go To Start (new button + `XQ #GOSTR`), More Stone / Less Stone (`XQ #MOREGRI` / `#LESSGRI` with motion-state gate), New Session (`XQ #NEWSESS` with two-step confirmation modal + Setup role gate), Pause/Stop (`ST ABCD` + `HX`), `cycle_running` driven by `hmiState` poll not just button handlers.

**Addresses:** All P1 features from FEATURES.md prioritization matrix. Operator workflow Sequences 1 and 2.

**Avoids:** Double-trigger race condition (Pitfall 1 — optimistic lock on button, DMC reset at block entry), motion commands during active cycle (Pitfall 2 — gate on `hmiState`), array write during active motion (Pitfall 7 — More/Less Stone gated on DMC state).

**Research flag:** Standard patterns — XQ, hmiVar trigger, ST/HX all confirmed in official Galil docs and existing codebase.

---

### Phase 5: Setup Loop — Axes Setup and Parameters

**Rationale:** Setup loop integration (AxesSetup + Parameters screens) is independent of RunScreen after Phase 1. Setup personnel workflow is secondary to operator workflow but must be correct before hardware validation of any production cycle.

**Delivers:** Enter Setup via `hmiSetp=0`, Homing via `hmiHome=0` (Setup role gate), Jog step buttons confirmed on real axes with jog protocol defined (`hmiJog=0` approach to avoid `#WheelJg` race), Teach Rest / Teach Start wired with corrected array names, Parameters screen write path flushed via `cmd("varName=value")` + `BV` + `hmiCalc=0`.

**Addresses:** Jog confirmed on real axes, Save Start/Rest point arrays, Parameters write to controller, Homing button, Varcalc trigger from HMI. Operator workflow Sequences 3 and 4.

**Avoids:** Competing jog commands during `#SETUP` mode (Pitfall 6 — define jog protocol before writing any jog code), excessive `BV` calls (Integration Gotchas), entering `#SETUP` via `XQ #SETUP` directly.

**Research flag:** Jog protocol requires hardware validation — which approach (`hmiJog=0` vs direct `PR/BG` with `_XQ==0` gate) is correct for this machine's specific `#SETUP` loop cannot be determined from code alone.

---

### Phase 6: State-Driven UI Polish and Live Plot Validation

**Rationale:** State-driven UI (button enable/disable, status labels, setup mode badge) can only be built after Phase 2 (state poll) and Phase 4 (RunScreen wiring) are validated. Plot buffer fill during active cycle needs the position poll working and `cycle_running` reliably set from `hmiState`.

**Delivers:** Buttons disabled/enabled based on `dmc_state`, status label showing IDLE / GRINDING / SETUP / HOMING, setup mode badge on all screens, Run tab disable when setup active, live A/B plot buffer confirmed filling during real grind cycle, knife count display (`ctSesKni`, `knfSess`), position readout in engineering units.

**Addresses:** Setup mode visual indicator, connection status visible at all times, plot populating from real positions. Operator workflow Sequence 5 (power-on / reconnect).

**Avoids:** Cycle running indicator staying on after physical E-STOP (resolved by `hmiState`-driven `cycle_running`), no visual feedback on button tap (immediate disable on tap).

**Research flag:** Standard patterns — KV property binding, `MachineState.notify()` propagation. No research needed.

---

### Phase Ordering Rationale

- Phase 1 (DMC program) is a hard prerequisite for Phases 3, 4, and 5 — trigger variables have no effect until OR conditions exist in the `.dmc` file.
- Phase 2 (read path) must precede Phase 6 (state-driven UI) — cannot gate buttons on state not yet being read.
- Phase 3 (E-STOP) placed before motion wiring (Phase 4) because safety validation on hardware must precede motion validation.
- Phases 4 and 5 are independent of each other after Phase 1; Phase 4 first because RunScreen is the operator's primary screen and the integration's critical path.
- Phase 6 can begin in parallel with Phase 5 after Phase 2 + 4 are validated.

---

### Research Flags

Phases likely needing deeper research or hardware validation during planning:
- **Phase 3 (E-STOP):** Dual-handle approach — verify Galil DMC firmware supports two concurrent `GOpen` TCP connections to the same controller. MEDIUM confidence.
- **Phase 5 (Jog protocol):** Hardware validation required to confirm `hmiJog=0` vs direct `PR/BG` approach for this machine's specific `#SETUP` loop structure.

Phases with standard, well-documented patterns (skip research-phase):
- **Phase 1:** gclib variable patterns, DMC syntax — confirmed in official docs + existing codebase.
- **Phase 2:** Poll extension, `Clock.schedule_once` — existing codebase is the reference.
- **Phase 4:** `XQ`, `ST`, `HX`, `hmiVar=0` — all confirmed in Galil docs and `4 Axis Stainless grind.dmc`.
- **Phase 6:** KV property binding, `MachineState.notify()` — established v1.0 pattern.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new libraries; all patterns confirmed in official gclib docs and existing codebase. Single MEDIUM caveat: gclib 2.4.x thread-safety claim is ambiguous for same-handle concurrent use. |
| Features | HIGH | Based on direct analysis of `4 Axis Stainless grind.dmc` and full v1.0 codebase audit. Feature list grounded in real subroutine names and real hardware I/O. |
| Architecture | HIGH | Direct code audit of all v1.0 files. Architecture is evolutionary, not a rewrite. Patterns already proven in the codebase. |
| Pitfalls | HIGH | gclib threading and DMC state machine pitfalls confirmed against official docs and code. MEDIUM for timing-specific scenarios (industrial HMI domain knowledge, not yet hardware-verified). |

**Overall confidence: HIGH**

### Gaps to Address

- **gclib thread-safety on 2.4.x:** Verify installed version with `gclib.py().GVersion()` at startup. If < 2.4.0, single-queue model is mandatory. Default to single-queue regardless — it works and is safe.
- **Array name case sensitivity on this specific controller firmware:** `StartPnt` vs `startPt` — case-insensitive on some firmware versions, not all. Verify on the actual hardware before committing to either rename approach.
- **Dual `GOpen` connection support:** Verify Galil firmware allows two simultaneous TCP connections if E-STOP dedicated-handle approach is chosen over priority queue.
- **Jog protocol on real machine:** `hmiJog=0` vs direct `PR/BG` with `_XQ==0` gate must be validated on hardware; cannot be determined from code analysis alone.

---

## Sources

### Primary (HIGH confidence)
- Official gclib Python class reference: https://www.galil.com/sw/pub/all/doc/gclib/html/classgclib_1_1py.html — GCommand, GArrayUpload, GArrayDownload signatures
- gclib thread safety documentation: https://accserv.lepp.cornell.edu/svn/packages/gclib/doc/html/threading_8md_source.html — single-handle constraint
- DMC command reference (Keck/DEIMOS): https://www2.keck.hawaii.edu/inst/deimos/com40x0.pdf — variable assignment, BV, XQ, HX, MG, ST, AB, JG syntax
- Existing codebase: `controller.py`, `run.py`, `axes_setup.py`, `parameters.py`, `app_state.py`, `utils/jobs.py` — confirmed working patterns from v1.0
- DMC program: `4 Axis Stainless grind.dmc` — subroutine names, state machine structure, physical I/O mapping, array declarations

### Secondary (MEDIUM confidence)
- gclib release notes (2026-03): https://www.galil.com/sw/pub/all/rn/gclib.html — version 2.4.1 current, "thread safe" in 2.4.0
- Galil Raspberry Pi HMI integration: https://www.galil.com/news/whats-new-galil/raspberry-pi-interface-galil-controllers — Python gclib on Pi
- CNC HMI operator workflow patterns: https://radonix.com/cnc-control-panel-functions-a-step-by-step-breakdown/
- Industrial HMI safety (ISO 13850 / ISA-101): https://machinerysafety101.com/2021/06/02/manual-reset-using-an-hmi/
- Project planning context: `.planning/PROJECT.md` — v2.0 milestone target, HMI variable naming decisions

### Tertiary (LOW confidence)
- HMI design best practices general guide: https://plcprogramming.io/blog/hmi-design-best-practices-complete-guide — confirmation dialog anti-pattern
- CNC cycle stop patterns: https://www.mmsonline.com/articles/4-ways-to-stop-a-cycle-to-allow-operator-intervention — ST vs HX distinction

---

*Research completed: 2026-04-06*
*Ready for roadmap: yes*
