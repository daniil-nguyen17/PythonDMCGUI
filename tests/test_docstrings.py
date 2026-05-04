"""Automated docstring coverage gate for AUDIT-03.

Uses the ``ast`` module to parse every .py file in src/dmccodegui/ and
verify that all public classes, public methods/functions, and non-obvious
private methods have non-empty docstrings.

Exclusions
----------
- ``__init__.py``   — often empty or re-exports only
- ``__main__.py``   — trivial entry point
- ``dmc_vars.py``   — module-level constants, no classes/functions needing
                      per-def docstrings beyond the module docstring

Coverage rules
--------------
1. All top-level class definitions (public by definition)
2. All methods/functions whose name does NOT start with ``_``
3. All methods/functions starting with ``on_`` (Kivy event callbacks,
   treated as public per project convention)
4. Private methods with a body of >15 lines (non-obvious logic)

Inner closures (nested functions inside other functions) are excluded —
they are implementation details of their enclosing function.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SRC_ROOT = Path(__file__).parent.parent / "src" / "dmccodegui"

# Files excluded from per-definition docstring checks
_EXCLUDED_FILES = frozenset({"__init__.py", "__main__.py", "dmc_vars.py"})


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def _body_line_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Return the approximate number of lines in a function/method body."""
    if not node.body:
        return 0
    first = node.body[0]
    last = node.body[-1]
    first_line = getattr(first, "lineno", 0)
    last_line = getattr(last, "end_lineno", getattr(last, "lineno", first_line))
    return max(0, last_line - first_line)


def _is_non_obvious_private(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if this private method is considered non-obvious (>15-line body)."""
    name = node.name
    if not name.startswith("_"):
        return False
    if name.startswith("__") and name.endswith("__"):
        return False  # dunders excluded
    return _body_line_count(node) > 15


def _should_have_docstring(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Decide whether this function/method node requires a docstring."""
    name = node.name
    # Dunder methods: skip (too noisy, usually self-explanatory)
    if name.startswith("__") and name.endswith("__"):
        return False
    # Public (no leading underscore) or Kivy on_* callback
    if not name.startswith("_") or name.startswith("on_"):
        return True
    # Non-obvious private (>15 lines body)
    return _is_non_obvious_private(node)


def _get_docstring(node: ast.AST) -> str | None:
    """Return the docstring of an AST node, or None if absent/empty."""
    try:
        doc = ast.get_docstring(node)
        if doc and doc.strip():
            return doc
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Walking — only top-level module defs and direct class members
# Inner closures (functions nested inside other functions) are excluded.
# ---------------------------------------------------------------------------

def _walk_file(filepath: Path) -> list[tuple[str, str, int, str]]:
    """Return [(filepath_str, name, lineno, kind)] for every def missing a docstring.

    kind is one of: 'class', 'function', 'method'

    Only inspects:
    - Top-level classes (direct children of module)
    - Top-level functions (direct children of module)
    - Methods that are direct children of a class body

    Skips inner closures (nested functions inside other functions) intentionally.
    """
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return []

    file_str = str(filepath)
    gaps: list[tuple[str, str, int, str]] = []
    seen: set[tuple[str, int]] = set()  # deduplicate by (name, lineno)

    def _add(name: str, lineno: int, kind: str) -> None:
        key = (name, lineno)
        if key not in seen:
            seen.add(key)
            gaps.append((file_str, name, lineno, kind))

    # Top-level nodes: classes and functions (direct children of Module)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            if _get_docstring(node) is None:
                _add(node.name, node.lineno, "class")

            # Methods: direct children of the class body only (no inner closures)
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if _should_have_docstring(child):
                        if _get_docstring(child) is None:
                            _add(
                                f"{node.name}.{child.name}",
                                child.lineno,
                                "method",
                            )

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _should_have_docstring(node):
                if _get_docstring(node) is None:
                    _add(node.name, node.lineno, "function")

    return gaps


def _collect_all_gaps() -> list[tuple[str, str, int, str]]:
    """Walk all non-excluded .py files under SRC_ROOT and collect docstring gaps."""
    gaps: list[tuple[str, str, int, str]] = []
    for dirpath, _dirs, filenames in os.walk(SRC_ROOT):
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            if filename in _EXCLUDED_FILES:
                continue
            filepath = Path(dirpath) / filename
            gaps.extend(_walk_file(filepath))
    return gaps


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_docstring_coverage():
    """Assert that all required definitions have non-empty docstrings.

    On failure, prints a formatted list of every missing docstring including
    the relative file path, definition name, and line number.
    """
    gaps = _collect_all_gaps()

    if not gaps:
        return  # All good

    # Format the report
    lines = [
        "",
        f"DOCSTRING COVERAGE FAILURES: {len(gaps)} missing",
        "=" * 70,
    ]
    for filepath, name, lineno, kind in sorted(gaps, key=lambda g: (g[0], g[2])):
        # Make path relative to project root for readability
        try:
            rel = Path(filepath).relative_to(SRC_ROOT.parent.parent)
        except ValueError:
            rel = Path(filepath)
        lines.append(f"  [{kind:8}] {rel}:{lineno}  {name}()")

    lines.append("=" * 70)
    report = "\n".join(lines)

    # Print to stderr so pytest -s shows full detail
    print(report, file=sys.stderr)

    assert not gaps, report
