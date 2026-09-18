from __future__ import annotations


def parse_money(text: str | None) -> float:
    try:
        if text is None:
            return 0.0
        s = str(text).strip()
        if not s:
            return 0.0
        s = s.replace("₺", "").replace("TL", "").replace("tl", "").strip()
        s = s.replace(".", "").replace(",", ".")
        return float(s)
    except Exception:
        return 0.0


def format_money(val) -> str:
    try:
        num = float(val)
        return f"{num:,.2f} ₺"
    except Exception:
        return "0.00 ₺"


def hesapla_personel_ucreti(personel_adi: str, seans_ucreti: float) -> float:
    """
    pipeline.py tarafından kullanılır.
    Kurallar core.env.PERSONEL_UCRET_KURALLARI içinden okunur.
    """
    try:
        from .env import PERSONEL_UCRET_KURALLARI
        ad = (personel_adi or "").strip()
        kural = PERSONEL_UCRET_KURALLARI.get(
            ad,
            PERSONEL_UCRET_KURALLARI.get("_default", {"tip": "yuzde", "oran": 40.0}),
        )
        tip = (kural.get("tip") or "").strip().lower()
        if tip == "sabit":
            return float(kural.get("tutar") or 0.0)
        if tip == "yuzde":
            oran = float(kural.get("oran") or 0.0)
            return (float(seans_ucreti or 0.0) * oran) / 100.0
        return (float(seans_ucreti or 0.0) * 40.0) / 100.0
    except Exception:
        return (float(seans_ucreti or 0.0) * 40.0) / 100.0