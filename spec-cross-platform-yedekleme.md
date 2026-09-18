# Spec: Çapraz Platform Veri Güvenliği ve Yedekleme

Kaynak: `intent/2026-09-18-cross-platform-yedekleme.md` (onaylandı, açık soru yok).
Status: draft — Batuhan onayı bekliyor.

## 1. Özellik özeti

Leta Takip yerel-öncelikli (offline-first) bir masaüstü uygulaması: ana veri
kaynağı her zaman yerel SQLite dosyasıdır (`leta_data.db`), internet
kesilse bile seans/ödeme kaydı durmaz. Bu spec'in kapsamı, mevcut
**tek-yönlü, pasif Google Drive yedeği** mekanizmasını hem Windows hem
macOS'ta güvenilir çalışır hale getirmek ve yedek durumunu kullanıcıya
görünür kılmaktır.

**AÇIKÇA KAPSAM DIŞI (Batuhan tarafından reddedildi):** canlı/gerçek-zamanlı
bulut veritabanı, çift yönlü senkron, otomatik conflict resolution. Bu
tasarım kararı intent aşamasında netleşti, bu spec'te tekrar açılmaz.
Google Drive burada sadece "arkada senkronlanan bir klasöre pasif kopya
bırakma" amacıyla kullanılıyor — bir senkron veritabanı değil.

Neden gerekli: kurum macOS'ta gerçek veri girecek, Batuhan Windows'ta
geliştiriyor ve kurumun makinesine doğrudan erişimi yok. Mevcut
`_google_drive_candidates()` sadece Windows'a özgü eski yol varsayımlarıyla
yazılmış; macOS'un güncel "Google Drive for Desktop" istemcisini hiç
kapsamıyor. Ayrıca `silent_backup()` tamamen sessiz — DB bozuksa veya Drive
klasörü bulunamazsa kullanıcı hiçbir şey görmüyor.

## 2. macOS / Windows Google Drive klasör tespiti tasarımı

### macOS — Google Drive for Desktop (güncel istemci)

Google, eski "Backup and Sync" istemcisini kaldırdı; güncel istemci
("Google Drive for Desktop", 2022 sonrası) macOS'ta senkron klasörleri
`~/Library/CloudStorage/` altına, **hesap başına ayrı bir klasör** olarak
bağlar:

```
~/Library/CloudStorage/GoogleDrive-<email>/My Drive/...
~/Library/CloudStorage/GoogleDrive-<email>/Shared drives/...
```

`<email>` kullanıcının Google hesap adresidir ve makineye önceden
bilinemez; ayrıca aynı makinede **birden fazla Google hesabı** bağlı
olabilir (her biri kendi `GoogleDrive-<email>` klasörüyle). Bu yüzden sabit
bir yol yazılamaz — **glob ile taranmalı**:

```python
Path.home() / "Library" / "CloudStorage"
# glob: "GoogleDrive-*" -> her eşleşen klasör altında "My Drive" var mı kontrol et
```

Eski istemci kalıntısı ihtimaline karşı (bazı kurulumlarda hâlâ görülebilir,
düşük öncelik ama ucuz bir kontrol):
```
~/Google Drive/My Drive
~/Google Drive
```

### Windows — Google Drive for Desktop (güncel istemci)

Güncel istemci Windows'ta iki senkron modundan biriyle çalışır, ikisi de
olası ve ikisi de ele alınmalı:

1. **"Sürücü harfi" modu (varsayılan, streaming):** Drive, sanal bir sürücü
   harfi olarak bağlanır — genelde `G:\My Drive`, ama kullanıcı farklı bir
   harf seçmiş olabilir. Sabit `G:` varsaymak yerine `A`–`Z` arası olası
   harfleri tarayıp her birinde `My Drive` klasörünün var olup olmadığına
   bakılır (ucuz bir işlem, 26 `Path.exists()` çağrısı).
2. **"Yerel klasör senkronu" modu (mirror/offline mod):** Kullanıcı bu modu
   seçmişse yol `%USERPROFILE%\Google Drive` (bazı sürümlerde
   `%USERPROFILE%\My Drive`) altında olur — mevcut kod zaten buna benzer
   adaylar deniyor, bu adaylar korunur.

Eski istemci (Backup and Sync, artık desteklenmiyor ama kurulu makineler
olabilir): `%LOCALAPPDATA%\Google\Drive\` deseni — mevcut kodda benzer bir
kontrol zaten var, korunur.

### Platform ayrımı

`_google_drive_candidates()` içine `sys.platform` bazlı dallanma eklenir:
`sys.platform == "darwin"` ise macOS aday üretici çağrılır, `startswith("win")`
ise Windows aday üretici (sürücü harfi tarama + klasör senkron yolları)
çağrılır. `LETA_BACKUP_GDRIVE_DIR` ortam değişkeni override'ı her iki
platformda da önceliklidir (mevcut davranış korunur — manuel override her
zaman kazanır, tarama sadece fallback).

Bulunan adaylar arasından **var olan ilk klasör** değil, **var olan
tümü** mirror listesine eklenir (mevcut `_backup_mirror_dirs()` davranışı
zaten böyle — korunuyor); böylece birden fazla Drive hesabı bağlıysa
hepsine yedek düşer, bu zarar vermez.

## 3. Yedek durumu görünürlüğü tasarımı

Şu an `silent_backup()` ve `backup_now()` her hatayı sessizce yutuyor
(`except Exception: pass`). Bu davranış **korunur** (uygulama başlangıcını
bir yedek hatası yüzünden kesmemeli — offline-first ilkesiyle uyumlu), ama
en azından son deneme sonucu bir **durum dosyasına** yazılır ve UI'da
okunabilir hale gelir.

**Durum dosyası:** `data_dir() / "yedek_durumu.json"` (basit, bağımlılıksız,
DB şemasına dokunmaz — bir tablo eklemek bu iş için gereksiz karmaşıklık).
İçerik:

```json
{
  "son_deneme_zamani": "2026-09-18T14:30:05",
  "basarili": true,
  "hedef": "backup_2026-09-18_143005.db",
  "drive_klasoru_bulundu": true,
  "drive_yolu": "/Users/kurum/Library/CloudStorage/GoogleDrive-ornek@gmail.com/My Drive/LetaYonetim_Yedek",
  "hata_mesaji": null
}
```

`drive_klasoru_bulundu`: `_google_drive_candidates()` taraması en az bir
gerçek (var olan) klasör buldu mu — bulamadıysa yedek sadece yerel mirror'a
düşmüş demektir, bu ayrımı kullanıcıya göstermek önemli (bkz. Riskler).

Yazma işlemi `except: pass` içinde en dış katmanda kalır (durum dosyası
yazımı bile başarısız olursa uygulama akışı bundan etkilenmez), ama normal
akışta hem başarı hem başarısızlık durumu kaydedilir — yani mevcut "hatayı
tamamen yut" davranışı yerini "hatayı kullanıcıya popup ile gösterme, ama
en azından okunabilir bir iz bırak" davranışına bırakır.

**UI gösterimi:** `script/app_ui.py` içindeki `hakkinda_goster()`
fonksiyonu (satır ~8758, `messagebox.showinfo("Hakkında", ...)`) genişletilir.
Yeni bir küçük yardımcı fonksiyon `script/core/backup.py` içine eklenir:
`son_yedek_durumu_ozeti() -> str` — durum dosyasını okuyup insan-okunur tek
satır üretir, örn:

```
Son yedek: 18.09.2026 14:30 — Google Drive'a yazıldı
```
veya
```
Son yedek: 18.09.2026 14:30 — yerel yedek OK, Google Drive klasörü bulunamadı
```
veya
```
Son yedek: hiç denenmedi
```

`hakkinda_goster()` bu satırı mevcut mesaj metnine ekler (ayrı bir yeni
ekran açmaya gerek yok — mevcut "Hakkında" penceresi yeterli, minimum
değişiklik). Ayrıca "Ayarlar" ekranı zaten var olduğundan (satır ~8447
civarı, logo yönetimi sekmesi) oraya da aynı özet tek satır eklenebilir;
zorunlu değil, düşük maliyetli ekstra — plan.md aşamasında Batuhan karar
verir.

## 4. Fonksiyon/dosya değişiklik listesi

`script/core/backup.py`:
- `_google_drive_candidates()` — **değişir**: `sys.platform` dallanmasıyla
  ikiye ayrılır, alt yardımcılar eklenir:
  - `_macos_gdrive_candidates()` — **yeni**: `~/Library/CloudStorage/GoogleDrive-*/My Drive` glob taraması + eski istemci fallback.
  - `_windows_gdrive_candidates()` — **yeni**: `A:`–`Z:` sürücü harfi taraması (`\My Drive` var mı) + mevcut klasör-senkron adayları (korunur).
  - Linux/diğer: mevcut genel `home / "Google Drive"` fallback korunur (düşük öncelik, kurum bu platformda değil).
- `_backup_mirror_dirs()` — değişmez (zaten `_google_drive_candidates()`'i çağırıyor, alt katman değiştiği için otomatik faydalanır).
- `_write_backup_status()` — **yeni**: `yedek_durumu.json` dosyasını yazan fonksiyon, `backup_now()` ve `silent_backup()`'ın sonunda (hem başarı hem `except` bloklarında) çağrılır.
- `read_backup_status()` — **yeni**: durum dosyasını okuyup dict döner (yoksa `None`).
- `son_yedek_durumu_ozeti()` — **yeni**: `read_backup_status()`'u insan-okunur tek satıra çevirir (bkz. madde 3).
- `backup_now()` — **değişir**: sonunda `_write_backup_status(...)` çağrısı eklenir (başarı ve başarısızlık için).
- `silent_backup()` — **değişir**: aynı şekilde `_write_backup_status(...)` eklenir; mevcut sessiz `except: pass` davranışı korunur, sadece durum artık dosyaya düşüyor.
- `_write_recovery_info()` — **değişir**: `YEDEK_GERI_YUKLEME_BILGISI.txt` içeriğine, Batuhan'ın kurumun Drive yedeğini nasıl bulup `leta_data.db` olarak geri yükleyeceğine dair somut adımlar eklenir (hangi klasör deseni, hangi dosya adı deseni `backup_YYYY-MM-DD_HHMMSS.db`, macOS'ta `CloudStorage` yolu örneği, Windows'ta sürücü harfi örneği).

`script/app_ui.py`:
- `hakkinda_goster()` (satır ~8758) — **değişir**: `core.backup.son_yedek_durumu_ozeti()` çağrısı eklenir, mesaj metnine tek satır olarak eklenir.
- Ayarlar ekranı (satır ~8447 civarı) — **opsiyonel, plan.md'de netleşir**: aynı özet satırı orada da gösterilebilir.

`script/core/__init__.py` (export layer, `main.py`'nin `from core import *`
yaptığı yer) — yeni fonksiyonlar (`son_yedek_durumu_ozeti` en azından)
dışa açılmalı; mevcut export listesi kontrol edilip gerekiyorsa eklenir.

## 5. Kapsam dışı

- Canlı/gerçek-zamanlı bulut veritabanı — reddedildi (intent'te net).
- Çift yönlü senkron.
- Otomatik conflict resolution.
- Google Drive dışında başka bir bulut sağlayıcı desteği (Dropbox, OneDrive vb.) — istenmedi, eklenmez.
- Yedek geri yükleme işleminin UI'dan tek tık otomatikleştirilmesi — şu an manuel (dosya kopyala) kalıyor, `YEDEK_GERI_YUKLEME_BILGISI.txt` metni netleştiriliyor ama bir "Geri Yükle" butonu bu spec'te yok.
- Durum bilgisinin DB'ye (SQLite tablosu) yazılması — gereksiz karmaşıklık, düz JSON dosyası yeterli.

## 6. Riskler / Bilinen kısıtlar

- **Kurumda Google Drive for Desktop kurulu değilse:** tarama hiçbir aday
  klasör bulamaz, `drive_klasoru_bulundu: false` olarak işaretlenir, yedek
  yine de yerel mirror'lara (`data_dir()/Yedekler`, `~/LetaYonetim_BackupMirror`)
  düşmeye devam eder — veri kaybı riski yok, ama Drive'a gitmiyor. Bu durum
  "Hakkında" ekranındaki özet satırında açıkça görünür olacağı için Batuhan
  kurumla iletişime geçip Drive kurulumunu isteyebilir. İlk kurulum
  adımlarının otomasyonu (Drive'ı kurdurma) bu spec'in kapsamında değil —
  bu bir insan/IT adımı.
- **macOS izin/sandbox:** `~/Library/CloudStorage` normal bir kullanıcı
  klasörüdür, App Sandbox'a tabi olmayan (App Store dışı, doğrudan dağıtılan
  Python/PyInstaller) bir uygulama için ek bir macOS izni (Full Disk Access)
  **genellikle gerekmez** — bu klasör kullanıcının kendi home dizini
  altındadır, sistem koruması (TCC) sadece Masaüstü/Belgeler/İndirilenler
  gibi özel korumalı klasörler ve gerçekten sistem-seviye konumlar için
  devreye girer. Riski düşük görüyoruz ama kesin garanti için kurumun
  gerçek macOS'unda bir kez elle doğrulanması (ilk kurulumda tek seferlik
  manuel test) öneriliyor — bu otomasyona alınmaz, kontrol listesine not
  düşülür.
- **Birden fazla Google hesabı bağlıysa (macOS):** glob taraması hepsini
  bulur, yedek hepsine kopyalanır — zararsız ama gereksiz disk kullanımı
  yaratabilir; öncelik sırası eklenmiyor (basitlik), kabul edilebilir bir
  trade-off.
- **Sürücü harfi taraması (Windows):** 26 harfin `exists()` kontrolü ağdan
  bağlı sürücülerde (varsa) yavaş olabilir; pratikte Drive for Desktop yerel
  bir sanal sürücü olduğundan risk düşük, ölçülmedi — sorun çıkarsa
  taramayı yalnızca `C`'den sonraki harflerle sınırlamak yeterli olur.
- Durum dosyası (`yedek_durumu.json`) kendisi Drive'a senkronlanmaz (yerel
  `data_dir()` içinde kalır) — bu bilinçli bir tercih, sadece o makinenin
  kendi son-deneme durumunu gösterir, çapraz makine durum paylaşımı bu
  spec'in kapsamında değil.

## 7. Kaba efor tahmini

Tek geliştirici, AI destekli (Claude Code) çalışma için:

- `_google_drive_candidates()` platform ayrımı + macOS/Windows alt fonksiyonları: **~2-3 saat** (kod + gerçek makinede test imkânı sınırlı, macOS testi ancak kurumla koordineli yapılabilir — bu bir risk, aşağıda not).
- Durum dosyası yazma/okuma + `son_yedek_durumu_ozeti()`: **~1-2 saat**.
- `hakkinda_goster()` / Ayarlar UI entegrasyonu: **~1 saat**.
- `_write_recovery_info()` metin güncellemesi: **~30 dakika**.
- Manuel test (Windows'ta gerçek Drive for Desktop kurulu bir hesapla): **~1 saat**.
- macOS gerçek ortam testi: **elde macOS makinesi/kurum erişimi olmadan
  yapılamaz** — kod mantık olarak doğru yazılır ama gerçek doğrulama
  kurumun makinesinde ilk kurulumda yapılmalı; bu bir zaman tahmini değil,
  açık bir bağımlılık/risk.

**Toplam kod yazımı: yaklaşık yarım iş günü (~5-6 saat).** macOS gerçek
ortam doğrulaması ayrı, kurumla koordinasyona bağlı, bu tahmine dahil değil.

---

**Onay noktası:** Bu `spec.md` Batuhan tarafından onaylanıp commit'lenene
kadar `plan.md`/kod aşamasına geçilmez.

**Karar noktaları — Batuhan tarafından onaylandı:**

1. Durum dosyası formatı (JSON, `data_dir()` içinde): **onaylandı**.
2. Özet satırı: **sadece "Hakkında" ekranına** eklenir. Ayarlar ekranı bu
   spec'in kapsamı dışında kalır (ileride farklı bir amaçla kullanılabilir,
   ayrı bir konu).
3. Kurumun Google Drive for Desktop kurulumu: **şu an KURULU DEĞİL**. Kod,
   bu senaryoyu zaten (Bölüm 6, "Kurumda Google Drive for Desktop kurulu
   değilse") ele alıyor — tarama hiçbir aday bulamaz,
   `drive_klasoru_bulundu: false` olur, yedek yerel mirror'lara düşmeye
   devam eder, "Hakkında" ekranında bu durum açıkça görünür. **Operasyonel
   not (kod dışı):** Batuhan kuruma gittiğinde Google Drive for Desktop'ı
   kurup senkron klasörünü ayarlaması gerekecek — bu bir kurulum/IT adımı,
   bu spec'in veya sonraki plan.md'nin kapsamında değil, ayrıca takip
   edilmeli.
