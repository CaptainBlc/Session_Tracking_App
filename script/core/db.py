import sqlite3
from .paths import db_path


DEFAULT_THERAPISTS = [
    "Pervin Hoca",
    "Çağlar Hoca",
    "Elif Hoca",
    "Arif Hoca",
    "Sena Hoca",
    "Aybüke Hoca",
]


def _ensure_minimum_schema(conn: sqlite3.Connection) -> None:
    """Login/register ve temel UI akışlarının ihtiyaç duyduğu minimum şema."""
    cur = conn.cursor()

    # Kullanıcı yönetimi
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'egitim_gorevlisi',
            access_role TEXT DEFAULT 'egitim_gorevlisi',
            title_role TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            email TEXT DEFAULT '',
            therapist_name TEXT,
            created_at TEXT,
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
        """
    )

    # Terapist/ayar listeleri
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            therapist_name TEXT UNIQUE,
            therapist_role TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """
    )

    # settings eski şemalardan geliyorsa eksik kolonları tamamla
    try:
        cur.execute("PRAGMA table_info(settings)")
        s_cols = [r[1] for r in cur.fetchall()]
        if "therapist_role" not in s_cols:
            cur.execute("ALTER TABLE settings ADD COLUMN therapist_role TEXT DEFAULT ''")
        if "created_at" not in s_cols:
            cur.execute("ALTER TABLE settings ADD COLUMN created_at TEXT")
    except Exception:
        pass

    # Varsayılan terapistleri ilk kurulumda ekle
    try:
        cur.execute("SELECT COUNT(*) FROM settings WHERE COALESCE(is_active,1)=1")
        cnt = int((cur.fetchone() or [0])[0] or 0)
        if cnt == 0:
            now = ""
            try:
                import datetime
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                now = ""
            cur.executemany(
                "INSERT OR IGNORE INTO settings (therapist_name, therapist_role, is_active, created_at) VALUES (?, '', 1, ?)",
                [(n, now) for n in DEFAULT_THERAPISTS],
            )
    except Exception:
        pass

    # Öğrenci aile bilgileri
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ogrenci_aile_bilgileri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ogrenci_id INTEGER NOT NULL,
            veli_adi TEXT NOT NULL,
            yakinlik TEXT,
            telefon TEXT,
            email TEXT,
            adres TEXT,
            notlar TEXT,
            olusturma_tarihi TEXT,
            FOREIGN KEY (ogrenci_id) REFERENCES danisanlar(id)
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_aile_ogrenci ON ogrenci_aile_bilgileri(ogrenci_id)")

    # Öğrenci kimlik bilgileri
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ogrenci_kimlik_bilgileri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ogrenci_id INTEGER NOT NULL UNIQUE,
            tc_kimlik_no TEXT,
            dogum_tarihi TEXT,
            dogum_yeri TEXT,
            notlar TEXT,
            olusturma_tarihi TEXT,
            guncelleme_tarihi TEXT,
            FOREIGN KEY (ogrenci_id) REFERENCES danisanlar(id)
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_kimlik_tc ON ogrenci_kimlik_bilgileri(tc_kimlik_no)")

    # Danışan temel tablosu
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS danisanlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            telefon TEXT DEFAULT '',
            email TEXT DEFAULT '',
            veli_adi TEXT DEFAULT '',
            veli_telefon TEXT DEFAULT '',
            dogum_tarihi TEXT DEFAULT '',
            adres TEXT DEFAULT '',
            notlar TEXT DEFAULT '',
            olusturma_tarihi TEXT,
            aktif INTEGER DEFAULT 1,
            balance REAL DEFAULT 0
        )
        """
    )


    # Haftalık seans programı
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS haftalik_seans_programi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personel_adi TEXT NOT NULL,
            hafta_baslangic_tarihi TEXT NOT NULL,
            gun TEXT NOT NULL,
            saat TEXT NOT NULL,
            ogrenci_adi TEXT,
            oda_adi TEXT,
            notlar TEXT,
            olusturma_tarihi TEXT,
            guncelleme_tarihi TEXT,
            olusturan_kullanici_id INTEGER,
            UNIQUE(personel_adi, hafta_baslangic_tarihi, gun, saat)
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_haftalik_personel ON haftalik_seans_programi(personel_adi)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_haftalik_tarih ON haftalik_seans_programi(hafta_baslangic_tarihi)")

    # Refactor modüllerinin kullandığı tablolar
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS seans_takvimi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            saat TEXT,
            danisan_adi TEXT,
            terapist TEXT,
            oda TEXT,
            durum TEXT DEFAULT 'planlandi',
            notlar TEXT DEFAULT '',
            hizmet_bedeli REAL DEFAULT 0,
            odeme_sekli TEXT DEFAULT '',
            seans_alindi INTEGER DEFAULT 0,
            ucret_alindi INTEGER DEFAULT 0,
            olusturma_tarihi TEXT,
            olusturan_kullanici_id INTEGER,
            record_id INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            saat TEXT,
            danisan_adi TEXT,
            terapist TEXT,
            hizmet_bedeli REAL DEFAULT 0,
            alinan_ucret REAL DEFAULT 0,
            kalan_borc REAL DEFAULT 0,
            seans_alindi INTEGER DEFAULT 0,
            notlar TEXT DEFAULT '',
            olusturma_tarihi TEXT,
            seans_id INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS odeme_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER,
            tutar REAL DEFAULT 0,
            tarih TEXT,
            odeme_sekli TEXT DEFAULT '',
            aciklama TEXT DEFAULT '',
            olusturma_tarihi TEXT,
            olusturan_kullanici_id INTEGER
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kasa_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            tip TEXT,
            aciklama TEXT,
            tutar REAL DEFAULT 0,
            odeme_sekli TEXT DEFAULT '',
            gider_kategorisi TEXT DEFAULT '',
            record_id INTEGER,
            seans_id INTEGER,
            olusturan_kullanici_id INTEGER,
            olusturma_tarihi TEXT
        )
        """
    )

    # Fiyatlandırma ve ücret takip modülleri
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ogrenci_personel_fiyatlandirma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ogrenci_id INTEGER NOT NULL,
            personel_adi TEXT NOT NULL,
            seans_ucreti REAL NOT NULL,
            baslangic_tarihi TEXT,
            bitis_tarihi TEXT,
            aktif INTEGER DEFAULT 1,
            zam_orani REAL DEFAULT 0,
            zam_uygulama_tarihi TEXT,
            olusturma_tarihi TEXT,
            guncelleme_tarihi TEXT
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fiyat_ogrenci ON ogrenci_personel_fiyatlandirma(ogrenci_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fiyat_personel ON ogrenci_personel_fiyatlandirma(personel_adi)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS personel_ucret_takibi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personel_adi TEXT NOT NULL,
            seans_id INTEGER,
            tarih TEXT NOT NULL,
            seans_ucreti REAL NOT NULL,
            personel_ucreti REAL NOT NULL,
            ucret_orani REAL DEFAULT 0,
            odeme_durumu TEXT DEFAULT 'beklemede',
            odeme_tarihi TEXT,
            aciklama TEXT,
            olusturma_tarihi TEXT,
            olusturan_kullanici_id INTEGER
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_personel_ucret_personel ON personel_ucret_takibi(personel_adi)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cocuk_gunluk_takip (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cocuk_id INTEGER NOT NULL,
            tarih TEXT NOT NULL,
            oda_adi TEXT,
            personel_adi TEXT NOT NULL,
            seans_id INTEGER,
            notlar TEXT,
            olusturma_tarihi TEXT
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cocuk_gunluk_tarih ON cocuk_gunluk_takip(tarih)")

    # Fiyat politikası (otomatik ücret)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pricing_policy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            teacher_name TEXT,
            price REAL NOT NULL,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(student_id, teacher_name)
        )
        """
    )

    # Audit trail / sistem logları
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_trail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            kullanici_id INTEGER,
            details TEXT,
            ip_address TEXT,
            olusturma_tarihi TEXT NOT NULL
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_tarih ON audit_trail(olusturma_tarihi)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sistem_gunlugu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            olay TEXT,
            aciklama TEXT,
            olusturma_tarihi TEXT
        )
        """
    )


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path()))
    conn.row_factory = sqlite3.Row
    _ensure_minimum_schema(conn)
    conn.commit()
    return conn


def init_db() -> None:
    conn = sqlite3.connect(str(db_path()))
    conn.row_factory = sqlite3.Row
    _ensure_minimum_schema(conn)

    # Geriye dönük legacy tablolar (eski scriptler için)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS seanslar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            saat TEXT,
            danisan TEXT NOT NULL,
            terapist TEXT NOT NULL,
            ucret REAL DEFAULT 0,
            alinan REAL DEFAULT 0,
            kalan REAL DEFAULT 0,
            notlar TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kayitlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seans_id INTEGER,
            tarih TEXT NOT NULL,
            danisan TEXT NOT NULL,
            terapist TEXT,
            ucret REAL DEFAULT 0,
            alinan REAL DEFAULT 0,
            kalan_borc REAL DEFAULT 0
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS kasa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            tip TEXT CHECK(tip IN ('giren','cikan')) NOT NULL,
            aciklama TEXT,
            tutar REAL DEFAULT 0
        )
        """
    )

    conn.commit()
    conn.close()