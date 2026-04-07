"""CSV Profile Engine + ProfilesScreen UI.

Pure-Python CSV engine (export, parse, diff, validate) plus the Kivy
ProfilesScreen that wires the engine to the controller.  The engine
functions are testable headless; the Kivy classes are only imported when
a Kivy event loop is present.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

KNOWN_ARRAYS: list[str] = ["deltaA", "deltaB", "deltaC", "deltaD"]
"""Array variable names that can be exported/imported in profiles."""


# ---------------------------------------------------------------------------
# 1. Export
# ---------------------------------------------------------------------------

def export_profile(
    path: Path,
    profile_name: str,
    scalars: dict[str, Any],
    arrays: dict[str, list[float]],
    machine_type: Optional[str] = None,
) -> None:
    """Write a knife profile to a CSV file.

    File layout:
      - 3 metadata rows: _machine_type, _export_date, _profile_name
      - One scalar row per entry in `scalars`: [var_name, value]
      - One array row per entry in `arrays`:  [array_name, val1, val2, ...]

    Args:
        path: Destination path (will be created/overwritten).
        profile_name: Human-readable name stored in _profile_name row.
        scalars: Dict mapping var names to numeric values.
        arrays: Dict mapping array names to lists of floats.
        machine_type: Machine type string. Defaults to mc.get_active_type() if None.
    """
    if machine_type is None:
        import dmccodegui.machine_config as mc
        machine_type = mc.get_active_type() or "Unknown"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)

        # Metadata rows
        writer.writerow(["_machine_type", machine_type])
        writer.writerow(["_export_date", datetime.now().isoformat(timespec="seconds")])
        writer.writerow(["_profile_name", profile_name])

        # Scalar rows
        for var_name, value in scalars.items():
            writer.writerow([var_name, value])

        # Array rows — format each float with :.6g to keep precision without trailing zeros
        for array_name, values in arrays.items():
            row = [array_name] + [f"{v:.6g}" for v in values]
            writer.writerow(row)


# ---------------------------------------------------------------------------
# 2. Parse
# ---------------------------------------------------------------------------

def parse_profile_csv(path: Path) -> dict:
    """Parse a profile CSV file into structured data.

    Returns:
        {
            'machine_type': str,
            'profile_name': str,
            'export_date': str,
            'scalars': {var_name: float},
            'arrays': {array_name: [float, ...]},
        }

    Rules:
        - Rows starting with '_' are metadata.
        - Rows whose key is a known scalar var (in mc.get_param_defs()) are scalars.
        - Rows with key in KNOWN_ARRAYS and >1 value column are arrays.
        - Empty rows are silently skipped.
        - Unrecognized rows are silently ignored.
    """
    import dmccodegui.machine_config as mc
    param_defs = mc.get_param_defs()
    _param_by_var = {p["var"]: p for p in param_defs}

    result: dict = {
        "machine_type": "",
        "profile_name": "",
        "export_date": "",
        "scalars": {},
        "arrays": {},
    }

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            # Skip empty rows
            if not row or all(cell.strip() == "" for cell in row):
                continue

            key = row[0]

            # Metadata rows
            if key.startswith("_"):
                if key == "_machine_type" and len(row) >= 2:
                    result["machine_type"] = row[1]
                elif key == "_profile_name" and len(row) >= 2:
                    result["profile_name"] = row[1]
                elif key == "_export_date" and len(row) >= 2:
                    result["export_date"] = row[1]
                # other _keys silently ignored
                continue

            # Array rows (multi-value, known name)
            if key in KNOWN_ARRAYS and len(row) > 1:
                try:
                    result["arrays"][key] = [float(v) for v in row[1:]]
                except ValueError:
                    pass  # malformed array — skip
                continue

            # Scalar rows (known var name, single value)
            if key in _param_by_var and len(row) >= 2:
                try:
                    result["scalars"][key] = float(row[1])
                except ValueError:
                    pass  # non-numeric scalar — skip
                continue

            # Unrecognized row — silently ignored

    return result


# ---------------------------------------------------------------------------
# 3. Diff
# ---------------------------------------------------------------------------

def compute_diff(
    csv_scalars: dict[str, Any],
    current_scalars: dict[str, Any],
    csv_arrays: dict[str, list[float]],
    current_arrays: dict[str, list[float]],
) -> list[dict]:
    """Compare CSV values against current controller values and return changed rows.

    Args:
        csv_scalars: Scalar values from the imported CSV file.
        current_scalars: Current scalar values from the live controller.
        csv_arrays: Array values from the imported CSV file.
        current_arrays: Current array values from the live controller.

    Returns:
        List of dicts with keys 'name', 'current', 'new' for each changed value.
        'current' is the live controller value; 'new' is the CSV (import) value.
        Empty list if no differences found.

    Note:
        Float equality uses abs(a - b) < 1e-9 to avoid spurious string diffs.
    """
    diffs: list[dict] = []

    # Scalar comparison — only compare vars present in CSV
    for var_name, csv_val in csv_scalars.items():
        ctrl_val = current_scalars.get(var_name)
        if ctrl_val is None:
            # Variable not in current controller state — include as changed
            diffs.append({
                "name": var_name,
                "current": "",
                "new": str(csv_val),
            })
            continue

        try:
            csv_float = float(csv_val)
            ctrl_float = float(ctrl_val)
        except (ValueError, TypeError):
            # Cannot compare numerically — treat as changed
            diffs.append({
                "name": var_name,
                "current": str(ctrl_val),
                "new": str(csv_val),
            })
            continue

        if abs(csv_float - ctrl_float) >= 1e-9:
            diffs.append({
                "name": var_name,
                "current": str(ctrl_float),
                "new": str(csv_float),
            })

    # Array comparison — only compare arrays present in CSV
    for array_name, csv_vals in csv_arrays.items():
        ctrl_vals = current_arrays.get(array_name, [])

        # Different lengths => changed
        if len(csv_vals) != len(ctrl_vals):
            diffs.append({
                "name": array_name,
                "current": ",".join(str(v) for v in ctrl_vals),
                "new": ",".join(str(v) for v in csv_vals),
            })
            continue

        # Element-wise comparison
        changed = any(
            abs(float(cv) - float(av)) >= 1e-9
            for cv, av in zip(csv_vals, ctrl_vals)
        )
        if changed:
            diffs.append({
                "name": array_name,
                "current": ",".join(str(v) for v in ctrl_vals),
                "new": ",".join(str(v) for v in csv_vals),
            })

    return diffs


# ---------------------------------------------------------------------------
# 4. Validate
# ---------------------------------------------------------------------------

def validate_import(parsed: dict) -> list[str]:
    """Validate a parsed profile dict before applying to the controller.

    Validation order:
      1. Machine type must match MACHINE_TYPE (if mismatch, return immediately).
      2. Each known scalar is checked for numeric type and min/max range.

    Args:
        parsed: Output of parse_profile_csv() or equivalent dict with keys
                'machine_type', 'scalars'.

    Returns:
        List of error strings. Empty list means the profile is valid.
        Unknown scalar var names are silently ignored.
    """
    import dmccodegui.machine_config as mc
    current_type = mc.get_active_type()
    param_defs = mc.get_param_defs()
    _param_by_var = {p["var"]: p for p in param_defs}

    errors: list[str] = []

    # Step 1: Machine type check
    if parsed.get("machine_type", "") != current_type:
        errors.append(
            f"Machine type mismatch: CSV has '{parsed.get('machine_type', '')}', "
            f"expected '{current_type}'"
        )
        return errors  # stop validation here

    # Step 2: Scalar range and numeric checks
    scalars = parsed.get("scalars", {})
    for var_name, value in scalars.items():
        param = _param_by_var.get(var_name)
        if param is None:
            # Unknown var — silently ignore per locked decision
            continue

        # Numeric check
        try:
            float_val = float(value)
        except (ValueError, TypeError):
            errors.append(
                f"'{var_name}' has non-numeric value: {value!r}"
            )
            continue

        # Range check
        if not (param["min"] <= float_val <= param["max"]):
            errors.append(
                f"'{var_name}' value {float_val} is out of range "
                f"[{param['min']}, {param['max']}]"
            )

    return errors


# ---------------------------------------------------------------------------
# Profiles directory helper
# ---------------------------------------------------------------------------

def get_profiles_dir() -> Path:
    """Return the project-root ``profiles/`` directory, creating it if needed.

    The path is resolved from this file's location rather than cwd so it
    works regardless of the working directory the app is launched from.
    """
    # src/dmccodegui/screens/profiles.py  ->  4 parents up = project root
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    profiles_dir = project_root / "profiles"
    profiles_dir.mkdir(exist_ok=True)
    return profiles_dir


# ---------------------------------------------------------------------------
# Kivy UI classes — only imported when a Kivy event loop is present
# ---------------------------------------------------------------------------

try:
    from kivy.clock import Clock
    from kivy.properties import ObjectProperty, StringProperty
    from kivy.uix.modalview import ModalView
    from kivy.uix.screenmanager import Screen

    from dmccodegui.utils import jobs

    # ------------------------------------------------------------------
    # FileChooserOverlay
    # ------------------------------------------------------------------

    class FileChooserOverlay(ModalView):
        """Modal file chooser for selecting a profile CSV.

        The ``on_file_selected`` callback receives the selected file path
        as its sole argument.
        """

        on_file_selected: Optional[Callable[[str], None]] = None

        def confirm_selection(self) -> None:
            """Dismiss overlay and invoke the callback with the chosen path."""
            try:
                chooser = self.ids.chooser
                if chooser.selection:
                    path = chooser.selection[0]
                    self.dismiss()
                    if callable(self.on_file_selected):
                        self.on_file_selected(path)
            except Exception:
                self.dismiss()

    # ------------------------------------------------------------------
    # DiffDialog
    # ------------------------------------------------------------------

    class DiffDialog(ModalView):
        """Modal diff dialog showing changed values before import.

        The ``on_apply`` callback is invoked when the user confirms import.
        """

        on_apply: Optional[Callable[[], None]] = None

        def build_diff_table(self, changes: list) -> None:
            """Populate the diff grid with one row per changed parameter.

            Each change dict must have keys: 'name', 'current', 'new'.
            """
            from kivy.uix.label import Label

            try:
                grid = self.ids.diff_grid
            except Exception:
                return

            grid.clear_widgets()

            # Header row
            for text, color in [
                ("Parameter", [0.4, 0.8, 1.0, 1]),
                ("Current",   [0.9, 0.9, 0.9, 1]),
                ("New",       [0.133, 0.773, 0.369, 1]),
            ]:
                lbl = Label(
                    text=text,
                    bold=True,
                    font_size="16sp",
                    color=color,
                    size_hint_y=None,
                    height="36dp",
                    halign="center",
                    valign="middle",
                )
                lbl.bind(size=lbl.setter("text_size"))
                grid.add_widget(lbl)

            # Data rows
            for ch in changes:
                for col_key, col_color in [
                    ("name",    [0.9, 0.9, 0.9, 1]),
                    ("current", [0.7, 0.7, 0.7, 1]),
                    ("new",     [0.133, 0.773, 0.369, 1]),
                ]:
                    lbl = Label(
                        text=str(ch.get(col_key, "")),
                        font_size="15sp",
                        color=col_color,
                        size_hint_y=None,
                        height="32dp",
                        halign="center",
                        valign="middle",
                    )
                    lbl.bind(size=lbl.setter("text_size"))
                    grid.add_widget(lbl)

        def apply_changes(self) -> None:
            """Dismiss and trigger the on_apply callback."""
            self.dismiss()
            if callable(self.on_apply):
                self.on_apply()

    # ------------------------------------------------------------------
    # ProfilesScreen
    # ------------------------------------------------------------------

    class ProfilesScreen(Screen):
        """Kivy Screen for importing and exporting knife profiles."""

        controller = ObjectProperty(None, allownone=True)
        state = ObjectProperty(None, allownone=True)

        # Status label text updated after export/import operations
        status_text = StringProperty("")

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._unsubscribe: Optional[Callable[[], None]] = None
            # Retain last parsed CSV data between parse and apply steps
            self._pending_parsed: Optional[dict] = None

        # ------------------------------------------------------------------
        # Lifecycle
        # ------------------------------------------------------------------

        def on_pre_enter(self, *args) -> None:
            """Subscribe to state changes, fire hmiSetp if needed, and update import button interlock."""
            from dmccodegui.hmi.dmc_vars import HMI_SETP, HMI_TRIGGER_FIRE, STATE_SETUP

            # Smart-enter: only send hmiSetp=0 if not already in setup mode
            already_in_setup = self.state is not None and self.state.dmc_state == STATE_SETUP
            if self.controller is not None and self.controller.is_connected() and not already_in_setup:
                try:
                    self.controller.cmd(f"{HMI_SETP}={HMI_TRIGGER_FIRE}")
                except Exception:
                    pass

            if self.state is not None:
                self._unsubscribe = self.state.subscribe(
                    lambda s: Clock.schedule_once(lambda *_: self._update_import_button())
                )
            self._update_import_button()

        def on_leave(self, *args) -> None:
            """Unsubscribe from state changes and send hmiExSt=0 to exit setup mode."""
            from dmccodegui.hmi.dmc_vars import HMI_EXIT_SETUP, HMI_TRIGGER_FIRE

            # Exit setup mode — profiles always fires exit on leave (no sibling check needed)
            if self.controller is not None and self.controller.is_connected():
                try:
                    self.controller.cmd(f"{HMI_EXIT_SETUP}={HMI_TRIGGER_FIRE}")
                except Exception:
                    pass

            if self._unsubscribe is not None:
                self._unsubscribe()
                self._unsubscribe = None

        # ------------------------------------------------------------------
        # Role mode (no-op — tab visibility handles role gating)
        # ------------------------------------------------------------------

        def _apply_role_mode(self, setup_unlocked: bool) -> None:
            """No-op: tab visibility restricts access to Setup/Admin only."""

        # ------------------------------------------------------------------
        # Import button interlock
        # ------------------------------------------------------------------

        def _update_import_button(self) -> None:
            """Disable import button when motion is active or disconnected."""
            try:
                btn = self.ids.import_btn
            except Exception:
                return
            if self.state is None:
                motion_active = False
            else:
                from dmccodegui.hmi.dmc_vars import STATE_GRINDING, STATE_HOMING
                motion_active = (
                    not self.state.connected
                    or self.state.dmc_state in (STATE_GRINDING, STATE_HOMING)
                )
            btn.disabled = motion_active
            btn.opacity = 0.4 if motion_active else 1.0

        # ------------------------------------------------------------------
        # Export flow
        # ------------------------------------------------------------------

        def on_export_press(self) -> None:
            """Show the export name popup."""
            from kivy.uix.popup import Popup
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.textinput import TextInput
            from kivy.uix.button import Button
            from kivy.uix.label import Label

            content = BoxLayout(orientation="vertical", padding="12dp", spacing="10dp")
            lbl = Label(
                text="Enter profile name:",
                font_size="18sp",
                size_hint_y=None,
                height="36dp",
                halign="left",
                valign="middle",
            )
            lbl.bind(size=lbl.setter("text_size"))
            content.add_widget(lbl)

            ti = TextInput(
                multiline=False,
                font_size="20sp",
                size_hint_y=None,
                height="48dp",
            )
            content.add_widget(ti)

            btn_row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height="52dp",
                spacing="12dp",
            )
            save_btn = Button(
                text="Save",
                font_size="18sp",
                background_normal="",
                background_color=(0.133, 0.773, 0.369, 1),
            )
            cancel_btn = Button(
                text="Cancel",
                font_size="18sp",
                background_normal="",
                background_color=(0.4, 0.4, 0.4, 1),
            )
            btn_row.add_widget(save_btn)
            btn_row.add_widget(cancel_btn)
            content.add_widget(btn_row)

            popup = Popup(
                title="Export Profile",
                content=content,
                size_hint=(0.5, 0.4),
                auto_dismiss=False,
            )
            save_btn.bind(on_release=lambda *_: (popup.dismiss(), self._do_export(ti.text.strip())))
            cancel_btn.bind(on_release=lambda *_: popup.dismiss())
            popup.open()

        def _do_export(self, profile_name: str) -> None:
            """Validate name, check overwrite, then trigger export."""
            if not profile_name:
                self.status_text = "Export cancelled: profile name cannot be empty."
                return

            path = get_profiles_dir() / f"{profile_name}.csv"

            if path.exists():
                self._confirm_overwrite(path, profile_name)
            else:
                self._run_export(path, profile_name)

        def _confirm_overwrite(self, path: Path, profile_name: str) -> None:
            """Show overwrite confirmation popup."""
            from kivy.uix.popup import Popup
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.button import Button
            from kivy.uix.label import Label

            content = BoxLayout(orientation="vertical", padding="12dp", spacing="10dp")
            lbl = Label(
                text=f"'{profile_name}.csv' already exists.\nOverwrite?",
                font_size="18sp",
                halign="center",
                valign="middle",
            )
            lbl.bind(size=lbl.setter("text_size"))
            content.add_widget(lbl)

            btn_row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height="52dp",
                spacing="12dp",
            )
            overwrite_btn = Button(
                text="Overwrite",
                font_size="18sp",
                background_normal="",
                background_color=(0.9, 0.3, 0.3, 1),
            )
            cancel_btn = Button(
                text="Cancel",
                font_size="18sp",
                background_normal="",
                background_color=(0.4, 0.4, 0.4, 1),
            )
            btn_row.add_widget(overwrite_btn)
            btn_row.add_widget(cancel_btn)
            content.add_widget(btn_row)

            popup = Popup(
                title="Overwrite Profile?",
                content=content,
                size_hint=(0.5, 0.35),
                auto_dismiss=False,
            )
            overwrite_btn.bind(on_release=lambda *_: (popup.dismiss(), self._run_export(path, profile_name)))
            cancel_btn.bind(on_release=lambda *_: popup.dismiss())
            popup.open()

        def _run_export(self, path: Path, profile_name: str) -> None:
            """Read all scalars and arrays from controller in background then write CSV."""
            if self.controller is None:
                self.status_text = "Export failed: no controller connected."
                return

            ctrl = self.controller

            def _job():
                import dmccodegui.machine_config as mc
                scalars: dict[str, Any] = {}
                arrays: dict[str, list] = {}

                # Read scalars
                for p in mc.get_param_defs():
                    var = p["var"]
                    try:
                        raw = ctrl.cmd(f"MG {var}")
                        scalars[var] = float(raw.strip())
                    except Exception:
                        pass

                # Read arrays
                for array_name in KNOWN_ARRAYS:
                    try:
                        values = ctrl.upload_array_auto(array_name)
                        if values is not None:
                            arrays[array_name] = list(values)
                    except Exception:
                        arrays[array_name] = []

                # Write CSV
                try:
                    export_profile(path, profile_name, scalars, arrays)
                    msg = f"Exported '{profile_name}' to {path.name}"
                except Exception as exc:
                    msg = f"Export failed: {exc}"

                Clock.schedule_once(lambda *_: setattr(self, "status_text", msg))

            jobs.submit(_job)
            self.status_text = "Exporting…"

        # ------------------------------------------------------------------
        # Import flow
        # ------------------------------------------------------------------

        def on_import_press(self) -> None:
            """Open the file chooser overlay."""
            overlay = FileChooserOverlay(
                auto_dismiss=False,
                size_hint=(1, 1),
            )
            overlay.ids.chooser.path = str(get_profiles_dir())
            overlay.ids.chooser.filters = ["*.csv", "*.CSV"]
            overlay.on_file_selected = self._on_file_selected
            overlay.open()

        def _on_file_selected(self, path: str) -> None:
            """Parse the chosen CSV, validate, read controller values, show diff."""
            try:
                parsed = parse_profile_csv(Path(path))
            except Exception as exc:
                self._show_error_popup(f"Could not read CSV:\n{exc}")
                return

            errors = validate_import(parsed)
            if errors:
                self._show_error_popup("Import validation failed:\n\n" + "\n".join(errors))
                return

            # Valid — read current controller values then show diff
            if self.controller is None:
                self._show_error_popup("Cannot read current values: no controller connected.")
                return

            ctrl = self.controller
            self._pending_parsed = parsed

            def _job():
                import dmccodegui.machine_config as mc
                current_scalars: dict[str, Any] = {}
                current_arrays: dict[str, list] = {}

                for p in mc.get_param_defs():
                    var = p["var"]
                    try:
                        raw = ctrl.cmd(f"MG {var}")
                        current_scalars[var] = float(raw.strip())
                    except Exception:
                        pass

                for array_name in KNOWN_ARRAYS:
                    try:
                        values = ctrl.upload_array_auto(array_name)
                        current_arrays[array_name] = list(values) if values else []
                    except Exception:
                        current_arrays[array_name] = []

                changes = compute_diff(
                    parsed["scalars"], current_scalars,
                    parsed["arrays"], current_arrays,
                )

                def _on_ui(*_):
                    self._show_diff_dialog(parsed, changes)

                Clock.schedule_once(_on_ui)

            jobs.submit(_job)
            self.status_text = "Reading current values…"

        def _show_diff_dialog(self, parsed: dict, changes: list) -> None:
            """Display the diff dialog and wire Apply button."""
            dialog = DiffDialog(auto_dismiss=False, size_hint=(0.9, 0.85))

            def _apply():
                self._apply_import(parsed)

            dialog.on_apply = _apply
            dialog.open()
            dialog.build_diff_table(changes)

        def _apply_import(self, parsed: dict) -> None:
            """Write CSV values to controller and burn NV in background."""
            if self.controller is None:
                self.status_text = "Import failed: no controller connected."
                return

            ctrl = self.controller

            def _job():
                # Write scalars
                for var, val in parsed["scalars"].items():
                    try:
                        ctrl.cmd(f"{var}={val}")
                    except Exception:
                        pass

                # Write arrays
                for array_name, values in parsed["arrays"].items():
                    if values:
                        try:
                            ctrl.download_array_full(array_name, values)
                        except Exception:
                            pass

                # Burn NV memory
                try:
                    ctrl.cmd("BV")
                    msg = f"Imported profile '{parsed.get('profile_name', '')}' — burned to NV."
                except Exception as exc:
                    msg = f"Import applied but BV burn failed: {exc}"

                Clock.schedule_once(lambda *_: setattr(self, "status_text", msg))

            jobs.submit(_job)
            self.status_text = "Applying import…"

        # ------------------------------------------------------------------
        # Helpers
        # ------------------------------------------------------------------

        def _show_error_popup(self, message: str) -> None:
            """Display an error message in a simple popup."""
            from kivy.uix.popup import Popup
            from kivy.uix.label import Label

            lbl = Label(
                text=message,
                font_size="17sp",
                halign="center",
                valign="middle",
            )
            lbl.bind(size=lbl.setter("text_size"))
            popup = Popup(
                title="Error",
                content=lbl,
                size_hint=(0.6, 0.4),
            )
            popup.open()

except ImportError:
    # Kivy not available (headless test environment) — skip UI classes silently.
    pass
