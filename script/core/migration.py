from __future__ import annotations
import datetime
from .logging_utils import log_exception, log_info


def _table_exists(conn, name: str) -> bool:
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,))
        return cur.fetchone() is not None
    except Exception:
        return False


def _backfill_personel_ucret_takibi() -> None:
    """
    Idempotent, güvenli geriye dönük onarım: seans_takvimi'nde olup (eski bir bug,
    Excel aktarımı veya manuel veri girişi yüzünden) personel_ucret_takibi'nde hiç
    karşılığı oluşmamış seanslar için eksik hakediş kaydını şimdi oluşturur.
    Var olan kayıtlara dokunmaz, sadece eksik olanları ekler (INSERT OR IGNORE +
    NOT EXISTS koruması). pipeline.seans_kayit ile aynı kural/formülü kullanır.
    """
    from .db import connect_db
    from .money import hesapla_personel_ucreti

    conn = connect_db()
    try:
        if not _table_exists(conn, "personel_ucret_takibi") or not _table_exists(conn, "seans_takvimi"):
            return
        cur = conn.cursor()
        cur.execute(
            """
            SELECT st.id, st.terapist, st.tarih, st.hizmet_bedeli
            FROM seans_takvimi st
            WHERE COALESCE(st.durum,'') NOT IN ('iptal', 'devir_borc')
              AND COALESCE(st.hizmet_bedeli, 0) > 0
              AND COALESCE(st.terapist, '') != ''
              AND NOT EXISTS (SELECT 1 FROM personel_ucret_takibi put WHERE put.seans_id = st.id)
            """
        )
        eksikler = cur.fetchall()
        eklenen = 0
        for seans_id, terapist, tarih, hizmet_bedeli in eksikler:
            try:
                hb = float(hizmet_bedeli or 0)
                personel_ucreti = float(hesapla_personel_ucreti(terapist, hb))
                kural = "sabit" if terapist == "Arif Hoca" else ("yuzde100" if terapist == "Pervin Hoca" else "yuzde40")
                ucret_orani = 100.0 if terapist == "Pervin Hoca" else (0.0 if terapist == "Arif Hoca" else 40.0)
                cur.execute(
                    """
                    INSERT OR IGNORE INTO personel_ucret_takibi
                    (personel_adi, seans_id, tarih, seans_ucreti, personel_ucreti, ucret_orani, odeme_durumu, aciklama, olusturma_tarihi)
                    VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        terapist, seans_id, tarih, hb, personel_ucreti, ucret_orani, "beklemede",
                        f"Kural:{kural} (geriye dönük onarım)",
                        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                eklenen += 1
            except Exception as e:
                log_exception("_backfill_personel_ucret_takibi_row", e)
        conn.commit()
        if eklenen:
            log_info(f"_backfill_personel_ucret_takibi: {eklenen} eksik hakediş kaydı geriye dönük oluşturuldu.")
    finally:
        conn.close()


def migrate_database_data() -> None:
    try:
        _backfill_personel_ucret_takibi()
    except Exception as e:
        log_exception("migrate_database_data", e)


def ensure_db_ready(conn) -> bool:
    """
    Veritabanının minimum şemaya sahip olduğundan emin olur.
    Güvenli: idempotent.
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if cur.fetchone():
            return True

        # tablo yoksa init etmeye çalış
        try:
            from .db import _init_db
            _init_db(conn)
            conn.commit()
        except Exception:
            pass

        return True
    except Exception as e:
        try:
            log_exception("ensure_db_ready", e)
        except Exception:
            pass
        return False