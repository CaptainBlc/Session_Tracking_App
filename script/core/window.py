from __future__ import annotations

import sys


def _screen_size(win) -> tuple[int, int]:
    try:
        win.update_idletasks()
    except Exception:
        pass
    sw = int(getattr(win, "winfo_screenwidth", lambda: 1366)() or 1366)
    sh = int(getattr(win, "winfo_screenheight", lambda: 768)() or 768)
    return max(1, sw), max(1, sh)


def center_window(win, w: int, h: int) -> None:
    sw, sh = _screen_size(win)
    # ekran dışına taşmayı engelle
    ww = min(max(320, int(w or 320)), max(320, sw - 40))
    hh = min(max(220, int(h or 220)), max(220, sh - 80))
    x = max(0, (sw - ww) // 2)
    y = max(0, (sh - hh) // 2)
    win.geometry(f"{ww}x{hh}+{x}+{y}")


def center_window_smart(
    win,
    w: int,
    h: int,
    max_ratio: float = 0.90,
    min_w: int = 320,
    min_h: int = 220,
    **_ignored,
) -> None:
    """Ekrana uyumlu, güvenli merkezleme.

    - app_ui'den gelen min_w/min_h gibi argümanları destekler.
    - İstenen boyutu korumaya çalışır, fakat ekran sınırını aşmaz.
    - Küçük ekranlarda zorla 800x600 gibi büyütme yapmaz.
    """
    try:
        sw, sh = _screen_size(win)
        target_w = max(int(w or min_w), int(min_w))
        target_h = max(int(h or min_h), int(min_h))

        cap_w = max(320, int(sw * max_ratio))
        cap_h = max(220, int(sh * max_ratio))

        final_w = min(target_w, cap_w)
        final_h = min(target_h, cap_h)
        center_window(win, final_w, final_h)
    except Exception:
        try:
            center_window(win, w, h)
        except Exception:
            pass


def maximize_window(win) -> None:
    """Platforma göre en güvenli maximize."""
    try:
        plat = sys.platform.lower()

        if plat.startswith("win"):
            try:
                win.state("zoomed")
                return
            except Exception:
                pass

        try:
            win.attributes("-zoomed", True)
            return
        except Exception:
            pass

        sw, sh = _screen_size(win)
        w = int(sw * 0.95)
        h = int(sh * 0.92)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        pass