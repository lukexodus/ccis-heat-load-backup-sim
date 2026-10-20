<#
.SYNOPSIS
    task-worktree.ps1 — Helper script to enforce AGENTS.md worktree rules for parallel tasks on Windows.
.DESCRIPTION
    Run from repository root. PowerShell equivalent of task-worktree.sh.
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command,

    [Parameter(Position = 1)]
    [string]$TaskId
)

$ErrorActionPreference = "Stop"

$repoRoot = (Get-Item -Path ".").FullName
$repoName = Split-Path $repoRoot -Leaf

function Show-Help {
    @"
Usage: .\scripts\task-worktree.ps1 <COMMAND> [TASK_ID]
       .\scripts\task-worktree.bat <COMMAND> [TASK_ID]

Commands:
  start <TASK-ID>   Create a dedicated task worktree at ../<repo>-<TASK-ID> on branch task/<TASK-ID>
  list              List all active worktrees and their current branch
  status <TASK-ID>  Check git status inside the specified task worktree
  diff <TASK-ID>    Output clean unified diff from the worktree with index lines
  handoff <TASK-ID> Validate the worktree state for operator review/commit (does not delete)
  remove <TASK-ID>  Safely remove a worktree (only after operator has merged/committed)
"@
}

if (-not $Command -or $Command -eq "-h" -or $Command -eq "--help") {
    Show-Help
    exit 0
}

function Find-PythonExecutable {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        return @("python3")
    }
    return $null
}

switch ($Command.ToLowerInvariant()) {
    "list" {
        Write-Host "Active Git Worktrees:"
        & git worktree list
        exit 0
    }

    "start" {
        if (-not $TaskId) {
            Write-Error "ERROR: Missing TASK_ID. Example: .\scripts\task-worktree.bat start CORE-001"
            exit 1
        }
        $targetDir = Join-Path (Split-Path $repoRoot -Parent) "${repoName}-${TaskId}"
        $branchName = "task/${TaskId}"

        if (Test-Path $targetDir) {
            Write-Error "ERROR: Worktree directory '$targetDir' already exists."
            exit 1
        }

        Write-Host "Creating dedicated worktree for task $TaskId..."
        & git worktree add "$targetDir" -b "$branchName"
        Write-Host "Worktree successfully created at: $targetDir"
        Write-Host "Branch: $branchName"
        Write-Host "Switch to the worktree directory before starting your local agent."
        exit 0
    }

    "status" {
        if (-not $TaskId) {
            Write-Error "ERROR: Missing TASK_ID."
            exit 1
        }
        $targetDir = Join-Path (Split-Path $repoRoot -Parent) "${repoName}-${TaskId}"
        if (-not (Test-Path $targetDir)) {
            Write-Error "ERROR: Worktree '$targetDir' does not exist."
            exit 1
        }
        & git -C "$targetDir" status --short
        exit 0
    }

    "diff" {
        if (-not $TaskId) {
            Write-Error "ERROR: Missing TASK_ID."
            exit 1
        }
        $targetDir = Join-Path (Split-Path $repoRoot -Parent) "${repoName}-${TaskId}"
        if (-not (Test-Path $targetDir)) {
            Write-Error "ERROR: Worktree '$targetDir' does not exist."
            exit 1
        }
        & git -C "$targetDir" diff
        exit 0
    }

    "handoff" {
        if (-not $TaskId) {
            Write-Error "ERROR: Missing TASK_ID."
            exit 1
        }
        $targetDir = Join-Path (Split-Path $repoRoot -Parent) "${repoName}-${TaskId}"
        if (-not (Test-Path $targetDir)) {
            Write-Error "ERROR: Worktree '$targetDir' does not exist."
            exit 1
        }

        Write-Host "=========================================="
        Write-Host "Worktree Handoff Audit for: $TaskId"
        Write-Host "Directory: $targetDir"
        Write-Host "Branch:    task/$TaskId"
        Write-Host "Git Status & Commit Check:"

        $statusLines = & git -C "$targetDir" status --porcelain
        $dirtyCount = 0
        if ($statusLines) {
            $dirtyCount = ($statusLines | Measure-Object).Count
        }

        if ($dirtyCount -eq 0) {
            Write-Host "  [OK] Working tree clean (changes are committed)"
            $latestCommit = & git -C "$targetDir" log -1 --oneline
            Write-Host "  Latest commit: $latestCommit"
        } else {
            Write-Host "  [WARNING] Worktree has $dirtyCount uncommitted change(s). Please commit your work."
        }

        Write-Host ""
        Write-Host "Patch File Check (in patch/):"
        $patchDir = Join-Path $targetDir "patch"
        $patchFile = $null
        if (Test-Path $patchDir) {
            $patchFile = Get-ChildItem -Path $patchDir -Filter "${TaskId}*.patch" -File -ErrorAction SilentlyContinue | Select-Object -First 1
        }
        if ($patchFile) {
            Write-Host "  [OK] Found patch file: $($patchFile.FullName)"
        } else {
            Write-Host "  [WARNING] No patch file found in patch/ matching ${TaskId}*.patch"
        }

        Write-Host ""
        Write-Host "Report Check:"
        $reportsDir = Join-Path $targetDir "docs/reports"
        $reportFile = $null
        if (Test-Path $reportsDir) {
            $reportFile = Get-ChildItem -Path $reportsDir -Filter "${TaskId}*" -File -ErrorAction SilentlyContinue | Select-Object -First 1
        }

        if ($reportFile) {
            Write-Host "  [OK] Found report file: $($reportFile.FullName)"
            $validatorScript = Join-Path $targetDir "scripts/validate-report.py"
            if (Test-Path $validatorScript) {
                Write-Host "  Running report validator..."
                $pyCmd = Find-PythonExecutable
                if ($pyCmd) {
                    $valArgs = @($validatorScript, $reportFile.FullName, "--repo-root", $targetDir)
                    if ($pyCmd.Count -gt 1) {
                        & $pyCmd[0] $pyCmd[1] @valArgs
                    } else {
                        & $pyCmd[0] @valArgs
                    }
                    if ($LASTEXITCODE -ne 0) {
                        Write-Host "  [WARNING] Report validation returned issues."
                    }
                } else {
                    Write-Host "  [WARNING] Python executable not found to run validator."
                }
            }
        } else {
            Write-Host "  [WARNING] No report file found in docs/reports/ matching $TaskId"
        }
        Write-Host "=========================================="
        exit 0
    }

    "remove" {
        if (-not $TaskId) {
            Write-Error "ERROR: Missing TASK_ID."
            exit 1
        }
        $targetDir = Join-Path (Split-Path $repoRoot -Parent) "${repoName}-${TaskId}"
        if (-not (Test-Path $targetDir)) {
            Write-Error "ERROR: Worktree '$targetDir' does not exist."
            exit 1
        }
        Write-Host "Removing worktree $targetDir..."
        & git worktree remove "$targetDir"
        Write-Host "Worktree removed. Note: the branch 'task/$TaskId' is preserved until explicitly deleted."
        exit 0
    }

    default {
        Write-Error "ERROR: Unknown command '$Command'"
        Show-Help
        exit 1
    }
}
