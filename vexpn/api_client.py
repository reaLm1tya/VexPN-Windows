from dataclasses import dataclass
from typing import Any
import json
import urllib.error
import urllib.request

from .key_store import VpnKey
import uuid


@dataclass
class ResolveKeyResponse:
    ok: bool
    key: str
    key_name: str
    active: bool
    remaining_days: int
    vless_uri: str | None
    error_message: str | None = None


def resolve_key(api_base_url: str, raw_key: str, timeout: float = 30.0) -> ResolveKeyResponse:
    base = api_base_url.strip().rstrip("/")
    url = f"{base}/api/vpn/key/resolve"
    body = json.dumps({"key": raw_key}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data: Any = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        if e.code in (400, 404, 401):
            return ResolveKeyResponse(
                ok=False,
                key=raw_key,
                key_name="",
                active=False,
                remaining_days=0,
                vless_uri=None,
                error_message="Ключ не найден, неактивен или неверный формат.",
            )
        return ResolveKeyResponse(
            ok=False,
            key=raw_key,
            key_name="",
            active=False,
            remaining_days=0,
            vless_uri=None,
            error_message="Ошибка HTTP при обращении к backend.",
        )
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TypeError):
        return ResolveKeyResponse(
            ok=False,
            key=raw_key,
            key_name="",
            active=False,
            remaining_days=0,
            vless_uri=None,
            error_message="Ошибка сети или неверный ответ сервера.",
        )
    if not isinstance(data, dict) or not data.get("ok"):
        return ResolveKeyResponse(
            ok=False,
            key=raw_key,
            key_name="",
            active=False,
            remaining_days=0,
            vless_uri=None,
            error_message="Ключ не прошёл проверку.",
        )
    if not data.get("active"):
        return ResolveKeyResponse(
            ok=True,
            key=str(data.get("key", raw_key)),
            key_name=str(data.get("key_name", "")),
            active=False,
            remaining_days=int(data.get("remaining_days", 0)),
            vless_uri=None,
            error_message="Нет активного VPN тарифа по этому ключу.",
        )
    vless = data.get("vless_uri")
    vless_s = str(vless).strip() if vless else None
    return ResolveKeyResponse(
        ok=True,
        key=str(data.get("key", raw_key)),
        key_name=str(data.get("key_name", "")),
        active=True,
        remaining_days=max(0, int(data.get("remaining_days", 0))),
        vless_uri=vless_s or None,
        error_message=None,
    )


def response_to_vpn_key(r: ResolveKeyResponse) -> VpnKey:
    return VpnKey(
        id=uuid.uuid4(),
        access_key=r.key,
        name=r.key_name,
        remaining_days=r.remaining_days,
        vless_uri=r.vless_uri,
    )
