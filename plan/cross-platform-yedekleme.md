# Plan: Çapraz Platform Veri Güvenliği ve Yedekleme

Kaynak: `spec/cross-platform-yedekleme.md` (Batuhan tarafından onaylandı).
Status: draft — Batuhan onayı bekliyor. Onaylanıp commit'lenmeden kod
aşamasına geçilmez.

Onaylanan 3 karar noktası (spec'in sonunda da not edildi, burada tekrar
tek yerde toplanıyor çünkü uygulama sırasını doğrudan etkiliyor):

1. Durum dosyası formatı: JSON, `data_dir()/yedek_durumu.json`.
2. Özet satırı: **sadece "Hakkında" ekranına** eklenir — Ayarlar ekranı
   entegrasyonu bu plan'ın kapsamında **değil**.
3. Kurumda Google Drive for Desktop **kurulu değil** — bu yüzden Windows
   tarafında "gerçek Drive hesabıyla" uçtan uca test şu an mümkün değilse
   "Drive bulunamadı" dalı simüle edilerek doğrulanır (bkz. Bölüm 2,
   checklist madde 4).

## 1. Uygulama sırası

Sıra spec Bölüm 4'teki bağımlılık zincirini izliyor: önce platform tespiti
(veri katmanının temeli, hiçbir şey ona bağlı değil), sonra durum
dosyası yazma/okuma (platform tespitine bağlı değil ama backup
fonksiyonlarına bağlı), en son UI entegrasyonu (ikisine de bağlı).
Tahminler spec Bölüm 7'deki toplam ~5-6 saatten dağıtıldı.

### Adım 1 — macOS Google Drive aday üretici (~1 saat)

- Dosya: `script/core/backup.py`
- Yeni fonksiyon: `_macos_gdrive_candidates() -> list[Path]`
- İçerik:
  - `Path.home() / "Library" / "CloudStorage"` altında `GoogleDrive-*`
    glob taraması, her eşleşen klasör altında `My Drive` var mı kontrolü.
  - Eski istemci fallback: `~/Google Drive/My Drive`, `~/Google Drive`.
  - Var olan tüm adaylar döner (ilk bulunan değil — spec Bölüm 2).
- Bu adımda macOS'a fiziksel erişim yok; fonksiyon mantık olarak yazılır,
  gerçek makinede doğrulama Bölüm 2, madde 5'te ayrı tutuluyor.

### Adım 2 — Windows Google Drive aday üretici (~1 saat)

- Dosya: `script/core/backup.py`
- Yeni fonksiyon: `_windows_gdrive_candidates() -> list[Path]`
- İçerik:
  - `A:`–`Z:` sürücü harfi taraması, her harfte `\My Drive` klasörü var mı
    (`Path.exists()`, 26 çağrı — spec Bölüm 6'da maliyeti kabul edilebilir
    bulundu).
  - Mevcut "yerel klasör senkronu" adayları korunur:
    `%USERPROFILE%\Google Drive`, `%USERPROFILE%\My Drive`.
  - Eski istemci deseni korunur: `%LOCALAPPDATA%\Google\Drive\`.
- Mevcut kodda zaten benzer adaylar var — bu adım onları yeni fonksiyona
  taşımak + sürücü harfi taramasını eklemek.

### Adım 3 — Platform dallanması (`_google_drive_candidates()`) (~30-45 dakika)

- Dosya: `script/core/backup.py`
- `_google_drive_candidates()` içine `sys.platform` bazlı dallanma:
  - `"darwin"` → Adım 1'deki fonksiyon
  - `startswith("win")` → Adım 2'deki fonksiyon
  - diğer (Linux) → mevcut genel `home / "Google Drive"` fallback korunur
- `LETA_BACKUP_GDRIVE_DIR` ortam değişkeni override'ı en üstte, platform
  dallanmasından önce kontrol edilmeye devam eder (mevcut davranış —
  manuel override her zaman kazanır).
- `_backup_mirror_dirs()` dokunulmaz — zaten bu fonksiyonu çağırıyor,
  alt katman değiştiği için otomatik faydalanır (spec Bölüm 4).

Adım 1-3 toplamı spec'teki "~2-3 saat" tahminine karşılık geliyor.

### Adım 4 — Durum dosyası yazma (`_write_backup_status()`) (~45 dakika)

- Dosya: `script/core/backup.py`
- Yeni fonksiyon: `_write_backup_status(basarili, hedef, drive_klasoru_bulundu, drive_yolu, hata_mesaji)`
- `data_dir() / "yedek_durumu.json"` dosyasına spec Bölüm 3'teki şemayla
  yazar (`son_deneme_zamani`, `basarili`, `hedef`, `drive_klasoru_bulundu`,
  `drive_yolu`, `hata_mesaji`).
- Yazma işlemi kendi `except: pass` bloğunda — durum dosyası yazımı
  başarısız olsa bile uygulama akışı etkilenmez (spec Bölüm 3).

### Adım 5 — Durum dosyası okuma + özet (`read_backup_status()`, `son_yedek_durumu_ozeti()`) (~30-45 dakika)

- Dosya: `script/core/backup.py`
- `read_backup_status() -> dict | None` — dosya yoksa/bozuksa `None`.
- `son_yedek_durumu_ozeti() -> str` — üç olası çıktı biçimi (spec Bölüm 3):
  - "Son yedek: hiç denenmedi"
  - "Son yedek: ... — Google Drive'a yazıldı"
  - "Son yedek: ... — yerel yedek OK, Google Drive klasörü bulunamadı"

Adım 4-5 toplamı spec'teki "~1-2 saat" tahminine karşılık geliyor.

### Adım 6 — `backup_now()` / `silent_backup()` entegrasyonu (~30 dakika)

- Dosya: `script/core/backup.py`
- Her iki fonksiyonun sonunda (hem başarı hem `except` bloklarında)
  `_write_backup_status(...)` çağrısı eklenir.
- `silent_backup()`'ın mevcut sessiz `except: pass` davranışı **korunur**
  — sadece artık aynı yerden durum dosyasına da yazılıyor.

### Adım 7 — `_write_recovery_info()` metin güncellemesi (~30 dakika)

- Dosya: `script/core/backup.py`
- `YEDEK_GERI_YUKLEME_BILGISI.txt` içeriğine somut adımlar eklenir:
  dosya adı deseni (`backup_YYYY-MM-DD_HHMMSS.db`), macOS `CloudStorage`
  yol örneği, Windows sürücü harfi yol örneği.

### Adım 8 — `core/__init__.py` export (~10-15 dakika)

- Dosya: `script/core/__init__.py`
- `son_yedek_durumu_ozeti` (ve gerekiyorsa `read_backup_status`) mevcut
  export listesine eklenir — `main.py`'nin `from core import *` çağrısı
  bu fonksiyonlara erişebilsin diye.

### Adım 9 — `hakkinda_goster()` UI entegrasyonu (~1 saat)

- Dosya: `script/app_ui.py`, satır ~8758
- `core.backup.son_yedek_durumu_ozeti()` çağrısı eklenir, dönen tek satır
  mevcut `messagebox.showinfo("Hakkında", ...)` metnine eklenir.
- **Ayarlar ekranına ekleme yapılmaz** — karar noktası 2 gereği bu spec'in
  ve bu plan'ın kapsamı dışında.

Adım 7-9 toplamı spec'teki "~1 saat + ~30 dakika" tahminlerine karşılık
geliyor.

**Toplam tahmini kod yazım süresi: ~5-6 saat** (spec Bölüm 7 ile uyumlu).

## 2. Manuel doğrulama checklist'i

Bu checklist iki ayrı bölüme ayrılıyor: (A) bu plan'ın "tamamlandı"
sayılması için gereken Windows-taraflı testler, (B) kurumla koordineli,
ayrı bir sonraki adım olan macOS testi — **B, bu plan'ın tamamlanma
kriterine dahil değil.**

### A. Windows tarafı (bu planın tamamlanma kriteri)

1. [ ] `_windows_gdrive_candidates()` birim testi: sahte/var olmayan bir
   sürücü harfi + `%USERPROFILE%` altında olmayan bir yol ile çağrılıp
   boş liste döndüğü doğrulanır (Drive kurulu değilken gerçek davranış).
2. [ ] `_google_drive_candidates()` platform dallanması: `sys.platform`
   mock'lanarak (veya doğrudan Windows'ta çalıştırılarak)
   `_windows_gdrive_candidates()`'in çağrıldığı, macOS/Linux dalının
   çağrılmadığı doğrulanır.
3. [ ] `LETA_BACKUP_GDRIVE_DIR` ortam değişkeni set edildiğinde tarama
   atlanıp doğrudan override yolunun kullanıldığı doğrulanır (mevcut
   davranış regresyona uğramamalı).
4. [ ] **"Drive bulunamadı" dalı (kurumdaki gerçek durumla eşleşen
   senaryo):** Kurumda Drive for Desktop kurulu olmadığı için bu dal
   gerçek bir hesapla test edilemiyor. Bunun yerine: sistemde Drive for
   Desktop kurulu olmayan/olmadığı varsayılan bir ortamda (ör. mevcut
   geliştirme makinesi, ya da `LETA_BACKUP_GDRIVE_DIR` set edilmeden)
   `backup_now()` çağrılır ve:
   - `yedek_durumu.json` dosyasının oluştuğu,
   - `drive_klasoru_bulundu: false` yazıldığı,
   - `drive_yolu: null` olduğu,
   - yerel mirror'a (`data_dir()/Yedekler`, `~/LetaYonetim_BackupMirror`)
     yedeğin yine de düştüğü
   doğrulanır. Bu, kurumdaki gerçek senaryonun simülasyonudur.
5. [ ] **Eğer Batuhan'ın kendi makinesinde gerçek bir Google Drive for
   Desktop hesabı kuruluysa** (kurumdakinden bağımsız, opsiyonel ekstra
   doğrulama): `backup_now()` çağrılır, `drive_klasoru_bulundu: true`,
   `drive_yolu` gerçek bir yol, yedek dosyasının o yolda oluştuğu
   doğrulanır. Bu adım kurulu Drive hesabı yoksa atlanır, plan'ın
   tamamlanma kriterine dahil değildir (opsiyonel ekstra güven artışı).
6. [ ] `son_yedek_durumu_ozeti()` üç durumun (hiç denenmedi / Drive'a
   yazıldı / Drive bulunamadı) doğru insan-okunur metni ürettiği
   doğrulanır.
7. [ ] "Hakkında" ekranı açılır, özet satırının mesaj metnine eklendiği
   görsel olarak doğrulanır.
8. [ ] `_write_recovery_info()` ile üretilen `YEDEK_GERI_YUKLEME_BILGISI.txt`
   dosyası açılıp yeni eklenen adımların (dosya adı deseni, macOS/Windows
   yol örnekleri) okunabilir ve doğru olduğu kontrol edilir.
9. [ ] `silent_backup()`'ın mevcut sessiz davranışının regresyona
   uğramadığı doğrulanır — yani hata durumunda hâlâ popup/exception
   fırlatmadığı, sadece durum dosyasına yazdığı.

### B. macOS tarafı — kurumla koordineli, AYRI bir sonraki adım

Bu bölüm bu plan'ın "tamamlandı" sayılma kriterine **dahil değildir**.
Spec Bölüm 7'de de aynı şekilde ayrı bir bağımlılık/risk olarak
işaretlenmişti.

1. [ ] Kurumun macOS makinesine erişim sağlandığında (Batuhan'ın kendi
   erişimi ya da kurumla koordineli uzaktan bir oturum), `_macos_gdrive_candidates()`
   gerçek `~/Library/CloudStorage/GoogleDrive-<email>/My Drive` yoluyla
   test edilir.
2. [ ] Kurumda birden fazla Google hesabı bağlıysa, glob taramasının
   hepsini bulduğu doğrulanır.
3. [ ] macOS izin/sandbox riski (spec Bölüm 6) — Full Disk Access
   gerekip gerekmediği gerçek makinede bir kez elle doğrulanır.
4. [ ] Bu adımlar tamamlanana kadar macOS tarafı "kod mantık olarak
   doğru, gerçek ortamda doğrulanmadı" statüsünde kalır — bu durum
   `REVIEW.md`'ye veya ilgili takip kaydına not düşülür.

## 3. Commit noktası

- Bu `plan.md` dosyası commit edilmez — Batuhan okur, onaylar, kendisi
  commit'ler.
- Kod aşamasına (backend-engineer / ilgili implementasyon) bu plan
  onaylanıp commit'lenmeden geçilmez.
- Kod tamamlandıktan sonra da commit'i Batuhan atar, Claude atmaz —
  proje genelindeki değişmez kural burada da geçerli.

---

**Onay noktası:** Bu `plan.md` Batuhan tarafından onaylanıp commit'lenene
kadar kod aşamasına geçilmez.
