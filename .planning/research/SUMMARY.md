# Research Summary — v4.1 Security, Polish & Code Health

## Stack Additions

| Tool | Purpose | Scope |
|------|---------|-------|
| `cryptography>=42.0` | Ed25519 signing/verification | Runtime (both platforms) |
| Custom `fingerprint.py` | Pi CPU serial + Windows BIOS UUID | Runtime (~50 lines, no deps) |
| Cython 3.x | `.py` → `.so` compilation on Pi | Build-time (Pi only) |
| PyArmor 9.x (paid Basic) | Bytecode encryption for Windows | Build-time (dev machine) |
| ruff `>=0.4` | Replaces flake8+isort+autoflake | Dev-only |
| vulture `>=2.11` | Dead code detection | Dev-only |

**Only one new runtime dependency:** `cryptography>=42.0`

## Feature Priorities

**Table Stakes (must-have):**
- Hardware fingerprint: Pi CPU serial (`/proc/cpuinfo`), Windows BIOS UUID
- Ed25519 signed license file (offline JSON, no internet)
- Keygen CLI (developer-only, never deployed)
- Startup validation before Kivy loads → `sys.exit(1)` on failure
- Cython `.so` for Pi business logic (source `.py` deleted post-compile)
- Ruff + Vulture audit pass with Kivy allowlist
- `_CONVEX_PARAM_DEFS` completion in machine_config.py

**Defer:**
- Online activation / revocation server
- Full mypy strict mode
- Cross-compilation of Cython from Windows

## Architecture — Key Integration Points

1. **License check** inserts into `main.py` pre-Kivy block (after `setup_logging()`, before `_detect_preset()`)
2. **License file** located via existing `_get_data_dir()` pattern — no new path logic
3. **Cython targets** (6 modules): `machine_config.py`, `hmi/dmc_vars.py`, `hmi/data_record.py`, `licensing/validator.py`, `auth/auth_manager.py`, plus `controller.py` is **EXCLUDED** (gclib ctypes boundary)
4. **PyArmor** uses two-step: obfuscate first → then PyInstaller reads obfuscated tree. Never `pyarmor pack`.
5. **Param defs** — only `_CONVEX_PARAM_DEFS` needs filling; registry pattern already correct

## Top 5 Pitfalls

1. **MAC as Pi fingerprint → lockout** when USB NIC changes. Use `/proc/cpuinfo` Serial only.
2. **`pyarmor pack` + PyInstaller 6 → broken bundle.** Two-step approach mandatory.
3. **Cython on `controller.py` → silent gclib failure.** Exclude from all compile targets.
4. **ARM `.so` ABI lock** → Python version upgrade breaks app. Pin Python version in install.sh.
5. **Vulture flags Kivy screen classes as dead code** — they're string-referenced in `_REGISTRY`. Build allowlist first.

## Suggested Phase Order

| # | Phase | Why this order |
|---|-------|----------------|
| 1 | Codebase Audit | Clean before protecting — don't compile dead code |
| 2 | Bug Fixes + UI Polish | Fix known issues on clean codebase |
| 3 | Per-Machine Parameter Pages | Data edit, no toolchain deps, unblocks Convex testing |
| 4 | Licensing Core + Integration | Ed25519 module → wire into main.py startup |
| 5 | Pi Cython Protection | After audit (clean code) + licensing (validator.py is a target) |
| 6 | Windows PyArmor Protection | Last — gated on paid license, highest complexity |

## Open Questions

- PyArmor paid license cost — verify before Phase 6
- Convex machine parameter specifications — needed for Phase 3
- Windows 11 build version on field machines — determines `wmic` vs PowerShell fingerprint path
- Pi Python version pinning — which exact version ships with target Bookworm build

---
*Synthesized: 2026-04-28 from STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md*
