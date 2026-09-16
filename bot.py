# bot.py — ربات مدیریت تلگرام NovaPanel (long polling، بدون نیاز به دامنه)
from __future__ import annotations

import asyncio
import os
import re

import httpx

from links import (
    DEFAULT_ALPN, DEFAULT_FINGERPRINT, DEFAULT_PORT, DEFAULT_PROTOCOL,
    FINGERPRINTS, MAX_PORT, MIN_PORT, PROTOCOLS,
    all_vless_links, create_sub_group, fmt_bytes, is_link_allowed,
    make_link, parse_size_to_bytes, parse_speed_to_bytes,
    remove_link, remove_sub_group, set_link_active, set_link_sub,
)
from state import LINKS, SUBS, connections, log_activity, logger, save_state, stats

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
_admin_ids_raw = os.environ.get("TELEGRAM_ADMIN_IDS", "").strip()
ADMIN_IDS = {int(x) for x in _admin_ids_raw.replace(" ", "").split(",") if x.isdigit()} if _admin_ids_raw else set()

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"
PAGE_SIZE = 6

_client: httpx.AsyncClient | None = None
_poll_task: asyncio.Task | None = None
_running = False
_pending: dict = {}
_host_fn = lambda: "localhost"  # توسط main تنظیم می‌شود


def _host() -> str:
    try:
        return _host_fn() or "localhost"
    except Exception:
        return "localhost"


WIZARD_STEPS = ["label", "protocol", "fingerprint", "alpn", "port", "volume", "speed", "iplimit", "days", "cdn"]

PROTOCOL_LABELS = {
    "vless-ws": "VLESS + WebSocket ⚡",
    "xhttp-stream-up": "XHTTP stream-up 🚀",
    "xhttp-packet-up": "XHTTP packet-up 📦",
}


def _protocol_label(p: str) -> str:
    return PROTOCOL_LABELS.get(p, p)


_VOLUME_RE = re.compile(r"^([\d.]+)\s*(GB|MB|KB)?$", re.IGNORECASE)
_SPEED_RE = re.compile(r"^([\d.]+)\s*(MBIT|MBPS|MB|KB)?$", re.IGNORECASE)


def _parse_volume_text(text: str):
    m = _VOLUME_RE.match(text.strip())
    if not m:
        return None
    try:
        value = float(m.group(1))
    except ValueError:
        return None
    if value <= 0:
        return 0
    return parse_size_to_bytes(value, (m.group(2) or "GB").upper())


def _parse_speed_text(text: str):
    m = _SPEED_RE.match(text.strip())
    if not m:
        return None
    try:
        value = float(m.group(1))
    except ValueError:
        return None
    if value <= 0:
        return 0
    unit = (m.group(2) or "MBIT").upper()
    if unit in ("MBIT", "MBPS"):
        return parse_speed_to_bytes(value)
    mult = {"MB": 1024 ** 2, "KB": 1024}.get(unit, 1024 ** 2)
    return int(value * mult)


def _parse_nonneg_int(text: str):
    try:
        return max(0, int(text.strip()))
    except ValueError:
        return None


# ── Telegram API ─────────────────────────────────────────────────────────────
async def _call(method: str, **params):
    if _client is None:
        return None
    try:
        r = await _client.post(f"{API_BASE}/{method}", json=params, timeout=40)
        data = r.json()
        if not data.get("ok"):
            logger.warning(f"Telegram API {method} failed: {data}")
        return data
    except Exception as e:
        logger.warning(f"Telegram API {method} error: {e}")
        return None


async def _send(chat_id: int, text: str, kb: dict | None = None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb:
        payload["reply_markup"] = kb
    return await _call("sendMessage", **payload)


async def _edit(chat_id: int, message_id: int, text: str, kb: dict | None = None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text,
               "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb:
        payload["reply_markup"] = kb
    res = await _call("editMessageText", **payload)
    if res is None or not res.get("ok"):
        await _send(chat_id, text, kb)


async def _answer_cb(cb_id: str, text: str = ""):
    await _call("answerCallbackQuery", callback_query_id=cb_id, text=text)


def _is_admin(chat_id: int) -> bool:
    return chat_id in ADMIN_IDS


# ── کیبوردها ─────────────────────────────────────────────────────────────────
def _main_menu_kb():
    return {"inline_keyboard": [
        [{"text": "📊 آمار", "callback_data": "stats"}],
        [{"text": "📋 لیست کانفیگ‌ها", "callback_data": "list:0"}],
        [{"text": "➕ ساخت کانفیگ جدید", "callback_data": "newcfg"}],
        [{"text": "🗂 گروه‌های ساب", "callback_data": "subs:0"}],
        [{"text": "🔄 رفرش", "callback_data": "menu"}],
    ]}


def _stats_text() -> str:
    online = len(connections)
    active = sum(1 for l in LINKS.values() if is_link_allowed(l))
    return (
        "📊 <b>آمار NovaPanel</b>\n\n"
        f"🔗 کانفیگ‌ها: {len(LINKS)} (فعال: {active})\n"
        f"🟢 آنلاین: {online}\n"
        f"🗂 گروه‌ها: {len(SUBS)}\n"
        f"📦 ترافیک کل: {fmt_bytes(stats.get('total_bytes', 0))}"
    )


def _links_list_kb(page: int):
    items = sorted(LINKS.items(), key=lambda kv: kv[1].get("created_at", ""), reverse=True)
    start = page * PAGE_SIZE
    rows = []
    for uid, l in items[start:start + PAGE_SIZE]:
        dot = "🟢" if is_link_allowed(l) else "🔴"
        rows.append([{"text": f"{dot} {l.get('label', '?')[:28]}", "callback_data": f"view:{uid}"}])
    nav = []
    if start > 0:
        nav.append({"text": "◀ قبلی", "callback_data": f"list:{page - 1}"})
    if start + PAGE_SIZE < len(items):
        nav.append({"text": "بعدی ▶", "callback_data": f"list:{page + 1}"})
    if nav:
        rows.append(nav)
    rows.append([{"text": "➕ ساخت کانفیگ جدید", "callback_data": "newcfg"}])
    rows.append([{"text": "⬅ منوی اصلی", "callback_data": "menu"}])
    return {"inline_keyboard": rows}


def _link_detail_kb(uid: str, active: bool):
    return {"inline_keyboard": [
        [{"text": "🔗 نمایش لینک‌ها (مستقیم + ابری)", "callback_data": f"link:{uid}"}],
        [{"text": "🗂 گروه ساب", "callback_data": f"cfggroup:{uid}"}],
        [{"text": ("⛔ غیرفعال‌سازی" if active else "✅ فعال‌سازی"), "callback_data": f"toggle:{uid}"}],
        [{"text": "🗑 حذف کانفیگ", "callback_data": f"del:{uid}"}],
        [{"text": "⬅ بازگشت به لیست", "callback_data": "list:0"}],
    ]}


def _confirm_delete_kb(uid: str):
    return {"inline_keyboard": [
        [{"text": "✅ بله، حذف کن", "callback_data": f"delok:{uid}"},
         {"text": "❌ انصراف", "callback_data": f"view:{uid}"}],
    ]}


def _wizard_cancel_kb():
    return {"inline_keyboard": [[{"text": "❌ انصراف", "callback_data": "w:cancel"}]]}


def _wizard_protocol_kb():
    rows = [[{"text": _protocol_label(p), "callback_data": f"w:proto:{p}"}] for p in PROTOCOLS]
    rows.append([{"text": "❌ انصراف", "callback_data": "w:cancel"}])
    return {"inline_keyboard": rows}


def _wizard_fp_kb():
    rows, row = [], []
    for fp in FINGERPRINTS:
        row.append({"text": fp.capitalize(), "callback_data": f"w:fp:{fp}"})
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "❌ انصراف", "callback_data": "w:cancel"}])
    return {"inline_keyboard": rows}


def _wizard_skip_kb(step_key: str, label: str):
    return {"inline_keyboard": [
        [{"text": label, "callback_data": f"w:skip:{step_key}"}],
        [{"text": "❌ انصراف", "callback_data": "w:cancel"}],
    ]}


ALPN_PRESET_MAP = {"p1": "http/1.1", "p2": "h2,http/1.1", "p3": "h2"}


def _wizard_alpn_kb():
    return {"inline_keyboard": [
        [{"text": "🔤 http/1.1 (پیشنهادی)", "callback_data": "w:alpnpreset:p1"}],
        [{"text": "🔤 h2,http/1.1", "callback_data": "w:alpnpreset:p2"}],
        [{"text": "🔤 h2", "callback_data": "w:alpnpreset:p3"}],
        [{"text": "⏭ پیش‌فرض پروتکل", "callback_data": "w:skip:alpn"}],
        [{"text": "❌ انصراف", "callback_data": "w:cancel"}],
    ]}


def _wizard_confirm_kb():
    return {"inline_keyboard": [
        [{"text": "✅ ساخت کانفیگ", "callback_data": "w:confirm"}],
        [{"text": "❌ انصراف", "callback_data": "w:cancel"}],
    ]}


def _wizard_prompt(step: str, data: dict) -> str:
    n = WIZARD_STEPS.index(step) + 1 if step in WIZARD_STEPS else len(WIZARD_STEPS)
    head = f"🧩 ساخت کانفیگ — مرحله {n}/{len(WIZARD_STEPS)}\n\n"
    return {
        "label": head + "✏️ اسم کانفیگ رو بفرست:",
        "protocol": head + "🌐 پروتکل مسیر مستقیم:",
        "fingerprint": head + "🖐 Fingerprint رو انتخاب کن:",
        "alpn": head + "🔤 ALPN رو انتخاب کن یا خودت تایپ کن:",
        "port": head + f"🔌 پورت (پیش‌فرض {DEFAULT_PORT}):",
        "volume": head + "📦 حجم، مثلاً <code>10GB</code> یا نامحدود:",
        "speed": head + "🚀 سرعت به Mbps، مثلاً <code>20</code> یا نامحدود:",
        "iplimit": head + "👥 سقف آی‌پی هم‌زمان یا نامحدود:",
        "days": head + "📅 روزهای اعتبار یا نامحدود:",
        "cdn": head + "☁️ دامنه ابری (کلادفلر) رو بفرست، مثلاً <code>cdn.example.com</code>\nیا رد کن تا از پیش‌فرض پنل استفاده بشه:",
    }.get(step, head)


def _wizard_summary(data: dict) -> str:
    limit = "نامحدود" if not data.get("limit_bytes") else fmt_bytes(data["limit_bytes"])
    speed = "نامحدود" if not data.get("speed_limit_bytes") else f"{data['speed_limit_bytes'] * 8 / 1e6:.1f} Mbps"
    cdn = data.get("cdn_host") or "پیش‌فرض پنل"
    return (
        "🧩 خلاصه — تایید کن:\n\n"
        f"برچسب: <b>{data.get('label', '?')}</b>\n"
        f"پروتکل: {_protocol_label(data.get('protocol', DEFAULT_PROTOCOL))}\n"
        f"پورت: {data.get('port', DEFAULT_PORT)}\n"
        f"حجم: {limit}\n"
        f"سرعت: {speed}\n"
        f"آی‌پی: {data.get('ip_limit', 0) or 'نامحدود'}\n"
        f"انقضا: {data.get('expires_days', 0) or 'بدون انقضا'} روز\n"
        f"☁️ دامنه ابری: {cdn}\n\n"
        "هر کانفیگ ۲ لینک می‌گیرد (⚡ مستقیم + ☁️ ابری)"
    )


def _format_detail(uid: str, l: dict) -> str:
    status = "🟢 فعال" if is_link_allowed(l) else "🔴 غیرفعال/منقضی"
    limit = "نامحدود" if not l.get("limit_bytes") else fmt_bytes(l["limit_bytes"])
    speed = "نامحدود" if not l.get("speed_limit_bytes") else f"{l['speed_limit_bytes'] * 8 / 1e6:.1f} Mbps"
    exp = l.get("expires_at")
    cdn = l.get("cdn_host") or "پیش‌فرض پنل"
    return (
        f"<b>{l.get('label', '?')}</b>\n"
        f"وضعیت: {status}\n"
        f"مصرف: {fmt_bytes(l.get('used_bytes', 0))} / {limit}\n"
        f"سرعت: {speed} · آی‌پی: {l.get('ip_limit', 0) or 'نامحدود'}\n"
        f"پروتکل: {_protocol_label(l.get('protocol', DEFAULT_PROTOCOL))}\n"
        f"پورت: {l.get('port', DEFAULT_PORT)} · ☁️ ابری: {cdn}\n"
        f"انقضا: {exp.split('T')[0] if exp else 'بدون انقضا'}\n"
        f"UUID: <code>{uid}</code>"
    )


def _group_public_url(s: dict) -> str:
    return f"https://{_host()}/p/{s.get('uuid_key', '')}"


def _subs_list_kb(page: int):
    items = sorted(SUBS.items(), key=lambda kv: kv[1].get("created_at", ""), reverse=True)
    start = page * PAGE_SIZE
    rows = []
    for sid, s in items[start:start + PAGE_SIZE]:
        rows.append([{"text": f"🗂 {s.get('name', '?')[:26]} ({len(s.get('link_ids', []))})",
                      "callback_data": f"subview:{sid}"}])
    nav = []
    if start > 0:
        nav.append({"text": "◀ قبلی", "callback_data": f"subs:{page - 1}"})
    if start + PAGE_SIZE < len(items):
        nav.append({"text": "بعدی ▶", "callback_data": f"subs:{page + 1}"})
    if nav:
        rows.append(nav)
    rows.append([{"text": "➕ ساخت گروه جدید", "callback_data": "newsub"}])
    rows.append([{"text": "⬅ منوی اصلی", "callback_data": "menu"}])
    return {"inline_keyboard": rows}


def _format_sub_detail(sid: str, s: dict) -> str:
    pw = "🔒 دارد" if s.get("password") else "بدون رمز"
    return (
        f"🗂 <b>{s.get('name', '?')}</b>\n"
        f"کانفیگ‌ها: {len(s.get('link_ids', []))} · رمز: {pw}\n\n"
        f"🌐 صفحه عمومی:\n<code>{_group_public_url(s)}</code>\n\n"
        f"📡 لینک ساب (اپ):\n<code>https://{_host()}/sub-group/{s.get('uuid_key', '')}</code>"
    )


def _sub_detail_kb(sid: str):
    return {"inline_keyboard": [
        [{"text": "➕ افزودن کانفیگ به این گروه", "callback_data": f"subaddlink:{sid}:0"}],
        [{"text": "🗑 حذف گروه", "callback_data": f"subdel:{sid}"}],
        [{"text": "⬅ لیست گروه‌ها", "callback_data": "subs:0"}],
    ]}


def _confirm_subdel_kb(sid: str):
    return {"inline_keyboard": [
        [{"text": "✅ بله، حذف کن", "callback_data": f"subdelok:{sid}"},
         {"text": "❌ انصراف", "callback_data": f"subview:{sid}"}],
    ]}


def _pick_link_for_group_kb(sid: str, page: int):
    items = sorted(LINKS.items(), key=lambda kv: kv[1].get("created_at", ""), reverse=True)
    start = page * PAGE_SIZE
    rows = []
    for uid, l in items[start:start + PAGE_SIZE]:
        mark = "✅ " if l.get("sub_id") == sid else ""
        rows.append([{"text": f"{mark}{l.get('label', '?')[:28]}", "callback_data": f"subaddlinkdo:{uid}"}])
    nav = []
    if start > 0:
        nav.append({"text": "◀ قبلی", "callback_data": f"subaddlink:{sid}:{page - 1}"})
    if start + PAGE_SIZE < len(items):
        nav.append({"text": "بعدی ▶", "callback_data": f"subaddlink:{sid}:{page + 1}"})
    if nav:
        rows.append(nav)
    rows.append([{"text": "⬅ بازگشت به گروه", "callback_data": f"subview:{sid}"}])
    return {"inline_keyboard": rows}


def _cfg_group_kb(uid: str):
    link = LINKS.get(uid, {})
    sid = link.get("sub_id")
    if sid and sid in SUBS:
        return {"inline_keyboard": [
            [{"text": "➖ خارج کردن از گروه", "callback_data": f"cfgungroup:{uid}"}],
            [{"text": "⬅ بازگشت", "callback_data": f"view:{uid}"}],
        ]}
    rows = []
    for sid2, s in sorted(SUBS.items(), key=lambda kv: kv[1].get("created_at", ""), reverse=True)[:8]:
        rows.append([{"text": f"➕ «{s.get('name', '?')[:24]}»", "callback_data": f"cfgaddgroup:{sid2}"}])
    rows.append([{"text": "🆕 گروه جدید و افزودن", "callback_data": f"cfgnewgroup:{uid}"}])
    rows.append([{"text": "⬅ بازگشت", "callback_data": f"view:{uid}"}])
    return {"inline_keyboard": rows}


def _format_cfg_group(uid: str) -> str:
    link = LINKS.get(uid, {})
    sid = link.get("sub_id")
    if sid and sid in SUBS:
        return (f"🗂 «{link.get('label', '?')}» توی گروه «{SUBS[sid].get('name', '?')}» هست.\n\n"
                f"🌐 صفحه عمومی:\n<code>{_group_public_url(SUBS[sid])}</code>")
    return f"«{link.get('label', '?')}» توی هیچ گروهی نیست. به یک گروه اضافه‌اش کن:"


# ── پیام‌ها ──────────────────────────────────────────────────────────────────
async def _handle_message(msg: dict):
    chat_id = msg.get("chat", {}).get("id")
    text = (msg.get("text") or "").strip()
    if chat_id is None:
        return
    if not _is_admin(chat_id):
        await _send(chat_id, "⛔ شما اجازه‌ی دسترسی ندارید.")
        return
    if text in ("/start", "/menu"):
        _pending.pop(chat_id, None)
        await _send(chat_id, "👋 به ربات NovaPanel خوش اومدی ⚡", _main_menu_kb())
        return
    if text == "/cancel":
        _pending.pop(chat_id, None)
        await _send(chat_id, "لغو شد.", _main_menu_kb())
        return

    pending = _pending.get(chat_id)
    if pending and pending.get("action") == "newsub" and pending.get("step") == "name" and text:
        sid, s = await create_sub_group(name=text[:60])
        link_uid = pending.get("link_uid")
        _pending.pop(chat_id, None)
        await save_state()
        if link_uid and link_uid in LINKS:
            await set_link_sub(link_uid, sid)
            await save_state()
            await _send(chat_id, f"✅ گروه ساخته و کانفیگ اضافه شد.\n\n{_format_cfg_group(link_uid)}",
                        _cfg_group_kb(link_uid))
        else:
            await _send(chat_id, f"✅ گروه ساخته شد.\n\n{_format_sub_detail(sid, s)}", _sub_detail_kb(sid))
        return

    if pending and pending.get("action") == "wizard" and text:
        step = pending["step"]
        data = pending["data"]
        if step == "label":
            data["label"] = text[:60] or "کانفیگ جدید"
            pending["step"] = "protocol"
            await _send(chat_id, _wizard_prompt("protocol", data), _wizard_protocol_kb())
            return
        if step in ("protocol", "fingerprint"):
            kb = _wizard_protocol_kb() if step == "protocol" else _wizard_fp_kb()
            await _send(chat_id, "از دکمه‌ها انتخاب کن 👆", kb)
            return
        if step == "alpn":
            data["alpn"] = text.strip()[:100]
            pending["step"] = "port"
            await _send(chat_id, _wizard_prompt("port", data),
                        _wizard_skip_kb("port", f"⏭ پیش‌فرض ({DEFAULT_PORT})"))
            return
        if step == "port":
            try:
                p = int(text.strip())
            except ValueError:
                p = None
            if p is None or not (MIN_PORT <= p <= MAX_PORT):
                await _send(chat_id, "❗️ پورت نامعتبره:",
                            _wizard_skip_kb("port", f"⏭ پیش‌فرض ({DEFAULT_PORT})"))
                return
            data["port"] = p
            pending["step"] = "volume"
            await _send(chat_id, _wizard_prompt("volume", data), _wizard_skip_kb("volume", "♾ نامحدود"))
            return
        if step == "volume":
            parsed = _parse_volume_text(text)
            if parsed is None:
                await _send(chat_id, "❗️ مثلاً: <code>10GB</code>", _wizard_skip_kb("volume", "♾ نامحدود"))
                return
            data["limit_bytes"] = parsed
            pending["step"] = "speed"
            await _send(chat_id, _wizard_prompt("speed", data), _wizard_skip_kb("speed", "♾ نامحدود"))
            return
        if step == "speed":
            parsed = _parse_speed_text(text)
            if parsed is None:
                await _send(chat_id, "❗️ یه عدد بفرست، مثلاً <code>20</code>", _wizard_skip_kb("speed", "♾ نامحدود"))
                return
            data["speed_limit_bytes"] = parsed
            pending["step"] = "iplimit"
            await _send(chat_id, _wizard_prompt("iplimit", data), _wizard_skip_kb("iplimit", "♾ نامحدود"))
            return
        if step == "iplimit":
            n = _parse_nonneg_int(text)
            if n is None:
                await _send(chat_id, "❗️ یه عدد بفرست:", _wizard_skip_kb("iplimit", "♾ نامحدود"))
                return
            data["ip_limit"] = n
            pending["step"] = "days"
            await _send(chat_id, _wizard_prompt("days", data), _wizard_skip_kb("days", "♾ نامحدود"))
            return
        if step == "days":
            n = _parse_nonneg_int(text)
            if n is None:
                await _send(chat_id, "❗️ یه عدد بفرست:", _wizard_skip_kb("days", "♾ نامحدود"))
                return
            data["expires_days"] = n
            pending["step"] = "cdn"
            await _send(chat_id, _wizard_prompt("cdn", data), _wizard_skip_kb("cdn", "⏭ پیش‌فرض پنل"))
            return
        if step == "cdn":
            data["cdn_host"] = text.strip().lower()[:120]
            pending["step"] = "confirm"
            await _send(chat_id, _wizard_summary(data), _wizard_confirm_kb())
            return

    await _send(chat_id, "از دکمه‌ها استفاده کن:", _main_menu_kb())


async def _handle_callback(cb: dict):
    chat_id = cb.get("message", {}).get("chat", {}).get("id")
    message_id = cb.get("message", {}).get("message_id")
    data = cb.get("data", "")
    cb_id = cb.get("id")
    if chat_id is None or not _is_admin(chat_id):
        await _answer_cb(cb_id, "⛔ دسترسی نداری")
        return
    await _answer_cb(cb_id)

    if data == "menu":
        _pending.pop(chat_id, None)
        await _edit(chat_id, message_id, "منوی NovaPanel ⚡", _main_menu_kb())
        return
    if data == "stats":
        await _edit(chat_id, message_id, _stats_text(), _main_menu_kb())
        return
    if data.startswith("list:"):
        page = int(data.split(":", 1)[1] or 0)
        if not LINKS:
            await _edit(chat_id, message_id, "هنوز کانفیگی نیست.", _main_menu_kb())
            return
        await _edit(chat_id, message_id, f"📋 کانفیگ‌ها ({len(LINKS)}):", _links_list_kb(page))
        return
    if data.startswith("subs:"):
        page = int(data.split(":", 1)[1] or 0)
        if not SUBS:
            await _edit(chat_id, message_id, "هنوز گروهی نیست. اول یه گروه بساز.", _subs_list_kb(0))
            return
        await _edit(chat_id, message_id, f"🗂 گروه‌ها ({len(SUBS)}):", _subs_list_kb(page))
        return
    if data == "newsub":
        _pending[chat_id] = {"action": "newsub", "step": "name", "link_uid": None}
        await _edit(chat_id, message_id, "✏️ اسم گروه رو بفرست:", _wizard_cancel_kb())
        return
    if data.startswith("subview:"):
        sid = data.split(":", 1)[1]
        s = SUBS.get(sid)
        if not s:
            await _edit(chat_id, message_id, "این گروه نیست.", _main_menu_kb())
            return
        await _edit(chat_id, message_id, _format_sub_detail(sid, s), _sub_detail_kb(sid))
        return
    if data.startswith("subaddlink:"):
        _, sid, page_s = data.split(":", 2)
        if sid not in SUBS or not LINKS:
            await _edit(chat_id, message_id, "گروه یا کانفیگی نیست.", _main_menu_kb())
            return
        _pending[chat_id] = {"action": "subaddlink_ctx", "sid": sid}
        await _edit(chat_id, message_id, "کدوم کانفیگ؟ (✅ یعنی الان توی این گروهه)",
                    _pick_link_for_group_kb(sid, int(page_s or 0)))
        return
    if data.startswith("subaddlinkdo:"):
        uid = data.split(":", 1)[1]
        ctx = _pending.get(chat_id) or {}
        sid = ctx.get("sid") if ctx.get("action") == "subaddlink_ctx" else None
        if not sid or sid not in SUBS or not await set_link_sub(uid, sid):
            await _answer_cb(cb_id, "منقضی شده، دوباره امتحان کن.")
            return
        _pending.pop(chat_id, None)
        await save_state()
        await _edit(chat_id, message_id, f"✅ اضافه شد.\n\n{_format_sub_detail(sid, SUBS[sid])}",
                    _sub_detail_kb(sid))
        return
    if data.startswith("subdel:"):
        sid = data.split(":", 1)[1]
        s = SUBS.get(sid)
        if not s:
            await _edit(chat_id, message_id, "این گروه نیست.", _main_menu_kb())
            return
        await _edit(chat_id, message_id, f"❗️ گروه «{s.get('name')}» حذف شود؟ (کانفیگ‌ها پاک نمی‌شوند)",
                    _confirm_subdel_kb(sid))
        return
    if data.startswith("subdelok:"):
        sid = data.split(":", 1)[1]
        sub = await remove_sub_group(sid)
        await save_state()
        await _edit(chat_id, message_id,
                    f"🗑 گروه «{sub.get('name', '?')}» حذف شد." if sub else "قبلاً حذف شده بود.",
                    _main_menu_kb())
        return
    if data.startswith("cfggroup:"):
        uid = data.split(":", 1)[1]
        if uid not in LINKS:
            await _edit(chat_id, message_id, "این کانفیگ نیست.", _main_menu_kb())
            return
        _pending[chat_id] = {"action": "cfg_group_ctx", "uid": uid}
        await _edit(chat_id, message_id, _format_cfg_group(uid), _cfg_group_kb(uid))
        return
    if data.startswith("cfgungroup:"):
        uid = data.split(":", 1)[1]
        await set_link_sub(uid, None)
        await save_state()
        l = LINKS.get(uid)
        if not l:
            await _edit(chat_id, message_id, "این کانفیگ نیست.", _main_menu_kb())
            return
        await _edit(chat_id, message_id, _format_detail(uid, l), _link_detail_kb(uid, l["active"]))
        return
    if data.startswith("cfgaddgroup:"):
        sid = data.split(":", 1)[1]
        ctx = _pending.get(chat_id) or {}
        uid = ctx.get("uid") if ctx.get("action") == "cfg_group_ctx" else None
        if not uid or uid not in LINKS or not await set_link_sub(uid, sid):
            await _answer_cb(cb_id, "منقضی شده، دوباره امتحان کن.")
            return
        _pending.pop(chat_id, None)
        await save_state()
        await _edit(chat_id, message_id, f"✅ اضافه شد.\n\n{_format_cfg_group(uid)}", _cfg_group_kb(uid))
        return
    if data.startswith("cfgnewgroup:"):
        uid = data.split(":", 1)[1]
        if uid not in LINKS:
            await _edit(chat_id, message_id, "این کانفیگ نیست.", _main_menu_kb())
            return
        _pending[chat_id] = {"action": "newsub", "step": "name", "link_uid": uid}
        await _edit(chat_id, message_id, "✏️ اسم گروه جدید:", _wizard_cancel_kb())
        return
    if data == "newcfg":
        _pending[chat_id] = {"action": "wizard", "step": "label", "data": {}}
        await _edit(chat_id, message_id, _wizard_prompt("label", {}), _wizard_cancel_kb())
        return
    if data == "w:cancel":
        _pending.pop(chat_id, None)
        await _edit(chat_id, message_id, "لغو شد.", _main_menu_kb())
        return

    if data.startswith("w:"):
        pending = _pending.get(chat_id)
        if not pending or pending.get("action") != "wizard":
            await _edit(chat_id, message_id, "منقضی شده، دوباره شروع کن.", _main_menu_kb())
            return
        step, wdata = pending["step"], pending["data"]
        if data.startswith("w:proto:") and step == "protocol":
            proto = data.split(":", 2)[2]
            wdata["protocol"] = proto if proto in PROTOCOLS else DEFAULT_PROTOCOL
            pending["step"] = "fingerprint"
            await _edit(chat_id, message_id, _wizard_prompt("fingerprint", wdata), _wizard_fp_kb())
            return
        if data.startswith("w:fp:") and step == "fingerprint":
            fp = data.split(":", 2)[2]
            wdata["fingerprint"] = fp if fp in FINGERPRINTS else DEFAULT_FINGERPRINT
            pending["step"] = "alpn"
            await _edit(chat_id, message_id, _wizard_prompt("alpn", wdata), _wizard_alpn_kb())
            return
        if data.startswith("w:alpnpreset:") and step == "alpn":
            wdata["alpn"] = ALPN_PRESET_MAP.get(data.split(":", 2)[2], "")
            pending["step"] = "port"
            await _edit(chat_id, message_id, _wizard_prompt("port", wdata),
                        _wizard_skip_kb("port", f"⏭ پیش‌فرض ({DEFAULT_PORT})"))
            return
        if data == "w:skip:alpn" and step == "alpn":
            wdata["alpn"] = ""
            pending["step"] = "port"
            await _edit(chat_id, message_id, _wizard_prompt("port", wdata),
                        _wizard_skip_kb("port", f"⏭ پیش‌فرض ({DEFAULT_PORT})"))
            return
        if data == "w:skip:port" and step == "port":
            wdata["port"] = DEFAULT_PORT
            pending["step"] = "volume"
            await _edit(chat_id, message_id, _wizard_prompt("volume", wdata),
                        _wizard_skip_kb("volume", "♾ نامحدود"))
            return
        if data == "w:skip:volume" and step == "volume":
            wdata["limit_bytes"] = 0
            pending["step"] = "speed"
            await _edit(chat_id, message_id, _wizard_prompt("speed", wdata),
                        _wizard_skip_kb("speed", "♾ نامحدود"))
            return
        if data == "w:skip:speed" and step == "speed":
            wdata["speed_limit_bytes"] = 0
            pending["step"] = "iplimit"
            await _edit(chat_id, message_id, _wizard_prompt("iplimit", wdata),
                        _wizard_skip_kb("iplimit", "♾ نامحدود"))
            return
        if data == "w:skip:iplimit" and step == "iplimit":
            wdata["ip_limit"] = 0
            pending["step"] = "days"
            await _edit(chat_id, message_id, _wizard_prompt("days", wdata),
                        _wizard_skip_kb("days", "♾ نامحدود"))
            return
        if data == "w:skip:days" and step == "days":
            wdata["expires_days"] = 0
            pending["step"] = "cdn"
            await _edit(chat_id, message_id, _wizard_prompt("cdn", wdata),
                        _wizard_skip_kb("cdn", "⏭ پیش‌فرض پنل"))
            return
        if data == "w:skip:cdn" and step == "cdn":
            wdata["cdn_host"] = ""
            pending["step"] = "confirm"
            await _edit(chat_id, message_id, _wizard_summary(wdata), _wizard_confirm_kb())
            return
        if data == "w:confirm" and step == "confirm":
            uid, link = await make_link(
                label=wdata.get("label") or "کانفیگ جدید",
                limit_bytes=wdata.get("limit_bytes", 0),
                expires_days=wdata.get("expires_days", 0),
                protocol=wdata.get("protocol", DEFAULT_PROTOCOL),
                fingerprint=wdata.get("fingerprint", DEFAULT_FINGERPRINT),
                alpn=wdata.get("alpn", ""),
                port=wdata.get("port", DEFAULT_PORT),
                ip_limit=wdata.get("ip_limit", 0),
                speed_limit_bytes=wdata.get("speed_limit_bytes", 0),
                cdn_host=wdata.get("cdn_host", ""),
            )
            _pending.pop(chat_id, None)
            log_activity("link", f"کانفیگ «{link['label']}» از ربات ساخته شد", "ok")
            await save_state()
            await _edit(chat_id, message_id, f"✅ ساخته شد.\n\n{_format_detail(uid, link)}",
                        _link_detail_kb(uid, link["active"]))
            return
        await _answer_cb(cb_id, "این دکمه معتبر نیست.")
        return

    if data.startswith("view:"):
        uid = data.split(":", 1)[1]
        l = LINKS.get(uid)
        if not l:
            await _edit(chat_id, message_id, "این کانفیگ نیست.", _main_menu_kb())
            return
        await _edit(chat_id, message_id, _format_detail(uid, l), _link_detail_kb(uid, l["active"]))
        return
    if data.startswith("toggle:"):
        uid = data.split(":", 1)[1]
        cur = LINKS.get(uid)
        l = await set_link_active(uid, not (cur or {}).get("active", True)) if cur else None
        if not l:
            await _edit(chat_id, message_id, "این کانفیگ نیست.", _main_menu_kb())
            return
        await save_state()
        await _edit(chat_id, message_id, _format_detail(uid, l), _link_detail_kb(uid, l["active"]))
        return
    if data.startswith("link:"):
        uid = data.split(":", 1)[1]
        l = LINKS.get(uid)
        if not l:
            await _answer_cb(cb_id, "پیدا نشد")
            return
        host = _host()
        vlinks = all_vless_links(l, uid, host)
        msg = (f"🔗 «{l.get('label')}» — هر دو رو کپی کن:\n\n"
               f"⚡ مستقیم:\n<code>{vlinks[0]}</code>\n\n"
               f"☁️ ابری:\n<code>{vlinks[1]}</code>\n\n"
               f"📡 ساب (هر دو لینک):\n<code>https://{host}/sub/{uid}</code>")
        sid = l.get("sub_id")
        if sid and sid in SUBS:
            msg += f"\n\n🌐 صفحه گروه:\n<code>{_group_public_url(SUBS[sid])}</code>"
        await _send(chat_id, msg)
        return
    if data.startswith("del:"):
        uid = data.split(":", 1)[1]
        l = LINKS.get(uid)
        if not l:
            await _edit(chat_id, message_id, "این کانفیگ نیست.", _main_menu_kb())
            return
        await _edit(chat_id, message_id, f"❗️ «{l.get('label')}» حذف شود؟", _confirm_delete_kb(uid))
        return
    if data.startswith("delok:"):
        uid = data.split(":", 1)[1]
        link = await remove_link(uid)
        await save_state()
        await _edit(chat_id, message_id,
                    f"🗑 «{link.get('label', '?')}» حذف شد." if link else "قبلاً حذف شده بود.",
                    _main_menu_kb())
        return


async def _poll_loop():
    global _running
    offset = 0
    logger.info(f"🤖 Bot polling started (admins: {len(ADMIN_IDS)})")
    while _running:
        try:
            res = await _call("getUpdates", offset=offset, timeout=30,
                              allowed_updates=["message", "callback_query"])
            if not res or not res.get("ok"):
                await asyncio.sleep(3)
                continue
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                try:
                    if "message" in upd:
                        await _handle_message(upd["message"])
                    elif "callback_query" in upd:
                        await _handle_callback(upd["callback_query"])
                except Exception as e:
                    logger.warning(f"Bot update error: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Bot poll error: {e}")
            await asyncio.sleep(3)


async def start_bot(host_fn=None):
    global _client, _poll_task, _running, _host_fn
    if host_fn:
        _host_fn = host_fn
    if not BOT_TOKEN:
        logger.info("Bot: TELEGRAM_BOT_TOKEN not set, disabled.")
        return
    if not ADMIN_IDS:
        logger.warning("Bot: TELEGRAM_ADMIN_IDS not set, everyone will be rejected.")
    _client = httpx.AsyncClient(timeout=httpx.Timeout(40.0, connect=10.0))
    _running = True
    _poll_task = asyncio.create_task(_poll_loop())


async def stop_bot():
    global _running, _client
    _running = False
    if _poll_task:
        _poll_task.cancel()
    if _client:
        await _client.aclose()
        _client = None
