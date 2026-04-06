# Phase 15: Run Page Missing Controls - Research

**Researched:** 2026-04-06
**Domain:** Kivy layout restructure — Run page right column, Stone Compensation card, startPtC persistent readback
**Confidence:** HIGH — all findings are based on direct inspection of the existing codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Button layout restructure**
- Bottom action bar: START GRIND + STOP only (remove More Stone, Less Stone)
- More Stone / Less Stone move to a new "STONE COMPENSATION" card in the right column, below the Axis Positions card
- Buttons stacked vertically inside the card (More Stone on top, Less Stone below)
- Card has border/background matching Cycle Status and Axis Positions panels, with "STONE COMPENSATION" header label

**More/Less Stone styling**
- More Stone: green color scheme (green for "more")
- Less Stone: orange color scheme (orange for "less")
- Must maintain 44dp+ touch targets
- Disabled during motion_active (same gate as before)
- Available to all roles (Operator, Setup, Admin) — unchanged from Phase 12

**startPtC readback**
- Persistent label inside the Stone Compensation card showing current startPtC value (e.g., "startPtC: 12,345")
- Read startPtC from controller on screen enter (on_pre_enter) so value is visible immediately
- Update label after each More/Less press (replaces the toast-style _alert readback)
- Remove the before/after toast — persistent label is sufficient

**Requirements re-mapping**
- RUN-02 (Go To Rest): re-map to Phase 13 — implemented on AxesSetupScreen
- RUN-03 (Go To Start): re-map to Phase 13 — implemented on AxesSetupScreen
- RUN-06 (New Session): re-map to Phase 13 — implemented on AxesSetupScreen with confirmation dialog
- Phase 15 becomes a layout-only phase with no requirement IDs
- Update ROADMAP.md and REQUIREMENTS.md traceability table accordingly

### Claude's Discretion
- Exact button sizing within the right column
- Card spacing relative to Axis Positions card
- Exact green/orange color hex values (should match existing theme patterns)
- Whether to show "startPtC" label or a more operator-friendly label like "Stone Position"

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

Note: Per the CONTEXT.md locked decisions, RUN-02, RUN-03, and RUN-06 are being RE-MAPPED to Phase 13 (already implemented on AxesSetupScreen). Phase 15 becomes a layout-only phase. The requirement IDs listed in the phase header are the ones whose traceability entries must be UPDATED in REQUIREMENTS.md and ROADMAP.md — not implemented here.

| ID | Description | Action in Phase 15 |
|----|-------------|---------------------|
| RUN-02 | User can send machine to rest position by pressing Go To Rest | Update traceability: re-map to Phase 13 (complete) |
| RUN-03 | User can send machine to start position by pressing Go To Start | Update traceability: re-map to Phase 13 (complete) |
| RUN-06 | User can start a new session with two-step confirmation (Setup/Admin role required) | Update traceability: re-map to Phase 13 (complete) |

The actual deliverable is: layout restructure of run.kv and run.py with the Stone Compensation card.
</phase_requirements>

---

## Summary

Phase 15 is a layout-only restructure of the Run page. The core work is:

1. **Remove** More Stone and Less Stone from the bottom action bar, leaving only START GRIND + STOP.
2. **Add** a "STONE COMPENSATION" card to the right column (below Axis Positions) containing vertically stacked More Stone (green) and Less Stone (orange) buttons plus a persistent startPtC readback label.
3. **Add** a `start_pt_c` StringProperty to RunScreen and the logic to read it on screen enter and update it after each More/Less press.
4. **Update** REQUIREMENTS.md and ROADMAP.md to re-map RUN-02, RUN-03, RUN-06 to Phase 13 (complete) and mark Phase 15 as a layout phase with no requirement IDs of its own.

The Python button handlers (`on_more_stone`, `on_less_stone`) are mostly reused as-is; the only change is replacing the before/after `_alert()` toast with an update to a persistent `start_pt_c` label. All existing tests remain valid — new tests cover the persistent property and the on_pre_enter read.

**Primary recommendation:** Keep changes surgical. run.kv layout moves are safe; the only Python changes are a new `start_pt_c` StringProperty, one `_read_start_pt_c()` background method, and label update calls replacing `_alert()` in the More/Less handlers.

---

## Standard Stack

### Core (all already present — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Kivy | ≥2.3 | UI layout, BoxLayout, Label, Button, KV bindings | Project framework |
| Kivy properties | built-in | StringProperty for start_pt_c reactive binding | KV-observable state |
| jobs.submit() | internal | Background thread for controller reads | Serialized gclib handle pattern |
| Clock.schedule_once | built-in | Post results from bg thread to main thread | Safe Kivy threading rule |

### No New Libraries Needed
This phase touches only `ui/run.kv` and `screens/run.py`. No imports added.

---

## Architecture Patterns

### Existing Card Pattern (MUST match exactly)

Both Cycle Status and Axis Positions cards in run.kv use this identical canvas pattern:

```kv
BoxLayout:
    canvas.before:
        Color:
            rgba: theme.bg_panel
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [8,]
        Color:
            rgba: theme.border
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, 8)
            width: 1.2
    orientation: 'vertical'
    padding: ['12dp', '8dp']
    spacing: '2dp'
```

Header label pattern (matches "CYCLE STATUS" and "AXIS POSITIONS" headers):

```kv
Label:
    text: 'STONE COMPENSATION'
    font_size: '11sp'
    bold: True
    color: theme.text_mid
    halign: 'left'
    valign: 'middle'
    text_size: self.size
    size_hint_y: None
    height: '24dp'
```

### Recommended Stone Compensation Card Structure

```kv
# Stone Compensation card — right column, below Axis Positions
BoxLayout:
    id: stone_comp_card
    canvas.before:
        Color:
            rgba: theme.bg_panel
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [8,]
        Color:
            rgba: theme.border
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, 8)
            width: 1.2
    size_hint_y: None
    height: '160dp'        # Claude's discretion: fits header + 2 buttons + label
    orientation: 'vertical'
    padding: ['12dp', '8dp']
    spacing: '6dp'

    # Header
    Label:
        text: 'STONE COMPENSATION'
        font_size: '11sp'
        bold: True
        color: theme.text_mid
        halign: 'left'
        valign: 'middle'
        text_size: self.size
        size_hint_y: None
        height: '24dp'

    # startPtC persistent readback label
    Label:
        id: start_pt_c_label
        text: root.start_pt_c
        font_size: '12sp'
        color: theme.text_mid
        halign: 'left'
        valign: 'middle'
        text_size: self.size
        size_hint_y: None
        height: '20dp'

    # More Stone button (green)
    Button:
        id: more_stone_btn
        text: 'MORE STONE'
        font_size: '14sp'
        bold: True
        size_hint_y: None
        height: '44dp'
        background_normal: ''
        background_color: 0.02, 0.18, 0.08, 1
        color: 0.133, 0.773, 0.369, 1
        disabled: root.motion_active
        on_release: root.on_more_stone()

    # Less Stone button (orange)
    Button:
        id: less_stone_btn
        text: 'LESS STONE'
        font_size: '14sp'
        bold: True
        size_hint_y: None
        height: '44dp'
        background_normal: ''
        background_color: 0.15, 0.08, 0.02, 1
        color: 0.984, 0.573, 0.235, 1
        disabled: root.motion_active
        on_release: root.on_less_stone()
```

### Color Values (Claude's Discretion — matched from existing codebase)

Green (More Stone) — matches existing "up" adjustment button pattern in delta_c_panel:
- background_color: `0.02, 0.12, 0.06, 1` (dark green background)
- color (text): `0.133, 0.773, 0.369, 1` (bright green, same as existing)

Orange (Less Stone) — matches existing "down" adjustment button pattern:
- background_color: `0.15, 0.08, 0.02, 1` (dark orange background)
- color (text): `0.984, 0.573, 0.235, 1` (bright orange, same as existing axis A badge)

These exact values are already used in run.kv's Delta-C panel controls and are the established pattern.

### Python: start_pt_c Property and Read Pattern

New StringProperty on RunScreen (follows existing StringProperty pattern for `session_knife_count`, `stone_knife_count`):

```python
# Add to RunScreen class properties section
start_pt_c = StringProperty("---")
```

New `_read_start_pt_c()` background method (follows Phase 12 read-fire pattern in `on_more_stone`/`on_less_stone`):

```python
def _read_start_pt_c(self) -> None:
    """Background: read startPtC from controller and update persistent label."""
    if not self.controller or not self.controller.is_connected():
        return
    ctrl = self.controller
    def _do():
        try:
            raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
            val = int(float(raw))
            Clock.schedule_once(lambda *_: setattr(self, 'start_pt_c', f"{val:,}"))
        except Exception:
            Clock.schedule_once(lambda *_: setattr(self, 'start_pt_c', '---'))
    jobs.submit(_do)
```

Call site in `on_pre_enter`:

```python
# After existing subscription setup
self._read_start_pt_c()
```

Updated `on_more_stone` / `on_less_stone` — replace `_alert()` toast with persistent label update. Only the readback section changes; the fire sequence stays identical. After the 0.4s sleep and after-read:

```python
# Replace the if/else _alert block with:
try:
    after_raw = ctrl.cmd(f"MG {STARTPT_C}").strip()
    after = int(float(after_raw))
    Clock.schedule_once(
        lambda *_, v=after: setattr(self, 'start_pt_c', f"{v:,}")
    )
except Exception:
    pass  # Label retains last known value
```

The `before` variable read and the before/after toast are removed entirely. The `_alert()` error paths for failed trigger commands stay — those are genuine errors, not normal readback.

### Bottom Action Bar Change

Current bar has 4 buttons: START GRIND, STOP, MORE STONE, LESS STONE.
After: START GRIND + STOP only. Remove the `more_stone_btn` and `less_stone_btn` entries from the bottom action bar KV block.

The STOP button visibility logic (`opacity: 1.0 if root.motion_active else 0.0`) stays unchanged. START GRIND takes full `size_hint_x: 1`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reactive label update | Custom observer/callback | StringProperty + KV binding (`text: root.start_pt_c`) | Kivy's property system handles thread-safe updates via Clock.schedule_once |
| Background read | Direct controller call from main thread | `jobs.submit(_do)` | Serialized gclib handle — never call controller from main thread |
| Color theme compliance | Hard-code arbitrary hex | Copy exact RGB tuples from existing run.kv buttons | Consistency; avoids visual mismatch |

---

## Common Pitfalls

### Pitfall 1: Lambda closure capturing mutable variable
**What goes wrong:** `lambda *_: setattr(self, 'start_pt_c', f"{after:,}")` — `after` is a local that may be garbage collected or shadowed.
**How to avoid:** Use default argument capture: `lambda *_, v=after: setattr(self, 'start_pt_c', f"{v:,}")`. This pattern is already established in Phase 11 (the `_m=msg` default arg fix in recover()).

### Pitfall 2: Removing buttons from bar breaks existing test ids
**What goes wrong:** Tests reference `r.ids.get('more_stone_btn')` or `r.ids.get('less_stone_btn')` if any such test exists; removing from bar and re-adding in the card changes the id scope.
**How to avoid:** The ids `more_stone_btn` and `less_stone_btn` are preserved in the new card location with the same id names — KV ids are screen-scoped, not bar-scoped. No test currently asserts button position in the bar, so this is safe.

### Pitfall 3: Card height too small for touch targets
**What goes wrong:** If `stone_comp_card` height is under-specified, Kivy clips buttons or compresses them below 44dp.
**How to avoid:** Use `size_hint_y: None` with explicit `height` on the card (e.g., 160dp) and explicit `height: '44dp'` on each button. Right column uses `size_hint_y: 1` for the Axis Positions card — the Stone Compensation card must be `size_hint_y: None` with fixed height so it doesn't compete.

### Pitfall 4: Disconnected state — `_read_start_pt_c` silently no-ops
**What goes wrong:** If the controller is disconnected on screen enter, `_read_start_pt_c` returns early and the label stays "---". This is correct behavior, but the handler must guard on `is_connected()` before submitting the job.
**How to avoid:** Guard is already in the pattern above. The label default "---" is the right disconnected indicator, consistent with pos_a..pos_d.

### Pitfall 5: startPtC constant already imported — don't add duplicate
**What goes wrong:** Adding a new `from ..hmi.dmc_vars import STARTPT_C` line when it is already in the existing imports at the top of run.py.
**How to avoid:** Verify before modifying imports. `STARTPT_C` is already imported in run.py line 28.

---

## Code Examples

### Existing right column structure (run.kv lines 319-797)
The right column is a `BoxLayout` with `size_hint_x: 0.4` and `orientation: 'vertical'`. It currently contains two children: the Cycle Status card and the Axis Positions card. The Stone Compensation card is appended as a third child inside this same BoxLayout.

### Existing StringProperty pattern in RunScreen
```python
# Source: src/dmccodegui/screens/run.py lines 277-278
session_knife_count = StringProperty("0")
stone_knife_count = StringProperty("0")
```
`start_pt_c = StringProperty("---")` follows this exact pattern.

### Existing before/after read-fire pattern (to be simplified)
```python
# Source: src/dmccodegui/screens/run.py lines 574-605 (on_more_stone)
# Current: reads before, fires trigger, sleeps 0.4s, reads after, calls _alert()
# Phase 15 change: keep fire + sleep + after-read; remove before-read; replace _alert with setattr
```

### Document update: REQUIREMENTS.md traceability rows to change
```
| RUN-02 | Phase 15 | Pending |   →   | RUN-02 | Phase 13 | Complete |
| RUN-03 | Phase 15 | Pending |   →   | RUN-03 | Phase 13 | Complete |
| RUN-06 | Phase 15 | Pending |   →   | RUN-06 | Phase 13 | Complete |
```
And in REQUIREMENTS.md body, uncheck → check the `[ ]` for RUN-02, RUN-03, RUN-06.

### ROADMAP.md phase 15 description update
Change: "Add Go To Rest, Go To Start, and New Session buttons to RunScreen (gap closure)"
To: "Restructure Run page layout: Stone Compensation card with More/Less Stone and persistent startPtC readback; remove buttons from action bar (layout gap closure)"

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| More/Less Stone in action bar with toast readback | More/Less Stone in dedicated card with persistent label | Operator always sees current stone position; action bar is cleaner |
| RUN-02/03/06 flagged as missing in RunScreen | RUN-02/03/06 satisfied by Phase 13 AxesSetupScreen | Requirements traceability corrected |

---

## Open Questions

1. **Card height budget in the right column**
   - What we know: Cycle Status card is `240dp` (non-serration) or `340dp` (serration). Axis Positions card is `size_hint_y: 1` (fills remaining space).
   - What's unclear: If Axis Positions takes remaining space and Stone Compensation is fixed-height, the right column on shorter screens may compress the axis positions display.
   - Recommendation: Set Stone Compensation card `size_hint_y: None`, `height: '160dp'`. Axis Positions keeps `size_hint_y: 1`. On small screens this auto-compresses Axis Positions — acceptable since the fixed panels' scroll is not in scope.

2. **startPtC label text format**
   - What we know: CONTEXT.md says "startPtC: 12,345" as example. Claude's discretion includes "Stone Position" alternative.
   - Recommendation: Use operator-friendly "Stone Pos: 12,345" — shorter, still unambiguous, avoids surfacing the DMC variable name to operators.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (detected: tests/ directory, test_*.py files) |
| Config file | none — invoked directly |
| Quick run command | `pytest tests/test_run_screen.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase 15 Requirements → Test Map

Phase 15 has no requirement IDs of its own (all re-mapped to Phase 13). Tests cover the layout changes and new Python properties.

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| RunScreen has `start_pt_c` StringProperty with default "---" | unit | `pytest tests/test_run_screen.py::test_run_screen_has_start_pt_c -x` | Wave 0 |
| `_read_start_pt_c()` submits a background job when connected | unit | `pytest tests/test_run_screen.py::test_read_start_pt_c_submits_job -x` | Wave 0 |
| `on_more_stone()` updates `start_pt_c` (not `_alert`) after fire | unit | `pytest tests/test_run_screen.py::test_more_stone_updates_start_pt_c -x` | Wave 0 |
| `on_less_stone()` updates `start_pt_c` after fire | unit | `pytest tests/test_run_screen.py::test_less_stone_updates_start_pt_c -x` | Wave 0 |
| Existing more/less stone trigger tests still pass (no regression) | unit | `pytest tests/test_run_screen.py -x -q` | ✅ exists |

### Sampling Rate
- **Per task commit:** `pytest tests/test_run_screen.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_run_screen.py::test_run_screen_has_start_pt_c` — covers new StringProperty
- [ ] `tests/test_run_screen.py::test_read_start_pt_c_submits_job` — covers on_pre_enter read
- [ ] `tests/test_run_screen.py::test_more_stone_updates_start_pt_c` — covers label update path
- [ ] `tests/test_run_screen.py::test_less_stone_updates_start_pt_c` — covers label update path

All four are new test functions added to the existing `tests/test_run_screen.py` file. No new test files needed.

---

## Sources

### Primary (HIGH confidence)
- Direct inspection: `src/dmccodegui/ui/run.kv` — full layout structure, existing button ids, card canvas patterns
- Direct inspection: `src/dmccodegui/screens/run.py` — existing handlers, properties, import list
- Direct inspection: `src/dmccodegui/hmi/dmc_vars.py` — STARTPT_C already imported, constant verified
- Direct inspection: `src/dmccodegui/theme_manager.py` — exact color values for bg_panel, border, text_mid
- Direct inspection: `.planning/phases/15-run-page-missing-controls/15-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- Direct inspection: `tests/test_run_screen.py` — existing tests verified not to rely on button position; no test for `more_stone_btn` id location
- Direct inspection: `src/dmccodegui/screens/axes_setup.py` — confirms go_to_rest_all/go_to_start_all already implemented in Phase 13

---

## Metadata

**Confidence breakdown:**
- Layout pattern: HIGH — copied from verified existing run.kv canvas blocks
- Color values: HIGH — extracted from existing run.kv delta_c_panel buttons
- Python changes: HIGH — follows established Phase 10-12 patterns for StringProperty + background read + Clock.schedule_once
- Traceability updates: HIGH — requirements and roadmap file contents inspected directly

**Research date:** 2026-04-06
**Valid until:** Stable (no external dependencies; all findings from local codebase)
