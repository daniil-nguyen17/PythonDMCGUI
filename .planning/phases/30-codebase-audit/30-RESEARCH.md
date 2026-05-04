# Phase 30: Codebase Audit - Research

**Researched:** 2026-05-04
**Domain:** Python static analysis, linting, docstring standards, dead code detection
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Docstring scope and style**
- Google-style docstrings (summary + Args/Returns/Raises sections)
- All public classes and functions require docstrings
- Private methods with non-obvious logic (state machines, DMC protocol, complex callbacks) also get docstrings
- Kivy callback methods referenced from .kv files are treated as public — they get docstrings
- Class docstrings are developer-facing: describe what the class does and how it integrates, not what the user sees

**Dead code handling**
- Vulture at 80% confidence threshold (matches ROADMAP.md success criteria)
- Auto-generate allowlist from .kv files — parse all .kv files, extract method/property references, generate `.vulture_allowlist.py`
- Audit both .py AND .kv files — orphaned KV rules (no matching Python class) are flagged as dead UI code
- Borderline code: comment out with `# DEAD_CODE` marker, don't delete. Clean removal in next milestone if nothing breaks
- No exceptions — all files go through the same pipeline, no sacred modules
- Codebase is truth: if a feature works and is reachable at runtime, it stays regardless of documentation state
- Ruff config lives in pyproject.toml, vulture allowlist as separate `.vulture_allowlist.py` file
- Add ruff and vulture to `[project.optional-dependencies] dev` group

**Naming conventions**
- Logger variable standardized to `logger` (rename controller.py's `log` to `logger`)
- Enforce snake_case for functions/variables, PascalCase for classes via ruff N-rules
- `dmc_vars.py` is exempt from naming rules — DMC variable names are a hardware contract (8-char camelCase names must match controller exactly)
- Kivy properties follow regular snake_case — no special suffix or prefix

**Ruff rule selection**
- Standard rule set: E (errors) + F (pyflakes) + I (isort) + N (naming) + W (warnings)
- Line length: 120 characters
- Import ordering: stdlib -> third-party -> local, blank line between groups
- Auto-fix safe rules (import sorting, unused import removal, whitespace). Manually review unsafe fixes
- Config lives in `[tool.ruff]` section of pyproject.toml

### Claude's Discretion
- Specific ruff rule exceptions/ignores for Kivy patterns (e.g., unused `app` import in kv-loading modules)
- Order of operations within the audit (imports first vs dead code first)
- How to structure the allowlist generation script
- Whether to add a `make lint` or similar developer convenience command

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUDIT-01 | All dead code identified by ruff + vulture is removed (with Kivy `_REGISTRY` allowlist) | Vulture 2.16 allowlist format, `# type: ignore` pattern for KV-referenced symbols, `.vulture_allowlist.py` at repo root |
| AUDIT-02 | All unused imports removed and import ordering standardized across the codebase | Ruff I-rules (isort), F401 (unused imports), `--select I` check, safe auto-fix available |
| AUDIT-03 | Docstrings updated on all public classes and functions to reflect current behavior | Coverage gaps identified per-file; jobs.py, transport.py, app_state.py are primary targets |
| AUDIT-04 | Naming conventions consistent across modules (no mixed `log`/`logger`, no stale variable names) | Exactly one outlier: `controller.py` line 12 uses `log`; ruff N-rules enforce snake_case/PascalCase |
</phase_requirements>

---

## Summary

The codebase is 44 Python source files (~8,200 lines) with a well-established `logger = logging.getLogger(__name__)` pattern — one outlier (`controller.py` uses `log`). Docstring coverage is uneven: core screens and HMI modules are reasonably covered, but `utils/jobs.py` is notably sparse (15 defs, 7 docstring markers), and `utils/transport.py` has minimal docstring coverage (8 defs, 2 docstring markers). `app_state.py` has missing docstrings on `subscribe`, `notify`, `set_connected`, and several other methods. The import ordering problem is structural: `flat_grind/run.py` mixes stdlib → Kivy → matplotlib in a non-standard interleaved order.

The dead code situation requires careful handling. `screens/flat_grind_widgets.py`, `screens/run.py`, `screens/parameters.py`, and `screens/axes_setup.py` are backward-compatibility shims — they are still imported via `screens/__init__.py` and are live, not dead. The `hmi/poll.py` `ControllerPoller` class warrants investigation: `DataRecordListener` replaced it in production, but `ControllerPoller` still lives in the file and may be a genuine dead-code candidate (though it is referenced in 28 tests). The vulture allowlist must cover all `root.*` and `app.*` method references from KV files — approximately 90 unique method/property names identified across 21 KV files.

**Primary recommendation:** Run the audit in three sequential passes — (1) ruff --fix for safe auto-fixes (imports, whitespace), (2) manual dead code pass with vulture + allowlist, (3) docstring completion pass. This ordering prevents docstring work on code that gets removed.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ruff | 0.15.12 (latest) | Linting + import sorting + naming enforcement | Single tool replacing flake8+isort+pep8-naming; fast, configurable in pyproject.toml |
| vulture | 2.16 (latest) | Dead code detection | Purpose-built for Python dead code; supports allowlist files; 80% confidence threshold reduces false positives |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | already in dev deps | Run test suite after each wave to confirm no behavioral changes | After every code modification wave |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| vulture allowlist file | `# noqa: vulture` inline comments | Inline comments scatter suppression; allowlist is easier to audit and review |
| ruff N-rules | pylint naming checks | ruff is already the chosen tool; no need for pylint |

**Installation (add to pyproject.toml dev group):**
```bash
pip install "ruff>=0.15" "vulture>=2.16"
```

---

## Architecture Patterns

### Recommended Project Structure (no changes — audit adds two new files)
```
repo-root/
├── pyproject.toml          # [tool.ruff] config added here
├── .vulture_allowlist.py   # NEW: auto-generated from KV file references
├── src/dmccodegui/
│   └── ... (all 44 .py files touched)
└── tests/
    └── test_lint.py        # NEW: ruff and vulture CI gate
```

### Pattern 1: Ruff Config in pyproject.toml
**What:** All ruff configuration lives in `[tool.ruff]` and `[tool.ruff.lint]` sections.
**When to use:** Always — single source of truth for linting.
**Example:**
```toml
# Source: ruff official docs
[tool.ruff]
line-length = 120
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = [
    "N999",   # module name (dmc_vars uses camelCase DMC names — exempt at file level)
    "E501",   # line-too-long (handled by line-length setting above)
]

[tool.ruff.lint.per-file-ignores]
"src/dmccodegui/hmi/dmc_vars.py" = ["N"]       # hardware contract names
"src/dmccodegui/screens/flat_grind_widgets.py" = ["F401"]  # backward-compat re-exports
"src/dmccodegui/screens/run.py" = ["F401"]     # backward-compat re-exports
"src/dmccodegui/screens/parameters.py" = ["F401"]  # backward-compat re-exports
"src/dmccodegui/screens/axes_setup.py" = ["F401"]  # backward-compat re-exports
"src/dmccodegui/screens/__init__.py" = ["F401"]    # package public API re-exports
```

### Pattern 2: Vulture Allowlist Generation
**What:** A Python script parses all `.kv` files, extracts `root.<name>` and `app.<name>` references, and writes a `.vulture_allowlist.py` that declares each name as a used attribute.
**When to use:** Run before the vulture pass, and re-run any time KV files change.
**Example:**
```python
# .vulture_allowlist.py (auto-generated — do not edit manually)
# Source: vulture docs — whitelists are valid Python with unused assignments
from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen
from dmccodegui.screens.serration.run import SerrationRunScreen
# ... (one entry per KV-referenced method/property)

# Suppress false positives for KV-referenced symbols:
FlatGrindRunScreen.on_start_grind
FlatGrindRunScreen.motion_active
# ...
```

The generator script reads all `.kv` files with `grep -h "root\.\|app\."`, extracts names, and resolves them to their Python class via the KV `<ClassName>:` rule header.

### Pattern 3: Import Ordering (ruff isort)
**What:** stdlib imports first, then third-party (kivy, matplotlib, gclib), then local (relative). One blank line between groups. `from __future__ import annotations` always first.
**Current violation in flat_grind/run.py:**
```python
# WRONG (current): stdlib, then kivy, then matplotlib mid-block
from __future__ import annotations
import logging
import sys
# ... (more stdlib)
from kivy.clock import Clock     # <- third-party starts here
from kivy.core.text import ...
import matplotlib.pyplot          # <- should be in same third-party block as kivy
```
**Correct (after ruff --fix --select I):**
```python
from __future__ import annotations

import logging
import sys
import threading
import time
from collections import deque

import matplotlib.pyplot          # third-party block
import kivy_matplotlib_widget
from kivy.clock import Clock
# ...

from ...app_state import MachineState   # local block
# ...
```

### Pattern 4: Google-Style Docstrings
**What:** Summary line, blank line, then Args/Returns/Raises sections as needed.
**When to use:** All public classes, all public functions, private methods with non-obvious logic.
```python
def submit_urgent(self, fn: JobFn, *args: Any, **kwargs: Any) -> None:
    """Submit an urgent job that preempts queued normal jobs.

    Sets the cancel_event so in-flight normal jobs can check and yield
    early. Drains any stale entry from the urgent queue before placing
    the new one.

    Args:
        fn: Callable to execute on the worker thread.
        *args: Positional arguments forwarded to fn.
        **kwargs: Keyword arguments forwarded to fn.
    """
```

### Anti-Patterns to Avoid
- **Deleting borderline dead code directly:** If vulture flags something at 80-90% confidence and it's unclear, use `# DEAD_CODE` comment-out, not deletion. Deletion is irreversible; comment-out is auditable.
- **Running ruff --fix on everything at once without review:** Safe fixes (import sorting, whitespace) are fine. Unsafe fixes (e.g., removing an import that's only used in a `# type: ignore` context) need manual review.
- **Writing allowlist entries without class context:** Vulture needs `ClassName.method_name` not just `method_name` in the allowlist, or it will still report false positives.
- **Applying N-rules to dmc_vars.py:** The 8-char camelCase DMC variable names (e.g., `hmiGrnd`, `hmiSetp`) are a hardware contract — N-rules must be suppressed per-file for this module.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Import sorting | Custom sort script | `ruff check --select I --fix` | Handles edge cases: `from __future__`, TYPE_CHECKING blocks, `# noqa` markers |
| Unused import detection | `grep -n "^import"` script | `ruff check --select F401` | Knows about `__all__`, re-exports, TYPE_CHECKING blocks |
| Dead code detection | Manual grep for uncalled functions | `vulture . --min-confidence 80` | Handles: properties, class attributes, `__all__`, dynamic dispatch patterns |
| KV reference extraction | Ad-hoc regex | Dedicated generator script using `re.findall(r'root\.(\w+)\|app\.(\w+)', kv_text)` | Systematic, repeatable, produces valid Python allowlist |

**Key insight:** The main dead code complexity in a Kivy app is that Python methods called from `.kv` files appear "unused" to static analysis. The allowlist approach is the established solution — vulture's own docs cover this pattern.

---

## Common Pitfalls

### Pitfall 1: Backward-Compat Shims Look Dead But Are Live
**What goes wrong:** Vulture flags `screens/flat_grind_widgets.py`, `screens/run.py`, `screens/parameters.py`, `screens/axes_setup.py` as dead because they just re-export from the subpackage.
**Why it happens:** They use `# noqa: F401` on imports, so ruff won't complain, but vulture sees the module-level names as never called.
**How to avoid:** These four shim files must be in the vulture allowlist — they are consumed transitively via `screens/__init__.py` which exports them in `__all__`.
**Warning signs:** Vulture reporting entire modules as "unused" rather than individual functions.

### Pitfall 2: Kivy `on_*` Observer Methods Trigger False Positives
**What goes wrong:** Methods like `on_connected`, `on_machine_type`, `on_dmc_state` are Kivy property observers defined in Python but called by the Kivy event system — never called directly in Python code.
**Why it happens:** Vulture cannot see the Kivy property dispatch mechanism.
**How to avoid:** Include all `on_<property_name>` methods in the vulture allowlist. The KV file scanner catches `on_press`/`on_release` but misses Python-side property observers defined directly in Python classes.
**Warning signs:** A legitimate `on_connected(self, instance, value)` method being flagged.

### Pitfall 3: `ControllerPoller` — Live in Tests, Potentially Dead in Production
**What goes wrong:** `hmi/poll.py`'s `ControllerPoller` class was replaced by `DataRecordListener` in production (`main.py` uses only `DataRecordListener`). However, 28 test files reference it.
**Why it happens:** DR migration plan left `ControllerPoller` in place as a fallback/reference.
**How to avoid:** Do NOT remove `ControllerPoller` during this phase — tests depend on it, and it is part of the live codebase by the "codebase is truth" rule. Flag with `# DEAD_CODE` only if confirmed unreachable from `main.py` and tests are updated. This is a Phase 30 investigation item, not a removal item.
**Warning signs:** Test failures in `test_poll.py`, `test_run_screen.py`, `test_machine_state_cycle.py` after any change to `poll.py`.

### Pitfall 4: N-Rules Conflict with Kivy Property Names
**What goes wrong:** Ruff N-rules (N815, N816) may flag Kivy properties defined as class-level names if they are `mixedCase` or have non-standard casing.
**Why it happens:** Kivy properties must be lowercase/snake_case by convention, but the rule check can also flag constants in the Kivy widget base classes.
**How to avoid:** Kivy properties in this codebase already use snake_case (`pos_a`, `motion_active`, `cycle_completion_pct`) — no violations expected. The risk is with any DMC variable names that leak into non-exempt files via import.

### Pitfall 5: Import in transport.py Uses a `TYPE_CHECKING` Pattern Incorrectly
**What goes wrong:** `transport.py` has a `try/except ImportError` block at module level for `GalilDriverProtocol` — this is not a standard `TYPE_CHECKING` guard and will be flagged by ruff as a bare `except` or import-order violation.
**Why it happens:** The module was structured to allow import without gclib installed, using a runtime fallback.
**How to avoid:** Treat this as a known pattern — add a targeted `# noqa` on that block or restructure to use the standard `TYPE_CHECKING` pattern. Don't let ruff --fix alter this silently.

### Pitfall 6: `sys` Import in flat_grind/run.py May Be Unused
**What goes wrong:** `flat_grind/run.py` imports `sys` (line 5) — needs verification that it's actually used in the file.
**Why it happens:** Stale import from an earlier version of the file.
**How to avoid:** `ruff check --select F401` will flag this automatically. Safe to let `--fix` remove it.

---

## Code Examples

Verified patterns from official sources:

### Running ruff check (lint only)
```bash
# Check all rules, no auto-fix
ruff check src/

# Check import ordering only
ruff check --select I src/

# Auto-fix safe rules (imports, whitespace)
ruff check --fix src/

# Show what would be fixed without applying
ruff check --fix --diff src/
```

### Running vulture
```bash
# Basic run — 80% confidence threshold, with allowlist
vulture src/ .vulture_allowlist.py --min-confidence 80

# Generate a starter allowlist from vulture itself (then prune false positives)
vulture src/ --make-whitelist > .vulture_allowlist.py
```

### Vulture Allowlist Structure
```python
# .vulture_allowlist.py
# Auto-generated by scripts/gen_vulture_allowlist.py
# DO NOT EDIT MANUALLY — regenerate with: python scripts/gen_vulture_allowlist.py

# KV-referenced methods on screen classes
from dmccodegui.screens.flat_grind.run import FlatGrindRunScreen  # noqa: F401
FlatGrindRunScreen.on_start_grind  # used in flat_grind/run.kv
FlatGrindRunScreen.on_shutdown     # used in flat_grind/run.kv
FlatGrindRunScreen.motion_active   # used in flat_grind/run.kv (KV binding)
# ...

# machine_config._REGISTRY — accessed dynamically via string keys
from dmccodegui import machine_config  # noqa: F401
machine_config._REGISTRY              # accessed via mc._REGISTRY[key] in main.py
```

### pyproject.toml ruff config (complete)
```toml
[tool.ruff]
line-length = 120
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = []

[tool.ruff.lint.per-file-ignores]
"src/dmccodegui/hmi/dmc_vars.py" = ["N"]
"src/dmccodegui/screens/flat_grind_widgets.py" = ["F401"]
"src/dmccodegui/screens/run.py" = ["F401"]
"src/dmccodegui/screens/parameters.py" = ["F401"]
"src/dmccodegui/screens/axes_setup.py" = ["F401"]
"src/dmccodegui/screens/__init__.py" = ["F401"]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| flake8 + isort + pep8-naming (3 tools) | ruff (single tool) | ruff 0.1+ (2023) | Single config, 10-100x faster, same rule coverage |
| vulture inline `# noqa` suppression | `.vulture_allowlist.py` file | vulture 2.0+ | Centralised, auditable suppression list |
| `# type: ignore[misc]` for Kivy properties | `# noqa: N` per-file-ignore | n/a | Cleaner than scattered inline ignores |

**Deprecated/outdated:**
- `flake8`: Superseded by ruff for this project — do not add flake8 to dev deps.
- `isort` standalone: ruff I-rules replace isort entirely.
- `pep8-naming` plugin: Replaced by ruff N-rules.

---

## Docstring Coverage Gaps (by file)

Identified files with clear docstring gaps requiring work in AUDIT-03:

| File | Defs | Docstring markers | Gap severity |
|------|------|-------------------|--------------|
| `utils/jobs.py` | 15 | 7 | HIGH — `stop`, `submit`, `_run`, `get_jobs`, `submit`, `schedule`, `shutdown` module-level functions lack docstrings |
| `utils/transport.py` | 8 | 2 | HIGH — `open`, `close`, `is_connected`, `command`, `_ensure_driver` undocumented |
| `app_state.py` | 11 | 4 | MEDIUM — `subscribe`, `notify`, `set_connected`, `update_status`, `log`, `clear_messages`, `set_auth`, `lock_setup` undocumented |
| `controller.py` | 39 | 22 | MEDIUM — several commented-out docstrings (lines 327-330, 400-405, 594, 633) |
| `screens/flat_grind/widgets.py` | 15 | 12 | LOW — minor gaps |
| `screens/convex/widgets.py` | 2 | 4 | OK (well documented, TODO markers are intentional pending customer spec) |

---

## Open Questions

1. **Is `ControllerPoller` in hmi/poll.py dead code or intentional fallback?**
   - What we know: `main.py` exclusively uses `DataRecordListener`. `ControllerPoller` still exists in `poll.py` and is referenced in test files.
   - What's unclear: Whether tests import `ControllerPoller` directly (in which case it's live for testing) or whether it's only referenced in test comments.
   - Recommendation: Audit test imports before flagging — if tests import `ControllerPoller` directly, it stays. If tests only reference it via `MachineState`, the class may be a `# DEAD_CODE` candidate.

2. **Orphaned KV class rules: `<RunScreen>:`, `<AxesSetupScreen>:`, `<ParametersScreen>:`**
   - What we know: `ui/run.kv`, `ui/parameters.kv` and `ui/axes_setup.kv` define rules for the flat-grind backward-compat aliases. These are loaded when the app runs.
   - What's unclear: Are these KV rules actually used at runtime when the machine type is Flat Grind (which loads `FlatGrindRunScreen` directly), or are they dead UI rules?
   - Recommendation: Trace through `main.py`'s dynamic screen loading via `_REGISTRY["screen_classes"]` to confirm. If `RunScreen` is never instantiated at runtime, the KV rule is dead UI code.

3. **Ruff N-rules and `_SERRATION_EXCLUDE` set literal**
   - What we know: `machine_config.py` has `_SERRATION_EXCLUDE = {"fdD", "pitchD", ...}` — lowercase private set with mixed-case string values. The strings are DMC variable names.
   - What's unclear: Whether ruff N-rules will flag the string contents (they shouldn't — strings are not identifiers).
   - Recommendation: This is almost certainly fine — ruff N-rules apply to Python identifiers only, not string literals.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already in dev deps) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` section |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUDIT-01 | `vulture src/ .vulture_allowlist.py --min-confidence 80` exits 0 | smoke | `python -m vulture src/ .vulture_allowlist.py --min-confidence 80` | ❌ Wave 0 — `.vulture_allowlist.py` must exist first |
| AUDIT-02 | `ruff check --select I src/` exits 0 | smoke | `ruff check --select I src/` | ❌ Wave 0 — ruff config in pyproject.toml first |
| AUDIT-03 | All public classes/functions have non-empty docstrings | unit | `pytest tests/test_docstrings.py -x` | ❌ Wave 0 |
| AUDIT-04 | No file uses `log =` pattern; ruff N passes | smoke | `ruff check --select N src/ && python -c "import subprocess; r=subprocess.run(['grep','-rn','log = logging','.'],capture_output=True); exit(1 if r.stdout else 0)"` | ❌ Wave 0 — ruff config needed |

### Sampling Rate
- **Per task commit:** `ruff check src/ && pytest tests/ -x -q`
- **Per wave merge:** `ruff check src/ && vulture src/ .vulture_allowlist.py --min-confidence 80 && pytest tests/ -v`
- **Phase gate:** Full suite + ruff + vulture all green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `pyproject.toml` — add `[tool.ruff]` and `[tool.ruff.lint]` config sections + add ruff and vulture to dev deps
- [ ] `.vulture_allowlist.py` — auto-generated at repo root from KV file scanner
- [ ] `scripts/gen_vulture_allowlist.py` — KV reference extraction script (or inline generation)
- [ ] `tests/test_lint.py` — optional CI gate that runs ruff and vulture as subprocess calls

---

## Sources

### Primary (HIGH confidence)
- ruff 0.15.12 (pip index verified) — version confirmed on this machine
- vulture 2.16 (pip index verified) — version confirmed on this machine
- Direct codebase inspection — all findings based on live file reads

### Secondary (MEDIUM confidence)
- ruff documentation patterns — standard pyproject.toml config structure is well-established and stable

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified via pip index on this machine
- Architecture: HIGH — all findings based on direct codebase inspection
- Pitfalls: HIGH — all pitfalls identified from actual code patterns found in the repo
- Docstring gaps: HIGH — counted from grep output on live files

**Research date:** 2026-05-04
**Valid until:** 2026-06-04 (ruff releases frequently but config format is stable; vulture allowlist format is stable)
