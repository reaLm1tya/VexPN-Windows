"""Генерация config.json для sing-box (TUN + VLESS / Reality) под Windows."""
from __future__ import annotations

import json
from typing import Any

from .vless_parse import VlessTarget, parse_vless_uri


def vless_to_outbound(uri: str) -> dict[str, Any]:
    t = parse_vless_uri(uri)
    o: dict[str, Any] = {
        "type": "vless",
        "tag": "proxy",
        "server": t.host,
        "server_port": t.port,
        "uuid": t.uuid,
    }
    if t.flow:
        o["flow"] = t.flow

    n = t.network
    if n in ("ws", "http", "h2", "httpupgrade"):
        wstype = "httpupgrade" if n in ("httpupgrade", "h2", "http") else "ws"
        path = (t.path or "/").strip() or "/"
        host_h = t.host_header or t.sni or t.host
        o["transport"] = {
            "type": wstype,
            "path": path,
            "headers": {"Host": host_h},
        }
    elif n == "grpc":
        svc = (t.path or "GunService").strip().strip("/") or "GunService"
        o["transport"] = {
            "type": "grpc",
            "service_name": svc,
        }
    # tcp: без transport

    if t.security in ("tls", "reality"):
        tls: dict[str, Any] = {
            "enabled": True,
        }
        if t.sni:
            tls["server_name"] = t.sni
        if t.alpn and t.alpn != "none":
            parts = [a.strip() for a in t.alpn.split(",") if a.strip()]
            if parts:
                tls["alpn"] = parts
        if t.fp:
            tls["utls"] = {
                "enabled": True,
                "fingerprint": t.fp,
            }
        if t.security == "reality" and t.pbk and t.sid:
            tls["reality"] = {
                "enabled": True,
                "public_key": t.pbk,
                "short_id": t.sid,
            }
        o["tls"] = tls

    return o


def build_tun_config(vless_uri: str) -> str:
    """JSON для sing-box run -c: полный TUN, весь трафик через VLESS."""
    out = vless_to_outbound(vless_uri)
    data: dict[str, Any] = {
        "log": {"level": "info", "timestamp": True},
        "dns": {
            "servers": [
                {"type": "udp", "server": "8.8.8.8", "server_port": 53},
                {"type": "udp", "server": "1.1.1.1", "server_port": 53},
            ],
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "address": ["172.19.0.1/30"],
                "mtu": 1500,
                "auto_route": True,
                "strict_route": True,
                "stack": "system",
                "sniff": True,
                "sniff_override_destination": True,
            }
        ],
        "outbounds": [
            out,
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"},
        ],
        "route": {
            "auto_detect_interface": True,
            "final": "proxy",
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _debug_parsed(vless_uri: str) -> VlessTarget:
    return parse_vless_uri(vless_uri)
