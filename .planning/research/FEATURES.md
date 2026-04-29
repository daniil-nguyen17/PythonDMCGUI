# Feature Landscape: v4.1 Security, Polish & Code Health

**Domain:** Industrial HMI — per-machine licensing, code protection, codebase audit
**Researched:** 2026-04-28
**Milestone:** v4.1 on top of existing Kivy/Python/gclib app with PyInstaller (Windows) and install.sh (Pi)

---

## Domain 1: Per-Machine Hardware-Bound Licensing

### Table Stakes

Features the approach must have to be usable at all.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Hardware fingerprint collection | Ties license to a specific machine; without it any license file copies freely | Low | Pi: `/proc/cpuinfo` Serial field is stable across reboots, unique per SoC. Windows: combination of MAC + volume serial or WMI disk serial |
| Ed25519 signed license file | Cryptographic proof the license was issued by the keyholder; tamper detection without network round-trip | Low | `cryptography` (PyCA) supports Ed25519 natively, is PyInstaller-compatible, already in the Python ecosystem |
| Keygen CLI tool (internal) | Someone must be able to generate a license for a new machine without writing code every time | Low | Simple Python script: read machine ID from customer, sign a JSON blob, output `.lic` file |
| Startup validation | App refuses to start if no valid license for the current machine is present | Low | Verify signature with embedded public key; check machine ID matches; check expiry if set |
| Graceful failure screen | Operator sees "Contact Binh An" rather than a Python traceback | Low | One locked screen shown before any auth or machine UI loads |

### Differentiators

Worth adding but not strictly required for the sub-100 deployment scale.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Expiry date in license payload | Allows trial licenses or forces renewal for paid-maintenance model | Low | Add `expires` field to JSON payload; verify at startup |
| Machine-type binding in license | License file explicitly permits only Flat Grind / Serration / Convex; prevents a license for one machine type being moved to another | Low | Add `machine_type` field alongside `machine_id`; check against `settings.json` on startup |
| Human-readable license header | Plain-text header block before binary signature makes license inspectable without tools | Very Low | e.g., `# BinhAnHMI License -- Machine: SN-XXXX -- Issued: 2026-04-28` |

### Anti-Features

Features to explicitly NOT build for this scale.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Online activation / phone-home | No internet on the factory floor; network dependency will break in production | Fully offline signed file with public key embedded in the app binary |
| Revocation server / CRL | Requires cloud infrastructure for fewer than 100 machines; over-engineered | If a machine is decommissioned, do not renew its license; expiry handles the rest |
| License server / floating licenses | Makes sense for enterprise seat licensing, not for fixed-installation industrial controllers | One license file per physical machine |
| Hardware security dongle (USB) | Adds hardware dependency that can be lost or break; dongles cost $30-100 each | Ed25519 signed file is sufficient at this scale |
| Per-build encryption key | Requires a new build per license, breaking the single-binary deployment model | Sign the license file; do not encrypt the binary uniquely per machine |
| Third-party licensing SaaS (Keygen, Cryptlex, LimeLM) | Monthly SaaS cost and internet dependency for fewer than 100 offline deployments; recurring vendor risk | Implement directly with PyCA `cryptography` — roughly 50 lines of code |

### Hardware Fingerprint Implementation Notes

**Raspberry Pi (MEDIUM confidence):**
- `/proc/cpuinfo` contains a `Serial` field: 16 hex characters, unique per SoC, stable across OS reinstalls
- Read with `open('/proc/cpuinfo').read()`, parse with regex `r'Serial\s+:\s+(\w+)'`
- MAC address from `uuid.getnode()` as a secondary component, but MAC can change on Pi 5 due to firmware; prefer CPU serial as the primary anchor

**Windows (MEDIUM confidence):**
- Volume serial: `subprocess` call to `vol C:` or WMI `Win32_LogicalDisk.VolumeSerialNumber`
- MAC address via `uuid.getnode()` — stable for built-in NICs, can drift if USB NICs are swapped
- Safe composite: SHA-256 of `(volume_serial + mac_address)` — if one component is unavailable, degrade gracefully with a warning

**Fingerprint stability risk:** Pi serial is maximally stable. Windows volume serial changes on full reformat. Document this as a known scenario requiring a new license file from Binh An.

### Feature Dependencies

```
Hardware fingerprint → Keygen CLI (machine ID input format must be defined first)
Keygen CLI → License file format (JSON payload + Ed25519 signature)
License file format → Startup validation (reads and verifies the same format)
Startup validation → Graceful failure screen (shown when validation fails)
```

---

## Domain 2: Code Protection

### Reality Check First

Python source protection is a spectrum, not a binary. No Python protection is equivalent
to compiled C code. The realistic goal for an industrial HMI at this scale is:
**raise the cost of casual copying above the benefit**, not prevent a determined
reverse-engineer. This shapes which features are worth implementing.

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Remove .py source files from Pi deployment | Source `.py` files are present on Pi at `/opt/binh-an-hmi/`; trivially copyable without action | Low | Compile to `.so`, then delete source `.py` files in install.sh after the build step; PyInstaller bundles on Windows do not expose raw `.py` files |
| Cython compilation for Pi (.py → .so) | Source `.py` files are present on Pi; compiling to `.so` removes them | Medium | Build natively on Pi with aarch64 GCC; produces per-arch binaries tied to Python version |
| PyArmor bytecode obfuscation for Windows | Wraps PyInstaller bundle with obfuscated bytecode; harder to decompile than raw `.pyc` | Medium | PyArmor 9.x integrates with PyInstaller via `--pack`; free tier has script-size limits — a paid Basic license is needed for a full Kivy app |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Cython for business-logic modules only | Protects IP-sensitive code (machine params, auth, licensing) without the complexity of compiling all UI | Low-Medium | Compile `auth_manager.py`, `machine_config.py`, and the new `licensing.py`; leave KV files and screen modules as-is — they contain no IP |
| Strip docstrings pre-compile | Removes implementation hints from decompiled bytecode | Low | Run `python -OO` or pre-process source before the Cython pass |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full Cython compilation of all modules including UI | KV files cannot be Cythonized; Kivy's dynamic widget system can break with aggressive Cython optimisation flags | Cython only the non-UI business logic modules |
| Cross-compilation of .so for Pi from Windows | Toolchain is fragile; .so file naming issues (x86_64 suffix instead of aarch64) require manual correction; ARM GCC setup on Windows is complex | Build natively on Pi or use a Pi-architecture Docker image on Linux |
| PyArmor and Cython simultaneously on the same module | Redundant layers with conflicting import mechanisms; PyArmor wraps the module loader, Cython replaces it | Choose one per target: PyArmor for Windows (PyInstaller path), Cython for Pi |
| Obfuscating Kivy .kv files | KV files are declarative text, not executable bytecode; no obfuscation tool handles them | Accept that .kv files are readable; they contain UI structure, not business logic |

### Platform-Specific Notes

**Windows (PyArmor + PyInstaller):**
- PyArmor 9.x workflow: `pyarmor gen` obfuscates source → `pyarmor gen --pack foo.spec` re-runs PyInstaller on obfuscated sources. The `--pack` flag is mandatory because obfuscated scripts have no importable names, so PyInstaller's analysis cannot find hidden imports without the existing spec file.
- PyArmor free tier blocks large scripts (exact limit undocumented; a full Kivy app is very likely to exceed it). A paid Basic license removes this limit.
- ANGLE GPU driver DLLs (`angle.dep_bins`) and gclib DLLs are already declared in `BinhAnHMI.spec`; PyArmor `--pack` must reference this spec file to preserve all existing binary and data inclusions.
- Build machine dependency: PyArmor obfuscated scripts are tied to the build machine's PyArmor license; a dedicated build machine or CI environment is required.

**Raspberry Pi (Cython):**
- Compile on Pi natively: `cython module.pyx` produces `module.c` → `gcc -shared -fPIC ... -o module.so module.c`
- Python version lock: `.so` files are tied to the CPython ABI (e.g., `module.cpython-310-aarch64-linux-gnu.so`). Pi OS Python upgrades require full recompilation.
- install.sh integration: Add a `build_extensions.sh` step that runs before the final pip install phase; or ship pre-compiled `.so` files in the deployment archive and exclude source `.py` files explicitly.
- Kivy itself imports cleanly alongside Cython-compiled app modules — no interference.

### Feature Dependencies

```
Cython (Pi) → aarch64 GCC + Python 3.10 headers on the build Pi
Cython (Pi) → Python version pin in install.sh (recompile on Python upgrade)
PyArmor (Windows) → Existing BinhAnHMI.spec (must use --pack with spec)
PyArmor (Windows) → PyArmor Basic+ paid license (free tier insufficient for full app)
Code protection → License validation module compiled first (validator is highest-priority protected module)
```

---

## Domain 3: Codebase Audit

### Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Dead code removal | Accumulated from 4 major versions; dead branches slow reading and create confusion for future changes | Low | Vulture finds unused functions, classes, variables; Ruff F401 finds unused imports |
| Unused import cleanup | Kivy screen files commonly accumulate unused Widget/Layout imports | Low | Ruff with `--fix` handles F401 auto-removal; safe to run non-destructively |
| Naming consistency pass | Mix of conventions across DMC variable names and Python helpers added across v1-v4 | Low | Manual review informed by Ruff N-series naming rules |
| Stale docstring and comment cleanup | Outdated comments referencing old architecture (pre-DR polling, pre-nav-gate patterns, XQ calls) | Low | Manual: search for references to patterns documented in MEMORY.md as superseded |
| Import organisation | Stdlib → third-party → local grouping; inconsistent across files | Very Low | Ruff I-series (isort rules) auto-fixes import order; safe to run with `--fix` |

### Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Ruff full lint pass with pyproject.toml config | Single tool replaces Flake8 + isort + autoflake; fast, configurable, auto-fixable | Low | Add `[tool.ruff]` section to existing `pyproject.toml`; run `ruff check --fix src/` |
| Cyclomatic complexity check | Flags functions too long or branchy to safely modify — especially DMC state machine callbacks | Low | Ruff C90 (McCabe complexity) with threshold of 10; `machine_config.py` and `controller.py` are likely flagged |
| Type annotation pass on public APIs | Enables mypy and editor support; important for `auth_manager.py`, `machine_config.py`, and the new `licensing.py` | Medium | Kivy types are incomplete (mypy-types-kivy stubs exist but are partial); annotate only non-Kivy modules; ignore Kivy widget subclasses entirely |
| Test coverage map | Identifies which modules have zero test coverage — licensing and auth are highest risk | Low | `pytest --cov=dmccodegui --cov-report=term-missing`; existing test infrastructure is already in place |

### Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Full mypy strict mode on Kivy subclasses | Kivy's metaclass and property system generates thousands of mypy errors; not fixable without complete stubs | Run mypy with `ignore_missing_imports = true` and `exclude` patterns for `ui/` and `screens/`; annotate only pure-Python modules |
| Automated refactoring of KV files | KV file structure is intentional and tested; automated refactoring risks breaking widget binding | Manual visual inspection only; KV files excluded from all linting passes |
| Rewriting passing modules | v3.0 `flat_grind/` is explicitly marked stable in project memory; audit means read and flag, not rewrite | Flag issues in notes; fix only what causes active bugs or directly blocks v4.1 features |
| SonarQube or heavyweight CI analysis | Adds server infrastructure for a single-developer project | Ruff + Vulture + pytest-cov run locally before each release is sufficient |

### Audit Categories and Tooling

```
Category                Tool(s)                           Scope
------------------------------------------------------------------
Unused imports          ruff check --select F401           src/
Dead code               vulture src/                       src/
Style / formatting      ruff format src/                   src/
Import ordering         ruff check --select I              src/
Naming consistency      ruff check --select N (manual fix) src/
Cyclomatic complexity   ruff check --select C90            src/
Type annotations        mypy --ignore-missing-imports      non-Kivy modules only
Test coverage           pytest --cov                       tests/
Docstring staleness     manual review                      key modules
HMI variable patterns   grep for XQ references             src/ (MEMORY.md rule)
Threading violations    manual review                      controller.py, hmi/
```

### Phase-Specific Audit Priorities

The audit is not uniform. Modules adjacent to new v4.1 additions carry the most risk.

| Module Area | Audit Priority | Reason |
|-------------|---------------|--------|
| `auth/auth_manager.py` | HIGH | New licensing code sits adjacent; ensure no logic drift between auth and license check |
| `machine_config.py` | HIGH | Per-machine parameter pages are being added; existing param_defs need consistency check |
| `controller.py` + `hmi/` | HIGH | DR migration (MEMORY.md) means old polling artifacts may remain as dead code |
| `screens/flat_grind/` | LOW | Marked stable in project memory — read-only audit, no changes without explicit request |
| `screens/serration/` | MEDIUM | Serration run screen UI was recently reworked; check for leftover bcomp/ccomp artifacts |
| `screens/convex/` | MEDIUM | Least tested machine type; parameter page likely incomplete |
| `ui/*.kv` | LOW | Excluded from automated linting; visual inspection only |
| `deploy/windows/BinhAnHMI.spec` | MEDIUM | Cython and PyArmor integration will require spec file changes |
| `deploy/pi/install.sh` | MEDIUM | Cython build step and license file deployment need to be added |

### Feature Dependencies

```
Ruff config → pyproject.toml (already exists; add [tool.ruff] section)
Vulture → run after Ruff to avoid false positives from imports that Ruff already removed
Type annotation → licensing.py must be annotated before Cython compilation (Cython uses annotations)
Test coverage → run after dead code removal to confirm nothing active was deleted
```

---

## MVP Recommendation

Prioritize in this order:

1. **Hardware fingerprint + license file format** — defines the data contract everything else depends on
2. **Startup validation + graceful failure screen** — the visible enforcement; no other security feature matters without this
3. **Keygen CLI** — internal tool; must exist before any machine can be shipped with a license
4. **Codebase audit (Ruff + Vulture pass)** — automated tooling first, then manual dead code review; do this before adding Cython to avoid compiling dead modules
5. **Cython compilation for Pi (business logic modules only)** — most impactful protection for Pi kiosk deployment
6. **PyArmor for Windows** — depends on confirming PyArmor license cost and testing integration with the existing `.spec` file; defer if toolchain friction is high

Defer:
- Online activation, revocation servers, floating licenses — out of scope at fewer than 100 units
- Full mypy strict mode — incomplete Kivy stubs make this a time sink with low ROI at this project scale
- Cross-compilation of Cython from Windows — build on Pi natively to avoid ARM toolchain complexity

---

## Sources

- [PyArmor license types](https://pyarmor.readthedocs.io/en/latest/licenses.html) — MEDIUM confidence
- [PyArmor GitHub](https://github.com/dashingsoft/pyarmor) — MEDIUM confidence
- [PyArmor pack + PyInstaller integration](https://pyarmor.readthedocs.io/en/latest/topic/repack.html) — MEDIUM confidence
- [Cython source files and compilation (official)](https://cython.readthedocs.io/en/latest/src/userguide/source_files_and_compilation.html) — HIGH confidence
- [Cython on Raspberry Pi forum](https://forums.raspberrypi.com/viewtopic.php?t=352039) — MEDIUM confidence
- [PyCA cryptography Ed25519 (official)](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/) — HIGH confidence
- [PyNaCl digital signatures (official)](https://pynacl.readthedocs.io/en/latest/signing/) — HIGH confidence
- [Raspberry Pi CPU serial from /proc/cpuinfo](https://www.raspberrypi-spy.co.uk/2012/09/getting-your-raspberry-pi-serial-number-using-python/) — HIGH confidence
- [Vulture dead code detection](https://github.com/jendrikseipp/vulture) — HIGH confidence
- [Ruff F401 unused import detection](https://github.com/astral-sh/ruff/issues/872) — HIGH confidence
- [mypy-types-kivy stubs (incomplete)](https://github.com/tonyfinn/mypy-types-kivy) — MEDIUM confidence
- [keygen.sh offline licensing model](https://keygen.sh/docs/choosing-a-licensing-model/offline-licenses/) — MEDIUM confidence

---

*Feature research for: v4.1 Security, Polish & Code Health milestone*
*Researched: 2026-04-28*
