import json
from dataclasses import dataclass, asdict

from .paths import data_path

CONFIG_FILE = "config.json"
DEFAULT_BASE_URL = "https://vex-gram.ru"


@dataclass
class AppSettings:
    api_base_url: str = DEFAULT_BASE_URL

    @staticmethod
    def path() -> str:
        return str(data_path(CONFIG_FILE))

    @classmethod
    def load(cls) -> "AppSettings":
        p = data_path(CONFIG_FILE)
        if not p.is_file():
            return cls()
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return cls()
        url = str(raw.get("api_base_url") or DEFAULT_BASE_URL).strip().rstrip("/")
        if not url.startswith("http"):
            url = DEFAULT_BASE_URL
        return cls(api_base_url=url)

    def save(self) -> None:
        p = data_path(CONFIG_FILE)
        p.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
