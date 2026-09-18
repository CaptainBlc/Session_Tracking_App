from __future__ import annotations
import datetime

APP_TITLE = "Leta Takip"
APP_VERSION = "v2.0"
APP_BUILD = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# Personel ücret kuralları (kurum talebine göre)
PERSONEL_UCRET_KURALLARI = {
    "Arif Hoca": {"tip": "sabit", "tutar": 2500.0},
    "Pervin Hoca": {"tip": "yuzde", "oran": 100.0},
    "_default": {"tip": "yuzde", "oran": 40.0},
}

DEFAULT_THERAPISTS: list[str] = [
    "Pervin Hoca",
    "Çağlar Hoca",
    "Elif Hoca",
    "Arif Hoca",
    "Sena Hoca",
    "Aybüke Hoca",
]