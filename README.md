# VexPN Windows

Клиент для Windows + онлайн-установщик, привязан к репозиторию: [VexPN-Windows](https://github.com/reaLm1tya/VexPN-Windows).

## Сборка

- `.\build.ps1` — `dist\VexPN.exe`, `dist\sing-box.exe`, `dist\VexPN-Setup.exe`, (опц.) установщик Inno
- `.\tools\download_singbox.ps1` — скачать `sing-box.exe` при необходимости

## Как `VexPN-Setup` берёт файлы с GitHub

1. [install_manifest.json](install_manifest.json) лежит в **ветке `main`**. Установщик скачивает его по `raw.githubusercontent.com/.../main/install_manifest.json`.
2. В манифесте указаны прямые ссылки `releases/latest/download/VexPN.exe` и `.../sing-box.exe` — **в последнем [Release](https://github.com/reaLm1tya/VexPN-Windows/releases) должны быть вложения с ровно такими именами**.

Пока релиза с файлами нет, скачивание из установщика вернёт 404 — создайте Release и прикрепите артефакты.

**Альтернатива без Releases:** выложите `VexPN.exe` и `sing-box.exe` в `dist/` на `main` и в `install_manifest.json` укажите `base_url` + `path` (см. [install_manifest.example.json](install_manifest.example.json)).

## `VexPN-Setup.config.json` (только для разработки)

Рядом с `VexPN-Setup.exe` можно положить `VexPN-Setup.config.json` с полем `manifest_url`, чтобы переопределить манифест. В обычной сборке поле ввода URL **убрано** — используется `install_manifest` с [raw GitHub](https://raw.githubusercontent.com/reaLm1tya/VexPN-Windows/main/install_manifest.json).

## Удаление

В папку установки копируются [uninstall_vexpn.cmd](uninstall_vexpn.cmd) и [uninstall_vexpn.ps1](uninstall_vexpn.ps1) (также в [install_manifest.json](install_manifest.json) с `raw.githubusercontent.com`). Запустите **uninstall_vexpn.cmd** в каталоге VexPN — удалятся ярлыки и папка приложения.
