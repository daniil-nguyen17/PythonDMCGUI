# Phase 23: Controller Communication Optimization - Research

**Researched:** 2026-04-13
**Domain:** gclib Python API, Galil DMC MG batching, connection flags, MG reader thread architecture
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Position Read Batching**
- Research QR (query record), DR (data record), and RP (report position) as alternatives to individual MG commands before committing to an approach
- Verify each alternative fits the disciplined single-channel architecture and won't bottleneck communication
- Batched MG (MG _TPA,_TPB,_TPC,_TPD) is the safe fallback if alternatives don't pan out
- Best-fit approach wins — researcher picks based on bandwidth/latency tradeoff analysis
- If batched MG parse fails, count as failure toward DISCONNECT_THRESHOLD (existing reconnect path)
- Always read 4 axes regardless of machine type (Serration ignores D=0) — poller stays generic
- Unify both poll.py (centralized poller) and RunScreen._tick_pos to use the same read method
- Poll rates stay as-is: 10 Hz centralized, 5 Hz RunScreen (1 Hz during grind)
- On position read failure, keep last known values (stale-but-real) until disconnect threshold fires

**Variable Batching**
- Batch hmiState, ctSesKni, ctStnKni, and _XQ into a single MG command
- Combine with position batch into a single mega-batch: MG _TPA,_TPB,_TPC,_TPD,hmiState,ctSesKni,ctStnKni,_XQ — one command reads all 8 values per tick (down from 8 separate commands)
- On variable batch failure, keep last known values (not zero defaults) to prevent state mismatch
- Apply same batching to RunScreen._tick_pos — both poller and RunScreen use identical batched reads
- Note: mega-batch approach applies if research confirms batched MG is the best method. If QR/DR/RP is chosen for positions, variables may still use batched MG separately

**MG State Messages**
- MG reader thread moves to app-wide scope (not just RunScreen) — both Run and AxesSetup need live state, Parameters reads some variables
- DMC program emits structured MG messages at state transitions — format is Claude's discretion
- MG state messages supplement polling, not replace it — MG gives sub-ms detection, poller confirms every tick as ground truth
- Structured state messages filtered out of RunScreen controller log panel — only freeform MG messages show in operator log

**Connection Hardening**
- Always use --direct flag for production connections (hard-coded, not configurable)
- --direct and explicit timeouts apply to BOTH handles (primary command handle and MG reader handle)
- reset_handle() (E-STOP recovery) also uses --direct and configured timeout
- Timeout values: let researcher determine safe values by checking gclib docs and controller response times
- Timeout errors treated same as other failures — count toward DISCONNECT_THRESHOLD (3 consecutive failures)
- Log connection flags on connect: "[CTRL] Connected to {address} --direct, timeout={ms}ms" for field debugging

### Claude's Discretion
- MG message format design (KEY:VALUE, tagged, etc.) — based on DMC MG command constraints
- Error handling granularity within the mega-batch parse
- MG reader thread architecture (standalone module vs extension of poll.py)
- GTimeout API usage patterns

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| COMM-01 | GRecord replaces individual MG position commands in poll loop (verify GRecord exists in wrapper first; check existing usage in screens before editing) | GRecord confirmed NOT in gclib Python wrapper — batched MG _TPA,_TPB,_TPC,_TPD is the correct approach |
| COMM-02 | Remaining user variables (hmiState, ctSesKni, ctStnKni) batched into single MG command | Single mega-batch MG command covers all 8 values; parse pattern documented |
| COMM-03 | DMC program emits structured MG messages at state transitions for sub-ms detection | MG command syntax in DMC documented; STATE:N format fits 8-char Galil convention; insertion points in existing DMC file mapped |
| COMM-04 | MG reader thread parses structured state messages and updates MachineState immediately | App-wide MgReader module pattern documented; Clock.schedule_once delivery to main thread |
| COMM-05 | Production connections use --direct flag to bypass gcaps middleware | --direct flag confirmed in GOpen address string; applies to both handles |
| COMM-06 | Explicit timeouts set on all gclib handles (primary: 1000ms, MG: 500ms) | GTimeout(ms) confirmed in installed gclib; --timeout N in GOpen address string; recommended values determined |
</phase_requirements>

---

## Summary

This phase optimizes the gclib command channel from 8 individual calls per poll tick to 1 (or 2 at most). The project memory already records that `GRecord()` is absent from the installed Python gclib wrapper — `python -c "import gclib; ..."` confirms the full method list: GCommand, GMessage, GTimeout, GOpen, GClose, GArrayUpload/Download, and utilities only. **No GRecord, no DR subscriber read, no QR, no RP method.** This settles COMM-01: the correct approach is a single batched MG command.

Batched MG is already in production for _tick_pos in FlatGrindRunScreen (`MG _TPA, _TPB, _TPC, _TPD` at run.py line 447) and for the variable batch (`MG hmiState, ctSesKni, ctStnKni` at line 465). The mega-batch merges these into one 8-value command. The centralized poller (poll.py) currently uses 7-8 individual calls and is the primary optimization target.

The MG reader thread exists in all three run screen classes (FlatGrindRunScreen, SerrationRunScreen, ConvexRunScreen) with duplicated code. Moving it to app-wide scope eliminates this duplication and serves AxesSetupScreen (which polls positions during jog moves). Connection hardening requires adding `--direct` and `--timeout 1000` to both GOpen calls in controller.py, and `--direct --timeout 500` to the MG reader GOpen, plus calling `GTimeout()` after open so the timeout applies to subsequent GMessage()/GCommand() calls within the session.

**Primary recommendation:** Implement as a single batched MG read shared by poll.py and all run screens, move MgReader to an app-wide module started in main.py, and harden both GOpen calls with `--direct --timeout N`.

---

## Standard Stack

### Core (confirmed installed)

| Component | Version/Detail | Purpose | Confirmed By |
|-----------|---------------|---------|-------------|
| `gclib.py()` | Installed (version from `GVersion()`) | gclib Python wrapper instance | `python -c "import gclib; g = gclib.py(); print(dir(g))"` |
| `GCommand(cmd)` | gclib method | Send a command string, get string response | Existing code throughout codebase |
| `GTimeout(ms)` | gclib method | Set socket timeout on a handle; applies to subsequent GCommand/GMessage | Confirmed in `gclib.py.GTimeout` docstring |
| `GMessage()` | gclib method | Block (up to GTimeout) for unsolicited MG message from --subscribe MG handle | Existing `_mg_reader_loop` in all three run screens |
| `GOpen(address)` | gclib method | Open a connection; address is a string of flags | Existing `controller.py connect()` and `reset_handle()` |
| `GClose()` | gclib method | Close a handle | Existing code |

### GOpen Address String Flags (confirmed from existing codebase + Galil docs)

| Flag | Effect | Used Where |
|------|--------|-----------|
| `--direct` | Bypasses gcaps middleware; connects directly to controller TCP port | To be added to controller.py connect() and reset_handle() |
| `--subscribe MG` | Configures handle for unsolicited MG message reception via GMessage() | Already in `_mg_reader_loop` across all run screens |
| `--timeout N` | Sets initial timeout in ms for GOpen; GTimeout() can override per-call | To be added to GOpen address strings |
| `-MG 0` | Suppresses unsolicited messages on the primary command handle | Already in existing GOpen calls (documented in project memory) |

**Confirmed missing from gclib Python wrapper (direct inspection):**
- `GRecord()` — not in installed gclib.py method list
- DR data record subscription reader — no Python API surface for it
- QR command (controller-side only; no Python wrapper method)
- RP command (DMC-side command; reads via GCommand as a text response only)

### Why Batched MG Wins Over Alternatives

| Alternative | Status | Verdict |
|------------|--------|---------|
| `GRecord()` | Not in gclib Python wrapper | Eliminated — confirmed absent from `dir(gclib.py())` |
| `--subscribe DR` in GOpen | Delivers binary data record; no Python decode API in gclib wrapper | Eliminated — no GDataRecord equivalent in Python binding |
| `QR` (query record, DMC command) | Returns binary block via GCommand(); decode requires model-specific struct | Eliminated — fragile, model-specific, no upside vs batched MG |
| `RP` (DMC report position command) | Returns 4-axis position as space-delimited text via GCommand() | **Viable alternative for positions only** — fewer values than TP but same format |
| Batched `MG _TPA,_TPB,_TPC,_TPD,hmiState,ctSesKni,ctStnKni,_XQ` | 1 GCommand call for 8 values; response is space-delimited floats | **Selected** — already proven in production (`_tick_pos` line 447), fits existing parse pattern |

**RP vs batched MG for position reads:**
`RP` returns encoder positions (4 values, space-delimited), which is equivalent to `MG _TPA,_TPB,_TPC,_TPD`. However, the mega-batch decision already collapses positions + variables into one MG call. RP cannot be combined with variable reads in one command. Use batched MG throughout.

---

## Architecture Patterns

### Current State (Before Phase 23)

**poll.py `_do_read()` — 7-8 separate GCommand calls per tick:**
```python
a = float(ctrl.cmd("MG _TPA").strip())      # call 1
b = float(ctrl.cmd("MG _TPB").strip())      # call 2
c = float(ctrl.cmd("MG _TPC").strip())      # call 3
d = float(ctrl.cmd("MG _TPD").strip())      # call 4
dmc_state = int(float(ctrl.cmd(f"MG {HMI_STATE_VAR}").strip()))  # call 5
ses_kni = int(float(ctrl.cmd(f"MG {CT_SES_KNI}").strip()))       # call 6
stn_kni = int(float(ctrl.cmd(f"MG {CT_STN_KNI}").strip()))       # call 7
xq_raw = int(float(ctrl.cmd("MG _XQ").strip()))                  # call 8
```

**run.py `_tick_pos()` — 2 batched calls (already partially optimized):**
```python
raw = ctrl.cmd("MG _TPA, _TPB, _TPC, _TPD").strip()  # call 1
raw2 = ctrl.cmd(f"MG {HMI_STATE_VAR}, {CT_SES_KNI}, {CT_STN_KNI}").strip()  # call 2
```

### Target State (After Phase 23)

**Shared read function — 1 GCommand call for all 8 values:**
```python
# Source: confirmed working pattern from flat_grind/run.py line 447
BATCH_CMD = (
    "MG _TPA,_TPB,_TPC,_TPD,"
    f"{HMI_STATE_VAR},{CT_SES_KNI},{CT_STN_KNI},_XQ"
)

def read_all_state(ctrl) -> tuple[float,float,float,float,int,int,int,bool] | None:
    """Single GCommand call returning all 8 controller values.

    Returns None on failure (caller keeps last known values).
    Response format: 8 space-delimited floats on one line.
    Example: " 1234.0000 -567.0000  890.0000    0.0000    1.0000   42.0000   77.0000    0.0000"
    """
    try:
        raw = ctrl.cmd(BATCH_CMD).strip()
        vals = [float(v) for v in raw.split()]
        if len(vals) < 8:
            return None
        a, b, c, d = vals[0], vals[1], vals[2], vals[3]
        dmc_state = int(vals[4])
        ses_kni = int(vals[5])
        stn_kni = int(vals[6])
        xq_raw = int(vals[7])
        program_running = (xq_raw >= 0)
        return (a, b, c, d, dmc_state, ses_kni, stn_kni, program_running)
    except Exception:
        return None
```

This function lives in `hmi/poll.py` (or a new `hmi/batch_read.py`). Both `ControllerPoller._do_read()` and all `RunScreen._tick_pos()` implementations call it.

### Stale-on-failure Pattern

```python
# In _do_read() / _tick_pos():
result = read_all_state(ctrl)
if result is None:
    self._fail_count += 1
    if self._fail_count >= DISCONNECT_THRESHOLD:
        Clock.schedule_once(self._on_disconnect)
    # Keep last known values — do NOT zero out state
    return
# success — unpack and proceed
self._fail_count = 0
a, b, c, d, dmc_state, ses_kni, stn_kni, program_running = result
```

**Why last-known instead of zero:** zeroing hmiState to 0 (STATE_UNINITIALIZED) could disable operator buttons mid-operation. Stale-but-real values are safe until DISCONNECT_THRESHOLD fires the proper disconnect path.

### Recommended Project Structure (new/modified files)

```
src/dmccodegui/
├── hmi/
│   ├── poll.py          # MODIFIED: _do_read() uses read_all_state(); imports MgReader
│   ├── dmc_vars.py      # MODIFIED: add BATCH_CMD constant; add STATE_MSG_PREFIX
│   └── mg_reader.py     # NEW: app-wide MgReader class (extracted from run.py)
├── controller.py         # MODIFIED: GOpen adds --direct --timeout flags; log on connect
├── main.py              # MODIFIED: start/stop MgReader lifecycle; pass to screens that need it
└── screens/
    ├── base.py          # MODIFIED: remove _mg_thread/_mg_stop_event references from cleanup()
    ├── flat_grind/run.py  # MODIFIED: remove _start/_stop/_mg_reader_loop; use app MgReader
    ├── serration/run.py   # MODIFIED: same
    └── convex/run.py      # MODIFIED: same; _tick_pos uses read_all_state()
```

### Pattern: App-Wide MgReader Module

```python
# hmi/mg_reader.py
import threading
import gclib
from kivy.clock import Clock

class MgReader:
    """App-wide MG unsolicited message reader.

    Owns a separate gclib handle opened with --subscribe MG --direct.
    Delivers messages to registered handlers on the Kivy main thread.
    State messages (STATE:N) are parsed and dispatched separately.
    """

    STATE_PREFIX = "STATE:"

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._log_handlers: list[callable] = []   # freeform message handlers
        self._state_handlers: list[callable] = [] # state transition handlers
        self._address: str = ""

    def start(self, address: str) -> None:
        """Start reader thread for address. address is IP only (flags added here)."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._address = address
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            args=(address, self._stop_event),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal thread to stop; join with timeout."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def add_log_handler(self, fn: callable) -> callable:
        """Register a handler for freeform MG messages. Returns unregister callable."""
        self._log_handlers.append(fn)
        def remove():
            try: self._log_handlers.remove(fn)
            except ValueError: pass
        return remove

    def add_state_handler(self, fn: callable) -> callable:
        """Register a handler for STATE:N messages. fn(state_int) called on main thread."""
        self._state_handlers.append(fn)
        def remove():
            try: self._state_handlers.remove(fn)
            except ValueError: pass
        return remove

    def _loop(self, address: str, stop_event: threading.Event) -> None:
        try:
            import gclib
        except ImportError:
            return
        handle = None
        try:
            handle = gclib.py()
            handle.GOpen(f"{address} --direct --subscribe MG")
            handle.GTimeout(500)  # 500ms timeout — loop checks stop_event regularly
        except Exception:
            if handle:
                try: handle.GClose()
                except Exception: pass
            return
        try:
            while not stop_event.is_set():
                try:
                    msg = handle.GMessage()
                    if msg:
                        for line in msg.strip().split('\n'):
                            line = line.strip()
                            if not line:
                                continue
                            if line.startswith(self.STATE_PREFIX):
                                self._dispatch_state(line)
                            else:
                                self._dispatch_log(line)
                except Exception:
                    pass  # timeout or read error — retry
        finally:
            try: handle.GClose()
            except Exception: pass

    def _dispatch_state(self, line: str) -> None:
        try:
            state_int = int(line[len(self.STATE_PREFIX):].strip())
        except (ValueError, IndexError):
            return
        for fn in list(self._state_handlers):
            Clock.schedule_once(lambda *_, s=state_int, f=fn: f(s))

    def _dispatch_log(self, line: str) -> None:
        for fn in list(self._log_handlers):
            Clock.schedule_once(lambda *_, t=line, f=fn: f(t))
```

### Pattern: Connection Hardening in controller.py

```python
# controller.py — connect() and reset_handle()
PRIMARY_FLAGS = "--direct --timeout 1000 -MG 0"

def connect(self, address: str) -> bool:
    # ...
    addr_with_flags = f"{address} {PRIMARY_FLAGS}"
    self._driver.GOpen(addr_with_flags)
    self._connected = True
    self._address = address  # store bare address for MG handle
    if self._logger:
        self._logger(f"[CTRL] Connected to {address} --direct, timeout=1000ms")
    return True

def reset_handle(self, address: Optional[str] = None) -> bool:
    addr = address or self._address
    if not addr:
        return False
    addr_with_flags = f"{addr} {PRIMARY_FLAGS}"
    try:
        self._driver.GClose()
        self._driver.GOpen(addr_with_flags)
        self._connected = True
        return True
    except Exception as e:
        log.error("reset_handle error: %s", e)
        self._connected = False
        return False
```

### Pattern: DMC Structured State Messages

The DMC `MG` command in a program emits the string over the controller's UDP unsolicited channel when using the `--subscribe MG` handle. Format constraint: string literals in DMC are quoted. Variables are embedded with commas.

```dmc
' In #MAIN, before entering IDLE:
hmiState = 1
MG "STATE:1"

' In #WtAtRt, before entering GRIND:
hmiState = 2
MG "STATE:2"

' In #SETUP, before entering SETUP mode:
hmiState = 3
MG "STATE:3"

' In #HOME, before entering HOMING:
hmiState = 4
MG "STATE:4"
```

**Format rationale:** `STATE:N` — colon-separated KEY:VALUE matches the existing `MG " A:", _TDA` pattern style, is distinct from all existing freeform messages ("BAT DAU MAI", "SYSTEM READY", etc.), parseable by `startswith("STATE:")`, and fits DMC string literal constraints.

**Why not `MG "STATE:", hmiState` (with variable):** DMC MG command with mixed string+variable would produce output like `STATE: 1.0000` with a space and float formatting — harder to parse reliably. Literal `"STATE:1"` is cleaner and the Python code already knows the mapping.

**Insertion points in 4 Axis Stainless grind.dmc:**

| Location | Line area | Action |
|----------|-----------|--------|
| `#MAIN` after `hmiState = 1` | Line 38-39 | Add `MG "STATE:1"` |
| `#WtAtRt` after `hmiState = 2` (before `JS #GRIND`) | Line 49 | Add `MG "STATE:2"` |
| `#WtAtRt` after `JS #GRIND` before `hmiState = 1` | Line 51 | Back to IDLE — handled by #MAIN return |
| `#WtAtRt` after `hmiState = 3` (before `JS #SETUP`) | Line 57 | Add `MG "STATE:3"` |
| `#HOME` entry | Line 244 area | Add `MG "STATE:4"` where hmiState=4 is set |

Note: The existing DMC file does NOT explicitly set hmiState=4 in a visible location — inspect `#HOME` to confirm and add both `hmiState = 4` and `MG "STATE:4"` there.

### Pattern: Filtering State Messages from Operator Log

In RunScreen's log handler (previously `_append_mg_log`), now only receives freeform messages because `MgReader._dispatch_log()` only calls log handlers for non-STATE lines. No additional filter needed — the separation happens in `MgReader._loop()`.

### Pattern: MgReader Lifecycle in main.py

```python
# main.py
# At module level or in build():
self._mg_reader = MgReader()

# After successful connect():
self._mg_reader.start(state.connected_address)

# In disconnect_and_refresh():
self._mg_reader.stop()

# In on_stop():
self._mg_reader.stop()
```

Screens register handlers in `on_pre_enter` and unregister in `on_leave`, same as MachineState listeners. The MgReader instance lives in the App — screens receive it via `app.mg_reader` or via injection at screen load time.

### Anti-Patterns to Avoid

- **Zeroing state on failure:** Using `dmc_state=0` / `ses_kni=0` on parse failure re-enables the mismatch risk the user explicitly flagged. Always keep last known values.
- **Per-screen MgReader instances:** Each screen opening its own --subscribe MG handle wastes a controller UDP slot and duplicates the thread. One app-wide instance serves all screens.
- **Calling GTimeout after GMessage in the same tick:** GTimeout configures the handle for the duration; call once after GOpen, not on every loop iteration.
- **Putting `--direct` in GOpen for the --subscribe MG handle without `--timeout`:** The MG handle needs its own timeout (500ms) so GMessage() returns regularly to check stop_event. Without it, stop() could block indefinitely.
- **Using semicolons in the mega-batch MG command:** The MG command takes comma-separated operands, not semicolons. `MG _TPA,_TPB` is correct. Semicolons would split into separate commands.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Batching reads | Custom framing protocol | Comma-separated `MG` operands | Already works in production (run.py line 447); no framing overhead |
| Timeout enforcement | Python `threading.Timer` wrapper | `GTimeout(ms)` in gclib | Built into gclib; applies to socket-level select(); no extra thread needed |
| Thread-safe state delivery | Lock + shared dict | `Clock.schedule_once` from thread to main thread | Kivy pattern already used everywhere; GIL-safe main-thread writes |
| Routing MG messages to multiple screens | Observer pattern with locks | `MgReader` handler list + `Clock.schedule_once` | Decoupled; screens register/unregister per lifecycle |

---

## Common Pitfalls

### Pitfall 1: MG batch response token count mismatch

**What goes wrong:** `MG _TPA,_TPB,_TPC,_TPD,hmiState,ctSesKni,ctStnKni,_XQ` returns 8 space-delimited floats under normal conditions. If any variable is undefined on the controller (e.g., hmiState not yet initialized because #PARAMS hasn't run), the controller may return `?` for that variable or return fewer tokens.

**Why it happens:** Controller starts in a pre-#PARAMS state where user variables have no value.

**How to avoid:** `if len(vals) < 8: return None` — count tokens before unpacking. The `None` return triggers the stale-value path.

**Warning signs:** Occasional IndexError in _do_read() during startup; connection succeeds but state reads look wrong.

### Pitfall 2: `--direct` changes reconnect behavior

**What goes wrong:** With `--direct`, gclib connects directly to the controller TCP port (502 by default for Ethernet). If gcaps was previously running and managing the connection, adding `--direct` in production for the first time may surface a "port already in use" or connection refused error.

**Why it happens:** gcaps holds the TCP connection when not using `--direct`. On a fresh boot without gcaps, `--direct` works correctly.

**How to avoid:** Log the full GOpen address string on connect. If connection fails, log the exception message so field debugging can identify gcaps conflicts. The `[CTRL] Connected to {address} --direct, timeout=1000ms` log line (locked decision) serves this purpose.

**Warning signs:** Connect fails with a "connection refused" or "already in use" error only after adding --direct.

### Pitfall 3: GTimeout on MG handle vs GCommand handle

**What goes wrong:** GTimeout(500) on the MG handle (used by `_mg_reader_loop`) sets the timeout for GMessage(). If the same timeout is applied to the primary command handle, short timeouts (500ms) may cause GCommand to time out during slow operations (array upload, parameter bulk-read).

**Why it happens:** GTimeout applies globally to the handle, not per-call.

**How to avoid:** Primary handle: `GTimeout(1000)` (1000ms). MG handle: `GTimeout(500)` (500ms). These differ intentionally — 1 second gives enough headroom for array operations; 500ms on the MG handle ensures the stop_event is checked twice per second.

**Determined safe values:**
- Primary (command) handle: `--timeout 1000` in GOpen + `GTimeout(1000)` after open = 1000ms. Matches COMM-06 spec.
- MG handle: `--timeout 500` in GOpen + `GTimeout(500)` after open = 500ms. Matches COMM-06 spec and existing `_mg_reader_loop` code.

### Pitfall 4: Existing test_poll.py expects 7 individual cmd() calls

**What goes wrong:** `test_poll.py` provides `cmd_return_values` as a list of 7 string responses (one per individual MG call). After refactoring to a single batched MG call, the test mocks break because they expect 7 calls but get 1.

**Why it happens:** Tests simulate controller responses at the `ctrl.cmd()` level. The batching refactor changes the call count and the response format (8 floats on one line vs 7 individual responses).

**How to avoid:** Rewrite test_poll.py mock responses to return one multi-value string: `" 100.0000  200.0000  300.0000  400.0000    1.0000   42.0000   77.0000    0.0000\r\n"` for a single cmd() call. All existing test assertions on state values remain valid — only the mock setup changes.

**Warning signs:** Tests pass individually but `ctrl.cmd.call_count` assertions fail; or tests get `StopIteration` when cmd() is called more times than mock responses provided.

### Pitfall 5: cleanup() in base.py references _mg_thread/_mg_stop_event

**What goes wrong:** `BaseRunScreen.cleanup()` (base.py line 186-189) references `self._mg_stop_event` and `self._mg_thread`. After moving MG reader to app scope, individual run screens no longer own these attributes. cleanup() will silently no-op (via `getattr` guard) but may log confusing warnings.

**Why it happens:** Phase 20 added these cleanup steps when MG reader was per-screen.

**How to avoid:** Remove or guard the MG reader cleanup block in BaseRunScreen.cleanup(). The app-wide MgReader is stopped in main.py `on_stop()` — screens only need to unregister their log/state handlers.

---

## Code Examples

### Mega-batch parse (production pattern)

```python
# Source: confirmed working from flat_grind/run.py line 447-469
# Extended to 8 values for the mega-batch

MEGA_BATCH_CMD = (
    f"MG _TPA,_TPB,_TPC,_TPD,"
    f"{HMI_STATE_VAR},{CT_SES_KNI},{CT_STN_KNI},_XQ"
)

def _do_batch_read(ctrl):
    """Returns (a,b,c,d,dmc_state,ses_kni,stn_kni,program_running) or None on failure."""
    try:
        raw = ctrl.cmd(MEGA_BATCH_CMD).strip()
        vals = [float(v) for v in raw.split()]
        if len(vals) < 8:
            return None
        return (
            vals[0], vals[1], vals[2], vals[3],
            int(vals[4]), int(vals[5]), int(vals[6]),
            int(vals[7]) >= 0,  # program_running: _XQ >= 0 means thread active
        )
    except Exception:
        return None
```

### GOpen with --direct and --timeout

```python
# Source: gclib.py GOpen documentation + project memory architecture
# Primary handle:
handle.GOpen(f"{address} --direct --timeout 1000 -MG 0")
handle.GTimeout(1000)  # Redundant but explicit; GTimeout overrides --timeout

# MG reader handle:
handle.GOpen(f"{address} --direct --timeout 500 --subscribe MG")
handle.GTimeout(500)   # 500ms — GMessage() returns regularly for stop_event check
```

### DMC STATE message emission

```dmc
' After setting hmiState, immediately emit structured message
hmiState = 2;              ' GRINDING
MG "STATE:2"
JS #GRIND
hmiState = 1;              ' back to IDLE
MG "STATE:1"
```

### MgReader state handler registration

```python
# In a screen's on_pre_enter:
from kivy.app import App
mg_reader = App.get_running_app().mg_reader
self._state_unsub_mg = mg_reader.add_state_handler(self._on_mg_state)
self._log_unsub_mg = mg_reader.add_log_handler(self._append_mg_log)

# In on_leave:
if self._state_unsub_mg:
    self._state_unsub_mg()
    self._state_unsub_mg = None
if self._log_unsub_mg:
    self._log_unsub_mg()
    self._log_unsub_mg = None
```

### Stale-on-failure in ControllerPoller._do_read()

```python
def _do_read(self) -> None:
    ctrl = self._controller
    state = self._state

    # ... reconnect logic unchanged ...

    result = _do_batch_read(ctrl)
    if result is None:
        self._fail_count += 1
        if self._fail_count >= DISCONNECT_THRESHOLD:
            Clock.schedule_once(self._on_disconnect)
        # No state update — last known values persist
        return

    self._fail_count = 0
    a, b, c, d, dmc_state, ses_kni, stn_kni, program_running = result
    Clock.schedule_once(
        lambda dt: self._apply(dmc_state, a, b, c, d, ses_kni, stn_kni, program_running)
    )
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 8 individual `MG var` calls per poll tick (poll.py) | 1 batched `MG` call for all 8 values | Phase 23 | 8x reduction in gclib round-trips at 10 Hz centralized poller |
| 2 batched `MG` calls per tick (run.py _tick_pos) | 1 batched `MG` call | Phase 23 | 2x reduction at 5 Hz run screen poller |
| Per-screen _mg_reader_loop (3 duplicated implementations) | App-wide MgReader in hmi/mg_reader.py | Phase 23 | Single thread, single handle, consistent lifecycle |
| GOpen with no explicit flags or timeout | GOpen with `--direct --timeout N` on both handles | Phase 23 | Bypasses gcaps; bounded failure detection |
| No structured state messages in DMC | `MG "STATE:N"` at each state transition | Phase 23 | Sub-ms state detection latency without polling |

**Deprecated patterns after this phase:**
- `_mg_thread`, `_mg_stop_event`, `_start_mg_reader()`, `_stop_mg_reader()`, `_mg_reader_loop()` in individual screen classes — replaced by `MgReader` registration/unregistration
- `BaseRunScreen.cleanup()` MG thread teardown block — replaced by app-level MgReader.stop()

---

## Open Questions

1. **DMC hmiState=4 assignment location in existing DMC file**
   - What we know: #HOME label starts at line 244; STATE_HOMING (4) exists in dmc_vars.py but `hmiState = 4` is not visible in the first 100 lines of the DMC file
   - What's unclear: Where exactly `hmiState = 4` is set (or if it's currently missing); whether `MG "STATE:4"` needs to be added alongside a new `hmiState = 4` assignment
   - Recommendation: Read the full #HOME section of the DMC file before planning the DMC edits task

2. **Serration and Convex DMC programs**
   - What we know: Serration and Convex use separate DMC programs; only the Flat Grind DMC file is in the repository
   - What's unclear: Whether Serration/Convex DMC programs need STATE: messages added; customer has not yet provided Serration DMC
   - Recommendation: Phase 23 DMC edits scope to the flat_grind DMC file only; add a TODO comment in Serration/Convex stub for when those programs arrive

3. **gcaps running on target Pi**
   - What we know: `--direct` bypasses gcaps; if gcaps is not running on the Pi, `--direct` is a no-op risk (safe); if gcaps IS running, `--direct` is essential
   - What's unclear: Whether gcaps is installed/enabled on the deployment Pi
   - Recommendation: `--direct` is always safe to add (it's a no-op if gcaps isn't running) and required if it is running. Hard-code it per the locked decision.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pytest.ini` or implicit (`tests/` directory discovered) |
| Quick run command | `python -m pytest tests/test_poll.py -x -q` |
| Full suite command | `python -m pytest tests/ -q --tb=short` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COMM-01 | Single cmd() call per poll tick for all 8 values | unit | `python -m pytest tests/test_poll.py::TestMegaBatchRead -x` | ❌ Wave 0 |
| COMM-01 | ctrl.cmd.call_count == 1 after _do_read() | unit | `python -m pytest tests/test_poll.py::TestMegaBatchCallCount -x` | ❌ Wave 0 |
| COMM-02 | Variables (hmiState, ctSesKni, ctStnKni) read in same cmd() as positions | unit | covered by COMM-01 test above | ❌ Wave 0 |
| COMM-02 | On batch parse failure, state retains last known values (not zeroed) | unit | `python -m pytest tests/test_poll.py::TestStaleOnFailure -x` | ❌ Wave 0 |
| COMM-03 | DMC emits STATE:N — tested via MgReader dispatch | unit | `python -m pytest tests/test_mg_reader.py::TestStateDispatch -x` | ❌ Wave 0 |
| COMM-04 | MgReader calls state handler with correct int on "STATE:2" | unit | `python -m pytest tests/test_mg_reader.py::TestStateHandlerCalledWithInt -x` | ❌ Wave 0 |
| COMM-04 | MgReader calls log handler for freeform message, not for STATE: line | unit | `python -m pytest tests/test_mg_reader.py::TestFilterStateFromLog -x` | ❌ Wave 0 |
| COMM-05 | GOpen called with "--direct" in address string | unit | `python -m pytest tests/test_controller.py::TestDirectFlag -x` | ❌ Wave 0 |
| COMM-06 | GTimeout called with 1000 on primary handle after GOpen | unit | `python -m pytest tests/test_controller.py::TestPrimaryTimeout -x` | ❌ Wave 0 |
| COMM-06 | GTimeout called with 500 on MG reader handle | unit | `python -m pytest tests/test_mg_reader.py::TestMgHandleTimeout -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_poll.py tests/test_mg_reader.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q --tb=short`
- **Phase gate:** Full suite green (6 existing failures in test_status_bar.py are pre-existing, not regressions) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_poll.py` — existing file needs new test classes for batched read; existing tests need mock responses updated to single-response format
- [ ] `tests/test_mg_reader.py` — new file; covers MgReader dispatch, state filtering, handler registration/unregistration
- [ ] `tests/test_controller.py` — new file (or extend existing); covers --direct flag in GOpen, GTimeout call verification

*(Existing test files: test_poll.py exists but all mock responses assume individual cmd() calls — must be updated in Wave 0 before implementation)*

---

## Sources

### Primary (HIGH confidence)

- `python -c "import gclib; g = gclib.py(); print(dir(g))"` — confirmed full method list; GRecord absent
- `python -c "import gclib; help(gclib.py)"` — confirmed GOpen, GTimeout, GMessage signatures
- `src/dmccodegui/screens/flat_grind/run.py` lines 447-469 — production batched MG pattern (2 calls, not 8)
- `src/dmccodegui/hmi/poll.py` lines 121-159 — current 8-call implementation (optimization target)
- `src/dmccodegui/screens/flat_grind/run.py` lines 1047-1092 — existing MgReader loop pattern
- `src/dmccodegui/controller.py` lines 108-175 — GOpen, reset_handle() (locations to add flags)
- `.claude/projects/.../memory/project_gclib_comms_architecture.md` — GRecord/DR confirmed not used

### Secondary (MEDIUM confidence)

- [Galil gclib connection docs](https://www.galil.com/sw/pub/all/doc/gclib/html/group__py__connection.html) — GTimeout documentation, --direct flag behavior
- [Galil thread safety docs](https://www.galil.com/sw/pub/all/doc/gclib/html/threading.html) — gcaps vs --direct explanation

### Tertiary (LOW confidence, not needed for planning)

- Various Galil command reference PDFs — QR/DR binary format details (not pursued; batched MG chosen)

---

## Metadata

**Confidence breakdown:**
- Standard stack (gclib methods): HIGH — confirmed by direct Python introspection of installed gclib
- Batched MG approach: HIGH — already in production use in `_tick_pos` (flat_grind/run.py line 447)
- `--direct` flag: MEDIUM — confirmed from project memory + gclib docs; exact gcaps interaction on Pi hardware requires field test
- Timeout values (1000ms primary, 500ms MG): HIGH — GTimeout API confirmed; values match COMM-06 spec and existing GTimeout(500) in `_mg_reader_loop`
- DMC STATE message format: HIGH — MG command behavior confirmed from existing DMC file; STATE:N parsing is straightforward string ops
- Architecture patterns: HIGH — based on reading actual source, not assumption

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (gclib API is stable; DMC behavior is hardware-verified)
