import os
import sys
from pathlib import Path


def app_dir() -> Path:
    if sys.platform == "win32" and "APPDATA" in os.environ:
        return Path(os.environ["APPDATA"]) / "VexPN"
    return Path.home() / ".vexpn"


def data_path(name: str) -> Path:
    p = app_dir() / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def bundled_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def exe_dir() -> Path:
    if getattr(sys, "frozen", False) and sys.executable:
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
