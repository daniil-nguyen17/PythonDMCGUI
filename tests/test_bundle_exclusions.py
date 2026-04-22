"""Content-inspection tests for Windows and Pi deployment bundle exclusions.

All tests read source files (BinhAnHMI.spec, install.sh) as plain text and
assert that non-runtime files are excluded from both deployment packages.
Tests do NOT build actual bundles — they verify the artifact source.

Covers APP-03: packages contain only runtime files.
"""
import pathlib
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / "deploy" / "windows" / "BinhAnHMI.spec"
INSTALL_SH = REPO_ROOT / "deploy" / "pi" / "install.sh"


@pytest.fixture(scope="module")
def spec_text():
    """Return the full BinhAnHMI.spec contents as a string."""
    return SPEC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def install_sh_text():
    """Return the full install.sh contents as a string."""
    return INSTALL_SH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Windows spec tests — datas= block must not include non-runtime files
# ---------------------------------------------------------------------------

def test_spec_datas_no_md_files(spec_text):
    """No .md file should be listed in the spec datas= block.

    The spec only bundles explicitly listed files, so this confirms no
    markdown was accidentally added as a data entry.
    """
    # Extract datas block: from 'datas=[' up to the closing '],'
    start = spec_text.find("datas=[")
    assert start != -1, "Could not find 'datas=[' in spec file"
    end = spec_text.find("],", start)
    assert end != -1, "Could not find closing '],' for datas= block in spec file"
    datas_block = spec_text[start:end]

    assert ".md" not in datas_block, (
        "BinhAnHMI.spec datas= block must not include any .md files — "
        "only runtime assets (kv, ttf, images) should be bundled"
    )


def test_spec_datas_no_xlsx_or_dmc(spec_text):
    """No .xlsx or .dmc file should appear in the spec datas= block.

    .xlsx are customer measurement data files; .dmc are controller source
    programs — neither belongs in the Windows application bundle.
    """
    start = spec_text.find("datas=[")
    assert start != -1, "Could not find 'datas=[' in spec file"
    end = spec_text.find("],", start)
    assert end != -1, "Could not find closing '],' for datas= block in spec file"
    datas_block = spec_text[start:end]

    assert ".xlsx" not in datas_block, (
        "BinhAnHMI.spec datas= block must not include any .xlsx files"
    )
    assert ".dmc" not in datas_block, (
        "BinhAnHMI.spec datas= block must not include any .dmc files"
    )


def test_spec_datas_no_planning_or_tests(spec_text):
    """No .planning/ or tests/ directory should appear in the spec datas= block.

    These are development directories, not runtime artifacts.
    """
    start = spec_text.find("datas=[")
    assert start != -1, "Could not find 'datas=[' in spec file"
    end = spec_text.find("],", start)
    assert end != -1, "Could not find closing '],' for datas= block in spec file"
    datas_block = spec_text[start:end]

    assert ".planning" not in datas_block, (
        "BinhAnHMI.spec datas= block must not include .planning/ directory"
    )
    assert "tests/" not in datas_block, (
        "BinhAnHMI.spec datas= block must not include tests/ directory"
    )


# ---------------------------------------------------------------------------
# Pi install.sh tests — rsync --exclude patterns must be present
# ---------------------------------------------------------------------------

def test_install_sh_excludes_md(install_sh_text):
    """install.sh rsync must exclude all markdown files.

    Markdown files (README, planning docs) are not needed at runtime on Pi.
    """
    assert "--exclude='*.md'" in install_sh_text, (
        "install.sh rsync must include --exclude='*.md' to strip markdown files "
        "from the Pi deployment at /opt/binh-an-hmi/"
    )


def test_install_sh_excludes_xlsx_dmc(install_sh_text):
    """install.sh rsync must exclude .xlsx and .dmc files.

    .xlsx are customer measurement data; .dmc are DMC controller programs
    loaded directly onto the controller, not needed in the app directory.
    """
    assert "--exclude='*.xlsx'" in install_sh_text, (
        "install.sh rsync must include --exclude='*.xlsx'"
    )
    assert "--exclude='*.dmc'" in install_sh_text, (
        "install.sh rsync must include --exclude='*.dmc'"
    )


def test_install_sh_excludes_dev_dirs(install_sh_text):
    """install.sh rsync must exclude .claude/, .planning/, and tests/ directories.

    These are development-only directories that have no role in Pi runtime operation.
    """
    assert "--exclude='.claude/'" in install_sh_text, (
        "install.sh rsync must include --exclude='.claude/' "
        "to strip the Claude config directory from the Pi deployment"
    )
    assert "--exclude='.planning/'" in install_sh_text, (
        "install.sh rsync must include --exclude='.planning/'"
    )
    assert "--exclude='tests/'" in install_sh_text, (
        "install.sh rsync must include --exclude='tests/'"
    )
