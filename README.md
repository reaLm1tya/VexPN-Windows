# VexPN Windows

Клиент для Windows + онлайн-установщик, привязан к репозиторию: [VexPN-Windows](https://github.com/reaLm1tya/VexPN-Windows).

## Сборка

В каталоге `pc\` из PowerShell:

```powershell
Set-Location путь\к\pc
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

Скрипт делает: `pip install -r requirements.txt` → (при необходимости) `tools\download_singbox.ps1` → `VexPN.exe` (PyInstaller) → копия `sing-box` в `dist\` → **Inno** `installer_output\VexPN-Windows-Setup-1.0.0.exe` (если установлен [Inno Setup 6](https://jrsoftware.org/isdl.php)) → **`dist\VexPN-Setup.exe`** + `VexPN-Setup.config.json`.

- Отдельно онлайн-установщик: `.\bootstrap\build_bootstrap.ps1`

## Как `VexPN-Setup` берёт файлы с GitHub

1. [install_manifest.json](install_manifest.json) лежит в **ветке `main`**. Установщик скачивает его по `raw.githubusercontent.com/.../main/install_manifest.json`.
2. В манифесте указаны прямые `raw`-ссылки на файлы в `main/bin`: `VexPN.exe`, `sing-box.exe`, `wintun.dll`, `UninstallVexPN.exe`.

## `VexPN-Setup.config.json` (только для разработки)

Рядом с `VexPN-Setup.exe` можно положить `VexPN-Setup.config.json` с полем `manifest_url`, чтобы переопределить манифест. В обычной сборке поле ввода URL **убрано** — используется `install_manifest` с [raw GitHub](https://raw.githubusercontent.com/reaLm1tya/VexPN-Windows/main/install_manifest.json).

## Удаление

В папку установки копируется `UninstallVexPN.exe`. Запустите его из каталога VexPN — удалятся ярлыки и папка приложения.
