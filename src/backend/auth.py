"""User accounts: registration, login and signed session tokens.

Passwords are never stored in readable form - only a PBKDF2-HMAC-SHA256 hash
with a per-user salt. Tokens are HMAC-signed with APP_SECRET, so a token
cannot be forged or edited on the client side.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
from typing import Any, Dict, Optional

from config import DATA_DIR

logger = logging.getLogger(__name__)

USERS_PATH = DATA_DIR / "users.json"
APP_SECRET = os.getenv("APP_SECRET", "")
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", str(60 * 60 * 24 * 7)))
PBKDF2_ITERATIONS = 260_000


class AuthError(Exception):
    """Raised for any authentication or registration failure."""


def _secret() -> str:
    if not APP_SECRET:
        raise AuthError("APP_SECRET is not configured on the server")
    return APP_SECRET


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str, salt: Optional[str] = None) -> Dict[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS
    )
    return {"salt": salt, "hash": digest.hex(), "iterations": str(PBKDF2_ITERATIONS)}


def verify_password(password: str, record: Dict[str, Any]) -> bool:
    expected = record.get("password_hash", {})
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        str(expected.get("salt", "")).encode(),
        int(expected.get("iterations", PBKDF2_ITERATIONS)),
    ).hex()
    return hmac.compare_digest(candidate, str(expected.get("hash", "")))


def create_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(_secret().encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def verify_token(token: str) -> str:
    try:
        body, signature = token.split(".", 1)
    except ValueError as exc:
        raise AuthError("Malformed token") from exc

    expected = _b64(hmac.new(_secret().encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise AuthError("Invalid token signature")

    payload = json.loads(_unb64(body))
    if payload.get("exp", 0) < time.time():
        raise AuthError("Token expired")
    return str(payload["sub"])


class UserStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.users: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            if USERS_PATH.exists():
                self.users = json.loads(USERS_PATH.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Could not load users: %s", exc)
            self.users = {}

    def _save(self) -> None:
        USERS_PATH.write_text(json.dumps(self.users, ensure_ascii=False), encoding="utf-8")

    def register(self, name: str, email: str, password: str) -> Dict[str, Any]:
        email = email.strip().lower()
        if not name.strip() or not email or len(password) < 8:
            raise AuthError("กรุณากรอกชื่อ อีเมล และรหัสผ่านอย่างน้อย 8 ตัวอักษร")

        with self._lock:
            if email in self.users:
                raise AuthError("อีเมลนี้ถูกใช้งานแล้ว กรุณาใช้อีเมลอื่น")
            user = {
                "id": secrets.token_hex(12),
                "name": name.strip(),
                "email": email,
                "password_hash": hash_password(password),
                "created_at": int(time.time()),
            }
            self.users[email] = user
            self._save()
        return self.public(user)

    def login(self, email: str, password: str) -> Dict[str, Any]:
        user = self.users.get(email.strip().lower())
        if not user or not verify_password(password, user):
            raise AuthError("อีเมลหรือรหัสผ่านไม่ถูกต้อง")
        return self.public(user)

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        for user in self.users.values():
            if user["id"] == user_id:
                return self.public(user)
        return None

    @staticmethod
    def public(user: Dict[str, Any]) -> Dict[str, Any]:
        return {"id": user["id"], "name": user["name"], "email": user["email"]}


user_store = UserStore()
