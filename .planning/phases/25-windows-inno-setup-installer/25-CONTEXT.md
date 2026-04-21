# Phase 25: Windows Inno Setup Installer - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

A single .exe installer delivers the PyInstaller onedir bundle (from Phase 24) to Windows 11 with Start Menu and Desktop shortcuts, an Add/Remove Programs entry with working uninstaller, optional auto-start on login via HKCU Run key, and Windows Firewall rules for Galil controller communication. No manual steps required after running the installer.

</domain>

<decisions>
## Implementation Decisions

### Installer Identity & Naming
- Installer filename: `BinhAn_HMI_v4.0.0_Setup.exe` (version in filename for file-share coexistence)
- Publisher: "Binh An" (matches Phase 24 CompanyName in version_file.txt)
- Display name in Add/Remove Programs: "Binh An HMI"
- Install path: user-choosable, defaults to `C:\Program Files\Binh An HMI`
- Wizard: minimal — no EULA, no readme page. Just install path picker, options checkboxes, and install
- Reinstall behavior: freely re-installable — no version blocking, overwrites existing installation
- Requires admin elevation (PrivilegesRequired=admin) — needed for Program Files and firewall rules

### Shortcuts
- Start Menu: subfolder "Binh An" containing "Binh An HMI" shortcut
- Desktop: always created (no checkbox — always present)
- Both shortcuts launch `BinhAnHMI.exe` from the install directory

### Post-Install Experience
- Final page: "Launch Binh An HMI now" checkbox, checked by default
- Auto-start on login: checkbox during install, **unchecked by default** — writes HKCU\Software\Microsoft\Windows\CurrentVersion\Run key when checked
- Auto-start is install-time only — no in-app toggle (change requires re-running installer or manual registry edit)
- Silent/unattended install supported via Inno Setup's built-in /SILENT and /VERYSILENT flags

### Firewall Rules
- Auto-create two Windows Firewall inbound rules during install:
  1. **"Binh An HMI - Galil DR"** — UDP port 60007, any source IP (Data Record streaming)
  2. **"Binh An HMI - Galil TCP"** — TCP port 23, any source IP (gclib command channel)
- Rules created via `netsh advfirewall firewall add rule` in installer [Run] section
- Both rules removed on uninstall

### Uninstall Behavior
- Uninstaller removes: Program Files install directory, Start Menu subfolder, Desktop shortcut, HKCU Run key (if set), both firewall rules
- Uninstaller preserves: `%APPDATA%/BinhAnHMI/` (users.json, settings.json) — operator PINs and settings survive reinstall
- App appears in Windows Settings > Apps > Installed apps with "Binh An" publisher and BinhAnHMI.ico icon

### Claude's Discretion
- Inno Setup script (.iss) structure and section organization
- Exact netsh commands for firewall rule creation/removal
- Build script integration (how .iss compilation fits with existing build_windows.bat)
- Installer wizard page layout and messaging text
- Output directory and intermediate file handling

</decisions>

<specifics>
## Specific Ideas

- Installer filename includes version so multiple versions can coexist on a network share (e.g., `BinhAn_HMI_v4.0.0_Setup.exe` alongside future `BinhAn_HMI_v4.1.0_Setup.exe`)
- Silent install support enables IT to deploy via group policy or batch scripts: `BinhAn_HMI_v4.0.0_Setup.exe /VERYSILENT /SUPPRESSMSGBOXES`
- APPDATA preservation means reinstalling/upgrading keeps all operator accounts and machine settings intact

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deploy/windows/BinhAnHMI.ico`: App icon — reuse for installer wizard and uninstaller icon
- `deploy/windows/version_file.txt`: Version metadata (4.0.0, "Binh An" publisher) — source of truth for installer version strings
- `deploy/windows/build_windows.bat`: Existing build script — installer compilation step will extend this or run as a separate post-build step
- `deploy/windows/BinhAnHMI.spec`: PyInstaller spec — defines the onedir output in `dist/BinhAnHMI/` that the installer packages

### Established Patterns
- PyInstaller onedir output: `dist/BinhAnHMI/` contains everything the installer needs to package
- APPDATA path: `%APPDATA%/BinhAnHMI/` established in Phase 24 — installer doesn't need to create this (app creates on first launch)
- App identity: "Binh An HMI" with `BinhAnHMI` as the internal name — consistent across EXE, installer, shortcuts, registry

### Integration Points
- Installer packages the entire `dist/BinhAnHMI/` directory from PyInstaller output
- New file: `deploy/windows/BinhAnHMI.iss` (Inno Setup script)
- Build pipeline: PyInstaller builds first → Inno Setup compiles installer from dist/ output
- HKCU Run key points to `{app}\BinhAnHMI.exe` (Inno Setup {app} constant resolves to install dir)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 25-windows-inno-setup-installer*
*Context gathered: 2026-04-21*
