# Phase 29: Integration Testing and Field Validation - Research

**Researched:** 2026-04-22
**Domain:** Hardware validation, deployment testing, inline bug fixing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Hardware availability**
- Galil controller available and connected — can run live Flat Grind cycles (FIX-02)
- Raspberry Pi with touchscreen(s) ready — multiple screen sizes available for preset validation
- Windows: both dev machine (Galil SDK installed) and separate clean factory PC available
- All four success criteria are testable with current hardware

**Test & fix workflow**
- Bugs found during validation are fixed inline in Phase 29 — no separate fix phases
- Test results documented as pass/fail checklist in SUMMARY.md with notes per test and log excerpts for failures — no screenshots required
- Phase 27 display preset validation included in scope (beyond FIX-02 and PI-06)
- If KIVY_METRICS_DENSITY values (0.65/0.75/1.0) don't look right on real screens, tune them inline during Phase 29 — iterative adjustment at the hardware

**Pi deployment methods**
- USB/SCP method: copy full repo to Pi via USB or SCP, then run install.sh (handles exclusions via rsync). Simplest for technicians.
- SD card image method: manual process with documented steps (install on Pi, configure, capture with Pi Imager/dd). No automation script — FUTURE-02 in REQUIREMENTS.md covers automation tooling.
- git clone method: Pi has internet access, clones from GitHub directly, then runs install.sh. Standard workflow.
- All three methods tested to boot-to-login-screen as the pass/fail gate

**Deployment documentation**
- Create a simple `deploy/pi/README.md` with step-by-step instructions for each of the three Pi deployment methods
- Technicians need this to deploy without the developer present
- Also create `deploy/windows/README.md` with Windows installer instructions

**Windows validation**
- Test on dev machine first (smoke test), then validate on clean factory PC (true gate)
- Clean-VM test: no Python, no Galil SDK, no dev tools — installer must work standalone
- Windows Defender active (default) — no AV exclusions, no admin overrides

### Claude's Discretion
- Test execution order and grouping
- How to structure the checklist in SUMMARY.md
- Exact steps in deployment READMEs
- Whether to create a formal test matrix or keep it informal
- How to handle Pi image creation documentation format

### Deferred Ideas (OUT OF SCOPE)
- SD card image automation — FUTURE-02 in REQUIREMENTS.md covers tooling for zero-touch Pi deployment via automated image creation
- Pi splash screen — FUTURE-03 in REQUIREMENTS.md (optional branding during startup)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FIX-02 | Flat Grind run page validated on real controller — graph draws during grind, buttons gray out during motion, machine state updates in real-time | Requires live Galil + Windows installer; DR streaming already implemented; 3 pre-existing test failures must be fixed first (motion_active homing, status_bar state_text i18n, _BareApp _stop_dr) |
| PI-06 | Three deployment methods documented and tested: USB/SCP folder transfer, SD card image, git clone + install.sh | deploy/pi/README.md to be created; all three paths terminate at boot-to-login-screen gate |
</phase_requirements>

---

## Summary

Phase 29 is a validation-and-fix phase: no new features, only hardware confirmation and inline repairs. The deliverables are (1) a working Windows installer confirmed on a clean factory PC, (2) a confirmed Pi kiosk via all three deployment paths, (3) a Flat Grind live-controller cycle that proves DR streaming works end-to-end, and (4) deployment READMEs for technicians.

The most important pre-work finding: **the test suite has 17 pre-existing failures before Phase 29 begins**. Three distinct bugs are present in the shipped code. These failures are not from Phase 28 regressions — they reflect logic mismatches added across earlier phases. They must be fixed as part of Phase 29's inline fix policy, and the fix tasks should come first so the suite reaches a clean baseline before hardware validation begins.

The second critical finding: **no `deploy/pi/README.md` or `deploy/windows/README.md` exists yet**. These are locked deliverables in CONTEXT.md and must be created.

**Primary recommendation:** Structure Phase 29 as four tasks — (1) fix pre-existing test failures, (2) create deployment READMEs, (3) Windows hardware validation, (4) Pi hardware validation — in that order.

---

## Standard Stack

### Core
| Component | Version/Path | Purpose | Why Standard |
|-----------|-------------|---------|--------------|
| pytest | installed (pyproject.toml) | Automated test suite | Already established across all phases |
| deploy/windows/build_windows.bat | existing | PyInstaller + Inno Setup build chain | Single entry point for Windows build |
| deploy/windows/BinhAnHMI.spec | existing | PyInstaller bundle config | Already validated through Phase 24/25 |
| deploy/pi/install.sh | existing | Idempotent Pi setup | Already validated through Phase 26 |
| %APPDATA%/BinhAnHMI/logs/app.log | runtime output | Windows validation evidence | Phase 28 logging infrastructure |
| ~/.binh-an-hmi/logs/app.log | runtime output | Pi validation evidence | Phase 28 logging infrastructure |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| Pi Imager / `dd` | SD card image capture | SD card image deployment method documentation |
| `scp` / USB | File transfer to Pi | USB/SCP deployment method |
| `git clone` | Repo pull on Pi | git clone deployment method |
| Windows Defender | AV gate | Clean-PC test must pass with default Defender active |

**Installation:** No new packages — all tooling already installed.

---

## Architecture Patterns

### Phase Task Ordering (Recommended)

```
Task 1: Fix pre-existing test failures (17 failures → 0)
Task 2: Create deploy/pi/README.md and deploy/windows/README.md
Task 3: Windows hardware validation (dev machine smoke, then clean PC gate)
Task 4: Pi hardware validation (all 3 deployment methods + live Flat Grind)
```

This order matters: fix tests first so the automated suite is green before touching hardware. Hardware validation findings may generate additional inline fixes; those fixes can be added as sub-tasks within Task 3/4.

### Pre-existing Test Failure Analysis

Three distinct bugs require fixes. All are in production source, not in test infrastructure.

**Bug 1: status_bar.py — Vietnamese state labels (5 failures)**
- Location: `src/dmccodegui/screens/status_bar.py`, `_STATE_MAP` dict, lines 26-31
- Root cause: `_STATE_MAP` was rewritten with Vietnamese strings ("CHỜ", "ĐANG MÀI", "ĐANG THIẾT LẬP", "ĐANG VỀ VỊ TRÍ GỐC") but tests expect English ("IDLE", "GRINDING", "SETUP", "HOMING")
- Fix: Restore English state labels in `_STATE_MAP`
- Tests affected: `test_state_text_idle`, `test_state_text_grinding`, `test_state_text_setup`, `test_state_text_homing`, `test_state_always_recomputed`

**Bug 2: flat_grind/run.py — STATE_HOMING not included in motion_active logic (1 failure)**
- Location: `src/dmccodegui/screens/flat_grind/run.py`, `_apply_state()`, around line 367
- Root cause: The `_apply_state()` grind detection block handles `STATE_GRINDING` but not `STATE_HOMING`. The `motion_active = dmc_state in (STATE_GRINDING, STATE_HOMING)` assignment at line 502 is inside a branch that only fires under certain conditions (the `_tick_pos` path); the direct `_apply_state()` path does not set `motion_active = True` when `dmc_state == STATE_HOMING`
- Fix: Add STATE_HOMING to the connected-but-not-grinding branch in `_apply_state()` so that when `dmc_state == STATE_HOMING`, `motion_active` is set to True
- Tests affected: `test_motion_gate_homing`

**Bug 3: main.py — _BareApp missing `_stop_dr` attribute (3 failures)**
- Location: `tests/test_screen_loader.py`, `_BareApp` stub class
- Root cause: `DMCApp.on_stop()` calls `self._stop_dr()` (line 1201 of main.py), but the `_BareApp` test stub only defines `_stop_poller` and `_stop_mg_reader`, not `_stop_dr`. This is a test fixture gap — `_BareApp` was written before `_stop_dr` was added to `DMCApp` (likely added during the DR migration in an earlier phase).
- Fix: Add a `_stop_dr` stub method to `_BareApp` in `test_screen_loader.py`
- Tests affected: `test_on_stop_calls_cleanup_on_screens_with_cleanup`, `test_on_stop_does_not_call_nonexistent_cleanup`, `test_on_stop_no_stop_pos_poll_or_stop_mg_reader_called`

### Windows Validation Checklist Pattern

Test on dev machine first (has Galil SDK, can verify app runs). Then on clean factory PC.

Clean PC gate (no Python, no Galil SDK, no dev tools, default Defender active):
1. Copy `DMCGrindingGUI_Setup.exe` to clean machine
2. Run installer — check no UAC escalation failures, no AV quarantine
3. Launch from Start Menu shortcut — check no missing DLL error
4. Connect to Galil controller — check DR streaming starts
5. Run a Flat Grind cycle — check live A/B plot updates, buttons gray out during motion
6. Check `%APPDATA%/BinhAnHMI/logs/app.log` exists and has content

### Pi Validation Checklist Pattern

For each of the three deployment methods:
- Gate: boot to login screen (kiosk fullscreen, operator can log in)
- Evidence: desktop shortcut works, app launches without console errors

Then live controller test (one method sufficient):
- Connect Pi to Galil controller
- Log in, navigate to Flat Grind
- Run a Flat Grind cycle
- Confirm: live position data on run screen (DR streaming), graph draws, buttons gray during motion

### Deployment README Structure

`deploy/pi/README.md` — three sections, one per method:
1. **Method A: USB/SCP Transfer** — prerequisites, copy command, install command, expected outcome
2. **Method B: SD Card Image** — when to use (zero-install), prerequisites (Pi Imager), how to write image, first-boot notes
3. **Method C: git clone** — prerequisites (Pi needs internet), clone command, install command

`deploy/windows/README.md` — single section:
- Build prerequisites (Python, PyInstaller, Inno Setup)
- Build command (`build_windows.bat`)
- Where to find the output (`DMCGrindingGUI_Setup.exe`)
- Clean-PC distribution notes

### Anti-Patterns to Avoid

- **Running hardware tests before test suite is green:** Fix the 17 failures first. Hardware bugs are harder to diagnose with a broken baseline.
- **Documenting SD card image creation with automation steps:** Out of scope per FUTURE-02.
- **Taking screenshots for SUMMARY.md:** User explicitly said no screenshots required — pass/fail + log excerpts only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deployment validation evidence | Custom logging or tracing | Existing app.log at `_get_data_dir()/logs/app.log` | Phase 28 already established this as the validation artifact |
| Pi transfer tooling | Custom sync scripts | Existing install.sh + rsync exclusions | Already idempotent; handles all exclusions from Phase 28 |
| Windows build | Custom packaging | Existing build_windows.bat + BinhAnHMI.spec | Already tested through Phases 24/25 |

---

## Common Pitfalls

### Pitfall 1: Attempting Hardware Validation with a Broken Test Suite
**What goes wrong:** If you skip fixing the 17 pre-existing failures, any new bugs found on hardware are harder to isolate — you can't tell if a test failure is new or pre-existing.
**Why it happens:** Phase ordering tempts skipping automated fixes and going straight to hardware.
**How to avoid:** Fix all 17 failures in Task 1. Run `python -m pytest tests/ -q` to confirm 0 failures before hardware work.
**Warning signs:** More than 0 failures before the first hardware test.

### Pitfall 2: Vietnamese Labels in _STATE_MAP
**What goes wrong:** The status bar shows Vietnamese text ("CHỜ" instead of "IDLE") — operators who don't read Vietnamese see illegible state labels.
**Why it happens:** `_STATE_MAP` was modified to Vietnamese strings at some point, contradicting the English test expectations and the English-language HMI requirement.
**How to avoid:** Restore English strings. The color values are correct; only the label strings need to change.

### Pitfall 3: _stop_dr Missing in Test Fixtures
**What goes wrong:** `_BareApp.on_stop()` raises `AttributeError: '_BareApp' object has no attribute '_stop_dr'`.
**Why it happens:** `DMCApp.on_stop()` gained a `self._stop_dr()` call during the DR migration (Phase 23), but `_BareApp` in `test_screen_loader.py` was not updated.
**How to avoid:** Add `_stop_dr(self): pass` (or a MagicMock stub) to `_BareApp`. This is a test fixture fix, not a production code fix.

### Pitfall 4: STATE_HOMING Not Gating motion_active in _apply_state
**What goes wrong:** When the controller is homing, `motion_active` stays `False`, so motion buttons are enabled during homing — a safety issue.
**Why it happens:** The direct `_apply_state()` path only checks `now_grinding = dmc_state == STATE_GRINDING`. STATE_HOMING is handled in `_tick_pos` (line 502) but not in `_apply_state()`.
**How to avoid:** In `_apply_state()`, after the `if now_grinding:` block, add a condition for `dmc_state == STATE_HOMING` that sets `motion_active = True`. This mirrors the `_tick_pos` behavior.

### Pitfall 5: Forgetting install.sh is Idempotent — Can Re-run After Inline Fixes
**What goes wrong:** On Pi validation, if a bug is found and fixed, developers re-flash the SD card unnecessarily.
**Why it happens:** Forgetting that `install.sh` checks for existing venv/gclib before re-creating.
**How to avoid:** After any inline fix to install.sh, just re-run `sudo bash install.sh` on the same Pi — it will skip steps already completed.

### Pitfall 6: Windows Defender Quarantine of gclib.dll
**What goes wrong:** Defender flags the vendored `gclib.dll` on the clean factory PC.
**Why it happens:** Unsigned industrial DLLs from Galil are occasionally flagged by behavioral AV heuristics.
**How to avoid:** Test with default Defender (as required). If quarantine occurs, the fix is to add a Windows Defender exclusion for the install dir — document this in `deploy/windows/README.md` as a known issue, not as a pre-requirement. Do NOT pre-configure exclusions before the test.
**Warning signs:** Install completes but app fails to launch with "DLL not found" on clean PC.

---

## Code Examples

### Bug 1 Fix: Restore English _STATE_MAP
```python
# Source: src/dmccodegui/screens/status_bar.py lines 26-31
# Current (broken):
_STATE_MAP: dict = {
    1: ("CHỜ",             [1.0,  0.6,  0.0,  1]),
    2: ("ĐANG MÀI",        [0.13, 0.77, 0.37, 1]),
    3: ("ĐANG THIẾT LẬP",  [0.9,  0.2,  0.2,  1]),
    4: ("ĐANG VỀ VỊ TRÍ GỐC", [1.0, 0.6, 0.0, 1]),
}

# Fixed:
_STATE_MAP: dict = {
    1: ("IDLE",    [1.0,  0.6,  0.0,  1]),
    2: ("GRINDING",[0.13, 0.77, 0.37, 1]),
    3: ("SETUP",   [0.9,  0.2,  0.2,  1]),
    4: ("HOMING",  [1.0,  0.6,  0.0,  1]),
}
```

### Bug 3 Fix: Add _stop_dr to _BareApp
```python
# Source: tests/test_screen_loader.py, _BareApp class
# Add after _stop_mg_reader:
def _stop_dr(self):
    pass  # No DR listener in unit tests
```

### Bug 2 Fix: Add STATE_HOMING to _apply_state
```python
# Source: src/dmccodegui/screens/flat_grind/run.py, _apply_state()
# In the connected branch, after the `if now_grinding:` block and `elif` block:
# Current logic at ~line 367:
elif self.cycle_running and not now_grinding and dmc_state != 0:
    # grace period / grind-end detection

# Add a new elif (or extend the elif) to handle HOMING:
elif dmc_state == STATE_HOMING:
    if not self.motion_active:
        self.motion_active = True
```

### Validation Evidence Check
```bash
# Windows: confirm log exists after app launch
dir "%APPDATA%\BinhAnHMI\logs\app.log"

# Pi: confirm log exists after app launch
ls ~/.binh-an-hmi/logs/app.log
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TCP poll for position/state | DR UDP streaming (DataRecordListener) | Phase 23 | Position updates at ~5-10 Hz without poll overhead |
| MG polling for machine state | DR packet dmc_state field | Phase 23 | Eliminates MG polling contention |
| Print statements | Structured logging via setup_logging() | Phase 28 | app.log usable as validation evidence |
| Manual bundle exclusions | Content-inspection tests guard spec and rsync | Phase 28 | Regression protection for APP-03 |

---

## Open Questions

1. **kivy_matplotlib_widget ARM wheel on Bookworm**
   - What we know: STATE.md flags this as the most likely Phase 26 failure point (unconfirmed PiWheels availability)
   - What's unclear: Whether aarch64 wheel is available or requires source compilation on first `pip install`
   - Recommendation: First Pi test (`sudo bash install.sh`) will reveal this — install.sh already includes SDL2 build deps and cmake for source compilation. If pip install fails, check install log at `/var/log/binh-an-hmi-install.log` and add a `--no-binary kivy_matplotlib_widget` flag or a build fallback.

2. **screeninfo on Pi HDMI-forced framebuffer**
   - What we know: STATE.md flags this as requiring validation on real hardware (Phase 27 research flag)
   - What's unclear: Whether `screeninfo.get_monitors()` returns correct resolution when X11 is forced via `raspi-config nonint do_wayland W1`
   - Recommendation: During Pi validation, check if `_detect_preset()` log line shows expected resolution. If it returns wrong preset, use `settings.json` override (`{"display_size": "7inch"}`) as the immediate workaround, then document the override in `deploy/pi/README.md`.

3. **17 pre-existing test failures — are any from Phase 28 regressions?**
   - What we know: Status bar failures are Vietnamese strings (pre-Phase-28 bug); _stop_dr failure is DR migration gap (Phase 23); motion_active homing is a logic gap (could be Phase 23 or earlier)
   - What's unclear: Whether Phase 28 introduced any new failures beyond the 17 identified
   - Recommendation: The 17 failures are the complete set as of this research date. Task 1 fixes all 17 and confirms the suite returns to 499 → 516 passing.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml config) |
| Config file | pyproject.toml |
| Quick run command | `python -m pytest tests/ -q --tb=no` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FIX-02 | Flat Grind live controller: graph draws, buttons gray out | manual (hardware) | N/A — hardware gate | N/A |
| FIX-02 | motion_active=True when STATE_HOMING | unit | `python -m pytest tests/test_run_screen.py::test_motion_gate_homing -x` | ✅ (currently failing) |
| FIX-02 | Status bar shows correct English state text | unit | `python -m pytest tests/test_status_bar.py -x` | ✅ (currently failing) |
| PI-06 | Three Pi deployment methods boot to login screen | manual (hardware) | N/A — hardware gate | N/A |
| PI-06 | deploy/pi/README.md covers all 3 methods | content inspection | manual review | ❌ Wave 0 |
| PI-06 | deploy/windows/README.md covers installer steps | content inspection | manual review | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -q --tb=no`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green (0 failures) before hardware validation tasks begin

### Wave 0 Gaps
- [ ] `deploy/pi/README.md` — technician deployment guide covering all 3 PI-06 methods (Task 2)
- [ ] `deploy/windows/README.md` — Windows installer instructions (Task 2)

*(All automated test files already exist — Wave 0 only requires documentation files and the 3 production code bug fixes.)*

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `src/dmccodegui/screens/status_bar.py` — confirmed Vietnamese strings in `_STATE_MAP`
- Direct code inspection: `src/dmccodegui/screens/flat_grind/run.py` — confirmed STATE_HOMING not handled in `_apply_state()` connected branch
- Direct code inspection: `tests/test_screen_loader.py` — confirmed `_BareApp` lacks `_stop_dr` method
- Direct test run: `python -m pytest tests/ -q` — confirmed 17 failed, 499 passed baseline
- CONTEXT.md Phase 29 — locked decisions on scope, workflow, and deliverables
- REQUIREMENTS.md — FIX-02 and PI-06 definitions
- STATE.md — critical pitfalls C1-C6, research flags

### Secondary (MEDIUM confidence)
- Phase 28 summaries (28-01, 28-02, 28-03) — confirmed what Phase 28 completed and what it did not touch
- Phase 26 CONTEXT.md (install.sh idempotency, deployment method decisions) — from accumulated project history

### Tertiary (LOW confidence)
- kivy_matplotlib_widget ARM wheel availability — unconfirmed; flagged in STATE.md as most likely Pi failure point

---

## Metadata

**Confidence breakdown:**
- Pre-existing bugs: HIGH — confirmed by direct test run and source inspection
- Architecture patterns: HIGH — directly derived from existing codebase and CONTEXT.md locked decisions
- Hardware validation pitfalls: MEDIUM — based on project history and research flags; actual outcomes determined by hardware tests

**Research date:** 2026-04-22
**Valid until:** Until hardware validation is complete (single-session phase)
