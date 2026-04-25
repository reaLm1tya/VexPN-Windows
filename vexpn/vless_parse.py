"""Парсинг vless:// ссылок в формате 3x-ui (Reality / TLS), как в root/bot/vpn_panel.py."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


@dataclass
class VlessTarget:
    uuid: str
    host: str
    port: int
    name: str
    network: str  # tcp, ws, grpc, httpupgrade
    security: str  # none, tls, reality
    flow: str | None
    sni: str | None
    fp: str | None
    alpn: str | None
    pbk: str | None
    sid: str | None
    spx: str | None
    path: str | None
    host_header: str | None  # for ws/grpc


def parse_vless_uri(uri: str) -> VlessTarget:
    u = uri.strip()
    if not u.lower().startswith("vless://"):
        raise ValueError("Не vless:// ссылка")
    p = urlparse(u)
    if p.scheme.lower() != "vless" or not p.netloc or "@" not in p.netloc:
        raise ValueError("Некорректный vless URI")
    userinfo, hostport = p.netloc.rsplit("@", 1)
    uuid = unquote(userinfo)
    if ":" in hostport:
        host, port_s = hostport.rsplit(":", 1)
        try:
            port = int(port_s)
        except ValueError as e:
            raise ValueError("Некорректный порт") from e
    else:
        host, port = hostport, 443

    frag = unquote(p.fragment) if p.fragment else "VexPN"
    if not frag.strip():
        frag = "VexPN"

    qs: dict[str, list[str]] = parse_qs(p.query)
    g = _first

    vtype = (g(qs, "type") or "tcp").lower()
    sec = (g(qs, "security") or "none").lower()
    enc = (g(qs, "encryption") or "none").lower()
    if enc and enc != "none":
        pass  # 3x-ui vless: encryption=none

    flow = g(qs, "flow")
    if flow is not None:
        flow = unquote(flow)

    sni = g(qs, "sni")
    if sni:
        sni = unquote(sni)
    fp = g(qs, "fp")
    alpn = g(qs, "alpn")
    if alpn:
        alpn = unquote(alpn)
    pbk = g(qs, "pbk")
    if pbk:
        pbk = unquote(pbk)
    sid = g(qs, "sid")
    if sid:
        sid = unquote(sid)
        if "," in sid:
            sid = sid.split(",")[0].strip()
    spx = g(qs, "spx")
    if spx:
        spx = unquote(spx)
    h_host = g(qs, "host")
    if h_host:
        h_host = unquote(h_host)
    path_q = g(qs, "path")
    if path_q and vtype in ("ws", "httpupgrade", "h2", "http", "grpc"):
        path_val: str | None = unquote(path_q)
    else:
        # tcp+reality: в 3x-ui path в ссылке обычно нет; spx — не HTTP path
        path_val = None

    return VlessTarget(
        uuid=uuid,
        host=host,
        port=port,
        name=frag,
        network=vtype,
        security=sec,
        flow=flow,
        sni=sni,
        fp=fp,
        alpn=alpn,
        pbk=pbk,
        sid=sid,
        spx=spx,
        path=path_val,
        host_header=h_host,
    )


def _first(qs: dict[str, list[str]], key: str) -> str | None:
    v: Any = qs.get(key)
    if not v:
        return None
    if isinstance(v, list) and v:
        return v[0]
    return str(v) if v else None
