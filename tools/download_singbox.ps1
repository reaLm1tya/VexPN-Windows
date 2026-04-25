# Скачивает sing-box (windows-amd64) в tools/sing-box.exe — для сборки и ручного теста.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$out = Join-Path $root "tools\sing-box.exe"
$dir = Join-Path $root "tools"
New-Item -ItemType Directory -Path $dir -Force | Out-Null

$rel = Invoke-RestMethod -Uri "https://api.github.com/repos/SagerNet/sing-box/releases/latest" -Headers @{"User-Agent"="VexPN-Build"}
$asset = $rel.assets | Where-Object { $_.name -match "windows-amd64\.zip$" } | Select-Object -First 1
if (-not $asset) { throw "No windows-amd64 zip in latest release" }
$uri = $asset.browser_download_url
$tmp = New-TemporaryFile
$zip = "$tmp.zip"
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
  Write-Host "OK: $out"
} finally {
  if (Test-Path $zip) { Remove-Item $zip -Force -ErrorAction SilentlyContinue }
  if (Test-Path $exdir) { Remove-Item $exdir -Recurse -Force -ErrorAction SilentlyContinue }
}
