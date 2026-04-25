# Лёгкий VexPN-Setup.exe: только stdlib+tk, тянет файлы с Git/HTTPS по манифесту
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
$here = (Get-Location).Path
& pyinstaller @(
  "--noconfirm", "--windowed", "--onefile",
  "-n", "VexPN-Setup",
  "--distpath", "dist",
  "--workpath", "build_bootstrap",
  (Join-Path $here "bootstrap\vexpn_setup_bootstrap.py")
)
if (Test-Path (Join-Path $here "dist\VexPN-Setup.exe")) {
  Copy-Item (Join-Path $here "bootstrap\VexPN-Setup.config.json") (Join-Path $here "dist\")
  Write-Host "OK: dist\\VexPN-Setup.exe + VexPN-Setup.config.json — манифест: github.com/reaLm1tya/VexPN-Windows"
}
