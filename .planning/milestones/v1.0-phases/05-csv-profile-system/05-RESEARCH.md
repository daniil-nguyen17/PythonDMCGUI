# Phase 5: CSV Profile System - Research

**Researched:** 2026-04-04
**Domain:** Python csv stdlib + Kivy FileChooser + Kivy ModalView dialogs
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CSV Format & Scope**
- One CSV format containing everything: all scalar parameters (PARAM_DEFS) plus all DMC arrays
- Array-as-columns layout: scalars as name/value rows, arrays as one row per array with values across columns
- Metadata header rows at top: machine type, export date, profile name
- Controller only updates values for recognized array/variable names — extra data in CSV is harmless
- Primary use case: full setup profile (first-time), but most common use is just the delta arrays (deltaA-D) when changing knives

**UI Placement & Flow**
- New dedicated Profiles tab/screen added to tab bar (role-gated to Setup/Admin)
- Screen has two big buttons: Import and Export — minimal layout, no file listing
- Import opens a Kivy FileChooser modal overlay (full-screen) — works on both Pi kiosk and Windows
- Export shows a text input popup for user to enter a profile name, then saves
- File chooser filters to .csv files only

**Import Confirmation Diff**
- After selecting a CSV, show a diff dialog with changed values only (not all values)
- Table format: Name, Current Value, New Value — only rows where values differ
- User confirms to apply — values sent to controller + BV burn immediately (one-step import)
- If any value fails validation (out of range, wrong type, unrecognized name), block the entire import with clear error messages listing all failures
- Machine-type mismatch blocks import with clear error before diff is even shown

**File Storage**
- Default storage: app-relative `/profiles/` directory (created if missing)
- File chooser starts at /profiles/ but allows browsing other locations (USB drives, Downloads, etc.)
- Export: if file with same name exists, show "Overwrite existing profile?" confirmation dialog
- CSV files are human-readable and Excel-compatible

**Safety Interlocks**
- Import button disabled (greyed out) while `state.cycle_running == True`
- Import/Export only accessible to Setup and Admin roles (Operator cannot see Profiles tab)

### Claude's Discretion
- Exact Kivy FileChooser configuration (list vs icon view, filters)
- Diff dialog visual design and scrolling behavior
- Text input popup styling for export naming
- How to discover which arrays exist on the controller for full export
- Error message wording and layout
- Loading indicators during import/export operations

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CSV-01 | User can export all current parameter values and array data to a CSV file | Python csv stdlib + controller.cmd(MG var) + upload_array_auto() for arrays; profiles/ directory creation |
| CSV-02 | User can import a CSV file to load a knife profile with confirmation diff before apply | FileChooserListView in ModalView + diff logic comparing CSV values vs controller values + download_array() + BV burn |
| CSV-03 | CSV import validates machine type compatibility before applying | Metadata header row (first row: machine_type,<value>) parsed before diff is shown; mismatch blocks with error |
| CSV-04 | CSV import is blocked during an active grinding cycle (safety interlock) | state.cycle_running check; import button disabled=True / opacity=0.4 when True; same pattern as apply_to_controller() |
| CSV-05 | CSV profiles are only importable/exportable by Setup and Admin roles | TabBar.ROLE_TABS extended to include "profiles" for setup and admin; ProfilesScreen._apply_role_mode() pattern |
</phase_requirements>

---

## Summary

Phase 5 adds a CSV profile save/load capability to the DMC GUI. The technical domain is narrow and well-bounded: Python's stdlib `csv` module handles all file I/O, Kivy's `FileChooserListView` (wrapped in a `ModalView`) handles file selection, and the existing `GalilController` methods (`cmd`, `upload_array_auto`, `download_array_full`) handle controller communication.

The entire feature can be built with zero new PyPI dependencies. Python's `csv.writer`/`csv.reader` (stdlib since Python 2) produce Excel-compatible output with proper `newline=''` handling. The Kivy `FileChooserListView` widget (in `kivy.uix.filechooser`) works identically on both Windows and Raspberry Pi Linux, making it the right choice over platform-specific dialogs.

The most complex logic in this phase is the diff engine: after reading a CSV, the screen must read all current controller values (scalars via `MG var`, arrays via `upload_array_auto`), compare them to CSV values, and present only changed rows for confirmation. This is pure Python and is fully unit-testable without Kivy.

**Primary recommendation:** Build all business logic (CSV read/write, validation, diff computation) as pure Python methods on `ProfilesScreen` that are testable without Kivy initialization. Wire the UI layer (FileChooser, popups) in KV and thin Python handlers. Reuse `ParametersScreen.validate_field()` and `PARAM_DEFS` directly.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `csv` (stdlib) | Python 3.10+ | CSV read/write | No dependency; Excel-compatible; already part of Python |
| `os` / `pathlib` (stdlib) | Python 3.10+ | profiles/ dir creation, path manipulation | No dependency |
| `kivy.uix.filechooser.FileChooserListView` | Kivy 2.2.0+ | File selection modal | Built into Kivy; works cross-platform; touch-friendly list layout |
| `kivy.uix.modalview.ModalView` | Kivy 2.2.0+ | Modal overlay container for FileChooser and dialogs | Same pattern as existing PINOverlay; proven in this codebase |
| `kivy.uix.popup.Popup` | Kivy 2.2.0+ | Small confirmation dialogs (overwrite, error, diff) | Simpler than ModalView for self-contained dialogs with title |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `kivy.uix.textinput.TextInput` | Kivy 2.2.0+ | Profile name entry on export | Single-line text entry in popup |
| `kivy.uix.scrollview.ScrollView` | Kivy 2.2.0+ | Scrollable diff table | Diff may have many rows |
| `kivy.uix.gridlayout.GridLayout` | Kivy 2.2.0+ | Diff table rows | Tabular diff display |
| `dmccodegui.utils.jobs.submit` | (project) | Background controller I/O during import/export | All controller calls must be off main thread |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `csv` stdlib | `pandas` | pandas adds ~20MB dependency; no benefit for simple profile files |
| `FileChooserListView` | `FileChooserIconView` | Icon view better for image files; list view is faster and more readable for .csv files on touchscreen |
| `Popup` for small dialogs | `ModalView` subclass | Popup is simpler (has built-in title); ModalView better for complex full-screen overlays like FileChooser |

**Installation:** No new packages required. All dependencies are in stdlib or already in Kivy (existing dependency).

---

## Architecture Patterns

### Recommended Project Structure
```
src/dmccodegui/
├── screens/
│   └── profiles.py          # ProfilesScreen — all business logic, pure Python methods
├── ui/
│   └── profiles.kv          # KV layout for ProfilesScreen, FileChooser overlay, popups
├── profiles/                # (created at runtime) default profile storage directory
└── main.py                  # Add profiles.kv to KV_FILES; add ProfilesScreen to base.kv
tests/
└── test_profiles.py         # Unit tests for CSV logic, validation, diff — no Kivy needed
```

### Pattern 1: CSV File Format (Mixed Scalars + Arrays)

**What:** A human-readable, Excel-compatible CSV with metadata rows at the top, followed by scalar name/value rows, followed by array rows with values spread across columns.

**When to use:** Always — this is the locked format decision.

**Structure:**
```
# Metadata rows (prefixed with # so csv.reader can skip them, but still readable)
machine_type,4-Axes Flat Grind
export_date,2026-04-04T14:30:00
profile_name,SerrationKnife_Setup_01
# Scalar parameters
knfThk,25.5
edgeThk,0.8
fdA,120.0
...
# Arrays (name in col 0, values in col 1..N)
deltaA,0.0,0.5,1.0,1.5,2.0,...
deltaB,0.0,0.3,0.6,...
deltaC,0.0,0.1,...
deltaD,0.0,0.2,...
```

**Key implementation note:** The `#`-prefix convention for metadata rows is NOT standard CSV comment syntax — `csv.reader` will include them. Use a custom convention: rows where `row[0].startswith('#')` are skipped during data parsing, OR use a dedicated two-column section before data. The locked decision says "metadata header rows at top: machine type, export date, profile name" — implement as plain CSV rows with a reserved first column value, not as `#` comments.

Recommended metadata row format (two-column, always first):
```
_machine_type,4-Axes Flat Grind
_export_date,2026-04-04T14:30:00
_profile_name,SerrationKnife_Setup_01
```
The `_` prefix distinguishes metadata from parameter names (no DMC variable starts with `_`).

**Example writer:**
```python
# Source: Python docs https://docs.python.org/3/library/csv.html
import csv
import datetime
from pathlib import Path

def export_profile(path: Path, profile_name: str, scalars: dict, arrays: dict, machine_type: str) -> None:
    """Write profile CSV. scalars={var: float}, arrays={name: [float]}."""
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        # Metadata block
        w.writerow(['_machine_type', machine_type])
        w.writerow(['_export_date', datetime.datetime.now().isoformat(timespec='seconds')])
        w.writerow(['_profile_name', profile_name])
        # Scalar parameters
        for var_name, value in scalars.items():
            w.writerow([var_name, value])
        # Array parameters
        for array_name, values in arrays.items():
            w.writerow([array_name] + list(values))
```

**Example reader:**
```python
def parse_profile_csv(path: Path) -> dict:
    """Returns {'machine_type': str, 'profile_name': str, 'export_date': str,
                'scalars': {var: float}, 'arrays': {name: [float]}}."""
    meta = {}
    scalars = {}
    arrays = {}

    SCALAR_VARS = {p['var'] for p in PARAM_DEFS}  # from parameters.py

    with open(path, 'r', newline='', encoding='utf-8') as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            key, *rest = row
            if key.startswith('_'):
                meta[key[1:]] = rest[0] if rest else ''
            elif key in SCALAR_VARS:
                try:
                    scalars[key] = float(rest[0])
                except (ValueError, IndexError):
                    pass  # let validation catch it
            elif len(rest) > 1 or key not in SCALAR_VARS:
                # Likely an array row: name + multiple values
                try:
                    arrays[key] = [float(v) for v in rest if v.strip()]
                except ValueError:
                    pass

    return {
        'machine_type': meta.get('machine_type', ''),
        'profile_name': meta.get('profile_name', ''),
        'export_date': meta.get('export_date', ''),
        'scalars': scalars,
        'arrays': arrays,
    }
```

### Pattern 2: FileChooser in ModalView

**What:** A full-screen `ModalView` containing a `FileChooserListView` with `.csv` filter, a Cancel button, and selection confirmation.

**When to use:** Import flow — user presses Import button on ProfilesScreen.

**Key properties:**
- `FileChooserListView.path`: set to absolute path of `profiles/` directory on open
- `FileChooserListView.filters`: `['*.csv']` — list-style filter, case-sensitive on Linux (Pi)
- `FileChooserListView.multiselect`: `False` (default)
- Trigger: bind to `on_submit` (double-tap confirms) OR a dedicated "Open" button that reads `chooser.selection[0]`

**KV pattern:**
```kv
#:import theme dmccodegui.theme_manager.theme

<FileChooserOverlay>:
    auto_dismiss: False
    size_hint: 1, 1
    background_color: 0, 0, 0, 0
    overlay_color: theme.overlay_bg

    BoxLayout:
        orientation: 'vertical'
        padding: '16dp'
        spacing: '8dp'
        canvas.before:
            Color:
                rgba: theme.bg_card
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: 'Select Profile'
            font_size: '28sp'
            size_hint_y: None
            height: '48dp'

        FileChooserListView:
            id: chooser
            filters: ['*.csv']
            size_hint_y: 1

        BoxLayout:
            size_hint_y: None
            height: '56dp'
            spacing: '8dp'
            Button:
                text: 'Cancel'
                on_release: root.dismiss()
            Button:
                text: 'Open'
                on_release: root.confirm_selection()
```

**Python pattern:**
```python
class FileChooserOverlay(ModalView):
    on_file_selected = ObjectProperty(None, allownone=True)  # callback(path: str)

    def open_at(self, start_path: str) -> None:
        self.ids.chooser.path = start_path
        self.open()

    def confirm_selection(self) -> None:
        selection = self.ids.chooser.selection
        if selection:
            self.dismiss()
            if self.on_file_selected:
                self.on_file_selected(selection[0])
```

### Pattern 3: Diff Dialog (ModalView or Popup)

**What:** After parsing a CSV and reading current controller values, show a table of only changed rows: Name | Current | New. User confirms to apply or cancels.

**When to use:** After successful CSV parse and machine-type validation.

**Implementation approach:** Build rows dynamically in `on_kv_post` or via `build_diff_table(changes: list[dict])` method. `changes` is a list of `{'name': str, 'current': str, 'new': str}` dicts. Use a `ScrollView` wrapping a `GridLayout(cols=3)`.

**KV structure:**
```kv
<DiffDialog>:
    auto_dismiss: False
    size_hint: 0.9, 0.85

    BoxLayout:
        orientation: 'vertical'
        padding: '16dp'
        spacing: '8dp'
        canvas.before:
            Color:
                rgba: theme.bg_card
            Rectangle:
                pos: self.pos
                size: self.size

        Label:
            text: 'Changes to Apply'
            font_size: '26sp'
            size_hint_y: None
            height: '44dp'

        # Column headers
        GridLayout:
            cols: 3
            size_hint_y: None
            height: '40dp'
            Label:
                text: 'Parameter'
            Label:
                text: 'Current'
            Label:
                text: 'New'

        ScrollView:
            size_hint_y: 1
            BoxLayout:
                id: diff_rows
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height

        BoxLayout:
            size_hint_y: None
            height: '56dp'
            spacing: '8dp'
            Button:
                text: 'Cancel'
                on_release: root.dismiss()
            Button:
                text: 'Apply'
                background_color: 0.133, 0.773, 0.369, 1
                on_release: root.apply_confirmed()
```

### Pattern 4: Export Name Popup

**What:** Small Popup with a TextInput for the profile name and Save/Cancel buttons.

**When to use:** User presses Export button on ProfilesScreen.

**Python pattern (fully dynamic, no separate KV rule needed):**
```python
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label

def _show_export_name_popup(self, on_save):
    content = BoxLayout(orientation='vertical', spacing='8dp', padding='12dp')
    lbl = Label(text='Profile Name:', size_hint_y=None, height='36dp')
    ti = TextInput(text='', multiline=False, size_hint_y=None, height='48dp')
    row = BoxLayout(size_hint_y=None, height='52dp', spacing='8dp')
    cancel_btn = Button(text='Cancel')
    save_btn = Button(text='Save', background_color=[0.133, 0.773, 0.369, 1])
    row.add_widget(cancel_btn)
    row.add_widget(save_btn)
    content.add_widget(lbl)
    content.add_widget(ti)
    content.add_widget(row)
    popup = Popup(title='Export Profile', content=content,
                  size_hint=(None, None), size=('480dp', '240dp'),
                  auto_dismiss=False)
    cancel_btn.bind(on_release=lambda *_: popup.dismiss())
    save_btn.bind(on_release=lambda *_: (popup.dismiss(), on_save(ti.text.strip())))
    popup.open()
```

### Pattern 5: Safety Interlock on Import Button

**What:** Subscribe to `state` changes; when `state.cycle_running` becomes True, disable and grey the Import button.

**When to use:** Always — locked requirement.

**Pattern (matches existing `_apply_role_mode` style):**
```python
def on_pre_enter(self, *args):
    if self.state is not None:
        self._unsub_cycle = self.state.subscribe(self._on_state_change)
    self._update_import_button()

def on_leave(self, *args):
    if hasattr(self, '_unsub_cycle') and self._unsub_cycle:
        self._unsub_cycle()

def _on_state_change(self, state):
    from kivy.clock import Clock
    Clock.schedule_once(lambda *_: self._update_import_button())

def _update_import_button(self):
    cycle_running = self.state.cycle_running if self.state else False
    btn = self.ids.get('import_btn')
    if btn:
        btn.disabled = cycle_running
        btn.opacity = 0.4 if cycle_running else 1.0
```

### Pattern 6: Profiles Directory Management

**What:** Create `profiles/` adjacent to the app package at startup; never raise if it already exists.

```python
import os
from pathlib import Path

def _get_profiles_dir() -> Path:
    """Return the profiles/ directory path, creating it if needed."""
    base = Path(__file__).parent.parent.parent  # src/dmccodegui/../../ = project root
    profiles = base / 'profiles'
    profiles.mkdir(exist_ok=True)
    return profiles
```

**Note:** On Pi kiosk, the app runs from a fixed location (SD card). `Path(__file__).parent` resolves correctly. On Windows, same logic applies. This is more reliable than `os.getcwd()` which depends on launch directory.

### Pattern 7: Tab Bar Integration

**What:** Add "profiles" to `TabBar.ALL_TABS` and `TabBar.ROLE_TABS` so Setup/Admin see it; Operator does not.

**Changes to `tab_bar.py`:**
```python
ALL_TABS = [
    ("run", "Run"),
    ("axes_setup", "Axes Setup"),
    ("parameters", "Parameters"),
    ("profiles", "Profiles"),       # ADD
    ("diagnostics", "Diagnostics"),
]

ROLE_TABS = {
    "operator": ["run"],
    "setup":    ["run", "axes_setup", "parameters", "profiles"],   # ADD profiles
    "admin":    ["run", "axes_setup", "parameters", "profiles", "diagnostics"],  # ADD
}
```

**Changes to `base.kv`:**
```kv
ProfilesScreen:
    name: 'profiles'
```

**Changes to `main.py`:**
```python
KV_FILES = [
    ...
    "ui/profiles.kv",    # ADD after parameters.kv
    ...
]
```

Also add `ProfilesScreen` injection in the controller/state injection loop — already handled by the generic `for screen in sm.screens` loop in `build()` since `ProfilesScreen` will have `controller` and `state` ObjectProperties.

### Anti-Patterns to Avoid

- **Do not use `csv.DictWriter`/`DictReader` for this format.** The mixed scalars+arrays layout has variable row width — standard DictReader assumes uniform column count. Use plain `csv.writer`/`csv.reader` with manual row routing.
- **Do not open files on the main thread.** Even small CSV reads should go through `jobs.submit()` to avoid momentary UI freeze on Pi.
- **Do not call `controller.cmd()` from the Kivy main thread.** All controller calls in import/export go through background jobs; UI is updated via `Clock.schedule_once`.
- **Do not use `os.path.join(os.getcwd(), 'profiles')` for the profiles directory.** Use `Path(__file__)` relative paths — `getcwd()` is unreliable when launched via desktop shortcut or systemd service.
- **Do not hard-code a fixed array list.** The CONTEXT.md says "discover which arrays exist on the controller" is discretion. Use a canonical `ARRAY_NAMES` constant in `profiles.py` (e.g., `['deltaA', 'deltaB', 'deltaC', 'deltaD']`) that covers the known arrays, plus `upload_array_auto` for each. Document which names are expected so import can route unknown rows gracefully.
- **Do not block import on unrecognized array names.** The locked decision says "extra data in CSV is harmless" — import should silently skip rows where the array name is not in the known list, rather than error.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV read/write | Custom file format parser | `csv.writer` / `csv.reader` stdlib | Handles quoting, escaping, newlines, Excel compatibility automatically |
| File browser UI | Custom directory listing widget | `FileChooserListView` (Kivy builtin) | Cross-platform (Pi + Windows), touch-friendly, already tested |
| Modal overlay | Custom overlay widget | `ModalView` (same pattern as PINOverlay already in codebase) | Proven pattern; handles dismiss, touch-blocking |
| Background I/O | Direct threading | `jobs.submit()` (project utility) | Thread pool already running; consistent error handling |
| Float formatting | Custom string conversion | Python `f'{value:.6g}'` | Avoids trailing zeros while preserving precision |

**Key insight:** The CSV module's silent-quoting behaviour is non-trivial to replicate correctly (comma-in-value, newline-in-value, quote escaping). Always use `csv.writer` even for "simple" numeric data.

---

## Common Pitfalls

### Pitfall 1: CSV Newline Handling on Windows
**What goes wrong:** Files written with default `open()` on Windows get `\r\r\n` line endings (double carriage return) instead of `\r\n`, which breaks Excel and csv.reader.
**Why it happens:** Python's text mode adds `\n` → `\r\n` translation on Windows, then `csv.writer` adds its own line ending.
**How to avoid:** Always open CSV files with `newline=''` on both read and write: `open(path, 'w', newline='', encoding='utf-8')`.
**Warning signs:** CSV opens in Excel with blank rows between every data row.

### Pitfall 2: FileChooserListView Filter Case Sensitivity on Pi
**What goes wrong:** Filter `['*.csv']` misses files saved as `Profile.CSV` (uppercase extension) on Linux/Pi filesystem.
**Why it happens:** Linux filesystem is case-sensitive; Kivy's filter is a glob match against the filename.
**How to avoid:** Use `filters=['*.csv', '*.CSV']` or implement a filter function: `filters=[lambda d, f: f.lower().endswith('.csv')]`.
**Warning signs:** User reports that profiles saved on Windows (which may use .CSV) don't appear in the file chooser on Pi.

### Pitfall 3: FileChooser Path on Pi vs Windows
**What goes wrong:** `profiles/` path resolves differently depending on whether app is launched from project root, a systemd service, or a desktop shortcut.
**Why it happens:** Relative paths are resolved relative to `os.getcwd()` at launch time, which varies.
**How to avoid:** Use `Path(__file__).resolve().parent` (the `screens/` or `dmccodegui/` directory) as the anchor, then navigate to the profiles directory relative to it.
**Warning signs:** "No such file or directory" error on Pi but not Windows.

### Pitfall 4: Controller Read During Export Freezes UI
**What goes wrong:** Reading 20 scalar vars + 4 arrays on a background job takes 1-3 seconds. If done on main thread, Kivy UI freezes and E-STOP becomes unresponsive.
**Why it happens:** GalilController.cmd() is a blocking network call.
**How to avoid:** Always wrap export's controller reads in `jobs.submit()`. Show a loading indicator (label text change) before submitting the job.
**Warning signs:** UI visually freezes when Export is pressed.

### Pitfall 5: Diff Computation With Floating Point
**What goes wrong:** Comparing `25.5` (from controller, as float) to `'25.5'` (from CSV, as string) with `==` always reports them as different.
**Why it happens:** String comparison vs numeric comparison.
**How to avoid:** Always convert CSV values to `float` before comparing. Use `abs(csv_val - ctrl_val) < 1e-9` for equality, consistent with `ParametersScreen.validate_field()`.
**Warning signs:** Diff dialog shows every parameter as "changed" even when values match.

### Pitfall 6: Array Discovery
**What goes wrong:** `upload_array_auto()` raises `RuntimeError` if the array name doesn't exist on the controller (e.g., the DMC program hasn't declared it yet).
**Why it happens:** `MG arrayName[-1]` returns an error for undeclared arrays.
**How to avoid:** Wrap each `upload_array_auto()` call in try/except; log the failure; continue with remaining arrays. An empty array in the export is acceptable.
**Warning signs:** Export silently fails with no arrays in the output file.

### Pitfall 7: ModalView Keyboard on Pi
**What goes wrong:** The export name TextInput opens the virtual keyboard (on Pi touchscreen), which can cover the popup.
**Why it happens:** Kivy auto-opens the VKB when a TextInput is focused on a touch device.
**How to avoid:** In `kivy.uix.textinput.TextInput`, set `keyboard_mode = 'managed'` globally or configure the app to use a fixed-size window. Alternatively, use a `Popup` sized larger to accommodate the keyboard, or use a numeric-style name (user types on a separate numpad overlay if needed). For now, a simple TextInput is acceptable — the user can type on Pi's physical keyboard or on-screen keyboard.

---

## Code Examples

Verified patterns from official sources and this codebase:

### Correct CSV Write (Python docs)
```python
# Source: https://docs.python.org/3/library/csv.html
import csv
with open('profiles/MyKnife.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['_machine_type', '4-Axes Flat Grind'])
    writer.writerow(['knfThk', '25.5'])
    writer.writerow(['deltaA', '0.0', '0.5', '1.0', '1.5'])
```

### Correct CSV Read
```python
# Source: https://docs.python.org/3/library/csv.html
import csv
with open('profiles/MyKnife.csv', 'r', newline='', encoding='utf-8') as f:
    for row in csv.reader(f):
        if not row:
            continue
        key, *values = row
        # route by key prefix or presence in SCALAR_VARS
```

### FileChooserListView Initial Path + Filter
```python
# Source: https://kivy.org/doc/stable/api-kivy.uix.filechooser.html
from kivy.uix.filechooser import FileChooserListView
chooser = FileChooserListView()
chooser.path = str(profiles_dir)
chooser.filters = ['*.csv', '*.CSV']
```

### Profiles Directory (safe on both platforms)
```python
from pathlib import Path

def get_profiles_dir() -> Path:
    pkg_dir = Path(__file__).resolve().parent  # .../src/dmccodegui/screens/
    profiles = pkg_dir.parent.parent.parent / 'profiles'  # project root / profiles
    profiles.mkdir(exist_ok=True)
    return profiles
```

### MachineState Subscribe/Unsubscribe (existing pattern)
```python
# Source: existing codebase — app_state.py MachineState.subscribe()
def on_pre_enter(self, *args):
    self._unsub = self.state.subscribe(self._on_state_change)

def on_leave(self, *args):
    if hasattr(self, '_unsub'):
        self._unsub()
```

### Import Disabled When Cycle Running
```python
# Pattern from ParametersScreen.apply_to_controller()
def _update_import_button(self):
    cycle_running = getattr(self.state, 'cycle_running', False)
    btn = self.ids.get('import_btn')
    if btn:
        btn.disabled = cycle_running
        btn.opacity = 0.4 if cycle_running else 1.0
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `open(f, 'w')` without `newline=''` | `open(f, 'w', newline='', encoding='utf-8')` | Python 3.x | Required for csv module to work correctly cross-platform |
| Manual file dialog (tkinter) | `FileChooserListView` in `ModalView` | Kivy 1.x | No tkinter dependency; works in Kivy's event loop without threading issues |

**Deprecated/outdated:**
- `csv.DictReader`/`DictWriter` for this format: not wrong, but assumes uniform column count per row — does not fit the mixed-width array rows.
- `tkinter.filedialog`: do not use; tkinter and Kivy cannot coexist in the same process on Pi.

---

## Open Questions

1. **Which array names to export?**
   - What we know: CONTEXT.md mentions "deltaA-D" as most common; controller can have other arrays
   - What's unclear: Full list of DMC array names declared in the controller program; no source of truth in the Python codebase currently
   - Recommendation: Define a `KNOWN_ARRAYS` constant in `profiles.py` as `['deltaA', 'deltaB', 'deltaC', 'deltaD']` for Phase 5. Note in code that Phase 6 (machine types) may extend this list. Wrap each `upload_array_auto()` call in try/except to handle absent arrays gracefully.

2. **Machine type string — where is it defined?**
   - What we know: CONTEXT.md says machine type is hard-coded at deployment (Phase 6 concern), not runtime-selectable. CSV-03 requires validating it.
   - What's unclear: What string value is used as the canonical machine type identifier before Phase 6 is built? No `MACHINE_TYPE` constant exists yet in the codebase.
   - Recommendation: Add a module-level constant `MACHINE_TYPE = '4-Axes Flat Grind'` (or similar) to a new `profiles.py` for Phase 5. Phase 6 will replace this with a proper machine-type module. Export writes this value; import compares against it.

3. **Profiles directory location on deployed Pi**
   - What we know: Pi runs the app from a fixed location on the SD card. USB drives mount at `/media/pi/<label>` on Raspbian.
   - What's unclear: Whether the default `profiles/` directory (adjacent to the app) is writable on the SD card in kiosk mode, or if it should default to `/home/pi/profiles/`.
   - Recommendation: Use `Path(__file__).resolve().parent.parent.parent / 'profiles'` for now. Phase 8 (kiosk/deploy) can revisit the default path. The FileChooser allows browsing anywhere anyway, so USB exports will work regardless.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (no version pin; `pyproject.toml` dev dep) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` |
| Quick run command | `pytest tests/test_profiles.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CSV-01 | `export_profile()` writes machine_type metadata row | unit | `pytest tests/test_profiles.py::test_export_writes_machine_type -x` | Wave 0 |
| CSV-01 | `export_profile()` writes all PARAM_DEFS scalars | unit | `pytest tests/test_profiles.py::test_export_writes_all_scalars -x` | Wave 0 |
| CSV-01 | `export_profile()` writes array rows with values across columns | unit | `pytest tests/test_profiles.py::test_export_writes_array_row -x` | Wave 0 |
| CSV-01 | `export_profile()` output is parseable by csv.reader | unit | `pytest tests/test_profiles.py::test_export_csv_parseable -x` | Wave 0 |
| CSV-02 | `parse_profile_csv()` extracts scalars and arrays from file | unit | `pytest tests/test_profiles.py::test_parse_returns_scalars_and_arrays -x` | Wave 0 |
| CSV-02 | `compute_diff()` returns only changed rows | unit | `pytest tests/test_profiles.py::test_diff_only_changed -x` | Wave 0 |
| CSV-02 | `compute_diff()` uses numeric comparison (not string) | unit | `pytest tests/test_profiles.py::test_diff_numeric_comparison -x` | Wave 0 |
| CSV-02 | Import validation rejects invalid scalar values | unit | `pytest tests/test_profiles.py::test_import_validates_scalars -x` | Wave 0 |
| CSV-03 | Machine-type mismatch returns error before diff | unit | `pytest tests/test_profiles.py::test_machine_type_mismatch_blocked -x` | Wave 0 |
| CSV-04 | `ProfilesScreen._update_import_button()` disables when cycle_running=True | unit | `pytest tests/test_profiles.py::test_import_disabled_when_cycle_running -x` | Wave 0 |
| CSV-05 | TabBar shows 'profiles' tab for setup/admin, not operator | unit | `pytest tests/test_tab_bar.py::test_profiles_tab_role_visibility -x` | Wave 0 (extend existing) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_profiles.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_profiles.py` — covers CSV-01, CSV-02, CSV-03, CSV-04 (pure Python, no Kivy)
- [ ] `src/dmccodegui/screens/profiles.py` — new screen module
- [ ] `src/dmccodegui/ui/profiles.kv` — KV layout

*(The existing `tests/test_tab_bar.py` must be extended for CSV-05 — adding a test for the "profiles" tab visibility per role.)*

---

## Sources

### Primary (HIGH confidence)
- Python stdlib `csv` module — https://docs.python.org/3/library/csv.html — writer/reader usage, newline='' requirement
- Kivy 2.3.1 FileChooser docs — https://kivy.org/doc/stable/api-kivy.uix.filechooser.html — path, filters, on_submit, multiselect
- Project source code (direct read) — `parameters.py`, `controller.py`, `pin_overlay.py`, `tab_bar.py`, `app_state.py`, `main.py`, `base.kv` — established patterns

### Secondary (MEDIUM confidence)
- WebSearch: Kivy FileChooserListView modal patterns — confirmed list view is standard approach; WebFetch of official docs confirmed API surface

### Tertiary (LOW confidence)
- Pi USB mount path `/media/pi/<label>` — common knowledge, not verified against current Raspbian Bookworm; Phase 8 should confirm

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools are stdlib or existing Kivy; no new dependencies
- Architecture: HIGH — directly derived from locked CONTEXT.md decisions and existing codebase patterns
- Pitfalls: HIGH for CSV newline and FileChooser filter (verified against official docs); MEDIUM for Pi path behavior (not live-tested)

**Research date:** 2026-04-04
**Valid until:** 2026-07-04 (Kivy 2.x API is stable; csv stdlib is stable)
