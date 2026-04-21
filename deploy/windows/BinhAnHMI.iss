; Inno Setup 6 installer script for Binh An HMI
; Produces: dist\BinhAn_HMI_v4.0.0_Setup.exe
; Compile with: ISCC.exe deploy\windows\BinhAnHMI.iss (from repo root)

#define MyAppName    "Binh An HMI"
#define MyAppVersion "4.0.0"
#define MyAppPublisher "Binh An"
#define MyAppExeName "BinhAnHMI.exe"

[Setup]
AppId={{135F218F-F578-4416-B2FE-0CD860124D9C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=
AppSupportURL=
AppUpdatesURL=
DefaultDirName={autopf}\Binh An HMI
DefaultGroupName=Binh An
DisableProgramGroupPage=yes
AllowNoIcons=no
OutputDir=..\..\dist
OutputBaseFilename=BinhAn_HMI_v{#MyAppVersion}_Setup
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

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; Description: "Launch {#MyAppName} at Windows startup"; \
  GroupDescription: "Additional options:"; Flags: unchecked

[Files]
Source: "..\..\dist\BinhAnHMI\*"; DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
; Desktop shortcut
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"

[Registry]
; Write HKCU Run key only when the startup task is selected (unchecked by default)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#MyAppName}"; \
  ValueData: """{app}\{#MyAppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startup

[Run]
; --- Firewall rules: delete first (idempotent reinstall) ---

; Delete existing "Binh An HMI - Galil DR" rule if present (suppress errors)
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall delete rule name=""Binh An HMI - Galil DR"""; \
  Flags: runhidden; StatusMsg: "Configuring firewall (Galil DR)..."

; Delete existing "Binh An HMI - Galil TCP" rule if present (suppress errors)
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall delete rule name=""Binh An HMI - Galil TCP"""; \
  Flags: runhidden; StatusMsg: "Configuring firewall (Galil TCP)..."

; --- Firewall rules: add ---

; Add UDP 60007 inbound rule for Galil Data Record streaming
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall add rule name=""Binh An HMI - Galil DR"" dir=in action=allow protocol=UDP localport=60007"; \
  Flags: runhidden; StatusMsg: "Adding firewall rule for Galil Data Record (UDP 60007)..."

; Add TCP 23 inbound rule for Galil command channel
Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall add rule name=""Binh An HMI - Galil TCP"" dir=in action=allow protocol=TCP localport=23"; \
  Flags: runhidden; StatusMsg: "Adding firewall rule for Galil TCP (port 23)..."

; --- Launch application after install (optional, skipped in silent mode) ---
Filename: "{app}\{#MyAppExeName}"; \
  Description: "Launch {#MyAppName}"; \
  Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"

[UninstallRun]
; Remove firewall rules on uninstall

Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall delete rule name=""Binh An HMI - Galil DR"""; \
  Flags: runhidden

Filename: "{sys}\netsh.exe"; \
  Parameters: "advfirewall firewall delete rule name=""Binh An HMI - Galil TCP"""; \
  Flags: runhidden
