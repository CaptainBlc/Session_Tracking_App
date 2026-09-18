# Spec: Personel Aylık Performans ve Kazanç Takibi

Kaynak intent: `intent/2026-09-18-personel-performans-takibi.md`
Durum: taslak — Batuhan onayı bekliyor.

## 1. Özellik özeti

`Ücret Takipi` sekmesindeki mevcut "Personel Ücret Takibi" sayfasına (bkz.
`script/app_ui.py:_build_personel_ucret_takibi_page`, satır ~3765), ham
seans-bazlı listenin **yanına** ikinci bir alt sekme eklenir: **"📈 Aylık
Özet / Performans"**. Bu sekme salt-okunur bir raporlama katmanıdır; hiçbir
yeni veri yazmaz, mevcut `personel_ucret_takibi` tablosunu aggregate ederek
okur. Kullanıcı personel (veya "Tümü") ve ay seçer; seçilen ay için seans
sayısı, brüt ciro, net kurum kazancı gösterilir; son 3 ay yan yana
karşılaştırılır ve seçili ayın bir önceki aya göre fark/% değişimi vurgulanır.

Mevcut ham liste sayfası (`_personel_ucret_listele`) ve verisi değişmeden
kalır.

## 2. Veri modeli / sorgu tasarımı

**Yeni tablo gerekmiyor.** Mevcut `personel_ucret_takibi` tablosu
(`script/core/db.py` ~254-272) yeterli: her satır zaten bir seansa karşılık
gelen `tarih`, `seans_ucreti`, `personel_ucreti` içeriyor. `tarih` formatı
`YYYY-MM-DD` (bkz. `pipeline.py:_today()` ve seans kaydı akışı) — SQLite
`strftime('%Y-%m', tarih)` ile doğrudan uyumlu.

**Aggregasyon kuralı (intent'teki varsayım teyit edilecek):**
`odeme_durumu`'ndan bağımsız, o aya ait **tüm** seans kayıtları sayılır
(iptal edilmiş seanslar hariç — `seans_id` üzerinden `seans_takvimi.durum`
kontrolü, mevcut `_personel_ucret_listele`'deki `has_put_seans` /
`(put.seans_id IS NULL OR st.id IS NOT NULL)` desenine benzer şekilde). Bu,
"yapılan iş" performansını ölçer, tahsilatı değil. **Açık teyit noktası:**
Batuhan bu varsayımı onaylamalı — aksi halde `odeme_durumu != 'iptal'` gibi
ek bir filtre gerekebilir.

### Ana sorgu taslağı — aylık özet (tek personel veya tümü)

```sql
SELECT
    strftime('%Y-%m', put.tarih)               AS ay,
    COUNT(*)                                     AS seans_sayisi,
    COALESCE(SUM(put.seans_ucreti), 0)           AS brut_ciro,
    COALESCE(SUM(put.personel_ucreti), 0)        AS personel_payi_toplam,
    COALESCE(SUM(put.seans_ucreti - put.personel_ucreti), 0) AS net_kurum_kazanci
FROM personel_ucret_takibi put
LEFT JOIN seans_takvimi st ON st.id = put.seans_id
WHERE (put.seans_id IS NULL OR st.id IS NOT NULL)
  AND (st.durum IS NULL OR st.durum != 'iptal')
  -- personel filtresi (opsiyonel):
  AND (:personel_adi = '' OR put.personel_adi = :personel_adi)
  -- 3 aylık pencere: seçilen ay ve önceki 2 ay
  AND strftime('%Y-%m', put.tarih) IN (:ay0, :ay1, :ay2)
GROUP BY strftime('%Y-%m', put.tarih)
ORDER BY ay ASC
```

- `:ay0, :ay1, :ay2` Python tarafında `datetime`/`dateutil` ile hesaplanır
  (seçili ay ve ondan önceki 2 ay — kayıt olmayan aylar için satır
  dönmeyeceğinden, Python tarafında eksik aylar 0 ile doldurulur).
- "Tümü" personel seçiminde `personel_adi` filtresi uygulanmaz; sonuç kurum
  geneli toplamı olur.
- Personel dropdown'ı mevcut kalıpla aynı kaynaktan doldurulur:
  `SELECT therapist_name FROM settings WHERE is_active=1 ORDER BY
  therapist_name`.
- Fark/% hesaplama: `net_kurum_kazanci[secili_ay] - net_kurum_kazanci[onceki_ay]`
  ve `(fark / onceki_ay) * 100` (önceki ay 0 ise "—" gösterilir, bölme
  yapılmaz).

**Neden `hesapla_personel_ucreti` tekrar çağrılmıyor:** tablo satırındaki
`personel_ucreti` değeri, seans kaydedildiği anda geçerli olan ücret
kuralına göre zaten hesaplanıp saklanmış (`pipeline.py` ~359). Aggregasyon
bu **saklı** değeri toplar, kuralı yeniden uygulamaz — bu hem daha basit
hem de tarihsel doğruluğu korur (personel ücret kuralı ileride değişirse
geçmiş aylar yanlış yeniden hesaplanmaz). Bkz. Riskler bölümü.

## 3. UI tasarımı

`_build_personel_ucret_takibi_page` içindeki mevcut `page_personel` yapısı,
kendi içine bir iç `ttk.Notebook` alır (mevcut `nb_ucret` deseniyle aynı
kalıp — bkz. satır ~3672-3683):

- **İç sekme 1:** "📋 Ham Liste" — mevcut içerik olduğu gibi taşınır
  (bugünkü `_build_personel_ucret_takibi_page` gövdesi).
- **İç sekme 2 (YENİ):** "📈 Aylık Özet / Performans" —
  `_build_personel_performans_sekmesi(parent)` tarafından kurulur.

### Aylık Özet / Performans sekmesi bileşenleri

1. **Filtre satırı** (üstte, mevcut `filter_frame` deseniyle aynı hizada):
   - `Personel:` combobox — değerler `["Tümü"] + settings.therapist_name
     listesi`, varsayılan "Tümü" (mevcut personel combobox kaynağıyla aynı
     sorgu).
   - `Ay:` combobox — `YYYY-MM` formatında, veritabanında kayıt bulunan
     aylardan türetilir (`SELECT DISTINCT strftime('%Y-%m', tarih) FROM
     personel_ucret_takibi ORDER BY 1 DESC`), varsayılan en son ay.
   - `🔄 Yenile` / `Göster` butonu.

2. **Verim + Kazanç kartları** (yan yana, `ttk.Labelframe` ikilisi — mevcut
   `summary_frame` bootstyle="secondary" deseniyle tutarlı):
   - Sol kart "Verim": seans sayısı, brüt ciro (`format_money`).
   - Sağ kart "Kazanç": brüt ciro, personel payı toplamı, net kurum
     kazancı — üçü yan yana etiket olarak (mevcut `summary_labels` içindeki
     `ttk.Label(..., bootstyle=...)` deseniyle, ör. brüt=info, personel
     payı=warning, net=success).

3. **Değişim vurgusu** (kartların altında tek satır): "Önceki aya göre: +X
   seans (%Y), net kazançta +/- Z ₺ (%W)" — pozitifse yeşil (`bootstyle=
   "success"`), negatifse kırmızı (`bootstyle="danger"`) etiket rengi;
   önceki ay veri yoksa "Karşılaştırma için önceki ay verisi yok" gösterilir.

4. **3 Aylık Karşılaştırma Tablosu** (`ttk.Treeview`, mevcut `Strong.Treeview`
   stiliyle, sıralama düzeni `_personel_ucret_listele`'deki tag_configure
   / even-odd desenine benzer):
   - Kolonlar: `Ay | Seans Sayısı | Brüt Ciro | Personel Payı | Net Kurum
     Kazancı`.
   - 3 satır (eksik aylar 0 değerleriyle gösterilir, "veri yok" değil —
     kurumun o ay hiç seansı olmamış olabilir, bu meşru bir durum).
   - Seçili ay satırı `tag_configure("secili_ay", ...)` ile vurgulanır
     (ör. açık mavi arka plan).

Tüm bileşenler mevcut `ttk.Notebook` / `filter_frame` / `Treeview` +
`tag_configure` renklendirme kalıplarını takip eder; yeni bir tasarım dili
getirilmez.

## 4. Fonksiyon / dosya değişiklik listesi

`script/app_ui.py` içinde:

- **Değişecek:** `_build_personel_ucret_takibi_page(self, parent)` —
  gövdesi olduğu gibi kalır ama artık doğrudan `parent`'a değil, içine
  eklenen bir `ttk.Notebook`'un ilk sayfasına (`page_ham_liste`) render
  edilir; ikinci sayfa için `_build_personel_performans_sekmesi` çağrılır.
- **Yeni:** `_build_personel_performans_sekmesi(self, parent)` — filtre
  satırı, kartlar, karşılaştırma tablosu widget'larını kurar, ilk
  yüklemeyi tetikler.
- **Yeni:** `_personel_performans_hesapla(self, personel_adi: str, ay: str)
  -> dict` — SQL sorgusunu çalıştırır, 3 aylık pencere verisini
  `{ay: {seans_sayisi, brut_ciro, personel_payi, net_kazanc}}` şeklinde
  döndürür. Hata durumunda boş dict + `log_exception` (mevcut
  `except Exception as e: ... log_exception(...)` kalıbı korunur).
- **Yeni:** `_personel_performans_render(self, parent, veri: dict, secili_ay:
  str)` — hesaplanan veriyi kart etiketlerine ve Treeview'e yazar, fark/%
  hesaplayıp vurgu satırını günceller.
- **Yeni (küçük yardımcı):** `_ay_listesi_getir(self) -> list[str]` —
  `personel_ucret_takibi` tablosundaki mevcut ayları `DISTINCT
  strftime('%Y-%m', tarih)` ile çeker (Ay combobox'ını doldurmak için).

`script/core/db.py`, `script/core/money.py`, `script/core/env.py`: **değişiklik
yok** — mevcut şema ve fonksiyonlar aynen kullanılır.

## 5. Kapsam dışı (bu spec'te YOK)

- Excel/PDF export (intent'te istenmedi). **Sonraki adım notu:** ileride
  istenirse mevcut `excel_ucret_listesi_yukle` deseninin tersi (export)
  ayrı bir intent olarak ele alınabilir.
- Grafik/chart görselleştirme (yalnızca tablo + etiket; sekmede grafik
  kütüphanesi eklenmiyor).
- 3 aydan uzun geçmiş karşılaştırma / trend analizi.
- Personel bazlı hedef/prim sistemi.
- `personel_ucret_takibi` tablosuna yeni kolon veya migrasyon.
- Ödeme durumuna göre filtreleme (bu özellik ödeme durumundan bağımsız
  çalışır — kapsam dışı değil ama bilinçli tasarım kararı, bkz. Bölüm 2).
- Rol bazlı erişim kısıtlaması / yeni yetki modeli — mevcut ekranın
  erişilebildiği herkes bu sekmeyi de görür.

## 6. Riskler / Bilinen Kısıtlar

- **Bu özellik salt-okunur bir raporlama katmanıdır.** `personel_ucret_takibi`
  tablosuna yazma yapmaz, mevcut hesaplama akışını (`pipeline.py` içindeki
  `hesapla_personel_ucreti` çağrısı ve seans kaydı sırasında satırın
  oluşturulması) değiştirmez. Dolayısıyla bu özellik **yeni bir risk
  eklemez**, ama mevcut verideki hataları/tutarsızlıkları olduğu gibi
  yansıtır (miras alır):
  - Eğer geçmişte `hesapla_personel_ucreti` bir `except Exception: pass`
    fallback'i (`core/money.py` satır 45-46, `%40` varsayılanına sessizce
    düşme) nedeniyle yanlış bir `personel_ucreti` kaydetmişse, aylık özet
    bu yanlış değeri de toplayıp gösterecektir. Bu spec bunu düzeltmiyor,
    sadece var olan veriyi aggregate ediyor.
  - `format_money` / `parse_money` (`core/money.py`) tutarsızlığı bu
    özelliği etkilemiyor çünkü sadece `format_money` (gösterim) kullanılır,
    kullanıcıdan money-input alınmıyor (salt-okunur ekran, form yok).
  - `records` / `seans_takvimi` elle iki yönlü senkronizasyon riski:
    aggregasyon sorgusu `seans_takvimi.durum != 'iptal'` kontrolü
    yapıyor; eğer bu iki tablo senkron değilse (bilinen denetim bulgusu),
    iptal edilmiş ama `seans_takvimi`'de güncellenmemiş bir seans yanlışlıkla
    sayılabilir. Bu, mevcut ham liste ekranının da paylaştığı bir risktir
    (aynı `LEFT JOIN` deseni kullanılıyor) — yeni değil, mevcut.
- **Personel ücret kuralı zaman içinde değiştiyse** (`PERSONEL_UCRET_KURALLARI`
  elle güncellenir, tarihçesi tutulmaz), geçmiş aylardaki `personel_ucreti`
  değerleri o dönemki kurala göre hesaplanmış olarak saklı kalır — bu doğru
  davranıştır (tarihsel doğruluk) ama kural değişikliği sonrası "geçmişe
  dönük yeniden hesaplama" beklentisi varsa bu özellik bunu YAPMAZ. Aylık
  özet her zaman o anda saklanmış `personel_ucreti` değerini gösterir.
- **Otomatik test yok** (bilinen proje geneli eksiklik). Bu özellik için de
  otomatik test yazılmayacaksa, `plan.md`'de en azından manuel doğrulama
  senaryoları (farklı ay/personel kombinasyonları, veri olmayan ay, "Tümü"
  seçimi) listelenmeli.
- **Kişisel veri / kimlik doğrulama / ödeme içermiyor** — personel adı ve
  parasal toplamlar zaten mevcut ekranlarda görünür veri; yeni bir
  yetkilendirme veya kimlik doğrulama yüzeyi açılmıyor. Bu nedenle
  `security-reviewer` incelemesi **zorunlu değil**, ama personel maaş/pay
  bilgisi hassas kabul edilebileceğinden Batuhan isterse kısa bir gözden
  geçirme yine de yapılabilir.

## 7. Kaba efor tahmini

Bu bir CRUD-benzeri, tek yönlü aggregasyon + raporlama özelliği (karmaşık
iş mantığı veya gerçek zamanlı senkronizasyon yok) — AI-hızlandırmalı
solo geliştirme için 5-10x çarpan aralığında.

| İş | Tahmini süre |
|---|---|
| SQL sorgusu + `_personel_performans_hesapla` (veri katmanı) | 1-1.5 saat |
| UI iskeleti: iç Notebook'a bölme, filtre satırı, kartlar | 1.5-2 saat |
| Karşılaştırma tablosu + fark/% vurgusu + renklendirme | 1.5-2 saat |
| Manuel uçtan uca test (farklı ay/personel/"Tümü" senaryoları, boş veri) | 1-1.5 saat |
| Küçük düzeltmeler / stil tutarlılığı (mevcut kalıplarla uyum) | 0.5-1 saat |
| **Toplam** | **≈ 5.5-8 saat (1 iş günü içinde bitebilir, ~1.5 gün tampon ile)** |

Not: geçmiş tahmin sapmaları için proje `CLAUDE.md`'sinde kayıtlı bir veri
bulunamadı (bu proje playbook ile ilk kez bootstrap ediliyor); bu nedenle
tahmin, benzer CRUD/raporlama işleri için gözlemlenen genel AI-hızlandırma
aralığına (5-10x) dayanıyor, kalibrasyon amaçlı geçmiş veri yok.

---

**Onay noktası:** Bu dosyayı Claude yazar, Batuhan okur / düzeltir / commit'ler.
Kod yazımı ancak bu dosya commit'lendikten ve `plan.md` onaylandıktan sonra
başlar.
