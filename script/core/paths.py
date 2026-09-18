from __future__ import annotations
import os
import sys
from pathlib import Path


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def app_dir() -> Path:
    # frozen / normal
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    # test override
    test_dir = os.environ.get("LETA_TEST_DATA_DIR", "").strip()
    if test_dir:
        td = Path(test_dir).expanduser()
        return ensure_dir(td)

    # portable mode: app_dir/portable_mode.txt
    if (app_dir() / "portable_mode.txt").exists():
        return ensure_dir(app_dir() / "data")

    # platform default
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
        return ensure_dir(Path(base) / "LetaYonetim")
    if sys.platform == "darwin":
        return ensure_dir(Path.home() / "Library" / "Application Support" / "LetaYonetim")

    xdg = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return ensure_dir(Path(xdg) / "LetaYonetim")


def db_path(filename: str = "leta_data.db") -> Path:
    return data_dir() / filename


def assets_dir() -> Path:
    # PyInstaller frozen: bundle içindeki assets
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        p = Path(sys._MEIPASS) / "assets"
        if p.exists():
            return p
    # Öncelik: script/assets (repo düzeni), sonra app/assets
    candidates = [
        app_dir() / "script" / "assets",
        app_dir() / "assets",
    ]
    for c in candidates:
        if c.exists():
            return ensure_dir(c)
    return ensure_dir(candidates[0])


def user_guide_path() -> Path:
    # basit: assets içinde txt/pdf
    return assets_dir() / "KULLANIM_KILAVUZU.txt"


def error_log_path() -> Path:
    return data_dir() / "leta_error.log"
    
def backups_dir() -> Path:
    """
    Veritabanı yedeklerinin tutulduğu klasör.
    """
    return ensure_dir(data_dir() / "Yedekler")