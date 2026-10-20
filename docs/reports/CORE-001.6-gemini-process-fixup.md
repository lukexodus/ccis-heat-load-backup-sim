# Task Report: CORE-001.6 — Process & Reporting Hygiene Fix-up

**Date:** 2026-10-20  
**Agent:** gemini  
**Task ID:** CORE-001.6  
**Status:** done  

---

## 1. Executive Summary

This task executes `CORE-001.6` (Process Correction & Reporting Hygiene), addressing two non-code process items identified by the APC AI during review of the `CORE-001.5` submission:
1. **Unreported Provenance Files in `docs/misc/`:** During the `CORE-001.5` turn, 9 pre-ARCH-001 archival source documents (`M&S Project Ideas.md` and 8 `deep-research-report*.md` files) were staged into the repository from exploratory workspaces without being documented in the task report's "Changes Made" section. These files are valuable provenance artifacts (the historical brainstorming pitch and the 8 deep research topic studies that originally grounded decisions `[D-05]` through `[D-11]`). They have now been formally documented in `docs/context/complete-context.md` §4, indexed with a dedicated `docs/misc/README.md`, and marked with an archival provenance banner in `docs/misc/M&S Project Ideas.md` clarifying that preliminary figures are superseded by the formal decision log and conceptual model.
2. **Self-Referential Patch Artifact Removal:** In the `CORE-001.5` commit, `patch/CORE-001.5-gemini-decision-gap-fixup.patch` was tracked and committed to git, introducing an unwanted self-referential patch artifact in git diffs. The patch file has been removed from git tracking (`git rm`), and `scripts/validate-report.py` was updated to remove the requirement that patch files exist as committed repository artifacts.

No domain models, test logic, or decision log entries were altered.

---

## 2. Implementation Details

### 2.1 Complete List of Files Touched

1. `docs/context/complete-context.md`:
   - Updated directory tree in §4 to include `docs/misc/`.
   - Added an explanatory note documenting that `docs/misc/` preserves pre-ARCH-001 source material for historical provenance and parameter traceability, while `docs/decisions/decision-log.md` and `docs/context/conceptual-model.md` remain the sole authoritative specifications.
2. `docs/misc/README.md`:
   - Created an index and authority disclaimer detailing the 9 archival files and their relation to the 8 deep research synthesis areas.
3. `docs/misc/M&S Project Ideas.md`:
   - Prepend an Archival Provenance Notice banner clarifying that early draft concepts (e.g., real electricity bills, daily time step, simplified battery model) are superseded by `[D-01]`–`[D-18]`.
4. `scripts/validate-report.py`:
   - Removed check #6 that previously enforced patch file presence in `patch/`, conforming to the APC specification that patch files are output formats for diff relay rather than tracked repository artifacts.
5. `patch/CORE-001.5-gemini-decision-gap-fixup.patch`:
   - Removed from repository git tracking via `git rm`.
6. `docs/tasks/status.md`:
   - Appended `CORE-001.6` tracking row under `CORE-001` block, marked `done`.
7. `docs/prompts/CORE-001.6-PROCESS-FIXUP-PROMPT.md`:
   - Standardized prompt filename from `CORE-001.6-PROCESS-FIXUP-standalone-prompt.md`.

---

## 3. Verification & Test Evidence

### 3.1 Verification Commands

1. **Verify `docs/misc/` content and provenance notice:**
   ```bash
   head -n 5 "docs/misc/M&S Project Ideas.md"
   # Output:
   # > [!NOTE]
   # > **Archival Provenance Notice:** This document is an early course brainstorming draft predating project initialization...
   ```

2. **Verify removal of tracked patch file:**
   ```bash
   git ls-files patch/CORE-001.5-gemini-decision-gap-fixup.patch
   # Output: (empty — successfully untracked)
   ```

3. **Verify full test suite integrity:**
   ```bash
   pytest -v
   # Output: 56 passed in 6.55s (100% green across all test suites)
   ```

4. **Verify report suite validation:**
   ```bash
   ./scripts/validate-report.py --all
   # Output: All report checks passed successfully!
   ```

---

## 4. Decisions Recorded

No new decision IDs were reserved or required for this process fixup.

---

## 5. Unified Git Diff

```diff
diff --git a/docs/context/complete-context.md b/docs/context/complete-context.md
index 194fa8d..5a1727c 100644
--- a/docs/context/complete-context.md
+++ b/docs/context/complete-context.md
@@ -61,14 +61,18 @@
 │   ├── decisions/
 │   │   └── decision-log.md     # Append-only immutable architectural decision log
 │   ├── reports/                # Completed task reports (one per task)
-│   └── prompts/                # Standalone prompt archive
+│   ├── prompts/                # Standalone prompt archive
+│   └── misc/                   # Pre-ARCH-001 archival source material & deep research
 ├── scripts/
 │   ├── apc-bundle.sh           # Safe packaging tool for APC context bundles
 │   └── task-worktree.sh        # Git worktree management script for parallel tasks
-├── src                 # Source code
+├── src/                        # Source code (ccis_sim package)
 └── tests/                      # Automated test suites
 ```
 
+> [!NOTE]
+> `docs/misc/` holds pre-ARCH-001 source material (original course project idea document, early deep-research inputs) preserved for historical provenance and parameter traceability. These files are not live specifications — `docs/decisions/decision-log.md` and `docs/context/conceptual-model.md` are the authoritative sources of truth for any decisions originally informed by these materials.
+
 ---
 
 ## 5. The Coordination Model (Why this setup exists)
diff --git a/docs/misc/M&S Project Ideas.md b/docs/misc/M&S Project Ideas.md
index cd8ea43..ab0d014 100644
--- a/docs/misc/M&S Project Ideas.md
+++ b/docs/misc/M&S Project Ideas.md
@@ -1,3 +1,6 @@
+> [!NOTE]
+> **Archival Provenance Notice:** This document is an early course brainstorming draft predating project initialization. Its preliminary descriptions (e.g., real electricity bills, daily time step, simplified battery model) are superseded by the formal decision log (`docs/decisions/decision-log.md`, [D-01]–[D-18]) and the canonical conceptual model (`docs/context/conceptual-model.md`). Kept for historical provenance and traceability.
+
 # **IDEA \#1: CCIS Heat, Load and Backup Power Simulation**
 
 # **1\. Overview**
diff --git a/docs/tasks/status.md b/docs/tasks/status.md
index 29fd6b8..da1d326 100644
--- a/docs/tasks/status.md
+++ b/docs/tasks/status.md
@@ -46,2 +46,3 @@
 | CORE-001.5   | Reconcile uncredited assumptions in Battery & Building ([D-17], [D-18])          | `done` | [CORE-001.5-gemini-decision-gap-fixup.md](../reports/CORE-001.5-gemini-decision-gap-fixup.md) |
+| CORE-001.6   | Process & reporting fixup for provenance files and patch cleanup                 | `done` | [CORE-001.6-gemini-process-fixup.md](../reports/CORE-001.6-gemini-process-fixup.md)           |
diff --git a/scripts/validate-report.py b/scripts/validate-report.py
index afdedec..f24d402 100755
--- a/scripts/validate-report.py
+++ b/scripts/validate-report.py
@@ -82,7 +82,0 @@
-    # 6. Check patch file existence in patch/
-    patch_dir = repo_root / "patch"
-    if patch_dir.exists() and task_id:
-        patch_files = list(patch_dir.glob(f"{task_id}*.patch"))
-        if not patch_files:
-            errors.append(f"No corresponding patch file found in 'patch/' matching '{task_id}*.patch'.")
-
```

---

## 6. Flagged for APC / Operator Attention

- [x] All 9 provenance files in `docs/misc/` are documented and indexed with authority disclaimers.
- [x] Self-referential `patch/CORE-001.5-gemini-decision-gap-fixup.patch` untracked and removed from git.
- [x] `validate-report.py` updated to ensure patches are not required as tracked repo artifacts.
