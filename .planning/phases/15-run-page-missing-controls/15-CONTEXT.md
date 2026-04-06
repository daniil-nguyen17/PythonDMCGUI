# Phase 15: Run Page Missing Controls - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Reorganize the Run page layout: move More/Less Stone buttons from the bottom action bar into their own card in the right column below Axis Positions. Bottom action bar shrinks to START GRIND + STOP only. Go To Rest, Go To Start, and New Session are NOT added to the Run page — they are satisfied by their existing implementation on AxesSetupScreen (Phase 13).

</domain>

<decisions>
## Implementation Decisions

### Button layout restructure
- Bottom action bar: START GRIND + STOP only (remove More Stone, Less Stone)
- More Stone / Less Stone move to a new "STONE COMPENSATION" card in the right column, below the Axis Positions card
- Buttons stacked vertically inside the card (More Stone on top, Less Stone below)
- Card has border/background matching Cycle Status and Axis Positions panels, with "STONE COMPENSATION" header label

### More/Less Stone styling
- More Stone: green color scheme (green for "more")
- Less Stone: orange color scheme (orange for "less")
- Must maintain 44dp+ touch targets
- Disabled during motion_active (same gate as before)
- Available to all roles (Operator, Setup, Admin) — unchanged from Phase 12

### startPtC readback
- Persistent label inside the Stone Compensation card showing current startPtC value (e.g., "startPtC: 12,345")
- Read startPtC from controller on screen enter (on_pre_enter) so value is visible immediately
- Update label after each More/Less press (replaces the toast-style _alert readback)
- Remove the before/after toast — persistent label is sufficient

### Requirements re-mapping
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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `dmc_vars.py`: HMI_MORE, HMI_LESS, HMI_TRIGGER_FIRE, STARTPT_C constants already imported in run.py
- `jobs.submit()`: existing background thread pattern for More/Less Stone fire + readback
- `MachineState.motion_active`: existing gate for disabling buttons during motion
- `_alert()` method: currently used for readback, will be replaced by persistent label

### Established Patterns
- Right column cards: Cycle Status and Axis Positions both use bg_panel + border + RoundedRectangle with radius [8,] and Line width 1.2
- Header labels: 11sp, bold, theme.text_mid color, halign left
- motion_active binding: `disabled: root.motion_active` in KV

### Integration Points
- `ui/run.kv`: Remove More/Less Stone from bottom action bar, add Stone Compensation card to right column
- `screens/run.py`: Add startPtC StringProperty, read startPtC in on_pre_enter, update label after More/Less press
- `ROADMAP.md` + `REQUIREMENTS.md`: Re-map RUN-02, RUN-03, RUN-06 to Phase 13

</code_context>

<specifics>
## Specific Ideas

- Vertical stack for More/Less buttons inside the card — gives each button full card width for easy touch targeting
- Green for "more" (adding stone), orange for "less" (removing stone) — intuitive color mapping
- Persistent startPtC label means operator always sees current stone position without needing to press anything

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-run-page-missing-controls*
*Context gathered: 2026-04-06*
