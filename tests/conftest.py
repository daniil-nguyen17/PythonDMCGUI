import os
import sys


def pytest_sessionstart(session):  # noqa: ARG001
    # Ensure src is on path for development runs
    root = os.path.dirname(os.path.dirname(__file__))
    src = os.path.join(root, "src")
    if src not in sys.path:
        sys.path.insert(0, src)

