# VexPN-Setup.exe: stdlib + tk, скачивание по install_manifest (PyInstaller)
$ErrorActionPreference = "Stop"
$pcRoot = Split-Path -Parent $PSScriptRoot
Set-Location $pcRoot

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) { throw "python not in PATH" }
$python = $py.Source

Write-Host "==> VexPN-Setup.exe (from bootstrap\vexpn_setup_bootstrap.py)" -ForegroundColor Cyan
$oe = $ErrorActionPreference; $ErrorActionPreference = "Continue"
& $python -m pip install -q "pyinstaller>=6.0"
$ErrorActionPreference = $oe

$script = Join-Path $pcRoot "bootstrap\vexpn_setup_bootstrap.py"
$distSetup = Join-Path $pcRoot "dist\VexPN-Setup.exe"

if ((Test-Path $distSetup) -and -not $env:FORCE_REBUILD) {
  try { Remove-Item -LiteralPath $distSetup -Force } catch { Write-Warning "Close VexPN-Setup.exe to rebuild" }
}

& $python -m PyInstaller @(
  "--noconfirm", "--windowed", "--onefile", "--clean",
  "-n", "VexPN-Setup",
  "--distpath", (Join-Path $pcRoot "dist"),
  "--workpath", (Join-Path $pcRoot "build_bootstrap"),
  "--hidden-import=tkinter",
  $script
)

$cfg = Join-Path $pcRoot "bootstrap\VexPN-Setup.config.json"
$distDir = Join-Path $pcRoot "dist"
$out = Join-Path $distDir "VexPN-Setup.exe"
if (Test-Path $out) {
  if (Test-Path $cfg) { Copy-Item -LiteralPath $cfg -Destination $distDir -Force }
  Write-Host "OK: $out" -ForegroundColor Green
  if (Test-Path (Join-Path $distDir "VexPN-Setup.config.json")) {
    Write-Host "OK: $(Join-Path $distDir 'VexPN-Setup.config.json')"
  }
} else {
  throw "PyInstaller did not create dist\\VexPN-Setup.exe"
}
