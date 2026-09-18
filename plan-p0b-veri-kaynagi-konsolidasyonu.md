# Plan: P0 Parça B — `records` / `seans_takvimi` Veri Kaynağı Konsolidasyonu

Kaynak: `spec-p0b-veri-kaynagi-konsolidasyonu.md`.
Status: draft — Batuhan onayı bekliyor. Onaylanıp commit'lenmeden kod
aşamasına geçilmez.

## 0. Onaylanan karar noktaları (spec Bölüm 8)

1. **Kaynak tablo:** `seans_takvimi` kazanan, `records` ona konsolide
   edilir — onaylandı.
2. **`alinan_ucret`/`kalan_borc`:** `seans_takvimi`'ye **denormalize kolon**
   olarak taşınır (canlı `SUM()` hesaplama değil) — onaylandı.
3. **İki migration fonksiyonunun menüde olup olmadığı** (spec'in
   doğrulayamadığı iddia) — bu, kararı etkilemiyor (`eski_veri_migration`
   kalır, `eski_veri_migration_legacy` kaldırılır, gerekçe fonksiyonların
   kendi içeriğine dayanıyor). **Bloklamıyor**, ama Batuhan'dan kod
   aşamasından önce uygulamayı açıp iki menüyü elle arayarak kontrol etmesi
   isteniyor — sonuç ne olursa olsun plan değişmez, sadece bir tutarsızlık
   notu düşülür.

`eski_veri_migration_legacy` ve `_sync_from_record_to_seans` komple
kaldırılıyor (ikisi de ölü/bozuk kod, spec Bölüm 2.1/2.2h/4'te doğrulandı).

## 1. Parça A ile koordinasyon (önemli, çakışma riski)

Parça A **kod olarak tamamlandı** (henüz commit edilmedi). Parça A'nın
[app_ui.py:7268-7277](script/app_ui.py:7268) değişikliği (`except: pass` →
`log_exception`) **tam olarak Parça B'nin taşıyacağı bir sorgunun**
(`records.kalan_borc` okuyan borç haritası) üzerinde:

```python
cur.execute("SELECT COALESCE(danisan_adi,''), COALESCE(kalan_borc,0) FROM records WHERE COALESCE(kalan_borc,0)>0")
```

**Kural:** Parça B bu sorguyu `seans_takvimi.kalan_borc`'a taşırken, Parça
A'da eklenen `log_exception("_tum_danisanlari_listele_borc_map", e)`
satırını **korumalı** — geriye `except: pass`'e dönülmemeli. Adım 5.5'te
ayrıca hatırlatılıyor.

İki parça aynı dosyalarda (`app_ui.py`, `pipeline.py`) çalıştığı için:
Parça A önce commit'lenmeli, Parça B o commit'in üzerine kodlanmalı (sırayla,
aynı anda değil) — birleştirme çakışmasını önler.

## 2. Uygulama sırası (spec Bölüm 5 ve 9'a dayanıyor)

Sıra bağımlılık zincirini izliyor: önce şema (her şey ona bağlı), sonra
`pipeline.py` (merkezi CRUD katmanı), sonra bağımlı FK taşımaları, en son
`app_ui.py`'nin dağınık ~59 referansı, en sonda manuel doğrulama.

### Adım 1 — Şema değişikliği (`script/core/db.py`) (~1-1.5 saat)

- `seans_takvimi` tanımına `alinan_ucret REAL DEFAULT 0`,
  `kalan_borc REAL DEFAULT 0` eklenir.
- `odeme_hareketleri` tanımına `seans_id INTEGER` eklenir.
- `records`, `kayitlar`, `seanslar` `CREATE TABLE IF NOT EXISTS` satırları
  kaldırılır.
- Geliştirme ortamındaki mevcut `.db` dosyaları için tek seferlik temizlik
  betiği (`DROP TABLE IF EXISTS records/kayitlar/seanslar`) — veri taşıma
  YOK (gerçek veri yok), sadece şema temizliği.
- **Checkpoint:** `init_db()` sıfırdan bir test DB'sinde hatasız çalışıyor,
  yeni kolonlar `PRAGMA table_info(seans_takvimi)` ile görünüyor.

### Adım 2 — `script/pipeline.py` refactor (~3-5 saat)

Fonksiyon fonksiyon, her birinden sonra ilgili ekran elle test edilecek
(spec Bölüm 7'nin talep ettiği "değişiklik fonksiyon fonksiyon" azaltma
stratejisi):

1. `seans_kayit` (287-382) — `records` INSERT'i kaldırılır, finansal
   alanlar (`hizmet_bedeli`, `alinan_ucret`, `kalan_borc`) doğrudan
   `seans_takvimi` INSERT'ine eklenir. `personel_ucret_takibi` zaten
   `seans_id` kullandığı için değişmez.
   - **Checkpoint:** yeni bir seans (tam ücret) ve bir tane kısmi ödemeli
     seans oluşturulur, `seans_takvimi` satırında doğru `alinan_ucret`/
     `kalan_borc` görülür.
2. `kayit_guncelle` (394-448), `kayit_sil` (450-486) — `records`
   referansları `seans_takvimi`'ye çevrilir.
   - **Checkpoint:** bir seans güncellenir, bir seans silinir (kasa/ödeme/
     personel ücret kayıtlarının da silindiği kontrol edilir).
3. `odeme_ekle` (496-537), borç haritası (918-935), kısmi ödeme dağıtımı
   (1215-1273), `eski_borc_sil` (642-...) — hepsi `seans_takvimi.kalan_borc`/
   `alinan_ucret` üzerinden çalışacak şekilde çevrilir.
   - **Checkpoint:** kısmi ödeme senaryosu elle hesaplanır (seed veri +
     beklenen bakiye), gerçek sonuçla karşılaştırılır (CLAUDE.md kuralı).

### Adım 3 — `odeme_hareketleri` FK taşıması (~1.5-2.5 saat)

- Tüm `record_id` referansları (`pipeline.py` ~340, 526, 684 ve
  `app_ui.py`'deki rapor sorguları) `seans_id`'ye çevrilir.
- Bu, tek gerçek şema-seviyeli FK göçü (spec Bölüm 2.2f) — en dikkatli
  yapılması gereken adım.
- **Checkpoint:** bir tahsilat/ödeme geçmişi raporu açılır, önceki
  davranışla birebir aynı satırların (artık `seans_id` üzerinden) doğru
  geldiği doğrulanır.

### Adım 4 — `kasa_hareketleri` join yönü (~30-45 dakika)

- Kolon zaten var (`record_id` VE `seans_id`), sadece
  `app_ui.py:1493, 1809, 1878, 10004, 10123, 10136, 10147` vb. join/where
  ifadeleri `seans_id`'ye çevrilir.
- **Checkpoint:** Kasa Defteri raporu açılır, tutarlar önceki davranışla
  birebir aynı.

### Adım 5 — `script/app_ui.py` geniş refactor (~6-10 saat)

En dağınık ve en riskli adım (~59 referans). Alt adımlara bölünüyor:

1. `_sync_from_record_to_seans` (750-823) ve `_sync_from_seans_to_record`
   (825-883) **tamamen silinir**.
2. Haftalık Takvim hızlı-ekle ekranı (10909-10957) `pipeline.seans_kayit`'i
   çağıracak şekilde yeniden yazılır — bu ekranın finansal alanları sıfır
   bırakma bug'ı (spec Bölüm 2.2h) bu adımda düzelmiş olur.
   - **Checkpoint:** Haftalık Takvim'den hızlı seans eklenir, `hizmet_bedeli`
     artık sıfır kalmıyor.
3. Ana liste sorguları (1766-1769, 1834-1837, 3428-3431) — çift-koşullu
   `LEFT JOIN records ... OR ...` kalıbından kurtulup doğrudan
   `seans_takvimi` okur.
   - **Checkpoint:** Seans Ücret Takip ana listesi açılır, satır sayısı ve
     tutarlar öncekiyle birebir aynı.
4. `eski_veri_migration` tekrar-önleme sorgusu (9692-9695) `seans_takvimi`'ye
   yönlendirilir; `eski_veri_migration_legacy` (9784-fonksiyon sonu) komple
   silinir.
   - **Checkpoint:** Excel wizard'ı gerçek/örnek bir dosyayla uçtan uca
     çalıştırılır, tekrar-önleme çalışıyor.
5. **Kalan tüm `FROM/INTO/UPDATE/JOIN records` noktaları** tek tek taranır
   ve taşınır. **Bölüm 1'deki uyarı burada geçerli:** borç haritası
   sorgusundaki (`_tum_danisanlari_listele`, ~7268-7277) `log_exception`
   çağrısı Parça A'dan geldiği gibi korunur, `except: pass`'e geri
   dönülmez. Aynı fonksiyondaki veli yakınlık sorgusu (Parça A'da ayrıca
   `yakinlik` kolon adı düzeltmesi almıştı) da dokunulmadan kalır — bu
   fonksiyon `records`'a değil `ogrenci_aile_bilgileri`'ne bakıyor.
   - **Checkpoint:** "Tüm Danışanlar" ekranı açılır, bakiyeler öncekiyle
     birebir aynı, log dosyasında yeni bir hata satırı düşmüyor.

### Adım 6 — Manuel uçtan uca doğrulama (~3-5 saat)

Spec Bölüm 5.6'daki senaryolar, seed veri + elle hesaplama karşılaştırmasıyla:

- [ ] Yeni seans oluşturma (tam ücret)
- [ ] Yeni seans oluşturma (kısmi ödeme) — bakiye elle hesaplanıp karşılaştırılır
- [ ] Ödeme ekleme (mevcut bir seansa)
- [ ] Borcu tamamen kapatma
- [ ] Seans silme — kasa/ödeme/personel ücret kayıtlarının da silindiği kontrolü
- [ ] Borç haritası raporu (Tüm Danışanlar ekranı)
- [ ] Personel hakediş/maaş hesaplama ekranı (Parça A'nın performans
      sekmesiyle de kesişiyor — orada da sayılar doğru mu bakılır)
- [ ] Haftalık Takvim hızlı-ekle
- [ ] Excel eski veri import wizard'ı (`eski_veri_migration`), uçtan uca

### Adım 7 — Regresyon/tampon (~2-4 saat)

Kaçırılan referans veya beklenmeyen davranış için ayrılmış tampon süre
(spec Bölüm 9) — plan'ın kendisi bu adımı önceden somutlaştırmıyor, Adım
2-6 sırasında bulunan sorunlar burada kapatılır.

**Toplam tahmini süre: ≈ 17-29 saat** (spec Bölüm 9 ile birebir aynı).

## 3. `security-reviewer` incelemesi

Spec Bölüm 7'nin önerisi gereği (finansal/kişisel veri, FK taşıma veri
bütünlüğü riski) — **Adım 3 (`odeme_hareketleri` FK taşıması) ve Adım 2'nin
finansal fonksiyonları (`odeme_ekle`, borç haritası, kısmi ödeme dağıtımı)
tamamlandıktan sonra, Adım 6'nın manuel doğrulamasından önce** bir
`security-reviewer` incelemesi yapılır. Kapsamı: FK taşımasının veri
bütünlüğünü bozup bozmadığı, borç/ödeme hesaplamalarının tutarlılığı.
İnceleme bulguları varsa Adım 7'nin tamponunda kapatılır.

## 4. Manuel doğrulama checklist'i — genel

Otomatik test yok. Her adımın kendi checkpoint'i yukarıda listelendi; ek
olarak tüm iş bitince Adım 6'nın 9 senaryosu tek seferde baştan sona bir
daha koşulur (regresyon garantisi).

## 5. Commit noktası

- Bu `plan.md` dosyası commit edilmez — Batuhan okur, onaylar, kendisi
  commit'ler.
- Kod aşamasına bu plan VE `spec-p0b-veri-kaynagi-konsolidasyonu.md`
  onaylanıp commit'lenmeden geçilmez.
- **Sıra şartı:** Parça A önce commit'lenmiş olmalı (Bölüm 1).
- Kod tamamlandıktan sonra da commit'i Batuhan atar, Claude atmaz.

---

**Onay noktası:** Bu `plan.md` Batuhan tarafından onaylanıp commit'lenene
kadar kod aşamasına geçilmez.
