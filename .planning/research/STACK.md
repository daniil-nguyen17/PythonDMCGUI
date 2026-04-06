# Technology Stack

**Project:** DMC Grinding GUI — v2.0 HMI-Controller Integration
**Researched:** 2026-04-06
**Confidence:** HIGH for gclib command patterns (verified against official docs + existing codebase).
MEDIUM for thread-safety claim in gclib 2.4.x (release note language is ambiguous — see Threading section).

---

## Existing Stack (Unchanged — Do Not Re-Research)

| Technology | Pin | Role |
|------------|-----|------|
| Python | >=3.10 | Runtime |
| Kivy | >=2.2.0 | UI framework |
| gclib | system install (2.4.1 current) | Galil controller comms |
| matplotlib + kivy_matplotlib_widget | existing | Live A/B position plot |
| `threading` / `kivy.clock.Clock` | stdlib | Off-thread I/O, UI result delivery |
| KV language | Kivy built-in | Declarative layouts |

**No new libraries are required for v2.0.** Everything in this document is
about how to use the existing gclib library correctly for the new HMI integration work.

---

## New Stack Additions for v2.0

None. The v2.0 work is entirely gclib command patterns, DMC variable protocol, and threading discipline
within the already-established `jobs.submit` / `Clock.schedule_once` model.

---

## gclib Command Reference — HMI Integration Patterns

### Variable Read

```python
# Read a named DMC variable
raw = controller.cmd("MG varName")        # returns "  1.0000\r\n" — strip and float()
val = float(raw.strip())

# Read multiple variables in one round-trip (semicolon-separated MG)
raw = controller.cmd("MG hmiGrnd; MG hmiSetp; MG hmiMore")
# Response is space-separated: "  1.0000   1.0000   0.0000\r\n"
# Parse by splitting on whitespace after strip()

# Read an axis position (encoder counts)
raw = controller.cmd("MG _TPA")           # reference operand — prefixed with underscore
# Alternatives: _TPB, _TPC, _TPD (Tell Position)
#               _TDA, _TDB, _TDC, _TDD (Tell Dual [position + position error])
# Existing code uses _TP{axis} for run screen polling, _TD{axis} for setup screen

# Read program execution state (is DMC program running?)
raw = controller.cmd("MG _XQ")            # returns thread 0 execution state; 0 = idle, 1..n = label
# Returns 0 when no thread running, non-zero when #AUTO / #MAIN loop is active
```

**Confidence: HIGH** — `MG varName` is the standard DMC variable read pattern used throughout the
existing codebase (`run.py`, `axes_setup.py`, `parameters.py`) and confirmed by Galil docs.

### Variable Write (HMI One-Shot Trigger)

The DMC code uses a one-shot trigger pattern: HMI variables are declared with default=1.
The HMI sets them to 0 to trigger an action; the DMC program branch executes and resets to 1.

```python
# Trigger pattern — send var=0 to fire the one-shot
controller.cmd("hmiGrnd=0")    # Trigger Start Grind  → controller branches to #GRIND
controller.cmd("hmiSetp=0")    # Trigger Setup mode   → controller branches to #SETUP
controller.cmd("hmiMore=0")    # Trigger More Stone   → controller calls #MOREGRI
controller.cmd("hmiLess=0")    # Trigger Less Stone   → controller calls #LESSGRI
controller.cmd("hmiNewS=0")    # Trigger New Session  → controller calls #NEWSESS
controller.cmd("hmiHome=0")    # Trigger Home all     → controller calls #HOME
controller.cmd("hmiJog=0")     # Trigger Jog mode
controller.cmd("hmiCalc=0")    # Trigger #VARCALC recalculation

# Write a named scalar variable (parameter update)
controller.cmd("fdA=50")                  # Set feedrate A to 50
controller.cmd("knfThk=1.3")              # Set knife thickness
controller.cmd("fdA=50;fdB=40;fdCup=25")  # Batch writes — semicolon-separated in one command

# Burn to NV memory after writes that must survive power cycle
controller.cmd("BV")                      # CAUTION: BV takes ~2 seconds — always off-thread
```

**HMI variable naming constraint:** DMC variable names are max 8 characters (hard limit). The names
`hmiGrnd`, `hmiSetp`, `hmiMore`, `hmiLess`, `hmiNewS`, `hmiHome`, `hmiJog`, `hmiCalc` are all within
limit. Verify with `len("hmiGrnd") == 7` before finalizing. Do not exceed 8 chars.

**Confidence: HIGH** — `varName=value` assignment syntax is confirmed by DMC command reference and
used in `axes_setup.py` (`ctrl.cmd(write_cmd)` pattern) and `run.py` (`ctrl.cmd(f"bComp[{i}]={int(val)}")`).

### Array Read

```python
# Read a single array element
raw = controller.cmd("MG deltaC[5]")
val = float(raw.strip())

# Read all elements of a known-size array (existing GArrayUpload pattern)
values = controller.upload_array("deltaC", 0, 99)   # returns List[float], len=100

# For arrays declared with DM in #COMPED (aBuf, bBuf, deltaA, etc.)
# Use GArrayUpload when available (fast path), MG fallback otherwise
# controller.upload_array() handles both paths — already implemented
```

### Array Write

```python
# Write a single array element
controller.cmd("deltaC[5]=150.0")

# Write a full array (existing GArrayDownload pattern)
controller.download_array("deltaC", 0, values)  # values: List[float], 100 elements

# For the HMI integration pattern — write directly via cmd() for individual elements:
# This is what run.py already does for bComp
for i, val in enumerate(offsets_snapshot):
    ctrl.cmd(f"bComp[{i}]={int(val)}")
```

### Program / Subroutine Execution

```python
# Start a named subroutine (non-blocking — controller runs it, returns immediately)
controller.cmd("XQ #GRIND")    # Start grind cycle
controller.cmd("XQ #GOREST")   # Go to rest position
controller.cmd("XQ #GOSTR")    # Go to start position
controller.cmd("XQ #HOME")     # Home all axes
controller.cmd("XQ #NEWSESS")  # New session / stone change
controller.cmd("XQ #VARCALC")  # Recalculate derived values

# Halt program execution
controller.cmd("HX")           # Halt all threads (existing in run.py for pause)
controller.cmd("ST ABCD")      # Stop motion on specified axes
```

**IMPORTANT:** In the current DMC code (`4 Axis Stainless grind.dmc`), the main poll loop is `#WtAtRt`
running inside `#MAIN`. The HMI one-shot variable pattern (setting `hmiGrnd=0` etc.) is the correct
approach — it does NOT require `XQ #GRIND` from the HMI. The DMC program itself polls the variables
and calls `JS #GRIND` internally.

The `XQ #CYCLE` call in the current `run.py` (`on_start_pause_toggle`) is a placeholder and must be
replaced with the one-shot variable write (`hmiGrnd=0`) once the DMC code is updated.

### State Query — Controller-Side State Machine

```python
# Determine if the DMC program's main loop is running
raw = controller.cmd("MG _XQ")
is_running = float(raw.strip()) != 0

# Check if specific axes are in motion
raw = controller.cmd("MG _BGA")    # 1 = Axis A motion in progress, 0 = stopped
raw = controller.cmd("MG _BGS")    # 1 = vector (coordinated) motion in progress

# Read HMI variable state — poll these to confirm trigger was reset by DMC
raw = controller.cmd("MG hmiGrnd")   # Should return 1.0 when reset (idle), 0.0 briefly during trigger
```

---

## Threading Model — Critical Rules

### The Single-Handle Constraint

**gclib versions before 2.4.0:** A single `GCon` handle (one `gclib.py()` instance) is NOT thread-safe.
Concurrent `GCommand()` calls from multiple threads on the same handle will corrupt responses.

**gclib 2.4.0+ (released 2025, current is 2.4.1 as of March 2026):** Release notes state "gclib is now
thread safe." However, the threading documentation (which may not have been updated) still states that
"it is not safe to call GCommand() in multiple threads to the same physical connection." Treat the 2.4.x
thread-safety claim as LOW confidence until verified against the installed version's release notes.

**Safe approach regardless of gclib version:** Route ALL `GCommand` calls through the single `jobs.submit`
background thread. This is already the established pattern in the codebase. Do NOT change this pattern
to allow concurrent gclib calls until you can confirm the installed gclib version is 2.4.0+ and the
thread-safety applies to same-handle concurrent use.

**Confidence: MEDIUM** — the 2.4.0 "thread safe" claim is from the release notes fetched 2026-04-06.
The installed gclib may be an older version. Check with `pip show gclib` or by running
`gclib.py().GVersion()` on startup.

### Established Pattern (use exactly this)

```python
# In any Kivy screen — trigger controller action from button press
def on_some_button(self):
    if not self.controller or not self.controller.is_connected():
        return

    ctrl = self.controller  # capture ref before thread

    def _do_action():
        try:
            ctrl.cmd("hmiGrnd=0")               # one-shot trigger
        except Exception as e:
            Clock.schedule_once(lambda *_: self._alert(str(e)))

    jobs.submit(_do_action)


# In any Kivy screen — poll state at a fixed Hz
def _on_poll_tick(self, dt):
    if not self.controller or not self.controller.is_connected():
        return
    jobs.submit(self._do_poll)

def _do_poll(self):
    try:
        raw = self.controller.cmd("MG _TPA")
        pos_a = float(raw.strip())
        Clock.schedule_once(lambda *_: self._apply_result(pos_a))
    except Exception:
        pass   # swallow poll errors silently; disconnect detection handled elsewhere
```

### Polling Frequencies

| Screen | Current Rate | Recommended Rate | Rationale |
|--------|-------------|-----------------|-----------|
| RunScreen position poll | 10 Hz | **10 Hz** | Current rate is correct. Submits one `_do_poll` job per tick. Jobs queue naturally absorbs latency spikes — if a poll takes > 100ms, the next tick skips it (queue has backlog). |
| RunScreen plot redraw | 5 Hz | **5 Hz** | Correct. Decoupled from poll clock to protect E-STOP button latency. |
| AxesSetup position poll | 3 Hz | **3 Hz** | Correct for setup — operator watching position, not time-critical. |
| State sync (HMI variables) | not yet implemented | **5 Hz** | Poll `_XQ`, `hmiGrnd` to detect controller state changes. Separate poll from position poll — simpler to manage independently. |
| Parameters screen | on-demand | **on-demand** | Read on enter, write on apply. No continuous poll needed. |

**10 Hz poll with 4 axes:** Each poll submits 4 `MG _TP{axis}` calls. At 10 Hz that is 40 GCommand
round-trips per second. Typical gclib round-trip on Ethernet is 1-3ms, so 40 calls = ~40-120ms per
second of controller bandwidth. This is safe for the Galil DMC. Do not poll faster than 10 Hz unless
profiling shows the controller is not bottlenecked.

**BV (burn NV) must never be in the poll loop.** BV takes ~2 seconds. Only call it on explicit user
actions (teach, apply parameters). This is already correct in the existing code.

---

## HMI Variable Protocol — DMC Code Side

The DMC program must be modified to add HMI variable checks as OR conditions alongside physical `@IN[]`
checks. Declared once in `#PARAMS`:

```dmc
' In #PARAMS — declare HMI trigger variables with default=1 (inactive state)
hmiGrnd = 1     ' Start Grind     (send 0 from HMI to trigger)
hmiSetp = 1     ' Enter Setup mode
hmiMore = 1     ' More Stone (compensation)
hmiLess = 1     ' Less Stone (compensation)
hmiNewS = 1     ' New Session (stone change)
hmiHome = 1     ' Home all axes
```

```dmc
' In #WtAtRt polling loop — add HMI OR conditions
IF (@IN[29] = 0) | (hmiGrnd = 0)   ' GO GRIND button OR HMI trigger
  hmiGrnd = 1                       ' Reset immediately after branch
  SB 1
  JS #GRIND
  JP #WtAtRt
ENDIF
```

**Variable naming:** `hmiGrnd` = 7 chars, `hmiSetp` = 7 chars, `hmiMore` = 7 chars,
`hmiLess` = 7 chars, `hmiNewS` = 7 chars, `hmiHome` = 7 chars. All within the 8-char DMC limit.

The existing `DM hmiBtn[40]` array in `#PARAMS` can be repurposed or replaced by the individual
scalar variables above. Individual scalars are simpler to read and write from Python than array elements
and make the DMC code easier to read.

---

## State Synchronization Model

The recommended pattern for HMI state sync is **polling DMC variables**, not interrupts.

**Why polling, not GInterrupt/GMessage:**
- GMessage requires subscribing with `GOpen('address --subscribe MG')` — changes the connection string
  used at startup, requires architectural change to the existing `GOpen` call.
- GInterrupt requires EI/UI commands in the DMC program — adds DMC complexity.
- Polling `_XQ` and named state variables at 5 Hz is sufficient for an industrial HMI that is
  inherently human-speed. E-STOP is not a state-sync concern — it is a hardware interlock.
- The existing codebase is poll-only; adding interrupt handling would require a second connection
  handle and a dedicated GMessage reader thread, which adds complexity for marginal benefit.

**State variables to poll:**

```python
# Recommended state sync poll (5 Hz, background thread)
state_vars = "MG _XQ; MG hmiGrnd; MG _BGA; MG _BGB"
raw = controller.cmd(state_vars)
# Parse space-separated floats
vals = [float(v) for v in raw.strip().split()]
xq, hmi_grnd, bg_a, bg_b = vals
```

**Controller state machine states:**
- `_XQ = 0` — no program running (idle, after HX or program error)
- `_XQ != 0` — program running (in `#MAIN` / `#WtAtRt` loop)
- `_BGA = 1` or `_BGB = 1` — motion in progress (don't re-trigger)
- `hmiGrnd = 0` — trigger is pending (briefly, normally resets to 1)

**HMI should reflect:** connected, idle, grinding, setup, at-rest, at-start, error states.
These are inferred from the combination of `_XQ`, `_BGA/_BGB`, and optional named state variables.
The DMC program can set a named variable like `machSt` (machine state) if explicit state values
are needed:

```dmc
machSt = 1    ' in #MAIN (idle)
machSt = 2    ' grinding active
machSt = 3    ' setup mode
machSt = 4    ' going to rest
machSt = 5    ' going to start
```

---

## Error Handling Pattern

```python
def _do_command(self, cmd_str: str) -> None:
    """Background thread: send a command; surface TC1 error to UI on failure."""
    try:
        self.controller.cmd(cmd_str)
    except RuntimeError as e:
        # controller.cmd() already calls TC1 and embeds the error text in the exception
        Clock.schedule_once(lambda *_: self._alert(str(e)))
```

The existing `GalilController.cmd()` already calls `TC1` on failure and includes the error text in
the `RuntimeError` message. Do not duplicate TC1 calls in screen code.

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Any new communication library (pyserial, modbus, etc.) | gclib is the Galil API; alternatives are unsupported for DMC | gclib only |
| GInterrupt-based state sync | Requires `--subscribe EI` in GOpen address string, a dedicated reader thread, DMC EI/UI command changes | Poll `_XQ` + named state vars at 5 Hz |
| GMessage-based unsolicited message reading | Same architectural cost as GInterrupt; messages are debug strings not structured state | Structured variable polling |
| gcaps (Galil Controller Asynchronous Proxy Server) | Adds an external service dependency for a single-client embedded system | Single handle with serialized access via `jobs` queue |
| Second `gclib.py()` handle for a "fast" command path | Two handles to the same controller = two TCP connections + coordination overhead + concurrency risk | Single handle, all calls via `jobs.submit` |
| Polling faster than 10 Hz from the HMI | 40 GCommand calls/sec already saturates practical Ethernet bandwidth for a 4-axis status poll; no user benefit above 10 Hz | 10 Hz for position, 5 Hz for state |
| `GMotionComplete()` blocking calls | Blocks the background thread for the full motion duration; the Kivy clock tick is unaffected but the jobs queue cannot service other requests during the block | Poll `_BGA/_BGB` until zero in a loop with `time.sleep(0.05)`, or use `AM` in the DMC program |
| Updating Kivy widgets directly from the background thread | Kivy's canvas drawing is not thread-safe; widget property assignments may work but are not guaranteed | `Clock.schedule_once(lambda *_: self._apply_ui(...))` always |

---

## Installation

No changes required. gclib is already installed as a system package.

```bash
# Verify installed gclib version (important for thread-safety question)
python -c "import gclib; g = gclib.py(); print(g.GVersion())"
# Expected output: version string like "gclib v2.4.1"
```

If the installed version is below 2.4.0, the single-connection-handle serialization via `jobs` queue
is mandatory. If 2.4.0+, per the release notes it may be safe to submit gclib calls from parallel
background threads — but the single-queue model already works and should not be changed without
profiling evidence of a bottleneck.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Variable trigger mechanism | One-shot scalar (default=1, send 0) | XQ #label from HMI | `XQ` starts a new thread on the controller; if #MAIN is already polling, this can conflict with the existing loop. One-shot variables let the DMC loop handle routing — simpler and matches the existing physical button pattern. |
| State detection | Poll `_XQ` + named vars at 5 Hz | GInterrupt subscription | Interrupt requires architectural changes to GOpen call and a dedicated reader thread. Too much complexity for a single-machine system. |
| Multi-variable reads | Semicolon-batched single `MG` command | Separate `cmd()` call per variable | One round-trip vs N round-trips. At 10 Hz, batching 4-axis position read saves ~3 round-trips per tick = ~30-90ms saved per second. |
| NV burn | `BV` on explicit user action | `BV` after every write | BV takes ~2 seconds. Calling it after every parameter change during a rapid-fire session would make the UI feel frozen. Batch at end of session. |

---

## Version Compatibility

| Library | Version Requirement | Notes |
|---------|---------------------|-------|
| gclib Python wrapper | system install (2.4.1 current) | Not a pip package; installed by Galil installer. `GArrayUpload`/`GArrayDownload` are available in all versions supported by the codebase. |
| Python | 3.10+ | Already pinned in pyproject.toml. No change. |
| Kivy | 2.2+ | Already pinned. `Clock.schedule_once` used for all UI updates from background thread. No change. |

---

## Sources

- Official gclib Python class reference: https://www.galil.com/sw/pub/all/doc/gclib/html/classgclib_1_1py.html — confirmed GCommand, GArrayUpload, GArrayDownload, GMessage, GInterrupt signatures (HIGH confidence)
- gclib thread safety documentation: https://accserv.lepp.cornell.edu/svn/packages/gclib/doc/html/threading_8md_source.html — single-handle constraint confirmed (HIGH confidence)
- gclib release notes: https://www.galil.com/sw/pub/all/rn/gclib.html — version 2.4.1 current as of March 2026, "thread safe" added in 2.4.0 (MEDIUM confidence — claim language is ambiguous regarding same-handle use)
- Galil forums variable read example: https://www.galil.com/forums/host-programming/how-read-variable-python — `MG _TTA` pattern confirmed (HIGH confidence)
- DMC command reference (Keck/DEIMOS copy): https://www2.keck.hawaii.edu/inst/deimos/com40x0.pdf — variable assignment, BV, XQ, HX, MG syntax (HIGH confidence)
- Existing codebase: `controller.py`, `run.py`, `axes_setup.py`, `parameters.py` — patterns confirmed working in v1.0 (HIGH confidence)
- DMC program: `4 Axis Stainless grind.dmc` — state machine structure, variable names, array declarations, HMI button array (HIGH confidence)

---
*Stack research for: DMC Grinding GUI v2.0 HMI-Controller Integration*
*Researched: 2026-04-06*
