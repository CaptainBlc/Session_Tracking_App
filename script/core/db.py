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
            record_id INTEGER,
            alinan_ucret REAL DEFAULT 0,
            kalan_borc REAL DEFAULT 0
        )
        """
    )
    # P0-B konsolidasyonu: mevcut bir DB'de seans_takvimi zaten olusmus
    # olabilir (yeni kolonlar olmadan) - eksikse ekle.
    try:
        cur.execute("PRAGMA table_info(seans_takvimi)")
        st_cols = [r[1] for r in cur.fetchall()]
        if "alinan_ucret" not in st_cols:
            cur.execute("ALTER TABLE seans_takvimi ADD COLUMN alinan_ucret REAL DEFAULT 0")
        if "kalan_borc" not in st_cols:
            cur.execute("ALTER TABLE seans_takvimi ADD COLUMN kalan_borc REAL DEFAULT 0")
    except Exception:
        pass

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS odeme_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER,
            seans_id INTEGER,
            tutar REAL DEFAULT 0,
            tarih TEXT,
            odeme_sekli TEXT DEFAULT '',
            aciklama TEXT DEFAULT '',
            olusturma_tarihi TEXT,
            olusturan_kullanici_id INTEGER
        )
        """
    )
    # P0-B konsolidasyonu: odeme_hareketleri'nde seans_id eksikse ekle.
    try:
        cur.execute("PRAGMA table_info(odeme_hareketleri)")
        oh_cols = [r[1] for r in cur.fetchall()]
        if "seans_id" not in oh_cols:
            cur.execute("ALTER TABLE odeme_hareketleri ADD COLUMN seans_id INTEGER")
    except Exception:
        pass
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

    _migrate_records_into_seans_takvimi(conn)


def _migrate_records_into_seans_takvimi(conn: sqlite3.Connection) -> None:
    """
    P0-B tek seferlik veri gocu: eski 'records' tablosu varsa (gercek
    kurulumlarda gecmis tahsilat/borc verisi tutuyor olabilir), icerigi
    seans_takvimi'ye tasinir. 'records' hicbir zaman DROP edilmez -
    gercek kurum verisiyle calisirken geri donus payi olsun diye
    'records_migrated_backup' olarak yeniden adlandirilir. 'records'
    tablosu yoksa (yeni kurulum ya da zaten gocmus DB) hemen cikar - bu
    yuzden fonksiyon her baglantida cagrilsa bile pratikte tek seferlik
    calisir.
    """
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='records'")
        if not cur.fetchone():
            return
    except Exception:
        return

    try:
        # _ensure_minimum_schema onceki CREATE/ALTER ifadeleriyle acik bir
        # (ambient) islem birakmis olabilir - kendi BEGIN'imizi baslatmadan
        # once onu kapatiyoruz, boylece bir hata durumunda rollback SADECE
        # bu gocu geri alir, kardes sema degisikliklerini etkilemez.
        conn.commit()
        cur.execute("BEGIN")

        # 1) records satiri bir seans_takvimi satirina bagliysa (iki yonlu
        #    eski FK'nin herhangi birinden) -> o seans_takvimi satirinin
        #    alinan_ucret/kalan_borc kolonlarini records'tan kopyala.
        cur.execute(
            """
            UPDATE seans_takvimi
            SET alinan_ucret = (
                    SELECT COALESCE(r.alinan_ucret,0) FROM records r
                    WHERE r.seans_id = seans_takvimi.id OR r.id = seans_takvimi.record_id
                    ORDER BY r.id DESC LIMIT 1
                ),
                kalan_borc = (
                    SELECT COALESCE(r.kalan_borc,0) FROM records r
                    WHERE r.seans_id = seans_takvimi.id OR r.id = seans_takvimi.record_id
                    ORDER BY r.id DESC LIMIT 1
                )
            WHERE EXISTS (
                SELECT 1 FROM records r
                WHERE r.seans_id = seans_takvimi.id OR r.id = seans_takvimi.record_id
            )
            """
        )
        updated = cur.rowcount

        # 2) records satiri hicbir seans_takvimi satirina bagli degilse
        #    (bagimsiz/devir borc kaydi) -> veri kaybolmasin diye yeni bir
        #    devir_borc satiri olarak seans_takvimi'ye eklenir (bkz.
        #    pipeline.eski_borc_ekle ile ayni sekil).
        cur.execute(
            """
            INSERT INTO seans_takvimi
                (tarih, saat, danisan_adi, terapist, oda, durum, notlar,
                 hizmet_bedeli, odeme_sekli, seans_alindi, ucret_alindi,
                 olusturma_tarihi, olusturan_kullanici_id, record_id,
                 alinan_ucret, kalan_borc)
            SELECT
                COALESCE(r.tarih,''), COALESCE(r.saat,''), COALESCE(r.danisan_adi,''),
                COALESCE(r.terapist,''), '', 'devir_borc',
                ('Devir Borç (eski kayıttan taşındı) | ' || COALESCE(r.notlar,'')),
                COALESCE(r.hizmet_bedeli,0), '', COALESCE(r.seans_alindi,0), 0,
                COALESCE(r.olusturma_tarihi,''), NULL, NULL,
                COALESCE(r.alinan_ucret,0), COALESCE(r.kalan_borc,0)
            FROM records r
            WHERE NOT EXISTS (
                SELECT 1 FROM seans_takvimi st
                WHERE st.id = r.seans_id OR st.record_id = r.id
            )
            """
        )
        inserted = cur.rowcount

        cur.execute("ALTER TABLE records RENAME TO records_migrated_backup")

        cur.execute(
            "INSERT INTO sistem_gunlugu (tarih, olay, aciklama, olusturma_tarihi) VALUES (date('now'), 'P0B_MIGRATION', ?, datetime('now'))",
            (
                f"records -> seans_takvimi gocu tamamlandi: {updated} satir guncellendi, "
                f"{inserted} yeni devir_borc satiri eklendi, records -> records_migrated_backup "
                f"olarak yeniden adlandirildi.",
            ),
        )

        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            from .logging_utils import log_exception
            log_exception("_migrate_records_into_seans_takvimi", e)
        except Exception:
            pass


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
    # NOT (P0-B): 'seanslar' ve 'kayitlar' kaldirildi - kod tabaninda hicbir
    # sorgu bu iki tabloyu kullanmiyordu (spec/p0b-veri-kaynagi-konsolidasyonu.md
    # Bolum 2.1, dogrulandi). 'kasa' (asagida) farkli bir tablo, dokunulmadi.
    cur = conn.cursor()
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