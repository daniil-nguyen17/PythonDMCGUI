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
  - Hooks controller logging to popup alerts and the message ticker

- `src/dmccodegui/controller.py`
  - `GalilController` API with functions to interface w controller

- `src/dmccodegui/app_state.py`
  - `MachineState` dataclass with pub/sub and a rotating `messages` list for alerts

- `src/dmccodegui/utils/jobs.py`
  - Single worker thread + interval scheduler

- `src/dmccodegui/screens/`
  - This directory holds python logic for each screen

- `src/dmccodegui/ui/`
  - `base.kv`: root layout; custom toolbar; global message ticker row
  - `setup.kv`, `rest.kv`, `start.kv`, `arrays.kv`: per-screen layouts
  - `edges.kv`: KV-only subclasses `EdgePointBScreen`/`EdgePointCScreen` using different arrays
  - `theme.kv`: shared styles



## Tests
```bash
pytest -q
```
See `tests/test_controller.py` and `tests/test_arrays.py` for controller behavior and array round-trips using dummy drivers.

## Links
- DMC Code and Info: https://www.galil.com/learn/sample-dmc-code
- GCLib documentation: https://www.galil.com/sw/pub/all/doc/gclib/html/examples.html