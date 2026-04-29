# Technology Stack: Security, Code Protection & Codebase Audit

**Project:** DMC Grinding GUI — v4.1 Security, Polish & Code Health
**Researched:** 2026-04-28
**Scope:** NEW capabilities only — per-machine licensing, code protection, codebase audit tooling.
**Existing validated stack:** NOT re-researched (Python 3.10+, Kivy 2.2+, gclib, matplotlib, PyInstaller 6.19, Inno Setup 6.7, install.sh + systemd).

---

## Recommended Stack: New Additions Only

### Licensing — Cryptographic Signing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `cryptography` (PyCA) | >=42.0 | Ed25519 key generation, license file signing, signature verification at startup | Ships pre-compiled wheels for both x86-64 (Windows) and aarch64 (Pi/ARM). Maintained by the same PyCA team that maintains PyNaCl. Ed25519 support is in the stable API (not "hazmat" hazardous-material tier — it is explicitly recommended in the docs). Single package covers signing, serialization, and any future crypto primitives. No libsodium native library dependency separate from the wheel. |

**Why `cryptography` over PyNaCl:** Both are PyCA projects. `cryptography` is more appropriate here because (a) it ships a single wheel with no separate libsodium .so requirement, (b) its Ed25519 API (`Ed25519PrivateKey`, `Ed25519PublicKey`) maps directly to the keygen + verify pattern without wrapping NaCl's signing key abstraction, and (c) it is already a transitive dependency of many packages so it may already be present in the venv. PyNaCl would be redundant.

**Why NOT stdlib:** Python's `hashlib` has no Ed25519. The `ssl` module wraps OpenSSL but not in a usable signing API. `cryptography` is the correct answer.

### Licensing — Hardware Fingerprinting

No third-party library is needed. Use platform-native sources with a custom ~50-line module:

| Platform | Primary source | Fallback |
|----------|---------------|---------|
| Raspberry Pi | `/proc/cpuinfo` Serial field (16-hex-digit, unique per board) | `/sys/firmware/devicetree/base/serial-number` |
| Windows | `wmic csproduct get UUID` via `subprocess` | MAC address from `uuid.getnode()` |

**Implementation pattern:**
```python
import hashlib, platform, subprocess, uuid

def hardware_fingerprint() -> str:
    """Return a stable 32-char hex fingerprint for this machine."""
    raw = _collect_raw_ids()
    return hashlib.sha256(raw.encode()).hexdigest()[:32]

def _collect_raw_ids() -> str:
    if platform.system() == "Linux":
        return _pi_serial()
    elif platform.system() == "Windows":
        return _windows_uuid()
    raise RuntimeError(f"Unsupported platform: {platform.system()}")

def _pi_serial() -> str:
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("Serial"):
                    return line.split(":")[1].strip()
    except OSError:
        pass
    try:
        with open("/sys/firmware/devicetree/base/serial-number") as f:
            return f.read().strip().rstrip("\x00")
    except OSError:
        pass
    raise RuntimeError("Cannot read Pi serial number")

def _windows_uuid() -> str:
    result = subprocess.check_output(
        ["wmic", "csproduct", "get", "UUID"], text=True
    )
    lines = [l.strip() for l in result.splitlines() if l.strip()]
    # lines[0] is "UUID", lines[1] is the value
    return lines[1] if len(lines) > 1 else str(uuid.getnode())
```

**Why not a fingerprinting library:** No maintained cross-platform Python library exists that handles both the Pi `/proc/cpuinfo` pattern and Windows WMIC UUID in one package. The custom module is ~50 lines, has zero dependencies, and is completely auditable. MAC address alone is too easily spoofed; Pi serial + Windows BIOS UUID are hardware-bound and stable across reboots/OS reinstalls.

**Why dmidecode is NOT used on Pi:** `dmidecode` is x86-only and not installable on ARM Raspberry Pi OS. `/proc/cpuinfo` is the correct Pi-native source.

### Licensing — License File Format

Use a JSON envelope signed with Ed25519. No library needed beyond `cryptography` and `json`:

```json
{
  "machine_id": "a3f9b2c1d4e5...",
  "machine_type": "flat_grind",
  "issued": "2026-04-28",
  "expires": null,
  "signature": "<base64url Ed25519 signature of canonical JSON payload>"
}
```

The keygen CLI tool (a small `keygen.py` script, not a separate package) reads a private key file, generates the fingerprint for the target machine, signs the payload, and writes `license.json`. The HMI validates on startup: compute fingerprint → verify signature with embedded public key → check machine_type matches current type → reject if any check fails.

**Embed the public key** as a constant string in the source (or compiled `.so` / PyArmor-obfuscated module). The private key never leaves the developer machine.

---

### Code Protection — Raspberry Pi (.so compilation)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Cython | >=3.0 | Transpile .py → .c → .so on the Pi; hides source from casual inspection | Cython 3.0 is the current stable major release (3.x series). Ships aarch64 wheels for Python 3.11/Bookworm on PyPI. The `build_ext --inplace` flow produces ARM-native `.so` files. No architecture-specific flags needed — GCC on Bookworm defaults to aarch64. |
| `build-essential` + `python3-dev` | OS-provided | C compiler toolchain for Cython's generated C → .so step | Already required for some Kivy deps; likely already in install.sh's apt block. |

**Build integration with install.sh:**

```bash
# In install.sh, after pip install:
log "Compiling Python modules to .so..."
cd "$INSTALL_DIR"
"$VENV_DIR/bin/pip" install cython
"$VENV_DIR/bin/python" setup_protect.py build_ext --inplace
# Remove .py sources after successful compile
find src/dmccodegui -name "*.py" \
    ! -name "__init__.py" \
    ! -name "main.py" \
    -delete
```

**setup_protect.py** (committed to repo, not part of main setup.py):
```python
from setuptools import setup
from Cython.Build import cythonize
import glob

# Cythonize everything except main.py and __init__.py files
modules = glob.glob("src/dmccodegui/**/*.py", recursive=True)
modules = [m for m in modules
           if "__init__" not in m and "main.py" not in m]

setup(ext_modules=cythonize(modules, compiler_directives={"language_level": "3"}))
```

**Do NOT Cythonize:**
- `main.py` — PyInstaller/systemd entry point, must remain a .py
- `__init__.py` files — package namespace, must remain importable as .py
- `keygen.py` — runs on dev machine only, not deployed

**Confidence note:** Cython 3.x on aarch64 Bookworm is confirmed. The `setup.py build_ext` pattern is the documented approach. Kivy `.kv` files and resource loading are unaffected — only `.py` logic modules are compiled.

### Code Protection — Windows (bytecode obfuscation)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PyArmor | 9.x (latest: 9.2.5) | Obfuscate Python bytecode in the PyInstaller bundle | The only mature Windows Python obfuscation tool with documented PyInstaller integration. |

**Critical constraint — PyArmor free tier is NOT sufficient:**

PyArmor's trial version has a hard ~32 KB per-file bytecode limit. The DMC GUI's larger modules (run screens, machine_config, etc.) will exceed this. A paid Basic or Pro license is required. License cost is a one-time purchase; v8.x licenses upgrade to v9.x free.

**PyInstaller 6 compatibility is a known pain point:**

PyArmor's `--pack` command targets PyInstaller < 6.0 in its standard flow. With PyInstaller 6.x (which this project uses at 6.19.0), the integration requires the manual repack approach:

```bash
# 1. Obfuscate scripts first
pyarmor gen src/dmccodegui/

# 2. Build with PyInstaller using the obfuscated output
pyinstaller dmcgui.spec --distpath dist_obfuscated

# 3. PyArmor repack step (injects PyArmor runtime into the bundle)
pyarmor repack -e dmcgui.spec dist_obfuscated/DMCGrindingGUI/DMCGrindingGUI.exe
```

The PyInstaller spec must add PyArmor's runtime as a hidden import and include its `.pyd` runtime module in `datas`. This adds complexity to the build pipeline.

**Honest assessment:** PyArmor on Windows with PyInstaller 6 works but requires careful integration. If the protection goal is "make casual inspection hard" rather than "military-grade security," an alternative is acceptable — see Alternatives Considered below.

**Do NOT use PyArmor on the Pi build.** Cython `.so` files ARE the protection on Pi. PyArmor is Windows-only in this stack.

---

### Codebase Audit Tooling

These are **dev-machine-only tools** (not deployed, not in requirements-pi.txt). Add to `requirements-dev.txt` or install manually in the dev venv.

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| ruff | >=0.4 (current: ~0.14.x) | Lint + import cleanup (replaces flake8 + isort + autoflake) | Written in Rust; runs full-repo scan in under 1 second. Single config in `pyproject.toml`. Covers unused imports (F401), undefined names (F821), import sort, and pydocstyle rules (D-series) in one pass. Replaces autoflake for import cleanup. |
| vulture | >=2.11 | Dead code detection (unused functions, classes, variables) | AST-based static analysis; assigns 60–100% confidence to dead code findings. Ruff does not replace vulture — ruff catches unused imports and variables in scope, vulture catches unreachable/unreferenced top-level definitions across modules. They are complementary. |

**Why NOT autoflake separately:** Ruff's `--fix` mode handles unused import removal (F401 rule with `--unsafe-fixes` flag). autoflake is made redundant.

**Why NOT pylint:** Ruff covers 90%+ of pylint's rules and is 100x faster. Pylint's remaining value (type inference, some refactoring suggestions) is not needed for this audit scope.

**Why NOT interrogate for docstring coverage:** Ruff's D-series rules (pydocstyle) flag missing docstrings inline with the rest of the lint pass. A separate coverage tool adds overhead without benefit at this project's scale.

**Suggested ruff config in `pyproject.toml`:**

```toml
[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = [
    "F",    # pyflakes: undefined names, unused imports, unused vars
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "I",    # isort: import ordering
    "D",    # pydocstyle: docstring rules
    "UP",   # pyupgrade: modernise Python syntax
]
ignore = [
    "D100", "D101", "D102", "D103",  # missing docstrings — add progressively
    "D203", "D213",  # conflicting docstring style rules (pick one set)
]

[tool.ruff.lint.pydocstyle]
convention = "google"
```

**Suggested vulture invocation:**

```bash
vulture src/dmccodegui/ --min-confidence 80 --ignore-names "on_*,kv_*,ids"
```

The `--ignore-names` filter prevents false positives from Kivy's event handler naming convention (`on_press`, `on_release`) and KV `ids` attribute lookups, which are dynamically resolved and appear "unused" to static analysis.

---

## Alternatives Considered and Rejected

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Ed25519 signing | `cryptography` (PyCA) | PyNaCl | Both PyCA packages; `cryptography` has no separate libsodium .so dependency, cleaner API for key serialization to PEM/DER for storage, likely already a transitive dep |
| Ed25519 signing | `cryptography` (PyCA) | `python-ed25519` | Unmaintained, the original author recommends PyNaCl instead; do not use |
| Hardware fingerprinting | Custom ~50-line module | `DeviceFingerprinting` library | Unmaintained third-party library; the Pi + Windows sources are simple enough that a custom module is more maintainable and auditable |
| Hardware fingerprinting | `/proc/cpuinfo` on Pi | `dmidecode` on Pi | dmidecode is x86-only, not available on ARM/Pi |
| Windows protection | PyArmor 9 (paid) | Nuitka | Nuitka compiles to C executables (strong protection) but requires 10-30 minute builds and a paid license for commercial use; over-engineered for "casual inspection deterrence" goal |
| Windows protection | PyArmor 9 (paid) | pyc bytecode only | `.pyc` files are trivially decompilable with `uncompyle6` or `decompile3`; provides no meaningful protection |
| Pi protection | Cython .so | PyArmor on Pi | PyArmor on ARM requires the pyarmor-cli platform wheel for aarch64-linux; adds another paid-license dependency when Cython already handles Pi protection; redundant |
| Dead code detection | vulture | bandit | bandit is a security scanner (SQL injection, hardcoded secrets), not dead code; wrong tool for this job |
| Import cleanup | ruff (F401 + --fix) | autoflake | Ruff supersedes autoflake; no need for both |
| Docstring audit | ruff D-series | interrogate | interrogate only reports coverage percentage; ruff's D-series gives file-level line numbers and is already in the lint pass |

---

## Installation

### Dev Machine (Windows — build + keygen)

```bash
# Cryptographic signing tools (also in runtime requirements.txt)
pip install "cryptography>=42.0"

# Code audit tools — dev only (not deployed)
pip install ruff vulture

# PyArmor — requires paid license key activation after install
pip install pyarmor
pyarmor reg pyarmor-regfile-<your-license>.zip  # activate license
```

### Runtime `requirements.txt` Addition

```
cryptography>=42.0
```

This is the only new runtime dependency. Everything else is dev-time or build-time.

### `requirements-pi.txt` Addition

```
cryptography>=42.0
cython>=3.0   # build-time only; can be removed post-compile but harmless to leave
```

### Pi `install.sh` Addition

```bash
# Ensure build toolchain is present (may already be installed)
apt-get install -y build-essential python3-dev

# Install cryptography + cython into venv
"$VENV_DIR/bin/pip" install "cryptography>=42.0" "cython>=3.0"

# Compile .py modules to .so
log "Compiling Python source to native extensions..."
cd "$INSTALL_DIR"
"$VENV_DIR/bin/python" setup_protect.py build_ext --inplace

# Optionally strip .py sources (leave __init__.py and main.py)
find "$INSTALL_DIR/src" -name "*.py" \
    ! -name "__init__.py" \
    ! -name "main.py" \
    -delete
log "Source stripping complete."
```

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| `cryptography` for Ed25519 | HIGH | PyCA project, official docs confirmed Ed25519 in stable API, ARM + x86 wheels on PyPI |
| Pi hardware fingerprint via `/proc/cpuinfo` | HIGH | Raspberry Pi Foundation documented; widely used for Pi licensing; Bookworm confirmed |
| Windows UUID via `wmic` | MEDIUM | wmic is deprecated in Windows 11 22H2+ in favor of PowerShell `Get-WmiObject`; may need fallback to `Get-CimInstance Win32_ComputerSystemProduct` via PowerShell |
| Cython 3.x on aarch64/Bookworm | HIGH | Pre-built wheels confirmed for cp311/aarch64; build_ext pattern is official Cython docs |
| PyArmor 9 + PyInstaller 6 | MEDIUM | Works but requires manual repack flow; trial version 32 KB limit will block large modules; paid license required; integration complexity is real |
| ruff for lint + import cleanup | HIGH | Actively maintained by Astral; 0.14.x confirmed current in 2025; replaces multiple tools |
| vulture for dead code | HIGH | Actively maintained; confirmed Kivy false-positive mitigation via --ignore-names |

---

## Key Integration Risk: Windows UUID Deprecation

`wmic` commands are deprecated as of Windows 11 22H2 (October 2023) and may be removed in a future Windows build. The fallback is a PowerShell one-liner:

```python
def _windows_uuid() -> str:
    # Try wmic first (Windows 10 / early Windows 11)
    try:
        result = subprocess.check_output(
            ["wmic", "csproduct", "get", "UUID"], text=True, timeout=5
        )
        lines = [l.strip() for l in result.splitlines() if l.strip()]
        if len(lines) > 1 and lines[1] != "UUID":
            return lines[1]
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    # Fallback: PowerShell Get-CimInstance (Windows 11 22H2+)
    result = subprocess.check_output(
        ["powershell", "-Command",
         "(Get-CimInstance Win32_ComputerSystemProduct).UUID"],
        text=True, timeout=5
    )
    return result.strip()
```

This handles both current Windows 11 versions and future-proofs against wmic removal. **Flag this for validation on target Windows machines before shipping.**

---

## What NOT to Add

- **A licensing SaaS or online activation server:** This is an in-house industrial tool. Network-dependent licensing is a single point of failure on a machine floor. License files are offline JSON — done.
- **Nuitka:** Overkill. 30-minute builds and a paid license for "make casual inspection harder" is wrong tradeoff.
- **Full `.pyx` rewrite of the Kivy UI layer:** Cython compiles plain `.py` files directly; no `.pyx` rewrite required. Only logic modules are compiled; KV files stay as-is.
- **A separate docstring coverage CI gate:** Run ruff + vulture manually during the audit phase. Adding CI gates for a one-time audit is process overhead that doesn't serve the project.
- **`bandit` security scanning:** No user-facing web exposure, no SQL, no network service. Bandit's rules don't apply to this use case.
- **License server or floating license model:** One license file per physical machine, generated by keygen.py, copied to the SD card / Windows install folder. No server required.

---

## Sources

- cryptography Ed25519 API (stable): https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/
- PyNaCl signing docs (comparison reference): https://pynacl.readthedocs.io/en/latest/signing/
- Raspberry Pi serial number via /proc/cpuinfo: https://www.raspberrypi-spy.co.uk/2012/09/getting-your-raspberry-pi-serial-number-using-python/
- Pi serial number forum (Raspberry Pi 4 confirmed): https://forums.raspberrypi.com/viewtopic.php?t=337570
- dmidecode ARM limitation: https://forums.raspberrypi.com/viewtopic.php?t=10741
- Cython 3.x installation + ARM support: https://cython.readthedocs.io/en/latest/src/quickstart/install.html
- Cython build_ext pattern: https://cython.readthedocs.io/en/latest/src/quickstart/build.html
- Cython Pi performance article (confirms .so generation on Pi): https://medium.com/data-science/boosting-python-scripts-with-cython-applied-on-raspberry-pi-5ea191292e68
- PyArmor 9.2.5 docs: https://pyarmor.readthedocs.io/en/latest/
- PyArmor license types (confirms 32KB trial limit and paid requirement): https://pyarmor.readthedocs.io/en/latest/licenses.html
- PyArmor repack for PyInstaller 6: https://pyarmor.readthedocs.io/en/latest/topic/repack.html
- PyArmor 9 release (Oct 2024): https://www.tegakari.net/en/2024/10/pyarmor_v9/
- Ruff linter docs: https://docs.astral.sh/ruff/linter/
- Ruff 0.14.x (current 2025): https://github.com/astral-sh/ruff
- vulture dead code detection: https://github.com/jendrikseipp/vulture
- Cython code protection analysis (Cisco): https://blogs.cisco.com/developer/securingpythoncodewithcython01

---

*Stack research for: DMC Grinding GUI — v4.1 Security, Polish & Code Health*
*Researched: 2026-04-28*
*Scope: New additions only — licensing, code protection, audit tooling*
