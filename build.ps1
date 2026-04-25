# Сборка: VexPN.exe + sing-box в dist. Установщик: installer.iss (Inno Setup 6).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "python not in PATH"
}
python -m pip install -q -r requirements.txt
if (-not (Test-Path "tools\sing-box.exe")) {
  Write-Host "Downloading sing-box…"
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "tools\download_singbox.ps1")
}
& pyinstaller @(
  "--noconfirm", "--windowed", "--onefile", "-n", "VexPN", "--paths", ".",
  "--hidden-import=customtkinter", "--hidden-import=tkinter",
  "--collect-all", "customtkinter",
  "launcher.py"
)
if ((Test-Path "dist\VexPN.exe") -and (Test-Path "tools\sing-box.exe")) {
  Copy-Item "tools\sing-box.exe" "dist\" -Force
  Write-Host "OK: dist\\VexPN.exe + dist\\sing-box.exe"
} else {
  if (-not (Test-Path "dist\VexPN.exe")) { throw "dist\\VexPN.exe missing" }
  Write-Warning "tools\\sing-box.exe missing - install via tools\\download_singbox.ps1, then re-run to copy to dist"
}

$iscc = $null
$paths = @(
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
  "C:\Program Files\Inno Setup 6\ISCC.exe"
) + (Get-Command iscc -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
foreach ($p in $paths) {
  if ($p -and (Test-Path $p)) { $iscc = $p; break }
}
if ($iscc -and (Test-Path "installer.iss")) {
  & $iscc (Join-Path $PSScriptRoot "installer.iss")
  Write-Host "Install kit: pc\\installer_output\\"
} else {
  Write-Host "Inno Setup not found. Install from https://jrsoftware.org/isdl.php  then: ISCC installer.iss"
}

# Онлайн-установщик (тянет VexPN.exe + sing-box с манифеста в репо)
$boot = Join-Path $PSScriptRoot "bootstrap\build_bootstrap.ps1"
if (Test-Path $boot) {
  Write-Host "Building VexPN-Setup.exe (Git manifest downloader)…"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $boot
}
