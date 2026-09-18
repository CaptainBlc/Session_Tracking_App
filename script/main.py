from __future__ import annotations
import sys
import traceback
from tkinter import messagebox

from core import *  # core package export layer
from core.backup import _db_integrity_ok
from app_ui import App


def main():
    print(">>> MAIN START")
    ensure_user_guide_present()
    print(">>> user guide ok")
    silent_backup()
    print(">>> backup ok")

    try:
        dbp = db_path()
        if dbp.exists() and not _db_integrity_ok(dbp):
            log_exception("main_db_integrity_check", Exception("Veritabani butunluk kontrolu basarisiz"))
            messagebox.showwarning(
                "Veritabanı Uyarısı",
                "Veritabanı bütünlük kontrolü başarısız oldu. Uygulama yine de "
                "açılacak, ancak yedeklerinizi kontrol etmenizi öneririz "
                "(Hakkında ekranından son yedek durumuna bakabilirsiniz).",
            )
    except Exception as e:
        log_exception("main_db_integrity_check_wrapper", e)

    init_db()
    print(">>> init_db ok")

    try:
        migrate_database_data()
        print(">>> migrate ok")
    except Exception as e:
        print(">>> migrate failed:", e)
        log_exception("migrate_database_data", e)

    configure_windows_dpi_awareness()
    print(">>> dpi ok")

    try:
        print(">>> creating App() ...")
        app = App()
        print(">>> App created, entering mainloop ...")
        app.mainloop()
        print(">>> mainloop ended")
    except Exception as e:
        print(">>> APP CRASH:", e)
        log_exception("APP_CRASH", e)
        raise
def global_exception_hook(exctype, value, tb):
    try:
        log_exception("GLOBAL_EXCEPTION", value)
        with open("leta_error.log", "a", encoding="utf-8") as f:
            f.write("\n--- GLOBAL EXCEPTION ---\n")
            traceback.print_exception(exctype, value, tb, file=f)
    except Exception:
        pass

sys.excepthook = global_exception_hook

if __name__ == "__main__":
    main()