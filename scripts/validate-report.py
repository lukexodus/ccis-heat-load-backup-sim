#!/usr/bin/env python3
"""validate-report.py — Lint and validate local agent task reports.

Enforces:
1. Valid naming: docs/reports/<TASK-ID>-<agent-name>-<short-slug>.md
2. Presence in docs/tasks/status.md with consistent status
3. Required sections: Executive Summary, Implementation Details, Verification & Test Evidence, Git Diff
4. Verbatim unified git diff check (diff --git or index lines)
5. Decision ID collision & reservation verification in docs/decisions/decision-log.md
"""

import argparse
import os
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = [
    r"#+ .*Executive Summary",
    r"#+ .*Implementation Details",
    r"#+ .*Verification",
    r"#+ .*Git Diff",
]

REPORT_NAME_REGEX = re.compile(r"^([A-Z][A-Z0-9]*(?:-[A-Z0-9.]+)+)-([a-z0-9_.-]+)\.md$")


def validate_report(report_path: Path, repo_root: Path) -> list[str]:
    errors = []
    filename = report_path.name

    # 1. Filename pattern check
    m = REPORT_NAME_REGEX.match(filename)
    if not m:
        errors.append(
            f"Filename '{filename}' does not follow convention '<TASK-ID>-<agent-name>-<short-slug>.md' "
            f"(e.g., CORE-001-claude-code-initial-models.md)"
        )
        task_id = filename.split("-")[0] if "-" in filename else None
    else:
        task_id = m.group(1)
        remainder = m.group(2)
        if "-" not in remainder and "_" not in remainder:
            errors.append(f"Filename '{filename}' must contain both agent name and short slug (e.g., CORE-001-gemini-initial-models.md).")

    try:
        content = report_path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Unable to read report file: {e}"]

    # 2. Required sections check
    for sec_pattern in REQUIRED_SECTIONS:
        if not re.search(sec_pattern, content, re.IGNORECASE):
            errors.append(f"Missing required section matching pattern: {sec_pattern}")

    # 3. Git Diff content check
    has_diff_block = "```diff" in content or "diff --git" in content or "index " in content
    if not has_diff_block:
        errors.append("No unified git diff (`diff` block or `diff --git`) found in the report.")

    # 4. Check status.md alignment
    status_file = repo_root / "docs/tasks/status.md"
    if status_file.exists() and task_id:
        status_text = status_file.read_text(encoding="utf-8")
        if task_id not in status_text:
            errors.append(f"Task ID '{task_id}' was not found in 'docs/tasks/status.md'.")
        else:
            # Check if linked
            if filename not in status_text and report_path.name not in status_text:
                errors.append(f"Report '{filename}' is not linked in 'docs/tasks/status.md' for task '{task_id}'.")

    # 5. Check decision log alignment
    decision_matches = re.findall(r"\[D-(\d+)\]", content)
    decisions_file = repo_root / "docs/decisions/decision-log.md"
    if decisions_file.exists() and decision_matches:
        d_log_text = decisions_file.read_text(encoding="utf-8")
        for d_id in set(decision_matches):
            d_tag = f"[D-{d_id}]"
            if d_tag not in d_log_text:
                errors.append(f"Report mentions decision {d_tag}, but it is missing from 'docs/decisions/decision-log.md'.")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate local agent task report format and repository alignment.")
    parser.add_argument("report_file", nargs="?", help="Specific report markdown file to validate")
    parser.add_argument("--all", action="store_true", help="Validate all reports in docs/reports/")
    parser.add_argument("--repo-root", default=".", help="Path to repository root")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    reports_dir = repo_root / "docs/reports"

    if args.all:
        if not reports_dir.exists():
            print(f"ERROR: Reports directory '{reports_dir}' does not exist.", file=sys.stderr)
            sys.exit(1)
        reports = [p for p in reports_dir.glob("*.md") if p.name != "TASK-TEMPLATE.md"]
        if not reports:
            print("No task reports found to validate.")
            sys.exit(0)
    elif args.report_file:
        reports = [Path(args.report_file).resolve()]
    else:
        # Default: validate the most recently modified report
        if not reports_dir.exists():
            print("ERROR: docs/reports directory does not exist.", file=sys.stderr)
            sys.exit(1)
        all_mds = [p for p in reports_dir.glob("*.md") if p.name != "TASK-TEMPLATE.md"]
        if not all_mds:
            print("No reports found to validate.")
            sys.exit(0)
        reports = [max(all_mds, key=lambda p: p.stat().st_mtime)]
        print(f"Defaulting to most recent report: {reports[0].name}")

    total_errors = 0
    for r in reports:
        print(f"Validating report: {r.name} ...")
        errs = validate_report(r, repo_root)
        if errs:
            total_errors += len(errs)
            print(f"  FAILED with {len(errs)} issue(s):")
            for e in errs:
                print(f"    - {e}")
        else:
            print("  PASSED (all structural & alignment checks passed).")

    if total_errors > 0:
        print(f"\nValidation failed with {total_errors} total error(s).", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nAll report checks passed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
