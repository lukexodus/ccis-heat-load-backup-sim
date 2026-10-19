# Standalone Task Prompt: ARCH-002

Copy and paste the text block below into a local agent session (Claude Code, Gemini CLI, Cursor, opencode):

```markdown
# TASK: ARCH-002 — Scaffold Repository, Toolchain, Linting & Baseline Test Harness

## Role & Worktree Instructions
- **Assigned Agent:** any (lead implementation / tooling agent)
- **Task ID:** ARCH-002
- **Branch / Worktree:** If running concurrently with ARCH-001 or another task, use a dedicated worktree:
  `./scripts/task-worktree.sh start ARCH-002`
  (or `git worktree add ../ccis-heat-load-backup-sim-ARCH-002 -b task/ARCH-002`)

## Orientation & Required Reading
Before writing any code, inspect these repository files in order:
1. `docs/context/complete-context.md` — project background and coordination model
2. `docs/tasks/status.md` — confirm ARCH-002 is open
3. `docs/decisions/decision-log.md` — review past decisions [D-01] through [D-11], especially [D-04] (Python stack)
4. `AGENTS.md` — operational rules, test verification, and delta reporting

## Context & Objectives
This task establishes the technical foundation for the CCIS Heat, Load and Backup Power Simulation (Project Outline §5). You will create the Python project structure, dependency declarations, package directories, linting configuration, and a clean baseline test suite so that subsequent Phase 1 tasks (`CORE-001` through `CORE-005`) can implement domain models against a green test runner.

## Specific Scope & Deliverables
1. **Dependency & Packaging Files:**
   - Create `requirements.txt` with locked major dependencies:
     ```text
     pandas>=2.0.0
     numpy>=1.24.0
     scipy>=1.10.0
     matplotlib>=3.7.0
     pytest>=7.4.0
     ruff>=0.1.0
     ```
   - Create `pyproject.toml` with:
     - Project metadata: name = "ccis-sim", version = "0.1.0", requires-python = ">=3.10"
     - `[tool.pytest.ini_options]` testpaths = ["tests"]
     - `[tool.ruff]` line-length = 100, target-version = "py310"

2. **Package Layout (`src/ccis_sim/`):**
   Create package directories with docstrings in `__init__.py`:
   - `src/ccis_sim/__init__.py` (defines `__version__ = "0.1.0"`)
   - `src/ccis_sim/core/__init__.py` (domain entities, state records, invariants)
   - `src/ccis_sim/demand/__init__.py` (bottom-up equipment audit & CDD cooling model)
   - `src/ccis_sim/solar/__init__.py` (irradiance, NOCT thermal derating, PV yield)
   - `src/ccis_sim/battery/__init__.py` (LFP storage dispatch, SoC recursion, reserves)
   - `src/ccis_sim/outage/__init__.py` (Poisson/Lognormal outage generator & load-shedding)
   - `src/ccis_sim/integration/__init__.py` (engine loop, CLI driver, Monte Carlo sweeps)
   - `src/ccis_sim/decision/__init__.py` (AHP multi-criteria scoring & sizing optimization)

3. **Data Directories:**
   - `data/fixtures/.gitkeep` (for committed offline weather & equipment CSV fixtures)
   - `data/raw/.gitkeep` (for raw downloaded NASA POWER queries)

4. **Smoke Test Baseline:**
   - Create `tests/__init__.py`
   - Create `tests/test_smoke.py`:
     - Test that `ccis_sim` is importable and has version `"0.1.0"`.
     - Test numpy/scipy environment sanity (e.g. array creation, normal CDF).
     - Test that package submodules are importable.

5. **Regenerate Repository Tree:**
   - Update `docs/context/repo-tree.txt` to capture the new directory structure.

## What NOT to Touch
- Do not implement domain logic or feature models yet (those belong to CORE-001..003).
- Do not modify `docs/context/complete-context.md` or `docs/decisions/decision-log.md`.

## Verification & Acceptance Criteria
- [ ] `requirements.txt` and `pyproject.toml` created.
- [ ] All package directories created with valid Python package `__init__.py` files.
- [ ] `pytest` passes with 100% success on `tests/test_smoke.py`.
- [ ] `docs/context/repo-tree.txt` updated to reflect the new structure.
- [ ] Report created at `docs/reports/ARCH-002-[agent]-repo-scaffolding.md` and passes `./scripts/validate-report.py`.
- [ ] `docs/tasks/status.md` updated for ARCH-002 and its subtasks.
```
