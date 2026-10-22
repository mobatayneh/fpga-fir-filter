# Download a pinned official portable simulator inside this project only.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$destination = Join-Path $root '.tools\ghdl-6.0.0'
if (Test-Path -LiteralPath $destination) {
    throw "Destination already exists: $destination. Keep it or select an existing GHDL with --ghdl."
}
$toolsDirectory = Join-Path $root '.tools'
New-Item -ItemType Directory -Path $toolsDirectory -Force | Out-Null
$archive = Join-Path $toolsDirectory 'ghdl-mcode-6.0.0-mingw64.zip'
$url = 'https://github.com/ghdl/ghdl/releases/download/v6.0.0/ghdl-mcode-6.0.0-mingw64.zip'
$expected = 'c1562b2a4767e34d33159b536b5e36a8a38ebdb6e7672aa9969a4f4ac2cadffe'
if (-not (Test-Path -LiteralPath $archive)) {
    Invoke-WebRequest -Uri $url -OutFile $archive
}
$actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLower()
if ($actual -ne $expected) { throw 'GHDL archive checksum mismatch. Do not execute the download.' }
Expand-Archive -LiteralPath $archive -DestinationPath $destination
& (Join-Path $destination 'bin\ghdl.exe') --version
if ($LASTEXITCODE -ne 0) { throw 'GHDL version check failed.' }
