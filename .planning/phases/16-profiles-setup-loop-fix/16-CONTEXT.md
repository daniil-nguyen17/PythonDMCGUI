# Phase 16: ProfilesScreen Setup Loop Fix - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix ProfilesScreen to correctly enter and exit controller setup mode using the same smart-enter/exit pattern as AxesSetupScreen and ParametersScreen. Two bugs: no smart-enter guard (re-sends hmiSetp=0 when already in setup) and wrong exit command (sends hmiSetp=1 instead of hmiExSt=0).

</domain>

<decisions>
## Implementation Decisions

### Setup sibling membership
- ProfilesScreen does NOT join the _SETUP_SCREENS frozenset in axes_setup.py or parameters.py
- ProfilesScreen manages its own enter/exit independently — navigating axes_setup→profiles triggers exit+re-enter, which is acceptable
- Only profiles.py is modified; axes_setup.py and parameters.py are untouched

### Smart-enter guard
- on_pre_enter must check dmc_state == STATE_SETUP before firing hmiSetp=0
- If already in STATE_SETUP, skip the trigger — just proceed with lifecycle (subscribe, update import button)
- Mirrors the pattern in AxesSetupScreen (lines 175-185) and ParametersScreen (lines 403-413)

### Exit command
- on_leave must send hmiExSt=0 (not hmiSetp=1) to correctly exit setup mode
- Uses HMI_EXIT_SETUP and HMI_TRIGGER_FIRE from dmc_vars.py
- No _SETUP_SCREENS sibling check needed since profiles is not in the sibling set — always fires hmiExSt=0 on leave

### Claude's Discretion
- Whether to add a connection guard (controller.is_connected()) to the enter/exit — axes_setup and parameters both check this
- Error handling pattern for the hmiExSt command

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- dmc_vars.py: HMI_SETP, HMI_EXIT_SETUP, HMI_TRIGGER_FIRE, HMI_TRIGGER_DEFAULT, STATE_SETUP constants
- AxesSetupScreen.on_pre_enter (lines 155-185): reference implementation of smart-enter guard
- ParametersScreen.on_pre_enter (lines 395-422): same pattern, slightly different structure

### Established Patterns
- Smart enter: check `self.state.dmc_state == STATE_SETUP` before firing hmiSetp=0
- Exit: send `HMI_EXIT_SETUP=HMI_TRIGGER_FIRE` (hmiExSt=0) instead of hmiSetp=1
- Connection guard: check `self.controller.is_connected()` before sending commands
- All controller commands wrapped in try/except with pass (fire-and-forget for HMI triggers)

### Integration Points
- profiles.py on_pre_enter (line 440): currently fires hmiSetp=0 unconditionally — needs smart-enter guard
- profiles.py on_leave (line 456): currently sends hmiSetp=1 — must change to hmiExSt=0

</code_context>

<specifics>
## Specific Ideas

No specific requirements — straightforward pattern replication from axes_setup.py and parameters.py into profiles.py.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-profiles-setup-loop-fix*
*Context gathered: 2026-04-07*
