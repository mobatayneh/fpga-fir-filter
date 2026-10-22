param([string]$PythonExecutable = '', [string]$GhdlExecutable = '')
$ErrorActionPreference = 'Stop'
if (-not $PythonExecutable) {
    $bundled = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Test-Path -LiteralPath $bundled) { $PythonExecutable = $bundled }
    else { $PythonExecutable = 'python' }
}
$runner = Join-Path $PSScriptRoot 'scripts\run_verification.py'
if ($GhdlExecutable) { & $PythonExecutable $runner --ghdl $GhdlExecutable }
else { & $PythonExecutable $runner }
if ($LASTEXITCODE -ne 0) { throw 'Verification failed. Inspect the printed log directory.' }
