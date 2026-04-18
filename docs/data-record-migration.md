# Data Record Migration Plan

## Migration from MG Polling to DR (Data Record) Streaming

**Date:** 2026-04-17
**Author:** Danny + Claude
**Status:** Implemented — awaiting #ZALOOP on controller for full validation
**Source:** Galil support case #767944, recommendation from Esther Chou (Galil Applications Engineer)

### Implementation Status (2026-04-17)

| Phase | Status | Notes |
|-------|--------|-------|
| A: DMC-side (#ZALOOP) | Pending | Code provided, Danny to load via GDK |
| B: data_record.py | Done | Includes packet calibration fix (226 vs 252 bytes) |
| C: dmc_vars.py | Done | DR constants added |
| D: main.py wiring | Done | _start_dr / _stop_dr replacing _start_poller / _stop_poller |
| E: Run screen simplification | Done | All 3 screens (flat_grind, serration, convex) |
| F: base.py | Done | No-op poller helpers + STATE_IDLE on exit setup |
| G: Cleanup | Done | poll.py → _poll_legacy.py |
| H: Testing | Partial | Connected to controller, DR packets received, offset calibration verified |

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Current Architecture (What We Have)](#2-current-architecture-what-we-have)
3. [Target Architecture (What We Want)](#3-target-architecture-what-we-want)
4. [DMC Command Reference](#4-dmc-command-reference)
5. [Data Record Map (DMC-4000)](#5-data-record-map-dmc-4000)
6. [DMC-Side Changes](#6-dmc-side-changes)
7. [Python-Side Changes](#7-python-side-changes)
8. [Implementation Steps](#8-implementation-steps)
9. [Risk & Rollback](#9-risk--rollback)
10. [Open Questions](#10-open-questions)

---

## 1. Problem Statement

The HMI polls the controller at 10 Hz using `MG _TDA,_TDB,_TDC,_TDD,hmiState,ctSesKni,ctStnKni,_XQ`
over the **same TCP command socket** used for button presses. This causes race conditions:

- When the operator clicks Run (`hmiGrnd=0`), the command waits behind the current poll
  response. The button appears to do nothing.
- After a delay, the queued commands arrive at the controller and it starts moving "on its own."
- On the serration screen, bComp/cComp array reads (N+1 sequential MG commands per array)
  make this worse — the grind command can be blocked for seconds.

**Root cause confirmed by Galil support:** Manual MG-based polling shares the command channel
with button commands. The controller processes one command at a time per handle.

**Galil's recommendation:** Use the **Data Record (DR)** — the controller streams a binary status
packet over a **separate UDP socket** at a configurable rate. The TCP command channel is never
used for polling, so button commands execute instantly.

---

## 2. Current Architecture (What We Have)

### Communication Handles

```
Handle 1 — TCP (GOpen --direct --timeout 1000 -MG 0)
  Purpose: ALL commands — polling AND button presses
  Used by: ControllerPoller (10 Hz MG batch), JobThread (button cmds, array r/w)
  Problem: Single channel, commands queue behind polls

Handle 2 — TCP (GOpen --direct --subscribe MG --timeout 500)
  Purpose: Receive unsolicited MG messages (controller log)
  Used by: MgReader (app-wide) or per-screen _mg_reader_loop
  No problem: Read-only, separate handle
```

### Polling Flow (current)

```
Main Thread (Kivy Clock)                    Worker Thread (JobThread)
  |                                           |
  |-- Clock tick (10 Hz) ------------------>  |
  |   ControllerPoller._on_tick()             |-- jobs.submit(_do_read)
  |                                           |   ctrl.cmd("MG _TDA,_TDB,...,_XQ")
  |                                           |   ← waits for TCP response
  |                                           |   Clock.schedule_once(_apply)
  |                                           |
  |-- User clicks "Run" ------------------>   |
  |   on_start_grind()                        |-- jobs.submit_urgent(_fire)
  |                                           |   ctrl.cmd("hmiGrnd=0")
  |                                           |   ← BLOCKED if _do_read is mid-flight
```

### Files Involved

| File | Role | Changes needed |
|------|------|----------------|
| `hmi/poll.py` | `ControllerPoller` — 10 Hz MG batch poller | **Replace entirely** with DR listener |
| `hmi/dmc_vars.py` | `BATCH_CMD` constant, state constants | Remove `BATCH_CMD`, add DR constants |
| `hmi/mg_reader.py` | MG message subscriber (controller log) | **No change** — stays on its own handle |
| `controller.py` | `GalilController` — TCP command handle | **No change** — still used for commands |
| `utils/jobs.py` | `JobThread` — FIFO + urgent queue | **No change** — still used for commands |
| `app_state.py` | `MachineState` dataclass | **No change** — DR listener writes to it |
| `main.py` | `_start_poller()` / `_stop_poller()` | Rewire to DR listener lifecycle |
| `screens/flat_grind/run.py` | `_do_page_load_read()`, `_tick_pos()` | Remove poll logic, rely on DR |
| `screens/serration/run.py` | `_do_one_shot_read()`, `_tick_pos()` | Remove poll logic, rely on DR |
| `screens/convex/run.py` | Same pattern as flat grind | Remove poll logic, rely on DR |
| `screens/base.py` | `_stop_app_poller()` / `_start_app_poller()` | May simplify or remove |

### What Each Run Screen Does Today

All three run screens (flat_grind, serration, convex) follow the same pattern:

1. **on_pre_enter**: Stop the app-wide poller (`_stop_poller`), do a one-shot `read_all_state()`,
   start per-screen MG reader, read screen-specific data (deltaC, bComp, etc.)
2. **During grind**: Start 5 Hz `_tick_pos` poll via `Clock.schedule_interval`. Each tick submits
   a `read_all_state()` job to the worker thread.
3. **on_leave**: Stop `_tick_pos`, restart app-wide poller (`_start_poller`), stop MG reader.

The reason screens stop/start the app-wide poller is to free up the command channel. With DR,
this entire dance goes away — the DR stream is always on and never touches the command channel.

---

## 3. Target Architecture (What We Want)

### Communication Handles

```
Handle 1 — TCP (GOpen --direct --timeout 1000 -MG 0)
  Purpose: COMMANDS ONLY — button presses, array reads/writes, parameter changes
  Used by: JobThread
  Benefit: Zero contention — commands execute instantly

Handle 2 — TCP (GOpen --direct --subscribe MG --timeout 500)
  Purpose: Receive unsolicited MG messages (controller log)
  Used by: MgReader
  No change from current

Handle B — UDP (opened by controller via IH command)
  Purpose: Controller pushes data record packets to HMI
  Used by: New DataRecordListener thread (Python UDP socket)
  Direction: Controller → HMI (push, not request/response)
  Rate: Configurable (5-10 Hz for normal, can go higher during grind)
```

### Data Flow (target)

```
Controller                     Python HMI
  |                              |
  |-- DR packet (UDP) -------->  |  DataRecordListener thread
  |   every 100-200ms            |    struct.unpack binary packet
  |   (automatic, no request)    |    update MachineState
  |                              |    Clock.schedule_once(state.notify)
  |                              |
  |                              |  User clicks "Run"
  |<-- "hmiGrnd=0" (TCP) -----  |    JobThread sends immediately
  |   instant, no queue          |    zero contention
```

### What Goes Away

- `ControllerPoller` class (replaced by `DataRecordListener`)
- `BATCH_CMD` constant
- `read_all_state()` function
- Per-screen `_tick_pos` polling loops
- Per-screen `_do_one_shot_read()` / `_do_page_load_read()`
- The `_stop_poller()` / `_start_poller()` dance in run screen lifecycle
- `cancel_event` checks in bComp/cComp reads (nice to keep, but no longer critical)

### What Stays

- `JobThread` (submit/submit_urgent) for all user-initiated commands
- `MgReader` for controller log messages
- `GalilController` TCP handle for commands
- `MachineState` as the single source of truth for UI
- bComp/cComp array reads/writes over TCP (no change)
- All KV files and UI layout (no change)

---

## 4. DMC Command Reference

### Commands We Will Use

#### DR — Data Record Update Rate

```
DR n0, n1
```

| Arg | Min | Max | Default | Description |
|-----|-----|-----|---------|-------------|
| n0 | 2 | 30,000 | 0 | Update rate in **samples** between packets. n0=0 turns off. |
| n1 | 0 | 7 | CF port | Ethernet handle to output DR packet (0=A..7=H). Must be UDP. |

- DMC-4000 default sample period = 1ms, so `DR 200,1` = 200ms = 5 Hz, `DR 100,1` = 100ms = 10 Hz
- `DR 0` turns off data record output
- Issuing BN, BV, BX, DL, LS, LV, QD, QU, UL **pauses** DR output until complete
- Operands: `_DR0` = current rate, `_DR1` = current handle

**Example:**
```
IHB=192,168,0,10<2048>1   ; open UDP handle B to HMI
DR 200,1                   ; stream DR every 200ms on handle B
DR 0                       ; stop streaming
```

#### IH — Open IP Handle

```
IHm= n0,n1,n2,n3 <port> p
```

| Arg | Description |
|-----|-------------|
| m | Handle letter (A-H) |
| n0-n3 | IP address bytes of the **HMI** (the listener) |
| port | UDP port number the HMI will listen on |
| p | Connection type: 1=UDP, 2=TCP |

- The controller acts as **client**, sending packets TO the HMI's IP:port
- Handle must not conflict with existing handles (check with `TH` command)
- Close with `IHm=>-1` (close specific handle) or `IHT=>-1` (close all UDP)

**Example:**
```
IHB=192,168,0,10<2048>1   ; controller opens UDP handle B → HMI at 192.168.0.10:2048
TH                         ; verify handle status
IHB=>-1                    ; close handle B
```

#### ZA — User Data Record Variables

```
ZAm= n
```

| Arg | Description |
|-----|-------------|
| m | Axis letter (A-H) — one ZA slot per axis |
| n | Integer value, variable name, or operand. **Only 4 bytes (integer). No fractions.** |

- ZA assigns a **static value** to the data record slot — it does NOT auto-track a variable
- To stream a live variable, a DMC thread must continuously update ZA in a loop
- 4-axis controller (DMC-4040) = 4 ZA slots: ZAA, ZAB, ZAC, ZAD

**Our assignments:**

| Slot | Variable | Byte offset in DR | Purpose |
|------|----------|--------------------|---------|
| ZAA | hmiState | 114-117 | Machine state (IDLE/GRINDING/SETUP/HOMING) |
| ZAB | ctSesKni | 150-153 | Session knife count |
| ZAC | ctStnKni | 186-189 | Stone knife count |
| ZAD | startPtC | 222-225 | Stone position (C-axis start point) |

**DMC-side thread needed:**
```
#ZALOOP
ZAA=hmiState
ZAB=ctSesKni
ZAC=ctStnKni
ZAD=startPtC
WT 10          ; update every 10ms (faster than DR rate)
JP#ZALOOP
```

#### QZ — Return Data Record Information

```
QZ
```

Returns 4 comma-separated integers:
1. Number of axes
2. Bytes in general block
3. Bytes in coordinate plane block
4. Bytes in each axis block

**Example (DMC-4040):** `4, 52, 26, 36`

Total DR size = 4 (header) + 52 (general) + 26 (S-plane) + 26 (T-plane) + 4*36 (axes) = 252 bytes

Use QZ at startup to dynamically calculate byte offsets instead of hardcoding.

### Other Useful DMC Commands

#### TH — Tell Ethernet Handles

```
TH
```

Returns status of all 8 handles (A-H): IP address, port, connection type, state.
**Use at startup** to find which handles are free before opening IH.

#### WH — Which Handle

```
WH
```

Returns the handle letter that sent this command. Useful for knowing which handle our
GOpen connection is using, so we don't accidentally reuse it for IH.

#### QR — Query Data Record (one-shot)

```
QR ABCDEFGHST
```

Returns a single data record snapshot. Same binary format as DR stream.
**Useful for:** initial read on connect before DR streaming starts, or debugging.

#### BN — Burn Parameters to Non-Volatile Memory

```
BN
```

Saves all parameters (including ZA assignments) to NV memory so they persist across
power cycles. **Pauses DR** while executing.

#### BV — Burn Variables to Non-Volatile Memory

```
BV
```

Saves all variables to NV. We already use this in our shutdown sequence.
**Pauses DR** while executing.

---

## 5. Data Record Map (DMC-4000)

### Header (4 bytes)

| Offset | Type | Field |
|--------|------|-------|
| 0-1 | UW | Header flags (bit field: which blocks present) |
| 2-3 | UW | Total data record size in bytes (little-endian) |

### General Block (bytes 4-81)

| Offset | Type | Field | Our use |
|--------|------|-------|---------|
| 4-5 | UW | Sample number | Sequence check |
| 51 | UB | Thread status (bit 0 = thread 0 running) | `_XQ` equivalent |

### Per-Axis Blocks (36 bytes each)

Each axis block repeats at a fixed stride. For a 4-axis controller:

| Axis | Block start | Relative offset | Absolute offset |
|------|-------------|-----------------|-----------------|
| A | 82 | +0 | 82 |
| B | 118 | +0 | 118 |
| C | 154 | +0 | 154 |
| D | 190 | +0 | 190 |

Within each axis block (36 bytes):

| Relative | Type | Field | Our use |
|----------|------|-------|---------|
| +0 | UW | Axis status (bit field) | Move in progress, homing, etc. |
| +2 | UB | Axis switches | Limit switches, home input |
| +3 | UB | Stop code | Why axis stopped |
| +4 to +7 | SL | Reference position (`_RP`) | -- |
| +8 to +11 | SL | Motor position (`_TP`) | -- |
| +12 to +15 | SL | Position error (`_TE`) | -- |
| +16 to +19 | SL | **Auxiliary position (`_TD`)** | **We read this** |
| +20 to +23 | SL | Velocity (`_TV` * 64) | -- |
| +24 to +27 | SL | Torque | -- |
| +28 to +29 | SW/UW | Analog input | -- |
| +30 | UB | Hall input status | -- |
| +31 | UB | Reserved | -- |
| +32 to +35 | SL | **User variable (ZA)** | **hmiState / ctSesKni / ctStnKni / startPtC** |

### Byte Offsets We Need (absolute, for DMC-4040)

| Value | Absolute offset | Type | Python struct format |
|-------|-----------------|------|---------------------|
| Sample number | 4-5 | UW | `H` (unsigned short) |
| Thread status | 51 | UB | `B` (unsigned byte) |
| A auxiliary pos (`_TDA`) | 98-101 | SL | `i` (signed int) |
| A user var (ZAA = hmiState) | 114-117 | SL | `i` |
| B auxiliary pos (`_TDB`) | 134-137 | SL | `i` |
| B user var (ZAB = ctSesKni) | 150-153 | SL | `i` |
| C auxiliary pos (`_TDC`) | 170-173 | SL | `i` |
| C user var (ZAC = ctStnKni) | 186-189 | SL | `i` |
| D auxiliary pos (`_TDD`) | 206-209 | SL | `i` |
| D user var (ZAD = startPtC) | 222-225 | SL | `i` |

All values are **little-endian** (`<` prefix in struct).

### Axis Status Bit Field (bytes 82-83, 118-119, 154-155, 190-191)

| Bit | Meaning |
|-----|---------|
| 15 | Move in progress |
| 14 | PA or PR mode active |
| 13 | PA mode active |
| 12 | Find Edge (FE) in progress |
| 11 | Home (HM) in progress |
| 10 | 1st phase of HM complete |
| 9 | 2nd phase of HM complete |
| 8 | VM/LM mode active |
| 7 | Negative direction move |
| 6 | CM mode active |
| 5 | Motion is slewing |
| 4 | Stopping due to ST or limit |
| 3 | Making final deceleration |
| 2 | Latch armed |
| 1 | 3rd phase of HM in progress |
| 0 | Motor off |

**Useful for us:** Bit 15 (move in progress) gives per-axis motion status without needing hmiState.

---

## 6. DMC-Side Changes

### New thread: #ZALOOP

Add to the DMC program (runs on thread 3 — threads 0-2 are in use):

```
#ZALOOP
ZAA=hmiState
ZAB=ctSesKni
ZAC=ctStnKni
ZAD=startPtC
WT 10
JP#ZALOOP
```

Start it from `#AUTO` after `#PARAMS`:
```
XQ#ZALOOP,3    ; run on thread 3 (threads 0-2 are in use)
```

This thread copies our 4 variables into ZA slots every 10ms. The DR engine reads ZA
values when building each packet, so the data record always has fresh values.

### Handle setup

The IH and DR commands will be sent from the Python HMI at connect time (not burned
into the DMC program), because the HMI's IP address may change:

```
IHB=<hmi_ip_bytes><port>1    ; controller opens UDP handle B → HMI
DR 200,1                      ; stream data record at 5 Hz on handle B
```

At disconnect/shutdown:
```
DR 0         ; stop streaming
IHB=>-1      ; close handle B
```

### DMC Thread Allocation

| Thread | Current use | Notes |
|--------|------------|-------|
| 0 | Main program (#AUTO → #MAIN → #GRIND, etc.) | Core logic |
| 1 | Position update (writes aPos/bPos/cPos/dPos from _TDA/_TDB/_TDC/_TDD) | See note below |
| 2 | Speed update and autowear | |
| 3 | **#ZALOOP (new)** | Copies hmiState/ctSesKni/ctStnKni/startPtC to ZA slots |
| 4-7 | Free | |

**Note about thread 1:** Thread 1 currently updates aPos/bPos/cPos/dPos variables by
reading _TDA/_TDB/_TDC/_TDD. With DR streaming, the HMI reads _TD values directly from
the data record — it no longer needs the aPos/bPos/cPos/dPos intermediary variables.
Thread 1 could potentially be removed in a future cleanup, but it's harmless to keep
running (other parts of the DMC code might reference aPos/bPos/etc.).

### Considerations

- **BN/BV pauses DR:** Our shutdown sequence already calls BV. DR output will pause
  during BV but that's fine — we're shutting down anyway.
- **#ZALOOP must run before DR starts:** Start #ZALOOP in #AUTO, and have the HMI
  send IH/DR commands after connecting (which is after #AUTO has run).

---

## 7. Python-Side Changes

### New module: `hmi/data_record.py`

**DataRecordListener** — replaces ControllerPoller entirely.

```python
class DataRecordListener:
    """UDP listener for DMC-4000 data record streaming.

    Lifecycle:
        listener = DataRecordListener(state, port=2048)
        listener.start(controller, hmi_ip)   # sends IH + DR to controller
        listener.stop(controller)             # sends DR 0 + IH close

    Threading:
        - Background thread: blocks on UDP recv() with 4s timeout
        - Posts state updates to Kivy main thread via Clock.schedule_once
        - Never touches the TCP command channel for polling
        - Sends IH/DR setup commands via controller.cmd() only at start/stop/rate-change

    Adaptive rate:
        - 5 Hz (DR 200) during IDLE/SETUP/HOMING
        - 10 Hz (DR 100) during GRINDING
        - Rate change sent over TCP command channel (one-shot, instant)

    Disconnect detection:
        - 4-second recv() timeout → declare disconnect
        - Enter reconnect loop: try controller.connect() every 2s via jobs
        - On reconnect success: re-send IH + DR, resume recv loop
    """

    DR_RATE_NORMAL  = 200   # 5 Hz  (samples between packets)
    DR_RATE_GRIND   = 100   # 10 Hz
    DISCONNECT_TIMEOUT = 4.0  # seconds with no packet → disconnect

    def __init__(self, state: MachineState, port: int = 2048):
        self._state = state
        self._port = port
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._handle_letter: str = ""       # e.g., "B" — discovered from TH
        self._handle_index: int = 1         # 0=A, 1=B, ...
        self._current_rate: int = self.DR_RATE_NORMAL
        # Offsets calculated from QZ at start time
        self._offsets: dict[str, int] = {}

    def start(self, controller, hmi_ip: str) -> None:
        """Open UDP socket, send IH + DR commands, start listener thread."""
        # 1. Query QZ to calculate dynamic offsets
        # 2. Query TH to find first available handle
        # 3. Open UDP socket bound to 0.0.0.0:self._port
        # 4. Send IH command via controller.cmd()
        # 5. Send DR command via controller.cmd()
        # 6. Start listener thread

    def stop(self, controller) -> None:
        """Send DR 0 + close IH, stop listener thread, close socket."""

    def set_rate(self, controller, grinding: bool) -> None:
        """Switch DR rate based on machine state. Called from _apply."""
        new_rate = self.DR_RATE_GRIND if grinding else self.DR_RATE_NORMAL
        if new_rate != self._current_rate:
            controller.cmd(f"DR {new_rate},{self._handle_index}")
            self._current_rate = new_rate

    def _listener_loop(self) -> None:
        """Background thread: recv UDP packets, parse, update state.

        On recv timeout (4s): declare disconnect, enter reconnect loop.
        On reconnect: re-send IH + DR, resume recv loop.
        """
        while not self._stop_event.is_set():
            try:
                data = self._sock.recv(512)
                self._parse_and_apply(data)
            except socket.timeout:
                self._handle_disconnect()

    def _parse_and_apply(self, data: bytes) -> None:
        """Parse binary data record, post to main thread."""
        # struct.unpack at known offsets
        # Detect grinding state change → call set_rate()
        # Clock.schedule_once(lambda dt: self._apply_to_state(...))

    def _handle_disconnect(self) -> None:
        """Called on recv timeout. Set state.connected=False, attempt reconnect loop."""
        # 1. Clock.schedule_once → state.connected = False, state.notify()
        # 2. Close UDP socket
        # 3. Loop: try controller.connect() via jobs, sleep 2s, retry
        # 4. On success: re-open UDP socket, re-send IH + DR, return to recv loop
```

### Offset calculation from QZ

```python
def calculate_offsets(qz_response: str) -> dict:
    """Parse QZ response and return byte offsets for our fields.

    QZ returns: num_axes, general_bytes, coord_bytes, axis_bytes
    Example:    4, 52, 26, 36

    General block starts at byte 4 (after 4-byte header).
    S-plane block starts at 4 + general_bytes.
    T-plane block starts at 4 + general_bytes + coord_bytes.
    Axis A starts at 4 + general_bytes + 2*coord_bytes.
    Axis B starts at axis_A + axis_bytes.
    etc.
    """
    nums = [int(x.strip()) for x in qz_response.split(',')]
    n_axes, gen_bytes, coord_bytes, axis_bytes = nums

    header = 4
    axis_base = header + gen_bytes + 2 * coord_bytes  # skip S and T planes

    offsets = {}
    offsets['sample_num'] = 4          # always at byte 4-5
    offsets['thread_status'] = header + gen_bytes - 1  # last byte of general block

    for i, axis in enumerate(['A', 'B', 'C', 'D'][:n_axes]):
        base = axis_base + i * axis_bytes
        offsets[f'{axis}_status']   = base + 0   # UW, 2 bytes
        offsets[f'{axis}_stop']     = base + 3   # UB
        offsets[f'{axis}_ref_pos']  = base + 4   # SL, 4 bytes (_RP)
        offsets[f'{axis}_mot_pos']  = base + 8   # SL, 4 bytes (_TP)
        offsets[f'{axis}_pos_err']  = base + 12  # SL, 4 bytes (_TE)
        offsets[f'{axis}_aux_pos']  = base + 16  # SL, 4 bytes (_TD) ← we read this
        offsets[f'{axis}_velocity'] = base + 20  # SL, 4 bytes
        offsets[f'{axis}_torque']   = base + 24  # SL, 4 bytes
        offsets[f'{axis}_za']       = base + 32  # SL, 4 bytes (ZA user var)

    return offsets
```

### Changes to `main.py`

```python
# Replace:
#   from .hmi.poll import ControllerPoller
# With:
#   from .hmi.data_record import DataRecordListener

# _start_poller / _stop_poller → _start_dr / _stop_dr

def _start_dr(self) -> None:
    if self._dr_listener is None:
        self._dr_listener = DataRecordListener(self.state, port=2048)
    hmi_ip = get_hmi_ip(self.state.connected_address)
    self._dr_listener.start(self.controller, hmi_ip)

def _stop_dr(self) -> None:
    if self._dr_listener:
        self._dr_listener.stop(self.controller)
```

**Call sites to update (replace `_start_poller` → `_start_dr`, `_stop_poller` → `_stop_dr`):**

| Location in main.py | Current call | New call |
|---------------------|-------------|----------|
| After verify_connection (line ~239) | `_start_poller()` | `_start_dr()` |
| Auto-connect success (line ~256) | `_start_poller()` | `_start_dr()` |
| `_on_connect_from_setup` (line ~622) | `_start_poller()` | `_start_dr()` |
| `on_stop` app shutdown (line ~941) | `_stop_poller()` | `_stop_dr()` |
| `disconnect_and_refresh` (line ~980) | `_stop_poller()` | `_stop_dr()` |

**No changes needed for:**
- `e_stop()` — DR listener continues on UDP, unaffected by TCP handle reset
- `recover()` — sends XQ #AUTO on TCP, DR stream continues independently

### Changes to run screens

All three run screens (flat_grind, serration, convex) get simpler:

**Remove:**
- `_stop_poller()` / `_start_poller()` calls in `on_pre_enter` / `on_leave`
- `_do_one_shot_read()` / `_do_page_load_read()`
- `_tick_pos()` and `_start_pos_poll()` / `_stop_pos_poll()`
- The `_pos_busy` guard
- The `cancel_event` checks (in serration bcomp/ccomp)

**Keep:**
- `_on_state_change()` — now receives all updates from DR instead of from poller
- Screen-specific reads (bComp, cComp, deltaC arrays) — still need TCP commands
- MG reader for controller log — unchanged

The `_on_state_change()` handler already updates positions, knife counts, cycle state
from MachineState. The only difference is the data now comes from DR instead of MG polling.

---

## 8. Implementation Steps

### Phase A: DMC-side prep (manual, in GDK)

1. Check thread usage: `MG _XQ0` through `MG _XQ7` — find a free thread
2. Add `#ZALOOP` label to the DMC program
3. Add `XQ#ZALOOP,<thread>` to `#AUTO`
4. Download updated program, verify ZA values update: `MG _ZAA`, `MG _ZAB`, etc.
5. Test DR manually in GDK terminal:
   ```
   IHB=<hmi_ip><port>1
   DR 200,1
   ```
   Verify packets arrive on the HMI (use a Python test script with raw UDP socket)

### Phase B: Python — DataRecordListener

1. Create `hmi/data_record.py` with `DataRecordListener` class
2. Implement QZ parsing for dynamic offset calculation
3. Implement binary packet parsing with `struct.unpack`
4. Implement UDP socket lifecycle (bind, recv loop, close)
5. Implement IH/DR command sending at start/stop
6. Write standalone test script to verify parsing against live controller

### Phase C: Python — Wire into app

1. Replace `ControllerPoller` import in `main.py` with `DataRecordListener`
2. Replace `_start_poller()` / `_stop_poller()` with `_start_dr()` / `_stop_dr()`
3. Update `MachineState` writes in `DataRecordListener._apply()` to match current
   `ControllerPoller._apply()` signature
4. Verify all state subscribers still get notified correctly

### Phase D: Simplify run screens

1. Remove `_do_one_shot_read()` / `_do_page_load_read()` — DR is always streaming
2. Remove `_tick_pos()` / `_start_pos_poll()` / `_stop_pos_poll()`
3. Remove `_stop_poller()` / `_start_poller()` calls from `on_pre_enter` / `on_leave`
4. Keep `_on_state_change()` as the single entry point for UI updates
5. Keep screen-specific reads (bComp, cComp, deltaC) as TCP commands
6. The `startPtC` label now auto-updates from DR (via ZAD) — remove manual reads
   except after more/less stone (which needs immediate confirmation)

### Phase E: Cleanup

1. Remove `hmi/poll.py` (ControllerPoller)
2. Remove `read_all_state()` function
3. Remove `BATCH_CMD` from `dmc_vars.py`
4. Add DR-related constants to `dmc_vars.py` (port number, handle letter, DR rate)
5. Update `base.py` — `_stop_app_poller()` / `_start_app_poller()` may no longer be needed
6. Test all three machine types (flat grind, serration, convex)

---

## 9. Risk & Rollback

### Risks

| Risk | Mitigation |
|------|------------|
| UDP packet loss (no acknowledgment) | DR sends faster than we need; stale-on-loss is fine for display. Detect via sample number gaps. |
| Firewall blocks UDP | HMI and controller are on a closed network. Document port 2048 in setup instructions. |
| DR pauses during BV/BN | Only happens during shutdown. No impact on normal operation. |
| ZA thread uses controller resources | WT 10 (10ms loop) is negligible. Thread uses minimal CPU. |
| IP address changes | IH is sent at connect time, not burned. Python detects local IP dynamically. |

### Rollback Plan

The old `ControllerPoller` code can be kept in a `_poll_legacy.py` file during development.
If DR doesn't work, swap back to the poller by reverting the import in `main.py`.
The DMC-side `#ZALOOP` thread is harmless even if DR is not used — it just writes ZA values
that nobody reads.

---

## 10. Resolved Questions

### 1. Which thread for #ZALOOP?

**Answer: Thread 3.**

Thread allocation on the controller:
- Thread 0: Main program flow (#AUTO → #MAIN → #GRIND, etc.)
- Thread 1: Position update loop (writes aPos/bPos/cPos/dPos from _TDA/_TDB/_TDC/_TDD)
- Thread 2: Speed update and autowear thread
- Thread 3+: Free

Start #ZALOOP on thread 3: `XQ#ZALOOP,3`

### 2. HMI IP detection?

**Answer: Derive from controller's GOpen address.**

Use the controller IP (stored in `state.connected_address` after GOpen) to find the
local network interface on the same subnet. Fall back to manual entry in config, but
this should almost never be needed since HMI and controller are on a closed network.

```python
import socket

def get_hmi_ip(controller_ip: str) -> str:
    """Find local IP on the same subnet as the controller.

    Opens a UDP socket to the controller IP (no actual traffic sent),
    then reads the local address the OS chose for routing.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((controller_ip, 80))  # doesn't send anything
        return s.getsockname()[0]
    finally:
        s.close()
```

### 3. Which handle letter for DR?

**Answer: Check with TH at connect time, pick first AVAILABLE.**

Our GOpen uses one handle (likely A). MG reader uses another (likely B or C).
At connect time, send `TH` and parse the response to find the first handle marked
"AVAILABLE". Use that for IH/DR. Store the handle letter so we can close it on
shutdown.

### 4. DR rate?

**Answer: Adaptive — 5 Hz normal, 10 Hz during grind.**

- Normal (IDLE, SETUP, HOMING): `DR 200` = 5 Hz — sufficient for display updates
- Grinding: `DR 100` = 10 Hz — smoother position tracking

Switch rate when `hmiState` (from ZAA in the data record) changes to/from STATE_GRINDING.
Send `DR <new_rate>,<handle>` over the TCP command channel (one-shot, no contention).

### 5. Disconnect detection?

**Answer: 4-second timeout at 5 Hz.**

If no UDP packet received for 4 seconds (= 20 missed packets at 5 Hz), declare
disconnect. Use `socket.settimeout(4.0)` on the UDP socket — when `recv()` times
out, fire the disconnect path.

During grinding at 10 Hz, keep the same 4-second timeout (= 40 missed packets).
This is conservative enough to avoid false positives from a single dropped UDP packet.

### 6. Reconnect flow?

**Answer: DataRecordListener detects timeout, notifies main.py, main.py handles reconnect.**

**Current reconnect flow (ControllerPoller):**
1. `_do_read()` detects 3 consecutive read failures
2. `_on_disconnect()` fires on main thread: sets `state.connected = False`, calls
   `controller.disconnect()` via jobs
3. On next tick, `_do_read()` sees `ctrl.is_connected() == False`, tries `ctrl.connect()`
4. If connect succeeds, reads proceed and `_apply()` sets `state.connected = True`

**New reconnect flow (DataRecordListener):**
1. UDP `recv()` times out after 4 seconds → listener sets `state.connected = False`
   and calls `state.notify()` on main thread
2. Listener thread enters a reconnect polling loop:
   - Close old UDP socket
   - Try `controller.connect(state.connected_address)` via `jobs.submit()`
   - If connect succeeds, re-send IH + DR commands, open new UDP socket, resume recv loop
   - If connect fails, sleep 2 seconds, retry
3. On first successful DR packet after reconnect, `_apply()` sets `state.connected = True`

**Key difference:** The poller reconnects via the same jobs thread it polls on. The DR
listener reconnects by submitting jobs to the TCP command channel (which is now free
since no polling happens there). The listener thread itself just waits for UDP packets.

**Integration with main.py:**
- `disconnect_and_refresh()` — already calls `_stop_poller()`. Will call `_stop_dr()`
  instead, which sends DR 0 + IH close before stopping the listener.
- `_on_connect_from_setup()` — already calls `_start_poller()`. Will call `_start_dr()`
  instead, which queries QZ/TH, sends IH + DR, starts listener.
- `on_stop()` (app shutdown) — already calls `_stop_poller()`. Will call `_stop_dr()`.
- `e_stop()` — sends ST ABCD + reset_handle. DR listener continues receiving packets
  (UDP is independent). After handle reset, TCP commands resume. No DR change needed.
- `recover()` — sends XQ #AUTO. DR listener unaffected (UDP keeps streaming).

## 11. Open Questions (remaining)

None — all resolved. Handle B is the default for DR streaming (matches Esther's example).
Will verify with `TH` on the live controller during testing.
