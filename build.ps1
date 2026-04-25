# Полная сборка: VexPN.exe, sing-box в dist, VexPN-Setup.exe, (если установлен) Inno
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

$py = Get-Command python -ErrorAction SilentlyContinue; if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
if (-not $py) { throw "python not in PATH" }
$python = $py.Source

Write-Host "==> pip + requirements" -ForegroundColor Cyan
$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $python -m pip install -q -r (Join-Path $Root "requirements.txt")
$ErrorActionPreference = $oldEap

$sb = Join-Path $Root "tools\sing-box.exe"
$wt = Join-Path $Root "tools\wintun.dll"
$dl = Join-Path $Root "tools\download_singbox.ps1"
if (-not (Test-Path $sb) -and (Test-Path $dl)) {
  Write-Host "==> download sing-box" -ForegroundColor Cyan
  & powershell -NoProfile -ExecutionPolicy Bypass -File $dl
}
if (-not (Test-Path $sb)) { Write-Warning "tools\\sing-box.exe missing; VPN kernel will not be in dist until you run tools\\download_singbox.ps1" }
if (-not (Test-Path $wt)) { Write-Warning "tools\\wintun.dll missing; TUN may fail on Windows" }

$genA = Join-Path $Root "tools\gen_vevpn_assets.py"
if (Test-Path $genA) {
  Write-Host "==> vexpn/assets (iOS-стиль PNG/GIF)" -ForegroundColor Cyan
  & $python $genA
}
$assetDir = Join-Path $Root "vexpn\assets"
if (-not (Test-Path $assetDir)) { throw "vexpn\\assets missing; run tools\\gen_vevpn_assets.py" }
$addData = $assetDir + ";" + "vexpn\assets"
$appIcon = Join-Path $Root "assets\app.ico"
if (-not (Test-Path $appIcon)) { throw "assets\\app.ico missing (build icon)" }

# Удаляем старый exe, если не заблокирован
$de = Join-Path $Root "dist\VexPN.exe"
if (Test-Path $de) {
  try { Remove-Item -LiteralPath $de -Force } catch { Write-Warning "Close VexPN.exe, then re-run build.ps1" }
}

Write-Host "==> PyInstaller: VexPN.exe" -ForegroundColor Cyan
$launcher = Join-Path $Root "launcher.py"
& $python -m PyInstaller @(
  "--noconfirm", "--windowed", "--onefile", "--clean",
  "--uac-admin",
  "--icon", $appIcon,
  "-n", "VexPN", "--paths", $Root,
  "--hidden-import=customtkinter", "--hidden-import=tkinter", "--hidden-import=PIL", "--hidden-import=PIL._tkinter_finder",
  "--add-data", $addData,
  "--collect-all", "customtkinter",
  $launcher
)

if (-not (Test-Path $de)) { throw "dist\\VexPN.exe not created" }

$uPy = Join-Path $Root "uninstall_vexpn.py"
$uEx = Join-Path $Root "dist\UninstallVexPN.exe"
if (Test-Path $uEx) { try { Remove-Item -LiteralPath $uEx -Force } catch { Write-Warning "Close UninstallVexPN.exe to rebuild" } }
Write-Host "==> UninstallVexPN.exe" -ForegroundColor Cyan
& $python -m PyInstaller @(
  "--noconfirm", "--windowed", "--onefile", "--clean",
  "--icon", $appIcon,
  "-n", "UninstallVexPN",
  "--distpath", (Join-Path $Root "dist"),
  "--workpath", (Join-Path $Root "build_uninstall"),
  $uPy
)
$ue = Join-Path $Root "dist\UninstallVexPN.exe"
if (-not (Test-Path $ue)) { throw "dist\\UninstallVexPN.exe not created" }
if (Test-Path $sb) {
  Copy-Item -LiteralPath $sb -Destination (Join-Path $Root "dist") -Force
  if (Test-Path $wt) { Copy-Item -LiteralPath $wt -Destination (Join-Path $Root "dist") -Force }
  Write-Host "OK: dist\\VexPN.exe + dist\\sing-box.exe (+ wintun.dll if present)" -ForegroundColor Green
} else {
  Write-Warning "dist has only VexPN.exe (no sing-box)"
}

# Inno Setup: offline installer
$iscc = $null
foreach ($cand in @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
  )) { if (Test-Path $cand) { $iscc = $cand; break } }
if ($iscc) {
  $iss = Join-Path $Root "installer.iss"
  if (Test-Path $iss) {
    Write-Host "==> Inno Setup" -ForegroundColor Cyan
    & $iscc $iss
    Write-Host "OK: installer_output\\" -ForegroundColor Green
  }
} else {
  Write-Host "Inno Setup 6 not found - skip offline installer. Install: https://jrsoftware.org/isdl.php" -ForegroundColor DarkYellow
}

# Онлайн-установщик
$boot = Join-Path $Root "bootstrap\build_bootstrap.ps1"
if (Test-Path $boot) {
  Write-Host "==> VexPN-Setup.exe" -ForegroundColor Cyan
  & $boot
} else { throw "bootstrap\build_bootstrap.ps1 missing" }

Write-Host ""
Write-Host "Done. See dist folder." -ForegroundColor Green
$distf = Join-Path $Root "dist"
if (Test-Path $distf) { Get-ChildItem $distf -ErrorAction SilentlyContinue | Format-Table Name, Length, LastWriteTime }
