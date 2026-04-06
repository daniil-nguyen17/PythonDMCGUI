# Phase 9: DMC Foundation - Research

**Researched:** 2026-04-06
**Domain:** Galil DMC program modification + Python constants module creation
**Confidence:** HIGH (all findings are from direct codebase inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Array name alignment**
- Replace startPt[4] and restPt[4] arrays with individual named variables: startPtA, startPtB, startPtC, startPtD, restPtA, restPtB, restPtC, restPtD
- All 4 axes declared for all machine types (unused axes hold 0)
- Remove the unused hmiBtn[40] array from the DMC file
- Computed sequence arrays (deltaD[], deltaC[], bComp[]) remain as indexed arrays — only position points get individual variables
- Python constants use exact DMC names (e.g., constant value is 'startPtA', not a human-friendly alias)
- Phase 9 updates ALL existing Python screen files to use constants from dmc_vars.py — no stale StartPnt/RestPnt strings left behind

**hmiState encoding**
- Keep hmiState as a dedicated DMC variable (not derived from trigger variables) — authoritative source for machine state including physical-button-initiated actions
- 4 core states only: IDLE=1, GRINDING=2, SETUP=3, HOMING=4
- hmiState=0 means uninitialized/error (all valid states are nonzero)
- No sub-states for GOING_TO_REST, GOING_TO_START, etc. — those are brief motions under core states
- State transitions tied to trigger variable lifecycle: hmiGrnd=0 triggers GRINDING state, reset to 1 returns to IDLE

**DMC backward compatibility**
- OR logic for all triggers: `IF (@IN[29]=0) | (hmiGrnd=0)` — physical buttons AND HMI variables both work
- Simultaneous physical button + HMI trigger is an acceptable race condition (subroutine runs once regardless)
- All OR conditions added in Phase 9 — both #WtAtRt (main loop) and #SULOOP (setup loop) modified in a single pass
- DMC file tracked in repo (already at repo root as '4 Axis Stainless grind.dmc')
- Keep original filename '4 Axis Stainless grind.dmc' — do not rename
- Leave existing DMC header comments as-is — only modify functional code

**Python constants scope**
- New file: src/dmccodegui/hmi/dmc_vars.py (new hmi/ package)
- Contains: HMI trigger variable names, hmiState integer constants, position variable names, default values — full integration contract in one file
- Flat Grind only for now — Serration/Convex constants added later when those DMC files arrive
- Parameter variable names (knfThk, fdA, etc.) stay in machine_config.py — they differ per machine type and are already there

### Claude's Discretion
- Exact structure/grouping within dmc_vars.py
- How to organize the hmi/ package __init__.py
- Which screen files need what level of refactoring to use new constants
- DMC OR condition syntax details

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DMC-01 | DMC program declares HMI trigger variables (hmiGrnd, hmiSetp, hmiMore, hmiLess, hmiNewS, hmiHome, hmiJog, hmiCalc) with default=1 in #PARAMS | #PARAMS block identified at line 448; DM/variable assignments pattern confirmed |
| DMC-02 | DMC main polling loop (#WtAtRt) OR's each @IN[] check with its corresponding HMI variable | #WtAtRt at line 38 inspected; current IF blocks confirmed, OR syntax pattern identified |
| DMC-03 | DMC resets each HMI variable to 1 as the first line inside each triggered block (before any motion) | Entry points confirmed: #GRIND, #SETUP, #NEWSESS, #MOREGRI, #LESSGRI |
| DMC-04 | DMC declares hmiState variable and sets it to distinct integer values at each state boundary | All state boundaries mapped: IDLE, GRINDING (in #GRIND), SETUP (in #SETUP), HOMING (in #HOME) |
| DMC-05 | DMC setup loop (#SULOOP) OR's physical button checks with HMI variables for home, jog, varcalc, and exit | #SULOOP at line 152 inspected; 4 button conditions confirmed |
| DMC-06 | Array names in Python code match DMC declarations (startPt/restPt, not StartPnt/RestPnt) | All 4 stale-name callsites identified across rest.py, start.py, axisDSetup.py, parameters_setup.py |
</phase_requirements>

---

## Summary

Phase 9 has two parallel work streams: (1) modifying the existing `4 Axis Stainless grind.dmc` file to add HMI trigger variables, OR conditions, hmiState tracking, and convert arrays to individual variables; and (2) creating a new Python constants module at `src/dmccodegui/hmi/dmc_vars.py` and migrating all screen files that currently use stale `StartPnt`/`RestPnt` string literals to use those constants.

The DMC file is fully readable and the complete current structure is known. The `#PARAMS` block is the right insertion point for all new variable declarations. The `#WtAtRt` loop has exactly 5 IF blocks to modify (GRIND, SETUP, NEWSESS, MOREGRI, LESSGRI). The `#SULOOP` block has exactly 4 IF blocks to modify (JOG, HOME, VARCALC, RETURN). The array-to-individual-variable conversion affects `#PARAMS` (declaration), `#SETREST`, `#SETSTR`, `#GOREST`, `#GOSTR`, `#MOREGRI`, `#LESSGRI`, and the diagnostic MG print lines inside those routines.

The Python migration scope is well bounded: four files have stale string literals (`rest.py`, `start.py`, `axisDSetup.py`, `parameters_setup.py`). One file (`axes_setup.py`) already uses the correct individual-variable pattern (`restPtA`, `startPtA`) and only needs to import from `dmc_vars.py` for future phases. The `app_state.py` dataclass needs one new field (`dmc_state: int = 0`). The `hmi/` package directory does not yet exist and must be created.

**Primary recommendation:** Work in this order: (1) create `hmi/dmc_vars.py` with constants, (2) modify DMC file, (3) migrate Python screen files, (4) add `dmc_state` to `MachineState`, (5) write tests. The constants module must be created before screen migration so imports resolve during testing.

---

## Standard Stack

### Core
| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| gclib Python wrapper | installed | Controller communication | Project's existing integration layer |
| pytest | installed (pyproject.toml dev dep) | Unit tests | Already used by 12 existing test files |
| Python dataclasses | stdlib | MachineState field additions | Already used in app_state.py |

### Supporting
| Component | Location | Purpose |
|-----------|----------|---------|
| `GalilController.cmd()` | controller.py | Single command execution; used for MG queries and variable writes |
| `jobs.submit()` | utils/jobs.py | All controller I/O off UI thread |
| `machine_config._FLAT_PARAM_DEFS` | machine_config.py | Pattern for constants organization |

**No new packages are required.** This phase is pure DMC file editing, Python module creation, and refactoring of existing code.

---

## Architecture Patterns

### Recommended Project Structure Addition
```
src/dmccodegui/
├── hmi/                 # NEW — HMI-controller integration contract
│   ├── __init__.py      # NEW — minimal, exports key names
│   └── dmc_vars.py      # NEW — all DMC variable name constants
├── app_state.py         # MODIFIED — add dmc_state field
├── screens/
│   ├── rest.py          # MODIFIED — use RESTPT_* constants
│   ├── start.py         # MODIFIED — use STARTPT_* constants
│   ├── axisDSetup.py    # MODIFIED — use RESTPT_* constants
│   └── parameters_setup.py  # MODIFIED — use RESTPT_* constants
└── (unchanged files)
4 Axis Stainless grind.dmc  # MODIFIED (repo root)
```

### Pattern 1: dmc_vars.py Constants Module Structure

**What:** A flat Python module holding string constants for all DMC variable names and integer constants for hmiState values. Constants are exact DMC names — no aliases.

**When to use:** Any Python code that sends a variable name to the controller reads from here, never a raw string literal.

```python
# src/dmccodegui/hmi/dmc_vars.py

# --- HMI trigger variables (default=1 on controller, send 0 to trigger) ---
HMI_GRND  = "hmiGrnd"   # Start grind cycle
HMI_SETP  = "hmiSetp"   # Enter setup mode
HMI_MORE  = "hmiMore"   # More stone compensation
HMI_LESS  = "hmiLess"   # Less stone compensation
HMI_NEWS  = "hmiNewS"   # New session (stone change)
HMI_HOME  = "hmiHome"   # Homing sequence
HMI_JOG   = "hmiJog"    # Jog mode
HMI_CALC  = "hmiCalc"   # Varcalc recalculation

HMI_TRIGGER_DEFAULT = 1  # All trigger vars default to this value
HMI_TRIGGER_FIRE    = 0  # Send this value to trigger an action

# --- hmiState values (polled from controller to determine machine state) ---
HMI_STATE_VAR      = "hmiState"
STATE_UNINITIALIZED = 0   # Controller not yet running or error
STATE_IDLE          = 1   # Main loop waiting, no motion
STATE_GRINDING      = 2   # Grind cycle active (#GRIND running)
STATE_SETUP         = 3   # Setup mode active (#SULOOP running)
STATE_HOMING        = 4   # Homing sequence active (#HOME running)

# --- Position variable names (individual scalars, replaces startPt[]/restPt[] arrays) ---
# Flat Grind — 4 axes (A, B, C, D)
RESTPT_A  = "restPtA"
RESTPT_B  = "restPtB"
RESTPT_C  = "restPtC"
RESTPT_D  = "restPtD"

STARTPT_A = "startPtA"
STARTPT_B = "startPtB"
STARTPT_C = "startPtC"
STARTPT_D = "startPtD"

# Ordered lists for batch operations (index = axis ordinal: A=0, B=1, C=2, D=3)
RESTPT_VARS  = [RESTPT_A,  RESTPT_B,  RESTPT_C,  RESTPT_D]
STARTPT_VARS = [STARTPT_A, STARTPT_B, STARTPT_C, STARTPT_D]

# Axis letter to variable name mapping (for AxesSetupScreen-style iteration)
RESTPT_BY_AXIS  = {"A": RESTPT_A,  "B": RESTPT_B,  "C": RESTPT_C,  "D": RESTPT_D}
STARTPT_BY_AXIS = {"A": STARTPT_A, "B": STARTPT_B, "C": STARTPT_C, "D": STARTPT_D}
```

### Pattern 2: DMC OR Condition Syntax

**What:** Each physical button IF block gets the HMI variable added as an OR condition.

**Galil DMC OR operator:** `|` (pipe character). Tested expression: `IF (expr1) | (expr2)`.

**When to use:** Every input-check IF block in #WtAtRt and #SULOOP.

```
' BEFORE (physical button only):
IF (@IN[29] = 0);             ' GO GRIND button
  SB 1;
  JS #GRIND
  JP #WtAtRt
ENDIF

' AFTER (OR with HMI variable):
IF (@IN[29] = 0) | (hmiGrnd = 0);   ' GO GRIND button OR HMI trigger
  hmiGrnd = 1;                        ' reset HMI var FIRST, before any motion
  hmiState = 2;                        ' GRINDING
  SB 1;
  JS #GRIND
  hmiState = 1;                        ' back to IDLE after grind completes
  JP #WtAtRt
ENDIF
```

### Pattern 3: DMC Variable Declaration in #PARAMS

**What:** All new scalar DMC variables declared and initialized in #PARAMS, replacing DM array declarations for position points.

```
' REMOVE these lines from #PARAMS:
DM startPt[4]; ' A B C D absolute start positions
DM restPt[4];  ' A B C D rest/park positions
DM hmiBtn[40]

' ADD these lines in #PARAMS:
' --- HMI trigger variables (default=1, send 0 to trigger) ---
hmiGrnd = 1
hmiSetp = 1
hmiMore = 1
hmiLess = 1
hmiNewS = 1
hmiHome = 1
hmiJog  = 1
hmiCalc = 1

' --- Machine state (IDLE=1, GRINDING=2, SETUP=3, HOMING=4) ---
hmiState = 1

' --- Position points as individual variables (all 4 axes) ---
startPtA = 0; startPtB = 0; startPtC = 0; startPtD = 0
restPtA  = 0; restPtB  = 0; restPtC  = 0; restPtD  = 0
```

### Pattern 4: MachineState dmc_state Field Addition

**What:** Add a new integer field to the MachineState dataclass to hold the current controller hmiState value.

```python
# app_state.py — add after cycle_completion_pct field
dmc_state: int = 0  # hmiState from controller; 0=uninitialized, 1=IDLE, 2=GRINDING, 3=SETUP, 4=HOMING
```

**Note:** `cycle_running` remains for now as a Python-side derived field; it becomes derived from `dmc_state` in Phase 14.

### Pattern 5: Screen File Migration

**What:** Replace raw string literals with imported constants from dmc_vars.

```python
# BEFORE (rest.py, axisDSetup.py, parameters_setup.py):
vals = self.controller.upload_array("RestPnt", 0, 2)
self.controller.download_array("RestPnt", 0, self.rest_vals)

# AFTER — must switch from array to individual variable reads:
from dmccodegui.hmi.dmc_vars import RESTPT_A, RESTPT_B, RESTPT_C, RESTPT_D, RESTPT_BY_AXIS

# Read individual variables
raw = ctrl.cmd(f"MG {RESTPT_BY_AXIS[axis]}").strip()

# Write individual variables
parts = [f"{RESTPT_BY_AXIS[axis]}={vals[axis]}" for axis in axis_list]
ctrl.cmd(";".join(parts))
```

**Important:** `rest.py`, `start.py`, and `axisDSetup.py` currently call `upload_array("RestPnt"/"StartPnt", ...)` and `download_array("RestPnt"/"StartPnt", ...)`. After migration these MUST switch to individual `MG varName` reads and semicolon-joined assignment writes — the DMC arrays will no longer exist.

### Anti-Patterns to Avoid

- **Raw string literals for DMC names:** Any `"StartPnt"`, `"RestPnt"`, `"hmiGrnd"` etc. typed directly in screen files — use constants.
- **XQ direct calls:** Out of scope per memory constraint. Never add `XQ #GRIND` etc. All triggers through HMI variable pattern only.
- **Resetting HMI variable after motion:** The reset must be the FIRST line inside the triggered block, before SH/SP/BG commands.
- **hmiState=0 as a named state:** Zero is reserved for uninitialized/error. All operational states are 1+.
- **BV in DMC trigger blocks:** BV burns EEPROM. Only appropriate at end of teach operations (#SETREST, #SETSTR, VARCALC). Do not add BV calls when updating hmiState.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semicolon-joined DMC command batch | Custom serializer | f-string join pattern (already in axes_setup.py) | `";".join(parts)` already works, keeps lines <300 chars |
| Individual variable read loop | Custom protocol | `ctrl.cmd(f"MG {varname}")` | `GalilController.cmd()` already handles error wrapping |
| HMI package init | Complex re-export tree | Minimal `__init__.py` with top-level imports | hmi/ is a simple namespace, not a framework |

---

## Common Pitfalls

### Pitfall 1: DMC 8-Character Variable Name Limit
**What goes wrong:** DMC variable names are limited to 8 characters. `hmiGrnd` = 7 chars (OK). `hmiState` = 8 chars (OK, exactly at limit). Any alias longer than 8 chars will cause a DMC parse error and the variable will silently not be declared.
**Why it happens:** The Galil controller rejects longer names without a clear Python-side error.
**How to avoid:** Verify all 8 new trigger names and the 8 position var names stay at or under 8 characters. Confirmed counts: `hmiGrnd`=7, `hmiSetp`=7, `hmiMore`=7, `hmiLess`=7, `hmiNewS`=7, `hmiHome`=7, `hmiJog`=6, `hmiCalc`=7, `hmiState`=8, `startPtA`=8, `restPtA`=7. All valid.
**Warning signs:** `MG hmiState` returns `?` after upload.

### Pitfall 2: Array-to-Scalar Migration Breaks Array Ops
**What goes wrong:** `rest.py`, `start.py`, `axisDSetup.py`, and `parameters_setup.py` all call `upload_array("RestPnt"/"StartPnt", ...)` and `download_array(...)`. After the DMC arrays are removed, these calls will fail at runtime with a controller error.
**Why it happens:** The Python files are reading DMC arrays that no longer exist after the DM declaration is removed from #PARAMS.
**How to avoid:** Phase 9 must update ALL four stale files to use individual MG queries and assignment commands. The `axes_setup.py` file already uses the individual pattern and serves as a reference.
**Warning signs:** `upload_array` returns `ControllerNotReady("Array restPt not available")` or `"Bad function or array"` error from controller.

### Pitfall 3: hmiState Not Set on Entry to #HOME Called from #SETUP
**What goes wrong:** #HOME is called via `JS #HOME` from within #SETUP (at SULOOP button 25). If `hmiState = 4` (HOMING) is only set at the top of #HOME, it correctly fires. But if hmiState is set to 3 (SETUP) in #SETUP and never changed to 4 when #HOME is JSed from inside setup, then polling cannot distinguish HOMING from SETUP.
**How to avoid:** Set `hmiState = 4` at the START of #HOME, restore to appropriate state (SETUP=3 or IDLE=1) at the END of #HOME based on call context. The simplest correct approach: set `hmiState = 4` at start of #HOME, set `hmiState = 3` at end of #HOME (if called from within SULOOP, the SULOOP will immediately be running again). When #HOME is called from #AUTO at startup, set to 1 (IDLE) after. This distinction can be handled by setting `hmiState = 1` after the standalone #HOME call in #AUTO, and letting SULOOP manage the return from #HOME when JSed from within setup.
**Warning signs:** Polling shows STATE_HOMING when setup mode is active even when not homing.

### Pitfall 4: startPt/restPt Case-Sensitivity on Controller
**What goes wrong:** The current DMC file uses `startPt` and `restPt` (mixed case). The Python `axes_setup.py` already uses `restPtA`/`startPtA` (already the target names). But `rest.py`/`start.py` use `RestPnt`/`StartPnt` (different name AND capitalization). The controller treats all variable names as case-insensitive at the DMC level, but the Python constants must match exactly what is declared in the DMC program.
**How to avoid:** Declare exactly `startPtA`, `restPtA` (lowercase `s`, `r`) in #PARAMS. Python constants use the same case. `axes_setup.py` already uses this exact casing.
**Warning signs:** STATE.md flags this as a hardware validation item.

### Pitfall 5: hmiState Assignment Placement Around JS Calls
**What goes wrong:** `JS #GRIND` is a subroutine call that returns. `hmiState = 2` must be set BEFORE `JS #GRIND`, and `hmiState = 1` AFTER the JS returns. If set inside #GRIND itself (where motion happens), this is also acceptable — but the outer IF block in #WtAtRt is the clearest location.
**How to avoid:** Set hmiState immediately after the HMI variable reset and before any JS call:
```
IF (@IN[29] = 0) | (hmiGrnd = 0)
  hmiGrnd = 1
  hmiState = 2
  SB 1
  JS #GRIND
  hmiState = 1
  JP #WtAtRt
ENDIF
```

### Pitfall 6: gclib Handle Not Closed on App Exit
**What goes wrong:** Success criterion 5 requires that after forced close, a new connection can be opened immediately. The current `on_stop()` in `main.py` calls `jobs.shutdown()` then `self.controller.disconnect()`. If `jobs.shutdown()` blocks until the jobs queue drains but a background job is holding the connection open, the disconnect call races with the job.
**What to verify:** `GalilController.disconnect()` calls `self._driver.GClose()` in a try/except with `finally: self._connected = False`. This is correct. The `globalDMC` module-level handle in `controller.py` is created once at import time (lines 21-28) but is NOT the handle used by `GalilController` (which creates its own handle in `connect()`). The module-level handle may leak. This needs verification.
**How to avoid:** The `globalDMC` variable at module level in `controller.py` is never used by `GalilController` — `connect()` creates its own `gclib.py()` instance stored in `self._driver`. The `globalDMC` reference holds an unclosed handle at module scope. For clean exit, either set `globalDMC = None` (the handle is never opened, just instantiated) or confirm `gclib.py()` instantiation does not open a connection (it should not — `GOpen` is the connection call). This is LOW risk but worth confirming on hardware.

---

## Code Examples

Verified patterns from codebase inspection:

### Existing Individual Variable Write Pattern (from axes_setup.py lines 291, 344)
```python
# Source: src/dmccodegui/screens/axes_setup.py
parts = [f"restPt{axis}={vals[axis]}" for axis in axis_list]
write_cmd = ";".join(parts)
ctrl.cmd(write_cmd)
ctrl.cmd("BV")
```
This is the REFERENCE PATTERN for all screen file migrations.

### Existing Individual Variable Read Pattern (from axes_setup.py lines 457, 462)
```python
# Source: src/dmccodegui/screens/axes_setup.py
raw = ctrl.cmd(f"MG restPt{axis}").strip()
# and
raw = ctrl.cmd(f"MG startPt{axis}").strip()
```

### DMC OR Condition Syntax (Galil standard)
```
' Galil DMC syntax — pipe character for OR
IF (@IN[29] = 0) | (hmiGrnd = 0)
  hmiGrnd = 1;              ' reset FIRST
  hmiState = 2;              ' GRINDING
  SB 1
  JS #GRIND
  hmiState = 1;              ' IDLE (back from grind)
  JP #WtAtRt
ENDIF
```

### DMC Variable Declaration in #PARAMS
```
' Declare scalar — just assign, no DM needed for scalars
hmiGrnd = 1
hmiState = 1
startPtA = 0

' DM still required for indexed arrays
DM deltaA[300]
```

### dmc_vars.py Import Pattern in Screen Files
```python
# At top of file
from dmccodegui.hmi.dmc_vars import RESTPT_BY_AXIS, STARTPT_BY_AXIS

# Usage (replaces upload_array("RestPnt", ...) pattern)
raw = ctrl.cmd(f"MG {RESTPT_BY_AXIS['A']}").strip()
```

### hmi/__init__.py (minimal)
```python
# src/dmccodegui/hmi/__init__.py
"""HMI-controller integration package.

Provides:
  dmc_vars  — DMC variable name constants and hmiState encoding
"""
from . import dmc_vars  # noqa: F401
```

---

## Complete DMC Modification Map

Every line that must change in `4 Axis Stainless grind.dmc`:

### Section 1: #PARAMS block (lines 448-473 in current file)

**Remove:**
```
DM startPt[4]; ' A B C D absolute start positions
DM restPt[4];  ' A B C D rest/park positions
DM hmiBtn[40]
```

**Add (after existing scalar variable assignments):**
```
' --- HMI trigger variables (default=1) ---
hmiGrnd = 1;  hmiSetp = 1;  hmiMore = 1;  hmiLess = 1
hmiNewS = 1;  hmiHome = 1;  hmiJog  = 1;  hmiCalc = 1
' --- Machine state (1=IDLE 2=GRINDING 3=SETUP 4=HOMING) ---
hmiState = 1
' --- Position scalars (4 axes, unused hold 0) ---
startPtA = 0; startPtB = 0; startPtC = 0; startPtD = 0
restPtA  = 0; restPtB  = 0; restPtC  = 0; restPtD  = 0
```

### Section 2: #WtAtRt block (lines 38-71)

5 IF blocks modified:

| Current @IN | HMI Variable | Block entered |
|-------------|--------------|---------------|
| @IN[29]=0 | hmiGrnd=0 | #GRIND (sets hmiState=2, resets to 1 after) |
| @IN[41]=0 | hmiSetp=0 | #SETUP (sets hmiState=3 inside #SETUP) |
| @IN[44]=0 | hmiNewS=0 | #NEWSESS (sets hmiState=2 during new session) |
| @IN[33]=0 | hmiMore=0 | #MOREGRI |
| @IN[36]=0 | hmiLess=0 | #LESSGRI |

### Section 3: #SULOOP block (lines 152-183)

4 IF blocks modified:

| Current @IN | HMI Variable | Action |
|-------------|--------------|--------|
| @IN[23]=0 | hmiJog=0 | #WheelJg (jog mode) |
| @IN[25]=0 | hmiHome=0 | #HOME (sets hmiState=4) |
| @IN[26]=0 | hmiCalc=0 | #VARCALC |
| @IN[32]=0 | (none — exit setup) | EN |

Note: The exit-setup button (@IN[32]) has no HMI variable equivalent in Phase 9 (SETP-08 is Phase 13). Do not add a HMI variable for exit in this phase.

### Section 4: #SETREST (lines 195-199)

Replace `restPt[0..3]` assignments with individual variable assignments:
```
' BEFORE:
restPt[0] = _TDA; ...

' AFTER:
restPtA = _TDA; WT 50; MG "SET REST A=", restPtA
restPtB = _TDB; WT 50; MG "SET REST B=", restPtB
restPtC = _TDC; WT 50; MG "SET REST C=", restPtC
restPtD = _TDD; WT 50; MG "SET REST D=", restPtD
```

### Section 5: #SETSTR (lines 202-209)

Same pattern as #SETREST but for startPt* variables.

### Section 6: #GOREST (lines 232-254)

Replace all `restPt[n]` array references:
- `PAC=restPt[2]` → `PAC=restPtC`
- `PAD=restPt[3]` → `PAD=restPtD`
- `PAA= restPt[0]` → `PAA=restPtA`
- `PAB=restPt[1]` → `PAB=restPtB`
- All `MG` debug lines that print `restPt[n]` → print `restPt{X}`

### Section 7: #GOSTR (lines 260-286)

Same pattern as #GOREST but for startPt* variables.

### Section 8: #MOREGRI / #LESSGRI (lines 292-304)

- `startPt[3]` → `startPtD` (D axis is the grind angle adjusted by stone compensation)
- Add `hmiMore = 1` / `hmiLess = 1` reset at start of each block

---

## Python Migration Surface — Complete Inventory

### Files requiring changes

| File | Current pattern | Required change |
|------|----------------|-----------------|
| `screens/rest.py` | `upload_array("RestPnt", 0, 2)` and `download_array("RestPnt", 0, vals)` | Switch to individual MG read / semicolon-write using `RESTPT_BY_AXIS` |
| `screens/start.py` | `upload_array("StartPnt", 0, 3)` and `download_array("StartPnt", 0, vals)` | Switch to individual MG read / semicolon-write using `STARTPT_BY_AXIS` |
| `screens/axisDSetup.py` | `upload_array("RestPnt", 0, 2)` and `download_array("RestPnt", 0, vals)` | Switch to individual MG read / semicolon-write using `RESTPT_BY_AXIS` |
| `screens/parameters_setup.py` | `upload_array("RestPnt", 0, 2)` and `download_array("RestPnt", 0, vals)` | Switch to individual MG read / semicolon-write using `RESTPT_BY_AXIS` |
| `app_state.py` | No dmc_state field | Add `dmc_state: int = 0` field to MachineState |
| `hmi/__init__.py` | Does not exist | Create minimal package init |
| `hmi/dmc_vars.py` | Does not exist | Create constants module |

### Files already using correct pattern (no migration needed)
- `screens/axes_setup.py` — already uses `restPtA`, `startPtA` individual var pattern. Only needs to import from `dmc_vars.py` for future type-safety (deferred to later phases when actively used).

### Files with comment/docstring references only (no runtime impact)
- `screens/serration_knife.py` — references `startPt[]`/`restPt[]` in docstrings and DMC pseudocode comments. No functional calls to update in Phase 9.
- `screens/setup.py` — single docstring mention of `StartPnt`, `RestPnt` as examples.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `DM startPt[4]` indexed array | `startPtA`, `startPtB`, `startPtC`, `startPtD` scalar vars | Named access, no index arithmetic, gclib reads as plain `MG varname` |
| `upload_array("RestPnt", 0, 2)` | `ctrl.cmd(f"MG {RESTPT_BY_AXIS[axis]}")` per axis | Eliminates GArrayUpload dependency; same pattern as axes_setup.py already uses |
| Physical buttons only | `IF (@IN[N] = 0) \| (hmiVar = 0)` | Both hardware and software can trigger any machine action |
| No state observable | `hmiState` polled at 10 Hz (Phase 10) | Controller is authoritative, Python is derived |

---

## Open Questions

1. **hmiState=4 return value after #HOME JSed from #AUTO**
   - What we know: #AUTO calls `JS #HOME` at startup, then continues to `JP #MAIN`. After #HOME, the machine is in IDLE.
   - What's unclear: Should hmiState be set inside #HOME (to 4 at entry, to 1 at exit) or in the callers?
   - Recommendation: Set `hmiState = 4` at START of #HOME and `hmiState = 1` at END of #HOME. When called from within #SULOOP, the SULOOP immediately resumes and sets `hmiState = 3` on next iteration — this brief 1 is acceptable.

2. **startPt/restPt case sensitivity on specific firmware**
   - What we know: STATE.md flags this as a hardware validation item.
   - What's unclear: Galil DMC is case-insensitive for variable names at the controller level; Python must match declared case exactly for gclib queries.
   - Recommendation: Declare as `startPtA` (lowercase s) in DMC. Python constants use same casing. Verify on hardware after upload.

3. **globalDMC module-level handle in controller.py**
   - What we know: Lines 21-28 of controller.py create `globalDMC = gclib.py()` at import time. `GalilController.connect()` creates a separate `gclib.py()` handle.
   - What's unclear: Whether `gclib.py()` instantiation opens a connection or just creates an object. If it opens a connection, it leaks.
   - Recommendation: Treat as harmless (gclib.py() is likely just object instantiation, not GOpen). If clean-exit test fails, add `globalDMC = None` or close it in on_stop(). This is a Phase 9 concern only for success criterion 5 (clean close test).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (from pyproject.toml dev deps) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` testpaths=["tests"] |
| Quick run command | `pytest tests/test_dmc_vars.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DMC-01 | All 8 HMI trigger variable names are valid DMC names (≤8 chars, correct spelling) | unit | `pytest tests/test_dmc_vars.py::test_hmi_trigger_names -x` | ❌ Wave 0 |
| DMC-02 | #WtAtRt OR conditions present for all 5 button blocks | manual | DMC file review after edit | N/A |
| DMC-03 | hmiVar reset is first line inside each triggered block | manual | DMC file review after edit | N/A |
| DMC-04 | hmiState is nonzero at each state boundary | manual | Verify via gclib query after XQ #AUTO | N/A |
| DMC-05 | #SULOOP OR conditions present for all 4 button blocks | manual | DMC file review after edit | N/A |
| DMC-06 | No raw "StartPnt"/"RestPnt" strings in Python screen files | unit | `pytest tests/test_dmc_vars.py::test_no_stale_array_names -x` | ❌ Wave 0 |
| DMC-06 | dmc_vars.py exports correct constant values (exact DMC names) | unit | `pytest tests/test_dmc_vars.py::test_constants_values -x` | ❌ Wave 0 |
| DMC-06 | MachineState has dmc_state field defaulting to 0 | unit | `pytest tests/test_dmc_vars.py::test_app_state_dmc_state -x` | ❌ Wave 0 |
| SC-5 | Controller.disconnect() leaves no dangling handle (gclib close completes) | unit | `pytest tests/test_dmc_vars.py::test_disconnect_closes_handle -x` | ❌ Wave 0 |

**Manual-only justification for DMC-02, DMC-03, DMC-04, DMC-05:** These require either a real Galil controller or a DMC emulator. Neither is available in the test environment. Verification is done by human review of the modified DMC file and by running the success criteria procedure on hardware after upload.

### Sampling Rate
- **Per task commit:** `pytest tests/test_dmc_vars.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dmc_vars.py` — covers DMC-01 (name validation), DMC-06 (no stale strings, constant values, app_state field), SC-5 (disconnect mock test)

*(All existing tests pass without new test file; Wave 0 only needs the new test file.)*

---

## Sources

### Primary (HIGH confidence)
- Direct inspection of `4 Axis Stainless grind.dmc` (all line numbers cited)
- Direct inspection of `src/dmccodegui/screens/axes_setup.py` (reference pattern for individual variable write)
- Direct inspection of `src/dmccodegui/app_state.py` (dataclass structure)
- Direct inspection of `src/dmccodegui/controller.py` (cmd/upload_array/download_array APIs)
- Direct inspection of `src/dmccodegui/main.py` (on_stop lifecycle)
- Direct inspection of all 4 stale-name screen files

### Secondary (MEDIUM confidence)
- Galil DMC language guide (from training knowledge): `|` pipe is OR operator, 8-char variable name limit, DM for arrays, scalar assignment without DM

### Tertiary (LOW confidence)
- `gclib.py()` instantiation behavior (no hardware available to confirm whether it opens a connection or is just object creation)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, all from existing codebase
- Architecture: HIGH — complete DMC file inspected, all callsites identified
- Pitfalls: HIGH (DMC limits, array migration) / MEDIUM (gclib handle behavior)
- DMC syntax: MEDIUM — OR condition syntax from training; needs hardware confirmation

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (DMC file does not change between now and planning; Python codebase is stable)
