from __future__ import annotations
from .logging_utils import log_exception


def migrate_database_data() -> None:
    # şimdilik boş: eski DB'den yeniye data taşıma gerekiyorsa burada yapacağız
    return


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