# Phase 27: Screen Resolution Detection - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Auto-detect display geometry before any Kivy Window import and apply the correct layout preset (7"/10"/15") so operators on all supported displays get a usable interface. A settings.json override allows a technician to force a preset without editing code. No layout reorganization — presets control Window.size, font density scaling, and fullscreen behavior only.

</domain>

<decisions>
## Implementation Decisions

### What presets control
- Window.size set per preset (replacing hardcoded 1920x1080 at main.py:54)
- KIVY_METRICS_DENSITY adjusted per preset so all existing sp() values in KV files scale proportionally — zero KV file changes needed
- App must launch truly fullscreen on all platforms — current behavior is broken (maximized but off to the side, requires manual drag/resize). Fix this as part of preset application.
- No layout adaptation (no hiding/reorganizing widgets per screen size) — density scaling only
- Preset confirmation via startup log line only (e.g., "Display preset: 7inch (800x480 detected)") — no in-app UI indicator

### Resolution thresholds
- Three presets: 7inch, 10inch, 15inch/desktop
- All three Pi touchscreen tiers supported: 7" (800x480), 10" (1024x600), 15" (various)
- Windows at 1920x1080 gets the 15inch/desktop preset automatically
- Ambiguous/borderline resolutions round DOWN to the smaller preset (larger fonts/targets, always usable) — technician can override up via settings.json
- Pi always uses Pi presets — no special handling for external monitors connected to Pi

### Override & fallback
- Manual override via settings.json key (Claude decides key name and value format)
- File edit only — no in-app UI for changing preset in this phase
- When screeninfo fails (SSH, headless, no display): fallback to 15inch/desktop preset
- Invalid override value in settings.json: log warning + use 15inch/desktop default (do NOT fall through to auto-detect)
- Override confirmed by a log line at startup (per success criteria SC-2)

### Claude's Discretion
- screeninfo detection implementation details
- Exact KIVY_METRICS_DENSITY values per preset
- settings.json key name and value format for the override
- Exact resolution threshold boundaries between presets
- How to achieve true fullscreen on both platforms (Config.set fullscreen vs borderless vs Window.size matching monitor)
- Whether screeninfo needs to be added to requirements-pi.txt

</decisions>

<specifics>
## Specific Ideas

- Current app is "maximized but off to the side" on Windows — must fix so it fills the entire screen on launch, no dragging
- STATE.md already notes: "screeninfo-based resolution detection in pre-Kivy block (same ordering pattern already established)"
- Detection must happen in the pre-import block (before `from kivy.core.window import Window`) following the established Config.set pattern at main.py:35-54

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main.py:35-54`: Pre-import Config.set block — resolution detection and preset application slot in here
- `main.py:15-32` (`_get_data_dir()`): Established pattern for platform-specific paths — settings.json location is already resolved
- `main.py:160-162`: settings.json loaded via `machine_config.init(settings_path)` — display_size override can be read from same file
- `machine_config.py`: Already reads/writes settings.json — pattern for adding display_size key

### Established Patterns
- Pre-import configuration: Config.set calls before Kivy Window import (GCLIB_ROOT, KIVY_DPI_AWARE, KIVY_METRICS_DENSITY all set before imports)
- Platform detection: `getattr(sys, 'frozen', False)`, `sys.platform == 'linux'` — extend for resolution detection
- KV files use `sp()` units for font sizes ('25sp', '17sp', '40sp') — density scaling via KIVY_METRICS_DENSITY will auto-apply

### Integration Points
- `main.py:54` (`Window.size = (1920, 1080)`) — replaced by preset-driven value
- `main.py:35-37` (KIVY_DPI_AWARE, KIVY_METRICS_DENSITY env vars) — density values come from preset
- `main.py:41-44` (Config.set graphics block) — fullscreen/maximized settings updated per preset
- `settings.json` in data_dir — gains display_size override key
- `deploy/pi/requirements-pi.txt` — may need screeninfo added

</code_context>

<deferred>
## Deferred Ideas

- **In-app display preset picker** — Admin/Setup dropdown to change display preset without editing settings.json. Good-to-have for a future phase.

</deferred>

---

*Phase: 27-screen-resolution-detection*
*Context gathered: 2026-04-22*
