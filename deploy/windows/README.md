# Windows Deployment Guide — Binh An HMI

---

## For Technicians (Installing)

### Prerequisites

- Windows 11 (64-bit)
- Galil controller reachable on the local network

### Installation steps

1. Copy `DMCGrindingGUI_Setup.exe` to the target Windows 11 machine.
2. Double-click the installer and follow the prompts.
   - No administrator rights required for a per-user install.
3. Launch the app from the **Start Menu** or the **Desktop shortcut**.
4. Enter the controller IP address on the Setup screen and connect.

### If Windows Defender quarantines gclib.dll

Galil's `gclib.dll` is not code-signed. Defender may flag it on first run.

**Fix:**
1. Open **Settings > Virus & threat protection > Manage settings**.
2. Scroll to **Exclusions** and click **Add or remove exclusions**.
3. Add the install directory (default: `%LOCALAPPDATA%\Programs\BinhAnHMI`).
4. Re-launch the app.

### Data locations

User data persists across uninstall and reinstall:

| Item | Path |
|------|------|
| User accounts (`users.json`) | `%APPDATA%\BinhAnHMI\users.json` |
| Settings (`settings.json`) | `%APPDATA%\BinhAnHMI\settings.json` |
| Application log | `%APPDATA%\BinhAnHMI\logs\app.log` |

---

## For Developers (Building the Installer)

### Prerequisites

- Python 3.11 or later
- PyInstaller: `pip install pyinstaller`
- Inno Setup 6 (optional — for producing `DMCGrindingGUI_Setup.exe`)
  - Download: https://jrsoftware.org/isdl.php
  - The build script auto-detects `ISCC.exe` via `%PATH%` and `Program Files`.

### Build command

From the repository root on Windows:

```bat
deploy\windows\build_windows.bat
```

The script performs two steps:

1. **PyInstaller** — packages the app into `dist\BinhAnHMI\` (onedir bundle).
   This folder is a self-contained Windows application.

2. **Inno Setup (ISCC)** — wraps the bundle into `Output\DMCGrindingGUI_Setup.exe`.
   This step is **non-fatal**: if ISCC is not installed, the script prints a
   warning and exits successfully. The `dist\BinhAnHMI\` folder can still be
   distributed by copying the directory directly.

### Key build notes

- `gclib.dll` is vendored into the repo (`deploy/windows/vendor/`) and
  explicitly listed in the spec file `binaries=` section. PyInstaller does
  not auto-detect ctypes-loaded DLLs.
- `BinhAnHMI.iss` uses a fixed `AppId` GUID so Windows Add/Remove Programs
  tracks upgrades correctly across installs.
- Firewall rules in `BinhAnHMI.iss` use delete-before-add to avoid duplicates
  on reinstall.
- The installer is per-user by default (`PrivilegesRequired=lowest`).
