# Spec: P0-A — Para Formatı, Sessiz Hata ve Yol Düzeltmeleri

Kaynak: `intent/2026-09-18-p0-finansal-veri-butunlugu.md` (Parça A), onaylandı.
Durum: taslak — Batuhan onayı bekliyor.

Bu spec, P0 paketinin **düşük riskli, mekanik** parçasını kapsar (madde
1, 3, 4, 5). Parça B (`records`/`seans_takvimi` konsolidasyonu, madde 2/10)
ayrı bir spec'te (`spec-p0b-...`), software-architect tarafından ele alınıyor.

## 1. `format_money` / `parse_money` tutarsızlığı (madde 1)

**Doğrulanmış gerçek bug (kod tabanında somut örnekler bulundu):**
`app_ui.py:2624` ve `app_ui.py:3045` bir Entry widget'ını
`ent.insert(0, format_money(deger))` ile dolduruyor, sonra aynı Entry'nin
`.get()` değeri `parse_money(...)` ile geri okunuyor. Şu an:
- `format_money` Python'ın varsayılan `{:,.2f}` biçimini kullanıyor →
  `1234.56` → `"1,234.56 ₺"` (virgül=binlik, nokta=ondalık — İngilizce format).
- `parse_money` Türkçe format varsayıyor (nokta=binlik, virgül=ondalık) →
  bu string'i geri okurken `.` siler, `,`→`.` çevirir → **1.23456** döner
  (1234.56 yerine, ~1000 kat küçük).

**Kök neden:** `parse_money` içindeki `.replace("₺","").replace(".","").replace(",",".")`
mantığı açıkça Türkçe format için yazılmış (₺ sembolü, nokta/virgül takas
sırası), ama `format_money` bununla hiç eşleşmiyor — muhtemelen bir gözden
kaçırma, bilinçli bir tasarım kararı değil.

**Düzeltme:** `format_money`'i Türkçe format üretecek şekilde değiştir
(nokta=binlik, virgül=ondalık — `parse_money`'nin zaten beklediği format):

```python
def format_money(val) -> str:
    try:
        num = float(val)
        s = f"{num:,.2f}"          # ara adım: "1,234.56" (İngilizce)
        s = s.replace(",", "§").replace(".", ",").replace("§", ".")
        return f"{s} ₺"             # "1.234,56 ₺"
    except Exception:
        return "0,00 ₺"             # hata mesajı da tutarlı Türkçe format
```

Bu değişiklik **görünüm** değiştirir (tüm uygulamada tutarlar artık
"1.234,56 ₺" şeklinde görünür, önceden "1,234.56 ₺" idi) ama **hesaplama
mantığını değiştirmez** — `format_money` sadece gösterim için kullanılıyor,
DB'ye hiçbir yerde doğrudan yazılmıyor (DB'ye yazılan değerler ham
`float`'lar, `format_money`'den geçmiyor). `parse_money` değişmiyor —
zaten doğru formatı bekliyordu, sorun `format_money` tarafındaydı.

**Regresyon riski:** `format_money` çağrıldığı ~100+ yerde artık farklı bir
string dönecek. Bu, sadece görsel bir formatlama değişikliği (ekranda
görünen metin), UI testleri/manuel doğrulama bunu göz önünde bulundurmalı
(plan.md'de: birkaç ekranda tutarların "1.234,56 ₺" formatında göründüğü
teyit edilecek).

## 2. `hesapla_personel_ucreti` sessiz %40 fallback (madde 3)

`core/money.py:31-46` — `float(kural.get("tutar") or 0.0)` veya
`float(kural.get("oran") or 0.0)` başarısız olursa (config'te yanlış tipte
bir değer varsa, örn. `"tutar": "2500 TL"` string), dış `except Exception`
sessizce `%40` hesaplamasına düşüyor.

**Düzeltme:** Davranışı DEĞİŞTİRMİYORUZ (yine %40'a düşsün — bu, hiç ücret
hesaplamamaktan daha güvenli bir fallback), ama artık **loglanıyor**:

```python
def hesapla_personel_ucreti(personel_adi: str, seans_ucreti: float) -> float:
    try:
        from .env import PERSONEL_UCRET_KURALLARI
        ad = (personel_adi or "").strip()
        kural = PERSONEL_UCRET_KURALLARI.get(
            ad, PERSONEL_UCRET_KURALLARI.get("_default", {"tip": "yuzde", "oran": 40.0}),
        )
        tip = (kural.get("tip") or "").strip().lower()
        if tip == "sabit":
            return float(kural.get("tutar") or 0.0)
        if tip == "yuzde":
            oran = float(kural.get("oran") or 0.0)
            return (float(seans_ucreti or 0.0) * oran) / 100.0
        return (float(seans_ucreti or 0.0) * 40.0) / 100.0
    except Exception as e:
        from .logging_utils import log_exception
        log_exception(f"hesapla_personel_ucreti_fallback[{personel_adi}]", e)
        return (float(seans_ucreti or 0.0) * 40.0) / 100.0
```

Böylece config hatası artık `leta_error.log`'da görünür oluyor — kullanıcı
akışı kesilmiyor (popup yok), ama artık iz bırakıyor.

## 3. Kritik `except: pass` noktalarında görünürlük (madde 4)

**Kapsam dışı (açıkça sınırlanıyor):** Kod tabanındaki ~230+ `except:
pass` örneğinin TAMAMINI düzeltmek bu spec'in kapsamında DEĞİL — bu hem
çok geniş hem de çoğu kozmetik/format normalizasyonu için zararsız. Sadece
**finansal/veri bütünlüğünü doğrudan etkileyen, önceki denetimde işaretli**
noktalar hedefleniyor:

- Borç haritası hesaplama (`app_ui.py` ~6910-6919 civarı — satır numarası
  bu oturumdaki eklemelerle kaymış olabilir, plan.md'de tekrar bulunacak).
- Veli yakınlık derecesi sorgusu (~6957-6974 civarı) — bakiye hesaplamasını
  etkileyen kısım.
- `backup.py:_db_integrity_ok` sonrası akış: `silent_backup()` artık durum
  dosyasına yazıyor (bu oturumda eklendi), ama `main.py`'deki genel akış
  (DB bozuksa `init_db()`/`migrate_database_data()` yine de çalışıyor) hâlâ
  kullanıcıya hiçbir şey göstermiyor. **Düzeltme:** `main.py`'ye, DB
  integrity kontrolü başarısızsa (backup modülündeki aynı kontrol
  tekrar kullanılarak) `log_exception` + tek seferlik, uygulamayı
  durdurmayan bir `messagebox.showwarning` eklenir ("Veritabanı bütünlük
  kontrolü başarısız, yedeklerinizi kontrol edin") — offline-first ilkesi
  korunur (uygulama yine de açılır), ama artık kullanıcı bilgilendirilir.

Yukarıdaki 2-3 nokta dışında hiçbir `except: pass` bloğuna dokunulmuyor.

## 4. `assets_dir()` çift yol hatası (madde 5)

`core/paths.py:52-59` — `app_dir()` zaten `.../script` döndürüyor
(`Path(__file__).resolve().parent.parent` → `core/paths.py`'den iki üst
klasör), bu yüzden ilk aday `app_dir() / "script" / "assets"` aslında
`.../script/script/assets` oluyor — hiç var olmayan bir yol.

**Ek bulgu (doğrulandı):** `script/assets/` klasörü şu an hiç yok ve
gerçek kullanım kılavuzu `KULLANIM_KILAVUZU.md` (not `.txt`) proje
KÖKÜNDE duruyor, `script/` altında bile değil. Yani sadece yol düzeltmek
yetmiyor — dosyanın kendisi de doğru yerde/formatta değil.

**Düzeltme (küçük kapsam, "bulunamadı" logunu gerçekten çözüyor):**
1. `assets_dir()`'deki hatalı ilk aday (`app_dir() / "script" / "assets"`)
   kaldırılır, sadece `app_dir() / "assets"` (= `script/assets`) kalır.
2. `script/assets/` klasörü oluşturulur, proje kökündeki
   `KULLANIM_KILAVUZU.md` içeriği `script/assets/KULLANIM_KILAVUZU.txt`
   olarak kopyalanır (basit metin kopyası — Markdown biçimlendirmesi
   `messagebox`/basit görüntüleyicide zaten düz metin gibi görünüyor,
   dönüştürme gerekmez).
3. Böylece `ensure_user_guide_present()` artık dosyayı gerçekten bulur,
   "Kullanıcı rehberi bulunamadı" log satırı bir daha çıkmaz.

**Kapsam dışı:** kılavuzu uygulama içinden açan bir buton/ekran eklemek
(mevcut davranış: sadece varlık kontrolü yapılıyor, açan bir UI yok) — bu
ayrı bir özellik, bu spec'te yok.

## 5. Fonksiyon / dosya değişiklik listesi

- `script/core/money.py` — `format_money` (değişir).
- `script/core/paths.py` — `assets_dir` (değişir).
- `script/core/money.py` — `hesapla_personel_ucreti` (değişir, `log_exception` eklenir).
- `script/main.py` — DB integrity kontrolü sonrası kullanıcı uyarısı eklenir.
- `script/app_ui.py` — sadece Bölüm 3'te sayılan 2 nokta (borç haritası,
  veli yakınlık sorgusu) `except: pass` yerine `except Exception as e:
  log_exception(...)` olur (davranış aynı kalır, sadece loglanır).
- Yeni: `script/assets/KULLANIM_KILAVUZU.txt` (kök `.md` dosyasının kopyası).

## 6. Kapsam dışı

- `records`/`seans_takvimi` konsolidasyonu — Parça B'de (ayrı spec).
- ~230 `except: pass` örneğinin tamamı — sadece Bölüm 3'teki 2-3 nokta.
- Otomatik test yazımı — P1'de ayrı ele alınacak (ama bu spec'in manuel
  doğrulama checklist'i, para formatı değişikliği için titiz olacak).
- Kullanım kılavuzunu uygulama içinden açan bir ekran/buton.

## 7. Riskler / Bilinen kısıtlar

- **`format_money` çıktısının görsel değişimi** en büyük risk — DB'ye hiçbir
  etkisi yok ama ekranda "1,234.56 ₺" yerine "1.234,56 ₺" görülecek; bu
  kasıtlı ve doğru (Türkçe format artık her yerde tutarlı), ama Batuhan
  bunu "hata" sanmasın diye burada açıkça not ediliyor.
- `hesapla_personel_ucreti` davranışı DEĞİŞMİYOR (yine %40 fallback), sadece
  görünürlük ekleniyor — config hatası hâlâ sessizce yanlış hesaplar, ama
  artık log'da görülebilir. Gerçek bir config-doğrulama (ör. uygulama
  açılışında `PERSONEL_UCRET_KURALLARI`'nı doğrula) bu spec'in kapsamında
  DEĞİL — istenirse ayrı bir küçük intent olabilir.

## 8. Kaba efor tahmini

| İş | Tahmini süre |
|---|---|
| `format_money`/`parse_money` düzeltme + round-trip doğrulama | 1-1.5 saat |
| `hesapla_personel_ucreti` loglama | 15-20 dakika |
| `main.py` DB integrity uyarısı + 2 nokta `except` loglama | 45 dakika-1 saat |
| `assets_dir()` düzeltme + dosya kopyalama | 20-30 dakika |
| Manuel doğrulama (round-trip senaryosu dahil, checklist aşağıda) | 1-1.5 saat |
| **Toplam** | **≈ 3.5-5 saat** |

---

**Onay noktası:** Bu dosyayı Claude yazar, Batuhan okur / düzeltir / commit'ler.
Kod yazımı ancak bu dosya commit'lendikten ve `plan-p0a-...` onaylandıktan
sonra başlar.
