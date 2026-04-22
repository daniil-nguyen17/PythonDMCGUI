---
phase: 26-pi-os-preparation-and-install-script
plan: 01
subsystem: data-dir / deploy
tags: [pi, linux, data-dir, deploy, tdd]
dependency_graph:
  requires: []
  provides: [linux-data-dir, deploy-pi-skeleton]
  affects: [src/dmccodegui/main.py, tests/test_data_dir.py]
tech_stack:
  added: []
  patterns: [TDD red-green, minimal PNG generation via stdlib struct/zlib]
key_files:
  created:
    - deploy/pi/requirements-pi.txt
    - deploy/pi/binh-an-hmi.desktop
    - deploy/pi/binh-an-hmi.png
    - deploy/pi/vendor/README.md
  modified:
    - src/dmccodegui/main.py
    - tests/test_data_dir.py
decisions:
  - "_get_data_dir() Linux branch uses elif sys.platform == 'linux' between frozen and else-dev branches — preserves all existing Windows behavior"
  - "gclib 1.0.1 py3-none-any wheel used — pure-Python ctypes wrapper, architecture-neutral; native .so provided by apt"
  - "binh-an-hmi.png is a minimal 1x1 PNG generated via Python stdlib — no external tooling needed, real icon deferred"
  - "vendor/ README documents .deb placement rather than committing the binary"
metrics:
  duration_seconds: 103
  completed_date: "2026-04-22"
  tasks_completed: 2
  files_created: 4
  files_modified: 2
---

# Phase 26 Plan 01: Pi OS Preparation and Code Changes Summary

**One-liner:** Linux data-dir branch (`~/.binh-an-hmi/`) added to `_get_data_dir()` with TDD coverage, plus `deploy/pi/` skeleton (requirements, .desktop entry, placeholder icon, vendor README).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add _get_data_dir() Linux branch and test | 9254d46 | src/dmccodegui/main.py, tests/test_data_dir.py |
| 2 | Create deploy/pi/ skeleton files | 2bcfe84 | deploy/pi/requirements-pi.txt, binh-an-hmi.desktop, binh-an-hmi.png, vendor/README.md |

## What Was Built

### Task 1: _get_data_dir() Linux branch

Added `elif sys.platform == 'linux':` between the frozen check and the Windows dev else-branch in `_get_data_dir()`. The Linux path returns `~/.binh-an-hmi/` and calls `os.makedirs(..., exist_ok=True)`.

Updated docstring to document all three paths:
- Frozen (PyInstaller onedir, Windows): `%APPDATA%\BinhAnHMI\`
- Linux (Pi, dev on Linux): `~/.binh-an-hmi/`
- Dev (Windows, non-frozen): `src/dmccodegui/auth/`

TDD flow: tests written first (RED — 2 new tests failed, 4 existing passed), then implementation (GREEN — all 6 pass).

New tests:
- `test_linux_mode_returns_home_dir`: monkeypatches `sys.platform='linux'`, `HOME=tmp_path`, confirms result equals `tmp_path/.binh-an-hmi` and directory is created
- `test_linux_mode_creates_directory`: same setup with nested non-existent home, confirms directory creation

Regression guard: `test_dev_mode_returns_auth_dir` does not mock `sys.platform`, so on Windows (`win32`) the new Linux branch is skipped and the else-branch runs unchanged — confirmed passing.

### Task 2: deploy/pi/ skeleton files

- `requirements-pi.txt`: kivy==2.3.1, matplotlib==3.9.4, kivy-matplotlib-widget==0.15.0, gclib @ Galil whl URL. Comments explain aarch64 source-build requirement and gclib ctypes wrapper architecture.
- `binh-an-hmi.desktop`: Freedesktop entry with `Exec=/opt/binh-an-hmi/venv/bin/python -m dmccodegui` and `Icon=/opt/binh-an-hmi/binh-an-hmi.png`. `Terminal=false`, `StartupNotify=false`.
- `binh-an-hmi.png`: 69-byte minimal 1x1 white PNG generated via Python `struct`/`zlib` — valid PNG signature confirmed. Placeholder for real icon derived from BinhAnHMI.ico.
- `vendor/README.md`: one-line note pointing to Galil .deb download URL for `galil-release_1_all.deb`.

## Verification Results

```
python -m pytest tests/test_data_dir.py -x -v
6 passed in 1.28s

test -f deploy/pi/requirements-pi.txt  -> OK
test -f deploy/pi/binh-an-hmi.desktop  -> OK
test -f deploy/pi/binh-an-hmi.png      -> OK
test -d deploy/pi/vendor               -> OK
grep -q "kivy" requirements-pi.txt     -> OK
grep -q "Exec=/opt/binh-an-hmi"        -> OK
PNG signature check                     -> OK
```

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] `src/dmccodegui/main.py` contains `sys.platform == 'linux'` branch
- [x] `tests/test_data_dir.py` contains `test_linux_mode_returns_home_dir`
- [x] `deploy/pi/requirements-pi.txt` exists and contains `kivy`
- [x] `deploy/pi/binh-an-hmi.desktop` exists and contains `[Desktop Entry]`
- [x] `deploy/pi/binh-an-hmi.png` exists (valid PNG)
- [x] `deploy/pi/vendor/` directory exists with README.md
- [x] Commit 9254d46 exists (Task 1)
- [x] Commit 2bcfe84 exists (Task 2)
