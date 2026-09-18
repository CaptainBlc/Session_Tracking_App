from __future__ import annotations

import tkinter as tk
from pathlib import Path

from .paths import assets_dir
from .logging_utils import log_exception


def _find_logo_file() -> Path | None:
    a = assets_dir()
    candidates = [
        a / "logo.png",
        a / "logo.gif",
        a / "logo.ppm",
        a / "logo.ico",
        a / "icon.ico",
        a / "icon.png",
    ]
    for p in candidates:
        try:
            if p.exists():
                return p
        except Exception:
            pass
    return None


def load_logo_photo(w: int = 28, h: int = 28) -> tk.PhotoImage | None:
    """
    Tk PhotoImage döndürür. Dosya yoksa None.
    png/gif desteği python build'e göre değişebilir.
    """
    try:
        p = _find_logo_file()
        if not p:
            return None

        img = tk.PhotoImage(file=str(p))

        # Güvenli küçültme: subsample (piksel resize yerine)
        try:
            iw, ih = img.width(), img.height()
            if iw > 0 and ih > 0:
                sx = max(1, int(iw / max(1, w)))
                sy = max(1, int(ih / max(1, h)))
                img = img.subsample(sx, sy)
        except Exception:
            pass

        return img
    except Exception as e:
        log_exception("load_logo_photo", e)
        return None


def safe_iconphoto(win: tk.Tk | tk.Toplevel, icon: tk.PhotoImage | None) -> None:
    """
    iconphoto bazen platforma göre patlıyor — güvenli wrapper.
    """
    try:
        if icon is not None:
            try:
                win.iconphoto(True, icon)
                return
            except Exception:
                pass

        # ICO varsa Windows'ta iconbitmap daha stabil olabilir
        p = _find_logo_file()
        if p and p.suffix.lower() == ".ico":
            try:
                win.iconbitmap(str(p))
            except Exception:
                pass
    except Exception as e:
        log_exception("safe_iconphoto", e)