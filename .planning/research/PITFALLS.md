# Domain Pitfalls

**Domain:** Industrial touchscreen GUI — Kivy/Python knife grinding machine control
**Researched:** 2026-04-04
**Confidence note:** Web tools unavailable during research. All findings derived from codebase analysis + training knowledge. Confidence levels are honest about this constraint.

---

## Critical Pitfalls

Mistakes that cause rewrites, safety incidents, or blocked deployments.

---

### Pitfall 1: Matplotlib Draws Called from the Background Thread

**What goes wrong:** `FigureCanvasKivyAgg` and matplotlib itself are not thread-safe. If the live position poll calls `ax.plot()`, `ax.set_data()`, or `canvas.draw()` from a `jobs.submit()` background thread, you get intermittent crashes, a blank plot, or a segfault on Pi — with no obvious traceback.

**Why it happens:** The existing threading model correctly posts all UI mutations back via `Clock.schedule_once`. A developer adding the live plot is tempted to update it inside the background polling function because it "feels like data, not UI." It is both — matplotlib's draw pipeline touches OpenGL/SDL2 resources owned by the Kivy main thread.

**Consequences:**
- Silent crashes on Pi (SIGABRT from SDL2)
- Plot renders blank or frozen while data accumulates in the background
- Race conditions that only appear under load (fast poll rates, Pi GPU memory pressure)

**Warning signs:**
- Plot works on Windows but crashes intermittently on Pi
- `canvas.draw()` called anywhere outside a `Clock.schedule_once` callback
- A background thread holds a reference to the `Figure` or `Axes` object

**Prevention:**
- All matplotlib calls (`ax.set_data`, `ax.relim`, `ax.autoscale`, `canvas.draw`) must execute on the Kivy main thread
- Pattern: background thread collects `(x, y)` tuple → posts to main thread via `Clock.schedule_once` → main thread updates plot
- Never pass the `Figure` or `Axes` object to a background thread

**Phase that should address this:** RUN page / live plot implementation phase — establish the pattern on day one.

**Confidence:** HIGH (Kivy's thread model is well-documented; matplotlib GL backends are single-threaded)

---

### Pitfall 2: Matplotlib Redraws Block the UI Thread at High Poll Rates

**What goes wrong:** `canvas.draw()` is synchronous and expensive. At 10+ Hz polling, each full redraw blocks the Kivy event loop long enough to make touch input feel laggy or miss E-STOP taps. On a Pi 4 with the default software renderer, a full matplotlib redraw of a scatter/line plot takes 30–120 ms.

**Why it happens:** The simplest implementation calls `canvas.draw()` every poll cycle. This is correct for correctness but destroys UI responsiveness on underpowered hardware.

**Consequences:**
- E-STOP button takes 200–500 ms to respond — unacceptable for a machine control panel
- Kivy's touch dispatching starves; buttons appear to not respond to taps
- Operators report "the screen is frozen" when the grind cycle is running

**Warning signs:**
- `canvas.draw()` called more than 5 times per second
- No rate limiting or dirty-flag on the plot update
- Plot refreshes even when axis positions haven't changed

**Prevention:**
- Use `canvas.draw_idle()` instead of `canvas.draw()` — lets Kivy coalesce redraws
- Or use `blit` animation: update `line.set_data()` only, then `ax.draw_artist(line)` + `canvas.blit(ax.bbox)` — 5–10x faster than full redraw
- Rate-limit plot updates to 5–10 Hz regardless of poll rate (the controller poll can remain faster; the plot update is decoupled)
- On Pi, test at target poll rate before finalising the plot implementation

**Phase that should address this:** RUN page phase — requires explicit performance testing on Pi before sign-off.

**Confidence:** HIGH (Pi GPU limitations for software-rendered matplotlib are well-documented in the Kivy community)

---

### Pitfall 3: PIN Auth State Lives Only in Memory — Clears on Screen Navigation

**What goes wrong:** If the role/session is stored as a plain Python attribute on a Screen object, it is reset whenever that screen is destroyed or recreated. Kivy's ScreenManager can destroy screens on transition (depending on configuration). Worse, a hard-coded check like `if self.current_role == 'setup':` in a screen's `on_pre_enter` silently locks out the Setup person because the role reset between screens.

**Why it happens:** Developers put auth state in the screen class (which feels natural) rather than in `MachineState` (which persists across screen transitions).

**Consequences:**
- Setup role silently reverts to Operator mid-session without any indication
- Admin changes are "forgotten" when navigating away from the user management screen
- Auth bypasses become possible if role is checked inconsistently across screens

**Warning signs:**
- `self.current_role` or `self.logged_in_user` attributes on individual Screen subclasses
- Role check duplicated in multiple screens rather than centralised in `MachineState`
- No test covering "navigate away and back while Setup role is active"

**Prevention:**
- Store the entire session (current user, role, PIN-unlock timestamp) in `MachineState`
- A single `state.current_role` property is the source of truth; screens read from it, never own it
- Re-lock logic (timeout after N minutes of Setup role) must be a Clock-scheduled callback on `MachineState`, not on any Screen

**Phase that should address this:** PIN auth / user roles phase — must be the first thing established before any role-gated UI is built.

**Confidence:** HIGH (this is a direct consequence of Kivy's object lifecycle and the existing MachineState pattern)

---

### Pitfall 4: CSV Profile Import Overwrites Live Controller State Without Confirmation

**What goes wrong:** Loading a CSV profile triggers `download_array` calls for every variable in the file. If an operator accidentally taps "Load Profile" mid-cycle, the running DMC program's parameters are overwritten while the machine is in motion. The Galil controller does not queue writes — the array changes take effect immediately.

**Why it happens:** The CSV load function is simple to write — read file, iterate rows, call `download_array`. The safety interlock (are we currently running?) is an afterthought.

**Consequences:**
- Machine moves to unexpected positions mid-grind
- Knife or tooling damage
- Potentially physical injury

**Warning signs:**
- `download_array` called from the CSV load handler without checking `state.running`
- No confirmation dialog before applying a profile
- Profile load accessible to the Operator role (should be Setup-only)

**Prevention:**
- Profile import must be gated behind: (1) Setup role, AND (2) machine not running (`state.running == False`)
- Show a confirmation dialog with the profile name before any writes begin
- Consider dry-run display: show a diff of what will change before committing
- The load function must check `state.running` inside the background job, not just in the UI handler (race condition possible between the UI check and the first `download_array` call)

**Phase that should address this:** CSV profile phase — safety interlock must be part of the initial implementation, not a later addition.

**Confidence:** HIGH (this is a fundamental motion control safety concern; the pattern is identical across all industrial GUI systems)

---

### Pitfall 5: Raspberry Pi Kiosk Mode Does Not Prevent Operator Access to Desktop

**What goes wrong:** A common Pi kiosk setup uses `@reboot` cron or a `.desktop` autostart entry to launch the app in fullscreen. The operator can still press `Ctrl+Alt+T` to open a terminal, right-click for a file manager, or use the Pi's task switcher. On Pi OS (Bookworm), the Wayland compositor's keyboard shortcuts are not blocked by the app going fullscreen.

**Why it happens:** "Fullscreen" in Kivy does not mean "locked kiosk." It just maximizes the window. The underlying desktop environment is still fully accessible.

**Consequences:**
- Operators access the file system, edit CSV profiles manually, or modify app config
- Kivy config file (`~/.kivy/config.ini`) becomes accessible and editable
- Security policy violated even though PIN auth works at the app level

**Warning signs:**
- App launched via cron or `.desktop` file without also disabling the desktop environment
- Using `Config.set('graphics', 'fullscreen', 'auto')` but not locking out the WM
- No test of "operator tries keyboard shortcuts while app is running"

**Prevention:**
- For true kiosk on Pi OS (Bookworm + Wayland): use a dedicated minimal session that launches the app as the only process — see `raspi-config` → Boot → Desktop / CLI → Console Autologin, then a `~/.bashrc` script that launches Kivy directly
- For Pi OS (Legacy, X11): use `matchbox-window-manager` or `openbox` in kiosk mode, disable right-click context menus via `.Xdefaults`
- Disable virtual keyboard shortcuts: `xdotool` or compositor config to remove `Ctrl+Alt+T`
- The app's `Config.set('graphics', 'fullscreen', 'auto')` must be set before any Window import; order matters (this is already partially handled in `main.py` but needs verification on Pi)
- Test kiosk lockout explicitly before shipping; it cannot be retrofitted from the mockup phase

**Phase that should address this:** Pi kiosk / deployment phase — requires dedicated Pi hardware testing, not just code changes.

**Confidence:** MEDIUM (Pi OS Bookworm/Wayland is relatively new; exact lockout procedure depends on Pi OS version at deploy time. Verify against the target Pi OS image.)

---

## Moderate Pitfalls

---

### Pitfall 6: `FigureCanvasKivyAgg` Added via `kivy_matplotlib_backend` — Import Order Breaks Kivy Startup

**What goes wrong:** `kivy_matplotlib_backend` (the community package for `FigureCanvasKivyAgg`) must be imported **after** `kivy.app` is imported but **before** `App.run()` is called. Importing it at module level in a screen file (which is imported at app startup) can trigger a premature OpenGL context initialization and crash on Pi or produce a blank window on Windows.

**Why it happens:** `matplotlib.use('module://kivy_matplotlib_backend.backend_kivyagg')` is a global matplotlib state call. If it runs before Kivy's Window is initialized, the backend has no context to attach to.

**Warning signs:**
- `import matplotlib` at the top of a screen `.py` file
- `matplotlib.use(...)` called before `DMCApp().run()`
- Blank or gray window on first launch that disappears on the second run

**Prevention:**
- Import matplotlib and set the backend lazily — only when the RUN screen is first entered (`on_kv_post` or `on_pre_enter`)
- Or import in `main.py` after `from kivy.app import App` but before `DMCApp().run()`
- Keep `matplotlib.use('module://kivy_matplotlib_backend.backend_kivyagg')` in exactly one place; calling it twice raises an error

**Phase that should address this:** RUN page phase — establish import pattern in the initial matplotlib integration PR.

**Confidence:** MEDIUM (training knowledge; verify with the actual `kivy_matplotlib_backend` package docs at integration time)

---

### Pitfall 7: Role-Gated UI Elements Hidden via `opacity: 0` Remain Tappable

**What goes wrong:** A common Kivy pattern to hide a widget is `opacity: 0` or `disabled: True`. Setting `opacity: 0` makes the widget invisible but does NOT remove it from the touch dispatch tree. An Operator could tap a "hidden" Setup button by tapping its approximate screen position.

**Why it happens:** Kivy's `opacity` property is a visual-only change. Touch events still hit the widget unless `disabled: True` is also set, or the widget is removed from the layout, or `size_hint: None, None; size: 0, 0` is applied.

**Warning signs:**
- Role-gated widgets controlled only by `opacity` binding in KV
- No test of "Operator tries to activate Setup controls by tapping their location"

**Prevention:**
- Use `disabled: state.current_role not in ('setup', 'admin')` alongside opacity for all role-gated widgets
- Or use a `size_hint: (0, 0) if not visible else (1, 1)` pattern to collapse the widget entirely
- The safest pattern: wrap role-gated sections in a parent widget with `size_hint_y: 0` when locked, so they consume no touch space

**Phase that should address this:** PIN auth / role UI phase.

**Confidence:** HIGH (this is documented Kivy behavior — opacity does not affect touch)

---

### Pitfall 8: CSV Profile Contains Stale or Wrong Array Lengths for This Machine Type

**What goes wrong:** A profile CSV exported from a 4-axis Flat Grind machine is imported on a 3-axis Serration machine. The CSV contains DMC array entries for axis D that do not exist on the 3-axis machine. `download_array` for a non-existent array name returns a Galil error code 57 ("Bad function or array"), but if this is silently swallowed, the rest of the profile is still applied — leaving the machine in a half-loaded state.

**Why it happens:** The CSV format has no machine-type header. The import function iterates all rows and calls `download_array` for each, catching exceptions per-row without aborting the batch.

**Warning signs:**
- CSV importer catches exceptions per row and continues
- No machine-type validation at the start of import
- Profile exported on one machine type, imported on another without warning

**Prevention:**
- Add a `machine_type` header row to the CSV format (e.g., `# machine_type=FlatGrind4Axis`)
- Validate at import time: if CSV machine type != current machine type, show a warning and require explicit confirmation before proceeding
- Import is all-or-nothing: if any `download_array` call fails, roll back (re-upload original values) rather than leaving a partial state
- Log every array name that was written vs skipped so the operator can review

**Phase that should address this:** CSV profile phase.

**Confidence:** HIGH (this is a direct consequence of the multi-machine-type requirement stated in PROJECT.md)

---

### Pitfall 9: Shared `RestPnt` Array Used by Two Different Screens for Different Data

**What goes wrong:** Both `axisDSetup.py` and `parameters_setup.py` read/write `RestPnt[0..2]`. `axisDSetup.py` treats indices 0–2 as D-axis angle positions. `parameters_setup.py` treats the same indices as A/B/C rest positions. This is explicitly noted as a known issue in `axisDSetup.py`:

> "NOTE: This screen shares the 'RestPnt' array with rest.py (A/B/C rest points). If the two screens need to be independent in the future, allocate a separate 'DAxisPnt' array."

Adding CSV export now will snapshot this ambiguous state. Adding CSV import will restore it — but restoring `RestPnt[0]` on a 3-axis machine that interprets it as D Zero will corrupt A-axis rest position.

**Why it happens:** The array collision is already present in the codebase. CSV profiles will expose it by making the ambiguity portable across machines and sessions.

**Warning signs:**
- `RestPnt` read/written from more than one screen with different semantic interpretations
- CSV row for `RestPnt` without axis-semantic documentation

**Prevention:**
- Resolve the array naming collision before implementing CSV profiles — allocate `DAxisPnt` for the D-axis screen as the existing code comment suggests
- Document each DMC array's semantic meaning in the CSV format (column headers)
- This is a pre-requisite for CSV profiles, not a follow-up task

**Phase that should address this:** This must be resolved in an early cleanup phase before CSV profile work begins.

**Confidence:** HIGH (directly observed in the existing codebase)

---

### Pitfall 10: `on_pre_enter` Controller Reads Run on the Main Thread

**What goes wrong:** Both `axisDSetup.py` and `parameters_setup.py` call `self.controller.upload_array(...)` directly in `on_pre_enter`, which runs on the Kivy main thread. For short arrays this works. For the CSV profile load (which reads all parameters — potentially dozens of arrays), this will freeze the UI for the duration of the read.

**Why it happens:** `upload_array` is synchronous and the small-array case is fast enough on current screens that the freeze is not noticeable. CSV profile export reads many more arrays.

**Warning signs:**
- `self.controller.upload_array(...)` called directly in `on_pre_enter`, `on_kv_post`, or any KV event callback
- No `jobs.submit()` wrapping controller reads in the Parameters or profile screens

**Prevention:**
- All multi-array reads (parameter page population, CSV export) must go through `jobs.submit()`
- Show a "Loading..." spinner in the UI between the submit and the `Clock.schedule_once` callback
- The existing threading pattern in `setup.py` is the correct model — follow it exactly for any new multi-read operations

**Phase that should address this:** Parameters setup refactor phase; CSV profile phase.

**Confidence:** HIGH (directly observed in codebase; the pattern diverges from `setup.py`'s correct threading model)

---

### Pitfall 11: Controller Injection Happens After KV Build — Screens Have `None` Controller at Init

**What goes wrong:** `main.py` injects `controller` and `state` into screens after `Factory.RootLayout()` builds all screens. Any screen code that runs during `__init__` or early KV events (before injection) will have `controller = None`. The current code guards against this with `if not self.controller or not self.controller.is_connected()` checks, which is correct. But new screens (run page, user management) added without this guard will crash on first navigation with `AttributeError: 'NoneType' object has no attribute 'is_connected'`.

**Why it happens:** New developer adds a screen, copies an existing screen's class, adds a controller call in `on_kv_post` without the None guard — works in dev (controller is fast to inject) but fails on Pi where the sequence timing differs.

**Warning signs:**
- Controller calls in `__init__`, `on_kv_post`, or class-level attribute initializers without None guard
- New screen added to `base.kv` but not to the injection loop in `main.py`

**Prevention:**
- Keep the `if not self.controller:` guard as a team convention; add it to a shared base Screen class if possible
- Add new screens to the injection loop in `main.py` explicitly — do not rely on the `hasattr` check alone (it works but is easy to miss if the attribute name changes)
- Consider a `BaseScreen` class that raises a clear error if controller methods are called before injection

**Phase that should address this:** Every new screen addition phase.

**Confidence:** HIGH (directly observed in `main.py` injection pattern and existing screen guards)

---

## Minor Pitfalls

---

### Pitfall 12: PIN Storage in Plain Text JSON — Acceptable per Scope, but Not File-Permission-Protected

**What goes wrong:** PROJECT.md explicitly scopes out encryption ("PIN is sufficient, no encryption/hashing required for in-house use"). However, if user/PIN data is stored in a world-readable JSON file on the Pi (e.g., `~/users.json`), any operator who finds a terminal can read all PINs.

**Prevention:**
- Store the user/PIN file in the app's data directory, not in home
- Set file permissions to `chmod 600` (owner read/write only) — the app runs as a dedicated user
- This is a minor hardening step, not a blocker

**Phase that should address this:** PIN auth phase.
**Confidence:** MEDIUM

---

### Pitfall 13: Kivy `Config.set` Calls Must Precede All Kivy Imports

**What goes wrong:** `main.py` already correctly calls `Config.set` before `from kivy.core.window import Window`. Adding kiosk mode configuration (fullscreen, borderless) in a new `kiosk_config.py` module that is imported lazily will have no effect — Kivy's config is frozen on first Window import.

**Prevention:**
- All `Config.set('graphics', ...)` calls must remain at the top of `main.py`, before any other Kivy import
- Pi kiosk fullscreen must be set there, not in a Pi-detection module that loads later
- Current `main.py` already demonstrates the correct pattern; do not move these calls

**Phase that should address this:** Kiosk deployment phase.
**Confidence:** HIGH (well-documented Kivy behavior; already handled in existing main.py)

---

### Pitfall 14: Matplotlib `FigureCanvasKivyAgg` Size Does Not Respond to Kivy Layout Changes

**What goes wrong:** When the live plot widget is placed in a dynamic layout (e.g., resizable panel, orientation change), `FigureCanvasKivyAgg` does not automatically resize its internal figure. The plot renders at its original `figsize` even though the widget's Kivy dimensions changed, resulting in a mismatched aspect ratio or clipped axes.

**Prevention:**
- Bind the plot widget's `on_size` event to `fig.set_size_inches(w/dpi, h/dpi)` followed by `canvas.draw_idle()`
- Set `figure.tight_layout()` or `figure.subplots_adjust()` after resize
- On fixed-resolution kiosk (Pi touchscreen), this is less critical — but test on both 800x480 and 1920x1080

**Phase that should address this:** RUN page phase.
**Confidence:** MEDIUM (known Kivy-garden-matplotlib limitation; verify with current package version)

---

### Pitfall 15: CSV Float Precision Causes Round-Trip Mismatch with DMC Controller

**What goes wrong:** The DMC controller stores positions as 32-bit integers (encoder counts). A CSV export that formats floats as `1500.0000` and re-imports them as floats introduces floating-point round-trip errors when passed back to `download_array`. For positions this is usually harmless (1-count error). For calibration arrays with small fractional values, it can cause the machine to behave differently after a profile reload.

**Prevention:**
- For position/count values: export and import as integers
- For fractional values (e.g., speed override ratios): preserve at least 6 significant figures
- Validate that `export → import → export` produces identical CSV files before releasing the profile feature

**Phase that should address this:** CSV profile phase.
**Confidence:** MEDIUM

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| RUN page / live plot | Matplotlib updates from background thread (Pitfall 1) | Establish Clock.schedule_once pattern on day one |
| RUN page / live plot | Full redraw blocking E-STOP responsiveness on Pi (Pitfall 2) | Benchmark redraw time on Pi at 5 Hz before merging |
| RUN page / live plot | Canvas size mismatch on different Pi resolutions (Pitfall 14) | Bind on_size → fig.set_size_inches |
| PIN auth / roles | Session state in Screen object, lost on navigation (Pitfall 3) | All auth state in MachineState |
| PIN auth / roles | Hidden Setup buttons still tappable (Pitfall 7) | disabled: + opacity: together |
| CSV profiles | Missing machine-type validation (Pitfall 8) | Add machine_type header row |
| CSV profiles | Shared RestPnt array semantic collision (Pitfall 9) | Rename DAxisPnt before CSV work |
| CSV profiles | Overwrite during active cycle (Pitfall 4) | Gate on state.running check + confirmation dialog |
| CSV profiles | Main-thread freeze during multi-array export (Pitfall 10) | jobs.submit all controller reads |
| Pi kiosk | Fullscreen != locked desktop (Pitfall 5) | Use minimal console session, not just fullscreen |
| Pi kiosk | Config.set order broken by refactor (Pitfall 13) | Keep all Config.set in main.py top block |
| Any new screen | Controller is None before injection (Pitfall 11) | Guard every controller call; add to BaseScreen |

---

## Sources

- Codebase analysis: `/src/dmccodegui/` (direct code inspection, HIGH confidence)
- Kivy thread model: Kivy documentation + existing `jobs.py` pattern (HIGH confidence)
- Matplotlib thread safety: matplotlib documentation (HIGH confidence — matplotlib is documented as non-thread-safe for draw operations)
- Pi kiosk constraints: training knowledge (MEDIUM confidence — verify against target Pi OS version at deploy time)
- `kivy_matplotlib_backend` import order: training knowledge (MEDIUM confidence — verify with current package version)
