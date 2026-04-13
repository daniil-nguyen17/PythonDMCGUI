# Requirements: DMC Grinding GUI

**Defined:** 2026-04-11
**Core Value:** An operator walks up, taps their PIN, runs parts while watching a live A/B position plot, and goes home — zero friction, zero confusion, zero access to things they shouldn't touch.

## v3.0 Requirements

Requirements for multi-machine screen architecture and controller communication optimization.

### Screen Architecture

- [x] **ARCH-01**: Base classes extracted (BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen) with shared controller wiring, poll subscription, and lifecycle hooks
- [x] **ARCH-02**: Base class enforces subscribe-on-enter / unsubscribe-on-leave for state listeners
- [ ] **ARCH-03**: Per-machine screen classes created (3 types x 3 screens = 9 classes) each with own .kv file
- [x] **ARCH-04**: All lifecycle hooks (on_pre_enter, on_enter, on_leave) defined in Python base classes, not in .kv files

### Screen Loading

- [x] **LOAD-01**: machine_config._REGISTRY includes screen_classes mapping machine type to its screen class names
- [x] **LOAD-02**: main.py _load_machine_screens() dynamically adds/removes machine-specific screens under canonical names ("run", "axes_setup", "parameters")
- [x] **LOAD-03**: Screen swap stops background threads (_stop_pos_poll, _stop_mg_reader) and closes matplotlib figure before removing outgoing screens
- [x] **LOAD-04**: App detects machine type on connect (controller variable + local config) and loads correct screen set

### Flat Grind

- [x] **FLAT-01**: Existing RunScreen renamed to FlatGrindRunScreen with own .kv file in ui/flat_grind/
- [x] **FLAT-02**: Existing AxesSetupScreen renamed to FlatGrindAxesSetupScreen with own .kv file
- [x] **FLAT-03**: Existing ParametersScreen renamed to FlatGrindParametersScreen with own .kv file
- [x] **FLAT-04**: All existing Flat Grind functionality preserved — zero behavior change from v2.0

### Serration

- [x] **SERR-01**: SerrationRunScreen created from Flat Grind base with D-axis elements removed
- [x] **SERR-02**: SerrationAxesSetupScreen created with 3-axis layout (A, B, C only)
- [x] **SERR-03**: SerrationParametersScreen created with serration-specific parameter groups
- [x] **SERR-04**: bComp panel stubbed in SerrationRunScreen (blocked on customer DMC program)

### Convex

- [x] **CONV-01**: ConvexRunScreen created from Flat Grind base with convex-specific adjustment panel
- [x] **CONV-02**: ConvexAxesSetupScreen created with 4-axis layout
- [x] **CONV-03**: ConvexParametersScreen created with convex-specific parameter groups
- [x] **CONV-04**: Placeholder param_defs noted — production sign-off requires real customer specs

### Controller Communication

- [x] **COMM-01**: GRecord replaces individual MG position commands in poll loop (verify GRecord exists in wrapper first; check existing usage in screens before editing)
- [x] **COMM-02**: Remaining user variables (hmiState, ctSesKni, ctStnKni) batched into single MG command
- [x] **COMM-03**: DMC program emits structured MG messages at state transitions for sub-ms detection
- [x] **COMM-04**: MG reader thread parses structured state messages and updates MachineState immediately
- [x] **COMM-05**: Production connections use --direct flag to bypass gcaps middleware
- [x] **COMM-06**: Explicit timeouts set on all gclib handles (primary: 1000ms, MG: 500ms)

## Future Requirements

### Deployment

- **DEPLOY-01**: Raspberry Pi kiosk mode
- **DEPLOY-02**: SD card deployment image
- **DEPLOY-03**: Operator desktop lockout

### Machine-Specific (pending customer specs)

- **SERR-05**: Serration bComp write path (blocked on customer DMC program)
- **CONV-05**: Convex real param_defs (blocked on customer specifications)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Hot-swap machine type without restart | Complex teardown while polling active; settings.json + restart covers 95% of use |
| Lazy kv loading | Pi memory optimization — not blocking, defer to v3.x |
| Delete old single-machine screen files | User chose to keep old files as reference |
| Base class for ProfilesScreen/UsersScreen | Already machine-agnostic, no refactor needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ARCH-01 | Phase 18 | Complete |
| ARCH-02 | Phase 18 | Complete |
| ARCH-03 | Phase 18 | Pending |
| ARCH-04 | Phase 18 | Complete |
| LOAD-01 | Phase 20 | Complete |
| LOAD-02 | Phase 20 | Complete |
| LOAD-03 | Phase 20 | Complete |
| LOAD-04 | Phase 20 | Complete |
| FLAT-01 | Phase 19 | Complete |
| FLAT-02 | Phase 19 | Complete |
| FLAT-03 | Phase 19 | Complete |
| FLAT-04 | Phase 19 | Complete |
| SERR-01 | Phase 21 | Complete |
| SERR-02 | Phase 21 | Complete |
| SERR-03 | Phase 21 | Complete |
| SERR-04 | Phase 21 | Complete |
| CONV-01 | Phase 22 | Complete |
| CONV-02 | Phase 22 | Complete |
| CONV-03 | Phase 22 | Complete |
| CONV-04 | Phase 22 | Complete |
| COMM-01 | Phase 23 | Complete |
| COMM-02 | Phase 23 | Complete |
| COMM-03 | Phase 23 | Complete |
| COMM-04 | Phase 23 | Complete |
| COMM-05 | Phase 23 | Complete |
| COMM-06 | Phase 23 | Complete |

**Coverage:**
- v3.0 requirements: 26 total
- Mapped to phases: 26
- Unmapped: 0

---
*Requirements defined: 2026-04-11*
*Last updated: 2026-04-11 — traceability mapped after roadmap creation*
