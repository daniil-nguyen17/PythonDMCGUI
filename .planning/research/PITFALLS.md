# Pitfalls Research

**Domain:** Kivy HMI multi-machine screen refactor (Flat Grind → Flat + Serration + Convex)
**Researched:** 2026-04-11
**Confidence:** HIGH — derived directly from the existing codebase structure, not generic advice

---

## Critical Pitfalls

### Pitfall 1: Kivy widget ID collisions across Builder.load_file calls

**What goes wrong:**
Each per-machine .kv file defines a screen rule like `<FlatGrindRunScreen>:` with `id: status_label`, `id: plot_widget`, etc. If any two machine .kv files define the same widget `id` inside a rule that resolves to the same Python class (or if someone accidentally gives two screen rules the same name in two files), Kivy's Builder will silently use whichever rule it parsed last. The first machine's screen silently renders with the wrong widget tree — no exception is raised.

**Why it happens:**
Developers copy the Flat Grind .kv file as the starting point for Serration and Convex. Widget IDs inside a `<ScreenClassName>:` rule are scoped to the rule, so as long as class names differ, the IDs are safe. The failure mode is if someone accidentally uses the same Python class name across two .kv files (e.g., both files define `<RunScreen>:` instead of `<FlatGrindRunScreen>:` and `<SerrationRunScreen>:`). The second .kv file's rule silently replaces the first.

**How to avoid:**
- Each machine screen Python class must have a unique name: `FlatGrindRunScreen`, `SerrationRunScreen`, `ConvexRunScreen`.
- Each .kv file's root rule must match the Python class name exactly: `<FlatGrindRunScreen>:`.
- Do a grep for duplicate `<ClassName>:` lines across all .kv files after adding each new machine variant. Run this check as part of the phase completion gate.

**Warning signs:**
- A machine's screen renders content from a different machine type's layout.
- Widget properties that should differ between machines appear identical at runtime.
- Changing a widget in one .kv file silently changes another machine's screen.

**Phase to address:** Phase that extracts per-machine .kv files (the kv split phase). Add the duplicate-rule grep as a success criterion.

---

### Pitfall 2: Builder.load_file ordering — theme.kv must remain first, base.kv must remain last

**What goes wrong:**
The current `KV_FILES` list in `main.py` is ordered deliberately: `theme.kv` first (defines global style rules), then per-screen files, then `base.kv` last (defines `RootLayout` which references everything else). Adding per-machine .kv files in the wrong position — especially before `theme.kv` — causes `#:import theme` references in the new files to fail or pick up an uninitialized theme object. Inserting them after `base.kv` means `RootLayout`'s rule is already parsed and will not pick up new screen classes registered afterward.

**Why it happens:**
The load order in `main.py` looks like a flat list — easy to append to the wrong end when adding new files. `base.kv` defines `RootLayout` and its `ScreenManager` inline; any screen class that needs to appear in the `ScreenManager` must be registered (its .kv rule loaded) before `base.kv` is parsed.

**How to avoid:**
Insert per-machine .kv files between the last per-screen file and `base.kv`. The canonical insertion point is immediately before `"ui/base.kv"`. Never append new machine .kv files after `base.kv`.

Keep the load order comment in `main.py` updated:
```python
KV_FILES = [
    "ui/theme.kv",          # base styles — always first
    ...existing screens...
    "ui/flat_grind_run.kv", # machine-specific — before base.kv
    "ui/serration_run.kv",
    "ui/convex_run.kv",
    "ui/base.kv",           # RootLayout — always last
]
```

**Warning signs:**
- `NameError` or blank screens when switching to a new machine type for the first time.
- `theme` attributes read as zero/default in new machine .kv files.
- Screen appears but with unstyled widgets (theme rules missing).

**Phase to address:** Phase that wires machine screen loading. Make the ordering rule explicit in the phase spec.

---

### Pitfall 3: ScreenManager name collision — "run", "axes_setup", "parameters" are currently hardcoded everywhere

**What goes wrong:**
`main.py` hardcodes screen names as strings in at least eight places: `sm.current = 'run'`, `sm.current = 'axes_setup'`, `sm.current = 'setup'`, `TabBar.ALL_TABS` tuples, `_on_login_success` routing, `_on_idle_timeout` navigation, `disconnect_and_refresh`, and `on_stop` (the RunScreen lookup by name). When the refactor adds `FlatGrindRunScreen` with `name: 'flat_grind_run'` or keeps `name: 'run'` (but now with multiple screens competing for that name), any mismatch between what `sm.current` is set to and what the `ScreenManager` actually contains causes a silent "screen not found" — Kivy does not raise an exception, it just does nothing.

**Why it happens:**
The temptation during refactoring is to rename screen classes but keep the `name:` property the same to avoid touching `main.py`. This works for a single machine but breaks during machine-type swapping because you now have multiple screen objects that all claim `name: 'run'`. Adding all three to the same `ScreenManager` will cause the second and third additions to fail silently or overwrite the first.

**How to avoid:**
Decide upfront: either keep one `ScreenManager` with machine-specific screen names (`flat_grind_run`, `serration_run`, `convex_run`) and update all string references in `main.py`, or use a screen-set swap pattern where only the active machine's screens are present in the `ScreenManager`. Either way, create a constants module for screen name strings so `'run'` appears in exactly one place:

```python
# screen_names.py
FLAT_GRIND_RUN = "flat_grind_run"
SERRATION_RUN  = "serration_run"
CONVEX_RUN     = "convex_run"
```

**Warning signs:**
- Tapping a tab does nothing and does not navigate.
- `sm.current` is set but the visible screen does not change.
- `on_stop` fails to find the RunScreen by name, leaving background threads running on exit.

**Phase to address:** Phase that defines the screen registry/loader. This must be the first thing resolved before any .kv splitting begins.

---

### Pitfall 4: State subscription leaks when swapping screen sets

**What goes wrong:**
`MachineState.subscribe()` returns an unsubscribe callable. If a screen subscribes in `on_pre_enter` (or `__init__`) but does not call the unsubscribe callable in `on_pre_leave` (or when being removed from the ScreenManager), the listener stays in `MachineState._listeners` even after the screen is no longer displayed. When machine type changes and a different screen set is loaded, the old screens' listeners keep firing — running `Clock.schedule_once` callbacks against widgets that may no longer be in the tree, triggering Kivy property access on orphaned widget instances, and slowing down the poll loop with dead callbacks.

**Why it happens:**
The current codebase (single machine) never removes screens, so subscriptions made in `__init__` or on-enter are fine — they run for the lifetime of the app. The multi-machine refactor introduces the first case where screens are actually removed. Developers unfamiliar with the subscription pattern will add `on_pre_enter` subscriptions without symmetric `on_pre_leave` unsubscribes.

**How to avoid:**
Establish a base class `MachineScreen(Screen)` that enforces the pattern:

```python
class MachineScreen(Screen):
    def on_pre_enter(self, *args):
        self._unsub = self.state.subscribe(self._on_state_change)

    def on_pre_leave(self, *args):
        if self._unsub:
            self._unsub()
            self._unsub = None
```

All machine-variant screens inherit from this base. Never subscribe in `__init__` — subscribe only in `on_pre_enter`.

**Warning signs:**
- State change callbacks fire after navigating away from a screen.
- `AttributeError` on widget properties when the app is on a different screen (widget no longer in tree).
- Poll loop slows down as more machine types are visited.
- Increasing `len(state._listeners)` over time (add a debug log to catch this).

**Phase to address:** Phase that extracts the shared base class. This is a prerequisite for all machine-variant screen phases.

---

### Pitfall 5: Breaking existing Flat Grind behavior by touching RunScreen during base class extraction

**What goes wrong:**
`RunScreen` currently contains the matplotlib live plot, the Delta-C bar chart (`DeltaCBarChart`), the B-comp bar chart (`BCompBarChart`), the MG reader thread, the position poll thread, and their respective `_stop_*` shutdown methods. If base class extraction moves any of these into a shared parent class but the inheritance chain changes what `__init__` or `on_pre_enter` calls get made (or their order), the existing Flat Grind plot can stop updating, the poll thread can fail to start, or `on_stop` can fail to stop the thread — leaving zombie threads on exit.

**Why it happens:**
Python MRO (method resolution order) changes when you insert a base class. If `RunScreen.__init__` previously relied on `Screen.__init__` being called implicitly, inserting `MachineScreen` in the chain with its own `__init__` can skip `super().__init__()` calls if not done carefully. Also, `.kv` rules call Python class names — if `RunScreen` is renamed `FlatGrindRunScreen`, the existing `ui/run.kv` rule `<RunScreen>:` no longer matches, silently producing an unstyled screen.

**How to avoid:**
- Extract base class without renaming `RunScreen`. First create `MachineScreen(Screen)` with only the subscription pattern and shared injected properties. Then make `RunScreen(MachineScreen)` — the existing screen name and .kv rule stay untouched.
- Do the rename (RunScreen → FlatGrindRunScreen + rename `<RunScreen>:` to `<FlatGrindRunScreen>:` in the .kv file) as a separate commit after verifying Flat Grind still works.
- Test Flat Grind end-to-end (connect → poll → run cycle → E-STOP → disconnect) before merging any base class or rename work.

**Warning signs:**
- Live A/B plot stops updating after base class extraction.
- `_stop_pos_poll` or `_stop_mg_reader` not called on shutdown (zombie threads).
- Screen appears unstyled (white background, no widgets) after rename without updating .kv rule.

**Phase to address:** Flat Grind preservation phase — must be the first phase of the refactor, before any Serration or Convex work begins.

---

### Pitfall 6: machine_config coupling — screens read mc.get_axis_list() directly instead of receiving it from state

**What goes wrong:**
`AxesSetupScreen._rebuild_axis_rows()` calls `mc.get_axis_list()` directly. `RunScreen` imports `machine_config as mc` directly. If the machine type changes at runtime (operator taps the machine type picker), `mc.set_active_type()` updates the module-level config, but any screen that cached `mc.get_axis_list()` in `on_pre_enter` will still be using stale data. Per-machine screen classes that hard-code which axes they show will not notice `mc` changes at all.

**Why it happens:**
For a single machine type that never changes, direct `mc` access is fine. The multi-machine refactor makes machine type a runtime value that can change before hardware validation reveals the correct type. Screens that call `mc` functions directly bypass the `MachineState` subscription chain, so they are not notified when `state.machine_type` changes.

**How to avoid:**
Machine-variant screens should not call `mc` functions. Instead:
- `MachineState.machine_type` is the single source of truth for which machine is active.
- Each per-machine screen class is purpose-built for one machine type — it never needs to query `mc` to determine axis count. `FlatGrindAxesSetupScreen` always shows ABCD; `SerrationAxesSetupScreen` always hides D.
- The screen loader (which swaps screen sets when machine type changes) is the only layer that reads `mc`.

**Warning signs:**
- Axes Setup shows wrong axis count after switching machine type at runtime.
- D axis shown on Serration machine because `mc` returned stale type.
- Changing machine type via picker does not update currently displayed screen layout.

**Phase to address:** Machine detection and screen-swap phase. Document that per-machine screen classes must not import `machine_config`.

---

### Pitfall 7: on_stop RunScreen lookup breaks when screen name changes

**What goes wrong:**
`DMCApp.on_stop()` in `main.py` finds the RunScreen by name:
```python
run_screen = next((s for s in sm.screens if getattr(s, 'name', '') == 'run'), None)
```
If the Flat Grind run screen is renamed `flat_grind_run`, this lookup returns `None`, `_stop_pos_poll()` is never called, and the position poll thread is left running when the app closes. On Windows this is annoying (process does not exit cleanly). On Pi kiosk mode this could leave the controller in a bad state.

**Why it happens:**
The name lookup is a string literal in `on_stop` — it is not updated when screens are renamed. Easy to miss because `on_stop` is rarely tested manually.

**How to avoid:**
Replace the string lookup with a type check, or use a registry:
```python
run_screen = next(
    (s for s in sm.screens if isinstance(s, (FlatGrindRunScreen, SerrationRunScreen, ConvexRunScreen))),
    None
)
```
Or have each active run screen register itself with the app at `on_pre_enter`.

**Warning signs:**
- App takes unusually long to exit (thread blocking shutdown).
- No `[pos_poll] stopped` log line on exit.

**Phase to address:** Screen registry/loader phase — the same phase that defines screen name constants.

---

### Pitfall 8: Kivy Factory not registering new screen classes

**What goes wrong:**
`main.py` imports `from . import screens as _screens` to force all screen classes to be registered with Kivy's `Factory`. The `screens/__init__.py` explicitly imports every class. When new machine-variant classes are added (e.g., `SerrationRunScreen` in `screens/serration/run.py`), they must be added to `screens/__init__.py` or the import chain. If forgotten, `Factory.SerrationRunScreen()` raises `FactoryException: Unknown class SerrationRunScreen` — but only at runtime when the user first triggers machine detection, not at startup.

**Why it happens:**
The `__init__.py` import list is easy to overlook when adding new files in subdirectories. The error is deferred until the factory is actually invoked.

**How to avoid:**
Add all new screen classes to `screens/__init__.py` immediately when the Python file is created. Verify at app startup by calling `Factory.get(ClassName)` for each machine screen class in `build()`, raising early if any is missing.

**Warning signs:**
- App starts fine but crashes on first machine type switch.
- `FactoryException` in logs only when a specific machine type is selected.

**Phase to address:** Each machine-variant screen phase (Serration phase, Convex phase) — add `__init__.py` update to the phase checklist.

---

### Pitfall 9: MG reader thread and position poll thread not stopped when screen is removed

**What goes wrong:**
`RunScreen` manages two background threads: `_pos_poll_thread` (position polling at 10 Hz) and `_mg_reader_thread` (MG variable reader). These are started in `on_pre_enter` and stopped via `_stop_pos_poll()` / `_stop_mg_reader()`. If the screen-swap logic removes a machine's `RunScreen` from the `ScreenManager` without calling these stop methods first, both threads keep running, issuing `controller.cmd()` calls on the jobs queue, competing with the new machine's run screen, and adding stale position data to the new machine's `MachineState`.

**Why it happens:**
Screen removal is usually done by clearing the `ScreenManager` or removing widgets directly — Kivy does not fire lifecycle events (`on_leave`, `on_pre_leave`) when a screen is removed programmatically, only when navigation changes the visible screen. A screen that is removed while it is not the current screen never gets `on_pre_leave` fired.

**How to avoid:**
The screen-swap function must explicitly call stop methods on the outgoing run screen before removing it from the `ScreenManager`:
```python
def _swap_screen_set(old_run_screen, new_screens):
    if old_run_screen:
        old_run_screen._stop_pos_poll()
        old_run_screen._stop_mg_reader()
    sm.remove_widget(old_run_screen)
    for s in new_screens:
        sm.add_widget(s)
```

**Warning signs:**
- Two sets of position readings in state.pos after machine type switch.
- `[CTRL]` log shows double the expected command rate after switching machine type.
- New machine's run screen shows position values from the previous machine type.

**Phase to address:** Machine detection and screen-swap phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keep one RunScreen and add `if machine_type == 'flat_grind':` branches inside it | Avoids creating new files and classes | RunScreen becomes a 1000-line multi-machine blob; impossible to tune machines independently; contradicts milestone goal | Never — this is exactly what the refactor is meant to prevent |
| Use `Builder.load_string()` with inline .kv per machine type | Avoids separate .kv files | .kv embedded in Python strings — no syntax highlighting, no editor support, harder to review | Never for primary screen layouts; acceptable for small dynamic overlays only |
| Import `machine_config` directly in per-machine screens | Convenient | Breaks machine-type isolation; screens become coupled to the module-level singleton | Never in per-machine screen classes |
| Keep `name: 'run'` on all three run screen variants | No changes to tab routing logic | Three screens with the same name cannot coexist in one ScreenManager | Never if all three screens are added simultaneously |
| Skip subscription unsubscribe for "simple" screens | Less boilerplate | Listener accumulation; stale callbacks on orphaned widgets | Never — unsubscribe is always required when screen is removed |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `Builder.load_file` + per-machine .kv | Load all three machine .kv files at startup, all rules active simultaneously | Load all three at startup (rules are scoped to class names) but ensure each rule targets a unique class name |
| `ScreenManager` + machine screen set swap | Call `sm.clear_widgets()` which fires no lifecycle events on non-current screens | Explicitly stop threads on run screens, then `sm.remove_widget()` each screen before adding new set |
| `MachineState.subscribe` + screen lifecycle | Subscribe in `__init__`, never unsubscribe | Subscribe in `on_pre_enter`, unsubscribe in `on_pre_leave`; enforce via base class |
| `machine_config` + runtime type change | Screens read `mc.get_active_type()` at render time and cache result | Route machine type through `state.machine_type` → subscription chain; per-machine screens do not call `mc` |
| `TabBar.ALL_TABS` + new screen names | Add new screen name strings to `ALL_TABS` and `ROLE_TABS` | Keep screen name constants in a single module; `TabBar` imports constants, not raw strings |
| `on_stop` shutdown + renamed screens | `next(s for s in sm.screens if s.name == 'run')` returns `None` after rename | Use `isinstance()` check or a typed registry rather than string name lookup |
| `jobs.shutdown()` + in-flight commands | Shutdown while machine-swap threads are mid-command | Ensure all screen stop methods complete before `jobs.shutdown()` in `on_stop` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| All three machine run screens active simultaneously, all subscribing to state | Poll loop fires state notifications to 3x the listeners; Clock queue grows | Only the active machine's screens subscribe; inactive screens do not hold subscriptions | Immediately on second machine type selection |
| matplotlib figure not destroyed when run screen is swapped | Memory leak; each swap adds a new Figure object | Call `plt.close(fig)` when removing a run screen from the ScreenManager | After 2-3 machine type swaps in a session |
| Duplicate `_preload_params` calls on machine type change | 5 simultaneous bulk MG reads on the jobs queue; controller command timeout | Gate `_preload_params` with a flag; only call once per connect event, not per machine-type change | Immediately on machine type switch |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Machine type change navigates to setup screen | Operator is mid-grind session; loses context | Machine type change updates screen set but navigates to the equivalent tab (run to run, axes_setup to axes_setup) |
| Tab bar shows wrong tabs during machine type swap | Operator sees "Axes Setup" tab that leads to wrong machine's screen | Swap screen set and update tab routing atomically in a single Clock.schedule_once callback |
| No visual confirmation of machine type change | Operator unsure if the switch took effect | StatusBar already shows machine type; ensure it refreshes immediately after `state.notify()` |
| Serration screen missing D axis row leaves blank space | Visual gap in layout; looks broken | Use `height: 0` + `size_hint_y: None` to fully collapse hidden rows, not just `opacity: 0` |

---

## "Looks Done But Isn't" Checklist

- [ ] **FlatGrindRunScreen rename:** Verify `<FlatGrindRunScreen>:` rule in .kv matches Python class name — check that `Factory.FlatGrindRunScreen` resolves without error at startup
- [ ] **Thread shutdown on swap:** Verify `_stop_pos_poll()` and `_stop_mg_reader()` are called before removing old run screen — check log for stop confirmation lines
- [ ] **Subscription cleanup:** Verify `len(state._listeners)` does not grow after repeated machine type switches — add a one-time debug assertion
- [ ] **on_stop lookup:** Verify app exits cleanly (under 2 seconds) after rename — a hanging exit means the run screen was not found and threads were not stopped
- [ ] **Flat Grind end-to-end:** After all base class extraction, verify connect → live plot → cycle start → E-STOP → disconnect still works without regression
- [ ] **Serration D-axis hidden:** Verify D axis row has `height: 0` (not just `opacity: 0`) so layout does not reserve space for it
- [ ] **Tab routing after swap:** Verify tabbing to "Axes Setup" after machine type change loads the correct machine's AxesSetupScreen, not the previous machine's

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Flat Grind regression from base class extraction | HIGH | `git revert` base class commit; re-extract incrementally, running Flat Grind smoke test after each change |
| Screen name collision in ScreenManager | MEDIUM | Rename `name:` property in .kv file; update all string references in `main.py` using grep; re-test all navigation paths |
| Subscription leak causing stale callbacks | MEDIUM | Add `_unsub` tracking to base class; audit all `state.subscribe()` call sites and add corresponding unsubscribe calls |
| Builder rule collision (two .kv files, same class rule) | LOW | grep for `<ClassName>:` across all .kv files; remove duplicate; re-test affected screen |
| Thread zombie on screen remove | MEDIUM | Add explicit stop calls in screen-swap function; verify with exit timing test |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Widget ID collision across .kv files | .kv split phase — add grep check for duplicate `<ClassName>:` rules to phase checklist | `grep -r "<.*Screen>:" ui/` shows no duplicates |
| Builder.load_file ordering | Screen loader phase — document insertion point before `base.kv` in phase spec | New machine .kv files load between last existing screen and `base.kv`; app starts without errors |
| ScreenManager name collision | Screen registry phase — define screen name constants before any .kv splitting | `TabBar` and `main.py` both import from `screen_names.py`; no bare string literals for screen names |
| State subscription leak | Base class extraction phase — `MachineScreen` base class enforces on_pre_enter/on_pre_leave pattern | `len(state._listeners)` stable after 3 machine type switches |
| Flat Grind regression | Flat Grind preservation phase — smoke test before any Serration/Convex work | Connect → poll → cycle → E-STOP → disconnect passes with no regressions |
| machine_config coupling in screens | Serration/Convex screen phases — each phase checklist includes "no mc import in screen file" | `grep -r "machine_config" screens/` shows only the screen loader, not individual screen files |
| on_stop lookup break | Screen registry phase — replace string lookup with isinstance or typed registry | App exits in under 2 seconds; no zombie thread warning in logs |
| Kivy Factory missing new classes | Each machine-variant phase — add class to `screens/__init__.py` on the same commit as Python file | `Factory.get('SerrationRunScreen')` at startup does not raise |
| MG reader thread not stopped on swap | Screen-swap phase — explicit stop calls before `sm.remove_widget()` | Stop log lines appear on every machine type switch |

---

## Sources

- Existing codebase: `main.py` (Builder.load_file ordering, on_stop name lookup, ScreenManager wiring)
- Existing codebase: `screens/__init__.py` (Factory registration pattern)
- Existing codebase: `screens/run.py` (thread lifecycle, subscription pattern)
- Existing codebase: `screens/axes_setup.py` (machine_config coupling via `mc.get_axis_list()`)
- Existing codebase: `app_state.py` (`MachineState.subscribe` / unsubscribe pattern)
- Existing codebase: `screens/tab_bar.py` (hardcoded screen name strings in `ALL_TABS`)
- Kivy documentation: Builder rule scoping, ScreenManager behavior on `remove_widget`, Factory registration

---
*Pitfalls research for: Kivy multi-machine screen refactor (PythonDMCGUI v3.0)*
*Researched: 2026-04-11*
