import logging
import os
import sys
from collections import deque
from pathlib import Path
import subprocess
import threading
import time

from .paths import data_path, exe_dir
from .singbox_config import build_tun_config

log = logging.getLogger(__name__)


def _is_windows_admin() -> bool:
    if sys.platform != "win32":
        return os.geteuid() == 0
    import ctypes  # type: ignore

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore
    except Exception:
        return False


def _find_singbox() -> Path | None:
    cands = [
        exe_dir() / "sing-box.exe",
        exe_dir() / "singbox.exe",
        Path(__file__).resolve().parent / "bin" / "sing-box.exe",
    ]
    for c in cands:
        if c.is_file():
            return c
    w = os.environ.get("Path", "")
    for part in w.split(os.pathsep):
        p = Path(part.strip()) / "sing-box.exe"
        if p.is_file():
            return p
    return None


class SingBoxRunner:
    def __init__(self) -> None:
        self._p: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._config_path: Path | None = None
        self._reader_thread: threading.Thread | None = None
        self._last_lines: deque[str] = deque(maxlen=12)

    @property
    def running(self) -> bool:
        with self._lock:
            if self._p is None:
                return False
            return self._p.poll() is None

    @staticmethod
    def wintun_hint() -> str:
        if sys.platform == "win32" and not _is_windows_admin():
            return "Для режима TUN обычно нужны права администратора. Закройте приложение и откройте VexPN «От имени администратора»."
        return ""

    def start(self, vless_uri: str) -> tuple[bool, str]:
        with self._lock:
            if self._p is not None and self._p.poll() is None:
                return False, "Уже запущен sing-box"
            sing = _find_singbox()
            if not sing:
                return (
                    False,
                    "Не найден sing-box.exe. Поместите sing-box.exe рядом с VexPN.exe или в PATH. См. build/download_singbox.ps1",
                )
            try:
                cfg = build_tun_config(vless_uri)
            except Exception as e:  # noqa: BLE001
                log.exception("vless->sing-box config")
                return False, f"Ошибка разбора / конфигурации: {e}"

            cfg_dir = data_path("")
            cfg_dir.mkdir(parents=True, exist_ok=True)
            self._config_path = cfg_dir / f"singbox-{int(time.time())}.json"
            self._config_path.write_text(cfg, encoding="utf-8")

            creation = 0
            if sys.platform == "win32" and hasattr(subprocess, "CREATE_NO_WINDOW"):
                creation = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

            try:
                self._p = subprocess.Popen(
                    [str(sing), "run", "-c", str(self._config_path)],
                    cwd=str(sing.parent),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=creation,
                )
            except OSError as e:
                return False, f"Не удалось запустить sing-box: {e}"
            st = _is_windows_admin()
            hint = self.wintun_hint()
            self._reader_thread = threading.Thread(
                target=self._drain_output, name="singbox-log", daemon=True
            )
            self._reader_thread.start()
            if not st and sys.platform == "win32" and hint:
                return True, hint
            return True, ""

    def _drain_output(self) -> None:
        p = self._p
        if p is None or p.stdout is None:
            return
        try:
            for line in p.stdout:
                if line:
                    s = line.rstrip()
                    self._last_lines.append(s)
                    log.debug("sing-box: %s", s)
        except Exception:
            pass

    def _last_error_hint(self) -> str:
        txt = "\n".join(self._last_lines).lower()
        if "access is denied" in txt:
            return (
                "Доступ запрещён (Access is denied). Запустите VexPN с правами администратора "
                "и проверьте, что UAC подтверждён."
            )
        if "configure tun interface" in txt:
            return "Не удалось поднять TUN интерфейс. Проверьте права администратора и драйвер wintun."
        if "wintun" in txt:
            return "Проблема с wintun. Установите/переустановите WireGuard или добавьте wintun.dll рядом с sing-box.exe."
        if "invalid config" in txt or "json" in txt:
            return "Ошибка конфигурации sing-box. Проверьте формат vless и параметры сервера."
        return ""

    def stop(self) -> None:
        with self._lock:
            p = self._p
            self._p = None
        if p is None or p.poll() is not None:
            return
        if sys.platform == "win32":
            try:
                p.terminate()
                p.wait(timeout=4)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    p.kill()
                except OSError:
                    pass
        else:
            p.terminate()
            try:
                p.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                p.kill()

    def check_alive(self) -> str | None:
        """Вернёт строку с ошибкой, если процесс сам завершился (нап. нет админ-прав / wintun)."""
        with self._lock:
            p = self._p
        if p is None:
            return None
        code = p.poll()
        if code is None:
            return None
        if code != 0:
            hint = self._last_error_hint()
            tail = "\n".join(list(self._last_lines)[-3:]).strip()
            details = f"\nПоследние строки:\n{tail}" if tail else ""
            base = f"sing-box завершился с кодом {code}."
            if hint:
                return f"{base} {hint}{details}"
            return f"{base} Проверьте права администратора и wintun.{details}"
        return "sing-box остановлен"


def find_singbox_path() -> Path | None:
    return _find_singbox()
