# gclib Communication Optimization Research

**Researched:** 2026-04-11
**Purpose:** Identify gclib API improvements for cleaner, more predictable controller communication in production

## Current State

The HMI polls at 10 Hz with **8 separate MG commands** per cycle:
- `MG _TPA`, `MG _TPB`, `MG _TPC`, `MG _TPD` (4 axis positions)
- `MG hmiState` (controller state)
- `MG ctSesKni`, `MG ctStnKni` (knife counts)
- `MG _XQ` (thread running)

That's **80 round-trips/second** on the bus. Each is a TCP command/response parse cycle.

---

## Priority 1: GRecord (Data Records) — Biggest Win

**What:** `GRecord()` returns a binary data record struct in a **single UDP packet**. One call contains:
- All axis positions (replaces 4x `MG _TPx`)
- Thread running status (replaces `MG _XQ`)
- Per-axis: velocity, torque, stop code, motor off, moving flag, forward/reverse limits
- Digital input/output states
- Error code, sample counter

**Impact:** Replaces 5 of 8 MG commands with 1 GRecord call. Combined with batching the remaining 3 user variables into 1 MG, the poll drops from **8 round-trips to 2** — a **75% reduction** in bus traffic.

**What GRecord CANNOT replace:**
- `hmiState`, `ctSesKni`, `ctStnKni` — these are user-defined DMC variables, not in the data record struct

**Implementation pattern:**
```python
# BEFORE: 8 round-trips
a = float(ctrl.cmd("MG _TPA"))
b = float(ctrl.cmd("MG _TPB"))
# ... 6 more individual commands

# AFTER: 2 round-trips
rec = handle.GRecord()                    # 1 binary packet — positions + thread status
a = rec['A']['position']
b = rec['B']['position']
c = rec['C']['position']
d = rec['D']['position']
program_running = rec['thread_running_0']  # replaces MG _XQ

raw = ctrl.cmd("MG hmiState, ctSesKni, ctStnKni")  # 1 combined MG
vals = raw.strip().split()
```

**Bonus fields from GRecord useful for us:**
- `moving` per axis — instant motion detection without `MG _BG`
- `stop_code` per axis — why motor stopped (useful for diagnostics)
- `motor_off` — servo state
- `forward_limit` / `reverse_limit` — limit switch states without polling @IN[]
- `position_error` — following error for tuning

**Action required:** Verify `GRecord()` exists in our installed Python gclib wrapper: `dir(gclib.py())`

---

## Priority 2: Structured MG Messages for State Transitions

**What:** Have the DMC program emit `MG "hmi=X"` at state transition boundaries. The existing MG reader thread (`_mg_reader_loop` on the `--subscribe MG` handle) parses these immediately.

**Why:** Polling detects state changes with up to 100ms latency. MG messages arrive in sub-millisecond. For cycle start/stop, E-STOP acknowledgment, and error conditions, instant detection matters.

**Implementation:**
```dmc
' In DMC program, at each state transition:
MG "hmi=2"  ; entering GRINDING
MG "hmi=3"  ; entering SETUP
MG "hmi=4"  ; entering HOMING
MG "hmi=1"  ; back to IDLE
```

```python
# In _mg_reader_loop, parse structured messages:
msg = handle.GMessage()
if msg.startswith("hmi="):
    state = int(msg.split("=")[1])
    machine_state.dmc_state = state  # immediate update
```

**The poll loop still runs as safety-net** — if an MG message is missed, the next poll catches it within 100ms.

---

## Priority 3: `--direct` Connection Flag

**What:** Bypasses gcaps (Galil Communication Server middleware). Since our HMI is the sole communicator in production, this removes a middleware layer.

**Benefits:**
- One fewer process dependency at runtime
- Slightly lower latency
- No risk of gcaps service being stopped/crashed
- Simpler deployment on Pi

**When NOT to use:** During development if you need GDK or Galil tools connected simultaneously.

**Pattern:**
```python
# Production
primary.GOpen("192.168.1.x --direct -d")
mg_handle.GOpen("192.168.1.x --direct --subscribe MG")

# Development (remove --direct for GDK access)
primary.GOpen("192.168.1.x -d")
```

---

## Priority 4: Consolidate Remaining MG Commands

**Even without GRecord**, combining MG commands reduces round-trips:

```python
# BEFORE: 4 round-trips for positions
a = float(ctrl.cmd("MG _TPA"))
b = float(ctrl.cmd("MG _TPB"))
c = float(ctrl.cmd("MG _TPC"))
d = float(ctrl.cmd("MG _TPD"))

# AFTER: 1 round-trip
raw = ctrl.cmd("MG _TPA, _TPB, _TPC, _TPD")
a, b, c, d = [float(v) for v in raw.strip().split()]
```

This alone cuts poll round-trips from 8 to 4. Can be done immediately as a low-risk change.

---

## Priority 5: Timeout Discipline

Set explicit timeouts on all handles for predictable behavior:

| Handle | Timeout | Rationale |
|--------|---------|-----------|
| Primary (commands) | 1000ms | Commands complete fast; 1s catches hangs |
| MG subscriber | 500ms | Already done — appropriate |
| DR subscriber (if added) | 200ms | Data records arrive every 100ms |

---

## Useful Memory/Array Functions

**Already in use:** `GArrayUpload(name)` and `GArrayDownload(name, data)` in controller.py with chunked fallback.

**Additional capabilities:**
- **Partial array writes:** `GArrayDownload(name, data, start=5, end=10)` writes only indices 5-10 — useful for updating a subset of deltaC values
- **Auto-dimension:** `GArrayDownload` auto-creates array if it doesn't exist (but explicit `DM` is safer for production)

---

## Program Management Functions

| Function | Use Case |
|----------|----------|
| `GProgramDownload(program)` | Send DMC program to controller in one shot |
| `GProgramUpload()` | Read back program for verification or diagnostics |

**Production concern:** `GProgramDownload` fails if a program is executing. Must `ST` all threads and verify `_XQ == -1` before download.

---

## What NOT to Change

- **FIFO job thread serialization** — correct, keep it
- **`submit_urgent()` E-STOP path** — separate from polling, keep it
- **One-shot variable pattern** (default=1, send 0) — right approach, no gclib changes needed
- **BV only on explicit save** — correct

---

## Summary: Recommended Changes for v3.0

| Priority | Change | Impact | Risk |
|----------|--------|--------|------|
| 1 | GRecord for positions + thread status | 75% fewer round-trips | LOW — verify GRecord exists in wrapper |
| 2 | Structured MG for state transitions | Sub-ms state detection | LOW — additive, poll remains as safety-net |
| 3 | `--direct` in production | Remove middleware dependency | LOW — flag on GOpen |
| 4 | Batch remaining MG commands | 50% fewer round-trips (even without GRecord) | VERY LOW — string concat |
| 5 | Explicit timeouts on all handles | Predictable hang behavior | VERY LOW — one line per handle |

**Action item before any implementation:** Run `dir(gclib.py())` on target machine to confirm GRecord availability.

---
*Researched: 2026-04-11*
*Sources: Galil gclib C API documentation (connection, unsolicited, memory, controller, data records)*
