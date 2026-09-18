from __future__ import annotations

import hashlib

# Fallback login bilgileri env.py'den gelsin
try:
    from .env import LOGIN_USER, LOGIN_PASS
except Exception:
    LOGIN_USER = "Leta"
    LOGIN_PASS = "Yildiz1327."


def role_label(access_role: str | None) -> str:
    r = (access_role or "").strip()
    if r == "kurum_muduru":
        return "Kurum Müdürü"
    if r == "egitim_gorevlisi":
        return "Eğitim Görevlisi"
    if r == "normal":
        return "Kullanıcı"
    if not r:
        return "Kullanıcı"
    return r


def hash_pass(p: str) -> str:
    """
    Monolit leta_app.py ile aynı hash:
    sha256(password)
    """
    return hashlib.sha256((p or "").encode("utf-8")).hexdigest()