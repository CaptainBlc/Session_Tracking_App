from __future__ import annotations
import sqlite3


def get_ogrenci_personel_ucreti(ogrenci_id: int, personel_adi: str, conn: sqlite3.Connection) -> float:
    """
    Danışan-personel bazlı fiyat varsa döndürür, yoksa 0.
    """
    try:
        cur = conn.cursor()
        personel = (personel_adi or "").strip()
        cur.execute(
            """
            SELECT price
            FROM pricing_policy
            WHERE student_id = ? AND TRIM(COALESCE(teacher_name,'')) = ?
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
            """,
            (ogrenci_id, personel),
        )
        row = cur.fetchone()
        if row and row[0]:
            return float(row[0])
        return 0.0
    except Exception:
        return 0.0