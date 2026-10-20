<#
.SYNOPSIS
    validate-report.ps1 — PowerShell wrapper for validate-report.py.
#>

[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyScript = Join-Path $scriptDir "validate-report.py"

$pythonBin = $null
$pythonArgs = @()

if (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonBin = "py"
    $pythonArgs = @("-3", $pyScript) + $ArgsList
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonBin = "python"
    $pythonArgs = @($pyScript) + $ArgsList
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonBin = "python3"
    $pythonArgs = @($pyScript) + $ArgsList
} else {
    Write-Error "ERROR: Python is not found on PATH. Please install Python 3.10+ and add it to PATH."
    exit 1
}

& $pythonBin @pythonArgs
exit $LASTEXITCODE
