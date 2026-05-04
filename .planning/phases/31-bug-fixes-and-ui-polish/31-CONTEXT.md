# Phase 31: Bug Fixes and UI Polish - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Resolve field-identified bugs (ANGLE GPU workaround, MG reader flags, install.sh hardening) and make the UI visually consistent and touch-safe across all machine types at 1920x1080 on 15.6" displays. No new features, no new screens.

</domain>

<decisions>
## Implementation Decisions

### MG reader on Pi (FIX-04)
- Research whether gclib on Linux actually supports `--subscribe MG` (correct flags, alternative API methods)
- If Linux gclib supports it: enable MG reader on Pi (remove the platform guard at mg_reader.py:252)
- If Linux gclib cannot do MG subscription: accept Windows-only MG — controller log display is a monitoring convenience, not operator-critical
- MG messages display in the existing controller log box on the Run screen — no new UI needed
- No extra startup logging for MG reader status — current behavior is sufficient

### ANGLE GPU fix verification (FIX-03)
- Code is already implemented (main.py:265-269 sets `KIVY_GL_BACKEND=angle_sdl2` on Windows)
- PyInstaller spec already bundles `angle.dep_bins`
- Add a log line at startup confirming the active GL backend (e.g., "GL backend: angle_sdl2")
- Verify with 30-minute sustained plot redraw test on the same AMD GPU machine that originally crashed (atio6axx.dll fault)
- User has access to the original AMD hardware for testing

### install.sh venv preservation (FIX-05)
- Code is already implemented (install.sh:211 rsync excludes `venv/`, line 226 checks venv existence)
- Existing log message ("Venv already exists — skipping creation") is sufficient verification
- Verify the rsync exclude is correct and re-run test on a Pi that already has the app installed
- User has a Pi set up for testing

### Touch targets (UI-01)
- All deployment screens are 15.6" at 1920x1080 — no 7" or 10" Pi touchscreens
- Remove the 7" and 10" display presets from the code entirely
- Default to 15" 1920x1080 preset only
- Audit all interactive elements at 1920x1080 — verify every one is >= 44dp
- If any are below 44dp, increase their visual size (not invisible padding)

### Layout consistency (UI-02)
- Standardize ALL padding, spacing, and card sizing across every screen
- Fixed spacing token scale: 4dp / 8dp / 12dp / 16dp / 24dp — every padding and spacing value maps to one of these
- Card heights are content-driven (adapt to content), not uniform across screens — but consistent within each screen
- Tab bar and status bar are already fixed-height shared chrome — verify they don't shift between screens
- No visual jumps when switching tabs — common chrome alignment must be pixel-perfect
- Tab bar + header alignment, standardized spacing, and no visual jumps on tab switch — all three

### Claude's Discretion
- Exact mapping of current spacing values to the 4/8/12/16/24dp token scale
- Which elements need size increases for 44dp compliance
- How to structure the spacing audit (per-screen vs per-component-type)
- Order of bug fix vs UI polish work within the phase

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main.py:265-269`: ANGLE backend code already in place — just needs log confirmation
- `install.sh:211`: venv rsync exclude already present
- `mg_reader.py`: Full MG message subscription/dispatch architecture exists — platform guard is the only issue
- `theme.kv`: Central theme definitions for colors and base styling
- `base.kv`: Shared screen chrome (StatusBar inclusion, background)
- `tab_bar.kv`: Fixed-height tab navigation bar

### Established Patterns
- Display presets in `main.py` control resolution/density/fullscreen
- KV files use mixed padding/spacing values (8dp, 10dp, 12dp, 16dp) — need standardization to token scale
- Machine-specific screens (flat_grind/, serration/, convex/) each have their own KV files
- Shared components: `tab_bar.kv`, `status_bar.kv`, `base.kv`, `pin_overlay.kv`

### Integration Points
- `main.py` display presets — remove 7"/10" presets, keep 15" only
- All 21 `.kv` files in `src/dmccodegui/ui/` — spacing/padding audit
- `controller.py` PRIMARY_FLAGS — platform-conditional MG flags
- `mg_reader.py` platform guard — research-dependent change

</code_context>

<specifics>
## Specific Ideas

- All deployment targets are 15.6" screens at 1920x1080 — smaller presets are dead code
- ANGLE fix and venv fix are verify-and-close, not implement — code is already there
- MG reader Pi support is research-dependent: try to enable, fall back to Windows-only
- Fixed spacing tokens (4/8/12/16/24dp) apply to every KV file in the project

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 31-bug-fixes-and-ui-polish*
*Context gathered: 2026-05-04*
