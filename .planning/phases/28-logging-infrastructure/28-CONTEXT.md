# Phase 28: Logging Infrastructure - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up rotating log files in the platform-correct location, capture all uncaught exceptions with full traceback before the app exits, migrate all 142 print() calls to structured logging, and exclude non-runtime files from both Windows PyInstaller bundles and Pi deployment. No in-app log viewer (deferred to FUTURE-01).

</domain>

<decisions>
## Implementation Decisions

### Log file location and rotation
- Windows: `%APPDATA%/BinhAnHMI/logs/app.log` (consistent with Phase 24 APPDATA path, NOT DMCGrindingGUI as SC-1 says — Phase 24 decision takes precedence)
- Pi/Linux: `~/.binh-an-hmi/logs/app.log` (consistent with Phase 26 data dir)
- Rotation: 5 MB limit, 3 backup files (per APP-01)
- Python `logging.handlers.RotatingFileHandler`

### Log format and output
- Format: `timestamp + level + module + message` (e.g., `2026-04-22 14:30:05 INFO [main] Starting app v4.0.0`)
- Dual output: logs go to BOTH file (RotatingFileHandler) AND console (StreamHandler)
- All 142 print() calls across 10 source files migrated to proper logger calls (logger.info, logger.debug, logger.warning, logger.error as appropriate)
- Ad-hoc `logging.getLogger(__name__)` calls in main.py (3 spots) consolidated into the new logging setup

### Exception handling
- `sys.excepthook` patched BEFORE Kivy import to capture ALL uncaught exceptions including Kivy internal errors
- On uncaught exception: log full traceback to app.log, then let the app crash normally (no graceful shutdown attempt)
- No gclib connection cleanup in excepthook — OS handles it. Simplest, most reliable approach.

### Artifact exclusion — Windows (.spec)
- Exclude from PyInstaller bundle: .md files, .planning/, tests/, .xlsx, .dmc, .git/, .claude/, deploy/, pyproject.toml, dotfiles
- Build on existing BinhAnHMI.spec exclude patterns (diagnostics already excluded)
- Add a test that scans the built output directory and fails if excluded file types are found — catches regressions

### Artifact exclusion — Pi (install.sh)
- Use rsync --exclude patterns in install.sh for: .md, .planning/, tests/, .xlsx, .dmc, .git/, .claude/, deploy/
- Exclude entire deploy/ directory from Pi deployment at /opt/binh-an-hmi/ (not needed at runtime)
- Add a similar exclusion verification test for Pi deployment directory

### DMC/Excel files
- .dmc and .xlsx files excluded from both packages (not bundled)
- No separate optional bundle created in this phase — technicians grab from repo if needed

### Claude's Discretion
- Exact logging configuration setup code structure
- Logger naming convention (module-level `__name__` loggers vs centralized)
- Which print() calls become info vs debug vs warning
- Exact rsync --exclude flag syntax in install.sh
- Test implementation for bundle content verification
- Whether to use logging.basicConfig or manual handler setup

</decisions>

<specifics>
## Specific Ideas

- The 3 existing ad-hoc `logging.getLogger(__name__)` calls in main.py (lines 326-327, 695-696, 1194-1195) should be consolidated into the new centralized logging setup
- print() calls in display preset detection (main.py:152-172) should become logger.info calls
- The excepthook patch must happen in the pre-import block alongside KIVY_DPI_AWARE and GCLIB_ROOT — before any Kivy import

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main.py:15-32` (`_get_data_dir()`): Platform-aware path logic — logs/ subdirectory follows same pattern
- `main.py:35-54`: Pre-import block — excepthook patch goes here
- `deploy/windows/BinhAnHMI.spec:42-47`: Existing exclude patterns — extend for full artifact exclusion
- `deploy/pi/install.sh`: File copy logic — add rsync --exclude patterns

### Established Patterns
- Pre-import configuration: Config.set, env vars, GCLIB_ROOT all set before Kivy imports — excepthook and logging setup follow same pattern
- Platform detection: `getattr(sys, 'frozen', False)`, `sys.platform == 'linux'` — log path detection reuses this
- `_get_data_dir()` returns base data dir — `os.path.join(_get_data_dir(), 'logs')` gives log directory

### Integration Points
- `main.py` pre-import block: excepthook + logging setup
- Every .py file with print() calls: migration to logger
- `BinhAnHMI.spec`: extended exclude list
- `deploy/pi/install.sh`: rsync --exclude patterns
- `tests/`: new test for bundle content verification

</code_context>

<deferred>
## Deferred Ideas

- **In-app log viewer** — Admin modal showing last 200 lines of app.log (FUTURE-01 in REQUIREMENTS.md)
- **Separate DMC/Excel bundle** — zip of .dmc and .xlsx files delivered alongside installer

</deferred>

---

*Phase: 28-logging-infrastructure*
*Context gathered: 2026-04-22*
