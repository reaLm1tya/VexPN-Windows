# Деинсталляция VexPN: лежит в корне папки установки рядом с VexPN.exe
$ErrorActionPreference = "SilentlyContinue"
$dir = (Get-Item -LiteralPath (Split-Path -Parent $MyInvocation.MyCommand.Path)).FullName

foreach ($n in @("VexPN", "sing-box", "VexPN-Setup")) {
    Get-Process -Name $n -ErrorAction SilentlyContinue | Stop-Process -Force
}

$rm = { param($P) if (Test-Path -LiteralPath $P) { Remove-Item -LiteralPath $P -Force } }
$startMenu = [Environment]::GetFolderPath("StartMenu")
$pro = Join-Path $startMenu "Programs"
$desktop = [Environment]::GetFolderPath("Desktop")
& $rm (Join-Path $pro "VexPN.lnk")
& $rm (Join-Path $pro "VexPN\VexPN.lnk")
& $rm (Join-Path $pro "VexPN\Удалить VexPN.lnk")
& $rm (Join-Path $desktop "VexPN.lnk")
if ($env:OneDrive) { & $rm (Join-Path $env:OneDrive "Desktop\VexPN.lnk") }

# Асинхронное удаление папки (текущий скрипт внутри неё)
$escaped = $dir -replace "'", "''"
$body = "Start-Sleep -Seconds 1; Remove-Item -LiteralPath '$escaped' -Recurse -Force -ErrorAction SilentlyContinue"
$enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($body))
Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoProfile", "-WindowStyle", "Hidden", "-EncodedCommand", $enc) -WindowStyle Hidden

Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show("Папка VexPN удаляется:`n$dir`n(через 1 c)", "VexPN", "OK", 64) | Out-Null
