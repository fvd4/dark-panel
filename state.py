# state.py — وضعیت مشترک پنل (بدون وابستگی به ماژول‌های دیگر، برای جلوگیری از import چرخه‌ای)
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("novapanel")

# ── مسیر ذخیره‌سازی ──────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DATA_FILE = DATA_DIR / "nova_state.json"
SECRET_FILE = DATA_DIR / ".secret"

CONFIG = {
    "port": int(os.environ.get("PORT", 8000)),
    "host": os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost"),
}

# ── وضعیت در حافظه ───────────────────────────────────────────────────────────
LINKS: dict = {}          # uuid -> link dict
SUBS: dict = {}           # sub_id -> sub-group dict
LINKS_LOCK = asyncio.Lock()
SAVE_LOCK = asyncio.Lock()

connections: dict = {}    # conn_id -> {uuid, ip, transport, connected_at, bytes}
stats = {"total_bytes": 0, "total_requests": 0, "total_errors": 0, "start_time": time.time()}
error_logs: deque = deque(maxlen=100)
activity_logs: deque = deque(maxlen=300)
hourly_traffic: dict = defaultdict(int)

# ── سکرت سشن ─────────────────────────────────────────────────────────────────
def _load_or_create_secret() -> str:
    env = os.environ.get("SECRET_KEY", "").strip()
    if env:
        return env
    try:
        if SECRET_FILE.exists():
            return SECRET_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    import secrets as _s
    new_secret = _s.token_urlsafe(32)
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SECRET_FILE.write_text(new_secret, encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not persist SECRET_KEY: {e}")
    return new_secret

SECRET = _load_or_create_secret()

AUTH = {"password_hash": ""}
SESSION_COOKIE = "nova_session"
SESSION_TTL = 60 * 60 * 24 * 365
SESSIONS: dict = {}
SESSIONS_LOCK = asyncio.Lock()


def hash_password(pw: str) -> str:
    return hashlib.sha256(f"{pw}{SECRET}".encode()).hexdigest()


async def create_session() -> str:
    import secrets as _s
    token = _s.token_urlsafe(32)
    async with SESSIONS_LOCK:
        SESSIONS[token] = time.time() + SESSION_TTL
    return token


async def is_valid_session(token) -> bool:
    if not token:
        return False
    async with SESSIONS_LOCK:
        exp = SESSIONS.get(token)
        if exp is None:
            return False
        if exp < time.time():
            SESSIONS.pop(token, None)
            return False
        return True


async def destroy_session(token):
    if not token:
        return
    async with SESSIONS_LOCK:
        SESSIONS.pop(token, None)


async def load_auth_state():
    """رمز ادمین: متغیر محیطی ADMIN_PASSWORD اولویت دارد، وگرنه مقدار ذخیره‌شده."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if DATA_FILE.exists():
            import aiofiles
            async with aiofiles.open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            if "password_hash" in data:
                AUTH["password_hash"] = data["password_hash"]
    except Exception as e:
        logger.warning(f"Could not load auth state: {e}")
    if os.environ.get("ADMIN_PASSWORD"):
        AUTH["password_hash"] = hash_password(os.environ["ADMIN_PASSWORD"])


def log_activity(kind: str, message: str, level: str = "info"):
    activity_logs.append({
        "kind": kind, "level": level, "message": message,
        "time": datetime.now().isoformat(),
    })
    if len(activity_logs) > 300:
        activity_logs.popleft()


def log_error(message: str):
    error_logs.append({"error": message, "time": datetime.now().isoformat()})
    if len(error_logs) > 100:
        error_logs.popleft()
    logger.error(message)


async def load_state():
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if DATA_FILE.exists():
            import aiofiles
            async with aiofiles.open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            LINKS.update(data.get("links", {}))
            SUBS.update(data.get("subs", {}))
            logger.info(f"State loaded: {len(LINKS)} links, {len(SUBS)} groups")
    except Exception as e:
        logger.warning(f"Could not load state: {e}")


async def save_state():
    async with SAVE_LOCK:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "links": dict(LINKS),
                "subs": dict(SUBS),
                "saved_at": datetime.now().isoformat(),
            }
            import aiofiles
            tmp = DATA_FILE.with_suffix(".tmp")
            async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            tmp.replace(DATA_FILE)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
