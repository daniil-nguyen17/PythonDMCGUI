"""Auto-generate .vulture_allowlist.py from .kv file references.

Parses all .kv files under src/dmccodegui/ui/ and extracts:
  - root.<name> references (methods and properties on the KV rule class)
  - app.<name> references (methods on the App class)

Also includes:
  - machine_config._REGISTRY (accessed dynamically by string key)
  - Backward-compat shim modules that re-export under old names
  - Kivy lifecycle observer methods (on_kv_post, on_pre_enter, on_leave, etc.)
    that are called by the framework, not directly referenced in Python

Usage:
    python scripts/gen_vulture_allowlist.py
    (run from repo root)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = REPO_ROOT / "src" / "dmccodegui" / "ui"
OUTPUT = REPO_ROOT / ".vulture_allowlist.py"

# ---------------------------------------------------------------------------
# KV class name -> Python class name overrides
# Some KV rule names don't exactly match Python class names.
# ---------------------------------------------------------------------------
KV_TO_PYTHON_CLASS: dict[str, str] = {
    "AxesSetupScreen": "BaseAxesSetupScreen",
    "ParametersScreen": "BaseParametersScreen",
    "RunScreen": "FlatGrindRunScreen",
    "RootLayout": None,  # anonymous KV dynamic class — skip
    "ActionButton": None,  # theme override rule — skip
    "Label": None,          # theme override rule — skip
    "Button": None,         # theme override rule — skip
    "ToggleButton": None,   # theme override rule — skip
    "TextInput": None,      # theme override rule — skip
    "Spinner": None,        # theme override rule — skip
    "SpinnerOption": None,  # theme override rule — skip
    "ImageButton": None,    # theme inline rule — skip
    "CenteredTextInput": None,  # theme inline rule — skip
    "VDivider": None,       # theme widget rule — skip
    "CardFrame": None,      # theme widget rule — skip
    "HControl": None,       # theme widget rule — skip
    "VControl": None,       # theme widget rule — skip
    "FileChooserOverlay": "FileChooserOverlay",
    "DiffDialog": "DiffDialog",
}

# ---------------------------------------------------------------------------
# Extra symbols that vulture cannot trace statically
# ---------------------------------------------------------------------------
EXTRA_ALLOWLIST: list[tuple[str, str]] = [
    # machine_config._REGISTRY is accessed via _REGISTRY[key] throughout the module
    ("machine_config", "_REGISTRY"),
    # Kivy framework lifecycle hooks — called by Kivy runtime, not explicit Python call sites
    ("BaseRunScreen", "on_kv_post"),
    ("BaseRunScreen", "on_pre_enter"),
    ("BaseRunScreen", "on_leave"),
    ("BaseAxesSetupScreen", "on_kv_post"),
    ("BaseAxesSetupScreen", "on_pre_enter"),
    ("BaseAxesSetupScreen", "on_leave"),
    ("BaseParametersScreen", "on_kv_post"),
    ("BaseParametersScreen", "on_pre_enter"),
    ("BaseParametersScreen", "on_leave"),
    ("FlatGrindRunScreen", "on_kv_post"),
    ("FlatGrindRunScreen", "on_pre_enter"),
    ("FlatGrindRunScreen", "on_leave"),
    ("SerrationRunScreen", "on_kv_post"),
    ("SerrationRunScreen", "on_pre_enter"),
    ("SerrationRunScreen", "on_leave"),
    ("ConvexRunScreen", "on_kv_post"),
    ("ConvexRunScreen", "on_pre_enter"),
    ("ConvexRunScreen", "on_leave"),
    ("FlatGrindAxesSetupScreen", "on_kv_post"),
    ("FlatGrindAxesSetupScreen", "on_pre_enter"),
    ("FlatGrindAxesSetupScreen", "on_leave"),
    ("SerrationAxesSetupScreen", "on_kv_post"),
    ("SerrationAxesSetupScreen", "on_pre_enter"),
    ("SerrationAxesSetupScreen", "on_leave"),
    ("ConvexAxesSetupScreen", "on_kv_post"),
    ("ConvexAxesSetupScreen", "on_pre_enter"),
    ("ConvexAxesSetupScreen", "on_leave"),
    ("FlatGrindParametersScreen", "on_kv_post"),
    ("FlatGrindParametersScreen", "on_pre_enter"),
    ("FlatGrindParametersScreen", "on_leave"),
    ("SerrationParametersScreen", "on_kv_post"),
    ("SerrationParametersScreen", "on_pre_enter"),
    ("SerrationParametersScreen", "on_leave"),
    ("ConvexParametersScreen", "on_kv_post"),
    ("ConvexParametersScreen", "on_pre_enter"),
    ("ConvexParametersScreen", "on_leave"),
    # DiagnosticsScreen — no methods in KV but lifecycle hooks still apply
    ("DiagnosticsScreen", "on_pre_enter"),
    ("DiagnosticsScreen", "on_leave"),
    # StatusBar — Kivy EventDispatcher binding triggers these
    ("StatusBar", "on_kv_post"),
    # PINOverlay — ModalView lifecycle
    ("PINOverlay", "on_kv_post"),
    ("PINOverlay", "on_pre_open"),
    # ProfilesScreen and overlays
    ("ProfilesScreen", "on_kv_post"),
    ("ProfilesScreen", "on_pre_enter"),
    ("ProfilesScreen", "on_leave"),
    # UsersScreen lifecycle
    ("UsersScreen", "on_kv_post"),
    ("UsersScreen", "on_pre_enter"),
    ("UsersScreen", "on_leave"),
    # SetupScreen lifecycle
    ("SetupScreen", "on_kv_post"),
    ("SetupScreen", "on_pre_enter"),
    ("SetupScreen", "on_leave"),
    # DataRecordListener — methods called from JobThread callbacks
    ("DataRecordListener", "on_disconnect"),
    ("DataRecordListener", "on_packet"),
    # AuthManager — called through dynamic dispatch
    ("AuthManager", "verify_pin"),
    # ThemeManager — bound in KV via app.toggle_theme
    ("ThemeManager", "toggle_theme"),
    # Widget drawing callbacks triggered by Kivy canvas
    ("DeltaCBarChart", "on_offsets"),
    ("DeltaCBarChart", "on_array_size"),
    ("CompVisualization", "on_pos"),
    ("CompVisualization", "on_size"),
    ("BCompVisualization", "on_pos"),
    ("BCompVisualization", "on_size"),
    ("CCompVisualization", "on_pos"),
    ("CCompVisualization", "on_size"),
    # CompPanel widget callbacks
    ("CompPanel", "on_kv_post"),
    ("BCompPanel", "on_kv_post"),
    ("CCompPanel", "on_kv_post"),
    # ConvexAdjustPanel callbacks
    ("ConvexAdjustPanel", "on_kv_post"),
    # on_selected_index for bar chart selection
    ("DeltaCBarChart", "on_selected_index"),
    # ImageButton — public widget
    ("ImageButton", "on_press"),
    # Backward-compat shim modules expose their re-exported names as public API
]

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
# Match <ClassName>: KV rule header (not @dynamic-class lines)
RE_CLASS_HEADER = re.compile(r"^<([A-Za-z][A-Za-z0-9_]*)>:\s*$")
# Match root.<name> or app.<name> attribute access
RE_ROOT_REF = re.compile(r"\broot\.([A-Za-z_][A-Za-z0-9_]*)")
RE_APP_REF = re.compile(r"\bapp\.([A-Za-z_][A-Za-z0-9_]*)")


def parse_kv_files() -> dict[str, set[str]]:
    """Parse all .kv files and return {python_class_name: {method_or_property, ...}}.

    Returns:
        Mapping from Python class name to set of referenced attribute names.
    """
    # class_refs[python_class] = set of attribute names referenced via root.*
    class_refs: dict[str, set[str]] = {}
    # app_refs[DMCApp] = set of app.* references
    app_refs: set[str] = set()

    kv_files = sorted(UI_DIR.rglob("*.kv"))
    if not kv_files:
        print(f"WARNING: no .kv files found under {UI_DIR}", file=sys.stderr)

    for kv_path in kv_files:
        current_class: str | None = None

        with open(kv_path, encoding="utf-8") as fh:
            for line in fh:
                # Check for new class rule header
                m = RE_CLASS_HEADER.match(line)
                if m:
                    kv_name = m.group(1)
                    python_name = KV_TO_PYTHON_CLASS.get(kv_name, kv_name)
                    current_class = python_name  # may be None → skip refs
                    if python_name and python_name not in class_refs:
                        class_refs[python_name] = set()
                    continue

                # Collect root.* references
                if current_class:
                    for attr in RE_ROOT_REF.findall(line):
                        class_refs[current_class].add(attr)

                # Always collect app.* references regardless of current class
                for attr in RE_APP_REF.findall(line):
                    app_refs.add(attr)

    if app_refs:
        class_refs.setdefault("DMCApp", set()).update(app_refs)

    return class_refs


def generate_allowlist(class_refs: dict[str, set[str]]) -> list[str]:
    """Generate allowlist lines in vulture format.

    Vulture recognises bare attribute accesses as "used" when they appear
    in the allowlist file. The pattern is:
        from module import ClassName
        ClassName.attribute_name

    We keep it simple by using the class name as a string to avoid import issues.

    Args:
        class_refs: Mapping from class name to set of referenced attributes.

    Returns:
        Lines to write to the allowlist file.
    """
    lines: list[str] = [
        "# Auto-generated by scripts/gen_vulture_allowlist.py -- DO NOT EDIT MANUALLY",
        "# Regenerate with: python scripts/gen_vulture_allowlist.py",
        "#",
        "# This file tells vulture which symbols are referenced from .kv files",
        "# (Kivy's declarative UI language) or from Kivy's internal framework",
        "# dispatch, and therefore must NOT be flagged as dead code.",
        "",
        "# ruff: noqa",
        "# flake8: noqa",
        "",
    ]

    # Build a sorted, deduplicated list of (class, attr) pairs
    pairs: list[tuple[str, str]] = []

    for class_name, attrs in sorted(class_refs.items()):
        for attr in sorted(attrs):
            pairs.append((class_name, attr))

    # Add extra allowlist entries
    for class_name, attr in EXTRA_ALLOWLIST:
        pairs.append((class_name, attr))

    # Deduplicate and sort
    pairs = sorted(set(pairs))

    # Group by class
    current_class: str | None = None
    for class_name, attr in pairs:
        if class_name != current_class:
            if current_class is not None:
                lines.append("")
            lines.append(f"# {class_name}")
            current_class = class_name
        lines.append(f"{class_name}.{attr}")

    lines.append("")
    return lines


def main() -> None:
    """Parse KV files and write .vulture_allowlist.py."""
    class_refs = parse_kv_files()
    allowlist_lines = generate_allowlist(class_refs)

    OUTPUT.write_text("\n".join(allowlist_lines), encoding="utf-8")
    print(f"Written: {OUTPUT}")
    print(f"  Classes: {len(class_refs)}")
    total_refs = sum(len(v) for v in class_refs.values())
    print(f"  KV-referenced attributes: {total_refs}")


if __name__ == "__main__":
    main()
