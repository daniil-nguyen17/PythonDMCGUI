# Phase 14: State-Driven UI - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Every interactive element reflects real controller state — buttons enable and disable correctly on controller-reported state, status labels name the current machine state, setup mode is visible across all screens, the Run tab blocks correctly during setup, and connection status is always visible. No new controller commands or HMI triggers — purely UI-side wiring of existing MachineState data.

</domain>

<decisions>
## Implementation Decisions

### State status display
- State label lives in StatusBar — visible on ALL screens at all times
- Colored text label (not a badge/chip) matching StatusBar density
- State colors: IDLE=orange, GRINDING=green, SETUP=red, HOMING=orange, OFFLINE=red/gray, E-STOP=red
- Shows state name only — no elapsed time, no context, no animations
- dmc_state=0 maps to either OFFLINE (program_running=True, uninitialized) or E-STOP (program_running=False, program was killed)
- E-STOP vs OFFLINE distinction uses MachineState.program_running flag — controller-authoritative

### Setup mode badge
- Yellow bar with "SETUP MODE" text centered, ~24dp tall
- Positioned between StatusBar and screen content area — visible on ALL screens
- Only visible when dmc_state == STATE_SETUP (3)
- Disappears on disconnect (clear everything, no stale state)

### Tab gating
- Run tab: disabled and grayed during SETUP state
- Axes Setup + Parameters tabs: disabled and grayed during GRINDING or HOMING states
- Profiles and Users tabs: always accessible regardless of state
- HOMING uses same gating rules as GRINDING (both are "motion active" states)
- When disconnected: ALL tabs accessible (motion buttons within screens are individually disabled via motion_active=True)
- When state returns to IDLE: all tab gates release

### Cross-screen button gating
- Profile import/apply buttons: disabled when motion_active (GRINDING/HOMING/disconnected)
- Parameters "Apply to Controller": disabled when motion_active
- Parameters "Read from Controller": always accessible (read-only operation)
- Run page buttons: already gated via motion_active from Phase 11 — no changes needed
- Axes Setup jog/teach: already gated on dmc_state==SETUP from Phase 13 — no changes needed

### Disconnect behavior
- On disconnect: clear setup badge, release all tab gates, state label shows OFFLINE
- All tabs accessible when disconnected
- All motion buttons disabled within each screen (existing motion_active=True when disconnected)
- On reconnect: state rebuilds from first poll tick — no special logic needed

### State transitions
- Instant updates only — no animations, no flashes, no color transitions
- Consistent with PROJECT.md constraint: "Animated screen transitions adds latency on industrial tool"

### Claude's Discretion
- Exact StatusBar layout adjustment to fit state label (may need to resize other elements)
- Setup badge implementation approach (separate widget vs canvas instruction)
- Tab gating mechanism (Kivy disabled property binding or ScreenManager override)
- How to propagate MachineState to tab bar for gating (subscription pattern or property binding)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `StatusBar` (status_bar.py): already has connection indicator, user/role, banner, E-STOP, RECOVER — needs state label added
- `MachineState` (app_state.py): has dmc_state, connected, program_running, subscribe() pattern — all data needed for UI gating already exists
- `motion_active` BooleanProperty on RunScreen: gates Run page buttons — pattern to replicate for other screens
- Profile import disabled text: `'Import (Cycle Running)'` already in profiles.kv — just needs real MachineState wiring
- `_apply_state()` pattern on RunScreen: subscribes to MachineState, updates Kivy properties — replicate for other screens

### Established Patterns
- MachineState.subscribe() with Clock.schedule_once for thread-safe UI updates
- Kivy `disabled` property binding for button gating
- StatusBar.update_from_state() called on every poll tick with change detection
- _prev_* caching in StatusBar to skip redundant UI updates

### Integration Points
- `ui/status_bar.kv`: add state label widget between banner ticker and theme toggle
- `screens/status_bar.py`: add state_text/state_color StringProperty/ListProperty, update in update_from_state()
- `main.py`: add setup badge widget to root layout, subscribe to MachineState for badge visibility
- `main.py` or tab bar widget: add tab gating logic based on dmc_state
- `screens/profiles.py`: subscribe to MachineState for import/apply button gating
- `screens/parameters.py`: add motion_active gating to Apply to Controller button

</code_context>

<specifics>
## Specific Ideas

- E-STOP state is distinct from OFFLINE — operator should know the machine was emergency-stopped vs just not initialized
- Setup badge between StatusBar and content is like a "mode indicator" — hard to miss, clearly communicates machine state
- Tab gating is bidirectional: Run blocked during SETUP, setup tabs blocked during GRINDING/HOMING — prevents accidental state conflicts
- Profile import "Cycle Running" text pattern already exists but is wired to old cycle_running flag — just re-wire to real MachineState

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-state-driven-ui*
*Context gathered: 2026-04-06*
