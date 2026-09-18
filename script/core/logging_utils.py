from __future__ import annotations
import datetime
import traceback
from .paths import error_log_path


def log_exception(prefix: str, exc: BaseException) -> None:
    try:
        p = error_log_path()
        with open(p, "a", encoding="utf-8") as f:
            f.write("\n" + ("=" * 80) + "\n")
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {prefix}\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except Exception:
        pass


def log_info(msg: str) -> None:
    try:
        p = error_log_path()
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | INFO | {msg}\n")
    except Exception:
        pass