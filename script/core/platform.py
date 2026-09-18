from __future__ import annotations
import os
import subprocess
import sys
import ctypes


IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def configure_windows_dpi_awareness() -> None:
    if not IS_WINDOWS:
        return
    try:
        if getattr(ctypes, "windll", None):
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
                return
            except Exception:
                pass
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    except Exception:
        pass


def open_path(path: str) -> None:
    p = (path or "").strip()
    if not p:
        raise ValueError("Path boş.")
    if IS_WINDOWS:
        os.startfile(p)  # type: ignore[attr-defined]
        return
    if IS_MAC:
        subprocess.Popen(["open", p], close_fds=True)
        return
    subprocess.Popen(["xdg-open", p], close_fds=True)

def configure_macos_scaling(win) -> None:
    """
    macOS'ta Retina/DPI sebebiyle UI küçük kalmasın diye ölçek ayarı.
    Windows/Linux'ta no-op.
    """
    if not IS_MAC or not win:
        return
    try:
        # ttkbootstrap/tk uyumluluk
        try:
            win.tk.call("tk::mac::useThemedToplevel", 1)
        except Exception:
            pass
        try:
            win.tk.call("set", "::tk::mac::useCompatibilityMetrics", 0)
        except Exception:
            pass

        dpi = float(win.winfo_fpixels("1i") or 0)
        if dpi <= 0:
            return
        scale = max(1.0, dpi / 72.0)
        win.tk.call("tk", "scaling", scale)
    except Exception:
        pass
