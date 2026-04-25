import json
import uuid
from dataclasses import asdict, dataclass
from typing import Any

from .paths import data_path

KEYS_FILE = "keys.json"


@dataclass
class VpnKeyRecord:
    id: str
    access_key: str
    name: str
    remaining_days: int
    vless_uri: str | None

    def to_vpn_key(self) -> "VpnKey":
        return VpnKey(
            id=uuid.UUID(self.id),
            access_key=self.access_key,
            name=self.name,
            remaining_days=self.remaining_days,
            vless_uri=self.vless_uri,
        )

    @classmethod
    def from_vpn_key(cls, k: "VpnKey") -> "VpnKeyRecord":
        return cls(
            id=str(k.id),
            access_key=k.access_key,
            name=k.name,
            remaining_days=k.remaining_days,
            vless_uri=k.vless_uri,
        )


@dataclass
class VpnKey:
    id: uuid.UUID
    access_key: str
    name: str
    remaining_days: int
    vless_uri: str | None


def keys_path() -> str:
    return str(data_path(KEYS_FILE))


def load_keys() -> list[VpnKey]:
    p = data_path(KEYS_FILE)
    if not p.is_file():
        return []
    try:
        raw: Any = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return []
    if not isinstance(raw, list):
        return []
    out: list[VpnKey] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            kid = str(item.get("id") or "")
            u = uuid.UUID(kid) if kid else uuid.uuid4()
            out.append(
                VpnKey(
                    id=u,
                    access_key=str(item.get("access_key", "")),
                    name=str(item.get("name", "")),
                    remaining_days=int(item.get("remaining_days", 0)),
                    vless_uri=(str(item["vless_uri"]) if item.get("vless_uri") else None),
                )
            )
        except (ValueError, TypeError, KeyError):
            continue
    return out


def save_keys(keys: list[VpnKey]) -> None:
    p = data_path(KEYS_FILE)
    data = [asdict(VpnKeyRecord.from_vpn_key(k)) for k in keys]
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
