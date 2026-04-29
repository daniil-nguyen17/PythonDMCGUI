# Architecture Patterns: v4.1 Security, Licensing & Code Protection

**Domain:** Python/Kivy industrial HMI — licensing, code protection, and per-machine parameter expansion
**Researched:** 2026-04-28
**Confidence:** HIGH for integration points (derived from reading actual codebase). MEDIUM for PyArmor/Cython pipeline (WebSearch + official docs, not yet validated against this specific project). HIGH for param_defs expansion (derived directly from machine_config.py structure).

---

## Scope

This document covers three new concerns in v4.1 and how they integrate with the existing architecture:

1. **Per-machine hardware-bound licensing** — Ed25519 signed license files, keygen CLI, startup validation
2. **Code protection** — Cython `.so` compilation for Pi, PyArmor bytecode encryption for Windows
3. **Per-machine parameter pages** — expanding `_CONVEX_PARAM_DEFS` and auditing the others

---

## Recommended Architecture

### New Module: `src/dmccodegui/licensing/`

A new sub-package, isolated from all controller and UI code. It has no Kivy dependency and no gclib dependency. It reads one file and returns a verdict.

```
src/dmccodegui/
  licensing/
    __init__.py          # exports: validate_license(), LicenseError
    validator.py         # Ed25519 verify + hardware fingerprint check
    fingerprint.py       # platform-specific hardware ID extraction
    keygen.py            # CLI tool: generate + sign license files (dev machine only)
```

**Public interface consumed by main.py:**

```python
from dmccodegui.licensing import validate_license, LicenseError

# Called once at startup, before DMCApp.build()
try:
    validate_license(license_path, public_key_bytes)
except LicenseError as e:
    # Show blocking error modal, then sys.exit(1)
```

`validator.py` uses `cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey.verify()`. The public key is embedded as a literal bytes constant in `validator.py` — not loaded from disk. The private key never ships with the app.

`fingerprint.py` extracts the hardware ID:
- **Pi (Linux):** Read `/proc/cpuinfo` lines starting with `Serial`, fall back to `uuid.getnode()` (MAC-based) if absent. Return a SHA-256 digest of the combined values.
- **Windows (frozen):** Use `uuid.getnode()` (MAC address of primary adapter) plus `platform.node()`. Return SHA-256 digest.

The license file format is a JSON file containing:
```json
{
  "machine_id": "<sha256 hex of fingerprint>",
  "machine_type": "4-Axes Flat Grind",
  "issued": "2026-04-28",
  "expires": null,
  "signature": "<base64 Ed25519 signature over canonical JSON without this key>"
}
```

`keygen.py` is a standalone CLI script (not imported by the app). It lives in the `licensing/` sub-package but is only run by the developer/manufacturer to produce license files for delivery.

### Integration Point in `main.py`

License validation happens after `setup_logging()` and `_setup_excepthook()` but before any Kivy imports or the `Config.set` block. This is the only pre-Kivy code location where a blocking failure is safe.

**Exact insertion point in `main.py`:**

```
setup_logging()          ← existing line ~250
_setup_excepthook()      ← existing line ~251
_log = ...               ← existing line ~255

# --- NEW: license check (before Kivy) ---
_license_path = _resolve_license_path()   # new helper
_check_license(_license_path)             # new helper; calls sys.exit(1) on failure

_ACTIVE_PRESET_NAME = _detect_preset(...)  ← existing
```

`_resolve_license_path()` follows the same platform logic as `_get_data_dir()`:
- **Frozen Windows:** `%APPDATA%\BinhAnHMI\license.json`
- **Pi (Linux):** `~/.binh-an-hmi/license.json`
- **Dev (non-frozen Windows):** `src/dmccodegui/auth/license.json` (dev bypass — see below)

`_check_license()` calls `validate_license()`. On `LicenseError`, it calls `sys.exit(1)` — there is intentionally no Kivy popup at this point because Kivy has not been imported. The error is logged to `app.log` via the already-configured file handler.

**Dev bypass:** In dev mode (`not getattr(sys, 'frozen', False)` and not Linux), if the license file does not exist, skip validation entirely. This keeps the dev loop intact and avoids distributing private keys.

### License File Delivery

| Platform | License file destination | How it gets there |
|----------|--------------------------|-------------------|
| Pi | `~/.binh-an-hmi/license.json` | Copied by `install.sh` from `deploy/pi/license.json` (keyed per machine) |
| Windows frozen | `%APPDATA%\BinhAnHMI\license.json` | Copied by Inno Setup from installer payload; or manual SCP/USB delivery |

The license file is machine-specific. The `deploy/pi/license.json` placed in the repo for Pi install is generated per-machine by the `keygen.py` CLI before each deployment.

---

## Code Protection Architecture

### Pi: Cython `.so` Compilation

**What gets compiled:** The business-logic modules that are worth protecting. UI-only files (`.kv`) and thin screen wrappers are lower value. The high-value targets are:

| Module | Why compile |
|--------|-------------|
| `machine_config.py` | Contains all param_defs, axis configs, registry |
| `controller.py` | Controller command logic, PRIMARY_FLAGS |
| `hmi/dmc_vars.py` | DMC variable name mapping |
| `hmi/data_record.py` | Data record parsing |
| `licensing/validator.py` | License validation logic |
| `auth/auth_manager.py` | PIN validation |

**What does NOT get compiled:** `main.py` (PyInstaller/Kivy entry point structure is fragile to Cython), `screens/**` (UI glue, lower value), `utils/jobs.py` (thread pool — safe to leave as `.py`).

**Build artifact:** `machine_config.cpython-311-aarch64-linux-gnu.so` alongside the original `.py`. Python's import machinery prefers `.so` over `.py` when both exist in the same directory, so no import changes are needed.

**New file: `deploy/pi/compile_cython.sh`**

```bash
#!/usr/bin/env bash
# Run inside the Pi venv (or with the venv's python) after install.sh completes.
# Compiles selected modules to .so files in-place.
set -euo pipefail
INSTALL_DIR="/opt/binh-an-hmi"
VENV_PYTHON="$INSTALL_DIR/venv/bin/python3"
SRC="$INSTALL_DIR/src"

cd "$SRC"
"$VENV_PYTHON" -m pip install cython --quiet

# Generate a temporary setup_cython.py and build in-place
"$VENV_PYTHON" - <<'PYEOF'
from setuptools import setup
from Cython.Build import cythonize
import sys

targets = [
    "dmccodegui/machine_config.py",
    "dmccodegui/controller.py",
    "dmccodegui/hmi/dmc_vars.py",
    "dmccodegui/hmi/data_record.py",
    "dmccodegui/licensing/validator.py",
    "dmccodegui/auth/auth_manager.py",
]
setup(ext_modules=cythonize(targets, compiler_directives={"language_level": "3"}))
PYEOF

"$VENV_PYTHON" setup_cython_tmp.py build_ext --inplace
rm -f setup_cython_tmp.py
echo "Cython compilation complete"
```

**Integration with `install.sh`:** Add a call to `compile_cython.sh` at the end of Step 9 (after pip install), as Step 9b. It is non-fatal: wrap in `if ... || log "Cython compile failed — running as .py"` so the installer does not abort if the build toolchain is missing.

**Cython constraint:** `build-essential` and `python3-dev` are already installed by Step 4 of `install.sh`. Cython is pip-installed into the venv (not system-wide), so it does not interfere with the system Python.

### Windows: PyArmor Bytecode Obfuscation

**Workflow:** PyArmor 9.x is the current stable release. The recommended production integration with an existing PyInstaller `.spec` is:

```
Step 1: pyarmor gen -r --output dist/obfuscated src/dmccodegui/
Step 2: python -m PyInstaller deploy/windows/BinhAnHMI.spec --clean --noconfirm
        (spec points to dist/obfuscated/ as the source tree instead of src/)
Step 3: ISCC.exe deploy/windows/BinhAnHMI.iss
```

PyArmor writes obfuscated `.py` files (and a small `pyarmor_runtime` package) into `dist/obfuscated/`. The PyInstaller spec is modified to use that directory instead of `src/` as the analysis root. This approach avoids `pyarmor pack --spec` (which has version-compatibility issues with PyInstaller 6+).

**Modified `.spec` change:**

```python
# Before:
SRC = REPO_ROOT / 'src'

# After:
import os as _os
_obfuscated = REPO_ROOT / 'dist' / 'obfuscated'
SRC = _obfuscated if _obfuscated.exists() else REPO_ROOT / 'src'
```

This makes the spec work in both dev (non-obfuscated) and production (obfuscated) modes, controlled by whether `dist/obfuscated/` exists.

**`build_windows.bat` changes:**

```bat
REM Step 1: Obfuscate (requires pyarmor license; skip if not installed)
where pyarmor >nul 2>&1
if not errorlevel 1 (
    echo Obfuscating with PyArmor...
    pyarmor gen -r --output dist\obfuscated src\dmccodegui
) else (
    echo WARNING: pyarmor not found -- building without obfuscation
    if exist dist\obfuscated rmdir /s /q dist\obfuscated
)

REM Step 2: PyInstaller (existing)
python -m PyInstaller deploy\windows\BinhAnHMI.spec --clean --noconfirm

REM Step 3: Inno Setup (existing)
...
```

**PyArmor licensing note:** PyArmor 9.x requires a paid license for production use (the free tier has output restrictions). The pyarmor license file (`pyarmor.rsa`) is stored on the developer machine only — it is not included in the repo or the bundle. MEDIUM confidence on current pricing/tier details; verify at [pyarmor.readthedocs.io](https://pyarmor.readthedocs.io/en/stable/licenses.html) before purchasing.

**What gets obfuscated:** PyArmor with `-r` (recursive) obfuscates the entire `src/dmccodegui/` tree. The `.kv` files, font files, and images are unaffected (PyArmor only processes `.py` files). Assets are still bundled by the spec's `datas=` list unchanged.

---

## Per-Machine Parameter Definitions

### Current State

`machine_config.py` already has the correct structure. The `_REGISTRY` dict maps machine type strings to entries containing `param_defs`. The pattern is already working for Flat Grind and Serration. The gap is `_CONVEX_PARAM_DEFS`, which is currently a copy of `_FLAT_PARAM_DEFS` marked "placeholder."

### Integration Pattern (No Structural Changes Needed)

The parameters screen for each machine type (`screens/convex/parameters.py`) reads param defs exclusively via `mc.get_param_defs()`. No screen-level changes are needed to accommodate new or different params — the registry drives everything.

**To add correct Convex params:**

1. Edit `_CONVEX_PARAM_DEFS` in `machine_config.py` only.
2. Remove vars that don't apply (e.g., if Convex has no D-axis feedrate, remove `fdD`).
3. Add Convex-specific vars (e.g., `convexRad` — radius parameter) with correct groups.
4. Verify the `"axes"` list in `_REGISTRY["4-Axes Convex Grind"]` matches the physical axes.

**No changes** to `screens/convex/parameters.py`, `screens/convex/__init__.py`, `machine_config.py`'s public API, or any screen that reads params.

### Adding the `"readonly"` Field (Already Done in Serration)

The Serration defs already use `"readonly": True` for CPM display fields. The pattern is established. Convex can use the same flag if it needs read-only display rows.

### Param Def Audit Checklist

Each param dict must have: `label`, `var`, `unit`, `group`, `min`, `max`. Optional: `readonly`. The screens will silently render any param that has these keys. Missing keys cause `KeyError` at render time.

---

## Component Boundaries (New vs Modified)

### New Components

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| `licensing/__init__.py` | NEW | `src/dmccodegui/licensing/` | Exports `validate_license`, `LicenseError` |
| `licensing/validator.py` | NEW | `src/dmccodegui/licensing/` | Ed25519 verify, fingerprint comparison |
| `licensing/fingerprint.py` | NEW | `src/dmccodegui/licensing/` | Platform hardware ID extraction |
| `licensing/keygen.py` | NEW | `src/dmccodegui/licensing/` | Dev-only CLI: sign license files |
| `deploy/pi/compile_cython.sh` | NEW | `deploy/pi/` | Cython in-place `.so` compilation |

### Modified Components

| Component | Change | Why |
|-----------|--------|-----|
| `main.py` | Add `_resolve_license_path()` + `_check_license()` in pre-Kivy block | License must be checked before Kivy loads |
| `machine_config.py` | Replace `_CONVEX_PARAM_DEFS` placeholder with real definitions | Correct per-machine params |
| `deploy/windows/build_windows.bat` | Add PyArmor step before PyInstaller | Obfuscation must precede bundling |
| `deploy/windows/BinhAnHMI.spec` | SRC path conditional on `dist/obfuscated/` existence | Spec must point to obfuscated source when present |
| `deploy/pi/install.sh` | Add Step 9b: call `compile_cython.sh` | Cython compile after pip install |
| `pyproject.toml` or `requirements-dev.txt` | Add `cryptography`, `pyarmor` (dev), `cython` (Pi build) | New build-time deps |

### Unchanged Components

`controller.py`, all `screens/**`, `hmi/**`, `auth/auth_manager.py` (structure unchanged, only Cython-compiled), `app_state.py`, `theme_manager.py`, all `.kv` files, `utils/jobs.py`.

---

## Data Flow: Startup with License Check

```
main.py (module level)
  setup_logging()
  _setup_excepthook()
  _log = ...
  _resolve_license_path()     ← new: returns platform-specific path
  _check_license(path)        ← new: calls validate_license()
    licensing/fingerprint.py  ← reads /proc/cpuinfo or uuid.getnode()
    licensing/validator.py    ← Ed25519.verify(signature, payload, public_key)
    if fail: log + sys.exit(1)
  _ACTIVE_PRESET_NAME = _detect_preset(...)
  Config.set(...)
  [Kivy imports]
  DMCApp().run()
    __init__: mc.init(settings_path)
    build(): _add_machine_screens() ← reads mc._REGISTRY[type]["param_defs"]
```

---

## Build Order (Dependencies)

The three v4.1 work streams have different dependencies. This is the correct sequencing:

### Stream A: Licensing (Pi and Windows)

```
A1. Implement licensing/ sub-package
    - fingerprint.py: platform hardware ID
    - validator.py: Ed25519 verify (depends on: cryptography package)
    - keygen.py: sign license files
    Output: working validate_license() in isolation (unit-testable without hardware)
    Gate: pytest tests pass with mocked fingerprint

A2. Add license check to main.py pre-Kivy block
    Depends on: A1
    Output: app exits cleanly on missing/invalid license in frozen mode
    Gate: frozen exe refuses to start with wrong license.json

A3. Generate per-machine license files for all deployed machines
    Depends on: A1 + knowing each machine's hardware fingerprint
    Output: license.json files per machine
    Note: Pi fingerprint requires running on the actual Pi hardware
```

### Stream B: Cython (Pi only)

```
B1. Identify compile targets, write compile_cython.sh
    Depends on: nothing (pure build tooling change)
    Output: script that produces .so files

B2. Integrate into install.sh as Step 9b
    Depends on: B1
    Output: fresh install on Pi produces .so files alongside .py files
    Gate: python -c "import dmccodegui.machine_config" works after compile

B3. Validate .so files load correctly with installed venv Python
    Depends on: B2
    Gate: full app run on Pi with Cython .so files, no ImportError
```

### Stream C: PyArmor (Windows only)

```
C1. Install pyarmor on dev machine, acquire license
    Depends on: nothing
    Note: requires paid license for production use

C2. Test pyarmor gen -r on src/dmccodegui/
    Depends on: C1
    Output: dist/obfuscated/ tree that Python can import
    Gate: python -c "import dmccodegui.main" from dist/obfuscated/ works

C3. Modify BinhAnHMI.spec to use dist/obfuscated/ when present
    Depends on: C2
    Output: spec file that builds correctly from both plain and obfuscated source

C4. Modify build_windows.bat to add PyArmor step
    Depends on: C3
    Output: single build_windows.bat run produces obfuscated installer
    Gate: obfuscated frozen exe runs on clean Windows VM
```

### Stream D: Param Definitions (no dependencies)

```
D1. Replace _CONVEX_PARAM_DEFS placeholder in machine_config.py
    Depends on: customer-provided Convex machine specifications
    Output: correct param defs for Convex machine type
    Gate: ConvexParametersScreen renders all expected params, no KeyError

D2. Audit _FLAT_PARAM_DEFS and _SERRATION_PARAM_DEFS
    Depends on: DMC variable names confirmed against .dmc file
    Output: corrected min/max/unit values where wrong
    Gate: all params read/write correctly on real controller
```

### Cross-Stream Dependencies

- **A must complete before C4 gate**, because the license check in main.py must work inside the obfuscated bundle.
- **B1 must not include `licensing/keygen.py` in Cython targets** — the keygen is a dev tool and should never be on the Pi.
- **D has no dependency on A, B, or C** — it is purely a data edit in `machine_config.py`.

**Recommended execution order given the above:**

```
1. D1 + D2 (quick wins, data-only, unblock testing of param pages)
2. A1      (licensing core, unit-testable)
3. B1 + B2 (Cython script, can run on Pi in parallel with A)
4. A2      (wire license into main.py — needs A1)
5. B3      (validate Pi build — needs B2 and the Pi hardware)
6. A3      (generate license files — needs A1 + Pi hardware for fingerprint)
7. C1 + C2 (PyArmor setup — needs pyarmor license purchased)
8. C3 + C4 (wire PyArmor into spec + bat — needs C2 and A2 working)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Calling validate_license() inside DMCApp.build() or after Kivy import
**What goes wrong:** Kivy has already initialized the window. A sys.exit(1) inside build() leaves a zombie window and may not terminate cleanly on Pi kiosk mode.
**Instead:** License check runs at module level in main.py, before any Kivy import. Failure logs to file handler (already initialized) and calls sys.exit(1). The process terminates before any window is created.

### Anti-Pattern 2: Embedding the private Ed25519 key in the app
**What goes wrong:** Anyone who reverses the app (Cython/PyArmor notwithstanding) can extract the private key and forge license files for any machine.
**Instead:** Only the public key (32 bytes) is embedded in `validator.py` as a literal. The private key exists only in the developer's secure storage (e.g., a password manager, not in the repo).

### Anti-Pattern 3: Including keygen.py in the Cython compile targets or PyInstaller bundle
**What goes wrong:** The keygen tool depends on the private key material at runtime. Shipping it (even obfuscated) increases attack surface.
**Instead:** `keygen.py` is excluded from `compile_cython.sh` targets. The PyInstaller spec's `excludes=` list explicitly excludes `dmccodegui.licensing.keygen`. The private key is referenced only in the developer's local invocation of keygen.py.

### Anti-Pattern 4: Cython-compiling main.py
**What goes wrong:** PyInstaller's entry point mechanism relies on importing `__main__` by name. Cython-compiled `__main__.so` is not discoverable by PyInstaller's bootstrap, and Kivy's pre-import block (Config.set before Window) breaks under Cython annotation if the module-level statements are reordered by Cython's optimizer.
**Instead:** Leave `main.py` and `__main__.py` as plain `.py`. Cython targets are limited to the business-logic modules listed above.

### Anti-Pattern 5: PyArmor `--pack` with the existing BinhAnHMI.spec
**What goes wrong:** `pyarmor gen --pack foo.spec` works only with PyInstaller < 6.0. The current spec uses PyInstaller 6+ features (angle.dep_bins, kivy hooks). Using `--pack` produces a broken bundle.
**Instead:** Use the two-step approach: `pyarmor gen -r` first, then `PyInstaller BinhAnHMI.spec` pointing to the obfuscated output directory. This is the documented approach for PyInstaller 6+ compatibility.

### Anti-Pattern 6: Fingerprinting by hostname or IP address
**What goes wrong:** Pi hostname is often `raspberrypi` (default), and IP changes with DHCP. Neither is unique or stable enough for license binding.
**Instead:** On Pi, use the hardware serial from `/proc/cpuinfo` (unique per SoC, stable across OS reinstalls). Fall back to MAC address via `uuid.getnode()`. Hash both together.

---

## Scalability Considerations

Licensing is per-machine, so scaling means operational process, not code:

| Concern | Approach |
|---------|----------|
| New Pi deployment | Run keygen.py on that Pi's fingerprint, copy license.json into deploy/pi/, run install.sh |
| Pi OS reinstall | Re-run install.sh with the same license.json — fingerprint is hardware-bound, survives OS wipe |
| Windows machine swap | Generate new license.json for new machine's MAC address, deliver via USB |
| License expiry | Set `"expires"` field in license JSON; validator checks date before signature verify |
| Multiple machine types at one customer | License file's `"machine_type"` field is informational (not enforced by default) — can add enforcement later in validator.py |

---

## Sources

- Ed25519 signing in Python cryptography library: [cryptography.io Ed25519](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
- Raspberry Pi hardware serial from /proc/cpuinfo: [RPi Spy serial number](https://www.raspberrypi-spy.co.uk/2012/09/getting-your-raspberry-pi-serial-number-using-python/)
- Cython compilation to .so, setuptools integration: [Cython build docs](https://cython.readthedocs.io/en/latest/src/quickstart/build.html)
- PyArmor 9 obfuscation tutorial: [PyArmor stable docs](https://pyarmor.readthedocs.io/en/stable/tutorial/obfuscation.html)
- PyArmor pack command with existing spec (PyInstaller 6+ approach): [PyArmor pack insight](https://pyarmor.readthedocs.io/en/latest/topic/repack.html)
- Cryptographic machine licensing pattern (Ed25519 + hardware fingerprint): [keygen.sh example](https://github.com/keygen-sh/example-python-cryptographic-machine-files)
