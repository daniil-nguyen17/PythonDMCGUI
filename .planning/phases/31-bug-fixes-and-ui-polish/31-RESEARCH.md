# Phase 31: Bug Fixes and UI Polish - Research

**Researched:** 2026-05-04
**Domain:** Kivy KV layout, gclib MG subscription, install.sh hardening, ANGLE/SDL2 GPU backend
**Confidence:** HIGH (all findings are from direct code inspection of the actual codebase)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- All deployment screens are 15.6" at 1920x1080 — remove the 7" and 10" display presets from the code entirely; default to 15" 1920x1080 preset only
- Standardize ALL padding, spacing, and card sizing across every screen using fixed spacing token scale: 4dp / 8dp / 12dp / 16dp / 24dp — every padding and spacing value maps to one of these
- Card heights are content-driven (adapt to content), not uniform across screens
- Tab bar and status bar are already fixed-height shared chrome — verify they don't shift between screens
- ANGLE fix and venv fix are verify-and-close, not implement — code is already there; just add log confirmation and run tests
- MG reader Pi support is research-dependent: remove platform guard if Linux gclib supports `--subscribe MG`, otherwise accept Windows-only
- MG messages display in the existing controller log box on the Run screen — no new UI needed
- No extra startup logging for MG reader status — current behavior is sufficient
- The spacing standardization (4/8/12/16/24dp tokens) applies to every KV file in the project

### Claude's Discretion

- Exact mapping of current spacing values to the 4/8/12/16/24dp token scale
- Which elements need size increases for 44dp compliance
- How to structure the spacing audit (per-screen vs per-component-type)
- Order of bug fix vs UI polish work within the phase

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FIX-03 | Windows app uses ANGLE (DirectX) backend instead of OpenGL to prevent AMD GPU driver crashes during sustained plot redraws | Code already at main.py:265-269; needs startup log line + 30-min AMD hardware test |
| FIX-04 | MG reader handles use `--direct --subscribe MG` on all platforms — controller log receives messages on both Windows and Pi | mg_reader.py:252 has Linux platform guard; research-dependent on gclib Linux capability |
| FIX-05 | Pi install.sh rsync excludes `venv/` directory to prevent destroying existing venv on re-installs | Already implemented at install.sh:211 and :226; needs re-run verification test on Pi |
| UI-01 | Touch targets verified at minimum 44dp across all screens on 15" display preset | Audit all interactive elements in 21 KV files; remove 7"/10" presets; fix any below 44dp |
| UI-02 | Layout consistency pass — alignment, spacing, and card sizing uniform across Run, Setup, Parameters, and Profiles screens | Standardize all padding/spacing in all KV files to 4/8/12/16/24dp token scale |
</phase_requirements>

## Summary

Phase 31 is primarily a verify-and-close phase for two bug fixes (ANGLE backend, venv rsync) and an implementation phase for one research-dependent fix (MG reader on Linux) plus a systematic UI token standardization pass across all 21 KV files.

The ANGLE backend fix (FIX-03) is already implemented in `main.py:265-269` — the only work is adding a startup log confirmation line and running the 30-minute AMD hardware test. The venv fix (FIX-05) is already implemented in `deploy/pi/install.sh:211` — the only work is verifying the rsync exclude path is correct and running a re-install test on the Pi.

The MG reader fix (FIX-04) has a platform guard at `mg_reader.py:252` that blocks Linux. The code already handles the non-`--direct` fallback path for Linux (line 201: `_direct = " --direct" if _sys.platform == "win32" else ""`), so the only question is whether `--subscribe MG` itself works on Linux gclib. If yes, remove the early-return guard; if no, document Windows-only.

The UI work (UI-01, UI-02) is systematic but straightforward: audit the 21 KV files for spacing/padding values, map everything to the 4/8/12/16/24dp token scale, check all interactive elements against the 44dp minimum, and remove the dead 7"/10" preset code from `main.py`.

**Primary recommendation:** Execute in order — bug fixes first (verifiable in hours), then 7"/10" preset removal, then spacing token audit. This ordering lets hardware tests run while the UI work proceeds in parallel.

## Standard Stack

### Core (already in use — no new installs needed)

| Component | Version/Path | Purpose | Notes |
|-----------|-------------|---------|-------|
| Kivy KV language | existing | UI layout and styling | All changes are .kv file edits |
| `main.py` pre-Kivy block | lines 100-299 | Display preset + ANGLE config | Remove 7"/10" presets, add GL log |
| `mg_reader.py` | `src/dmccodegui/hmi/mg_reader.py` | MG message subscription | Platform guard at line 252 |
| `install.sh` | `deploy/pi/install.sh` | Pi deployment | venv exclude at line 211 |
| pytest | existing (519 tests) | Test suite | `python -m pytest tests/ -q` |

### No New Dependencies

This phase introduces zero new libraries. All work is code modification and verification of existing implementations.

## Architecture Patterns

### Existing KV Spacing Values (Inventory)

Spacing values found across KV files before standardization:

| Value | Locations | Token Mapping |
|-------|-----------|--------------|
| `'2dp'` | tab_bar.kv (spacing, padding), run.kv (spacing) | Map to `4dp` (round up) |
| `'3dp'` | run.kv (delta_c_panel spacing) | Map to `4dp` |
| `'4dp'` | run.kv, theme.kv (HControl spacing) | Keep as `4dp` |
| `'6dp'` | status_bar.kv (padding/spacing), run.kv right col spacing | Map to `8dp` |
| `'8dp'` | run.kv (main padding, spacing), setup.kv, parameters.kv | Keep as `8dp` |
| `'10dp'` | theme.kv CardFrame padding/spacing, axes_setup.kv | Map to `8dp` or `12dp` |
| `'12dp'` | parameters.kv, profiles.kv, axes_setup.kv | Keep as `12dp` |
| `'16dp'` | profiles.kv, axes_setup.kv | Keep as `16dp` |
| `'20dp'` | profiles.kv, axes_setup.kv save button | Map to `24dp` |
| `'24dp'` | profiles.kv | Keep as `24dp` |
| `'40dp'` | profiles.kv (main content spacing) | Non-standard — evaluate vs 24dp |
| `'14dp'` | users.kv | Map to `16dp` |

### Fixed-Height Chrome Elements (must not shift between tabs)

These are verified to be fixed-height and should remain stable:

| Element | Height | File |
|---------|--------|------|
| StatusBar | `64dp` | base.kv + status_bar.kv |
| TabBar | `64dp` | base.kv + tab_bar.kv |
| TabBar padding | `2dp` each side | tab_bar.kv |

Total chrome height: 128dp. Screen content area = window height - 128dp.

### Interactive Element Size Audit (44dp minimum)

Elements found in the code with their current sizes:

| Element | Current Size | Compliant? | File |
|---------|-------------|------------|------|
| StatusBar buttons (E-STOP, RECOVER, theme toggle) | `56dp` height | YES | status_bar.kv |
| Machine type button | `56dp` height | YES | status_bar.kv |
| TabBar buttons | inherits `64dp` height | YES | tab_bar.kv |
| Parameters "Read" button | `44dp` height | YES (at limit) | parameters.kv, flat_grind/parameters.kv |
| Parameters "Apply" button | `44dp` height | YES (at limit) | parameters.kv |
| Bottom action bar buttons (Start, Stop) | `72dp` height | YES | run.kv |
| Jog << >> buttons | `56dp` x `72dp` | YES | axes_setup.kv |
| Step toggle buttons (10/5/1) | `60dp` width, inherits `48dp` height | YES | axes_setup.kv |
| Mode toggle buttons (SetRest/SetStart) | inherits `64dp` top bar | YES | axes_setup.kv |
| Profiles Export/Import buttons | `64dp` height | YES | profiles.kv |
| Setup.kv connect/refresh rows | `44dp` height | YES (at limit) | setup.kv |
| addr_list rows | `36dp` height | **BORDERLINE** — below 44dp | setup.kv |
| Delta-C +/- section count buttons | `24dp` wide | **SMALL** — needs audit | run.kv |
| Delta-C up/down arrow buttons | `28dp` height | **BELOW 44dp** | run.kv |
| CardFrame inner controls row | `30dp` height (controls row) | **BELOW 44dp** | run.kv |
| bComp +/- buttons | full-width with `size_hint_x: 0.2` | needs measurement | run.kv |
| Stone comp less/more stone | `40dp` height | **BELOW 44dp** | run.kv |

### Display Preset Removal Pattern

Files affected by removing 7"/10" presets:

1. `main.py` — `_DISPLAY_PRESETS` dict (remove `7inch` and `10inch` keys), `_classify_resolution()` function (simplify — only returns `15inch`), `_detect_preset()` (simplify valid presets set)
2. `tests/test_display_preset.py` — `TestClassifyResolution.test_classify_7inch`, `test_classify_10inch`, `TestDetectPreset.test_override_valid` (7inch case) — these tests must be updated to match the new behavior

### MG Reader Platform Guard

Current code at `mg_reader.py:252`:
```python
def start(self, address: str) -> None:
    if _sys.platform != "win32":
        logger.info("MgReader disabled on Linux (gclib MG subscription not supported)")
        return
```

Current code at `mg_reader.py:201` (inside `_loop`):
```python
_direct = " --direct" if _sys.platform == "win32" else ""
connection_string = f"{address}{_direct} --subscribe MG --timeout 500"
```

The `--direct` flag difference is already handled. The open question is whether `GOpen` with `--subscribe MG` (without `--direct`) succeeds on Linux gclib. If it does, only the `start()` early-return guard at line 252 needs to be removed.

### ANGLE Backend Log Line Location

Current code at `main.py:265-269`:
```python
if sys.platform == "win32":
    os.environ.setdefault("KIVY_GL_BACKEND", "angle_sdl2")
```

The log line should be added immediately after this block, reading the environment variable back to confirm what was set. The log call must use `_log` (the module-level logger defined at line 256) and must come after `setup_logging()` (line 251). The `os.environ.setdefault` pattern means if `KIVY_GL_BACKEND` was already set externally, the log should reflect the actual value, not assume `angle_sdl2`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Spacing token enforcement | Manual search-replace | Grep by pattern + systematic edit | KV files are static; grep for all `Ndp` patterns then remap in one pass |
| 44dp measurement | Runtime instrumentation code | Static analysis of KV height: lines | All sizes are hardcoded in dp — readable directly from KV |
| GL backend detection at startup | Custom Kivy introspection | Read `os.environ["KIVY_GL_BACKEND"]` back after setting it | setdefault already stores the value |

## Common Pitfalls

### Pitfall 1: rsync venv exclude path sensitivity
**What goes wrong:** rsync `--exclude='venv/'` with a trailing slash excludes the `venv` directory inside the source root. If the `venv/` directory is at `INSTALL_DIR/venv` and `rsync` source is `"$SCRIPT_DIR/../../"`, the exclude must match the path relative to the rsync source root, not the destination.
**Why it happens:** rsync processes excludes relative to the transfer root. `--exclude='venv/'` matches any `venv/` directory at any depth in the source tree.
**How to avoid:** The current exclude at install.sh:211 is `--exclude='venv/'` — this correctly excludes any `venv/` directory. Verify by dry-run (`rsync -n`) on a Pi that already has a venv. Confirm `$INSTALL_DIR/venv` is not wiped.
**Warning signs:** Log shows "Venv already exists" but the directory is empty or pip packages are gone after re-run.

### Pitfall 2: Kivy dp() vs string literal 'Ndp' inconsistency
**What goes wrong:** KV files use both `'8dp'` string literals and Python `dp(8)` function calls. Only string literals with the dp suffix are valid in KV language property values. `dp(8)` is only valid in Python expressions within KV (e.g., `height: dp(8)` in a canvas block or `size: dp(5), dp(56)` in Widget).
**How to avoid:** When standardizing spacing tokens, leave `dp()` function call usages (in canvas instructions) unchanged. Only touch string literal `'Ndp'` padding and spacing properties.
**Warning signs:** Kivy throws a parse error or runtime exception on token sizes that use `dp()` in a KV property value position.

### Pitfall 3: Removing 7"/10" presets breaks existing tests
**What goes wrong:** `test_display_preset.py` has tests for `test_classify_7inch` and `test_classify_10inch` that will fail once the presets are removed, and for the `test_override_valid` test with `'7inch'` as the value.
**How to avoid:** Update `test_display_preset.py` in the same plan task that removes the presets. The 7"/10" test cases should be replaced with tests that verify invalid values return `'15inch'`.
**Warning signs:** CI shows 3 test failures in `test_display_preset.py` after preset removal without corresponding test updates.

### Pitfall 4: `os.environ.setdefault` vs forced set for ANGLE log
**What goes wrong:** If `KIVY_GL_BACKEND` is already set in the environment (e.g., a developer has it set manually), `setdefault` does not overwrite it. A log line that says "angle_sdl2 active" when a different backend is actually in use is misleading.
**How to avoid:** Log `os.environ.get("KIVY_GL_BACKEND", "default")` after the setdefault block, not the hardcoded string `"angle_sdl2"`. This reflects whatever value is actually active.

### Pitfall 5: MG reader test mocking runs on `sys.platform == "win32"` branch
**What goes wrong:** `tests/test_mg_reader.py` `TestMgHandleTimeout.test_loop_opens_handle_with_correct_string` asserts `"--direct" in gopen_arg`. This test runs on the developer's machine (Windows) and passes because the Windows branch adds `--direct`. If the Linux platform guard is removed, the test must also verify the non-`--direct` connection string is valid on Linux — but test_mg_reader.py currently patches platform at the `_loop` level, not at `start()`.
**How to avoid:** If the Linux guard is removed, update `TestStartStop` to verify `start()` does not early-return on Linux by patching `sys.platform`. The `_loop` tests already work because they test `_loop` directly, bypassing the `start()` platform guard.

### Pitfall 6: Layout shifts from non-tokenized padding in inherited screen chrome
**What goes wrong:** Profiles screen has `padding: '40dp'` on its main content BoxLayout, which is much larger than the 24dp maximum token. If this is changed to `24dp` during standardization, the content position shifts visually.
**How to avoid:** The profiles main content area uses proportional spacers (`Widget: size_hint_y: 0.1`) around buttons. Changing padding from 40dp to 24dp will reflow the layout. Evaluate whether the 40dp was intentional for the sparse profiles layout — if the visual result is better with 24dp, apply; if it causes layout regression, keep 40dp but document as an accepted deviation.

## Code Examples

### ANGLE Backend Log Line Pattern

```python
# Source: main.py:265-269 (existing code to augment)
if sys.platform == "win32":
    os.environ.setdefault("KIVY_GL_BACKEND", "angle_sdl2")
# Add this line immediately after:
_log.info("GL backend: %s", os.environ.get("KIVY_GL_BACKEND", "default (platform gl)"))
```

### MG Reader Guard Removal

```python
# Source: mg_reader.py:252 (current — Linux early-return guard)
# BEFORE (current):
if _sys.platform != "win32":
    logger.info("MgReader disabled on Linux (gclib MG subscription not supported)")
    return

# AFTER (if Linux gclib supports --subscribe MG):
# Remove the above block entirely. The _loop already handles non---direct correctly:
# _direct = " --direct" if _sys.platform == "win32" else ""
```

### Spacing Token Audit Grep Patterns

```bash
# Find all non-token dp values in KV files:
grep -rn "'[0-9]\+dp'" src/dmccodegui/ui/ | grep -v "'4dp'\|'8dp'\|'12dp'\|'16dp'\|'24dp'\|'64dp'\|'56dp'\|'44dp'\|'72dp'\|'80dp'"
```

Fixed-height structural elements (64dp for chrome bars, 56/72/80dp for interactive controls) are exempt from the token scale — they are intentional sizing choices, not spacing values. Only `padding` and `spacing` KV properties need to map to the token scale.

### Display Preset Simplification

```python
# Source: main.py (after removing 7"/10" presets)
# _DISPLAY_PRESETS becomes a single-entry dict:
_DISPLAY_PRESETS: dict[str, dict] = {
    "15inch": {
        "density": "1",
        "width": 1920,
        "height": 1080,
        "fullscreen_mode": "0",
        "borderless": "0",
        "maximized": "1",
        "resizable": "1",
    },
}

# _classify_resolution() simplifies to always return '15inch'.
# _detect_preset() _valid_presets set shrinks to {'15inch'}.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mixed spacing values (2/3/6/10/14/20/40dp) | Token scale (4/8/12/16/24dp) | Phase 31 | Visual consistency across all screens |
| All 3 display presets (7/10/15") | 15" only | Phase 31 | Removes dead code; simplifies main.py and tests |
| MG reader Windows-only | MG reader on all platforms (pending research) | Phase 31 | Controller log populated on Pi |
| ANGLE set silently | ANGLE set + logged | Phase 31 | App log confirms GPU backend at startup |

## Open Questions

1. **Does gclib on Linux support `--subscribe MG` without `--direct`?**
   - What we know: The `_loop` code already uses `_direct = " --direct" if sys.platform == "win32" else ""`, meaning a non-`--direct` connection string is already constructed for Linux. The `GOpen` call then passes `"{address} --subscribe MG --timeout 500"` (no `--direct`) on Linux.
   - What's unclear: Whether Galil's Linux gclib implementation supports the `--subscribe MG` flag at all. This is a gclib-version-specific question that requires a live Pi test.
   - Recommendation: Plan task should be "try it on Pi hardware; if it works, remove the line 252 guard; if GOpen fails, revert and document Windows-only." The implementation path (removing line 252) is a 1-line change either way.

2. **Which small delta-C/bComp controls need 44dp remediation?**
   - What we know: `run.kv` delta_c_panel has buttons at `28dp` height (up/down arrows) and section count +/- buttons at `24dp` width. Stone comp buttons are `40dp`. These are below the 44dp minimum.
   - What's unclear: Whether increasing these sizes will fit within the `185dp` delta_c_panel height constraint.
   - Recommendation: Increase the delta_c_panel height to accommodate larger buttons (e.g., from 185dp to 200dp) rather than squeezing small buttons into the fixed height. The panel's `size_hint_y: None` height is a hardcoded constraint — it can be adjusted.

3. **Are spacing values in `profiles.kv` (40dp padding, 20dp spacing) intentional design or oversight?**
   - What we know: The profiles screen uses `padding: '40dp'` and `spacing: '20dp'` in the main content BoxLayout, far outside the 4/8/12/16/24dp token scale.
   - What's unclear: Visual intent — the profiles screen is sparse (2 large buttons) so extra whitespace may be intentional.
   - Recommendation: Map `40dp` → `24dp` and `20dp` → `16dp` during the audit, then visually verify. If the screen looks correct, keep the change. If it looks cramped, revert to 24dp as the ceiling and document.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (519 tests collected) |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `python -m pytest tests/test_mg_reader.py tests/test_display_preset.py tests/test_install_pi.py -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FIX-03 | ANGLE backend env var set on Windows | unit | `python -m pytest tests/test_main.py -k angle -q` | needs new test |
| FIX-03 | GL backend log line emitted at startup | unit | `python -m pytest tests/test_main.py -k gl_backend -q` | needs new test |
| FIX-03 | 30-min AMD hardware soak | manual | n/a — hardware required | manual-only |
| FIX-04 | MG reader start() does not early-return on Linux | unit | `python -m pytest tests/test_mg_reader.py -k linux -q` | needs new test if guard removed |
| FIX-04 | Live Pi MG subscription produces log messages | manual | n/a — Pi hardware required | manual-only |
| FIX-05 | install.sh rsync excludes venv/ | unit (content inspection) | `python -m pytest tests/test_install_pi.py -k venv -q` | exists (line 155) |
| FIX-05 | Re-install on Pi with existing venv preserves packages | manual | n/a — Pi hardware required | manual-only |
| UI-01 | All interactive elements >= 44dp | manual | n/a — visual inspection required | manual-only |
| UI-01 | 7"/10" presets removed from _DISPLAY_PRESETS | unit | `python -m pytest tests/test_display_preset.py -q` | exists — needs update |
| UI-02 | Spacing values map to token scale | manual | grep-based check | manual-only |
| UI-02 | Tab switching produces no visual jump | manual | n/a — visual inspection required | manual-only |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_mg_reader.py tests/test_display_preset.py tests/test_install_pi.py -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_main.py` needs `test_angle_backend_env_set` — verifies `KIVY_GL_BACKEND=angle_sdl2` is set on `win32` platform
- [ ] `tests/test_main.py` needs `test_gl_backend_log_line` — verifies `_log.info("GL backend: ...")` is emitted at startup
- [ ] `tests/test_mg_reader.py` needs `TestStartStop::test_start_not_blocked_on_linux` — verifies `start()` does not early-return when platform guard is removed (conditional: only write this test if the guard is actually removed)
- [ ] `tests/test_display_preset.py` — existing `test_classify_7inch`, `test_classify_10inch`, and `test_override_valid("7inch")` must be updated to reflect preset removal

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `src/dmccodegui/main.py` lines 100-299 — display presets, ANGLE backend code, _detect_preset function
- Direct code inspection: `src/dmccodegui/hmi/mg_reader.py` — full MgReader class, platform guard at line 252, _loop connection string at line 201
- Direct code inspection: `deploy/pi/install.sh` lines 196-260 — rsync exclude at line 211, venv existence check at line 226
- Direct code inspection: All 21 `.kv` files in `src/dmccodegui/ui/` — spacing/padding inventory
- Direct code inspection: `tests/` directory — 519 tests, confirmed passing subset (53 tests in 3 relevant files)

### Secondary (MEDIUM confidence)

- gclib Linux MG subscription capability: NOT verified — requires live Pi test. The code already handles the non-`--direct` path (mg_reader.py:201), but whether `--subscribe MG` succeeds on Linux is unknown from code inspection alone.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Bug fix verification (FIX-03, FIX-05): HIGH — code is present and inspected; the work is adding log lines and running existing tests
- MG reader Pi support (FIX-04): MEDIUM — code path exists but Linux gclib compatibility requires hardware confirmation
- UI token standardization (UI-01, UI-02): HIGH — all KV files inspected, all spacing values catalogued, non-compliant elements identified
- Preset removal (UI-01 scope): HIGH — all affected code locations identified including test files that need updating

**Research date:** 2026-05-04
**Valid until:** 2026-06-04 (stable codebase — no fast-moving dependencies)
