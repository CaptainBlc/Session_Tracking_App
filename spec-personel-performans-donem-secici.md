# Spec: Personel Performans — Günlük / Aylık / Yıllık Dönem Seçici

Kaynak intent: `intent/2026-09-18-personel-performans-donem-secici.md`
Durum: taslak — Batuhan onayı bekliyor.

## 1. Özellik özeti

Mevcut "📈 Aylık Özet / Performans" sekmesine (uygulandı, `spec.md` /
`plan.md` — artık `spec-personel-performans-takibi.md` olarak arşivlendi)
bir **Dönem tipi** seçici eklenir: **Günlük / Aylık / Yıllık**. Seçilen
tipe göre aynı kartlar (Verim, Kazanç) ve aynı 3 satırlık karşılaştırma
tablosu, farklı bir zaman biriminde gruplanmış veriyle doldurulur.
Varsayılan davranış (uygulama ilk açıldığında) **Aylık** olarak kalır —
mevcut kullanıcı deneyiminde regresyon olmaz.

## 2. Veri modeli / sorgu tasarımı

Yeni tablo yok. Mevcut `personel_ucret_takibi` tablosu üzerinde `strftime`
formatı dönem tipine göre parametreleştirilir:

| Dönem tipi | strftime formatı | Pencere (3'lü karşılaştırma) |
|---|---|---|
| Günlük | `%Y-%m-%d` | seçili gün + önceki 2 takvim günü |
| Aylık | `%Y-%m` (mevcut) | seçili ay + önceki 2 ay |
| Yıllık | `%Y` | seçili yıl + önceki 2 yıl |

### Genelleştirilmiş fonksiyonlar (mevcutların yerini alır)

- **`_personel_performans_donem_format(donem_tipi: str) -> str`** — yukarıdaki
  tablodaki strftime formatını döndürür.
- **`_donem_listesi_getir(self, donem_tipi: str) -> list[str]`** — eski
  `_ay_listesi_getir`'in yerini alır: `SELECT DISTINCT strftime(<format>,
  tarih) FROM personel_ucret_takibi ... ORDER BY 1 DESC`.
- **`_personel_performans_pencere_hesapla(donem_tipi: str, donem: str) ->
  list[str]`** — 3'lü pencereyi hesaplar:
  - `gunluk`: `datetime.date.fromisoformat(donem)` üzerinden `timedelta(days=1)`
    ile geriye 2 gün.
  - `aylik`: mevcut ay aritmetiği (ay/yıl taşması dahil, zaten uygulanmış
    mantık aynen taşınır).
  - `yillik`: `int(donem)` üzerinden basit `-1`, `-2`.
  - Dönüş kronolojik sırada (en eski → seçili dönem), aylık akıştaki gibi.
- **`_personel_performans_hesapla(self, personel_adi: str, donem_tipi: str,
  donem: str) -> dict`** — mevcut fonksiyonun genelleştirilmiş hâli;
  SQL'deki `strftime('%Y-%m', ...)` yerine `strftime(<format>, ...)`
  kullanılır, pencere `_personel_performans_pencere_hesapla`'dan gelir.
  İptal edilmiş seans hariç tutma mantığı (`st.durum != 'iptal'`) aynen
  korunur — dönem tipinden bağımsız.

Bu üç fonksiyon eski `_ay_listesi_getir` / (ay-özel pencere hesaplama) yerini
alır; **mevcut aylık davranış, `donem_tipi="aylik"` çağrısıyla birebir aynı
sonucu üretmeli** (regresyon testi bunu doğrulayacak).

## 3. UI tasarımı

Filtre satırına, Personel/Ay seçicilerinin **üstüne** bir dönem tipi
seçici eklenir — mevcut kod tabanında zaten kullanılan bir kalıp:
Kasa Defteri raporundaki (`app_ui.py:5242-5245`) `ttk.Radiobutton` grubu
ile aynı stil:

```
Dönem: ( ) 📅 Günlük   (•) 📆 Aylık   ( ) 📊 Yıllık
```

- Radiobutton değişince (`command=...`): "Dönem" combobox'ının değerleri
  `_donem_listesi_getir(yeni_tip)` ile yeniden doldurulur, en son değer
  varsayılan seçilir, `_personel_performans_yukle` tetiklenir.
- "Personel", "Ay" etiketi artık dönem tipine göre **"Gün" / "Ay" / "Yıl"**
  olarak değişir (statik `ttk.Label` metni `config(text=...)` ile
  güncellenir — mevcut kodda bu tür dinamik metin güncellemesi zaten var,
  ör. özet etiketleri; risksiz).
- Karşılaştırma tablosunun ilk kolon başlığı da dönem tipine göre
  "Gün" / "Ay" / "Yıl" olur (`tree.heading(...)`).
- Değişim vurgu metni dönem tipine göre "Önceki güne göre" / "Önceki aya
  göre" / "Önceki yıla göre" olarak değişir.
- Kart tasarımı (Verim / Kazanç), renk kuralları (`success`/`danger`),
  "veri yok" / "0" gösterimi, seçili satır vurgusu — **hiçbiri değişmez**,
  sadece veri kaynağı ve etiketler dönem tipine göre parametreleşir.

## 4. Fonksiyon / dosya değişiklik listesi

`script/app_ui.py` içinde:

- **Kaldırılacak/değişecek:** `_ay_listesi_getir` → yerini
  `_donem_listesi_getir(self, donem_tipi)` alır (çağrı yerleri güncellenir).
- **Değişecek:** `_personel_performans_hesapla` — `ay: str` parametresi
  `donem_tipi: str, donem: str` olur; iç mantık `strftime` formatını
  parametreden okur.
- **Yeni:** `_personel_performans_donem_format(donem_tipi)`.
- **Yeni:** `_personel_performans_pencere_hesapla(donem_tipi, donem)`.
- **Değişecek:** `_build_personel_performans_sekmesi` — dönem tipi
  radiobutton grubu eklenir, mevcut "Ay" combobox'ı genel "Dönem"
  combobox'ına dönüşür (widget aynı kalır, sadece besleme kaynağı/etiketi
  değişir).
- **Değişecek:** `_personel_performans_yukle` — seçili `donem_tipi`'ni
  radiobutton'dan okuyup `_personel_performans_hesapla`'ya iletir.
- **Değişecek:** `_personel_performans_render` — kolon başlığı ve
  "önceki X'e göre" metni dönem tipine göre parametrelenir (küçük bir
  `donem_tipi_etiket = {"gunluk": "gün", "aylik": "ay", "yillik": "yıl"}`
  sözlüğü ile).

`script/core/*`: değişiklik yok.

## 5. Kapsam dışı

- Haftalık dönem tipi (intent'te istenmedi — sadece Günlük/Aylık/Yıllık).
- Dönemler arası özel tarih aralığı seçimi (ör. "01.03-15.03").
- Grafik/chart görselleştirme.
- 3'ten fazla dönemlik trend.

## 6. Riskler / Bilinen Kısıtlar

- **Regresyon riski:** mevcut aylık görünüm zaten üretimde çalışır durumda
  (test edildi). Genelleştirme sırasında `donem_tipi="aylik"` davranışının
  birebir korunması kritik — plan.md'nin doğrulama checklist'i bunu ilk
  madde olarak içermeli.
- Günlük dönemde, eğer kurumda o gün hiç seans yoksa (çoğu gün için beklenen
  durum — kurumlar her gün çalışmaz), pencere çoğunlukla 0 değerli satırlar
  gösterecektir; bu "hata" değil, beklenen/doğru davranıştır (aylık
  görünümdeki "veri olmayan ay" senaryosuyla aynı ilke).
- Salt-okunur rapor katmanı olmaya devam ediyor — yeni bir veri yazma riski
  eklenmiyor.

## 7. Kaba efor tahmini

Mevcut kodun genelleştirilmesi (yeniden yazım değil) — küçük/orta.

| İş | Tahmini süre |
|---|---|
| Pencere hesaplama + format genelleştirme (veri katmanı) | 1-1.5 saat |
| UI: dönem tipi radiobutton + dinamik etiketler | 1-1.5 saat |
| Render fonksiyonunun dönem-farkındalıklı hale getirilmesi | 0.5-1 saat |
| Regresyon testi (aylık davranış birebir korunuyor mu) + günlük/yıllık manuel test | 1-1.5 saat |
| **Toplam** | **≈ 3.5-5.5 saat** |

---

**Onay noktası:** Bu dosyayı Claude yazar, Batuhan okur / düzeltir / commit'ler.
Kod yazımı ancak bu dosya commit'lendikten ve `plan-personel-performans-donem-secici.md`
onaylandıktan sonra başlar.
