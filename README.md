# Welcome to PythonDMCGUI
Custom Python + Kivy GUI to control a Galil machine using DMC.

## Requirements
- GCLib: https://www.galil.com/sw/pub/all/rn/gclib.html
- Conda (optional): https://www.anaconda.com/download/success
- Kivy: https://kivy.org/doc/stable/gettingstarted/installation.html
- Python 3.10+

## Setup
- conda env create -f environment.yml (run in repo root)
- conda activate dmc
- Install GCLib (x64) and ensure PATH is set

## Run
```bash
python -m dmccodegui.main
```

Environment:
- `DMC_ADDRESS=192.168.0.50` (example)

## Architecture (Developer Guide)

Layered structure keeps UI responsive and testable:

- `src/dmccodegui/main.py`
  - Loads KV files, builds root, injects `GalilController` and `MachineState` into all screens
  - Starts 10 Hz poll via background worker
  - Hooks controller logging to popup alerts and the message ticker

- `src/dmccodegui/controller.py`
  - `GalilController` API: `connect`, `disconnect`, `is_connected`, `cmd`, `read_status`, `jog`, `stop_jog`, `teach_point`, `read_array`, `write_array`, `list_addresses`
  - No Kivy imports; safe chunked array IO; TC1 error parsing; pluggable logger

- `src/dmccodegui/app_state.py`
  - `MachineState` dataclass with pub/sub and a rotating `messages` list for alerts

- `src/dmccodegui/utils/jobs.py`
  - Single worker thread + interval scheduler
  - `submit(fn, ...)` for one-shot tasks; `schedule(interval_s, fn)` for periodic jobs

- `src/dmccodegui/screens/`
  - `setup.py`: discovery, connect/disconnect, teach helpers with robust alerting
  - `arrays.py`: generic chunked array editor with validation; base for edge screens
  - `rest.py`, `start.py`: 4-axis teach screens with +/- step controls and manual entry
  - `__init__.py`: imports Python-defined screens so Kivy registers them

- `src/dmccodegui/ui/`
  - `base.kv`: root layout; custom toolbar; global message ticker row
  - `setup.kv`, `rest.kv`, `start.kv`, `arrays.kv`: per-screen layouts
  - `edges.kv`: KV-only subclasses `EdgePointBScreen`/`EdgePointCScreen` using different arrays
  - `theme.kv`: shared styles

## Alerts and Error Handling
- All controller calls run off the UI thread; screens guard with `controller.is_connected()` and use a local `_alert("No controller connected")` helper.
- The app’s `_log_message` surfaces messages as a short popup and in the ticker; `MachineState.messages` retains recent entries.

## Tests
```bash
pytest -q
```
See `tests/test_controller.py` and `tests/test_arrays.py` for controller behavior and array round-trips using dummy drivers.

## Links
- DMC Code and Info: https://www.galil.com/learn/sample-dmc-code
- GCLib documentation: https://www.galil.com/sw/pub/all/doc/gclib/html/examples.html