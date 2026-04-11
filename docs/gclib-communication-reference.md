# gclib Communication Reference

**Created:** 2026-04-11
**Purpose:** Reference guide for gclib API capabilities and optimization patterns for the DMC Grinding GUI HMI.
**Sources:** Galil gclib C API documentation — connection, unsolicited data, memory, controller, data records.

Use this document when evaluating controller communication improvements in future milestones.

---

## Table of Contents

1. [Current Communication Pattern](#current-communication-pattern)
2. [GRecord — Data Records](#grecord--data-records)
3. [Unsolicited Messages (GMessage)](#unsolicited-messages-gmessage)
4. [Connection Options](#connection-options)
5. [Memory and Array Functions](#memory-and-array-functions)
6. [Program Management](#program-management)
7. [Python gclib.py Wrapper Method Availability](#python-gclibpy-wrapper-method-availability)
8. [API Quick Reference](#api-quick-reference)

---

## Current Communication Pattern

The HMI polls at 10 Hz with **8 separate MG commands** per cycle:

| Command | Purpose | Round-trips |
|---------|---------|-------------|
| `MG _TPA` | Axis A position | 1 |
| `MG _TPB` | Axis B position | 1 |
| `MG _TPC` | Axis C position | 1 |
| `MG _TPD` | Axis D position | 1 |
| `MG hmiState` | Controller state | 1 |
| `MG ctSesKni` | Session knife count | 1 |
| `MG ctStnKni` | Stone knife count | 1 |
| `MG _XQ` | Thread running | 1 |
| **Total** | | **8 per cycle = 80/sec** |

A secondary gclib handle opened with `--subscribe MG` runs `GMessage()` in a background thread for unsolicited controller messages.

---

## GRecord -- Data Records

### What It Is

`GRecord()` returns a binary data record struct from the controller in a **single UDP packet**. The controller assembles this record continuously — reading it is a passive operation that doesn't interrupt the DMC program.

### Available Fields Per Axis (A, B, C, D)

| Field | Description | Replaces |
|-------|-------------|----------|
| `position` | Actual encoder position | `MG _TPx` |
| `reference_position` | Commanded position | — |
| `position_error` | Following error | — |
| `velocity` | Current velocity | — |
| `torque` | Current torque | — |
| `stop_code` | Why motor stopped (0=running, 1=commanded, etc.) | — |
| `motor_off` | Servo enabled/disabled | — |
| `moving` | Motion being profiled (true/false) | Useful for motion gate |
| `forward_limit` | Forward limit switch state | Replaces `@IN[]` polling |
| `reverse_limit` | Reverse limit switch state | Replaces `@IN[]` polling |
| `home_input` | Home switch state | — |
| `mode_of_motion` | JOG, PA, PR, etc. | — |
| `variable` | One user variable per axis (ZA, ZB, ZC, ZD) | Potential hmiState carrier |

### Available Global Fields

| Field | Description | Replaces |
|-------|-------------|----------|
| `thread_running[0..7]` | Per-thread execution status | `MG _XQ` |
| `input[index]` | Digital input state | `@IN[]` polling |
| `output[index]` | Digital output state | — |
| `error_code` | Controller error code | — |
| `sample` | Sample counter (incrementing) | — |

### What GRecord CANNOT Replace

User-defined DMC variables (`hmiState`, `ctSesKni`, `ctStnKni`) are **not** in the data record. These must still be read via `MG` commands.

**Workaround:** The data record has one `variable` slot per axis (via DMC `ZA`, `ZB`, `ZC`, `ZD` commands). If the DMC program sets `ZA=hmiState`, `ZB=ctSesKni`, `ZC=ctStnKni`, all data could come from a single GRecord. This requires DMC program modifications and hardware validation.

### Optimization Impact

| Approach | Round-trips per cycle | Reduction |
|----------|----------------------|-----------|
| Current (8x MG) | 8 | Baseline |
| GRecord + 1 batched MG | 2 | **75%** |
| GRecord + ZA/ZB/ZC workaround | 1 | **87.5%** |
| Batched MG only (no GRecord) | 3-4 | **50-62%** |

### Connection for Data Records

```python
# Dedicated data record handle (optional — can also use primary handle)
dr_handle = gclib.py()
dr_handle.GOpen("192.168.1.x --direct --subscribe DR")
dr_handle.GTimeout(200)
rec = dr_handle.GRecord()
```

The `--subscribe DR` flag opens a UDP channel for data records. The controller pushes records continuously; `GRecord()` reads the latest one.

### Push-Based Data Records (C API 2.4.1+)

The newer C API supports callback-based data record subscription:

```c
gclib_set_data_records(handle, 100);    // push every 100ms
gclib_subscribe_data_records(handle, callback, user_data);
```

**Not likely available in Python wrapper** — verify with `dir(gclib.py())`.

---

## Unsolicited Messages (GMessage)

### How It Works

The DMC program can emit messages using `MG "text"`. These arrive asynchronously on a handle opened with `--subscribe MG`. `GMessage()` blocks until a message arrives or times out.

### Available Functions

| C Function | Python Equivalent | Purpose |
|------------|-------------------|---------|
| `gclib_message(h, buf, len, timeout)` | `GMessage()` | Blocking read of next message |
| `gclib_subscribe_messages(h, callback, data)` | Probably not available | Callback-based (C API 2.4.1) |
| `gclib_set_interrupts(h, mask, axes, inputs)` | Probably not available | Configure hardware interrupts |
| `gclib_subscribe_interrupts(h, callback, data)` | Probably not available | Callback for interrupts |

### Use Cases for Our HMI

**State transition notifications:**
```dmc
' DMC program emits at each state boundary:
MG "hmi=2"   ; entering GRINDING
MG "hmi=3"   ; entering SETUP
MG "hmi=4"   ; entering HOMING
MG "hmi=1"   ; back to IDLE
```

```python
# Python MG reader parses immediately:
msg = handle.GMessage()
if msg.startswith("hmi="):
    state = int(msg.split("=")[1])
    machine_state.dmc_state = state  # sub-ms update
```

**Advantages over polling:**
- Sub-millisecond latency vs. up to 100ms polling interval
- Event-driven — no wasted reads when state hasn't changed
- Poll loop remains as safety-net backup

**Error and diagnostic messages:**
```dmc
MG "ERR:axis_fault A"
MG "DONE:grind_cycle"
MG "WARN:limit_approach B"
```

### Hardware Interrupts (C API only)

The C API supports interrupt subscriptions for:
- **Motion complete** on specific axes
- **Digital input transitions** (E-STOP, limit switches)

These fire without any DMC program `MG` statements. **Not available in Python wrapper** — requires C extension or ctypes bridge.

---

## Connection Options

### GOpen Address Flags

| Flag | Purpose | When to Use |
|------|---------|-------------|
| `--direct` | Bypass gcaps middleware | Production (HMI is sole communicator) |
| `-d` | Disable unsolicited data on this handle | Primary command handle |
| `--subscribe MG` | Receive MG print messages | Dedicated message reader handle |
| `--subscribe DR` | Receive data records | Dedicated data record handle |
| `--subscribe DR2` | Alternate DR subscription | Some firmware versions |

### Recommended Handle Architecture

```python
# Handle 1: Commands (send triggers, read user vars)
primary = gclib.py()
primary.GOpen("192.168.1.x --direct -d")
primary.GTimeout(1000)

# Handle 2: Unsolicited messages (state transitions, errors)
mg_handle = gclib.py()
mg_handle.GOpen("192.168.1.x --direct --subscribe MG")
mg_handle.GTimeout(500)

# Handle 3 (optional): Data records (positions, motion status)
dr_handle = gclib.py()
dr_handle.GOpen("192.168.1.x --direct --subscribe DR")
dr_handle.GTimeout(200)
```

The DMC-40x0 supports up to **8 concurrent Ethernet handles** (A-H). Three handles is well within limits.

### Other Connection Functions

| Function | Python | Purpose |
|----------|--------|---------|
| `gclib_addresses()` | `GAddresses()` | Discover controllers on network |
| `gclib_set_timeout(h, ms)` | `GTimeout(ms)` | Set command timeout |
| `gclib_close(h)` | `GClose()` | Close connection |
| `gclib_error(h)` | — | Get last error string |
| `gclib_address(h, buf, len)` | — | Get connected address |

### Timeout Recommendations

| Handle | Timeout | Rationale |
|--------|---------|-----------|
| Primary (commands) | 1000ms | Commands complete fast; 1s catches hangs without being aggressive |
| MG subscriber | 500ms | Already implemented — appropriate |
| DR subscriber | 200ms | Data records arrive continuously; 200ms detects stale quickly |

---

## Memory and Array Functions

### Array Transfer

| Function | Python | Purpose |
|----------|--------|---------|
| `gclib_array(h, name, buf, len, start, end)` | `GArrayUpload(name, start, end)` | Read array from controller |
| `gclib_set_array(h, name, buf, start, end)` | `GArrayDownload(name, data, start, end)` | Write array to controller |

**Already in use** in controller.py with chunked `GCommand` fallback.

### Capabilities

- **Bulk transfer:** Single operation for entire array — significantly faster than element-by-element `MG deltaC[i]` for large arrays
- **Partial read/write:** `GArrayDownload(name, data, start=5, end=10)` writes only indices 5-10
- **Auto-dimension:** `GArrayDownload` auto-creates array if it doesn't exist (explicit `DM` safer for production)
- **Binary protocol:** Optimized transfer internally — for 100+ element arrays, orders of magnitude faster than individual MG commands

### Use Cases

| Array | Current Usage | Optimization |
|-------|---------------|--------------|
| `deltaC[]` | Element-by-element | Bulk `GArrayDownload` for writes, `GArrayUpload` for reads |
| `startPt[]` | Individual reads | Could batch via `GArrayUpload("startPt")` |
| `restPt[]` | Individual reads | Could batch via `GArrayUpload("restPt")` |
| `bComp[]` (Serration) | TBD | Will need `GArrayDownload` for profile upload |

---

## Program Management

| Function | Python | Purpose |
|----------|--------|---------|
| `gclib_set_program(h, program, insert)` | `GProgramDownload(program, label)` | Write program to controller |
| `gclib_program(h, buf, len)` | `GProgramUpload()` | Read program from controller |
| `gclib_set_firmware(h, path)` | `GFirmwareDownload(path)` | Flash firmware (use with extreme caution) |

### Important Constraints

- **`GProgramDownload` fails if a program is executing.** Must `ST` all threads and verify `_XQ == -1` before download.
- The `label` parameter allows downloading to a specific label position (partial update).
- `GProgramUpload()` is useful for verification after download and for diagnostics.

---

## Python gclib.py Wrapper Method Availability

| Method | Available | Confidence | Notes |
|--------|-----------|------------|-------|
| `GOpen(address)` | Yes | Confirmed | In use |
| `GClose()` | Yes | Confirmed | In use |
| `GCommand(cmd)` | Yes | Confirmed | In use |
| `GMessage()` | Yes | Confirmed | In use in _mg_reader_loop |
| `GRecord()` | **Likely** | MEDIUM | Verify with `dir(gclib.py())` |
| `GTimeout(ms)` | Yes | Confirmed | In use |
| `GProgramDownload(prog)` | Likely | MEDIUM | Standard wrapper method |
| `GProgramUpload()` | Likely | MEDIUM | Standard wrapper method |
| `GArrayDownload(name, data)` | Yes | Confirmed | In use in controller.py |
| `GArrayUpload(name)` | Yes | Confirmed | In use in controller.py |
| `GAddresses()` | Yes | Confirmed | In use |
| `gclib_subscribe_*` | **No** | HIGH | C API 2.4.1 only — not in Python wrapper |
| `gclib_set_data_records` | **No** | HIGH | C API 2.4.1 only |
| `gclib_set_interrupts` | **No** | HIGH | C API 2.4.1 only |

**First step before implementing any GRecord changes:** Run `dir(gclib.py())` on the target machine.

---

## API Quick Reference

### Most Useful for Our HMI (by priority)

```python
# 1. Data record — single-packet position + status read
rec = handle.GRecord()
pos_a = rec['A']['position']
is_moving = rec['A']['moving']
thread_running = rec['thread_running_0']

# 2. Batched MG — multiple user vars in one command
vals = handle.GCommand("MG hmiState, ctSesKni, ctStnKni")

# 3. Unsolicited messages — event-driven state changes
msg = mg_handle.GMessage()  # blocks until message or timeout

# 4. Array bulk transfer — profile upload/download
data = handle.GArrayUpload("deltaC")
handle.GArrayDownload("deltaC", new_data)

# 5. Program management
handle.GProgramDownload(dmc_source)
current_program = handle.GProgramUpload()

# 6. Discovery
controllers = gclib.py.GAddresses()
```

### DMC Commands Still Needed via GCommand

| Command | Purpose | Cannot Replace With |
|---------|---------|---------------------|
| `MG hmiState` | User-defined state variable | GRecord (unless ZA workaround) |
| `MG ctSesKni` | Session knife count | GRecord (unless ZB workaround) |
| `MG ctStnKni` | Stone knife count | GRecord (unless ZC workaround) |
| `hmiGrnd=0` etc. | HMI trigger variables | N/A — write commands |
| `BV`, `BP`, `BN` | Save to flash | N/A — write commands |
| `ST`, `HX` | Stop/halt | N/A — control commands |
| `SH ABCD` | Servo enable | N/A — control commands |
| `XQ #AUTO` | Start program | N/A — control commands |

---

*Created: 2026-04-11*
*Sources: Galil gclib C API documentation (v2.3.1/2.4.1)*
*Location: docs/gclib-communication-reference.md*
*See also: .planning/research/GCLIB-COMMS.md (milestone-specific optimization plan)*
