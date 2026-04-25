# Скачивает sing-box (windows-amd64) в tools/sing-box.exe + wintun.dll — для сборки и ручного теста.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$out = Join-Path $root "tools\sing-box.exe"
$wout = Join-Path $root "tools\wintun.dll"
$dir = Join-Path $root "tools"
New-Item -ItemType Directory -Path $dir -Force | Out-Null

$ua = @{"User-Agent"="VexPN-Build"}
$rel = Invoke-RestMethod -Uri "https://api.github.com/repos/SagerNet/sing-box/releases/latest" -Headers $ua
$asset = $rel.assets | Where-Object { $_.name -match "windows-amd64\.zip$" } | Select-Object -First 1
if (-not $asset) { throw "No windows-amd64 zip in latest release" }
$uri = $asset.browser_download_url
$tmp = New-TemporaryFile
$zip = "$tmp.zip"
$wzip = $null
$wex = $null
Remove-Item $tmp -Force
try {
  Write-Host "Downloading $($asset.name)"
  Invoke-WebRequest -Uri $uri -OutFile $zip
  $exdir = Join-Path (Split-Path $zip) "singbox-extract"
  if (Test-Path $exdir) { Remove-Item $exdir -Recurse -Force }
  Expand-Archive -Path $zip -DestinationPath $exdir
  $exe = Get-ChildItem -Path $exdir -Recurse -Filter "sing-box.exe" | Select-Object -First 1
  if (-not $exe) { throw "sing-box.exe not in archive" }
  Copy-Item $exe.FullName $out -Force
  $wintun = Get-ChildItem -Path $exdir -Recurse -Filter "wintun.dll" | Select-Object -First 1
  if ($wintun) {
    Copy-Item $wintun.FullName $wout -Force
    Write-Host "OK: $wout"
  } else {
    Write-Host "wintun.dll missing in sing-box archive, trying wintun.net builds..." -ForegroundColor Yellow
    $wuri = "https://www.wintun.net/builds/wintun-0.14.1.zip"
    $wzip = Join-Path (Split-Path $zip) "wintun.zip"
    try {
      Invoke-WebRequest -Uri $wuri -OutFile $wzip -TimeoutSec 35
      $wex = Join-Path (Split-Path $zip) "wintun-extract"
      if (Test-Path $wex) { Remove-Item $wex -Recurse -Force }
      Expand-Archive -Path $wzip -DestinationPath $wex
      $wdll = Get-ChildItem -Path $wex -Recurse -Filter "wintun.dll" | Where-Object { $_.FullName -match "amd64|x64" } | Select-Object -First 1
      if (-not $wdll) { $wdll = Get-ChildItem -Path $wex -Recurse -Filter "wintun.dll" | Select-Object -First 1 }
      if (-not $wdll) { throw "wintun.dll not found in downloaded archive" }
      Copy-Item $wdll.FullName $wout -Force
      Write-Host "OK: $wout"
    } catch {
      Write-Warning "Could not download wintun.dll automatically: $($_.Exception.Message)"
      Write-Warning "Install WireGuard once (or manually place wintun.dll into tools\\ and dist\\)."
    }
  }
  Write-Host "OK: $out"
} finally {
  if (Test-Path $zip) { Remove-Item $zip -Force -ErrorAction SilentlyContinue }
  if (Test-Path $exdir) { Remove-Item $exdir -Recurse -Force -ErrorAction SilentlyContinue }
  if ($wzip -and (Test-Path $wzip)) { Remove-Item $wzip -Force -ErrorAction SilentlyContinue }
  if ($wex -and (Test-Path $wex)) { Remove-Item $wex -Recurse -Force -ErrorAction SilentlyContinue }
}
