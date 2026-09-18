# Intent: Çapraz Platform Veri Güvenliği ve Yedekleme
Author: Batuhan. Status: draft.

## Problem
Leta Takip, yerel bir SQLite dosyasını (`%LOCALAPPDATA%\LetaYonetim\leta_data.db`
Windows'ta, karşılığı macOS'ta `~/Library/Application Support/LetaYonetim/`)
tek makinede tutan bir masaüstü uygulaması. Yakında gerçek kullanım şu şekilde
olacak:

- **Kurum**, uygulamayı kendi **macOS** bilgisayarında, gerçek danışan/seans/
  ödeme verisiyle kullanacak.
- **Batuhan**, geliştirmeyi kendi **Windows** makinelerinde yapıyor ve
  kurumun bilgisayarında değil, kendi cihazlarında çalışacak — yani kurumun
  canlı verisine doğrudan, aynı makinede erişimi olmayacak.
- Şu an ne kullanıcıda (kurumda) ne Batuhan'da gerçek veri var — bu, mimariyi
  gerçek veri birikmeden önce doğru kurmak için doğru zaman.

Mevcut yedekleme kodu (`script/core/backup.py`) zaten bir "Google Drive
senkron klasörü" kavramı içeriyor (`_google_drive_candidates`,
`_backup_mirror_dirs`) ama:
1. Aday klasör yolları **Windows varsayımıyla** yazılmış
   (`Path.home() / "Google Drive" / ...` gibi göreli isimler) ve macOS'un
   güncel "Google Drive for Desktop" istemcisinin gerçek klasör yapısını
   (`~/Library/CloudStorage/GoogleDrive-<hesap>/My Drive/...`) kapsamıyor —
   kurumun macOS makinesinde bu mekanizma muhtemelen hiç çalışmayacak.
2. Yedekleme tek yönlü ve pasif (yerel DB'den Drive klasörüne kopya) — bu
   doğru ve korunacak bir tasarım kararı (aynı dosyaya iki makineden eşzamanlı
   yazma riski yok), ama Batuhan'ın bu yedeği ne zaman/nasıl fark edip
   indireceği/kullanacağı tanımlı değil.

## Proposed outcome
Batuhan'ın onayladığı yön: **yerel-öncelikli (offline-first) SQLite +
otomatik tek-yönlü Google Drive yedeği** — canlı/gerçek-zamanlı bulut
veritabanına geçiş YOK (bu, kapsam dışı bırakıldı; karmaşıklık/maliyet/
internet bağımlılığı artışı gerekçesiyle reddedildi).

Kapsam:
1. `_google_drive_candidates` (ve ilgili yol tespiti), **macOS'un güncel
   Google Drive for Desktop klasör yapısını** (`~/Library/CloudStorage/
   GoogleDrive-*/My Drive/...`) ve Windows'un güncel yollarını (mevcut
   adaylara ek olarak `Path.home() / "Google Drive"` gibi eski yapı yanında,
   güncel My Drive senkron istemcisinin gerçek varsayılan yolları) doğru
   tespit edecek şekilde güncellenir — platform bazlı (macOS/Windows) ayrı
   aday listeleri.
2. Uygulama **tamamen offline çalışabilir** kalır (bu zaten mevcut tasarım —
   local SQLite ana kaynak; bu intent bunu bozmaz, sadece yedek
   mekanizmasının güvenilirliğini artırır).
3. Yedek durumu kullanıcıya görünür kılınır: yedek başarılı/başarısız oldu mu,
   en son ne zaman Drive'a yazıldı — şu an `silent_backup()` tamamen sessiz
   (bkz. bilinen denetim bulgusu: DB bozuksa veya Drive klasörü
   bulunamazsa kullanıcıya hiçbir uyarı yok). En azından ayarlar/hakkında
   ekranında son yedek zamanı ve durumu gösterilir.
4. `YEDEK_GERI_YUKLEME_BILGISI.txt` (zaten var) Batuhan'ın kurumun Drive
   yedeğini bulup kendi makinesinde nasıl açacağını/inceleyeceğini net
   anlatacak şekilde güncellenir (hangi klasör, hangi dosya adı deseni,
   nasıl `leta_data.db` olarak geri yüklenir).

## Affected users and systems
- **Kullanıcı:** kurum (macOS, gerçek veri girer), Batuhan (Windows, ihtiyaç
  halinde Drive'daki yedeği indirip inceler/geliştirme yapar — canlı erişim
  değil, periyodik yedek erişimi).
- **Sistemler / dosyalar:**
  - `script/core/backup.py` — `_google_drive_candidates`,
    `_backup_mirror_dirs`, `_write_recovery_info`, `silent_backup`,
    `backup_now` platform-farkındalıklı hale getirilecek.
  - `script/core/paths.py` — `data_dir()` zaten platform bazlı (Windows/
    macOS/Linux ayrımı var), değişiklik beklenmiyor.
  - Muhtemelen yeni: yedek durumunu okuyup UI'da gösterecek küçük bir
    fonksiyon (`script/app_ui.py`'de bir "Hakkında"/"Ayarlar" ekranına
    eklenecek, spec.md'de kesinleşecek).

## Constraints
- **Canlı/gerçek-zamanlı bulut veritabanına GEÇİLMEYECEK** — bu, Batuhan
  tarafından açıkça reddedilen bir seçenekti (karmaşıklık, internet
  bağımlılığı, maliyet). Bu intent'in kapsamı sadece mevcut yerel-DB +
  pasif-yedek modelini çapraz platform çalışır/güvenilir hale getirmek.
  Gelecekte gerçek zamanlı senkron istenirse bu **ayrı bir intent** olur.
  Uygulama **offline-first** kalmalı: internet kesildiğinde günlük
  kullanım (seans/ödeme kaydı) durmamalı, sadece yedek adımı ertelenir.
- Yedekleme servisi: **Google Drive** (kullanıcı tercihi). Kurumun zaten bir
  Google Drive for Desktop kurulumu olduğu varsayılıyor — bu varsayım
  spec.md aşamasında teyit edilmeli (kurumda Drive kurulu değilse, ilk
  kurulum adımı da tanımlanmalı).
  Bu proje şu an playbook ile bootstrap edilmiş durumda ama henüz git
  deposu yok (bu makinede `git` kurulu değil) — commit noktaları fiilen
  bekletiliyor; bu ayrı bir konu, bu intent'i engellemiyor.
- Henüz gerçek veri yok (ne kurumda ne Batuhan'da) — bu, riski düşük
  kılıyor: yanlış bir tasarım kararı şimdi düzeltilirse veri kaybı riski
  yok. Ama karar, gerçek veri girilmeden ÖNCE netleşmeli.

## Open questions
(yok — temel yön Batuhan tarafından onaylandı: yerel-öncelikli + offline
çalışabilir + Google Drive tek-yönlü yedek. Kurumun Drive hesabı/kurulumu
detayları spec.md aşamasında netleşecek.)

---
**Dosya adı kuralı:** `intent/YYYY-MM-DD-kisa-slug.md`
(ASCII, küçük harf, tire ile ayrılmış)
**Onay noktası:** Bu dosyayı Claude yazar, kullanıcı commit'ler.
