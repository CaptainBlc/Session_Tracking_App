from __future__ import annotations
from tkinter import messagebox
import shutil

from .paths import assets_dir, data_dir
from .logging_utils import log_exception


def ask_yesno(title: str, text: str) -> bool:
    try:
        return messagebox.askyesno(title, text)
    except Exception:
        return False


def info(title: str, text: str) -> None:
    try:
        messagebox.showinfo(title, text)
    except Exception:
        pass


def warn(title: str, text: str) -> None:
    try:
        messagebox.showwarning(title, text)
    except Exception:
        pass


def err(title: str, text: str) -> None:
    try:
        messagebox.showerror(title, text)
    except Exception:
        pass


def ensure_user_guide_present() -> None:
    """
    Kullanıcı kılavuzu yoksa assets'ten data_dir'a kopyala.
    Yoksa da crash etmesin.
    """
    try:
        dst = data_dir() / "KULLANIM_KILAVUZU.txt"
        if dst.exists():
            return

        candidates = [
            assets_dir() / "KULLANIM_KILAVUZU.txt",
            assets_dir() / "kullanim_kilavuzu.txt",
        ]
        for src in candidates:
            if src.exists():
                try:
                    shutil.copy2(str(src), str(dst))
                    return
                except Exception:
                    pass

        try:
            dst.write_text("Kullanım kılavuzu bulunamadı.\n", encoding="utf-8")
        except Exception:
            pass
    except Exception as e:
        log_exception("ensure_user_guide_present", e)