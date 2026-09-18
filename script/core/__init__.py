from __future__ import annotations

# core package export layer (kırılmaya dayanıklı)
# Amaç: app_ui/main "from core import X" yaptığında import patlamasın.

from .backup import *  # noqa: F401,F403
from .db import *  # noqa: F401,F403
from .env import *  # noqa: F401,F403
from .logging_utils import *  # noqa: F401,F403
from .migration import *  # noqa: F401,F403
from .money import *  # noqa: F401,F403
from .paths import *  # noqa: F401,F403
from .pricing import *  # noqa: F401,F403
from .security import *  # noqa: F401,F403
from .ui_utils import *  # noqa: F401,F403

from .platform import *  # noqa: F401,F403
from .window import *  # noqa: F401,F403
from .icons import *  # noqa: F401,F403
  # noqa: F401


def ensure_user_guide_present() -> None:
    """
    Bazı UI akışları bunu çağırıyor. Rehber dosyası yoksa crash ettirmesin.
    """
    try:
        ug = globals().get("user_guide_path", None)
        if callable(ug):
            p = ug()
            try:
                if hasattr(p, "exists") and not p.exists():
                    log_info(f"Kullanıcı rehberi bulunamadı: {p}")
            except Exception:
                pass
        else:
            log_info("user_guide_path() tanımlı değil; rehber kontrolü atlandı.")
    except Exception as e:
        try:
            log_exception("ensure_user_guide_present", e)
        except Exception:
            pass