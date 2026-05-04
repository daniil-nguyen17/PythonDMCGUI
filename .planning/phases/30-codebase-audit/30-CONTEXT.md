# Phase 30: Codebase Audit - Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove dead code, standardize imports and naming, add docstrings across all modules. The codebase passes ruff and vulture clean with zero violations. This is a health phase — no behavioral changes, no new features.

**Critical constraint:** The codebase is the source of truth. Working features are preserved even if not documented in supporting .md files. The roadmap and docs are somewhat outdated — the audit does NOT remove code just because it's undocumented.

</domain>

<decisions>
## Implementation Decisions

### Docstring scope and style
- Google-style docstrings (summary + Args/Returns/Raises sections)
- All public classes and functions require docstrings
- Private methods with non-obvious logic (state machines, DMC protocol, complex callbacks) also get docstrings
- Kivy callback methods referenced from .kv files are treated as public — they get docstrings
- Class docstrings are developer-facing: describe what the class does and how it integrates, not what the user sees

### Dead code handling
- Vulture at 80% confidence threshold (matches ROADMAP.md success criteria)
- Auto-generate allowlist from .kv files — parse all .kv files, extract method/property references, generate `.vulture_allowlist.py`
- Audit both .py AND .kv files — orphaned KV rules (no matching Python class) are flagged as dead UI code
- Borderline code: comment out with `# DEAD_CODE` marker, don't delete. Clean removal in next milestone if nothing breaks
- No exceptions — all files go through the same pipeline, no sacred modules
- Codebase is truth: if a feature works and is reachable at runtime, it stays regardless of documentation state
- Ruff config lives in pyproject.toml, vulture allowlist as separate `.vulture_allowlist.py` file
- Add ruff and vulture to `[project.optional-dependencies] dev` group

### Naming conventions
- Logger variable standardized to `logger` (rename controller.py's `log` to `logger`)
- Enforce snake_case for functions/variables, PascalCase for classes via ruff N-rules
- `dmc_vars.py` is exempt from naming rules — DMC variable names are a hardware contract (8-char camelCase names must match controller exactly)
- Kivy properties follow regular snake_case — no special suffix or prefix

### Ruff rule selection
- Standard rule set: E (errors) + F (pyflakes) + I (isort) + N (naming) + W (warnings)
- Line length: 120 characters
- Import ordering: stdlib -> third-party -> local, blank line between groups
- Auto-fix safe rules (import sorting, unused import removal, whitespace). Manually review unsafe fixes
- Config lives in `[tool.ruff]` section of pyproject.toml

### Claude's Discretion
- Specific ruff rule exceptions/ignores for Kivy patterns (e.g., unused `app` import in kv-loading modules)
- Order of operations within the audit (imports first vs dead code first)
- How to structure the allowlist generation script
- Whether to add a `make lint` or similar developer convenience command

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pyproject.toml`: Already has `[tool.pytest.ini_options]` — ruff config will extend this file naturally
- `dmc_vars.py`: Hardware contract module — exempt from naming enforcement
- 44 Python source files, ~8,200 lines — manageable single-pass audit

### Established Patterns
- Logger pattern: `logger = logging.getLogger(__name__)` used in 10/11 files (one outlier: controller.py uses `log`)
- Import style: Mixed — some files group correctly, others don't. No enforced ordering exists
- Machine-specific screens: Flat Grind, Serration, Convex each in their own subpackage under `screens/`
- Base class pattern: `screens/base.py` defines shared lifecycle hooks

### Integration Points
- `pyproject.toml` — ruff and vulture config added here and in dev deps
- `.vulture_allowlist.py` — new file at repo root, auto-generated from .kv references
- All 44 `.py` files touched for import ordering and potentially docstrings
- All `.kv` files scanned for cross-reference with Python classes

</code_context>

<specifics>
## Specific Ideas

- "The codebase is the priority version. Supporting .md files are somewhat outdated." — Do not use roadmap/docs as the arbiter of what's dead. If code runs and is reachable, it lives.
- Borderline dead code gets `# DEAD_CODE` comment-out, not deletion — safe to clean up next milestone after confirming nothing breaks.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 30-codebase-audit*
*Context gathered: 2026-05-04*
