from __future__ import annotations

import datetime
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

from .paths import data_dir, db_path


_DRIVE_BACKUP_SUBDIR = "LetaYonetim_Yedek"


def backups_dir() -> Path:
    return data_dir() / "Yedekler"


def _macos_gdrive_candidates() -> list[Path]:
    """
    macOS Google Drive for Desktop (güncel istemci) senkron klasörü adayları.
    Sadece gerçekten VAR OLAN kökler döner (kör tahmin değil) — hesap adı
    önceden bilinemediği ve birden fazla hesap bağlı olabileceği için
    ~/Library/CloudStorage altında glob ile taranır.
    """
    out: list[Path] = []
    home = Path.home()

    try:
        cloud_storage = home / "Library" / "CloudStorage"
        if cloud_storage.exists():
            for acc_dir in cloud_storage.glob("GoogleDrive-*"):
                try:
                    my_drive = acc_dir / "My Drive"
                    if my_drive.exists():
                        out.append(my_drive / _DRIVE_BACKUP_SUBDIR)
                except Exception:
                    pass
    except Exception:
        pass

    # Eski istemci (Backup and Sync, artık desteklenmiyor) kalıntısı ihtimaline karşı
    for rel in ("Google Drive/My Drive", "Google Drive"):
        try:
            cand = home / rel
            if cand.exists():
                out.append(cand / _DRIVE_BACKUP_SUBDIR)
        except Exception:
            pass

    return out


def _windows_gdrive_candidates() -> list[Path]:
    """
    Windows Google Drive for Desktop (güncel istemci) senkron klasörü adayları.
    İki senkron modu da ele alınır: sürücü harfi (streaming) ve yerel klasör
    senkronu (mirror). Sadece gerçekten VAR OLAN kökler döner.
    """
    out: list[Path] = []

    # 1) Sürücü harfi modu (varsayılan, streaming) — sabit "G:" varsaymak yerine tara
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        try:
            my_drive = Path(f"{letter}:/My Drive")
            if my_drive.exists():
                out.append(my_drive / _DRIVE_BACKUP_SUBDIR)
        except Exception:
            pass

    # 2) Yerel klasör senkronu modu (mirror/offline mod)
    home = Path.home()
    for rel in ("Google Drive", "My Drive"):
        try:
            cand = home / rel
            if cand.exists():
                out.append(cand / _DRIVE_BACKUP_SUBDIR)
        except Exception:
            pass

    # Eski istemci (Backup and Sync) kalıntısı ihtimaline karşı
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        try:
            cand = Path(local) / "Google" / "DriveFS"
            if cand.exists():
                out.append(cand / _DRIVE_BACKUP_SUBDIR)
        except Exception:
            pass

    return out


def _google_drive_candidates() -> list[Path]:
    """
    Google Drive senkron klasörü adayları — platform bazlı (macOS/Windows),
    gerçekten var olan kökler taranır. LETA_BACKUP_GDRIVE_DIR ortam
    değişkeni her zaman ek bir aday olarak eklenir (manuel override, elle
    verildiği için var olup olmadığı kontrol edilmeden kabul edilir) ama
    otomatik taramayı ENGELLEMEZ — ikisi birlikte kullanılabilir (mevcut
    davranış korunuyor).
    """
    out: list[Path] = []

    env = os.environ.get("LETA_BACKUP_GDRIVE_DIR", "").strip()
    if env:
        try:
            out.append(Path(env).expanduser())
        except Exception:
            pass

    try:
        if sys.platform == "darwin":
            out.extend(_macos_gdrive_candidates())
        elif sys.platform.startswith("win"):
            out.extend(_windows_gdrive_candidates())
        else:
            # Linux / diğer: kurum bu platformda değil, düşük öncelikli genel fallback
            home = Path.home()
            cand = home / "Google Drive"
            if cand.exists():
                out.append(cand / _DRIVE_BACKUP_SUBDIR)
    except Exception:
        pass

    return out


def _backup_mirror_dirs() -> list[Path]:
    """Ek yedek klasörleri (lokal bozulmaya karşı ikinci lokasyon)."""
    out: list[Path] = []

    # Elle verilen mirror klasörü
    env = os.environ.get("LETA_BACKUP_MIRROR", "").strip()
    if env:
        try:
            out.append(Path(env).expanduser())
        except Exception:
            pass

    # Varsayılan lokal mirror
    try:
        out.append(Path.home() / "LetaYonetim_BackupMirror")
    except Exception:
        pass

    # Windows hedef: C:\Users\...\AppData\Local\LetaYonetim\Yedekler
    try:
        out.append(data_dir() / "Yedekler")
    except Exception:
        pass

    # Google Drive senkron klasörü (kurumun kendi hesabı) — sadece var olan kökler
    for gdir in _google_drive_candidates():
        try:
            out.append(gdir)
        except Exception:
            pass

    # Tekilleştir
    uniq: list[Path] = []
    seen: set[str] = set()
    for p in out:
        k = str(p)
        if k not in seen:
            uniq.append(p)
            seen.add(k)
    return uniq


def _db_integrity_ok(path: Path) -> bool:
    try:
        conn = sqlite3.connect(str(path))
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        row = cur.fetchone()
        conn.close()
        return bool(row and str(row[0]).lower() == "ok")
    except Exception:
        return False


def _write_backup_status(
    basarili: bool,
    hedef: str | None,
    drive_klasoru_bulundu: bool,
    drive_yolu: str | None,
    hata_mesaji: str | None,
) -> None:
    """
    Son yedekleme denemesinin sonucunu data_dir()/yedek_durumu.json dosyasına
    yazar. Bu fonksiyon ASLA dışarı exception fırlatmaz — silent_backup()'ın
    sessiz (uygulama akışını bozmayan) davranışı korunur, sadece artık son
    deneme sonucu okunabilir bir izde tutulur.
    """
    try:
        durum = {
            "son_deneme_zamani": datetime.datetime.now().isoformat(timespec="seconds"),
            "basarili": bool(basarili),
            "hedef": hedef,
            "drive_klasoru_bulundu": bool(drive_klasoru_bulundu),
            "drive_yolu": drive_yolu,
            "hata_mesaji": hata_mesaji,
        }
        (data_dir() / "yedek_durumu.json").write_text(
            json.dumps(durum, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def read_backup_status() -> dict | None:
    """yedek_durumu.json dosyasını okur. Dosya yoksa/bozuksa None döner."""
    try:
        p = data_dir() / "yedek_durumu.json"
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def son_yedek_durumu_ozeti() -> str:
    """Son yedek durumunu insan-okunur tek satıra çevirir ("Hakkında" ekranında gösterilir)."""
    try:
        durum = read_backup_status()
        if not durum:
            return "Son yedek: hiç denenmedi"

        zaman_str = durum.get("son_deneme_zamani") or ""
        try:
            zaman = datetime.datetime.fromisoformat(zaman_str)
            zaman_str = zaman.strftime("%d.%m.%Y %H:%M")
        except Exception:
            pass

        if not durum.get("basarili"):
            hata = durum.get("hata_mesaji") or "bilinmeyen hata"
            return f"Son yedek: {zaman_str} — başarısız ({hata})"

        if durum.get("drive_klasoru_bulundu"):
            return f"Son yedek: {zaman_str} — Google Drive'a yazıldı"

        return f"Son yedek: {zaman_str} — yerel yedek OK, Google Drive klasörü bulunamadı"
    except Exception:
        return "Son yedek: durum okunamadı"


def _write_recovery_info() -> None:
    """Kurumun developer olmadan taşıma/geri yükleme yapabilmesi için bilgi dosyası."""
    try:
        info = data_dir() / "YEDEK_GERI_YUKLEME_BILGISI.txt"
        lines = [
            "Leta Takip Yedek Bilgisi",
            "========================",
            f"Ana veritabanı adı: {db_path().name}",
            f"Ana veritabanı konumu: {db_path()}",
            f"Yedek klasörü: {backups_dir()}",
            "",
            "Yedek dosya adı deseni: backup_YYYY-MM-DD_HHMMSS.db",
            "(örn. backup_2026-09-18_143005.db — en yeni tarih/saat damgalı olan geçerli yedektir)",
            "",
            "Ek mirror klasörleri:",
        ]
        for d in _backup_mirror_dirs():
            lines.append(f"- {d}")
        lines += [
            "",
            "Google Drive öneri:",
            "- Kurum bilgisayarına Google Drive for Desktop kurulmalı ve bir",
            "  Google hesabıyla senkron aktif olmalı.",
            "- Uygulama, Drive senkron klasörünü otomatik bulmaya çalışır:",
            "  * macOS'ta: ~/Library/CloudStorage/GoogleDrive-<hesap>/My Drive/LetaYonetim_Yedek",
            "  * Windows'ta (sürücü harfi modu): G:\\My Drive\\LetaYonetim_Yedek (harf değişebilir)",
            "  * Windows'ta (klasör senkron modu): %USERPROFILE%\\Google Drive\\LetaYonetim_Yedek",
            "- Otomatik bulunamazsa LETA_BACKUP_GDRIVE_DIR ortam değişkenine",
            "  Drive senkron klasörünün TAM yolunu yazabilirsiniz — bu her zaman",
            "  otomatik taramaya ek bir yedek hedefi olarak kullanılır.",
            "",
            "Yeni bir bilgisayarda geri yükleme:",
            "- Yukarıdaki Drive klasöründen (veya bu bilgisayardaki Yedekler",
            "  klasöründen) en güncel backup_*.db dosyasını bulun.",
            "- Bu dosyayı kopyalayıp yeni bilgisayarda yukarıdaki 'Ana veritabanı",
            f"  konumu' yoluna '{db_path().name}' adıyla yapıştırın (uygulama kapalıyken).",
            "- Uygulamayı yeniden açın; geri yüklenen veriyle devam eder.",
            "",
            "Son yedek durumu için uygulama içinde 'Hakkında' ekranına bakabilirsiniz",
            "(en son yedekleme denemesinin Drive'a ulaşıp ulaşmadığını gösterir).",
        ]
        info.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass


def _copy_to_mirrors(src: Path) -> None:
    for mdir in _backup_mirror_dirs():
        try:
            mdir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(mdir / src.name))
        except Exception:
            pass


def _drive_durumu_belirle() -> tuple[bool, str | None]:
    """(drive_klasoru_bulundu, drive_yolu) — durum dosyasına yazmak için."""
    try:
        adaylar = _google_drive_candidates()
        if adaylar:
            return True, str(adaylar[0])
    except Exception:
        pass
    return False, None


def backup_now(prefix: str = "backup") -> str | None:
    hedef_str: str | None = None
    try:
        bdir = backups_dir()
        bdir.mkdir(parents=True, exist_ok=True)

        src = db_path()
        if not src.exists():
            _write_backup_status(False, None, False, None, "Kaynak veritabanı dosyası bulunamadı.")
            return None

        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        dst = bdir / f"{prefix}_{ts}.db"
        shutil.copy2(str(src), str(dst))
        hedef_str = dst.name

        # Mirror'a da yaz (lokal dizin bozulmasına karşı + Google Drive varsa oraya da)
        _copy_to_mirrors(dst)
        _write_recovery_info()

        # Rotasyon
        backups = sorted(bdir.glob(f"{prefix}_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[30:]:
            try:
                old.unlink()
            except Exception:
                pass

        drive_bulundu, drive_yolu = _drive_durumu_belirle()
        _write_backup_status(True, hedef_str, drive_bulundu, drive_yolu, None)

        return str(dst)
    except Exception as e:
        _write_backup_status(False, hedef_str, False, None, str(e))
        return None


def silent_backup() -> None:
    """Açılışta sessiz yedek: integrity OK ise yedekle + mirror kopya."""
    try:
        src = db_path()
        if not src.exists():
            _write_backup_status(False, None, False, None, "Kaynak veritabanı dosyası henüz yok.")
            return

        # Kaynak DB bozuk görünüyorsa yine de dokunmadan çık (durumu kötüleştirmeyelim)
        if not _db_integrity_ok(src):
            _write_backup_status(False, None, False, None, "Veritabanı bütünlük kontrolü başarısız — yedek atlandı.")
            return

        bdir = backups_dir()
        bdir.mkdir(parents=True, exist_ok=True)

        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
        dst = bdir / f"backup_{ts}.db"
        shutil.copy2(str(src), str(dst))
        _copy_to_mirrors(dst)
        _write_recovery_info()

        backups = sorted(bdir.glob("backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[30:]:
            try:
                old.unlink()
            except Exception:
                pass

        drive_bulundu, drive_yolu = _drive_durumu_belirle()
        _write_backup_status(True, dst.name, drive_bulundu, drive_yolu, None)
    except Exception as e:
        try:
            _write_backup_status(False, None, False, None, str(e))
        except Exception:
            pass
