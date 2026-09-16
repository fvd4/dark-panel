# main.py — NovaPanel: اپ FastAPI، احراز هویت، API مدیریت، ساب و صفحات عمومی
from __future__ import annotations

import asyncio
import base64
import os
from datetime import datetime

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel

try:
    import qrcode
    from io import BytesIO
    from fastapi.responses import Response as _QRResponse
    _HAS_QR = True
except ImportError:
    _HAS_QR = False

from limits import reset_bucket
from links import (
    DEFAULT_ALPN, DEFAULT_FINGERPRINT, DEFAULT_PORT, DEFAULT_PROTOCOL,
    FINGERPRINTS, PROTOCOLS,
    all_vless_links, clamp_port, create_sub_group, fmt_bytes, generate_uuid,
    is_link_allowed, is_link_expired, link_summary, make_link, norm_fp,
    parse_size_to_bytes, parse_speed_to_bytes, remove_link, remove_sub_group,
    route_host, set_link_active, set_link_sub, unique_ips_for_uuid,
    vless_link_for_route,
)
from state import (
    AUTH, CONFIG, LINKS, LINKS_LOCK, SESSION_COOKIE, SUBS, activity_logs,
    connections, create_session, destroy_session, error_logs, hash_password,
    hourly_traffic, is_valid_session, load_auth_state, load_state, log_activity,
    logger, save_state, stats, utcnow,
)
from transport import router as xhttp_router, websocket_tunnel, xhttp_sessions

app = FastAPI(title="NovaPanel", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
app.include_router(xhttp_router)
app.add_api_websocket_route("/ws/{uuid}", websocket_tunnel)
app.state.http_client = None

DEFAULT_CDN_HOST = os.environ.get("CDN_HOST", "").strip()
DEFAULT_DIRECT_HOST = os.environ.get("DIRECT_HOST", "").strip()


# ── احراز هویت ───────────────────────────────────────────────────────────────
async def require_auth(request: Request):
    if not await is_valid_session(request.cookies.get(SESSION_COOKIE)):
        raise HTTPException(status_code=401, detail="unauthorized")
    return True


def get_host(request: Request | None = None) -> str:
    if request is not None:
        h = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if h:
            h = h.split(":")[0].strip()
            if h:
                CONFIG["host"] = h
                return h
    return CONFIG["host"]


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "نامشخص"


@app.on_event("startup")
async def startup():
    limits = httpx.Limits(max_connections=500, max_keepalive_connections=100)
    timeout = httpx.Timeout(30.0, connect=10.0)
    app.state.http_client = httpx.AsyncClient(limits=limits, timeout=timeout, follow_redirects=True)
    await load_state()
    await load_auth_state()
    try:
        from bot import start_bot
        await start_bot(lambda: get_host(None))
    except Exception as e:
        logger.warning(f"Bot not started: {e}")
    log_activity("system", "سرور نوا راه‌اندازی شد", "ok")
    logger.info(f"NovaPanel started on port {CONFIG['port']}")


@app.on_event("shutdown")
async def shutdown():
    await save_state()
    try:
        from bot import stop_bot
        await stop_bot()
    except Exception:
        pass
    if app.state.http_client:
        await app.state.http_client.aclose()


# ── مدل‌ها ───────────────────────────────────────────────────────────────────
class LoginBody(BaseModel):
    password: str = ""


class LinkCreateBody(BaseModel):
    label: str = "کاربر"
    protocol: str = DEFAULT_PROTOCOL
    fingerprint: str = DEFAULT_FINGERPRINT
    alpn: str = ""
    port: int = DEFAULT_PORT
    limit_value: float = 0
    limit_unit: str = "GB"
    speed_mbps: float = 0
    ip_limit: int = 0
    expires_days: int = 0
    cdn_host: str = ""
    cdn_protocol: str = ""
    cdn_port: int = 0
    direct_host: str = ""
    note: str = ""
    sub_id: str | None = None


# ── لاگین ────────────────────────────────────────────────────────────────────
@app.post("/api/login")
async def api_login(body: LoginBody, request: Request):
    if hash_password(body.password or "") == AUTH.get("password_hash"):
        token = await create_session()
        log_activity("auth", f"ورود موفق از {client_ip(request)}", "ok")
        resp = JSONResponse({"ok": True})
        resp.set_cookie(SESSION_COOKIE, token, max_age=60 * 60 * 24 * 365,
                        httponly=True, samesite="lax")
        return resp
    log_activity("auth", f"تلاش ورود ناموفق از {client_ip(request)}", "warn")
    raise HTTPException(status_code=401, detail="wrong password")


@app.post("/api/logout")
async def api_logout(request: Request):
    await destroy_session(request.cookies.get(SESSION_COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@app.get("/api/me")
async def api_me(_=Depends(require_auth)):
    return {"ok": True}


# ── داشبورد ──────────────────────────────────────────────────────────────────
@app.get("/api/overview")
async def api_overview(request: Request, _=Depends(require_auth)):
    host = get_host(request)
    async with LINKS_LOCK:
        items = list(LINKS.items())
    links = [link_summary(uid, l, host) for uid, l in items]
    active_links = sum(1 for uid, l in items if is_link_allowed(l))
    return {
        "host": host,
        "default_cdn": DEFAULT_CDN_HOST,
        "now": utcnow().isoformat(),
        "uptime_secs": int(datetime.now().timestamp() - stats["start_time"]),
        "totals": {
            "links": len(items),
            "active_links": active_links,
            "groups": len(SUBS),
            "online": len(connections),
            "xhttp_sessions": len(xhttp_sessions),
            "total_bytes": stats["total_bytes"],
            "total_bytes_h": fmt_bytes(stats["total_bytes"]),
            "total_requests": stats["total_requests"],
            "total_errors": stats["total_errors"],
        },
        "hourly": dict(hourly_traffic),
        "links": links,
    }


@app.get("/api/connections")
async def api_connections(_=Depends(require_auth)):
    out = []
    for cid, c in connections.items():
        link = LINKS.get(c.get("uuid"), {})
        out.append({
            "id": cid, "ip": c.get("ip"), "transport": c.get("transport"),
            "label": link.get("label", "?"), "bytes": c.get("bytes", 0),
            "bytes_h": fmt_bytes(c.get("bytes", 0)),
            "connected_at": c.get("connected_at"),
        })
    return {"connections": out}


@app.get("/api/logs")
async def api_logs(kind: str = "all", _=Depends(require_auth)):
    data = {}
    if kind in ("all", "activity"):
        data["activity"] = list(activity_logs)[-100:][::-1]
    if kind in ("all", "errors"):
        data["errors"] = list(error_logs)[-100:][::-1]
    return data


# ── کانفیگ‌ها ────────────────────────────────────────────────────────────────
@app.post("/api/links")
async def api_create_link(body: LinkCreateBody, request: Request, _=Depends(require_auth)):
    host = get_host(request)
    proto = body.protocol if body.protocol in PROTOCOLS else DEFAULT_PROTOCOL
    uid, link = await make_link(
        label=body.label, protocol=proto,
        fingerprint=norm_fp(body.fingerprint), alpn=body.alpn,
        port=clamp_port(body.port),
        limit_bytes=parse_size_to_bytes(body.limit_value, body.limit_unit) if (body.limit_value or 0) > 0 else 0,
        speed_limit_bytes=parse_speed_to_bytes(body.speed_mbps) if (body.speed_mbps or 0) > 0 else 0,
        ip_limit=max(0, int(body.ip_limit or 0)),
        expires_days=max(0, int(body.expires_days or 0)),
        cdn_host=body.cdn_host or DEFAULT_CDN_HOST,
        cdn_protocol=body.cdn_protocol,
        cdn_port=clamp_port(body.cdn_port) if body.cdn_port else 0,
        direct_host=body.direct_host or DEFAULT_DIRECT_HOST,
        note=body.note, sub_id=body.sub_id,
    )
    log_activity("link", f"کانفیگ «{link['label']}» ساخته شد", "ok")
    await save_state()
    return link_summary(uid, link, host)


@app.get("/api/links")
async def api_list_links(request: Request, _=Depends(require_auth)):
    host = get_host(request)
    async with LINKS_LOCK:
        items = list(LINKS.items())
    return {"links": [link_summary(uid, l, host) for uid, l in items]}


@app.get("/api/links/{uid}")
async def api_get_link(uid: str, request: Request, _=Depends(require_auth)):
    host = get_host(request)
    link = LINKS.get(uid)
    if not link:
        raise HTTPException(status_code=404, detail="not found")
    d = link_summary(uid, link, host)
    d["raw"] = dict(link)
    return d


@app.patch("/api/links/{uid}")
async def api_update_link(uid: str, request: Request, _=Depends(require_auth)):
    body = await request.json()
    host = get_host(request)
    async with LINKS_LOCK:
        link = LINKS.get(uid)
        if not link:
            raise HTTPException(status_code=404, detail="not found")
        if "label" in body:
            link["label"] = (body.get("label") or "کاربر").strip() or "کاربر"
        if "note" in body:
            link["note"] = (body.get("note") or "").strip()
        if "protocol" in body and body["protocol"] in PROTOCOLS:
            link["protocol"] = body["protocol"]
        if "fingerprint" in body:
            link["fingerprint"] = norm_fp(body.get("fingerprint"))
        if "alpn" in body:
            link["alpn"] = (body.get("alpn") or "").strip()
        if "port" in body:
            link["port"] = clamp_port(body.get("port"))
        if "limit_value" in body or "limit_unit" in body:
            v = float(body.get("limit_value", 0) or 0)
            u = body.get("limit_unit", "GB") or "GB"
            link["limit_bytes"] = parse_size_to_bytes(v, u) if v > 0 else 0
        if "speed_mbps" in body:
            link["speed_limit_bytes"] = parse_speed_to_bytes(float(body.get("speed_mbps") or 0))
            reset_bucket(uid)
        if "ip_limit" in body:
            link["ip_limit"] = max(0, int(body.get("ip_limit") or 0))
        if "expires_days" in body:
            from datetime import timedelta
            days = max(0, int(body.get("expires_days") or 0))
            link["expires_days"] = days
            link["expires_at"] = (utcnow() + timedelta(days=days)).isoformat() if days > 0 else None
        if "cdn_host" in body:
            link["cdn_host"] = (body.get("cdn_host") or "").strip()
        if "cdn_protocol" in body:
            cp = (body.get("cdn_protocol") or "").strip()
            link["cdn_protocol"] = cp if cp in PROTOCOLS else ""
        if "cdn_port" in body:
            link["cdn_port"] = clamp_port(body.get("cdn_port")) if body.get("cdn_port") else 0
        if "direct_host" in body:
            link["direct_host"] = (body.get("direct_host") or "").strip()
    if "sub_id" in body:
        await set_link_sub(uid, body.get("sub_id"))
    log_activity("link", f"کانفیگ «{link['label']}» ویرایش شد", "info")
    await save_state()
    return link_summary(uid, link, host)


@app.delete("/api/links/{uid}")
async def api_delete_link(uid: str, _=Depends(require_auth)):
    link = await remove_link(uid)
    if not link:
        raise HTTPException(status_code=404, detail="not found")
    log_activity("link", f"کانفیگ «{link.get('label', '?')}» حذف شد", "warn")
    await save_state()
    return {"ok": True}


@app.post("/api/links/{uid}/toggle")
async def api_toggle_link(uid: str, request: Request, _=Depends(require_auth)):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    link = LINKS.get(uid)
    if not link:
        raise HTTPException(status_code=404, detail="not found")
    active = body.get("active")
    if active is None:
        active = not link.get("active", True)
    link = await set_link_active(uid, bool(active))
    log_activity("link", f"کانفیگ «{link['label']}» {'فعال' if active else 'غیرفعال'} شد", "info")
    await save_state()
    return {"ok": True, "active": bool(active)}


@app.post("/api/links/{uid}/reset")
async def api_reset_usage(uid: str, _=Depends(require_auth)):
    async with LINKS_LOCK:
        link = LINKS.get(uid)
        if not link:
            raise HTTPException(status_code=404, detail="not found")
        link["used_bytes"] = 0
    log_activity("link", f"مصرف کانفیگ «{link['label']}» صفر شد", "info")
    await save_state()
    return {"ok": True}


# ── گروه‌های ساب ─────────────────────────────────────────────────────────────
@app.get("/api/groups")
async def api_list_groups(request: Request, _=Depends(require_auth)):
    host = get_host(request)
    out = []
    for sid, s in SUBS.items():
        out.append({
            "sub_id": sid, "name": s.get("name"), "desc": s.get("desc", ""),
            "protected": bool(s.get("password")),
            "count": len(s.get("link_ids", [])),
            "public_url": f"https://{host}/p/{s.get('uuid_key')}",
            "sub_url": f"https://{host}/sub-group/{s.get('uuid_key')}",
            "created_at": s.get("created_at"),
        })
    return {"groups": out}


@app.post("/api/groups")
async def api_create_group(request: Request, _=Depends(require_auth)):
    body = await request.json()
    host = get_host(request)
    sid, s = await create_sub_group(body.get("name", "گروه جدید"),
                                    body.get("desc", ""), body.get("password", ""))
    log_activity("group", f"گروه ساب «{s['name']}» ساخته شد", "ok")
    await save_state()
    return {
        "sub_id": sid, "name": s["name"],
        "public_url": f"https://{host}/p/{s['uuid_key']}",
        "sub_url": f"https://{host}/sub-group/{s['uuid_key']}",
    }


@app.delete("/api/groups/{sid}")
async def api_delete_group(sid: str, _=Depends(require_auth)):
    sub = await remove_sub_group(sid)
    if not sub:
        raise HTTPException(status_code=404, detail="not found")
    log_activity("group", f"گروه «{sub.get('name', '?')}» حذف شد", "warn")
    await save_state()
    return {"ok": True}


@app.post("/api/groups/{sid}/assign")
async def api_assign(sid: str, request: Request, _=Depends(require_auth)):
    body = await request.json()
    if sid not in SUBS:
        raise HTTPException(status_code=404, detail="group not found")
    for uid in body.get("link_ids", []):
        await set_link_sub(uid, sid)
    await save_state()
    return {"ok": True}


@app.post("/api/links/{uid}/group")
async def api_set_link_group(uid: str, request: Request, _=Depends(require_auth)):
    body = await request.json()
    sub_id = body.get("sub_id")
    if sub_id and sub_id not in SUBS:
        raise HTTPException(status_code=404, detail="group not found")
    if not await set_link_sub(uid, sub_id):
        raise HTTPException(status_code=404, detail="link not found")
    await save_state()
    return {"ok": True}


# ── ساب تک‌کاربره و گروهی (متن base64 برای کلاینت‌ها) ─────────────────────────
def _sub_text_for_links(items: list[tuple[str, dict]], host: str) -> str:
    lines: list[str] = []
    for uid, link in items:
        if not is_link_allowed(link):
            continue
        lines.extend(all_vless_links(link, uid, host))
    return base64.b64encode("\n".join(lines).encode()).decode()


@app.get("/sub/{uid}")
async def subscription_single(uid: str, request: Request):
    host = get_host(request)
    link = LINKS.get(uid)
    if not link:
        raise HTTPException(status_code=404, detail="not found")
    vless = "\n".join(all_vless_links(link, uid, host))
    return PlainTextResponse(base64.b64encode(vless.encode()).decode())


@app.get("/sub-group/{uuid_key}")
async def sub_group_subscription(uuid_key: str, request: Request):
    host = get_host(request)
    sub = next((s for s in SUBS.values() if s.get("uuid_key") == uuid_key), None)
    if not sub:
        raise HTTPException(status_code=404, detail="not found")
    # اگر با مرورگر (گوگل/کروم) باز شد → صفحه شیک عمومی؛ اگر با اپ V2Ray → متن ساب
    ua = (request.headers.get("user-agent") or "").lower()
    is_browser = "mozilla" in ua and request.query_params.get("format") != "text"
    if is_browser:
        from fastapi.responses import RedirectResponse
        pw = request.query_params.get("password", "")
        dest = f"/p/{uuid_key}" + (f"?password={pw}" if pw else "")
        return RedirectResponse(dest, status_code=302)
    if sub.get("password"):
        pw = request.query_params.get("password", "")
        import hashlib as _h
        if _h.sha256(f"{pw}".encode()).hexdigest() != _h.sha256(sub["password"].encode()).hexdigest():
            raise HTTPException(status_code=403, detail="password required")
    items = [(lid, LINKS[lid]) for lid in sub.get("link_ids", []) if lid in LINKS]
    return PlainTextResponse(_sub_text_for_links(items, host))


# ── QR کد ────────────────────────────────────────────────────────────────────
@app.get("/api/qr")
async def api_qr(text: str = "", _=Depends(require_auth)):
    if not _HAS_QR:
        raise HTTPException(status_code=501, detail="qrcode not installed")
    from fastapi.responses import Response
    from io import BytesIO
    img = qrcode.make((text or "")[:2000])
    buf = BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


@app.get("/qr-pub")
async def qr_public(text: str = ""):
    """QR عمومی برای صفحه ساب (بدون نیاز به لاگین)."""
    if not _HAS_QR:
        raise HTTPException(status_code=501, detail="qrcode not installed")
    from fastapi.responses import Response
    from io import BytesIO
    img = qrcode.make((text or "")[:2000])
    buf = BytesIO()
    img.save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


# ── صفحات وب ─────────────────────────────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
async def page_login():
    from ui import LOGIN_HTML
    return LOGIN_HTML


@app.get("/dashboard", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    if not await is_valid_session(request.cookies.get(SESSION_COOKIE)):
        return RedirectResponse("/login", status_code=302)
    from ui import DASHBOARD_HTML
    return DASHBOARD_HTML


@app.get("/", response_class=HTMLResponse)
async def page_root(request: Request):
    if await is_valid_session(request.cookies.get(SESSION_COOKIE)):
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/p/{uuid_key}", response_class=HTMLResponse)
async def public_sub_page_route(uuid_key: str, request: Request):
    host = get_host(request)
    sub = next((s for s in SUBS.values() if s.get("uuid_key") == uuid_key), None)
    if not sub:
        raise HTTPException(status_code=404, detail="not found")
    pw = request.query_params.get("password", "")
    authed = (not sub.get("password")) or (pw and pw == sub.get("password"))
    # در ui.py از /api/qr استفاده شده که لاگین می‌خواهد؛ برای صفحه عمومی بازنویسی می‌کنیم
    items = []
    if authed:
        for lid in sub.get("link_ids", []):
            link = LINKS.get(lid)
            if link:
                items.append((lid, link, all_vless_links(link, lid, host)))
    from ui import public_sub_page
    page = public_sub_page(sub, items, host, authed)
    return HTMLResponse(page.replace("/api/qr?text=", "/qr-pub?text="))


# ── تغییر رمز ────────────────────────────────────────────────────────────────
@app.post("/api/password")
async def api_change_password(request: Request, _=Depends(require_auth)):
    body = await request.json()
    cur, new = body.get("current", ""), (body.get("new") or "").strip()
    if hash_password(cur or "") != AUTH.get("password_hash"):
        raise HTTPException(status_code=403, detail="wrong current password")
    if len(new) < 4:
        raise HTTPException(status_code=400, detail="password too short")
    AUTH["password_hash"] = hash_password(new)
    log_activity("auth", "رمز ادمین تغییر کرد", "warn")
    await save_state()
    return {"ok": True}
