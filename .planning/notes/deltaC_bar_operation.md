# DeltaC Compensation Bar — Complete Operating Documentation

## Overview

The deltaC compensation bar is a run-time tool for operators to fine-tune knife
thickness after grinding. It divides the knife length into user-selectable
sections (bars) and lets the operator add or remove grinding depth per section.

**Key principle:** The bar adjustments are ADDITIVE — they modify whatever
deltaC values are already on the controller (from a profile import, previous
session BV, or manual GalilTools entry). They never replace the baseline.

---

## Physical Context

### Stone Geometry
- Stone outer diameter: 347mm
- Stone inner diameter: 267mm
- Grind surface per side: (347 - 267) / 2 = **40mm** (left side used)
- Start point: 3mm past the heel of the knife

### DeltaC Array
- 100 elements: `deltaC[0]` through `deltaC[99]`
- Each index represents approximately **1.2–1.5mm** along the knife (STEP_MM ~ 1.3)
- Index 0 = heel end, Index 99 = tip end
- Total knife coverage: ~100 x 1.3mm = ~130mm

### What deltaC Values Mean
- deltaC values are **incremental C-axis movements** used in Galil's LI
  (Linear Interpolation) vector mode
- The **cumulative sum** of deltaC = actual C-axis position profile along the knife
- **Positive deltaC** = C moves down = **more grinding** (stone presses deeper)
- **Negative deltaC** = C moves up = **less grinding** (stone lifts away)
- The DMC program feeds these via `LI deltaA[n],deltaB[n],deltaC[n],deltaD[n]`
  in the `#GRIND` section's vector motion loop

---

## Data Flow

### On Page Load (`on_pre_enter` → `_do_page_load_read`)

```
Controller deltaC array (from profile/previous BV)
        │
        ▼
  upload_array_auto("deltaC")
        │
        ▼
  stored as self._controller_delta_c  (BASELINE — never modified by bars)
  stored as self._last_delta_c        (tracks what's currently on controller)
```

The baseline is the "ground truth" — whatever the operator or profile system
put into the controller before the bars were used.

### When Operator Adjusts Bars

```
  User clicks THEM (+50) or BOT (-50) on a selected bar
        │
        ▼
  self.delta_c_offsets[bar_index] += DELTA_C_STEP  (accumulates per bar)
        │
        ▼
  UI bar chart updates to show current offset per bar
  (NO controller write yet — just visual)
```

### When Operator Clicks "Save to Controller"

```
  self.delta_c_offsets  (bar adjustments, e.g., [0, 0, 0, 50, 100])
        │
        ▼
  _offsets_to_delta_c()  (converts bar offsets → 100-element adjustment array)
        │                 (depends on comp_mode: "cumulative" or "spline")
        ▼
  adjustments[100]  (incremental deltaC adjustments from bars)
        │
        ▼
  final[i] = _controller_delta_c[i] + adjustments[i]   ← ADDITIVE
        │
        ▼
  diff against _last_delta_c → only changed indices sent
        │
        ▼
  chunked commands: deltaC[40]=103;deltaC[41]=105;...  (max 80 chars/cmd)
        │
        ▼
  _last_delta_c updated to match what's now on controller
```

### On Shutdown (TAT MAY button)

```
  hmiSetp=0  → enter setup mode
  hmiHome=0  → home all axes
  poll hmiState until back to SETUP (homing complete)
  BV          → save ALL variables and arrays to NV memory
```

Next day when machine powers on, deltaC array is restored from NV.
The bars start at zero again — the adjusted values are now part of the
baseline that gets read on page load.

---

## Compensation Modes

The `comp_mode` property (toggled by the mode button in the bar header)
determines how bar offsets are converted into the 100-element adjustment array.

### Mode 1: Cumulative (Default)

**Button color:** Cyan
**Label:** CUMULATIVE

**Behavior:** Each bar's offset CARRIES FORWARD for all subsequent indices.
The offset represents a CHANGE in grind depth from that point onward.

**Algorithm (`_offsets_to_delta_c_cumulative`):**

1. Build a desired **position profile** (cumulative depth):
   - Start at 0 (no adjustment)
   - At each bar boundary, the cumulative depth changes by that bar's offset
   - Within each bar's index range, the transition is a smooth linear ramp
     (not a step) to avoid sudden changes

2. Convert position profile to incremental deltaC:
   - `deltaC[0] = position[0]`
   - `deltaC[i] = position[i] - position[i-1]`

**Example (5 bars, bar 4 = +50, bar 5 = +100):**

```
Bar offsets:      [0,    0,    0,    +50,  +100]
Cumulative depth: [0,    0,    0,    50,   150]

Position profile (100 indices):
  indices  0-19:  0 ──────────────── (flat, no adjustment)
  indices 20-39:  0 ──────────────── (flat)
  indices 40-59:  0 ──────────────── (flat)
  indices 60-79:  0 → ramp to 50 ── (smooth transition over 20 indices)
  indices 80-99:  50 → ramp to 150 ─ (smooth transition over 20 indices)

Incremental deltaC (what gets added to baseline):
  indices  0-59:  0 each
  indices 60-79:  ~2.6 each (50/19 ≈ 2.6, ramping up)
  indices 80-99:  ~5.0 each (100/20 = 5.0, ramping up further)
```

**Use case:** "From this point toward the tip, grind 50 counts deeper."
To return to baseline later, add -50 in a subsequent bar.
Operator has full control — nothing auto-returns.

### Mode 2: Spline

**Button color:** Purple
**Label:** SPLINE

**Behavior:** User sets offset values at bar centers. A smooth cubic spline
(natural boundary conditions) interpolates between all control points.
The result is the smoothest possible profile — no corners, no steps.

**Algorithm (`_offsets_to_delta_c_spline`):**

1. Place control points at bar centers with cumulative offsets as Y values
2. Pin start (index 0) and end (index 99) as additional control points
3. Fit a `scipy.interpolate.CubicSpline` through all points
4. Evaluate the spline at every index → position profile
5. Convert to incremental deltaC (same as cumulative mode)

**Example (5 bars, bar 3 = +50):**

```
Control points:   (0, 0), (10, 0), (30, 0), (50, 50), (70, 50), (90, 50), (99, 50)
Spline: smooth S-curve rising from 0 to 50 around index 40-60
deltaC: derivative of the curve (gradual positive increments)
```

**Use case:** Natural, smooth thickness adjustments. Best for gradual
profiles where you want no visible grind marks or transition lines.

**Dependency:** Requires `scipy` and `numpy` (imported on demand).

---

## UI Layout

### Bar Header Row
```
┌─────────────────────────────────────────────────────────────┐
│ CHINH DO MAI TREN DAO    [CUMULATIVE]    CHIA PHAN: [-][3][+] │
└─────────────────────────────────────────────────────────────┘
```
- Title: "CHINH DO MAI TREN DAO" (Knife Grind Adjustment)
- Mode toggle button: shows current mode, click to switch
- Section count: number of bars (adjustable with +/- buttons)

### Bar Chart + Controls
```
┌─────────────────────────────────────────────────────────────┐
│  ▲  BOT 50        ← less grinding (subtract DELTA_C_STEP)  │
│ ┌──┐┌──┐┌██┐┌──┐┌──┐   ← bar chart (selected bar highlighted) │
│  ▼  THEM 50       ← more grinding (add DELTA_C_STEP)       │
│ DA CHON: 50 cts   [XOA]   [LUU VAO MAY]                    │
└─────────────────────────────────────────────────────────────┘
```
- **BOT (top, orange):** subtract DELTA_C_STEP from selected bar — matches
  BOT DA (less stone) position in the stone compensation box
- **THEM (bottom, green):** add DELTA_C_STEP to selected bar — matches
  THEM DA (more stone) position in the stone compensation box
- **Positive C = more grinding** — THEM makes the knife thinner at that section
- **DA CHON:** shows current offset value of selected bar
- **XOA:** clear all bar offsets to zero (baseline preserved on controller)
- **LUU VAO MAY:** save adjustments to controller (additive on baseline)

### Button Layout (Bottom Bar)
```
┌────────────────────┬────────────────────┐
│   BAT DAU MAI      │     TAT MAY        │
│  (Start Grind)     │   (Shutdown)       │
│  green, disabled   │  amber, disabled   │
│  during motion     │  during motion     │
└────────────────────┴────────────────────┘
```

---

## Constants

| Constant | Value | Location | Meaning |
|----------|-------|----------|---------|
| DELTA_C_WRITABLE_START | 0 | flat_grind/widgets.py | First writable index |
| DELTA_C_WRITABLE_END | 99 | flat_grind/widgets.py | Last writable index |
| DELTA_C_ARRAY_SIZE | 100 | flat_grind/widgets.py | Total elements |
| DELTA_C_STEP | 50 | flat_grind/widgets.py | Counts per button click |
| STEP_MM | 1.3 | flat_grind/widgets.py | Approx mm per index |
| STONE_SURFACE_MM | 40.0 | flat_grind/widgets.py | Stone grind width |
| STONE_OVERHANG_MM | 3.0 | flat_grind/widgets.py | Stone past heel |

---

## Command Protocol

### Writing to Controller
- Commands are chunked to max **80 characters** per line
- Values are **rounded to nearest integer** (`round(v):.0f`)
- Only **changed indices** are sent (diff against `_last_delta_c`)
- Commands run on the background jobs thread (no UI blocking)
- Example: `deltaC[60]=103;deltaC[61]=105;deltaC[62]=108`

### Reading from Controller
- On page load: `upload_array_auto("deltaC")` reads all 100 elements
- Stored as `_controller_delta_c` (baseline, never modified by UI)
- If read fails, baseline defaults to all zeros

---

## Lifecycle Summary

```
┌─────────────────────────────────────────────────────────────┐
│ PROFILE IMPORT (CSV or previous BV)                         │
│   deltaC[0..99] loaded into controller NV memory            │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│ PAGE LOAD (on_pre_enter)                                     │
│   Read deltaC from controller → _controller_delta_c          │
│   Bars start at zero (no adjustments yet)                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│ FIRST GRIND                                                  │
│   Uses original deltaC profile as-is                         │
│   Operator inspects knife thickness after grind              │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│ OPERATOR ADJUSTS BARS                                        │
│   Clicks THEM/BOT on specific bars                           │
│   Bar offsets accumulate in UI (delta_c_offsets)              │
│   Clicks "LUU VAO MAY" (Save to Controller)                  │
│   Final = baseline + adjustment → sent to controller         │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│ SUBSEQUENT GRINDS                                            │
│   Controller uses adjusted deltaC values                     │
│   Operator can adjust again (bars still show current offsets) │
│   Each save is additive on the ORIGINAL baseline             │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│ SHUTDOWN (TAT MAY)                                           │
│   hmiSetp=0 → enter setup                                    │
│   hmiHome=0 → home all axes                                  │
│   Wait for homing complete (poll hmiState)                    │
│   BV → save adjusted deltaC + all vars to NV                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│ NEXT DAY POWER ON                                            │
│   deltaC restored from NV (includes yesterday's adjustments) │
│   Page load reads it as new baseline                         │
│   Bars start at zero — operator can fine-tune again           │
└─────────────────────────────────────────────────────────────┘
```

---

## Files Involved

| File | What it contains |
|------|------------------|
| `screens/flat_grind/run.py` | on_apply_delta_c, _offsets_to_delta_c_cumulative, _offsets_to_delta_c_spline, _do_page_load_read, on_shutdown |
| `screens/convex/run.py` | Same methods (convex variant) |
| `screens/flat_grind/widgets.py` | Constants (DELTA_C_ARRAY_SIZE, DELTA_C_STEP, etc.), DeltaCBarChart widget |
| `ui/flat_grind/run.kv` | Bar chart layout, THEM/BOT buttons, mode toggle, Save/Clear buttons |
| `ui/convex/run.kv` | Same layout (convex variant) |
| `hmi/dmc_vars.py` | HMI trigger constants (HMI_SETP, HMI_HOME, etc.) |
| `4 Axis Stainless grind.dmc` | DMC program that consumes deltaC in #GRIND vector loop |
