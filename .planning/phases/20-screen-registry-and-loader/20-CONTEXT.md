# Phase 20: Screen Registry and Loader - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

The application detects the connected machine type and loads the correct screen set under canonical names. Machine switching is a restart-and-reconnect, not a hot-swap, and the swap function tears down threads and figures cleanly. Satisfies LOAD-01, LOAD-02, LOAD-03, LOAD-04.

</domain>

<decisions>
## Implementation Decisions

### Machine detection
- Local config only: settings.json `machine_type` determines which screens to load — no controller query for initial detection
- Screen set loaded at app startup during `build()`, before any connection attempt — screens are ready before ScreenManager renders
- Machine type change requires full app exit: save to settings.json, show "Machine type changed. Please restart the application." message, call cleanup then `App.stop()`. On Pi kiosk, systemd auto-restarts
- Mismatch warning: after connecting, query `machType` DMC variable. If it doesn't match settings.json, show a popup dialog asking operator to pick the correct machine type (with option to change and restart)
- If `machType` variable doesn't exist on controller (query fails or empty), skip check silently — graceful degradation

### Screen swap teardown
- Build a `cleanup()` method on base classes even though swap is restart-only — satisfies LOAD-03 and enables clean shutdown
- Teardown order: (1) stop `_pos_poll` thread, (2) stop `_mg_reader` thread, (3) `plt.close(fig)` on run screen, (4) unsubscribe state listeners, (5) `sm.remove_widget(screen)`
- `cleanup()` method on each base class: BaseRunScreen handles threads + figure, BaseAxesSetupScreen/BaseParametersScreen handle setup exit + unsubscribe
- `cleanup()` called both during screen swap AND during normal `App.on_stop()` shutdown — prevents thread-still-running-after-window-close
- Log each cleanup step at INFO level: `[FlatGrindRunScreen] cleanup: stopping pos_poll`, etc. — aids hardware debugging
- Thread stop strategy: set stop flag and don't wait — no blocking the UI thread. Thread finishes current iteration naturally

### Registry shape
- Import path strings in `_REGISTRY`: `'screen_classes': {'run': 'dmccodegui.screens.flat_grind.FlatGrindRunScreen', ...}` — avoids circular imports, lightweight
- Registry also stores `load_kv` path: `'load_kv': 'dmccodegui.screens.flat_grind.load_kv'` — loader imports and calls before resolving screen classes. Explicit, no convention magic
- Canonical screen names as keys: `{'run': '...', 'axes_setup': '...', 'parameters': '...'}` — matches ScreenManager `name=` values, tab bar and navigation unchanged
- Every machine type package follows identical `load_kv()` + class export pattern established by flat_grind in Phase 19

### First-launch UX
- Blocking picker popup when no machine type is configured (first launch) — operator must pick to proceed
- If settings.json contains unknown machine type string (corrupted/old), treat as unconfigured — show first-launch picker (self-healing)
- After first-launch pick: continue directly into the app without restart — nothing to tear down yet
- First-launch picker shows machine type names only ("4-Axes Flat Grind", etc.) — operators know their machine

### Error handling
- If screen loading fails (bad import, missing KV file): show error popup with exception message, then exit. Running without screens makes no sense
- Unknown machine type in settings.json: treated as unconfigured, shows first-launch picker

### Tab bar integration
- Same 5 tabs for all machine types: Run, Axes Setup, Parameters, Profiles, Users — navigation is identical across machines
- Status bar shows active machine type (already has tappable label for picker) — no tab bar changes
- Profiles and Users stay in base.kv as machine-agnostic screens — only Run, Axes Setup, Parameters go through the registry

### Claude's Discretion
- Exact `_load_machine_screens()` implementation details
- importlib resolution strategy for dotted path strings
- Mismatch popup dialog layout and wording
- Test structure for verifying screen loading and cleanup

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `machine_config._REGISTRY`: already has per-type entries with `axes`, `has_bcomp`, `param_defs` — add `screen_classes` and `load_kv` keys
- `machine_config.init()` / `get_active_type()` / `is_configured()`: existing API for reading persisted machine type
- `screens/flat_grind/__init__.py`: established `load_kv()` + class export pattern — template for serration/convex packages
- `main.py._show_machine_type_picker()`: existing picker popup — reusable for first-launch and mismatch flows
- `screens/base.py`: BaseRunScreen, BaseAxesSetupScreen, BaseParametersScreen — add `cleanup()` methods here

### Established Patterns
- Deferred KV loading: `load_kv()` called from `main.py build()` before Factory instantiation — avoids circular imports
- ObjectProperty injection: `main.py` sets controller/state on screens via `sm.get_screen(name)` — works with canonical names
- HMI one-shot variable pattern: `machType` variable query follows same pattern as other DMC variable reads
- Screen names are canonical: `name='run'`, `name='axes_setup'`, `name='parameters'` — all navigation uses these

### Integration Points
- `machine_config.py._REGISTRY`: add `screen_classes` and `load_kv` entries per machine type
- `main.py.build()`: replace hard-coded flat_grind import with registry-driven loader
- `main.py._show_machine_type_picker()`: wire to first-launch flow and mismatch dialog
- `screens/base.py`: add `cleanup()` methods to base classes
- `main.py.on_stop()`: wire cleanup() calls for all active machine screens
- Connect callback: add `machType` query and mismatch check after gclib connection succeeds

</code_context>

<specifics>
## Specific Ideas

- Mismatch popup should let the operator pick the correct machine type (not just dismiss) — if they change it, save and restart
- If `machType` query fails silently, the app just uses settings.json — no error, no warning, no friction
- The cleanup() + on_stop() wiring means the app always shuts down cleanly whether exiting normally, changing machine type, or being killed by systemd

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-screen-registry-and-loader*
*Context gathered: 2026-04-11*
