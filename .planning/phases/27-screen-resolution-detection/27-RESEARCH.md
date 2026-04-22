# Phase 27: Screen Resolution Detection - Research

**Researched:** 2026-04-22
**Domain:** screeninfo + Kivy Config/metrics pre-import block, settings.json override
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Window.size set per preset (replacing hardcoded 1920x1080 at main.py:54)
- KIVY_METRICS_DENSITY adjusted per preset so all existing sp() values in KV files scale proportionally — zero KV file changes needed
- App must launch truly fullscreen on all platforms — current behavior is broken (maximized but off to the side, requires manual drag/resize). Fix this as part of preset application.
- No layout adaptation (no hiding/reorganizing widgets per screen size) — density scaling only
- Preset confirmation via startup log line only — no in-app UI indicator
- Three presets: 7inch, 10inch, 15inch/desktop
- All three Pi touchscreen tiers supported: 7" (800x480), 10" (1024x600), 15" (various)
- Windows at 1920x1080 gets the 15inch/desktop preset automatically
- Ambiguous/borderline resolutions round DOWN to the smaller preset
- Pi always uses Pi presets — no special handling for external monitors connected to Pi
- Manual override via settings.json key
- File edit only — no in-app UI for changing preset in this phase
- When screeninfo fails (SSH, headless, no display): fallback to 15inch/desktop preset
- Invalid override value in settings.json: log warning + use 15inch/desktop default (do NOT fall through to auto-detect)
- Override confirmed by a log line at startup

### Claude's Discretion
- screeninfo detection implementation details
- Exact KIVY_METRICS_DENSITY values per preset
- settings.json key name and value format for the override
- Exact resolution threshold boundaries between presets
- How to achieve true fullscreen on both platforms
- Whether screeninfo needs to be added to requirements-pi.txt

### Deferred Ideas (OUT OF SCOPE)
- In-app display preset picker — Admin/Setup dropdown to change display preset without editing settings.json.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| APP-04 | App auto-detects screen resolution at startup with manual override option in settings.json for 7"/10"/15" displays | screeninfo get_monitors() provides width/height; ScreenInfoError catch handles headless fallback; settings.json display_size key provides override; KIVY_METRICS_DENSITY env var provides density scaling; Config.set graphics block provides fullscreen behavior |
</phase_requirements>

---

## Summary

Phase 27 inserts a resolution detection block into main.py's existing pre-Kivy import section (lines 35-54). The block runs screeninfo.get_monitors() before any Kivy import, reads the primary monitor's pixel dimensions, classifies them into one of three presets (7inch, 10inch, 15inch/desktop), and applies the preset by setting KIVY_METRICS_DENSITY and adjusting the Config.set graphics block. A settings.json key named `display_size` allows technician override without code edits.

The current "maximized but off to the side" bug on Windows is caused by Config.set('graphics', 'maximized', '1') combined with Window.size = (1920, 1080) — these conflict. The correct fix is to use Config.set('graphics', 'fullscreen', 'auto') for Pi (true OS fullscreen at native resolution) and a borderless window sized to match screeninfo-detected dimensions for Windows desktop. The 'auto' fullscreen mode ignores width/height Config values entirely and uses the display's native resolution, which is exactly right for Pi kiosk operation.

screeninfo 0.8.1 is the current stable release (September 2022 — no newer version). It raises `screeninfo.common.ScreenInfoError` with "No enumerators available" in headless/SSH/no-display environments. This is the single exception type to catch for the fallback path. The library is not present in requirements-pi.txt and must be added.

**Primary recommendation:** Insert `_detect_preset()` function immediately before the `os.environ["KIVY_DPI_AWARE"]` line at main.py:35, reading settings.json for override, then calling screeninfo, then setting env vars and Config.set values all in one function. This keeps the pre-Kivy block self-contained and testable.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| screeninfo | 0.8.1 | Get primary monitor pixel dimensions before Kivy import | Only pure-Python library that works on X11 (Pi) and Windows without a running Kivy window; no C extension compile required on Pi |
| kivy (existing) | 2.3.1 | Config.set pre-import + KIVY_METRICS_DENSITY env var | Already in project; density env var read at Kivy startup before Window creation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | stdlib | Read settings.json for display_size override | Already used in machine_config.py — same read pattern |
| logging (stdlib) | stdlib | Emit startup log line confirming preset | Already used in machine_config and main.py |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| screeninfo | tkinter root.winfo_screenwidth() | tkinter creates a window, which can conflict with Kivy SDL2 on Pi; avoid |
| screeninfo | subprocess xrandr parsing | Fragile, Linux-only, breaks in SSH, more code |
| screeninfo | os.environ['DISPLAY'] + Xlib | Requires python-xlib, heavier dependency |

**Installation:**
```bash
# Dev/Windows
pip install screeninfo==0.8.1

# Pi — add to deploy/pi/requirements-pi.txt:
screeninfo==0.8.1
```

## Architecture Patterns

### Recommended Project Structure
No new files or directories needed. All changes are in:
```
src/dmccodegui/
├── main.py          # _detect_preset() + pre-import block changes (lines 35-54)
└── machine_config.py  # (no changes needed — settings.json read happens in main.py pre-import)
deploy/pi/
└── requirements-pi.txt  # add screeninfo==0.8.1
tests/
└── test_display_preset.py  # new test file (Wave 0 gap)
```

### Pattern 1: Pre-Import Resolution Detection Function

**What:** A module-level function `_detect_preset()` called before any Kivy import, returns a preset dict with all values the Config.set block needs.

**When to use:** Whenever configuration must happen before Kivy initializes its window system — the exact same constraint that governs GCLIB_ROOT and KIVY_DPI_AWARE in the existing block.

**Example:**
```python
# In main.py — BEFORE any kivy import

import os
import sys
import json
import logging

_log = logging.getLogger(__name__)

# Preset definitions — locked values
_DISPLAY_PRESETS = {
    "7inch": {
        "density": "0.75",
        "width": 800,
        "height": 480,
        "fullscreen_mode": "auto",   # Pi: let OS own fullscreen
        "borderless": "0",
        "maximized": "0",
        "resizable": "0",
    },
    "10inch": {
        "density": "0.85",
        "width": 1024,
        "height": 600,
        "fullscreen_mode": "auto",   # Pi: let OS own fullscreen
        "borderless": "0",
        "maximized": "0",
        "resizable": "0",
    },
    "15inch": {
        "density": "1",
        "width": 1920,
        "height": 1080,
        "fullscreen_mode": "0",      # Windows: windowed
        "borderless": "1",           # borderless covers full screen
        "maximized": "0",
        "resizable": "0",
    },
}

_PRESET_NAMES = ("7inch", "10inch", "15inch")

def _detect_preset(settings_path: str) -> str:
    """Return preset name: '7inch', '10inch', or '15inch'.

    Priority:
      1. settings.json display_size override (if valid)
      2. screeninfo primary monitor detection
      3. Fallback: '15inch' (headless/SSH/error)
    """
    # --- 1. Check settings.json override ---
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            override = data.get("display_size", "")
            if override in _PRESET_NAMES:
                _log.info("Display preset: %s (settings.json override)", override)
                return override
            elif override:
                _log.warning(
                    "Invalid display_size %r in settings.json — using 15inch default",
                    override,
                )
                return "15inch"
        except (json.JSONDecodeError, OSError):
            pass

    # --- 2. Auto-detect via screeninfo ---
    try:
        from screeninfo import get_monitors
        from screeninfo.common import ScreenInfoError
        monitors = get_monitors()
        # Pick primary monitor; fall back to first
        primary = next((m for m in monitors if m.is_primary), monitors[0] if monitors else None)
        if primary is None:
            raise ScreenInfoError("No monitors returned")
        w, h = primary.width, primary.height
        preset = _classify_resolution(w, h)
        _log.info("Display preset: %s (%dx%d detected)", preset, w, h)
        return preset
    except Exception as exc:
        _log.warning("screeninfo failed (%s) — using 15inch fallback", exc)
        return "15inch"


def _classify_resolution(width: int, height: int) -> str:
    """Map pixel dimensions to preset name, rounding DOWN on ambiguous."""
    # Use the smaller dimension (height) as the discriminator — landscape or portrait
    short = min(width, height)
    if short <= 480:
        return "7inch"
    elif short <= 600:
        return "10inch"
    else:
        return "15inch"
```

**Threshold rationale (Claude's discretion):**
- `short <= 480` → 7inch (800x480 Pi official touchscreen)
- `short <= 600` → 10inch (1024x600 Pi 10" displays; covers 768px-tall 10" variants too if they exist)
- else → 15inch/desktop (covers 768, 1080, etc.)
- Uses `min(width, height)` as discriminator so the classification is rotation-agnostic

### Pattern 2: Applying Preset in the Pre-Import Config Block

**What:** Replace the static Config.set block (main.py:41-54) with preset-driven values.

**When to use:** Immediately after `_detect_preset()` returns, still before `from kivy.config import Config`.

**Example:**
```python
# main.py pre-import block — replaces existing static lines 35-54

def _get_data_dir() -> str:
    # ... (unchanged)

# --- NEW: resolve settings path early (same logic as DMCApp.__init__) ---
def _early_settings_path() -> str:
    """Duplicate _get_data_dir logic for pre-Kivy settings read."""
    if getattr(sys, 'frozen', False):
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        return os.path.join(appdata, 'BinhAnHMI', 'settings.json')
    elif sys.platform == 'linux':
        return os.path.join(os.path.expanduser('~'), '.binh-an-hmi', 'settings.json')
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth', 'settings.json')

_ACTIVE_PRESET_NAME = _detect_preset(_early_settings_path())
_PRESET = _DISPLAY_PRESETS[_ACTIVE_PRESET_NAME]

os.environ["KIVY_DPI_AWARE"] = "1"
os.environ["KIVY_METRICS_DENSITY"] = _PRESET["density"]
os.environ["KIVY_MOUSE"] = "mouse,multitouch_on_demand"

from kivy.config import Config
Config.set('graphics', 'fullscreen', _PRESET["fullscreen_mode"])
Config.set('graphics', 'maximized', _PRESET["maximized"])
Config.set('graphics', 'borderless', _PRESET["borderless"])
Config.set('graphics', 'resizable', _PRESET["resizable"])
Config.set('graphics', 'width',  str(_PRESET["width"]))
Config.set('graphics', 'height', str(_PRESET["height"]))
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.core.window import Window
# Window.size line REMOVED — fullscreen='auto' ignores it on Pi;
# for 15inch borderless, width/height Config values set above take effect.
```

**Critical: Window.size = (1920, 1080) at main.py:54 must be deleted.** On Pi with `fullscreen='auto'`, setting Window.size after import has no effect (OS controls it) but wastes a call. On Windows borderless, the width/height Config.set values above control the initial size correctly — no post-import Window.size needed.

### Pattern 3: Fullscreen Strategy Per Platform

**What:** Different `fullscreen_mode` values for Pi vs. Windows to achieve "fills the screen on launch."

**Why the current code is broken:** `Config.set('graphics', 'maximized', '1')` + `Window.size = (1920, 1080)` causes the SDL2 window to open maximized but positioned at SDL2's default position (often offset). The maximize and the explicit size fight each other.

**Pi (7inch, 10inch):** Use `fullscreen='auto'` — SDL2 calls SDL_WINDOW_FULLSCREEN_DESKTOP, which uses the desktop's native resolution and positions the window at (0,0) with zero decoration. No width/height Config values needed (they are ignored in auto mode). This is the correct kiosk mode.

**Windows/15inch:** Use `fullscreen='0'` + `borderless='1'` + explicit `width` and `height` from screeninfo. The borderless window covers the taskbar area visually, and since resizable='0' the user cannot move it. This is preferable to true fullscreen on Windows desktops because true fullscreen (`fullscreen='1'`) can cause monitor mode switches.

**Alternative for Windows if borderless causes issues:** Use `fullscreen='0'` + `maximized='1'` + `borderless='0'` with a `Window.maximize()` call post-import. This is the fallback if the borderless approach produces edge artifacts on the Windows dev machine. The planner should add a note to test both and use borderless first.

### Anti-Patterns to Avoid

- **Setting Window.size after import when using fullscreen='auto':** On Pi, `fullscreen='auto'` means SDL2 owns the window geometry. Post-import Window.size calls are silently ignored. Remove the hardcoded `Window.size = (1920, 1080)` line.
- **Using `fullscreen='1'` (true fullscreen) on Windows:** Changes the monitor's video mode. On dual-monitor setups this can black out the second monitor. Use borderless instead.
- **Using tkinter to detect screen size:** tkinter initializes its own display connection; on some Pi X11 configurations this conflicts with SDL2's display lock. Use screeninfo only.
- **Logging before basicConfig:** `_log = logging.getLogger(__name__)` at module level works, but if basicConfig hasn't run yet the startup log line may not appear. Ensure logging is initialized before `_detect_preset()` runs, or use `print()` as a bootstrap log and switch to logging after Kivy import. The existing project uses `print()` statements in the pre-Kivy block — match that pattern for consistency.
- **Reading settings.json twice:** `_early_settings_path()` duplicates `_get_data_dir()` logic. This is intentional (Kivy not yet imported, no App instance exists). Document clearly that this is a pre-init bootstrap read; `mc.init()` in DMCApp.__init__() will read settings.json again later and that is fine.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Get screen pixel dimensions | Custom X11 xrandr subprocess parsing | `screeninfo.get_monitors()` | screeninfo handles X11/Xinerama, Windows, macOS with a single API; xrandr is brittle and Linux-only |
| Font/touch target scaling | Per-widget sp() overrides in KV files | `KIVY_METRICS_DENSITY` env var | Setting density before Kivy import scales ALL sp() values globally; zero KV changes needed |
| Headless detection | Check `os.environ.get('DISPLAY')` | `except Exception` around get_monitors | DISPLAY env var doesn't always indicate whether Xinerama can enumerate monitors; screeninfo's exception is the reliable signal |

**Key insight:** KIVY_METRICS_DENSITY is the right lever for this project because all KV files already use sp() units. Density=0.75 makes 40sp render as 30px, density=1.0 keeps 40sp=40px. No widget code needs to change.

## Common Pitfalls

### Pitfall 1: screeninfo raises ScreenInfoError on Pi when called over SSH
**What goes wrong:** A developer SSH's into the Pi to run the app for testing (no X11 forwarding, DISPLAY not set). screeninfo finds no X11 enumerator and raises `ScreenInfoError: No enumerators available`. App falls to 15inch/desktop preset and launches with wrong density.
**Why it happens:** X11 Xinerama enumeration requires a running X server and the DISPLAY env var pointing to it. SSH sessions don't have this by default.
**How to avoid:** This is the defined fallback behavior — log the warning, return "15inch". On real Pi hardware with a locally connected display, X11 is always available (install.sh forces X11, PI-04 complete). The only time this fallback fires is dev/testing over SSH, which is acceptable.
**Warning signs:** Startup log shows "screeninfo failed" warning. Only concerning if it fires on physical hardware with a display attached.

### Pitfall 2: `fullscreen='auto'` ignores Config width/height — but Window.size still set
**What goes wrong:** If the existing `Window.size = (1920, 1080)` line at main.py:54 is not deleted, on Pi with `fullscreen='auto'` the assignment is silently a no-op but misleads future readers about the actual window geometry.
**Why it happens:** Kivy's SDL2 backend, when fullscreen='auto', controls window geometry from the OS. The Window.size setter does nothing.
**How to avoid:** Delete `Window.size = (1920, 1080)` in the same commit as the preset block is added.

### Pitfall 3: screeninfo 0.8.1 returns monitors in undefined order on multi-monitor setups
**What goes wrong:** A development machine with 2 monitors returns monitors in an order that may not put the primary monitor first.
**Why it happens:** The order from the underlying enumerator is OS-defined, not screeninfo-defined.
**How to avoid:** Use `next((m for m in monitors if m.is_primary), monitors[0])` — prefer the primary flag, fall back to first. On Pi (single display), there is always exactly one monitor and `is_primary` may be True or may not be set depending on the X11 driver; the `monitors[0]` fallback handles this.

### Pitfall 4: settings.json not yet created on first launch
**What goes wrong:** `_early_settings_path()` returns a path that doesn't exist yet. `os.path.exists()` returns False, so the override check is skipped correctly — but only if the path check is done before the open() call.
**Why it happens:** First-time launch: data_dir doesn't exist, settings.json hasn't been written.
**How to avoid:** The pattern `if os.path.exists(settings_path): try: open()...` already handles this correctly. Do NOT use `open()` inside a bare try without the existence check, as OSError would be caught by the outer Exception handler and silently fall through to auto-detect (which is actually fine, but the intent should be explicit).

### Pitfall 5: Invalid display_size in settings.json falls through to auto-detect (wrong behavior)
**What goes wrong:** A typo like `"display_size": "7-inch"` (hyphen instead of empty) should produce the 15inch fallback, NOT auto-detect.
**Why it happens:** If the override validation only skips on empty string, any non-empty invalid value slips through to detection.
**How to avoid:** The decision is explicit: invalid override value → log warning + return "15inch". Do NOT fall through to auto-detect for invalid values. The test should cover this case specifically.

### Pitfall 6: Logging before logging is configured
**What goes wrong:** `_log = logging.getLogger(__name__)` at module top, called in `_detect_preset()` before DMCApp configures logging, produces no output or spurious output.
**Why it happens:** The existing codebase uses `print()` in the pre-Kivy block for bootstrap messages. Python's logging module is unconfigured at module import time.
**How to avoid:** Use `print()` for the preset detection log lines (matching existing project style in the pre-Kivy block), or delay the `_log.info()` until after Kivy imports. The startup log line confirming the preset can also be emitted via `logging.getLogger(__name__).info()` inside `DMCApp.build()` using the module-level `_ACTIVE_PRESET_NAME` variable.

## Code Examples

Verified patterns from official sources:

### screeninfo: Get primary monitor dimensions
```python
# Source: https://github.com/rr-/screeninfo (README example + issue #22 for error type)
from screeninfo import get_monitors
from screeninfo.common import ScreenInfoError

try:
    monitors = get_monitors()
    primary = next((m for m in monitors if m.is_primary), monitors[0] if monitors else None)
    if primary:
        print(f"{primary.width}x{primary.height}")
except ScreenInfoError as exc:
    print(f"No display: {exc}")
except Exception as exc:
    print(f"Unexpected error: {exc}")
```

### Kivy: fullscreen='auto' for true OS fullscreen (Pi/Linux)
```python
# Source: https://kivy.org/doc/stable/api-kivy.config.html
# "If set to auto, your current display's resolution will be used"
from kivy.config import Config
Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'resizable', '0')
# width/height are ignored when fullscreen='auto'
```

### Kivy: borderless window sized to display (Windows)
```python
# Source: https://kivy.org/doc/stable/api-kivy.config.html
# borderless=1 removes window decoration; width/height set initial size
from kivy.config import Config
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'width', '1920')
Config.set('graphics', 'height', '1080')
```

### Kivy: KIVY_METRICS_DENSITY effect on sp()
```python
# Source: https://kivy.org/doc/stable/api-kivy.metrics.html
# "if set, this value will be used for density instead of the systems one"
# sp(40) at density=0.75 → effective size 30 logical units
# sp(40) at density=1.0  → effective size 40 logical units
import os
os.environ["KIVY_METRICS_DENSITY"] = "0.75"  # must set before any kivy import
```

### machine_config.py: settings.json read pattern (reference for display_size)
```python
# Source: src/dmccodegui/machine_config.py lines 223-231
# This is the existing pattern — display_size override follows same structure
if os.path.exists(settings_path):
    try:
        with open(settings_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        stored = data.get("machine_type", "")
        if stored in _REGISTRY:
            _active_type = stored
    except (json.JSONDecodeError, OSError):
        pass
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `fullscreen='fake'` in Kivy | `borderless=1` (Config) | Kivy ~2.0 | 'fake' deprecated; use borderless + width/height |
| Static `Window.size = (1920, 1080)` | Preset-driven Config.set width/height | Phase 27 | Replaces hardcoded value; per-display sizing |
| `Config.set('graphics', 'maximized', '1')` | `fullscreen='auto'` on Pi, `borderless='1'` on Windows | Phase 27 | Fixes "off to the side" bug |

**Deprecated/outdated:**
- `fullscreen='fake'`: Kivy docs say "fake fullscreen has been deprecated. Use the borderless property instead."
- `Window.size = (1920, 1080)` post-import: Correct for windowed mode but wrong when fullscreen='auto' overrides it on Pi; must be removed.

## Open Questions

1. **KIVY_METRICS_DENSITY exact values for 7inch and 10inch presets**
   - What we know: density=1.0 is current (Windows/desktop). KV files use sp() at values like 25sp, 17sp, 40sp designed for a 1920x1080 display.
   - What's unclear: What density makes a 40sp button "tappable" on an 800x480 touchscreen? Needs field testing.
   - Recommendation: Start with density=0.75 for 7inch (scales sp proportionally to ~800/1080 ≈ 0.74) and density=0.85 for 10inch (1024/1080 ≈ 0.95, but keep lower because 600px height is the binding constraint: 600/1080 ≈ 0.56 — suggest 0.65 for 7inch and 0.75 for 10inch instead). Technician can override via settings.json. **The planner should treat these values as initial guesses pending hardware validation, not locked values.** Make them constants that are easy to update.

2. **screeninfo on Pi with HDMI-forced framebuffer vs. DSI touchscreen**
   - What we know: STATE.md flags "screeninfo on Pi HDMI-forced framebuffer — validate on real hardware in Phase 27." The Pi 7" official display uses DSI, not HDMI. X11 may report the display differently.
   - What's unclear: Whether X11 Xinerama correctly reports 800x480 for the DSI display, or whether it reports a different resolution due to framebuffer/DRM scaling.
   - Recommendation: The `_classify_resolution` function should use the `short = min(width, height)` approach so rotation doesn't matter. If X11 reports a different-than-expected resolution (e.g., 480x800 portrait), the classifier still works. **This is the primary hardware validation risk for Phase 29.**

3. **Windows: borderless window and taskbar**
   - What we know: `fullscreen='0'` + `borderless='1'` + `width=detected` + `height=detected` should fill the screen. On Windows, the taskbar may still be visible above/below a borderless window unless the window exactly matches the screen.
   - What's unclear: Whether Config.set width/height matching the screeninfo-detected monitor geometry will hide the taskbar on Windows 11.
   - Recommendation: If the taskbar remains visible, the fallback is `fullscreen='0'` + `maximized='1'` + `borderless='0'` (classic maximized window). Document this as the fallback strategy for the planner.

## Validation Architecture

nyquist_validation is enabled (config.json: `"nyquist_validation": true`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml: `[project.optional-dependencies] dev = ["pytest"]`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options] testpaths = ["tests"]`) |
| Quick run command | `pytest tests/test_display_preset.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| APP-04 | 800x480 detected → 7inch preset returned | unit | `pytest tests/test_display_preset.py::test_classify_7inch -x` | Wave 0 |
| APP-04 | 1024x600 detected → 10inch preset returned | unit | `pytest tests/test_display_preset.py::test_classify_10inch -x` | Wave 0 |
| APP-04 | 1920x1080 detected → 15inch preset returned | unit | `pytest tests/test_display_preset.py::test_classify_15inch -x` | Wave 0 |
| APP-04 | Ambiguous (e.g., 1024x768) → rounds DOWN | unit | `pytest tests/test_display_preset.py::test_classify_ambiguous -x` | Wave 0 |
| APP-04 | screeninfo raises → fallback to 15inch | unit | `pytest tests/test_display_preset.py::test_screeninfo_failure_fallback -x` | Wave 0 |
| APP-04 | Valid display_size in settings.json → override used | unit | `pytest tests/test_display_preset.py::test_override_valid -x` | Wave 0 |
| APP-04 | Invalid display_size in settings.json → 15inch (not auto-detect) | unit | `pytest tests/test_display_preset.py::test_override_invalid -x` | Wave 0 |
| APP-04 | Missing settings.json → auto-detect runs | unit | `pytest tests/test_display_preset.py::test_no_settings_file -x` | Wave 0 |
| APP-04 | Startup log line contains preset name | unit | `pytest tests/test_display_preset.py::test_startup_log_line -x` | Wave 0 |
| APP-04 | KIVY_METRICS_DENSITY env var set correctly for each preset | unit | `pytest tests/test_display_preset.py::test_density_values -x` | Wave 0 |

**Note:** Tests for `_detect_preset()` and `_classify_resolution()` must mock `screeninfo.get_monitors` — these functions are testable without Kivy import because the detection logic runs before any Kivy import. Follow the `importlib.reload(m)` + `monkeypatch` pattern established in `tests/test_data_dir.py`.

### Sampling Rate
- **Per task commit:** `pytest tests/test_display_preset.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_display_preset.py` — covers all APP-04 unit tests listed above
- [ ] `screeninfo==0.8.1` added to `deploy/pi/requirements-pi.txt`
- [ ] `screeninfo` available in dev environment: `pip install screeninfo==0.8.1` (not in pyproject.toml dev deps — add if desired, or install manually)

## Sources

### Primary (HIGH confidence)
- https://github.com/rr-/screeninfo — README, screeninfo.py source, issue #22 (ScreenInfoError in Docker/headless)
- https://pypi.org/project/screeninfo/ — version 0.8.1 confirmed, Monitor dataclass fields confirmed
- https://kivy.org/doc/stable/api-kivy.config.html — fullscreen modes ('0','1','auto','fake'), borderless, width/height, resizable behavior confirmed
- https://kivy.org/doc/stable/api-kivy.metrics.html — KIVY_METRICS_DENSITY env var behavior, sp() scaling confirmed
- `src/dmccodegui/main.py` — lines 35-54 pre-import block structure; line 54 Window.size hardcoded value
- `src/dmccodegui/machine_config.py` — settings.json read pattern (lines 223-231)

### Secondary (MEDIUM confidence)
- https://github.com/kivy/kivy/issues/2151 — 'auto' fullscreen behavior confirmed: uses display native resolution, width/height Config values ignored
- WebSearch cross-reference: ScreenInfoError raised as "No enumerators available" in headless/SSH confirmed by multiple GitHub issues

### Tertiary (LOW confidence)
- KIVY_METRICS_DENSITY exact values (0.75, 0.85) for 7inch and 10inch — derived from ratio calculation, not from official guidance; needs hardware validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — screeninfo is the only reasonable option; Kivy Config/env pattern confirmed from official docs
- Architecture: HIGH — pre-import block pattern is established in this codebase; fullscreen modes confirmed from Kivy docs
- Pitfalls: HIGH — ScreenInfoError behavior confirmed from screeninfo source and multiple issue reports; fullscreen Config interactions confirmed
- KIVY_METRICS_DENSITY values: LOW — estimated from pixel ratios, must be validated on hardware

**Research date:** 2026-04-22
**Valid until:** 2026-07-22 (screeninfo 0.8.1 stable since 2022; Kivy 2.3.1 stable)
