# Plan: P0-A — Para Formatı, Sessiz Hata ve Yol Düzeltmeleri

Kaynak: `spec/p0a-para-ve-hata-duzeltmeleri.md`.
Status: draft — Batuhan onayı bekliyor. Onaylanıp commit'lenmeden kod
aşamasına geçilmez.

Bu plan spec'in 4 bağımsız düzeltmesini (Bölüm 1-4) ve dosya listesini
(Bölüm 5) somut adımlara döküyor. Dört düzeltme birbirinden bağımsız
dosyalarda/fonksiyonlarda — aralarında bağımlılık yok, aşağıdaki sıra
sadece risk/efor artan şekilde düzenlendi (küçük & izole önce, UI'ye
dokunan en sona).

## 1. Uygulama sırası

### Adım 1 — `format_money` TR format düzeltmesi (~1-1.5 saat)

- Dosya: `script/core/money.py`
- Spec Bölüm 1'deki kod aynen uygulanır:
  ```python
  def format_money(val) -> str:
      try:
          num = float(val)
          s = f"{num:,.2f}"
          s = s.replace(",", "§").replace(".", ",").replace("§", ".")
          return f"{s} ₺"
      except Exception:
          return "0,00 ₺"
  ```
- `parse_money` **değişmez**.
- Bu adımdan hemen sonra, kod yazımının bir parçası olarak, scratchpad'e
  küçük bir round-trip doğrulama scripti yazılır (bkz. Bölüm 2, madde 1) —
  "düzeltme doğru mu" sorusu koda geçmeden değil, geçtikten hemen sonra
  kapatılır.

### Adım 2 — `hesapla_personel_ucreti` loglama (~15-20 dakika)

- Dosya: `script/core/money.py`
- Spec Bölüm 2'deki kod aynen uygulanır: `except Exception as e:` bloğuna
  `from .logging_utils import log_exception` + `log_exception(f"hesapla_personel_ucreti_fallback[{personel_adi}]", e)`
  eklenir, dönüş değeri (%40 fallback) **değişmez**.

### Adım 3 — `assets_dir()` düzeltmesi + kılavuz dosyası (~20-30 dakika)

- Dosya: `script/core/paths.py`
- `assets_dir()` içindeki hatalı `app_dir() / "script" / "assets"` adayı
  kaldırılır, sadece `app_dir() / "assets"` kalır.
- `script/assets/` klasörü oluşturulur.
- Proje kökündeki `KULLANIM_KILAVUZU.md` içeriği `script/assets/KULLANIM_KILAVUZU.txt`
  olarak kopyalanır (düz metin kopya, biçim dönüşümü yok).

### Adım 4 — `main.py` DB integrity uyarısı (~45 dakika-1 saat)

- Dosya: `script/main.py`
- `from tkinter import messagebox` ve `from core.backup import _db_integrity_ok`
  importları eklenir (ikisi de şu an dosyada yok; `_db_integrity_ok` alt
  çizgiyle başladığı için `from core import *` onu otomatik getirmiyor,
  doğrudan import gerekiyor).
- `silent_backup()` çağrısından hemen sonra, `init_db()`'den önce:
  ```python
  try:
      dbp = db_path()
      if dbp.exists() and not _db_integrity_ok(dbp):
          log_exception("main_db_integrity_check", Exception("Veritabani butunluk kontrolu basarisiz"))
          messagebox.showwarning(
              "Veritabanı Uyarısı",
              "Veritabanı bütünlük kontrolü başarısız oldu. Uygulama yine de "
              "açılacak, ancak yedeklerinizi kontrol etmenizi öneririz "
              "(Hakkında ekranından son yedek durumuna bakabilirsiniz).",
          )
  except Exception as e:
      log_exception("main_db_integrity_check_wrapper", e)
  ```
- `dbp.exists()` koruması bilinçli: DB dosyası henüz hiç yoksa (ilk açılış)
  `_db_integrity_ok` yine de bir bağlantı denemesi yapar ve yanlış pozitif
  "bozuk" uyarısı verebilir — `silent_backup()` içindeki aynı kalıp burada
  da tekrarlanıyor.
- Offline-first ilkesi korunur: uygulama hiçbir koşulda burada durmaz,
  sadece tek seferlik bir uyarı popup'ı gösterir.

### Adım 5 — `app_ui.py`'de 2 nokta `except: pass` → loglama (~30-45 dakika)

- Dosya: `script/app_ui.py`, fonksiyon: `_tum_danisanlari_listele`
  (spec'teki tahmini satırlar bu oturumdaki eklemelerle kaymıştı, güncel
  konumlar bu plan yazılırken doğrulandı):
  - **Borç haritası** — satır 7268-7277: `records` tablosundan
    `kalan_borc` toplamı çekilirken `except Exception: pass`.
    `except Exception as e: log_exception("_tum_danisanlari_listele_borc_map", e)`
    olur.
  - **Veli yakınlık derecesi** — satır 7313-7332: `ogrenci_aile_bilgileri`
    sorgusu çevresindeki `except Exception: pass`.
    `except Exception as e: log_exception("_tum_danisanlari_listele_veli_yakinlik", e)`
    olur.
- Davranış aynı kalır (hata yutulmaya devam eder, akış kesilmez) — sadece
  artık `leta_error.log`'da iz bırakır.
- Bu iki nokta dışında `app_ui.py`'deki başka hiçbir `except` bloğuna
  dokunulmaz (spec Bölüm 6, kapsam dışı listesi).

**Toplam tahmini kod yazım süresi: ≈ 2-3 saat** (spec Bölüm 8'deki
"3.5-5 saat" tahmininin doğrulama kısmı Bölüm 2'ye ayrıldı).

## 2. Manuel doğrulama checklist'i

Otomatik test yok (spec Bölüm 6, kapsam dışı) — bu yüzden özellikle para
formatı değişikliği için round-trip senaryosu titiz tutuluyor.

1. [ ] **Round-trip regresyon testi** (en kritik madde): scratchpad'de bir
   script, `format_money(1234.56)` çağrısının `"1.234,56 ₺"` döndürdüğünü,
   ardından bu string'in `ent.get()` benzeri bir okumadan sonra
   `parse_money("1.234,56 ₺")`'ye verildiğinde tekrar `1234.56`'ya
   (± ondalık hata payı) döndüğünü doğrular. Birkaç ek değer de denenir:
   `0`, negatif olmayan küçük değer (`5.0`), büyük değer (`123456.78`).
2. [ ] `format_money` çağıran gerçek ekranlardan en az 2-3 tanesi
   (`app_ui.py:2624` ve `:3045` çevresindeki Entry alanları + Personel
   Ücret Takibi / Kasa Defteri özet kartları) uygulama açık şekilde elle
   gezilir, tutarların artık `"1.234,56 ₺"` formatında (nokta=binlik,
   virgül=ondalık) göründüğü teyit edilir.
3. [ ] `hesapla_personel_ucreti`: `PERSONEL_UCRET_KURALLARI`'na geçici
   olarak bozuk bir değer (`"tutar": "abc"`) verilip fonksiyon çağrılır;
   dönüş değerinin hâlâ %40 fallback'e eşit olduğu VE `leta_error.log`'a
   `hesapla_personel_ucreti_fallback[...]` satırının düştüğü doğrulanır;
   test sonrası config eski haline döndürülür.
4. [ ] `assets_dir()`: uygulama açılır, log dosyasında daha önce her
   açılışta görülen "Kullanıcı rehberi bulunamadı" satırının artık
   ÇIKMADIĞI doğrulanır; `script/assets/KULLANIM_KILAVUZU.txt` dosyasının
   var ve okunabilir olduğu kontrol edilir.
5. [ ] `main.py` DB integrity uyarısı: geçerli bir DB ile normal açılışta
   hiçbir popup çıkmadığı doğrulanır (yanlış pozitif yok); ardından bir
   test kopyası DB dosyası bilerek bozulur (ör. birkaç byte üzerine
   rastgele veri yazılır), uygulama o kopya ile açılır, uyarı popup'ının
   çıktığı VE uygulamanın yine de açılmaya devam ettiği (durmadığı)
   doğrulanır; test DB'si sonrasında silinir, gerçek DB'ye dokunulmaz.
6. [ ] `_tum_danisanlari_listele` iki nokta: "Tüm Danışanlar" ekranı normal
   veriyle açılır, borç bakiyelerinin ve veli yakınlık derecelerinin
   önceki davranışla birebir aynı şekilde (regresyon yok) göründüğü
   doğrulanır. İsteğe bağlı ek doğrulama: `ogrenci_aile_bilgileri`
   tablosuna geçici olarak geçersiz bir satır eklenip except bloğunun
   tetiklendiği ve artık log'a düştüğü gözlemlenebilir (opsiyonel, çekirdek
   kriter değil).

## 3. Commit noktası

- Bu `plan.md` dosyası commit edilmez — Batuhan okur, onaylar, kendisi
  commit'ler.
- Kod aşamasına bu plan VE `spec/p0a-para-ve-hata-duzeltmeleri.md`
  onaylanıp commit'lenmeden geçilmez.
- Kod tamamlandıktan sonra da commit'i Batuhan atar, Claude atmaz.

## 4. Uygulama sırasında bulunan ek düzeltme (plan onayından sonra)

Adım 5'in doğrulaması sırasında (gerçek `_tum_danisanlari_listele`
fonksiyonu seed veriyle çalıştırılarak), veli yakınlık sorgusunun
`except: pass` tarafından gizlenen **kalıcı bir hata** olduğu ortaya
çıktı: `ogrenci_aile_bilgileri` tablosundaki gerçek kolon adı `yakinlik`,
ama sorgu var olmayan `veli_yakinlik_derecesi` kolonunu arıyordu — yani bu
except sadece nadiren değil, veli_adi'i olan her satırda tetikleniyordu.
Loglama eklenince bu, her ekran açılışında log dosyasına traceback
yağmasına yol açacaktı.

Batuhan'a soruldu, **kolon adını da düzeltme** onaylandı (spec'in "davranış
değişmez" sınırının hafif dışında, ama izole/düşük riskli tek satırlık bir
düzeltme): `app_ui.py`'de sorgu `SELECT veli_yakinlik_derecesi` →
`SELECT yakinlik` olarak değiştirildi. Seed veriyle doğrulandı: artık
"Test Veli (Anne)" gibi doğru yakınlık etiketi görünüyor, except bloğu
tetiklenmiyor.

**Not:** Aynı `veli_yakinlik_derecesi` (ve `guncelleme_tarihi`) kolon adı
uyuşmazlığı `app_ui.py`'de başka 3 yerde de var (~6901, ~6980, ~7021 —
"Veli Bilgileri" ekleme/düzenleme akışı) — bunlar bu planın kapsamı
dışında, dokunulmadı. Ayrı bir küçük intent olarak ele alınmalı.

---

**Onay noktası:** Bu `plan.md` Batuhan tarafından onaylanıp commit'lenene
kadar kod aşamasına geçilmez.
