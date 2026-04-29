# Domain Pitfalls: v4.1 Security, Polish & Code Health

**Domain:** Adding hardware-bound licensing, code protection, codebase audit, and param-page changes to a deployed industrial HMI
**Researched:** 2026-04-28
**Confidence:** HIGH (codebase read directly; toolchain issues verified via official issue trackers)

---

## Critical Pitfalls

Mistakes that cause production lockouts, silent feature regressions, or require re-shipping SD cards / installers.

---

### Pitfall 1: MAC Address Is Not a Stable Hardware Fingerprint

**What goes wrong:** The license system uses `uuid.getnode()` or `netifaces` to get the Pi's MAC address as the fingerprint, then an operator swaps the Ethernet cable to a USB-to-Ethernet adapter (common in the field), adds a Wi-Fi dongle, or the Pi 500 assigns different NIC ordering after an OS update. The MAC now differs from what is in the signed license file. The machine boots to a lockout screen. The operator cannot run parts. There is no recovery path short of a keygen re-issue and manual file transfer.

**Why it happens:** Linux enumerates network interfaces in kernel discovery order. On the Pi 500 (Bookworm 64-bit), adding or removing USB peripherals changes the `eth0`/`eth1` ordering. The Pi's onboard NIC has a stable MAC, but it requires querying the right interface by name, not by index. `uuid.getnode()` returns the first non-loopback MAC it finds, which is non-deterministic when multiple NICs are present.

**Consequences:** Silent production lockout in the field with no user-visible explanation. The machine boots but the operator cannot dismiss the license error without admin intervention (SSH or keyboard) and a new license file from the keygen operator.

**Prevention:**
- Build the fingerprint from the Raspberry Pi CPU serial, not the MAC. The CPU serial is hardcoded on the board and survives SD card replacement, NIC changes, and OS reinstalls. Read it with: `cat /proc/cpuinfo | grep Serial` (Linux) or via `subprocess`.
- On Windows, use the `wmic csproduct get UUID` motherboard UUID (stable across NIC changes) as primary, with MAC as a secondary component.
- Hash multiple components (CPU serial + motherboard UUID) together so no single component change causes an outright mismatch; use a weighted match or tolerance (e.g., 2-of-3 components must match).
- Build a grace-period counter into the license file: allow N boots after a fingerprint mismatch before hard locking, giving time to re-issue without stopping production.

**Detection:** Test fingerprint stability by unplugging Ethernet and plugging in a USB dongle before the license check runs. Verify the fingerprint string does not change.

---

### Pitfall 2: PyArmor 8.x Is Not Compatible with PyInstaller 6.x

**What goes wrong:** The current build chain uses PyInstaller 6.x (shipping in the `dist/BinhAnHMI` output that already exists in the repo). PyArmor 8 does not support PyInstaller 6.0 and above. Attempting to use `pyarmor pack` against PyInstaller 6.x raises spec-file errors or silently produces a build that raises `RuntimeError` on import of any protected module at launch. The symptom is that the installer boots to a black screen with no error because `console=False` hides stderr.

**Why it happens:** PyArmor 8's `pyarmor pack` command replaces the PyInstaller spec bootstrap. PyInstaller 6 changed internal spec hooks in a way that broke PyArmor's repack function. The issue is confirmed in the official PyArmor issue tracker (issues #1714, #1824, #1834) and remains open as of mid-2025. The workaround is to pin PyInstaller to 5.x, which conflicts with any dependency that requires PyInstaller 6+ or with Windows 11 AV that flags older PyInstaller stubs as malware.

**Consequences:** The existing working Windows installer must be rebuilt from scratch using a pinned old PyInstaller version, or PyArmor must be abandoned for an alternative. Either path is significant rework.

**Prevention:**
- Do not use `pyarmor pack` at all. Use PyArmor in "obfuscate only" mode: obfuscate `.py` sources first, then run PyInstaller manually on the obfuscated output. This decouples the two tools and avoids the spec incompatibility.
- Pin the PyArmor version in `requirements-dev.txt` to the last known-good version for the PyInstaller version in use. Verify the combination in a clean venv before committing to it.
- Consider whether PyArmor is necessary on Windows at all. The deployed `.exe` is a bundled binary that already strips source. For this threat model (preventing casual inspection, not professional reverse engineering), `.pyc` obfuscation inside the bundle may be sufficient and eliminates the PyArmor dependency entirely.

**Detection:** After adding PyArmor to the build, run the built `.exe` from a terminal (not double-click) so stderr is visible. Confirm no `RuntimeError` on startup.

---

### Pitfall 3: Cython Compilation Breaks gclib ctypes Import Path at Runtime

**What goes wrong:** `controller.py` loads gclib as a ctypes-wrapped C extension. When `controller.py` is compiled to a `.so` by Cython for Pi deployment, the Cython-compiled module cannot find `gclib.so` at runtime because the ctypes `CDLL` path resolution differs between a `.py` source import and a Cython `.so` module. Specifically, the `__file__` attribute of a Cython module points to the `.so` file, not a `.py`, which breaks any relative path construction used in `find_library()` fallback logic.

**Why it happens:** In `controller.py`, the gclib library is loaded via `import gclib` (a Python C extension), not `ctypes.CDLL` directly. But gclib's own Python wrapper internally uses `ctypes.CDLL` to load `libgclib.so`. When the importing module is a Cython `.so`, the working directory assumptions for `ctypes.util.find_library()` differ from when it is a plain `.py`. Additionally, PyInstaller cannot detect ctypes DLL dependencies inside Cython-compiled modules because it can only inspect Python ASTs, not compiled C code.

**Consequences:** The app launches on the Pi but silently falls back to `gclib = None` / `GCLIB_AVAILABLE = False`, meaning all controller commands become no-ops with no exception — the HMI appears to work but never communicates with the Galil controller. This is dangerous in a machine control context.

**Prevention:**
- Do not compile `controller.py` with Cython. This file is the ctypes boundary. Keep it as a plain `.py` source on Pi and protect only the business logic files (screen logic, auth, machine_config).
- Verify `GCLIB_AVAILABLE` is `True` at startup and surface a visible error (not a silent log) if it is not. The current `try/except ImportError` that sets `gclib = None` swallows this failure in production.
- On Pi, test the Cython build against the controller before deploying to the field. The gclib import success/failure is easy to check with a 2-line test script.

**Detection:** After Cython compilation, run `python -c "from dmccodegui.controller import GCLIB_AVAILABLE; assert GCLIB_AVAILABLE"` from the Pi deployment directory.

---

### Pitfall 4: ARM64 .so Files Are Not Portable Between Pi Models and Python Minor Versions

**What goes wrong:** Cython `.so` files compiled on a Pi 4 running Python 3.11 will fail to load on a Pi 500 running Python 3.12 (or vice versa). The `.so` filename encodes the Python ABI tag (e.g., `machine_config.cpython-311-aarch64-linux-gnu.so`). An ABI mismatch produces `ImportError: ... does not match expected version` at startup, which — given that `machine_config` is imported in every screen's `__init__` — crashes the app before any UI renders.

**Why it happens:** Cython `.so` files are ABI-tagged and not forward/backward compatible across Python minor versions. Pi 4 (Bookworm) and Pi 500 both ship Python 3.11, but a future OS update or pip install that bumps to 3.12 will invalidate all compiled `.so` files simultaneously.

**Consequences:** A Pi OS update (`sudo apt upgrade`) silently breaks the deployed app. The operator sees a blank screen or Python traceback. Recovery requires re-compiling all `.so` files and re-deploying.

**Prevention:**
- Compile `.so` files on the exact target machine (or a matching Docker image with identical OS + Python version), never cross-compile from Windows or a different Pi model.
- Pin the Python version in `install.sh` (`python3.11` not `python3`) and add a startup version check that aborts with a clear error if the Python minor version does not match the compiled `.so` ABI.
- Document the exact `python3 --version` used for compilation in a build manifest file committed to the repo.

**Detection:** After installing the Cython build on the Pi, run `python3 -c "import dmccodegui.machine_config"` before starting the app. Fail loud, not silent.

---

## Moderate Pitfalls

---

### Pitfall 5: Vulture and Manual Dead Code Removal Flag Kivy KV String References as Unused

**What goes wrong:** The KV files use string-based class names in `#:import` directives and `Factory` lookups (e.g., `<FlatGrindRunScreen@Screen>` in a `.kv` file, or `Builder.load_string()` calls that reference class names). Static analysis tools (vulture, pylint, pyflakes) see no Python reference to `FlatGrindRunScreen` except its class definition, and flag it as "unused class" or "dead code." A developer running the audit removes the class or its imports, causing `FactoryException: Unknown class <FlatGrindRunScreen>` at runtime when the KV file tries to instantiate it.

**Why it happens:** Kivy's KV language parser looks up widget class names at parse time via `kivy.factory.Factory`, which uses string-based lookup — invisible to any Python static analysis tool. The `machine_config._REGISTRY` also stores fully-qualified class name strings (e.g., `"dmccodegui.screens.flat_grind.FlatGrindRunScreen"`) that are resolved via `importlib` at runtime. Neither pattern creates a Python import or reference that AST-based tools can follow.

**Prevention:**
- Before running any dead code audit, audit the `machine_config._REGISTRY` `screen_classes` dict to build an explicit list of every string-referenced class. These classes and their imports are untouchable regardless of what static analysis says.
- Add a `# noqa: F401 — registered in machine_config._REGISTRY` comment to every such import to suppress false-positive linting warnings.
- Run the full test suite after every batch of dead code removals. The test suite covers screen loading indirectly via `test_screen_loader.py` and `test_machine_config.py`.

**Detection:** After any audit pass, run the app cold (not resumed from a cached state) and navigate to each machine type's Run, Axes Setup, and Parameters screens. A `FactoryException` or `ModuleNotFoundError` at screen load time is the signal.

---

### Pitfall 6: Adding a param_def Entry Fails Silently if the DMC Variable Does Not Exist on the Controller

**What goes wrong:** A new entry is added to `_FLAT_PARAM_DEFS` (e.g., a new Convex-specific geometry variable). The UI card renders correctly. When `read_from_controller()` runs, the `ctrl.cmd(f"MG {var}")` call for the new variable returns an error string (Galil returns `?` for undefined variables). The `float()` parse raises `ValueError`, which is silently caught in the `except Exception: pass` block. The field stays blank (`---` or empty), with no indication to the operator that the param was never read.

**Why it happens:** `read_from_controller()` and `apply_to_controller()` both use blanket `except Exception: pass` around every individual variable read/write. This is intentional for resilience (one bad variable doesn't block all others), but it means a typo in a `var` name or a missing DMC `#PARAMS` initialization is completely invisible at runtime.

**Prevention:**
- When adding a new param_def entry, simultaneously verify the corresponding DMC variable exists in the `.dmc` file's `#PARAMS` label initialization block. If it is a new variable, add it to `#PARAMS` before adding it to `_PARAM_DEFS`.
- Add a validation step to `read_from_controller()` that logs a `WARNING` (not a silent pass) when a variable returns `?` or fails to parse: `logger.warning("param read failed: %s returned %r", var, raw)`. This is a one-line change per read loop.
- Check `var` name length — Galil DMC has an 8-character limit for variable names. `edgeThk` (7) and `grindDp` (7) are fine, but any new variable that exceeds 8 characters will always return `?` silently.

**Detection:** Enable DEBUG logging and search the log for `param read failed` after navigating to the Parameters screen with a controller connected.

---

### Pitfall 7: License Startup Check Blocking the Kivy Main Thread Causes Timeout Freeze

**What goes wrong:** The license validation reads the signed license file, computes the hardware fingerprint (which may involve `subprocess` calls to `cat /proc/cpuinfo` or `wmic`), and verifies the Ed25519 signature before the Kivy `App.run()` call or inside `App.build()`. If the subprocess call stalls (e.g., the Pi is cold-booting and `/proc` is not yet fully populated, or `wmic` is slow on a Windows domain machine), the entire UI freezes at a black screen for 5-15 seconds, which operators interpret as a crash.

**Why it happens:** `App.build()` runs on the Kivy main (GL) thread. Any blocking I/O in `App.build()` stalls the window from appearing. Kivy's event loop does not start until `App.build()` returns.

**Prevention:**
- Run license validation before `App().run()` in `main.py`, not inside `App.build()`. The validation result is passed into the app as a constructor argument or module-level flag. If validation fails, print a clear error and `sys.exit(1)` — no Kivy window needed.
- Cache the hardware fingerprint at install time (write it to a local file) so subsequent startups skip the subprocess call and just read the cached string. Invalidate the cache only if the OS detects hardware changes.
- Set a hard timeout on any subprocess calls (e.g., `subprocess.run(..., timeout=3)`). If the timeout fires, use the cached fingerprint with a warning log. Do not block startup indefinitely.

**Detection:** Time the gap between process start and first Kivy window appearance. It should be under 2 seconds on both Pi and Windows.

---

### Pitfall 8: PyArmor Runtime Raises RuntimeError When System Clock Is Wrong (Pi RTC Missing)

**What goes wrong:** PyArmor can embed an expiry date in the obfuscated runtime. When NTP is unavailable (Pi cold-boot without internet) and the system clock defaults to a past date (the Pi 500 has no RTC), PyArmor's runtime check reads the system time, determines the license is "expired," and raises `RuntimeError: Resource temporarily unavailable` before any application code runs. The app dies silently (no stderr on frozen builds).

**Why it happens:** The Pi 500 has no battery-backed RTC. On first boot without internet, the system clock defaults to the Unix epoch or last-known-good time from `/etc/fake-hwclock`. PyArmor's expiry check is a wall-clock comparison, not a TOFU (time-of-first-use) comparison. If the check happens before NTP sync completes (common on kiosk boot with slow AP association), the check fails.

**Prevention:**
- Do not embed a time-based expiry in the obfuscated runtime for Pi builds. Use PyArmor's perpetual (no-expiry) license mode for the on-device runtime, and rely on the hardware-bound license file (Ed25519) for revocation instead of time-based expiry.
- If expiry is required, use `fake-hwclock` in `install.sh` (`sudo apt-get install fake-hwclock`) and verify it saves/restores the clock correctly. Add an NTP sync wait in the systemd unit file (`After=time-sync.target`) before launching the HMI.

**Detection:** Set the Pi system clock to 2020-01-01 manually (`sudo date -s "2020-01-01"`) and attempt to launch the app. Confirm it starts normally and logs a warning rather than crashing.

---

## Minor Pitfalls

---

### Pitfall 9: `_SERRATION_PARAM_DEFS` Is Built at Module Import Time Using Shallow Copies — Mutation Leaks

**What goes wrong:** `_SERRATION_PARAM_DEFS` is constructed at module import time with `[d.copy() for d in _FLAT_PARAM_DEFS if d["var"] not in _SERRATION_EXCLUDE]`. The `d.copy()` is a shallow copy. If any code appends a new key to a dict inside `_FLAT_PARAM_DEFS` at runtime (e.g., a future audit adds a `"tooltip"` key to some flat params in-place), that key leaks into the serration defs too, breaking the serration-specific validation rules.

**Prevention:** When adding new optional keys to param defs, do it in the `_SERRATION_PARAM_DEFS` append block explicitly, or switch to deep copies. Add a test that asserts the serration def set does not contain the flat-only variables (`fdD`, `pitchD`, etc.) after import.

---

### Pitfall 10: `build_param_cards()` Rebuilds the Entire Widget Tree on Every `on_pre_enter`

**What goes wrong:** `_rebuild_for_machine_type()` calls `container.clear_widgets()` and rebuilds hundreds of widgets from scratch every time the user navigates to the Parameters screen. On a Pi, this takes 300-800 ms and causes a visible freeze on tab switch. During an audit pass, if someone adds another card group or increases param count, this freeze becomes worse.

**Prevention:** Add a dirty flag to `BaseParametersScreen` that marks the machine type as "needs rebuild." Only call `build_param_cards()` when the machine type has actually changed since the last build, not on every `on_pre_enter`. Since machine type changes only happen at first-launch setup (in field use, the machine type never changes), the rebuild frequency in practice is zero after the first use.

---

### Pitfall 11: Removing `noqa: F401` Comments During Import Cleanup Breaks Re-exported Symbols

**What goes wrong:** `base.py` imports `theme` and `submit` with `# noqa: F401` comments explaining they are re-exported for KV bindings and test patching, respectively. An audit pass that strips "unused imports" removes these, which breaks `build_param_cards()` (uses `theme.bg_panel`) and the test suite that patches `dmccodegui.screens.base.submit`.

**Prevention:** Before any import cleanup pass, grep for all `noqa: F401` comments and verify each one: if the comment explains why the import is needed, leave it untouched. Only remove `noqa: F401` comments where the symbol is genuinely unused and the comment is wrong.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Hardware fingerprint design | MAC address instability on Pi with USB NICs (Pitfall 1) | Use CPU serial (`/proc/cpuinfo`) as primary ID; multi-component hash |
| License lockout recovery | No recovery path if fingerprint changes in the field | Build grace-period counter (N boots) into license file before hard lock |
| Windows code protection | PyArmor 8 + PyInstaller 6 incompatibility (Pitfall 2) | Obfuscate first, then bundle manually; or skip PyArmor on Windows |
| Pi Cython compilation | gclib ctypes path broken in compiled `.so` (Pitfall 3) | Exclude `controller.py` from Cython; keep it as plain `.py` |
| Pi Cython compilation | ABI tag mismatch on Python minor version change (Pitfall 4) | Compile on exact target machine; add startup ABI check |
| Pi kiosk + PyArmor expiry | No RTC, clock at epoch, PyArmor runtime error before app starts (Pitfall 8) | Disable time-based expiry for Pi builds; use `fake-hwclock` + `After=time-sync.target` |
| Codebase audit / dead code | Kivy KV class names and `_REGISTRY` string refs flagged as unused (Pitfall 5) | Allowlist `machine_config._REGISTRY` screen_classes before running vulture |
| Codebase audit / imports | `noqa: F401` comments stripped, removing re-exported symbols (Pitfall 11) | Review every `noqa: F401` comment before removing |
| Param page definitions | New var name missing from DMC `#PARAMS`, fails silently (Pitfall 6) | Add `logger.warning` to read loop; cross-check DMC file first |
| Param def expansion | Shallow copy in `_SERRATION_PARAM_DEFS` leaks new flat keys (Pitfall 9) | Use explicit deep copies or add mutation-isolation test |
| Licensing startup | Fingerprint subprocess stalls Kivy main thread (Pitfall 7) | Run validation before `App().run()`, not inside `App.build()` |

---

## Sources

- PyArmor PyInstaller 6.x incompatibility: [Issue #1714](https://github.com/dashingsoft/pyarmor/issues/1714), [Issue #1834](https://github.com/dashingsoft/pyarmor/issues/1834), [Issue #1824](https://github.com/dashingsoft/pyarmor/issues/1824)
- PyArmor NTP/clock expiry handling: [PyArmor FAQ](https://pyarmor.readthedocs.io/en/latest/questions.html), [Error Messages v8.2.8](https://pyarmor.readthedocs.io/en/v8.2.8/reference/errors.html)
- PyInstaller ctypes auto-detection limitations: [PyInstaller Feature Notes (stable)](https://pyinstaller.org/en/stable/feature-notes.html)
- PyInstaller + Kivy KV hidden imports: [Kivy PyInstaller hooks](https://kivy.org/doc/stable/api-kivy.tools.packaging.pyinstaller_hooks.html)
- Python dead code detection false positives (getattr, dynamic): [Vulture GitHub](https://github.com/jendrikseipp/vulture), [HN: dead code in Python is undecidable](https://news.ycombinator.com/item?id=46866141)
- Raspberry Pi CPU serial as stable hardware ID: [RPi Forums — unique ID](https://forums.raspberrypi.com/viewtopic.php?t=309508), [RPi Hardware ID gist](https://gist.github.com/amir-saniyan/854db35a789f07e61f48994b07d236df)
- MAC address instability for licensing: [LimeLM — why hardware locking](https://wyday.com/limelm/features/why/), [NetLicensing machine fingerprint](https://netlicensing.io/wiki/faq-how-to-generate-machine-fingerprint)
- Cython cross-compilation ARM64 .so naming: [Cython Issue #5009](https://github.com/cython/cython/issues/5009), [RPi Forums Cython](https://forums.raspberrypi.com/viewtopic.php?t=352039)
- Ed25519 license signing: [cryptography.io Ed25519 docs](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ed25519/)
- Direct codebase inspection: `src/dmccodegui/machine_config.py`, `src/dmccodegui/screens/base.py`, `src/dmccodegui/controller.py`, `src/dmccodegui/main.py` (this repo)
