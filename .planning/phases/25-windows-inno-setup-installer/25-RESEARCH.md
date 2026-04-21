# Phase 25: Windows Inno Setup Installer - Research

**Researched:** 2026-04-21
**Domain:** Inno Setup 6, Windows installer scripting, netsh firewall rules, HKCU Run key
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Installer filename: `BinhAn_HMI_v4.0.0_Setup.exe` (version in filename for file-share coexistence)
- Publisher: "Binh An" (matches Phase 24 CompanyName in version_file.txt)
- Display name in Add/Remove Programs: "Binh An HMI"
- Install path: user-choosable, defaults to `C:\Program Files\Binh An HMI`
- Wizard: minimal — no EULA, no readme page. Just install path picker, options checkboxes, and install
- Reinstall behavior: freely re-installable — no version blocking, overwrites existing installation
- Requires admin elevation (PrivilegesRequired=admin) — needed for Program Files and firewall rules
- Start Menu: subfolder "Binh An" containing "Binh An HMI" shortcut
- Desktop: always created (no checkbox — always present)
- Both shortcuts launch `BinhAnHMI.exe` from the install directory
- Final page: "Launch Binh An HMI now" checkbox, checked by default
- Auto-start on login: checkbox during install, **unchecked by default** — writes HKCU\Software\Microsoft\Windows\CurrentVersion\Run key when checked
- Auto-start is install-time only — no in-app toggle
- Silent/unattended install supported via built-in /SILENT and /VERYSILENT flags
- Auto-create two firewall inbound rules during install:
  1. "Binh An HMI - Galil DR" — UDP port 60007, any source IP
  2. "Binh An HMI - Galil TCP" — TCP port 23, any source IP
- Rules created via `netsh advfirewall firewall add rule` in [Run] section
- Both rules removed on uninstall
- Uninstaller removes: Program Files install directory, Start Menu subfolder, Desktop shortcut, HKCU Run key (if set), both firewall rules
- Uninstaller preserves: `%APPDATA%/BinhAnHMI/` (users.json, settings.json)

### Claude's Discretion
- Inno Setup script (.iss) structure and section organization
- Exact netsh commands for firewall rule creation/removal
- Build script integration (how .iss compilation fits with existing build_windows.bat)
- Installer wizard page layout and messaging text
- Output directory and intermediate file handling

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| WIN-03 | Inno Setup installer creates Start Menu and Desktop shortcuts that launch the app | [Icons] section with {group}\Binh An\Binh An HMI and {commondesktop}\Binh An HMI, both pointing to {app}\BinhAnHMI.exe |
| WIN-04 | App appears in Windows Add/Remove Programs with a working uninstaller that cleanly removes all installed files | [Setup] AppName/AppId/AppPublisher + UninstallDisplayIcon + uninstalldelete flags; Inno Setup auto-generates unins000.exe |
| WIN-06 | Installer offers optional "Launch at Windows startup" checkbox that adds HKCU Run key for auto-start on login | [Tasks] + [Registry] with Tasks: parameter + uninsdeletevalue flag |
</phase_requirements>

---

## Summary

Inno Setup 6 (current stable: 6.7.1, released 2026-02-17) is the standard tool for producing Windows .exe installers from PyInstaller onedir bundles. It uses a declarative .iss script organized into named sections (`[Setup]`, `[Files]`, `[Icons]`, `[Tasks]`, `[Registry]`, `[Run]`, `[UninstallRun]`) that the ISCC.exe console compiler processes into a single self-extracting installer. For this phase every required feature — shortcuts, Add/Remove Programs entry, auto-start checkbox, firewall rules — maps cleanly to native Inno Setup section entries without any Pascal scripting required.

The PyInstaller onedir output at `dist/BinhAnHMI/` is packaged using a single wildcard `[Files]` entry with `recursesubdirs createallsubdirs ignoreversion` flags, which recursively copies the entire directory tree. The ISCC.exe compiler is invoked from a batch file after the PyInstaller step, accepting `/O` and `/F` overrides for output path and filename.

The three requirement IDs (WIN-03, WIN-04, WIN-06) each have a direct, well-understood Inno Setup mechanism: WIN-03 uses `[Icons]` entries for `{group}` and `{commondesktop}`; WIN-04 is automatic from `[Setup]` `AppName`/`AppPublisher`/`UninstallDisplayIcon` directives; WIN-06 uses a `[Tasks]` entry (unchecked flag) linked to a `[Registry]` HKCU Run key entry via `Tasks:` parameter. No third-party extensions or custom code needed.

**Primary recommendation:** Write `deploy/windows/BinhAnHMI.iss` with the seven standard sections, invoke with `iscc.exe /O"dist" /F"BinhAn_HMI_v4.0.0_Setup"`, and extend `build_windows.bat` with a second ISCC.exe call after PyInstaller succeeds.

---

## Standard Stack

### Core
| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| Inno Setup | 6.7.1 (stable) | .iss → .exe installer compiler | Most widely used free Windows installer tool; simpler than NSIS; out-of-scope in REQUIREMENTS.md explicitly excludes NSIS |
| ISCC.exe | Ships with Inno Setup 6 | Command-line compiler for .iss scripts | Enables batch file automation, CI integration, exit code checking |

### No Additional Libraries Required
This phase is entirely declarative .iss scripting + netsh.exe (ships with Windows). No Python packages, no npm, no external dependencies.

**Installation (developer machine):**
```
Download: https://jrsoftware.org/isdl.php
Installer: innosetup-6.7.1.exe
Default path: C:\Program Files (x86)\Inno Setup 6\ISCC.exe
```

---

## Architecture Patterns

### Recommended File Layout
```
deploy/windows/
├── BinhAnHMI.iss          # New — Inno Setup script (this phase)
├── BinhAnHMI.ico          # Existing — reused for wizard + uninstall icon
├── BinhAnHMI.spec         # Existing — PyInstaller spec
├── build_windows.bat      # Existing — extended to call ISCC.exe after PyInstaller
├── version_file.txt       # Existing — version metadata source of truth
└── vendor/                # Existing — gclib DLLs
dist/
└── BinhAnHMI/             # PyInstaller output — packaged by installer
    ├── BinhAnHMI.exe
    └── ... (hundreds of files)
```

### Pattern 1: Full .iss Script Structure

A minimal but complete script for this project:

```iss
; Source: Inno Setup 6 documentation + verified working patterns
#define MyAppName "Binh An HMI"
#define MyAppVersion "4.0.0"
#define MyAppPublisher "Binh An"
#define MyAppExeName "BinhAnHMI.exe"
#define MyAppId "BinhAnHMI"

[Setup]
AppId={{GENERATE-GUID-HERE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppPublisher}
OutputBaseFilename=BinhAn_HMI_v{#MyAppVersion}_Setup
OutputDir=..\..\dist
SetupIconFile=BinhAnHMI.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableWelcomePage=no
DisableReadyPage=no
DisableProgramGroupPage=no
AllowNoIcons=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Launch {#MyAppName} at Windows startup"; \
  GroupDescription: "Additional options:"; Flags: unchecked

[Files]
Source: "..\..\dist\BinhAnHMI\*"; DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
  WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
  WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"

[Registry]
; Auto-start on login (HKCU — only when startup task is checked)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#MyAppName}"; \
  ValueData: """{app}\{#MyAppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startup

[Run]
; Delete existing firewall rules (idempotent re-install safety)
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall delete rule name=""Binh An HMI - Galil DR"""; \
  Flags: runhidden; StatusMsg: "Configuring firewall...";
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall delete rule name=""Binh An HMI - Galil TCP"""; \
  Flags: runhidden;

; Add inbound rules for Galil controller communication
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall add rule name=""Binh An HMI - Galil DR"" protocol=UDP dir=in action=allow localport=60007 enable=yes"; \
  Flags: runhidden;
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall add rule name=""Binh An HMI - Galil TCP"" protocol=TCP dir=in action=allow localport=23 enable=yes"; \
  Flags: runhidden;

; Launch app after install (postinstall = shows checkbox on final wizard page)
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; \
  Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"

[UninstallRun]
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall delete rule name=""Binh An HMI - Galil DR"""; \
  Flags: runhidden;
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall delete rule name=""Binh An HMI - Galil TCP"""; \
  Flags: runhidden;
```

### Pattern 2: ISCC.exe Build Integration

Extend `build_windows.bat` after the existing PyInstaller block:

```bat
REM Compile Inno Setup installer (requires Inno Setup 6 installed)
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
    echo WARNING: Inno Setup 6 not found — skipping installer build
    echo Install from: https://jrsoftware.org/isdl.php
    exit /b 0
)

%ISCC% /Q "deploy\windows\BinhAnHMI.iss"
if errorlevel 1 (
    echo INSTALLER BUILD FAILED
    exit /b 1
)
echo Installer: dist\BinhAn_HMI_v4.0.0_Setup.exe
```

The `/Q` flag suppresses all output except errors. Exit code 0 = success, 2 = compile failure.

### Pattern 3: HKCU Run Key via Tasks (WIN-06)

The `[Tasks]` + `[Registry]` combination is the standard Inno Setup pattern for optional registry writes:

```iss
[Tasks]
Name: "startup"; Description: "Launch at Windows startup"; Flags: unchecked

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run";
  ValueType: string; ValueName: "Binh An HMI";
  ValueData: """{app}\BinhAnHMI.exe""";
  Flags: uninsdeletevalue; Tasks: startup
```

- `Flags: unchecked` — checkbox is unchecked by default (matches locked decision)
- `Tasks: startup` — registry entry only written if user checks the box
- `Flags: uninsdeletevalue` — uninstaller automatically removes the Run value

### Anti-Patterns to Avoid

- **Program-based firewall rules instead of port-based:** The decisions specify UDP port 60007 and TCP port 23 — use `localport=` not `program=`. Port rules survive the app being moved or reinstalled.
- **Omitting the delete-before-add in [Run]:** Re-running the installer without the prior delete leaves duplicate firewall rule entries. Always delete by name first.
- **Using `{pf}` instead of `{autopf}`:** On x64 Windows, `{pf}` maps to Program Files (x86). Use `{autopf}` which resolves to 64-bit Program Files when `ArchitecturesInstallIn64BitMode=x64compatible` is set.
- **Missing `ignoreversion` flag on [Files]:** Without it, Inno Setup checks file version numbers and may skip overwriting files during reinstall. Use `ignoreversion` for all application files.
- **AppId without GUID:** Using a plain string AppId risks collisions if user installs another app with the same name. Use a GUID (generated via Inno Setup IDE: Tools > Generate GUID). Wrap in `{` `}` and Inno Setup escapes the brace.
- **Forgetting `SolidCompression=yes`:** Without it, compression ratio is poor for large PyInstaller bundles (often 200-400 MB uncompressed).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Uninstaller | Custom uninstall script | Inno Setup auto-generated unins000.exe | Handles partial installs, registry cleanup, log tracking automatically |
| Add/Remove Programs entry | Manual registry writes to Uninstall key | Inno Setup [Setup] directives | Inno Setup writes all 12+ required values (DisplayName, Publisher, UninstallString, DisplayVersion, etc.) correctly |
| Shortcut creation | Manual .lnk scripting | [Icons] section | Handles Start Menu subfolder creation, working directory, icon index |
| APPDATA directory creation | Install-time mkdir | Do nothing — app creates on first launch | Phase 24 decision: app creates %APPDATA%/BinhAnHMI/ on first run |
| File version checking | Custom logic | ignoreversion flag | Inno Setup's built-in version logic is sufficient; just bypass it for app files |

---

## Common Pitfalls

### Pitfall 1: AppId GUID Format
**What goes wrong:** Using bare curly braces `{GUID}` in the .iss file causes a parse error — Inno Setup interprets `{...}` as a constant reference.
**Why it happens:** Inno Setup uses `{` and `}` for constants like `{app}`, `{sys}`, etc.
**How to avoid:** Double the opening brace: `AppId={{A1B2C3D4-...}` — the double brace is an escape that produces a literal `{`.
**Warning signs:** Compiler error "Unknown constant" during ISCC.exe compile.

### Pitfall 2: Firewall Rule Accumulation on Reinstall
**What goes wrong:** Each reinstall adds another firewall rule with the same name. Windows allows duplicate-named rules, so after 3 installs there are 6 rules.
**Why it happens:** `netsh add rule` does not check for existing rules by name.
**How to avoid:** Add a `delete rule` step before the `add rule` step in `[Run]`. The delete silently succeeds even if no rule exists.

### Pitfall 3: Source Path Relative to .iss Location
**What goes wrong:** `Source: "dist\BinhAnHMI\*"` fails because ISCC.exe resolves relative paths from the .iss file's directory (`deploy/windows/`), not the repo root.
**Why it happens:** The .iss lives in `deploy/windows/` but the dist/ folder is at the repo root.
**How to avoid:** Use `..\..\dist\BinhAnHMI\*` in the Source parameter — or pass `/D` defines from the build script to inject the absolute dist path.

### Pitfall 4: Missing ArchitecturesInstallIn64BitMode
**What goes wrong:** Installer runs in 32-bit mode on 64-bit Windows. Registry writes go to `SOFTWARE\WOW6432Node\` instead of `SOFTWARE\`, and `{autopf}` resolves to Program Files (x86).
**Why it happens:** Inno Setup defaults to 32-bit installer mode for compatibility.
**How to avoid:** Add both `ArchitecturesAllowed=x64compatible` and `ArchitecturesInstallIn64BitMode=x64compatible` to [Setup].

### Pitfall 5: HKCU Run Key Quoting
**What goes wrong:** Auto-start fails silently if the install path contains spaces — Windows parses the Run value as a command line and splits on the space.
**Why it happens:** `C:\Program Files\Binh An HMI\BinhAnHMI.exe` becomes `C:\Program` with arguments `Files\Binh An HMI\BinhAnHMI.exe`.
**How to avoid:** Wrap the path in double quotes in ValueData: `ValueData: """{app}\BinhAnHMI.exe"""` (three double-quotes: one literal, one Inno constant boundary, one literal closing).

### Pitfall 6: Uninstall Not Removing Shortcuts
**What goes wrong:** After uninstall, Start Menu and Desktop shortcuts remain.
**Why it happens:** Inno Setup only auto-removes shortcuts it created IF the shortcut still exists at the exact path it was created at.
**How to avoid:** This is the default behavior — Inno Setup tracks everything it creates in unins000.dat. No special flags needed. The risk is if files were moved manually; not a concern here.

---

## Code Examples

### Port-Based Firewall Rule (official Microsoft syntax)
```
; Source: https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/netsh-advfirewall-firewall-control-firewall-behavior
netsh advfirewall firewall add rule name="Open Port 80" dir=in action=allow protocol=TCP localport=80
netsh advfirewall firewall delete rule name="rule name" protocol=udp localport=500
```

In .iss [Run] context:
```iss
; Source: verified from qbt64.iss pattern + Microsoft docs
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall add rule name=""Binh An HMI - Galil DR"" protocol=UDP dir=in action=allow localport=60007 enable=yes"; \
  Flags: runhidden;
```

### ISCC.exe compilation from batch
```bat
; Source: https://jrsoftware.org/ishelp/topic_compilercmdline.htm
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /Q /O"dist" /F"MyApp-1.0" "script.iss"
; Exit code: 0=success, 1=bad args, 2=compile failed
```

### [Files] wildcard for onedir bundle
```iss
; Source: jrsoftware.org/ishelp/topic_filessection.htm + verified working pattern
[Files]
Source: "..\..\dist\BinhAnHMI\*"; DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs
```

### Conditional HKCU Run key
```iss
; Source: jrsoftware.org/ishelp/topic_registrysection.htm
[Tasks]
Name: "startup"; Description: "Launch Binh An HMI at Windows startup"; \
  GroupDescription: "Additional options:"; Flags: unchecked

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "Binh An HMI"; \
  ValueData: """{app}\BinhAnHMI.exe"""; \
  Flags: uninsdeletevalue; Tasks: startup
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `netsh firewall add allowedprogram` | `netsh advfirewall firewall add rule` | Windows Vista+ | Old command deprecated; `netsh firewall` context may be removed in future Windows versions |
| WizardStyle=classic (default) | WizardStyle=modern | Inno Setup 6.0 (2019) | Modern style gives white-background wizard that matches Windows 11 aesthetics |
| Inno Setup 5.x | Inno Setup 6.x | 2019 | IS6 adds Unicode support, modern wizard style, improved 64-bit support |
| Inno Setup 6 stable | Inno Setup 7 preview | IS7 preview April 2026 | Do NOT use IS7 preview for production — use 6.7.1 |

---

## Open Questions

1. **ISCC.exe path on developer machine**
   - What we know: Default install is `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
   - What's unclear: Developer may have installed to a custom path
   - Recommendation: In build_windows.bat, check default path, fall back to PATH lookup (`where iscc`), and print install URL if not found. Non-fatal — PyInstaller output still usable without installer step.

2. **AppId GUID value**
   - What we know: Should be a unique GUID, generated once and kept stable across versions
   - What's unclear: No GUID has been generated yet for this project
   - Recommendation: Planner should specify that the implementation step generates a GUID (via Inno Setup IDE or PowerShell `[guid]::NewGuid()`) and hard-codes it in the .iss file.

3. **OutputDir relative path from .iss**
   - What we know: Source is `deploy/windows/BinhAnHMI.iss`, dist is at repo root `dist/`
   - What's unclear: Whether to use `..\..\dist` in OutputDir or pass `/O` override from batch
   - Recommendation: Use `OutputDir=..\..\dist` in the .iss file — simpler, no batch override needed. ISCC resolves relative OutputDir from the .iss file location.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (pyproject.toml `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` — `testpaths = ["tests"]` |
| Quick run command | `pytest tests/test_installer.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WIN-03 | Installer file `dist/BinhAn_HMI_v4.0.0_Setup.exe` exists after build | smoke/file-check | `pytest tests/test_installer.py::test_installer_exe_exists -x` | Wave 0 |
| WIN-03 | .iss script contains Start Menu icon entry for `{group}\Binh An\Binh An HMI` | unit/content | `pytest tests/test_installer.py::test_iss_start_menu_shortcut -x` | Wave 0 |
| WIN-03 | .iss script contains Desktop icon entry for `{commondesktop}\Binh An HMI` | unit/content | `pytest tests/test_installer.py::test_iss_desktop_shortcut -x` | Wave 0 |
| WIN-04 | .iss [Setup] contains AppName, AppPublisher, UninstallDisplayIcon | unit/content | `pytest tests/test_installer.py::test_iss_appname_publisher -x` | Wave 0 |
| WIN-04 | .iss [Setup] contains AppId directive | unit/content | `pytest tests/test_installer.py::test_iss_appid -x` | Wave 0 |
| WIN-06 | .iss [Tasks] contains startup entry with Flags: unchecked | unit/content | `pytest tests/test_installer.py::test_iss_startup_task_unchecked -x` | Wave 0 |
| WIN-06 | .iss [Registry] HKCU Run entry has Tasks: startup and uninsdeletevalue | unit/content | `pytest tests/test_installer.py::test_iss_hkcu_run_key -x` | Wave 0 |

**Note:** Full functional testing (shortcuts actually work, uninstaller removes files, Run key takes effect on login) requires a real Windows install target. Those are manual acceptance tests, not automated pytest tests.

### Sampling Rate
- **Per task commit:** `pytest tests/test_installer.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_installer.py` — covers WIN-03, WIN-04, WIN-06 via .iss content inspection (parse the .iss file as text, assert required strings present)

*(All tests read the .iss file as text and assert required patterns are present — no Windows runtime or actual installer execution needed in CI.)*

---

## Sources

### Primary (HIGH confidence)
- [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php) — confirmed current version 6.7.1 (released 2026-02-17)
- [jrsoftware.org/ishelp/topic_filessection.htm](https://jrsoftware.org/ishelp/topic_filessection.htm) — Source, DestDir, recursesubdirs, createallsubdirs, ignoreversion flags
- [jrsoftware.org/ishelp/topic_registrysection.htm](https://jrsoftware.org/ishelp/topic_registrysection.htm) — Root, Subkey, ValueType, ValueData, uninsdeletevalue flag
- [jrsoftware.org/ishelp/topic_runsection.htm](https://jrsoftware.org/ishelp/topic_runsection.htm) — [Run]/[UninstallRun] parameters, runhidden, postinstall, skipifsilent flags
- [jrsoftware.org/ishelp/topic_iconssection.htm](https://jrsoftware.org/ishelp/topic_iconssection.htm) — [Icons] Name/Filename/WorkingDir/IconFilename
- [jrsoftware.org/ishelp/topic_consts.htm](https://jrsoftware.org/ishelp/topic_consts.htm) — directory constants {app}, {autopf}, {commondesktop}, {group}, {sys}
- [jrsoftware.org/ishelp/topic_compilercmdline.htm](https://jrsoftware.org/ishelp/topic_compilercmdline.htm) — ISCC.exe /O, /F, /Q, exit codes
- [jrsoftware.org/ishelp/topic_setup_appid.htm](https://jrsoftware.org/ishelp/topic_setup_appid.htm) — AppId GUID purpose and _is1 key naming
- [learn.microsoft.com - netsh advfirewall firewall context](https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/netsh-advfirewall-firewall-control-firewall-behavior) — port-based rule syntax, delete rule syntax

### Secondary (MEDIUM confidence)
- [github.com/Gelmir/scriptroot/blob/master/qbt/qbt64.iss](https://github.com/Gelmir/scriptroot/blob/master/qbt/qbt64.iss) — real-world delete-before-add firewall pattern; verified against Microsoft docs
- [engineertips.wordpress.com - Inno Setup Auto Run at Startup](https://engineertips.wordpress.com/2020/08/05/inno-setup-auto-run-at-startup/) — HKCU Run key pattern; verified against official [Registry] docs
- [jrsoftware.org/ishelp/topic_setup_wizardstyle.htm](https://jrsoftware.org/ishelp/topic_setup_wizardstyle.htm) — WizardStyle=modern behavior

### Tertiary (LOW confidence — for awareness only)
- None required; all critical claims verified against official sources

---

## Metadata

**Confidence breakdown:**
- Standard stack (Inno Setup 6.7.1, ISCC.exe): HIGH — confirmed from official download page
- Architecture (.iss structure, section contents): HIGH — all section parameters verified from official docs
- Firewall netsh commands: HIGH — verified from Microsoft Learn official reference
- HKCU Run key pattern: HIGH — verified from official [Registry] section docs
- Build script integration: HIGH — ISCC.exe flags confirmed from official compiler docs

**Research date:** 2026-04-21
**Valid until:** 2026-10-21 (Inno Setup 6 is stable; Inno Setup 7 preview should not be used for production)
