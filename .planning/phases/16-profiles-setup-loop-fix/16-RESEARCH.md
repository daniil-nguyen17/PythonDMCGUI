# Phase 16: ProfilesScreen Setup Loop Fix - Research

**Researched:** 2026-04-07
**Domain:** Kivy Screen lifecycle — on_pre_enter smart-enter guard, on_leave exit command
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- ProfilesScreen does NOT join the `_SETUP_SCREENS` frozenset in `axes_setup.py` or `parameters.py`
- ProfilesScreen manages its own enter/exit independently — navigating axes_setup→profiles triggers exit+re-enter, which is acceptable
- Only `profiles.py` is modified; `axes_setup.py` and `parameters.py` are untouched
- `on_pre_enter` must check `dmc_state == STATE_SETUP` before firing `hmiSetp=0`
- If already in `STATE_SETUP`, skip the trigger — just proceed with lifecycle (subscribe, update import button)
- Mirrors the pattern in `AxesSetupScreen` (lines 175–185) and `ParametersScreen` (lines 403–413)
- `on_leave` must send `hmiExSt=0` (not `hmiSetp=1`) to correctly exit setup mode
- Uses `HMI_EXIT_SETUP` and `HMI_TRIGGER_FIRE` from `dmc_vars.py`
- No `_SETUP_SCREENS` sibling check needed since profiles is not in the sibling set — always fires `hmiExSt=0` on leave

### Claude's Discretion

- Whether to add a connection guard (`controller.is_connected()`) to the enter/exit — axes_setup and parameters both check this
- Error handling pattern for the `hmiExSt` command

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SETP-01 | User can enter Setup mode on the controller from the HMI (sends hmiSetp=0) | Smart-enter guard ensures hmiSetp=0 is sent once on first entry; skipped if already in STATE_SETUP |
| SETP-08 | User can exit Setup mode back to main loop from HMI | on_leave must send hmiExSt=0 (via HMI_EXIT_SETUP constant); current code incorrectly sends hmiSetp=1 |
</phase_requirements>

---

## Summary

Phase 16 is a focused two-line-area bug fix in `src/dmccodegui/screens/profiles.py`. There are exactly two bugs: `on_pre_enter` fires `hmiSetp=0` unconditionally (line 443–447), and `on_leave` resets `hmiSetp=1` (line 459–463) instead of firing `hmiExSt=0`. Both patterns have verified working reference implementations already in the codebase — `AxesSetupScreen.on_pre_enter` (lines 175–186) and `ParametersScreen.on_pre_enter` (lines 403–422) for smart-enter; `AxesSetupScreen.on_leave` (lines 187–202) and `ParametersScreen.on_leave` (lines 424–443) for exit.

The fix differs slightly from sibling screens because ProfilesScreen is intentionally NOT added to the `_SETUP_SCREENS` frozenset. This means `on_leave` has no sibling check — it always fires `hmiExSt=0` when connected. The smart-enter guard in `on_pre_enter` is identical in logic to the sibling implementations: check `dmc_state == STATE_SETUP` before sending the trigger.

The connection guard (`controller.is_connected()`) is present in both reference implementations and should be adopted here for consistency. All controller commands use try/except with pass (fire-and-forget). The existing test suite for ProfilesScreen uses headless mock patterns that apply directly to the new tests needed.

**Primary recommendation:** Replicate AxesSetupScreen/ParametersScreen patterns verbatim into ProfilesScreen.on_pre_enter and on_leave, omitting only the `_SETUP_SCREENS` sibling check in on_leave.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dmccodegui.hmi.dmc_vars` | project-local | All DMC variable name constants | Single source of truth per Phase 09 decision |
| `dmccodegui.utils.jobs` | project-local | Background thread submission | All controller I/O must be off the main thread |

### Constants used in this phase
| Constant | Value | Meaning |
|----------|-------|---------|
| `HMI_SETP` | `"hmiSetp"` | Enter setup trigger variable name |
| `HMI_EXIT_SETUP` | `"hmiExSt"` | Exit setup trigger variable name |
| `HMI_TRIGGER_FIRE` | `0` | Value to write to fire a trigger |
| `HMI_TRIGGER_DEFAULT` | `1` | Resting/not-triggered value (used in WRONG code to be removed) |
| `STATE_SETUP` | `3` | hmiState integer when controller is in setup loop |

**Installation:** No new packages. All imports from existing project modules.

---

## Architecture Patterns

### Smart-Enter Guard (Reference: AxesSetupScreen lines 175–186)

**What:** Check if controller is already in STATE_SETUP before firing hmiSetp=0. If already there, skip the trigger entirely and go straight to the remaining lifecycle steps.

**When to use:** Always in on_pre_enter for any screen that triggers setup mode entry.

**Pattern from axes_setup.py (lines 178–185):**
```python
# Source: src/dmccodegui/screens/axes_setup.py lines 178–185
if self.controller and self.controller.is_connected():
    already_in_setup = (
        self.state is not None and self.state.dmc_state == STATE_SETUP
    )
    if already_in_setup:
        jobs.submit(self._read_initial_values)
    else:
        jobs.submit(self._enter_setup_and_read)
```

**Pattern from parameters.py (lines 403–413) — no background job branch:**
```python
# Source: src/dmccodegui/screens/parameters.py lines 403–413
already_in_setup = (
    self.state is not None and self.state.dmc_state == STATE_SETUP
)
if self.controller is not None and self.controller.is_connected():
    if not already_in_setup:
        try:
            self.controller.cmd(f"{HMI_SETP}={HMI_TRIGGER_FIRE}")
        except Exception:
            pass
```

**ProfilesScreen adaptation:** ProfilesScreen's on_pre_enter has no background job branch (no initial values to read). Use the ParametersScreen inline pattern — check connection, check already_in_setup, fire conditionally.

### Exit Command Pattern (Reference: ParametersScreen lines 424–443)

**What:** on_leave sends `hmiExSt=0` (HMI_EXIT_SETUP) to exit the controller setup loop. For ProfilesScreen (no sibling membership), there is NO `next_screen not in _SETUP_SCREENS` check — always fire when connected.

**ParametersScreen on_leave with sibling check (for reference):**
```python
# Source: src/dmccodegui/screens/parameters.py lines 424–443
next_screen = ""
if self.manager:
    next_screen = self.manager.current
if next_screen not in _SETUP_SCREENS:
    if self.controller is not None and self.controller.is_connected():
        try:
            self.controller.cmd(f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}")
        except Exception:
            pass
```

**ProfilesScreen adaptation (no sibling check):**
```python
# Always fire hmiExSt=0 — profiles is not in any sibling frozenset
if self.controller is not None and self.controller.is_connected():
    try:
        self.controller.cmd(f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}")
    except Exception:
        pass
```

### Anti-Patterns to Avoid

- **Sending `hmiSetp=1` on leave:** This is the current bug. `hmiSetp` is an enter-setup trigger only. Exiting uses `hmiExSt` (HMI_EXIT_SETUP). Never reset `hmiSetp` to 1 explicitly from Python — the DMC program owns that reset.
- **Using `HMI_TRIGGER_DEFAULT` in on_leave:** `HMI_TRIGGER_DEFAULT=1` is the rest state of HMI vars managed by DMC. Python should only ever write `HMI_TRIGGER_FIRE=0` to fire triggers. Writing 1 to `hmiSetp` is semantically wrong and mimics an "enter setup" that was never requested.
- **Importing `HMI_TRIGGER_DEFAULT` into on_leave:** Once the bug is fixed, the on_leave method will no longer need `HMI_TRIGGER_DEFAULT` — remove that import from on_leave.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Controller state check | Custom polling or event subscription | `self.state.dmc_state == STATE_SETUP` | MachineState already polled at 10 Hz; truth is there |
| Background thread | threading.Thread | `jobs.submit()` | Serialized through FIFO worker, prevents concurrent handle access |
| Variable name strings | Raw literals like `"hmiExSt=0"` | `f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}"` | dmc_vars.py is single source of truth — prevents 8-char typos |

**Key insight:** The entire fix is pattern-replication. Any custom logic is wrong — copy exactly from reference implementations.

---

## Common Pitfalls

### Pitfall 1: Adding profiles to _SETUP_SCREENS in axes_setup.py or parameters.py
**What goes wrong:** Navigating axes_setup → profiles would incorrectly suppress hmiExSt=0, leaving controller in setup mode when leaving to profiles screen (which does its own enter separately). This contradicts the CONTEXT.md decision.
**Why it happens:** Cargo-culting the sibling pattern when profiles is explicitly NOT a sibling.
**How to avoid:** Only profiles.py is modified. `_SETUP_SCREENS` in axes_setup.py and parameters.py stays as `frozenset({"axes_setup", "parameters"})`.
**Warning signs:** Any modification to axes_setup.py or parameters.py in this plan.

### Pitfall 2: Keeping the `HMI_TRIGGER_DEFAULT` / `hmiSetp` import in on_leave
**What goes wrong:** Dead imports remain, code is confusing, and future readers may think the pattern is intentional.
**Why it happens:** Partial fix — changing the command string but forgetting to clean up imports.
**How to avoid:** on_leave should import only `HMI_EXIT_SETUP` and `HMI_TRIGGER_FIRE`. Remove `HMI_SETP` and `HMI_TRIGGER_DEFAULT` from on_leave's import block (they are only needed in on_pre_enter).

### Pitfall 3: Moving connection check OUTSIDE the already_in_setup branch
**What goes wrong:** If controller is not connected, `self.state.dmc_state` comparison still runs, which is fine, but the subscribe/update-import-button path below the guard should always run regardless.
**Why it happens:** Putting the connection guard too high up, before the subscribe call.
**How to avoid:** Connection guard wraps only the controller.cmd() call — subscribe and `_update_import_button()` run unconditionally after the guard, matching the existing on_pre_enter structure.

### Pitfall 4: Omitting connection guard in on_leave
**What goes wrong:** Calling `self.controller.cmd()` when controller is None or disconnected raises AttributeError or connection error.
**Why it happens:** The on_leave fix is simple — easy to skip the guard.
**How to avoid:** Always check `self.controller is not None and self.controller.is_connected()` before cmd(), as both reference implementations do.

---

## Code Examples

### Current Buggy on_pre_enter (lines 440–454 in profiles.py)
```python
# CURRENT — fires unconditionally, bug SETP-01
def on_pre_enter(self, *args) -> None:
    if self.controller is not None:
        try:
            from dmccodegui.hmi.dmc_vars import HMI_SETP, HMI_TRIGGER_FIRE
            self.controller.cmd(f"{HMI_SETP}={HMI_TRIGGER_FIRE}")
        except Exception:
            pass
    if self.state is not None:
        self._unsubscribe = self.state.subscribe(...)
    self._update_import_button()
```

### Fixed on_pre_enter
```python
# FIXED — smart-enter guard, mirrors ParametersScreen pattern
def on_pre_enter(self, *args) -> None:
    from dmccodegui.hmi.dmc_vars import HMI_SETP, HMI_TRIGGER_FIRE, STATE_SETUP

    already_in_setup = (
        self.state is not None and self.state.dmc_state == STATE_SETUP
    )
    if self.controller is not None and self.controller.is_connected():
        if not already_in_setup:
            try:
                self.controller.cmd(f"{HMI_SETP}={HMI_TRIGGER_FIRE}")
            except Exception:
                pass

    if self.state is not None:
        self._unsubscribe = self.state.subscribe(
            lambda s: Clock.schedule_once(lambda *_: self._update_import_button())
        )
    self._update_import_button()
```

### Current Buggy on_leave (lines 456–468 in profiles.py)
```python
# CURRENT — wrong command: hmiSetp=1, bug SETP-08
def on_leave(self, *args) -> None:
    if self.controller is not None:
        try:
            from dmccodegui.hmi.dmc_vars import HMI_SETP, HMI_TRIGGER_DEFAULT
            self.controller.cmd(f"{HMI_SETP}={HMI_TRIGGER_DEFAULT}")  # sends hmiSetp=1
        except Exception:
            pass
    if self._unsubscribe is not None:
        self._unsubscribe()
        self._unsubscribe = None
```

### Fixed on_leave
```python
# FIXED — correct command: hmiExSt=0, no sibling check (profiles not in _SETUP_SCREENS)
def on_leave(self, *args) -> None:
    if self.controller is not None and self.controller.is_connected():
        try:
            from dmccodegui.hmi.dmc_vars import HMI_EXIT_SETUP, HMI_TRIGGER_FIRE
            self.controller.cmd(f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}")
        except Exception:
            pass
    if self._unsubscribe is not None:
        self._unsubscribe()
        self._unsubscribe = None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Unconditional hmiSetp=0 on enter | Smart-enter guard (check STATE_SETUP first) | Phase 13 for axes_setup/parameters | Prevents spurious setup loop re-entry |
| hmiSetp=1 to "exit" | hmiExSt=0 (HMI_EXIT_SETUP) | Phase 13 for axes_setup/parameters | Correct exit command that DMC program listens for |

**Deprecated/outdated:**
- `hmiSetp=HMI_TRIGGER_DEFAULT` in on_leave: Never correct. `hmiSetp` is an enter-only trigger. Exit uses `hmiExSt`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pytest.ini` or `pyproject.toml` (existing) |
| Quick run command | `pytest tests/test_profiles.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SETP-01 | on_pre_enter with dmc_state=STATE_SETUP does NOT send hmiSetp=0 | unit | `pytest tests/test_profiles.py::test_enter_skips_fire_when_already_setup -x` | ❌ Wave 0 |
| SETP-01 | on_pre_enter with dmc_state=STATE_IDLE sends hmiSetp=0 | unit | `pytest tests/test_profiles.py::test_enter_fires_when_not_in_setup -x` | ❌ Wave 0 |
| SETP-08 | on_leave sends hmiExSt=0 when connected | unit | `pytest tests/test_profiles.py::test_exit_fires_hmi_exit_setup -x` | ❌ Wave 0 |
| SETP-08 | on_leave does NOT send hmiSetp=1 | unit | `pytest tests/test_profiles.py::test_exit_does_not_send_hmiSetp -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_profiles.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_profiles.py` — add 4 new test functions to existing class for SETP-01 and SETP-08 (file exists, needs new tests added)

**Test pattern (mirrors test_parameters.py lines 479–567):**
```python
# In tests/test_profiles.py — add to existing file

def _make_profiles_screen(connected: bool, dmc_state: int):
    """Create ProfilesScreen with mock controller and state — no Kivy needed."""
    import os
    os.environ.setdefault('KIVY_NO_ENV_CONFIG', '1')
    os.environ.setdefault('KIVY_LOG_LEVEL', 'critical')
    from unittest.mock import MagicMock
    from dmccodegui.screens.profiles import ProfilesScreen

    screen = ProfilesScreen.__new__(ProfilesScreen)
    screen._unsubscribe = None
    screen._pending_parsed = None

    ctrl = MagicMock()
    ctrl.is_connected.return_value = connected
    ctrl.cmd.return_value = ""
    screen.controller = ctrl

    state = MagicMock()
    state.dmc_state = dmc_state
    screen.state = state

    return screen, ctrl


def test_enter_skips_fire_when_already_setup():
    """SETP-01: on_pre_enter with dmc_state=STATE_SETUP does NOT send hmiSetp=0."""
    from dmccodegui.hmi.dmc_vars import STATE_SETUP
    from unittest.mock import patch

    screen, ctrl = _make_profiles_screen(connected=True, dmc_state=STATE_SETUP)

    with patch('dmccodegui.screens.profiles.Clock'):
        screen.on_pre_enter()

    calls = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert not any('hmiSetp=0' in s for s in calls)


def test_enter_fires_when_not_in_setup():
    """SETP-01: on_pre_enter with dmc_state=STATE_IDLE sends hmiSetp=0."""
    from dmccodegui.hmi.dmc_vars import STATE_IDLE
    from unittest.mock import patch

    screen, ctrl = _make_profiles_screen(connected=True, dmc_state=STATE_IDLE)

    with patch('dmccodegui.screens.profiles.Clock'):
        screen.on_pre_enter()

    calls = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert any('hmiSetp=0' in s for s in calls)


def test_exit_fires_hmi_exit_setup():
    """SETP-08: on_leave sends hmiExSt=0."""
    from unittest.mock import patch

    screen, ctrl = _make_profiles_screen(connected=True, dmc_state=3)

    screen.on_leave()

    calls = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert any('hmiExSt=0' in s for s in calls)


def test_exit_does_not_send_hmiSetp():
    """SETP-08: on_leave does NOT send hmiSetp=1 (old bug)."""
    from unittest.mock import patch

    screen, ctrl = _make_profiles_screen(connected=True, dmc_state=3)

    screen.on_leave()

    calls = [c[0][0] for c in ctrl.cmd.call_args_list]
    assert not any('hmiSetp=1' in s for s in calls)
```

*(Existing test infrastructure covers all other phase behavior — only these 4 gap tests needed.)*

---

## Open Questions

1. **Import placement: module-level vs inline in methods**
   - What we know: current profiles.py uses inline imports inside try blocks in on_pre_enter/on_leave
   - What's unclear: AxesSetupScreen imports at module level; ParametersScreen also module level; profiles uses inline. Which style should match?
   - Recommendation: Use module-level imports in the fixed version — matches axes_setup.py and parameters.py, eliminates repeated import overhead per lifecycle call. The existing inline style in profiles.py was likely incidental to the original implementation.

---

## Sources

### Primary (HIGH confidence)
- `src/dmccodegui/screens/profiles.py` — current buggy implementation, lines 440–468
- `src/dmccodegui/screens/axes_setup.py` — reference smart-enter implementation, lines 155–203
- `src/dmccodegui/screens/parameters.py` — reference smart-enter and exit implementation, lines 393–443
- `src/dmccodegui/hmi/dmc_vars.py` — all HMI constants, verified present: HMI_SETP, HMI_EXIT_SETUP, HMI_TRIGGER_FIRE, HMI_TRIGGER_DEFAULT, STATE_SETUP
- `tests/test_parameters.py` — test pattern for smart-enter/exit, lines 479–567

### Secondary (MEDIUM confidence)
- `.planning/phases/16-profiles-setup-loop-fix/16-CONTEXT.md` — locked implementation decisions
- `.planning/REQUIREMENTS.md` — SETP-01 and SETP-08 requirement definitions

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all constants and modules directly verified in source
- Architecture: HIGH — reference implementations read line-by-line from axes_setup.py and parameters.py
- Pitfalls: HIGH — bugs confirmed by reading current profiles.py on_pre_enter (line 446) and on_leave (line 461)

**Research date:** 2026-04-07
**Valid until:** Stable — no external dependencies, pure internal pattern replication
