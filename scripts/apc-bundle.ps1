<#
.SYNOPSIS
    apc-bundle.ps1 — Package repository files into a self-describing, verifiable APC archive.
.DESCRIPTION
    Runs from the ccis-heat-load-backup-sim repository root. PowerShell equivalent of apc-bundle.sh.
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$ProfileName = "core",

    [string[]]$Exclude = @(),
    [string[]]$Add = @(),
    [switch]$WithReports,
    [switch]$List,
    [switch]$Tokens,
    [switch]$Discover,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

function Show-Help {
    @"
Usage: .\scripts\apc-bundle.ps1 [PROFILE] [OPTIONS]
       .\scripts\apc-bundle.bat [PROFILE] [OPTIONS]

Profiles:
  core          Governance, tracking, and architectural context (default)
  dev           Core implementation modules, interfaces, and test fixtures
  full          Complete project snapshot (union of all profiles)

Options:
  --exclude GLOB    Drop any resolved path matching the glob (repeatable)
  --add PATH        Add an ad hoc file (repeatable)
  --with-reports    Include active entries from OPTIONAL_REPORTS
  --list            Print resolved file list with byte sizes and exit 0
  --tokens          Estimate token count (~4 chars/token heuristic) and exit 0
  --discover        Search src for core classes/functions and exit 0
  -h, --help        Show this help message and exit
"@
}

if ($Help) {
    Show-Help
    exit 0
}

# Determine repository root
$repoRoot = (Get-Item -Path ".").FullName

# Define profiles
$PROFILE_CORE = @(
    "AGENTS.md",
    "pyproject.toml",
    "requirements.txt",
    "docs/context/*.md",
    "docs/context/repo-tree.txt",
    "docs/decisions/decision-log.md",
    "docs/tasks/status.md",
    "docs/tasks/high-level-tasks.md",
    "docs/prompts/*.md",
    "docs/guide/*.md"
)

$PROFILE_DEV = $PROFILE_CORE + @(
    "src/ccis_sim/*.py",
    "src/ccis_sim/*/*.py",
    "tests/*.py"
)

$PROFILE_FULL = $PROFILE_CORE + $PROFILE_DEV

$OPTIONAL_REPORTS = @(
    "docs/reports/*.md"
)

function Test-SecretOrForbidden([string]$relPath) {
    $norm = $relPath.Replace("\", "/").TrimStart("./")
    $baseName = Split-Path $norm -Leaf
    $lower = $norm.ToLowerInvariant()

    # Forbidden build, dependency, and storage directories
    $forbiddenPrefixes = @(
        "results", "data/raw", ".git", ".venv", "venv",
        "__pycache__", "node_modules", "dist", "build"
    )
    foreach ($pfx in $forbiddenPrefixes) {
        if ($norm -eq $pfx -or $norm.StartsWith("$pfx/")) {
            return $true
        }
    }

    # Forbidden filename prefixes or credential extensions
    if ($baseName -like ".env*" -or $baseName -like "*.key" -or
        $baseName -like "*.pem" -or $baseName -like "*.p12" -or $baseName -like "*.pfx") {
        return $true
    }

    # Forbidden sensitive keywords anywhere in the path
    $sensitiveKeywords = @("*secret*", "*token*", "*credential*", "*id_rsa*", "*password*")
    foreach ($kw in $sensitiveKeywords) {
        if ($lower -like $kw) {
            return $true
        }
    }

    return $false
}

if ($Discover) {
    Write-Host "Discovered core source files in src:"
    $srcDir = Join-Path $repoRoot "src"
    if (Test-Path $srcDir) {
        Get-ChildItem -Path $srcDir -Recurse -File -Include "*.py", "*.ts", "*.go", "*.rs" |
            ForEach-Object {
                $_.FullName.Substring($repoRoot.Length).TrimStart("\", "/").Replace("\", "/")
            } | Sort-Object -Unique | ForEach-Object { Write-Host $_ }
    }
    exit 0
}

# Auto-update docs/context/repo-tree.txt if tree command supports GNU options
$treeCmd = Get-Command tree -ErrorAction SilentlyContinue
if ($treeCmd) {
    try {
        # Check if GNU tree or Windows tree
        $isGnuTree = & tree --version 2>&1 | Select-String "tree v"
        if ($isGnuTree) {
            $contextDir = Join-Path $repoRoot "docs/context"
            if (-not (Test-Path $contextDir)) {
                New-Item -ItemType Directory -Path $contextDir -Force | Out-Null
            }
            & tree -I ".git|.venv|venv|__pycache__|*.egg-info|node_modules|dist|build|*.tar.gz|*.log" --dirsfirst --noreport > (Join-Path $contextDir "repo-tree.txt")
        }
    } catch {
        # Non-critical fallback
    }
}

# Select raw profile patterns
$rawItems = @()
switch ($ProfileName.ToLowerInvariant()) {
    "core" { $rawItems = $PROFILE_CORE }
    "dev"  { $rawItems = $PROFILE_DEV }
    "full" { $rawItems = $PROFILE_FULL }
    default {
        Write-Error "ERROR: Unknown profile '$ProfileName'. Valid options: core, dev, full."
        exit 2
    }
}

if ($WithReports) {
    $rawItems += $OPTIONAL_REPORTS
}

# Resolve globs
$resolvedRaw = [System.Collections.Generic.List[string]]::new()
foreach ($pattern in $rawItems) {
    if ($pattern.Contains("*") -or $pattern.Contains("?") -or $pattern.Contains("[")) {
        # Wildcard matching relative to repo root
        $searchPath = Join-Path $repoRoot ($pattern.Replace("/", [System.IO.Path]::DirectorySeparatorChar))
        $matches = Get-ChildItem -Path $searchPath -File -ErrorAction SilentlyContinue
        if (-not $matches -or $matches.Count -eq 0) {
            Write-Error "ERROR: Glob '$pattern' matched no files."
            exit 1
        }
        foreach ($m in $matches) {
            $rel = $m.FullName.Substring($repoRoot.Length).TrimStart("\", "/").Replace("\", "/")
            $resolvedRaw.Add($rel)
        }
    } else {
        $resolvedRaw.Add($pattern.Replace("\", "/").TrimStart("./"))
    }
}

# Add ad hoc files
foreach ($ad in $Add) {
    $resolvedRaw.Add($ad.Replace("\", "/").TrimStart("./"))
}

# Deduplicate while preserving order
$deduped = [System.Collections.Generic.List[string]]::new()
$seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($p in $resolvedRaw) {
    $norm = $p.Replace("\", "/").TrimStart("./")
    if (-not $seen.Contains($norm)) {
        $seen.Add($norm) | Out-Null
        $deduped.Add($norm)
    }
}

# Apply exclusions
$filtered = [System.Collections.Generic.List[string]]::new()
foreach ($p in $deduped) {
    $base = Split-Path $p -Leaf
    $excluded = $false
    foreach ($ex in $Exclude) {
        $exNorm = $ex.Replace("\", "/")
        if ($p -like $exNorm -or $base -like $exNorm) {
            $excluded = $true
            break
        }
    }
    if (-not $excluded) {
        $filtered.Add($p)
    }
}

# Validate existence and security guard
$validationFailed = $false
foreach ($f in $filtered) {
    if (Test-SecretOrForbidden $f) {
        Write-Error "ERROR: Security guard triggered! Path '$f' matches secret or forbidden pattern."
        $validationFailed = $true
        continue
    }

    $fullPath = Join-Path $repoRoot ($f.Replace("/", [System.IO.Path]::DirectorySeparatorChar))
    if (-not (Test-Path $fullPath)) {
        Write-Error "MISSING FILE: $f"
        $validationFailed = $true
    } elseif (-not (Test-Path $fullPath -PathType Leaf)) {
        Write-Error "NOT A REGULAR FILE: $f"
        $validationFailed = $true
    }
}

if ($validationFailed) {
    exit 1
}

# List mode
if ($List) {
    Write-Host "Files in profile '$ProfileName' ($($filtered.Count) total):"
    $totalBytes = 0
    foreach ($f in $filtered) {
        $fullPath = Join-Path $repoRoot ($f.Replace("/", [System.IO.Path]::DirectorySeparatorChar))
        $sz = (Get-Item $fullPath).Length
        $totalBytes += $sz
        "{0,10}  {1}" -f $sz, $f | Write-Host
    }
    Write-Host "---"
    Write-Host ("Total: {0} bytes (approx {1} KB)" -f $totalBytes, [math]::Floor($totalBytes / 1024))
    exit 0
}

# Tokens mode (~4 chars per token)
if ($Tokens) {
    $totalChars = 0
    foreach ($f in $filtered) {
        $fullPath = Join-Path $repoRoot ($f.Replace("/", [System.IO.Path]::DirectorySeparatorChar))
        $content = [System.IO.File]::ReadAllText($fullPath)
        $totalChars += $content.Length
    }
    $estTokens = [math]::Floor($totalChars / 4)
    Write-Host "Estimated token count for profile '$ProfileName': ~$estTokens tokens ($totalChars characters across $($filtered.Count) files)."
    exit 0
}

# Check for tar command
$tarCmd = Get-Command tar.exe -ErrorAction SilentlyContinue
if (-not $tarCmd) {
    $tarCmd = Get-Command tar -ErrorAction SilentlyContinue
}
if (-not $tarCmd) {
    Write-Error "ERROR: 'tar' utility is not found on PATH. On Windows 10/11, tar.exe is located in System32."
    exit 1
}

# Archive generation
$timestamp = Get-Date -Format "yyyyMMdd-HHmm"
$outArchive = "apc-bundle-$ProfileName-$timestamp.tar.gz"

$tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ("apc-bundle-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null

try {
    # Stage files preserving relative paths
    foreach ($f in $filtered) {
        $srcFile = Join-Path $repoRoot ($f.Replace("/", [System.IO.Path]::DirectorySeparatorChar))
        $destFile = Join-Path $tmpDir ($f.Replace("/", [System.IO.Path]::DirectorySeparatorChar))
        $destParent = Split-Path $destFile -Parent
        if (-not (Test-Path $destParent)) {
            New-Item -ItemType Directory -Path $destParent -Force | Out-Null
        }
        Copy-Item -Path $srcFile -Destination $destFile -Force
    }

    # Generate MANIFEST.txt
    $manifestPath = Join-Path $tmpDir "MANIFEST.txt"
    $utcIso = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    
    $gitCommit = "uncommitted"
    try {
        $gitCommit = & git rev-parse --short HEAD 2>$null
        if (-not $gitCommit) { $gitCommit = "uncommitted" }
    } catch {}

    $manifestLines = [System.Collections.Generic.List[string]]::new()
    $manifestLines.Add("Profile: $ProfileName")
    $manifestLines.Add("Timestamp (UTC): $utcIso")
    $manifestLines.Add("Git commit: $gitCommit")
    $manifestLines.Add("Git status:")
    
    try {
        $gitStatus = & git status --porcelain -- $filtered 2>$null
        if ($gitStatus) {
            foreach ($line in $gitStatus) {
                $manifestLines.Add($line)
            }
        }
    } catch {}

    $manifestLines.Add("")
    $manifestLines.Add("Paths are repo-relative. Extract with: tar -xzf <archive>.")
    $manifestLines.Add("")
    $manifestLines.Add("Files (SHA256, Size in bytes, Path):")

    foreach ($f in $filtered) {
        $srcFile = Join-Path $repoRoot ($f.Replace("/", [System.IO.Path]::DirectorySeparatorChar))
        $hashObj = Get-FileHash -Path $srcFile -Algorithm SHA256
        $sha = $hashObj.Hash.ToLowerInvariant()
        $sz = (Get-Item $srcFile).Length
        $manifestLines.Add("$sha  $sz  $f")
    }

    [System.IO.File]::WriteAllLines($manifestPath, $manifestLines)

    # Build tar.gz
    $outFullPath = Join-Path $repoRoot $outArchive
    $tarArgs = @("-czf", $outFullPath, "-C", $tmpDir, "MANIFEST.txt") + $filtered
    & $tarCmd @tarArgs

    $archiveSz = (Get-Item $outFullPath).Length
    $fileCnt = $filtered.Count + 1

    Write-Host "=================================================="
    Write-Host "APC Bundle Created Successfully!"
    Write-Host "Archive:    $outArchive"
    Write-Host "Size:       $archiveSz bytes"
    Write-Host "Files:      $fileCnt (including MANIFEST.txt)"
    Write-Host "Verify with: tar -xzf $outArchive"
    Write-Host "=================================================="

} finally {
    if (Test-Path $tmpDir) {
        Remove-Item -Path $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
