"""
UninstallVexPN.exe: полное удаление папки установки и ярлыков (как iOS-деинсталляция).
Папка — каталог, где лежит этот .exe.
"""
from __future__ import annotations

import base64
import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

BG = "#F2F2F7"


def _install_dir() -> str:
    if getattr(sys, "frozen", False) and sys.executable:
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _remove_shortcuts() -> None:
    from pathlib import Path

    pro = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    nested = pro / "VexPN"
    for p in (
        pro / "VexPN.lnk",
        pro / "Uninstall VexPN.lnk",
        nested / "VexPN.lnk",
        nested / "Удалить VexPN.lnk",
    ):
        if p.is_file():
            try:
                p.unlink()
            except OSError:
                pass
    try:
        if nested.is_dir() and not any(nested.iterdir()):
            nested.rmdir()
    except OSError:
        pass
    for base in (os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),):
        p = os.path.join(base, "VexPN.lnk")
        if os.path.isfile(p):
            try:
                os.remove(p)
            except OSError:
                pass
    od = os.environ.get("OneDrive")
    if od:
        p = os.path.join(od, "Desktop", "VexPN.lnk")
        if os.path.isfile(p):
            try:
                os.remove(p)
            except OSError:
                pass


def _stop_processes() -> None:
    cf = int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)) if sys.platform == "win32" else 0
    for n in ("VexPN.exe", "sing-box.exe", "VexPN-Setup.exe"):
        subprocess.run(
            ["taskkill", "/F", "/T", "/IM", n], capture_output=True, check=False, creationflags=cf
        )


def _schedule_delete_folder(d: str) -> None:
    esc = d.replace("'", "''")
    body = f"Start-Sleep -Seconds 1; Remove-Item -LiteralPath '{esc}' -Recurse -Force -ErrorAction SilentlyContinue"
    enc = base64.b64encode(body.encode("utf-16le")).decode("ascii")
    line = f"Start-Process powershell.exe -ArgumentList '-NoProfile -WindowStyle Hidden -EncodedCommand {enc}' -WindowStyle Hidden"
    cf = int(getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)) if sys.platform == "win32" else 0
    subprocess.run(
        ["powershell", "-NoProfile", "-NoLogo", "-Command", line], check=False, creationflags=cf
    )


def main() -> None:
    if sys.platform == "win32":
        try:
            from ctypes import windll  # type: ignore

            windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
        except Exception:
            pass

    d = _install_dir()
    r = tk.Tk()
    r.title("VexPN — удаление")
    r.minsize(400, 240)
    r.configure(padx=0, pady=0, bg=BG)
    r.geometry("440x300")

    f = ttk.Frame(r, padding=24)
    f.pack(fill=tk.BOTH, expand=True)
    ttk.Label(
        f, text="Удалить VexPN", font=("Segoe UI", 20, "bold"), foreground="#1C1C1E"
    ).pack(anchor=tk.W)
    ttk.Label(
        f,
        text="Все компоненты, ярлыки и папка установки будут удалены.",
        font=("Segoe UI", 11),
        wraplength=380,
        justify=tk.LEFT,
    ).pack(anchor=tk.W, pady=(8, 0))
    ttk.Label(
        f,
        text=d,
        font=("Consolas", 10),
        wraplength=380,
        justify=tk.LEFT,
        foreground="#3C3C43",
    ).pack(anchor=tk.W, pady=(8, 16))

    bfr = ttk.Frame(f)
    bfr.pack(fill=tk.X, pady=8, anchor=tk.E)

    def on_remove() -> None:
        if not messagebox.askokcancel("VexPN", "Удалить эту папку безвозвратно?\n\n" + d):
            return
        _stop_processes()
        _remove_shortcuts()
        _schedule_delete_folder(d)
        messagebox.showinfo("VexPN", f"Папка удаляется (через 1 c):\n{d}", parent=r)
        r.destroy()

    ttk.Button(bfr, text="Отмена", command=r.destroy, width=12).pack(side=tk.RIGHT, padx=(8, 0))
    rm = tk.Button(
        bfr,
        text="Удалить",
        width=10,
        command=on_remove,
        bg="#FF3B30",
        fg="white",
        activebackground="#C62828",
        activeforeground="white",
        font=("Segoe UI", 10, "bold"),
        pady=6,
        cursor="hand2",
        relief=tk.FLAT,
    )
    rm.pack(side=tk.RIGHT)

    try:
        r.tk_setPalette(background=BG)
    except Exception:
        pass
    r.mainloop()


if __name__ == "__main__":
    main()
