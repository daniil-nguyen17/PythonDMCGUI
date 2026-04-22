# Phase 28: Logging Infrastructure - Research

**Researched:** 2026-04-22
**Domain:** Python stdlib logging, PyInstaller datas exclusion, rsync exclusion, sys.excepthook
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Windows log path: `%APPDATA%/BinhAnHMI/logs/app.log` (Phase 24 path wins over SC-1)
- Pi/Linux log path: `~/.binh-an-hmi/logs/app.log`
- Rotation: 5 MB limit, 3 backup files — `logging.handlers.RotatingFileHandler`
- Format: `timestamp + level + module + message` (e.g., `2026-04-22 14:30:05 INFO [main] Starting app v4.0.0`)
- Dual output: file (RotatingFileHandler) AND console (StreamHandler)
- All 142 print() calls across 10 source files migrated to proper logger calls
- 3 ad-hoc `logging.getLogger(__name__)` calls in main.py consolidated into new setup
- `sys.excepthook` patched BEFORE Kivy import to capture ALL uncaught exceptions including Kivy internal errors
- On uncaught exception: log full traceback, then let app crash normally — no cleanup
- No gclib connection cleanup in excepthook — OS handles it
- PyInstaller bundle excludes: .md files, .planning/, tests/, .xlsx, .dmc, .git/, .claude/, deploy/, pyproject.toml, dotfiles
- rsync install.sh excludes: .md, .planning/, tests/, .xlsx, .dmc, .git/, .claude/, deploy/
- .dmc and .xlsx excluded from both packages — no separate optional bundle in this phase
- Add content-inspection test for bundle exclusion (scans dist/ output for forbidden file types)
- Add similar exclusion verification test for Pi rsync exclusion patterns in install.sh

### Claude's Discretion
- Exact logging configuration setup code structure
- Logger naming convention (module-level `__name__` loggers vs centralized)
- Which print() calls become info vs debug vs warning
- Exact rsync --exclude flag syntax in install.sh
- Test implementation for bundle content verification
- Whether to use logging.basicConfig or manual handler setup

### Deferred Ideas (OUT OF SCOPE)
- In-app log viewer (FUTURE-01): Admin modal showing last 200 lines of app.log
- Separate DMC/Excel bundle: zip of .dmc and .xlsx files alongside installer
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| APP-01 | Rotating log file writes to platform-correct location (APPDATA on Windows, ~/.binh-an-hmi/logs/ on Pi) with 5 MB limit and 3 backups | `RotatingFileHandler(path, maxBytes=5*1024*1024, backupCount=3)` — stdlib, no new deps |
| APP-02 | All uncaught exceptions are logged with full traceback before the app exits (sys.excepthook patched before Kivy import) | `sys.excepthook` receives `(exc_type, exc_value, exc_tb)` — `logging.exception()` or `traceback.format_exception()` |
| APP-03 | Packages exclude non-runtime files: .md, .planning/, tests/, .xlsx, .dmc from installed bundle | PyInstaller Analysis `excludes_datas` or post-build COLLECT filter; rsync --exclude patterns in install.sh |
</phase_requirements>

## Summary

Phase 28 adds logging infrastructure using Python stdlib only — no new runtime dependencies. The central task is wiring a `setup_logging()` function in main.py's pre-Kivy block that creates a `logs/` subdirectory under `_get_data_dir()`, attaches a `RotatingFileHandler` and a `StreamHandler`, then patches `sys.excepthook` to write tracebacks before crash. All 142 `print()` calls across 10 source files are then migrated to module-level `logging.getLogger(__name__)` calls.

The artifact exclusion work (APP-03) has two halves. The Windows half extends the existing `BinhAnHMI.spec` COLLECT step to exclude non-runtime files from `datas=` — the existing spec already excludes diagnostics and has a clean `_app_excludes` pattern. The Pi half updates `install.sh`'s existing rsync call to add `--exclude` patterns for .md, .xlsx, .dmc, and .claude/ directories. Both halves already have partial exclusions in place; this phase completes them.

The rsync in `install.sh` already excludes `.planning/`, `tests/`, `.git`, `deploy/`, and `dist/`. The PyInstaller spec is onedir-only and bundles only what is explicitly listed in `datas=`. Since `.md`, `.xlsx`, and `.dmc` files are never added to `datas=` in the spec, they are naturally absent from the Windows bundle. The real verification gap is a test that confirms absence, not new exclusion logic.

**Primary recommendation:** Implement `setup_logging()` as a manual handler setup (not `logging.basicConfig`) placed in the pre-Kivy block of `main.py`, after `_get_data_dir()` but before the `Config.set` calls. Migrate prints file-by-file using `logger = logging.getLogger(__name__)` at module level. For APP-03, extend install.sh rsync and write content-inspection tests that scan the spec's `datas=` list and install.sh's exclude list — do NOT try to actually build and scan `dist/` in tests (that requires PyInstaller to run).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `logging` | stdlib | Structured log records to file+console | No dep, battle-tested, hierarchical |
| `logging.handlers.RotatingFileHandler` | stdlib | Rotate at 5 MB, keep 3 backups | Exact match for APP-01 requirement |
| `traceback` | stdlib | Format exception tracebacks in excepthook | Used inside the excepthook to get full tb string |
| `sys` | stdlib | `sys.excepthook` patching | Only way to intercept truly uncaught exceptions |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pathlib.Path` | stdlib | Build log dir path from `_get_data_dir()` | Already used in tests; cleaner than os.path.join |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Manual handler setup | `logging.basicConfig` | basicConfig is a one-shot call; fails silently if any handler is already attached (Kivy attaches its own). Manual setup is explicit and reliable. |
| `sys.excepthook` | `faulthandler` | faulthandler catches C-level segfaults, not Python exceptions; not a replacement |
| rsync --exclude | cp + find -prune | rsync is already used in install.sh; extending its --exclude list is simpler than replacing it |

**Installation:**
```bash
# No new runtime packages required — all stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
src/dmccodegui/
├── main.py              # setup_logging() added in pre-Kivy block
│                        # sys.excepthook patch added in pre-Kivy block
│                        # All print() calls → logger.info/debug/warning/error
├── controller.py        # Module-level logger = logging.getLogger(__name__)
├── hmi/mg_reader.py     # Module-level logger
├── screens/             # Each screen module gets module-level logger
│   ├── convex/
│   ├── flat_grind/
│   └── serration/
└── utils/transport.py   # Module-level logger
```

### Pattern 1: Centralized Logging Setup in Pre-Kivy Block

**What:** A single `setup_logging()` function called once in main.py before any Kivy import. Creates the logs directory, attaches RotatingFileHandler and StreamHandler to the root logger.

**When to use:** Exactly once at startup, in the pre-import block where GCLIB_ROOT, KIVY_DPI_AWARE, and excepthook are already configured.

**Example:**
```python
# Source: Python docs — logging.handlers.RotatingFileHandler
import logging
import logging.handlers
import os

def setup_logging() -> None:
    """Configure root logger with rotating file + console output.

    Must be called before any Kivy import.
    Log directory is logs/ under _get_data_dir().
    """
    log_dir = os.path.join(_get_data_dir(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'app.log')

    fmt = logging.Formatter(
        '%(asctime)s %(levelname)s [%(module)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,   # 5 MB
        backupCount=3,
        encoding='utf-8',
    )
    file_handler.setFormatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
```

### Pattern 2: sys.excepthook Patch

**What:** Replace `sys.excepthook` before the first Kivy import so that ALL uncaught Python exceptions — including those raised inside Kivy event handlers — are written to app.log before the process exits.

**When to use:** Placed immediately after `setup_logging()` call in the pre-Kivy block.

**Example:**
```python
# Source: Python docs — sys.excepthook
import sys
import logging
import traceback

def _excepthook(exc_type, exc_value, exc_tb):
    """Log uncaught exceptions then call the original excepthook (crash normally)."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Let Ctrl-C exit silently — don't log as error
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.getLogger(__name__).critical('Uncaught exception:\n%s', msg)

sys.excepthook = _excepthook
```

**Critical note:** `KeyboardInterrupt` must be allowed through silently so Ctrl-C on the console doesn't produce an ugly ERROR log entry.

### Pattern 3: Module-Level Logger (Per-File Migration)

**What:** Each source file that had `print()` calls gets a module-level logger. Module name comes from `__name__` — in a package this is `dmccodegui.controller`, `dmccodegui.screens.flat_grind.axes_setup`, etc.

**When to use:** Top of every .py file being migrated, below the imports.

**Example:**
```python
import logging
logger = logging.getLogger(__name__)

# Previously: print(f"[CTRL] Sending command: {command}")
logger.debug("Sending command: %s", command)

# Previously: print(f"[CTRL] Command failed: {command} -> {e}")
logger.error("Command failed: %s -> %s", command, e)

# Previously: print("[CTRL] Waiting for controller ready...")
logger.info("Waiting for controller ready...")
```

**Level assignment heuristic:**
- `logger.debug` — Verbose trace: individual command sends, response parsing, array element reads
- `logger.info` — State transitions, startup events, connection success, screen loads
- `logger.warning` — Recoverable issues: fallback triggered, parse failure, retry
- `logger.error` — Operation failures that don't crash: command failed, KV load failed

### Pattern 4: PyInstaller Spec — Confirming File Exclusion

**What:** The PyInstaller `Analysis` object bundles only what is explicitly listed in `datas=`. Files NOT in `datas=` and NOT in `binaries=` are not included. The existing spec already enumerates every data file it needs. Non-runtime files (.md, .xlsx, .dmc, .planning/) are simply not listed and are therefore absent from the bundle.

**Verification approach:** A content-inspection test scans the spec file's `datas=` block and asserts that none of the forbidden patterns appear. It also verifies the `_app_excludes` list. This avoids requiring a real PyInstaller build in CI.

**Example test:**
```python
# tests/test_bundle_exclusions.py
import pathlib
import re

SPEC_PATH = pathlib.Path(__file__).resolve().parent.parent / 'deploy' / 'windows' / 'BinhAnHMI.spec'

def test_spec_does_not_include_md_files():
    text = SPEC_PATH.read_text(encoding='utf-8')
    # No *.md in datas
    assert '.md' not in text or 'exclude' in text.lower()
    # More specifically: check that README.md is not in a datas tuple
    assert re.search(r'\(.*README\.md.*\)', text) is None

def test_spec_does_not_include_xlsx():
    text = SPEC_PATH.read_text(encoding='utf-8')
    assert '.xlsx' not in text
```

### Pattern 5: install.sh rsync — Adding Exclusions

**What:** The existing rsync call already excludes `.planning/`, `tests/`, `.git`, `deploy/`, `dist/`. Add `--exclude` flags for `.md`, `.xlsx`, `.dmc`, `.claude/`, and `pyproject.toml`.

**Current install.sh (line 136-144):**
```bash
rsync -a --delete "$SCRIPT_DIR/../../" "$INSTALL_DIR/" \
    --exclude='.git' \
    --exclude='deploy/' \
    --exclude='dist/' \
    --exclude='build/' \
    --exclude='.planning/' \
    --exclude='tests/' \
    --exclude='__pycache__' \
    2>&1 | tee -a "$LOG_FILE"
```

**Extended exclusions to add:**
```bash
rsync -a --delete "$SCRIPT_DIR/../../" "$INSTALL_DIR/" \
    --exclude='.git' \
    --exclude='deploy/' \
    --exclude='dist/' \
    --exclude='build/' \
    --exclude='.planning/' \
    --exclude='tests/' \
    --exclude='__pycache__' \
    --exclude='.claude/' \
    --exclude='*.md' \
    --exclude='*.xlsx' \
    --exclude='*.dmc' \
    --exclude='pyproject.toml' \
    2>&1 | tee -a "$LOG_FILE"
```

**rsync --exclude behavior:**
- `--exclude='*.md'` — wildcard, matches any .md file at any depth when combined with -a (recursive)
- `--exclude='.claude/'` — trailing slash matches directory only (not a file named `.claude`)
- `--exclude='*.dmc'` — catches all DMC program files
- Order does not matter for these non-overlapping patterns
- `--delete` removes previously synced files that now match exclusions on re-run

### Anti-Patterns to Avoid
- **logging.basicConfig in main.py:** Kivy calls `logging.basicConfig()` internally. If basicConfig has already been called (even with no handlers), subsequent calls are no-ops. The manual handler setup in `setup_logging()` bypasses this problem.
- **getLogger(__name__) inside functions (old pattern in main.py):** The 3 existing `import logging; logging.getLogger(__name__)` calls at lines 326, 695, 1194 create a new logger on every call. Consolidated into module-level `_log = logging.getLogger(__name__)` after the Kivy imports block.
- **print() in pre-Kivy block before setup_logging():** The 4 print calls in `_detect_preset()` (lines 152, 156, 169, 172) happen BEFORE `setup_logging()` is called (which happens after `_detect_preset()`). These must stay as print() or the logging setup must be moved earlier. Resolution: move `setup_logging()` call to before `_detect_preset()` call, or accept that display detection prints to console only and replace them with logger calls anyway — since the logger will be configured by the time any log file reader looks at the output, this is fine.
- **Logging in PyInstaller frozen apps with console=False:** The Windows spec sets `console=False`. This means `StreamHandler` will still work (Python's sys.stderr is redirected internally), but there is no visible console for operators. The StreamHandler target is only useful in dev mode — which is correct behavior. No change needed.
- **Trying to build dist/ in tests for APP-03:** Building PyInstaller output takes minutes and requires all Windows deps. Content-inspection tests should scan source files (spec, install.sh) not build outputs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Log file rotation | Custom rotation logic | `logging.handlers.RotatingFileHandler` | Handles concurrent write, OS-level rename, cross-platform — edge cases are tricky |
| Traceback formatting | `str(exc)` | `traceback.format_exception(exc_type, exc_value, exc_tb)` | Captures full chain including chained exceptions and context |
| Log directory creation | Check-then-create | `os.makedirs(log_dir, exist_ok=True)` | Atomic, no race condition |

**Key insight:** Everything needed for this phase is in the Python stdlib. The complexity is organizational (where to call setup, how to handle pre-Kivy prints) not technical.

## Common Pitfalls

### Pitfall 1: setup_logging() Called After Kivy Imports
**What goes wrong:** Kivy imports trigger `logging.basicConfig()` with its own handlers. When `setup_logging()` then adds RotatingFileHandler to the root logger, Kivy's handler is already there, causing duplicate log lines and possible log-to-wrong-file behavior.
**Why it happens:** Kivy configures Python logging as a side effect of `from kivy.app import App`.
**How to avoid:** Call `setup_logging()` in the pre-Kivy block, after `_get_data_dir()` is defined and before `os.environ["KIVY_DPI_AWARE"] = "1"`. The call sequence in main.py should be: `_get_data_dir()` definition → `_detect_preset()` definition → `setup_logging()` call → excepthook patch → `os.environ` settings → `from kivy.config import Config`.
**Warning signs:** Log file gets created but has no entries from controller.py or screen modules; only Kivy internal messages appear.

### Pitfall 2: print() Calls in Pre-Kivy Block Before Logger Exists
**What goes wrong:** `_detect_preset()` calls print() at lines 152, 156, 169, 172. These run at module load time before `setup_logging()` is called. Migrating them to `logger.info()` where `logger = logging.getLogger(__name__)` at module level means those calls land before any handler is attached — they are silently discarded or go to a NullHandler.
**Why it happens:** The pre-Kivy block executes sequentially; logging is not configured until `setup_logging()` runs.
**How to avoid:** Call `setup_logging()` before `_detect_preset()` runs. Since `_detect_preset()` depends on `_get_data_dir()` (called inside it), and `setup_logging()` also depends on `_get_data_dir()`, the safe order is:
  1. Define `_get_data_dir()`
  2. Call `setup_logging()` (creates log dir, attaches handlers)
  3. Define/call `_detect_preset()` — now logging is live
**Warning signs:** Display preset detection messages never appear in app.log.

### Pitfall 3: RotatingFileHandler on Windows with Frozen App (console=False)
**What goes wrong:** In a PyInstaller frozen onedir bundle with `console=False`, sys.stdout and sys.stderr are `None`. A bare `StreamHandler()` without a stream argument defaults to `sys.stderr`. If stderr is None (frozen + no console), writing to the StreamHandler raises `AttributeError: 'NoneType' object has no attribute 'write'`.
**Why it happens:** PyInstaller sets stderr/stdout to None when console=False.
**How to avoid:** Guard the StreamHandler:
```python
import sys
if sys.stderr is not None:
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)
```
Or use `sys.stderr or open(os.devnull, 'w')` as the stream. The file handler always works.
**Warning signs:** App crashes immediately on Windows bundle launch with `AttributeError` from logging internals.

### Pitfall 4: Kivy Swallowing Exceptions in Event Callbacks
**What goes wrong:** Kivy wraps many event callbacks in try/except and logs them through its own logger rather than re-raising. `sys.excepthook` does NOT fire for exceptions caught by Kivy internals.
**Why it happens:** Kivy's clock dispatch loop catches exceptions to keep the event loop running.
**How to avoid:** This is expected behavior — Kivy exceptions inside callbacks appear in the log via Kivy's own logger (which goes through the root logger). For app-level crashes (startup, import-time exceptions), `sys.excepthook` is sufficient. The phase decision explicitly states "log full traceback, then let app crash normally" — this is correct for true uncaught exceptions.
**Warning signs:** An exception in a button callback doesn't crash the app — that's correct Kivy behavior, not a bug.

### Pitfall 5: rsync --exclude='*.md' Fails to Exclude Nested .md Files
**What goes wrong:** `--exclude='*.md'` matches files named `*.md` in the source root but not in subdirectories when using rsync path anchoring.
**Why it happens:** rsync's `--exclude` patterns without a leading `/` match at any level in the tree when using `-a` (recursive). With a leading `/` they are anchored to root. The `*.md` pattern (no leading `/`) correctly matches at all depths.
**How to avoid:** Use `--exclude='*.md'` (no leading slash) to match at any depth. This is the standard rsync pattern and works correctly with `-a`.
**Warning signs:** After rsync, `find $INSTALL_DIR -name '*.md'` still returns files in subdirectories.

## Code Examples

Verified patterns from official sources:

### Full setup_logging() Implementation
```python
# Source: Python 3.x docs — logging.handlers.RotatingFileHandler, logging.Formatter
import logging
import logging.handlers
import os
import sys

def setup_logging() -> None:
    """Configure root logger: RotatingFileHandler + StreamHandler (dev only).

    Call BEFORE any Kivy import and BEFORE _detect_preset().
    Log directory: _get_data_dir()/logs/
    """
    log_dir = os.path.join(_get_data_dir(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, 'app.log')

    fmt = logging.Formatter(
        '%(asctime)s %(levelname)s [%(module)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8',
    )
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    # Only add console output in non-frozen mode (frozen+no-console has stderr=None)
    if sys.stderr is not None:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(fmt)
        console_handler.setLevel(logging.DEBUG)
        root.addHandler(console_handler)
```

### excepthook Patch
```python
# Source: Python docs — sys.excepthook
import sys
import logging
import traceback

def _setup_excepthook() -> None:
    """Patch sys.excepthook to log uncaught exceptions before crash."""
    _orig = sys.excepthook

    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            _orig(exc_type, exc_value, exc_tb)
            return
        msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logging.getLogger('dmccodegui').critical('Uncaught exception:\n%s', msg)

    sys.excepthook = _excepthook
```

### Call Order in Pre-Kivy Block
```python
# ---- pre-Kivy block (before any 'from kivy...' line) ----

# 1. PyInstaller GCLIB_ROOT patch (already exists)
if getattr(sys, 'frozen', False): ...

# 2. Setup logging (new — must be before _detect_preset call)
setup_logging()
_setup_excepthook()

# 3. Display preset detection (uses logger now instead of print)
_ACTIVE_PRESET_NAME: str = _detect_preset(_early_settings_path())
_PRESET = _DISPLAY_PRESETS[_ACTIVE_PRESET_NAME]

# 4. Kivy environment variables (already exist)
os.environ["KIVY_DPI_AWARE"] = "1"
...

# 5. Kivy imports (already exist)
from kivy.config import Config
...
```

### Print Level Assignment Examples for This Codebase
```python
# controller.py — verbose protocol trace → DEBUG
logger.debug("Sending command: %s", command)
logger.debug("Response: %s", resp.strip())
logger.debug("Reading slice %s[%d:%d]", var_name, start, start + count)
logger.warning("Command failed: %s -> %s", command, e)
logger.warning("TC1 error code: %s", tc1)

# screens/*/axes_setup.py — operational state → INFO/WARNING
logger.info("CPM values from controller: %s", cpm_updates)
logger.warning("teach_rest_point: empty axis_list, aborting")
logger.warning("Read failed: %s -> %s", command, e)

# screens/*/run.py — operational events → INFO
logger.info("BV done — all variables saved")
logger.info("hmiSetp fired — entering setup")

# hmi/mg_reader.py → INFO/WARNING
logger.info("connected: %s", connection_string)
logger.warning("GOpen failed: %s", exc)
logger.info("handle closed")

# main.py display detection → INFO
logger.info("Preset override from settings: %s", override)
logger.warning("Invalid display_size '%s' in settings.json — using 15inch default", override)
logger.info("Auto-detected preset '%s' from %dx%d", preset, mon.width, mon.height)
logger.warning("screeninfo unavailable (%s) — using 15inch default", exc)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `print()` everywhere | `logging.getLogger(__name__)` | Best practice since Python 3.2 | File output, levels, configurable |
| `logging.basicConfig` | Manual handler setup | Always needed when mixing with frameworks | Prevents Kivy handler collision |
| No excepthook | `sys.excepthook` patch | Introduced for crash capture | Full tracebacks in log before exit |

**Deprecated/outdated:**
- `import logging; logging.getLogger(__name__)` inside functions (current main.py pattern at lines 326, 695, 1194): replaced with module-level `_log = logging.getLogger(__name__)` after Kivy imports.

## Open Questions

1. **Kivy's own logging output — level and noise**
   - What we know: Kivy attaches its own handler to the root logger at DEBUG level by default, generating verbose internal messages.
   - What's unclear: Whether Kivy's default log level should be raised to WARNING in the log file to reduce noise.
   - Recommendation: In `setup_logging()`, after Kivy imports are done (or via a deferred call), set `logging.getLogger('kivy').setLevel(logging.WARNING)` to suppress Kivy internal DEBUG spam. This is a Claude's Discretion item — planner should include this as part of the setup function.

2. **print() in controller.py diagnostic block (lines 674-685)**
   - What we know: Lines 674-685 are inside a `if __name__ == '__main__':` block at the bottom of controller.py — a dev-only script entry point.
   - What's unclear: Whether to migrate these or leave them as print() since they're in a `__main__` block.
   - Recommendation: Leave the `if __name__ == '__main__':` block prints unchanged — they're dev tooling, not app runtime code. Migrate all other print() calls.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (from pyproject.toml `[tool.pytest.ini_options] testpaths = ["tests"]`) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_logging.py tests/test_bundle_exclusions.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| APP-01 | `setup_logging()` creates logs/app.log with RotatingFileHandler at correct path | unit | `pytest tests/test_logging.py::test_log_file_created -x` | ❌ Wave 0 |
| APP-01 | RotatingFileHandler has maxBytes=5MB, backupCount=3 | unit | `pytest tests/test_logging.py::test_rotating_handler_config -x` | ❌ Wave 0 |
| APP-01 | Log format matches `timestamp level [module] message` | unit | `pytest tests/test_logging.py::test_log_format -x` | ❌ Wave 0 |
| APP-01 | On Linux platform, log goes to `~/.binh-an-hmi/logs/app.log` | unit | `pytest tests/test_logging.py::test_linux_log_path -x` | ❌ Wave 0 |
| APP-02 | `sys.excepthook` is replaced by `_setup_excepthook()` call | unit | `pytest tests/test_logging.py::test_excepthook_patched -x` | ❌ Wave 0 |
| APP-02 | Uncaught exception writes full traceback to log before crash | unit | `pytest tests/test_logging.py::test_excepthook_logs_traceback -x` | ❌ Wave 0 |
| APP-02 | KeyboardInterrupt is NOT logged as error (passes through) | unit | `pytest tests/test_logging.py::test_excepthook_keyboard_interrupt -x` | ❌ Wave 0 |
| APP-03 | spec datas= list contains no .md, .xlsx, .dmc entries | content-inspection | `pytest tests/test_bundle_exclusions.py::test_spec_no_md_files -x` | ❌ Wave 0 |
| APP-03 | spec datas= list contains no .planning/ entries | content-inspection | `pytest tests/test_bundle_exclusions.py::test_spec_no_planning_dir -x` | ❌ Wave 0 |
| APP-03 | install.sh rsync excludes *.md, *.xlsx, *.dmc, .claude/ | content-inspection | `pytest tests/test_bundle_exclusions.py::test_install_sh_excludes_noncritical -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_logging.py tests/test_bundle_exclusions.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_logging.py` — covers APP-01 and APP-02 (7 tests)
- [ ] `tests/test_bundle_exclusions.py` — covers APP-03 (3 tests)

*(No framework or fixture gaps — pytest + existing conftest.py are sufficient)*

## Sources

### Primary (HIGH confidence)
- Python 3.x stdlib docs — `logging`, `logging.handlers.RotatingFileHandler`, `sys.excepthook`, `traceback.format_exception`
- Source code inspection: `src/dmccodegui/main.py` lines 1-250 (pre-Kivy block structure), lines 326, 695, 1194 (existing ad-hoc loggers)
- Source code inspection: `deploy/windows/BinhAnHMI.spec` (existing datas= list, _app_excludes pattern)
- Source code inspection: `deploy/pi/install.sh` lines 134-144 (existing rsync --exclude patterns)
- Grep audit: 142 print() calls across 10 files confirmed

### Secondary (MEDIUM confidence)
- PyInstaller docs (6.x) — Analysis datas= only bundles explicitly listed files; files absent from datas= are not included
- rsync man page — `--exclude` without leading `/` matches at all directory depths with `-r`/`-a`

### Tertiary (LOW confidence)
- Kivy source behavior re: logging.basicConfig — inferred from known framework pattern of calling basicConfig at import time; validate by running `python -c "from kivy.app import App; import logging; print(logging.root.handlers)"` in dev env

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, well-documented, no external dependencies
- Architecture: HIGH — pre-Kivy block pattern already established in codebase; follows exact same pattern as GCLIB_ROOT and screeninfo setup
- Pitfalls: HIGH (stdlib/PyInstaller) / MEDIUM (Kivy logging interaction) — Kivy behavior inferred from pattern analysis, not live tested

**Research date:** 2026-04-22
**Valid until:** 2026-10-22 (stdlib — stable indefinitely; PyInstaller spec format — stable for 6.x)
