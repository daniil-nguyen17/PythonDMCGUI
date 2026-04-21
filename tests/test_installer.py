"""
Content-inspection tests for deploy/windows/BinhAnHMI.iss.

All tests read the .iss file as plain text and assert required patterns
per the locked decisions for Phase 25 (WIN-03, WIN-04, WIN-06).
"""
import re
import pathlib
import pytest

ISS_PATH = pathlib.Path(__file__).resolve().parent.parent / "deploy" / "windows" / "BinhAnHMI.iss"


@pytest.fixture(scope="module")
def iss_text():
    """Return the full .iss file contents as a string."""
    return ISS_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------

def test_iss_file_exists():
    assert ISS_PATH.exists(), f".iss file not found at {ISS_PATH}"
    assert ISS_PATH.stat().st_size > 0, ".iss file is empty"


# ---------------------------------------------------------------------------
# [Setup] section
# ---------------------------------------------------------------------------

def test_iss_setup_section(iss_text):
    assert "AppName=" in iss_text, "[Setup] missing AppName"
    assert 'AppName="Binh An HMI"' in iss_text or "AppName={#MyAppName}" in iss_text, \
        "[Setup] AppName does not match 'Binh An HMI'"
    assert 'AppPublisher="Binh An"' in iss_text or "AppPublisher={#MyAppPublisher}" in iss_text, \
        "[Setup] AppPublisher does not match 'Binh An'"
    assert "AppVersion=" in iss_text, "[Setup] missing AppVersion"
    assert "PrivilegesRequired=admin" in iss_text, "[Setup] PrivilegesRequired must be admin"
    assert "WizardStyle=modern" in iss_text, "[Setup] WizardStyle must be modern"


def test_iss_appid(iss_text):
    # AppId must use double-brace escape: {{...}
    assert "AppId={{" in iss_text, "[Setup] AppId must use double-brace escape (AppId={{...})"
    # Must contain a GUID-like pattern
    guid_pattern = re.compile(r"\{\{[0-9A-Fa-f\-]{36}\}")
    assert guid_pattern.search(iss_text), "[Setup] AppId does not contain a valid GUID"


def test_iss_appname_publisher(iss_text):
    """WIN-04: locked AppName and AppPublisher values."""
    assert "Binh An HMI" in iss_text, "AppName 'Binh An HMI' not found in .iss"
    assert "Binh An" in iss_text, "AppPublisher 'Binh An' not found in .iss"


def test_iss_uninstall_display_icon(iss_text):
    """WIN-04: uninstall icon in Add/Remove Programs."""
    assert "UninstallDisplayIcon=" in iss_text, "[Setup] missing UninstallDisplayIcon"
    assert "BinhAnHMI.exe" in iss_text or "MyAppExeName" in iss_text, \
        "UninstallDisplayIcon should reference BinhAnHMI.exe"


def test_iss_64bit_mode(iss_text):
    assert "ArchitecturesInstallIn64BitMode=x64compatible" in iss_text, \
        "[Setup] ArchitecturesInstallIn64BitMode=x64compatible not set"


def test_iss_output_filename(iss_text):
    assert "BinhAn_HMI_v4.0.0_Setup" in iss_text, \
        "OutputBaseFilename must contain 'BinhAn_HMI_v4.0.0_Setup'"


# ---------------------------------------------------------------------------
# [Files] section
# ---------------------------------------------------------------------------

def test_iss_files_source(iss_text):
    """[Files] source must point to the PyInstaller onedir output."""
    assert re.search(r"dist[\\\/]BinhAnHMI", iss_text), \
        "[Files] Source must reference dist\\BinhAnHMI"
    assert "recursesubdirs" in iss_text.lower(), "[Files] Flags must include recursesubdirs"
    assert "ignoreversion" in iss_text.lower(), "[Files] Flags must include ignoreversion"


# ---------------------------------------------------------------------------
# [Icons] section — WIN-03
# ---------------------------------------------------------------------------

def test_iss_start_menu_shortcut(iss_text):
    """WIN-03: Start Menu shortcut."""
    assert "{group}" in iss_text, "[Icons] missing Start Menu shortcut ({group})"
    # Check that the group entry points to the exe
    assert re.search(r"\{group\}.*BinhAnHMI\.exe", iss_text) or \
           re.search(r"\{group\}.*MyAppExeName", iss_text), \
        "[Icons] Start Menu shortcut does not point to BinhAnHMI.exe"


def test_iss_desktop_shortcut(iss_text):
    """WIN-03: Desktop shortcut."""
    assert "{commondesktop}" in iss_text, "[Icons] missing Desktop shortcut ({commondesktop})"
    assert re.search(r"\{commondesktop\}.*BinhAnHMI\.exe", iss_text) or \
           re.search(r"\{commondesktop\}.*MyAppExeName", iss_text), \
        "[Icons] Desktop shortcut does not point to BinhAnHMI.exe"


# ---------------------------------------------------------------------------
# [Tasks] section — WIN-06
# ---------------------------------------------------------------------------

def test_iss_startup_task_unchecked(iss_text):
    """WIN-06: auto-start task must be unchecked by default."""
    assert "[Tasks]" in iss_text, "[Tasks] section missing"
    # The startup task entry must have 'unchecked' in its Flags
    assert re.search(r"Flags:.*unchecked", iss_text, re.IGNORECASE), \
        "[Tasks] startup entry must have Flags: unchecked"


# ---------------------------------------------------------------------------
# [Registry] section — WIN-06
# ---------------------------------------------------------------------------

def test_iss_hkcu_run_key(iss_text):
    """WIN-06: HKCU Run key written only when startup task is checked."""
    assert "[Registry]" in iss_text, "[Registry] section missing"
    assert "HKCU" in iss_text, "[Registry] must use HKCU for Run key"
    # Must be conditional on the startup task
    assert re.search(r"Tasks:.*startup", iss_text, re.IGNORECASE), \
        "[Registry] Run key must have Tasks: startup condition"
    assert "uninsdeletevalue" in iss_text.lower(), \
        "[Registry] Run key must have uninsdeletevalue flag for clean uninstall"


# ---------------------------------------------------------------------------
# [Run] section — firewall rules
# ---------------------------------------------------------------------------

def test_iss_firewall_install_rules(iss_text):
    """[Run] must add both Galil firewall rules on install."""
    assert "Binh An HMI - Galil DR" in iss_text, \
        "[Run] missing netsh rule 'Binh An HMI - Galil DR' (UDP 60007)"
    assert "Binh An HMI - Galil TCP" in iss_text, \
        "[Run] missing netsh rule 'Binh An HMI - Galil TCP' (TCP 23)"
    assert "60007" in iss_text, "[Run] UDP port 60007 not mentioned"
    assert re.search(r"\b23\b", iss_text), "[Run] TCP port 23 not mentioned"


def test_iss_firewall_uninstall_rules(iss_text):
    """[UninstallRun] must delete both firewall rules on uninstall."""
    assert "[UninstallRun]" in iss_text, "[UninstallRun] section missing"
    # Both rule names should appear in the delete commands
    sections = iss_text.split("[UninstallRun]")
    assert len(sections) > 1, "[UninstallRun] section not found"
    uninstall_section = sections[1]
    assert "Binh An HMI - Galil DR" in uninstall_section, \
        "[UninstallRun] missing delete for 'Binh An HMI - Galil DR'"
    assert "Binh An HMI - Galil TCP" in uninstall_section, \
        "[UninstallRun] missing delete for 'Binh An HMI - Galil TCP'"


def test_iss_firewall_delete_before_add(iss_text):
    """[Run] must delete existing rules before adding (idempotent reinstall)."""
    assert "[Run]" in iss_text, "[Run] section missing"
    run_section_match = re.search(r"\[Run\](.*?)(?=\[|\Z)", iss_text, re.DOTALL)
    assert run_section_match, "[Run] section not parseable"
    run_section = run_section_match.group(1)
    # Both 'delete' and 'add' must appear, with delete coming first
    delete_pos = run_section.lower().find("delete")
    add_pos = run_section.lower().find("localport")
    assert delete_pos != -1, "[Run] no delete command found before firewall add"
    assert add_pos != -1, "[Run] no localport (add rule) command found"
    assert delete_pos < add_pos, \
        "[Run] firewall delete must appear before firewall add for idempotent reinstall"


# ---------------------------------------------------------------------------
# [Run] launch after install
# ---------------------------------------------------------------------------

def test_iss_launch_after_install(iss_text):
    """[Run] must have a postinstall launch entry for the exe."""
    assert "postinstall" in iss_text.lower(), \
        "[Run] missing postinstall flag for launch-after-install entry"
    assert "nowait" in iss_text.lower(), \
        "[Run] launch entry must have nowait flag"
    assert "skipifsilent" in iss_text.lower(), \
        "[Run] launch entry must have skipifsilent flag"
