# DeltaC Compensation Modes — Design Notes

## Problem
The original ramp approach (triangular: ramp up then ramp down within each bar) works
against the grind because it lifts the stone back up at the end of the bar, leaving
the spine unground. The net-zero triangle was wrong — when you want to grind deeper in
a section, you want it to STAY deeper until you explicitly bring it back.

## Stone Geometry Reference
- Stone: 347mm OD / 267mm ID = 40mm grind surface per side (left side used)
- Start point: 3mm past heel
- Each deltaC index ≈ 1.2–1.5mm (STEP_MM ≈ 1.3)
- deltaC values are incremental C-axis movements in LI vector mode
- Cumulative sum of deltaC = actual C-axis position profile along the knife
- 100 indices total, bars divide these evenly (5 bars = 20 indices each)

## Two Modes to Implement (both available, user selects which to use)

### Mode 1: Cumulative Offset
Each bar's offset CARRIES FORWARD for all subsequent indices. The user sets the
CHANGE at each bar — positive = grind deeper from this point, negative = grind less.

Example (5 bars, bar 3 = +50):
```
Bar 1: +0   → indices  0-19: cumulative offset = 0
Bar 2: +0   → indices 20-39: cumulative offset = 0
Bar 3: +50  → indices 40-59: cumulative offset = 50 (grind 50cts deeper)
Bar 4: +0   → indices 60-79: cumulative offset = 50 (stays deeper)
Bar 5: -50  → indices 80-99: cumulative offset = 0  (back to baseline)
```

deltaC array: each index within a bar gets `offset[bar] / chunk` as increment.
At bar boundaries the step is distributed across the bar width.

To return to baseline, user must explicitly add opposite offset in a later bar.

**Pros:** Intuitive for "from here onward, grind deeper". Good for fixing taper.
**Cons:** User must manually balance. Forgetting to cancel = tapered knife.

### Mode 2: Smooth Spline
User sets offset values at bar centers. A smooth curve (cubic spline) interpolates
between control points. The deltaC values are computed as the derivative of the
spline (since deltaC = incremental, and the spline represents the desired position).

Example (5 bars):
```
Bar centers at indices: 10, 30, 50, 70, 90
User offsets:           0,  0, +50, 0,  0
Spline: smooth bell curve peaking at index 50
deltaC: derivative of the spline (positive on approach, negative on departure)
```

**Pros:** Smoothest result. Natural curves. No steps.
**Cons:** More complex math. Harder to predict exact effect.

## Implementation Plan
- Add a toggle/selector on the run screen segment bar UI (e.g., dropdown: "Cumulative" / "Spline")
- Both modes use the same bar UI (select bar, +/- offset buttons)
- `_offsets_to_delta_c()` checks the mode and dispatches to the right algorithm
- Keep both algorithms in the same file for easy A/B comparison
- Default to Cumulative (simpler, more predictable)

## Testing
- Test each mode by writing to controller, reading back, visual inspection in GalilTools
- Compare grinding results side-by-side with same knife profile
- Document which mode works better for flat grind vs convex
