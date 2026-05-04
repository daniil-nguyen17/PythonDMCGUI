"""CI gate: ruff and vulture checks as pytest test cases.

Failing either check means the codebase has lint or dead-code violations
that must be fixed before merging.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = str(REPO_ROOT / "src")
VULTURE_ALLOWLIST = str(REPO_ROOT / ".vulture_allowlist.py")


def _run(*args: str) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(
        [sys.executable, "-m", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def test_ruff_check() -> None:
    """ruff check src/ must exit 0 — no lint violations allowed."""
    result = _run("ruff", "check", SRC_DIR)
    if result.returncode != 0:
        print("ruff stdout:\n", result.stdout)
        print("ruff stderr:\n", result.stderr)
    assert result.returncode == 0, (
        f"ruff check found violations:\n{result.stdout}{result.stderr}"
    )


def test_vulture_check() -> None:
    """vulture must exit 0 — no dead code at 80% confidence."""
    result = _run(
        "vulture",
        SRC_DIR,
        VULTURE_ALLOWLIST,
        "--min-confidence", "80",
    )
    if result.returncode != 0:
        print("vulture stdout:\n", result.stdout)
        print("vulture stderr:\n", result.stderr)
    assert result.returncode == 0, (
        f"vulture found dead code:\n{result.stdout}{result.stderr}"
    )
