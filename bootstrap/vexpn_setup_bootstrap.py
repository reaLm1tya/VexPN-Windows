"""
VexPN-Setup.exe: тихо скачивает install_manifest с GitHub (main) и перечисленные файлы.
Переопределение URL манифеста (только для разработки): VexPN-Setup.config.json рядом с .exe.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_MANIFEST_URL = "https://raw.githubusercontent.com/reaLm1tya/VexPN-Windows/main/install_manifest.json"


def _app_dir() -> str:
    if getattr(sys, "frozen", False) and sys.executable:
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read_local_config() -> str | None:
    for name in ("VexPN-Setup.config.json", "vexpn_setup_config.json"):
        p = os.path.join(_app_dir(), name)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            u = (d or {}).get("manifest_url")
            if isinstance(u, str) and u.strip().lower().startswith("http"):
                return u.strip()
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return None


def _fetch_url(url: str, timeout: float = 60.0) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "VexPN-Setup/1.0 (Windows; +https://vex-gram.ru)"},
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read()


def _download_to_file(url: str, dest: str) -> None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "VexPN-Setup/1.0 (Windows; +https://vex-gram.ru)"},
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=300, context=ctx) as r:
        with open(dest, "wb") as f:
            while True:
                chunk = r.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)


def _parse_manifest(data: bytes) -> dict:
    m = json.loads(data.decode("utf-8", errors="strict"))
    if not isinstance(m, dict) or "files" not in m or not isinstance(m["files"], list):
        raise ValueError("ожидается JSON { version, files: [...] }")
    if not m["files"]:
        raise ValueError("files[] пустой")
    return m


def _file_url(manifest: dict, item: dict) -> str:
    path = str(item.get("path", "")).strip()
    u = str(item.get("url", "")).strip()
    if u.lower().startswith("http"):
        return u
    if not path:
        raise ValueError("нужен path")
    base = (manifest.get("base_url") or "").strip()
    if not base.lower().startswith("http"):
        raise ValueError("нужен url в элементе files или base_url в манифесте")
    b = base if base.endswith("/") else base + "/"
    return urllib.parse.urljoin(b, path.replace("\\", "/"))


def _main_exe_name(manifest: dict) -> str:
    for it in manifest["files"]:
        if not isinstance(it, dict):
            continue
        p = (it.get("path") or "").lower()
        if p.endswith("vexpn.exe"):
            return os.path.basename(str(it.get("path")))
    for it in manifest["files"]:
        if not isinstance(it, dict):
            continue
        p = (it.get("path") or "").lower()
        if p.endswith(".exe") and "sing" not in os.path.basename(p).lower():
            return os.path.basename(it["path"])
    return "VexPN.exe"


def _powershell_shortcut(lnk: str, target: str, work: str) -> None:
    target = target.replace("'", "''")
    work = work.replace("'", "''")
    lnk = lnk.replace("'", "''")
    ps = (
        f"$W=New-Object -ComObject WScript.Shell; "
        f"$s=$W.CreateShortcut('{lnk}'); $s.TargetPath='{target}'; $s.WorkingDirectory='{work}'; $s.Save();"
    )
    cf = 0
    if sys.platform == "win32":
        cf = int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000))
    subprocess.run(
        ["powershell", "-NoProfile", "-NoLogo", "-Command", ps],
        check=False,
        creationflags=cf,
    )


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Установщик VexPN")
        self.minsize(500, 280)
        self.geometry("520x400")

        def_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "VexPN")
        self._dir = tk.StringVar(value=def_dir)
        self._desktop = tk.IntVar(value=0)
        self._work = False

        f = ttk.Frame(self, padding=10)
        f.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            f,
            text="VexPN скачивается с GitHub (VexPN-Windows). Ссылка на манифест встроена — ничего вводить не нужно.",
            wraplength=500,
        ).pack(anchor=tk.W, pady=(0, 8))

        r = ttk.Frame(f)
        r.pack(fill=tk.X, pady=2)
        ttk.Label(r, text="Папка:").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(r, textvariable=self._dir, width=55).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(r, text="Обзор…", command=self._browse).pack(side=tk.LEFT)
        ttk.Checkbutton(
            f, text="Ярлык на рабочем столе", variable=self._desktop
        ).pack(anchor=tk.W, pady=6)

        self._bar = ttk.Progressbar(f, mode="indeterminate", length=520)
        self._bar.pack(fill=tk.X, pady=4)
        self._log = tk.Text(f, height=8, state=tk.DISABLED, font=("Consolas", 9))
        self._log.pack(fill=tk.BOTH, expand=True, pady=4)
        ttk.Button(f, text="Скачать и установить", command=self._go).pack(pady=2)

    @staticmethod
    def _get_manifest_url() -> str:
        u = (_read_local_config() or DEFAULT_MANIFEST_URL or "").strip()
        return u

    def _browse(self) -> None:
        p = filedialog.askdirectory(initialdir=self._dir.get() or None)
        if p:
            self._dir.set(p)

    def _logl(self, s: str) -> None:
        self._log.config(state=tk.NORMAL)
        self._log.insert(tk.END, s + "\n")
        self._log.see(tk.END)
        self._log.config(state=tk.DISABLED)
        self.update_idletasks()

    def _go(self) -> None:
        if self._work:
            return
        self.update_idletasks()
        url = self._get_manifest_url()
        if not re.match(r"^https?://\S+$", url) or re.search(r"\s", url):
            messagebox.showerror("VexPN", "Сборка VexPN-Setup без URL манифеста. Обновите VexPN-Setup.exe с GitHub.")
            return
        self._work = True
        self._bar.start(8)
        threading.Thread(
            target=self._worker, args=(url, self._dir.get().strip(), int(self._desktop.get())), daemon=True
        ).start()

    def _worker(self, murl: str, install_dir: str, add_desktop: int) -> None:
        def ui(fn) -> None:
            self.after(0, fn)

        tmpd: str | None = None
        try:
            if not install_dir:
                install_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "VexPN")

            ui(lambda: self._logl("Загрузка манифеста: " + murl))
            raw = _fetch_url(murl)
            m = _parse_manifest(raw)
            v = m.get("version", "?")
            an = m.get("app_name", "VexPN")
            main_exe = _main_exe_name(m)
            nfiles = len(m["files"])
            ui(
                lambda: self._logl(
                    f"Версия: {v!s}  ·  {an!s}  ·  файлов: {nfiles}  ·  запуск: {main_exe}"
                )
            )

            tmpd = tempfile.mkdtemp(prefix="vexpn_")
            for i, item in enumerate(m["files"]):
                if not isinstance(item, dict):
                    raise TypeError("files[]: каждый элемент — объект {path, url?}")
                fu = _file_url(m, item)
                name = os.path.basename((item.get("path") or "x.dat").replace("\\", "/"))
                out = os.path.join(tmpd, name)
                ui(
                    lambda i=i, nfiles=nfiles, name=name, fu=fu: self._logl(
                        f"({i+1}/{nfiles}) {name}\n  ← {fu}"
                    )
                )
                _download_to_file(fu, out)

            os.makedirs(install_dir, exist_ok=True)
            ui(lambda: self._logl("Копирование в: " + install_dir))
            for name in os.listdir(tmpd):
                shutil.copy2(os.path.join(tmpd, name), os.path.join(install_dir, name))
            ex = os.path.join(install_dir, main_exe)
            sm = os.path.join(
                os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "VexPN.lnk"
            )
            os.makedirs(os.path.dirname(sm), exist_ok=True)
            ui(
                lambda: _powershell_shortcut(
                    sm,
                    ex,
                    install_dir,
                )
            )
            if add_desktop:
                dlnk = os.path.join(os.path.expanduser("~"), "Desktop", "VexPN.lnk")
                ui(
                    lambda: _powershell_shortcut(
                        dlnk, ex, install_dir
                    )
                )

            ui(
                lambda e=ex, d=install_dir: self._work_done(
                    True,
                    e,
                    f"Установка завершена. Папка:\n{d}\n\n"
                    f"Удаление: {os.path.join(d, 'UninstallVexPN.exe')}\n(или {os.path.join(d, 'uninstall_vexpn.cmd')})",
                )
            )
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            # нельзя использовать `e` внутри lambda без привязки — после except e обнуляется
            http = ""
            if isinstance(e, urllib.error.HTTPError):
                http = f" HTTP {e.code}"
                try:
                    rawb = e.read() or b""
                    body = rawb.decode("utf-8", errors="replace")
                except Exception:
                    body = ""
                bstrip = body.strip()
                if bstrip:
                    if bstrip.lstrip()[:1] == "<" and ("html" in bstrip[:200].lower() or "DOCTYPE" in bstrip):
                        bstrip = f"[страница HTML, обычно 404: проверьте вложения в релизе] ({len(bstrip)} симв.)"
                    else:
                        bstrip = bstrip[:320]
                    http += f"\nКратко: {bstrip}"
            err_msg = (
                f"Сеть/файл{http}: {e!s}\n\n"
                "Проверьте:\n"
                "• Release: https://github.com/reaLm1tya/VexPN-Windows/releases — "
                "должны быть вложения VexPN.exe и sing-box.exe (имена точно такие);\n"
                "• raw: uninstall_* и install_manifest.json в ветке main."
            )
            ui(lambda m=err_msg: self._work_done(False, "", m))
        except (ValueError, json.JSONDecodeError, TypeError) as e:
            err_msg2 = f"Манифест или ответ: {e!s}"
            ui(lambda m=err_msg2: self._work_done(False, "", m))
        finally:
            if tmpd and os.path.isdir(tmpd):
                shutil.rmtree(tmpd, ignore_errors=True)
            ui(self._bar.stop)

    def _work_done(self, ok: bool, run_ex: str, text: str) -> None:
        self._work = False
        self._bar.stop()
        if not ok:
            self._logl("ОШИБКА: " + text)
            messagebox.showerror("VexPN", text)
            return
        self._logl(text)
        messagebox.showinfo("VexPN", "Готово.")
        if run_ex and os.path.isfile(run_ex) and messagebox.askyesno("VexPN", "Запустить VexPN сейчас?"):
            try:
                os.startfile(run_ex)  # type: ignore[attr-defined]
            except (OSError, RuntimeError) as e:
                messagebox.showerror("VexPN", str(e))


def main() -> None:
    if sys.platform == "win32":
        try:
            from ctypes import windll  # type: ignore

            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    App().mainloop()


if __name__ == "__main__":
    main()
