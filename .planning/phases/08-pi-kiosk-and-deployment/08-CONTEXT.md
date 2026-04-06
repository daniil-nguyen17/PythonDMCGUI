# Phase 8: Pi Kiosk and Deployment - Context

**Gathered:** 2026-04-06
**Status:** Deferred — awaiting hardware validation

<domain>
## Phase Boundary

The app boots automatically on a Raspberry Pi into a locked-down kiosk with no path for operators to reach the desktop, and installs from an SD card image. Same codebase runs as a standard window on Windows 11.

</domain>

<decisions>
## Implementation Decisions

### Deferral Decision
- Phase 8 is deferred until all feature phases (1-7) have been tested on a real DMC controller machine
- Rationale: Locking down the OS before confirming all features work against real hardware adds unnecessary friction to debugging
- Resume this phase after hardware validation is complete and any issues are resolved

### Claude's Discretion
- All technical implementation details deferred to post-hardware-testing discussion
- Pi OS version, window manager, systemd config, SD card packaging approach — all TBD

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main.py` top block: Config.set calls already in correct position (before any Kivy Window import)
- `platform.machine()` or env var detection can be added to main.py top block for Pi vs Windows branching

### Established Patterns
- Config.set order: all graphics config at top of main.py, before imports (Pitfall 13 compliance)
- Machine type hard-coded at deployment (Phase 6 decision)

### Integration Points
- `main.py` top block: kiosk fullscreen/borderless config goes here
- systemd service unit: external to Python code, OS-level configuration
- SD card image: packaging concern, not code concern

</code_context>

<specifics>
## Specific Ideas

No specific requirements captured — discussion deferred to post-hardware-testing.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-pi-kiosk-and-deployment*
*Context gathered: 2026-04-06*
