# Helper Scripts Guide — CCIS Heat, Load and Backup Power Simulation

This directory contains automation utilities that enforce the APC + Local Agent operational protocol.
All scripts provide dual **Linux/macOS** (`.sh` / Python) and **Windows** (`.bat` / `.ps1`) support with 100% feature parity.

---

## Quick Reference by Platform

| Utility | Linux / macOS / Git Bash | Windows Command Prompt (CMD) | Windows PowerShell |
| :--- | :--- | :--- | :--- |
| **APC Bundle** | `./scripts/apc-bundle.sh` | `.\scripts\apc-bundle.bat` | `.\scripts\apc-bundle.ps1` |
| **Task Worktree** | `./scripts/task-worktree.sh` | `.\scripts\task-worktree.bat` | `.\scripts\task-worktree.ps1` |
| **Validate Report** | `./scripts/validate-report.py` | `.\scripts\validate-report.bat` | `.\scripts\validate-report.ps1` |
| **Manage Decisions** | `./scripts/manage-decisions.py` | `.\scripts\manage-decisions.bat` | `.\scripts\manage-decisions.ps1` |

---

## 1. `apc-bundle` (`apc-bundle.sh` / `apc-bundle.bat` / `apc-bundle.ps1`) — Context Packaging Utility

Packages repository files into self-describing, verifiable `.tar.gz` archives for upload to the external APC AI session.

### Common Commands:
```bash
# Linux / macOS:
./scripts/apc-bundle.sh --list
./scripts/apc-bundle.sh --tokens
./scripts/apc-bundle.sh core
./scripts/apc-bundle.sh dev --add path/to/extra-file.py
./scripts/apc-bundle.sh --with-reports

# Windows CMD:
.\scripts\apc-bundle.bat --list
.\scripts\apc-bundle.bat --tokens
.\scripts\apc-bundle.bat core
.\scripts\apc-bundle.bat dev --add path\to\extra-file.py
.\scripts\apc-bundle.bat --with-reports

# Windows PowerShell:
.\scripts\apc-bundle.ps1 -List
.\scripts\apc-bundle.ps1 -Tokens
.\scripts\apc-bundle.ps1 core
.\scripts\apc-bundle.ps1 dev -Add path/to/extra-file.py
.\scripts\apc-bundle.ps1 -WithReports
```

### Safety Features:
- Aborts on missing files.
- Automatically excludes secrets (`.env*`, `*.key`, `*.pem`, `*secret*`, `*token*`).
- Excludes large build and artifact folders (`.git/`, `.venv/`, `node_modules/`, `dist/`).
- Generates `MANIFEST.txt` with SHA256 hashes, timestamps, and git status.

---

## 2. `task-worktree` (`task-worktree.sh` / `task-worktree.bat` / `task-worktree.ps1`) — Worktree Lifecycle Helper

Enforces worktree isolation when running multiple local agents or tasks in parallel.

### Common Commands:
```bash
# Linux / macOS:
./scripts/task-worktree.sh start CORE-001
./scripts/task-worktree.sh list
./scripts/task-worktree.sh status CORE-001
./scripts/task-worktree.sh diff CORE-001
./scripts/task-worktree.sh handoff CORE-001
./scripts/task-worktree.sh merge CORE-001
./scripts/task-worktree.sh remove CORE-001

# Windows CMD:
.\scripts\task-worktree.bat start CORE-001
.\scripts\task-worktree.bat list
.\scripts\task-worktree.bat status CORE-001
.\scripts\task-worktree.bat diff CORE-001
.\scripts\task-worktree.bat handoff CORE-001
.\scripts\task-worktree.bat merge CORE-001
.\scripts\task-worktree.bat remove CORE-001

# Windows PowerShell:
.\scripts\task-worktree.ps1 start CORE-001
.\scripts\task-worktree.ps1 list
.\scripts\task-worktree.ps1 status CORE-001
.\scripts\task-worktree.ps1 diff CORE-001
.\scripts\task-worktree.ps1 handoff CORE-001
.\scripts\task-worktree.ps1 merge CORE-001
.\scripts\task-worktree.ps1 remove CORE-001
```

---

## 3. `validate-report` (`validate-report.py` / `validate-report.bat` / `validate-report.ps1`) — Report Linter & Verification

Verifies that local agent task reports conform to the required schema, match `docs/tasks/status.md`, and contain valid unified git diffs.

### Common Commands:
```bash
# Linux / macOS:
./scripts/validate-report.py
./scripts/validate-report.py docs/reports/CORE-001-agent-title.md
./scripts/validate-report.py --all

# Windows CMD:
.\scripts\validate-report.bat
.\scripts\validate-report.bat docs\reports\CORE-001-agent-title.md
.\scripts\validate-report.bat --all

# Windows PowerShell:
.\scripts\validate-report.ps1
.\scripts\validate-report.ps1 docs/reports/CORE-001-agent-title.md
.\scripts\validate-report.ps1 --all
```

---

## 4. `manage-decisions` (`manage-decisions.py` / `manage-decisions.bat` / `manage-decisions.ps1`) — Decision ID Allocator & Log Inspector

Prevents decision ID collisions when multiple parallel worktrees operate concurrently.

### Common Commands:
```bash
# Linux / macOS:
./scripts/manage-decisions.py next
./scripts/manage-decisions.py list
./scripts/manage-decisions.py check --id 42
./scripts/manage-decisions.py reserve --title "Select PostgreSQL over SQLite"

# Windows CMD:
.\scripts\manage-decisions.bat next
.\scripts\manage-decisions.bat list
.\scripts\manage-decisions.bat check --id 42
.\scripts\manage-decisions.bat reserve --title "Select PostgreSQL over SQLite"

# Windows PowerShell:
.\scripts\manage-decisions.ps1 next
.\scripts\manage-decisions.ps1 list
.\scripts\manage-decisions.ps1 check --id 42
.\scripts\manage-decisions.ps1 reserve --title "Select PostgreSQL over SQLite"
```
