# links.py — منطق کانفیگ‌ها: UUID، لینک VLESS دوگانه (direct + CDN)، ساب‌گروه، کوتاها
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from urllib.parse import quote

from state import LINKS, SUBS, connections, utcnow

# ── پروتکل‌ها ────────────────────────────────────────────────────────────────
PROTOCOLS = ("vless-ws", "xhttp-stream-up", "xhttp-packet-up")
DEFAULT_PROTOCOL = "vless-ws"

# هر کانفیگ منطقی دو پروفایل واقعی دارد تا لینک ساب همیشه دو لینک بدهد:
# پروفایل A = اتصال مستقیم (دامنه Railway، بدون CDN)
# پروفایل B = اتصال از روی CDN/کلادفلر یا در نبود دامنه شخصی، ترنسپورت جایگزین
ROUTES = ("direct", "cdn")
ROUTE_LABELS = {"direct": "مستقیم ⚡", "cdn": "ابری ☁️"}

FINGERPRINTS = ("chrome", "firefox", "safari", "ios", "android", "edge", "360", "qq", "random", "randomized")
DEFAULT_FINGERPRINT = "chrome"

DEFAULT_ALPN = "http/1.1"
DEFAULT_PORT = 443
MIN_PORT, MAX_PORT = 1, 65535


def generate_uuid() -> str:
    h = secrets.token_hex(16)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def clamp_port(port) -> int:
    try:
        p = int(port or DEFAULT_PORT)
    except (TypeError, ValueError):
        return DEFAULT_PORT
    return p if MIN_PORT <= p <= MAX_PORT else DEFAULT_PORT


def norm_fp(fp) -> str:
    fp = (fp or DEFAULT_FINGERPRINT).strip() or DEFAULT_FINGERPRINT
    return fp if fp in FINGERPRINTS else DEFAULT_FINGERPRINT


# ── ساخت لینک VLESS ──────────────────────────────────────────────────────────
def generate_vless_link(
    uuid: str,
    host: str,
    remark: str = "Nova",
    protocol: str = DEFAULT_PROTOCOL,
    fingerprint: str | None = None,
    alpn: str | None = None,
    port: int | None = None,
) -> str:
    fp = norm_fp(fingerprint)
    alpn_val = (alpn or "").strip() or DEFAULT_ALPN
    port_val = clamp_port(port)

    if protocol == "xhttp-packet-up":
        mode = "packet-up"
        path = f"/nx/{mode}/{uuid}"
        params = {
            "encryption": "none", "security": "tls", "type": "xhttp",
            "mode": mode, "host": host, "path": path, "sni": host,
            "fp": fp, "alpn": alpn_val,
        }
    elif protocol == "xhttp-stream-up":
        mode = "stream-up"
        path = f"/nx/{mode}/{uuid}"
        params = {
            "encryption": "none", "security": "tls", "type": "xhttp",
            "mode": mode, "host": host, "path": path, "sni": host,
            "fp": fp, "alpn": alpn_val,
        }
    else:  # vless-ws
        path = f"/ws/{uuid}"
        params = {
            "encryption": "none", "security": "tls", "type": "ws",
            "host": host, "path": path, "sni": host,
            "fp": fp, "alpn": alpn_val,
        }
    query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
    return f"vless://{uuid}@{host}:{port_val}?{query}#{quote(remark)}"


def route_host(link: dict, route: str, fallback_host: str) -> str:
    """هاست واقعی هر مسیر: direct همیشه دامنه Railway؛ cdn دامنه شخصی اگر تنظیم شده باشد."""
    if route == "direct":
        return link.get("direct_host") or fallback_host
    cdn = (link.get("cdn_host") or "").strip()
    return cdn or fallback_host


def route_protocol(link: dict, route: str) -> str:
    """پروتکل هر مسیر: اگر cdn پروتکل جدا نداشت، از ترنسپورت جایگزین استفاده می‌کند
    تا دو لینک هیچ‌وقت دقیقاً یکسان نشوند."""
    if route == "direct":
        return link.get("protocol", DEFAULT_PROTOCOL)
    alt = (link.get("cdn_protocol") or "").strip()
    if alt in PROTOCOLS:
        return alt
    main = link.get("protocol", DEFAULT_PROTOCOL)
    return "xhttp-stream-up" if main == "vless-ws" else "vless-ws"


def route_remark(link: dict, route: str) -> str:
    label = link.get("label", "")
    tag = "D" if route == "direct" else "C"
    return f"Nova-{label}-{tag}"


def vless_link_for_route(link: dict, uid: str, route: str, fallback_host: str) -> str:
    host = route_host(link, route, fallback_host)
    proto = route_protocol(link, route)
    port = link.get("port") if route == "direct" else (link.get("cdn_port") or link.get("port"))
    return generate_vless_link(
        uid, host,
        remark=route_remark(link, route),
        protocol=proto,
        fingerprint=link.get("fingerprint"),
        alpn=link.get("alpn"),
        port=port,
    )


def all_vless_links(link: dict, uid: str, fallback_host: str) -> list[str]:
    """هر کانفیگ همیشه دو لینک می‌دهد (فالبک خودکار)."""
    return [vless_link_for_route(link, uid, r, fallback_host) for r in ROUTES]


# ── وضعیت و کوتاها ───────────────────────────────────────────────────────────
def fmt_bytes(n) -> str:
    try:
        n = float(n or 0)
    except (TypeError, ValueError):
        n = 0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.1f} TB"


def parse_size_to_bytes(value: float, unit: str) -> int:
    mult = {"KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}.get((unit or "GB").upper(), 1024 ** 3)
    return int(float(value or 0) * mult)


def parse_speed_to_bytes(value: float) -> int:
    """Mbps -> byte/s"""
    return int(float(value or 0) * 1_000_000 / 8)


def is_link_expired(link: dict) -> bool:
    exp = link.get("expires_at")
    if not exp:
        return False
    try:
        return utcnow() >= datetime.fromisoformat(exp)
    except (ValueError, TypeError):
        return False


def is_link_allowed(link: dict | None) -> bool:
    if not link or not link.get("active", True):
        return False
    if is_link_expired(link):
        return False
    limit = int(link.get("limit_bytes", 0) or 0)
    if limit > 0 and int(link.get("used_bytes", 0) or 0) >= limit:
        return False
    return True


def unique_ips_for_uuid(uid: str) -> set:
    return {c.get("ip") for c in connections.values() if c.get("uuid") == uid and c.get("ip")}


def is_ip_allowed(link: dict | None, uid: str, ip: str) -> bool:
    if not link:
        return False
    limit = int(link.get("ip_limit", 0) or 0)
    if limit <= 0:
        return True
    ips = unique_ips_for_uuid(uid)
    if ip in ips:
        return True
    return len(ips) < limit


def link_summary(uid: str, link: dict, host: str) -> dict:
    limit = int(link.get("limit_bytes", 0) or 0)
    used = int(link.get("used_bytes", 0) or 0)
    pct = round(used / limit * 100, 1) if limit > 0 else 0.0
    return {
        "uuid": uid,
        "label": link.get("label", ""),
        "active": bool(link.get("active", True)),
        "protocol": link.get("protocol", DEFAULT_PROTOCOL),
        "allowed": is_link_allowed(link),
        "expired": is_link_expired(link),
        "used_bytes": used,
        "limit_bytes": limit,
        "used_h": fmt_bytes(used),
        "limit_h": fmt_bytes(limit) if limit else "نامحدود",
        "pct": pct,
        "ips": len(unique_ips_for_uuid(uid)),
        "ip_limit": int(link.get("ip_limit", 0) or 0),
        "expires_at": link.get("expires_at"),
        "vless_links": all_vless_links(link, uid, host),
    }


async def make_link(
    label: str = "کاربر",
    protocol: str = DEFAULT_PROTOCOL,
    fingerprint: str = DEFAULT_FINGERPRINT,
    alpn: str = "",
    port: int = DEFAULT_PORT,
    limit_bytes: int = 0,
    speed_limit_bytes: int = 0,
    ip_limit: int = 0,
    expires_days: int = 0,
    cdn_host: str = "",
    cdn_protocol: str = "",
    cdn_port: int = 0,
    direct_host: str = "",
    note: str = "",
    sub_id: str | None = None,
) -> tuple[str, dict]:
    from state import LINKS_LOCK, SUBS  # import محلی برای جلوگیری از چرخه
    uid = generate_uuid()
    expires_at = None
    if expires_days and int(expires_days) > 0:
        expires_at = (utcnow() + timedelta(days=int(expires_days))).isoformat()
    link = {
        "label": (label or "کاربر").strip() or "کاربر",
        "protocol": protocol if protocol in PROTOCOLS else DEFAULT_PROTOCOL,
        "fingerprint": norm_fp(fingerprint),
        "alpn": (alpn or "").strip(),
        "port": clamp_port(port),
        "limit_bytes": int(limit_bytes or 0),
        "used_bytes": 0,
        "speed_limit_bytes": int(speed_limit_bytes or 0),
        "ip_limit": int(ip_limit or 0),
        "expires_at": expires_at,
        "expires_days": int(expires_days or 0),
        "active": True,
        "created_at": utcnow().isoformat(),
        "cdn_host": (cdn_host or "").strip(),
        "cdn_protocol": (cdn_protocol or "").strip() if (cdn_protocol or "").strip() in PROTOCOLS else "",
        "cdn_port": clamp_port(cdn_port) if cdn_port else 0,
        "direct_host": (direct_host or "").strip(),
        "note": (note or "").strip(),
        "sub_id": sub_id,
    }
    async with LINKS_LOCK:
        LINKS[uid] = link
        if sub_id and sub_id in SUBS:
            ids = SUBS[sub_id].setdefault("link_ids", [])
            if uid not in ids:
                ids.append(uid)
    return uid, link


async def remove_link(uid: str) -> dict | None:
    from state import LINKS_LOCK, SUBS
    from limits import reset_bucket
    async with LINKS_LOCK:
        link = LINKS.pop(uid, None)
        if link:
            for s in SUBS.values():
                ids = s.get("link_ids", [])
                if uid in ids:
                    ids.remove(uid)
    if link:
        reset_bucket(uid)
    return link


async def set_link_active(uid: str, active: bool) -> dict | None:
    from state import LINKS_LOCK
    async with LINKS_LOCK:
        link = LINKS.get(uid)
        if link is None:
            return None
        link["active"] = bool(active)
        return link


# ── گروه ساب ─────────────────────────────────────────────────────────────────
async def create_sub_group(name: str = "گروه جدید", desc: str = "", password: str = "") -> tuple[str, dict]:
    from state import SUBS
    sub_id = generate_uuid()
    uuid_key = secrets.token_urlsafe(16)
    import asyncio as _a
    sub = {
        "name": (name or "گروه جدید").strip() or "گروه جدید",
        "desc": (desc or "").strip(),
        "password": (password or "").strip(),
        "uuid_key": uuid_key,
        "link_ids": [],
        "created_at": utcnow().isoformat(),
    }
    SUBS[sub_id] = sub
    return sub_id, sub


async def remove_sub_group(sub_id: str) -> dict | None:
    from state import LINKS_LOCK, SUBS
    sub = SUBS.pop(sub_id, None)
    if sub:
        async with LINKS_LOCK:
            for uid in sub.get("link_ids", []):
                if uid in LINKS:
                    LINKS[uid]["sub_id"] = None
    return sub


async def set_link_sub(uid: str, sub_id: str | None) -> bool:
    from state import LINKS_LOCK, SUBS
    async with LINKS_LOCK:
        link = LINKS.get(uid)
        if link is None:
            return False
        old = link.get("sub_id")
        if old and old in SUBS:
            ids = SUBS[old].get("link_ids", [])
            if uid in ids:
                ids.remove(uid)
        link["sub_id"] = sub_id
        if sub_id and sub_id in SUBS:
            ids = SUBS[sub_id].setdefault("link_ids", [])
            if uid not in ids:
                ids.append(uid)
        return True
