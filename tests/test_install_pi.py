"""Content-inspection tests for deploy/pi/ install artifacts.

All tests read files as plain text and assert required patterns
per the locked decisions for Phase 26 (PI-01, PI-04, PI-05).
Mirrors the test_installer.py pattern from Phase 25.
"""
import re
import pathlib
import pytest

DEPLOY_PI = pathlib.Path(__file__).resolve().parent.parent / "deploy" / "pi"
INSTALL_SH = DEPLOY_PI / "install.sh"
REQUIREMENTS = DEPLOY_PI / "requirements-pi.txt"
DESKTOP_FILE = DEPLOY_PI / "binh-an-hmi.desktop"


@pytest.fixture(scope="module")
def install_sh_text():
    """Return the full install.sh contents as a string."""
    return INSTALL_SH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------

def test_install_sh_exists():
    assert INSTALL_SH.exists(), f"install.sh not found at {INSTALL_SH}"
    assert INSTALL_SH.stat().st_size > 0, "install.sh is empty"


# ---------------------------------------------------------------------------
# Strict mode and safety
# ---------------------------------------------------------------------------

def test_install_sh_set_e(install_sh_text):
    """Script uses set -euo pipefail for fail-fast operation."""
    assert "set -euo pipefail" in install_sh_text, \
        "install.sh must use 'set -euo pipefail'"


def test_install_sh_root_check(install_sh_text):
    """Script checks that it is running as root/sudo."""
    assert re.search(r"\$EUID|whoami|id -u", install_sh_text), \
        "install.sh must check for root/sudo before proceeding"


# ---------------------------------------------------------------------------
# Architecture detection (informational, not abort)
# ---------------------------------------------------------------------------

def test_install_sh_arch_info(install_sh_text):
    """Script detects aarch64 and prints informational message about source compilation."""
    assert "uname -m" in install_sh_text or "uname" in install_sh_text, \
        "install.sh must detect architecture via 'uname -m'"
    assert "aarch64" in install_sh_text, \
        "install.sh must reference 'aarch64' (for informational message)"
    # Must NOT abort on 64-bit — user decision targets aarch64.
    # Check that the aarch64 conditional block does NOT call exit 1.
    # We look for a pattern where the aarch64 if-block contains exit 1 on the same or next line.
    assert not re.search(r'if.*aarch64[^f]*\bfi\b', install_sh_text, re.DOTALL) or \
           not re.search(r'if.*aarch64.*exit\s+1.*\bfi\b', install_sh_text, re.DOTALL), \
        "install.sh must NOT exit on aarch64 (user decision: target is 64-bit Pi OS)"


# ---------------------------------------------------------------------------
# X11 forcing — must be FIRST functional operation
# ---------------------------------------------------------------------------

def test_install_sh_x11_first(install_sh_text):
    """First raspi-config call must be do_wayland W1 (X11 before anything else)."""
    assert "do_wayland W1" in install_sh_text, \
        "install.sh must force X11 via 'raspi-config nonint do_wayland W1'"
    # X11 forcing must appear before apt-get install
    x11_pos = install_sh_text.find("do_wayland W1")
    apt_pos = install_sh_text.find("apt-get install")
    assert x11_pos < apt_pos, \
        "do_wayland W1 must appear before apt-get install (X11 first)"


# ---------------------------------------------------------------------------
# apt dependencies — base + aarch64 build toolchain
# ---------------------------------------------------------------------------

def test_install_sh_apt_deps(install_sh_text):
    """Script installs core Python and build tools via apt."""
    assert "python3" in install_sh_text, "install.sh must install python3"
    assert re.search(r"python3-pip|python3\.11-pip", install_sh_text), \
        "install.sh must install python3-pip"
    assert re.search(r"python3-venv|python3\.11-venv", install_sh_text), \
        "install.sh must install python3-venv"
    assert "build-essential" in install_sh_text, \
        "install.sh must install build-essential (gcc/g++ for source compilation)"
    assert "cmake" in install_sh_text, \
        "install.sh must install cmake (Kivy build system)"
    assert "pkg-config" in install_sh_text, \
        "install.sh must install pkg-config (library path resolution)"


def test_install_sh_aarch64_build_deps(install_sh_text):
    """Script installs aarch64-specific SDL2 dev headers for Kivy source compilation."""
    assert "libsdl2-dev" in install_sh_text, \
        "install.sh must install libsdl2-dev (SDL2 headers for Kivy source build)"
    assert "libsdl2-image-dev" in install_sh_text, \
        "install.sh must install libsdl2-image-dev"
    assert "libsdl2-mixer-dev" in install_sh_text, \
        "install.sh must install libsdl2-mixer-dev"
    assert "libsdl2-ttf-dev" in install_sh_text, \
        "install.sh must install libsdl2-ttf-dev"


# ---------------------------------------------------------------------------
# Galil gclib installation
# ---------------------------------------------------------------------------

def test_install_sh_gclib(install_sh_text):
    """Script installs Galil gclib via vendored .deb and apt."""
    assert re.search(r"dpkg\s+-i.*galil", install_sh_text, re.IGNORECASE), \
        "install.sh must run 'dpkg -i' with galil vendor .deb"
    assert re.search(r"apt-get\s+install.*gclib|apt-get\s+install.*gcapsd", install_sh_text), \
        "install.sh must install gclib/gcapsd via apt-get after dpkg"


# ---------------------------------------------------------------------------
# Venv creation
# ---------------------------------------------------------------------------

def test_install_sh_venv(install_sh_text):
    """Script creates venv at /opt/binh-an-hmi/venv (may use variable expansion)."""
    assert "python3 -m venv" in install_sh_text, \
        "install.sh must create venv via 'python3 -m venv'"
    # Accept either the literal path or variable references that resolve to it:
    #   VENV_DIR="$INSTALL_DIR/venv"  +  INSTALL_DIR="/opt/binh-an-hmi"
    assert ("/opt/binh-an-hmi/venv" in install_sh_text
            or (re.search(r'VENV_DIR.*venv', install_sh_text)
                and "/opt/binh-an-hmi" in install_sh_text)), \
        "install.sh must place venv at /opt/binh-an-hmi/venv (or via VENV_DIR variable)"


# ---------------------------------------------------------------------------
# pip install
# ---------------------------------------------------------------------------

def test_install_sh_pip_install(install_sh_text):
    """Script runs pip install using requirements-pi.txt."""
    assert re.search(r"pip.*install.*requirements-pi\.txt", install_sh_text), \
        "install.sh must run 'pip install -r requirements-pi.txt'"


# ---------------------------------------------------------------------------
# Idempotency guard
# ---------------------------------------------------------------------------

def test_install_sh_idempotent(install_sh_text):
    """Script has idempotency guard — checks venv/gclib existence before creating."""
    # Venv existence check
    assert re.search(r"if.*!.*-d.*VENV_DIR|if.*!.*-d.*venv", install_sh_text), \
        "install.sh must check if venv exists before creating it"
    # gclib existence check
    assert re.search(r"dpkg.*-l.*gclib|dpkg.*gclib", install_sh_text, re.IGNORECASE), \
        "install.sh must check if gclib is already installed"


# ---------------------------------------------------------------------------
# Screen blanking disable
# ---------------------------------------------------------------------------

def test_install_sh_screen_blanking(install_sh_text):
    """Script disables screen blanking via raspi-config."""
    assert re.search(r"do_blanking\s+1", install_sh_text), \
        "install.sh must disable screen blanking via 'raspi-config nonint do_blanking 1'"


# ---------------------------------------------------------------------------
# SSH enable
# ---------------------------------------------------------------------------

def test_install_sh_ssh(install_sh_text):
    """Script enables SSH service."""
    assert re.search(r"systemctl\s+enable\s+ssh|raspi-config.*do_ssh", install_sh_text), \
        "install.sh must enable SSH (via systemctl or raspi-config)"


# ---------------------------------------------------------------------------
# Desktop shortcut
# ---------------------------------------------------------------------------

def test_install_sh_desktop_shortcut(install_sh_text):
    """Script copies .desktop file to ~/Desktop/ and /usr/share/applications/."""
    assert re.search(r"binh-an-hmi\.desktop", install_sh_text), \
        "install.sh must reference binh-an-hmi.desktop"
    assert "/usr/share/applications" in install_sh_text, \
        "install.sh must copy .desktop to /usr/share/applications/"
    assert re.search(r"Desktop.*binh-an-hmi\.desktop|binh-an-hmi\.desktop.*Desktop",
                     install_sh_text), \
        "install.sh must copy .desktop file to user's ~/Desktop/"


# ---------------------------------------------------------------------------
# Reboot countdown
# ---------------------------------------------------------------------------

def test_install_sh_reboot(install_sh_text):
    """Script ends with a reboot countdown."""
    assert "reboot" in install_sh_text, \
        "install.sh must end with a reboot command"
    assert re.search(r"sleep\s+1|seq\s+10", install_sh_text), \
        "install.sh must have a countdown before rebooting"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def test_install_sh_log_file(install_sh_text):
    """Script defines LOG_FILE and redirects output to it."""
    assert "LOG_FILE" in install_sh_text, \
        "install.sh must define a LOG_FILE variable"
    assert re.search(r"tee\s+-a.*LOG_FILE|tee.*\$LOG_FILE", install_sh_text), \
        "install.sh must redirect output to LOG_FILE via tee"


# ---------------------------------------------------------------------------
# Plan 01 artifact checks (no install.sh fixture needed)
# ---------------------------------------------------------------------------

def test_requirements_pi_txt_contains_kivy():
    """requirements-pi.txt (from Plan 01) contains kivy."""
    assert REQUIREMENTS.exists(), f"requirements-pi.txt not found at {REQUIREMENTS}"
    text = REQUIREMENTS.read_text(encoding="utf-8")
    assert "kivy" in text.lower(), "requirements-pi.txt must contain 'kivy'"
    assert "gclib" in text.lower(), "requirements-pi.txt must contain 'gclib'"


def test_desktop_file_fields():
    """binh-an-hmi.desktop (from Plan 01) has required Freedesktop fields."""
    assert DESKTOP_FILE.exists(), f"binh-an-hmi.desktop not found at {DESKTOP_FILE}"
    text = DESKTOP_FILE.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in text, ".desktop file must have [Desktop Entry] section"
    assert "Type=Application" in text, ".desktop file must have Type=Application"
    assert "Exec=" in text, ".desktop file must have Exec= field"
    assert "Icon=" in text, ".desktop file must have Icon= field"
    assert "Terminal=false" in text, ".desktop file must have Terminal=false"
