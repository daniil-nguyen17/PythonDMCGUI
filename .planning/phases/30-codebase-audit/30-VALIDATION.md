---
phase: 30
slug: codebase-audit
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-04
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (already in dev deps) |
| **Config file** | pyproject.toml — `[tool.pytest.ini_options]` section |
| **Quick run command** | `ruff check src/ && pytest tests/ -x -q` |
| **Full suite command** | `ruff check src/ && vulture src/ .vulture_allowlist.py --min-confidence 80 && pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `ruff check src/ && pytest tests/ -x -q`
- **After every plan wave:** Run `ruff check src/ && vulture src/ .vulture_allowlist.py --min-confidence 80 && pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 30-01-01 | 01 | 1 | AUDIT-01, AUDIT-02 | smoke | `ruff check src/` | ❌ W0 | ⬜ pending |
| 30-01-02 | 01 | 1 | AUDIT-01 | smoke | `vulture src/ .vulture_allowlist.py --min-confidence 80` | ❌ W0 | ⬜ pending |
| 30-02-01 | 02 | 2 | AUDIT-02 | smoke | `ruff check --select I src/` | ✅ (via ruff config) | ⬜ pending |
| 30-02-02 | 02 | 2 | AUDIT-04 | smoke | `ruff check --select N src/` | ✅ (via ruff config) | ⬜ pending |
| 30-03-01 | 03 | 3 | AUDIT-03 | unit | `pytest tests/test_docstrings.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — add `[tool.ruff]` and `[tool.ruff.lint]` config sections + add ruff and vulture to dev deps
- [ ] `.vulture_allowlist.py` — auto-generated at repo root from KV file scanner
- [ ] `scripts/gen_vulture_allowlist.py` — KV reference extraction script
- [ ] `tests/test_lint.py` — CI gate that runs ruff and vulture as subprocess calls
- [ ] `tests/test_docstrings.py` — docstring coverage verification

*Wave 0 creates the tooling infrastructure before any code changes.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docstrings accurately describe current behavior | AUDIT-03 | Content accuracy requires human review | Spot-check 5 random docstrings against actual implementation |
| Borderline dead code correctly identified | AUDIT-01 | Judgment call on "borderline" | Review all `# DEAD_CODE` comments for correctness |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
