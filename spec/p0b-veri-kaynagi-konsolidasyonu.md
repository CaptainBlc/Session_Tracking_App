# Spec: P0 Parça B — `records` / `seans_takvimi` Veri Kaynağı Konsolidasyonu

Kaynak intent: `intent/2026-09-18-p0-finansal-veri-butunlugu.md` (Parça B,
madde 2 ve 10)
Durum: taslak — Batuhan onayı bekliyor.

## 1. Özet

`script/core/db.py` içinde seans/kayıt verisini tutan **dört** tablo var:
`records`, `seans_takvimi` (aktif, karşılıklı FK ile elle senkronize edilen
ikili) ve `kayitlar`, `seanslar` (init_db()'de hâlâ oluşturulan ama —
aşağıda doğrulandığı gibi — hiçbir sorgunun dokunmadığı ölü kod).

Kod kullanım analizine göre öneri:

- **Kalacak "doğru" kaynak: `seans_takvimi`.** `records` bu tabloya
  konsolide edilir (gerekçe Bölüm 3).
- **Kalacak migration fonksiyonu: `eski_veri_migration`** (Excel wizard).
  `eski_veri_migration_legacy` kaldırılır — hem işlevsiz (var olmayan bir
  modülü import ediyor) hem de artık hiçbir menüden çağrılmıyor (Bölüm 4).
- **Konsolidasyon stratejisi: tek adımda temiz kesim** (kademeli değil) —
  gerçek veri yokluğu + mevcut senkron kodunun zaten kırılgan/yetersiz
  olması bunu haklı çıkarıyor (Bölüm 5).
- `kayitlar` ve `seanslar` tabloları hiçbir yerde okunmuyor/yazılmıyor —
  doğrulandı, doğrudan kaldırılabilir.

**İşaretlenmiş endişe (Bölüm 8'de detay):** intent, iki migration
fonksiyonunun "aynı anda menüde durduğunu" varsayıyor; kod tabanında bu
doğrulanamadı — ikisi de şu an hiçbir `command=`/menü bağlamasından
çağrılmıyor görünüyor. Bu, önceki bir kısmi temizliğin izi olabilir. Öneri
bundan etkilenmiyor (ikisi de gerekçeyle karşılaştırıldı) ama Batuhan'ın
bilmesi gereken bir tutarsızlık.

## 2. Kullanım analizi bulguları

### 2.1 `kayitlar` / `seanslar` (legacy, `init_db()` satır ~350-378) — ÖLÜ KOD, doğrulandı

```
grep "(FROM|INTO|UPDATE|JOIN)\s+(kayitlar|seanslar)\b" script/ → 0 sonuç
```

`app_ui.py` içinde `seanslar`/`kayitlar` metinleri geçiyor ama hepsi yerel
Python değişken adı (örn. `script/app_ui.py:10750`, `:10825-10829` —
`seans_takvimi`'den `fetchall()` sonucu tutan değişkenin adı `seanslar`,
SQL tablo adı değil). Hiçbir `CREATE`, `SELECT`, `INSERT`, `UPDATE`,
`DELETE` bu iki tabloyu hedeflemiyor. **Önceki denetimin bulgusu teyit
edildi — bu iki tablo tamamen ölü kod, veri kaybı riski olmadan
kaldırılabilir.**

### 2.2 `records` ↔ `seans_takvimi` kullanım yoğunluğu

Ham sorgu sayıları (`script/app_ui.py` + `script/pipeline.py`, kaba grep):

| İşlem | `records` | `seans_takvimi` |
|---|---|---|
| `INSERT INTO` | 4 | 4 |
| `UPDATE` | 13 | 16 |
| `DELETE FROM` | 3 | 1 |
| `SELECT ... FROM` (ana tablo) | 32 | 32 |
| `JOIN` (başka sorguya eklenen taraf) | 10 | 5 |

Ham sayılar neredeyse simetrik — bu beklenen, çünkü tablolar elle iki yönlü
senkronize ediliyor (`app_ui.py:750` `_sync_from_record_to_seans`,
`app_ui.py:825` `_sync_from_seans_to_record`). Sayı simetrisi tek başına
karar vermeye yetmiyor; asıl ayrım **hangi tablonun "birincil"/"ebeveyn"
rolünde kullanıldığında** ortaya çıkıyor:

**a) Oturum oluşturma akışının sırası (`pipeline.py:287-382`,
`DataPipeline.seans_kayit`):**
1. Önce `seans_takvimi`'ye INSERT edilir → `seans_id` (lastrowid) alınır
   (`pipeline.py:291`, `:314`).
2. Sonra `records`'a INSERT edilir, `seans_id` FK olarak yazılır
   (`pipeline.py:320-326`).
3. `seans_takvimi.record_id` geri güncellenir (`pipeline.py:330`).
4. `personel_ucret_takibi` satırı **`seans_id`** ile oluşturulur
   (`pipeline.py:365`) — `record_id` değil.
5. Audit/event kaydı `_audit("seans_kayit", "seans_takvimi", seans_id, ...)`
   ve `_trigger_event("seans_created", {...})` — alan adı "seans", "record"
   değil (`pipeline.py:373-381`).

Yani kod, bir "seans"ı kavramsal olarak `seans_takvimi` satırıyla özdeşleştiriyor;
`records` satırı onun finansal-detay uydusu olarak ikinci sırada oluşturuluyor.

**b) Silme/güncelleme akışının birincil parametresi:** `pipeline.py`'deki
CRUD giriş noktaları (`kayit_sil(self, seans_id: int)` satır 450,
`kayit_guncelle(...)` satır ~394) birincil parametre olarak **`seans_id`**
alıyor, `record_id`'yi içeride `seans_takvimi.record_id`'den türetiyor
(`pipeline.py:456-457`, `:671-672`). Tersi yok — hiçbir CRUD girişi
`record_id`'yi birincil handle olarak almıyor (`odeme_ekle` istisna, o da
zaten finansal bir işlem — Bölüm 2.2c'ye bakın).

**c) Finansal alanların (`hizmet_bedeli`, `alinan_ucret`, `kalan_borc`)
merkezi olarak `records`'ta tutulması** doğru — ama bu, `records`'un ayrı
bir tablo olarak kalması gerektiği anlamına gelmiyor; borç haritası
(`pipeline.py:918-935`), kısmi ödeme dağıtımı (`pipeline.py:1215-1273`) ve
`odeme_ekle` (`pipeline.py:496-537`) hep `records.kalan_borc` /
`records.alinan_ucret` üzerinden çalışıyor. Bu üç alan `seans_takvimi`'ye
taşınabilir nitelikte — aşağıda gerekçelendirildi.

**d) Ana UI listeleme/rapor sorguları zaten `seans_takvimi`'yi sürücü
tablo olarak kullanıyor**, `records`'u yan tabloya (`LEFT JOIN`) indirgemiş
durumda:

```sql
-- app_ui.py:1766-1769, 1834-1837 (Seans Ücret Takip ana liste) ve 3428-3431
FROM seans_takvimi st
LEFT JOIN records r ON r.id = st.record_id OR r.seans_id = st.id
```

Dikkat: `OR r.id = st.record_id OR r.seans_id = st.id` — çift eşleşme
denemesi, bağlantının güvenilir olmadığının doğrudan kanıtı (senkron bazen
tek yönlü kalıyor).

**e) `kasa_hareketleri` zaten çift FK taşıyor** (`record_id` VE `seans_id`
kolonları, `db.py:217-231`) — bu tablo değişmeden kalabilir, join'i
`seans_id` üzerinden yapacak şekilde güncellemek yeterli.

**f) `odeme_hareketleri` sadece `record_id` taşıyor** (`db.py:203-213`) —
konsolidasyonda gerçek şema değişikliği gerektiren tek bağımlı tablo bu
(Bölüm 5, adım 3).

**g) Şema genişliği:** `seans_takvimi` (14 kolon) zaten `records`'un (12
kolon) süper kümesine yakın; `records`'ta olup `seans_takvimi`'de
olmayanlar sadece **`alinan_ucret`, `kalan_borc`** (2 kolon, ikisi de
`odeme_hareketleri.tutar` toplamından türetilebilir/senkron tutulabilir).
Tersi yönde (`seans_takvimi`'de olup `records`'ta olmayan): `oda`, `durum`,
`odeme_sekli`, `ucret_alindi`, `olusturan_kullanici_id` (5 kolon). Yani
`records`'u kazanan yaparsak 5 yeni kolon + `personel_ucret_takibi`'nin
FK'ini `record_id`'ye çevirmek gerekir; `seans_takvimi`'yi kazanan yaparsak
sadece 2 yeni kolon + `odeme_hareketleri`'nin FK'ini `seans_id`'ye çevirmek
gerekir. İkinci yol daha az şema değişikliği istiyor.

**h) `_sync_from_record_to_seans` fiilen ölü kod:** tanımlı
(`app_ui.py:750-823`) ama hiçbir yerden çağrılmıyor — sadece
`_sync_from_seans_to_record` çağrılıyor, tek bir noktadan
(`app_ui.py:10946`, Haftalık Takvim hızlı-seans-ekle ekranı). Bu ekran
`pipeline.seans_kayit`'i **atlayıp** doğrudan `seans_takvimi`'ye INSERT
yapıyor (`app_ui.py:10927-10943`) ve finansal alanları sıfır bırakıyor
(`hizmet_bedeli`, `alinan_ucret` bu akışta hiç set edilmiyor) — bu,
intent'in işaret ettiği "yeni bir ekran senkronu unutursa veri
tutarsızlığı kaçınılmaz" riskinin canlı bir örneği; şu an zaten kısmen
gerçekleşmiş durumda.

## 3. Önerilen "doğru" kaynak tablo: `seans_takvimi`

**Gerekçe (özet, Bölüm 2'ye dayanıyor):**

1. Kod, bir oturumu kavramsal olarak `seans_takvimi` satırıyla
   özdeşleştiriyor — oluşturma sırası, CRUD giriş noktalarının parametre
   adı, audit/event isimlendirmesi hep "seans" merkezli.
2. `personel_ucret_takibi` (P0 Parça A'daki `hesapla_personel_ucreti`
   hatasının doğrudan etkilediği tablo) zaten `seans_id` ile FK'li — yani
   personel maaş/hakediş hattı zaten `seans_takvimi.id`'yi kalıcı kimlik
   olarak kabul etmiş durumda.
3. Ana UI listeleme ekranları (Seans Ücret Takip ana liste, borç
   raporları) zaten `seans_takvimi`'yi sürücü tablo yapmış, `records`'u
   `LEFT JOIN` ile (güvenilmez çift-koşullu eşleşmeyle) ekliyor.
4. Şema açısından daha az iş: `records`'u kazanan yapmak 5 yeni kolon +
   `personel_ucret_takibi` FK taşıması gerektirirken, `seans_takvimi`'yi
   kazanan yapmak sadece 2 yeni kolon (`alinan_ucret`, `kalan_borc`) +
   `odeme_hareketleri` FK taşıması gerektiriyor.
5. `kasa_hareketleri` zaten iki FK'yi de taşıdığı için bu tabloda hiç şema
   değişikliği gerekmiyor, sadece join yönü değişiyor.

**Not:** `alinan_ucret` ve `kalan_borc`, prensipte `odeme_hareketleri`
üzerinden `SUM(tutar)` ile türetilebilir (tam normalize çözüm), ama bu spec
kapsamında **denormalize kolon olarak `seans_takvimi`'ye taşınmaları**
öneriliyor — mevcut tüm borç/ödeme kodu (`pipeline.py` borç haritası,
kısmi ödeme dağıtımı, hızlı bakiye okumaları) zaten bu iki alanı doğrudan
kolon olarak okuyor; tam normalizasyona geçmek bu spec'in kapsamını (basit
tablo birleştirme) bir performans/mimari yeniden tasarımına genişletir —
kapsam dışı bırakıldı (Bölüm 6).

## 4. Migration fonksiyonu kararı: `eski_veri_migration` kalır, `eski_veri_migration_legacy` kaldırılır

**`eski_veri_migration`** (`app_ui.py:9272-9783`, Excel şablon wizard'ı):
- Excel'den okuduğu her "Seans Ücret Takip" satırı için
  **`pipeline.seans_kayit(...)`** çağırıyor (`app_ui.py:9701-9714`) — yani
  tekilleştirilmiş, doğru, senkron-güvenli giriş noktasını kullanıyor
  (hem `seans_takvimi` hem `records` hem `personel_ucret_takibi` tutarlı
  şekilde oluşuyor).
- Tekrar-önleme kontrolü var (`app_ui.py:9689-9699`).
- Kendi kendine yeten, harici dosyaya bağımlı değil.

**`eski_veri_migration_legacy`** (`app_ui.py:9784-...`, harici DB dosyası
import wizard'ı):
- `import migration_eski_veriler` yapıyor (`app_ui.py:9846`) — bu modül
  proje içinde **hiçbir yerde yok** (`Glob "**/migration_eski_veriler*"` →
  0 sonuç). Çağrıldığı an `ModuleNotFoundError` ile patlar. **Fiilen
  bozuk.**
- Farklı bir kullanım senaryosu hedefliyor (harici/eski bir `.db` dosyasından
  aktarım) ama uygulanması eksik bırakılmış.

**Karar:** `eski_veri_migration_legacy` ve içindeki `migration_baslat`
mantığı komple kaldırılır. `eski_veri_migration` tutulur; içindeki tek
doğrudan `records` referansı (tekrar-önleme sorgusu, `app_ui.py:9692-9695`)
konsolidasyon sırasında `seans_takvimi`'ye yönlendirilir (Bölüm 5, adım 5).

## 5. Konsolidasyon adımları (tek adımda temiz kesim)

**Neden kademeli değil tek adım:** İki seçenek karşılaştırıldı —

- *Kademeli* (önce merkezi bir yazma fonksiyonu kurup senkronu bir süre
  daha koru, sonra `records`'u kaldır): mevcut senkron kodu zaten hatalı/
  eksik (`_sync_from_record_to_seans` hiç çağrılmıyor, Haftalık Takvim
  ekranı `pipeline.seans_kayit`'i atlayıp finansal alanları sıfırlıyor).
  Kademeli yaklaşım bu **zaten bozuk** senkronu bir süre daha canlı tutmayı
  gerektirir — ek risk, ek kod, ek süre; gerçek veri koruma faydası sıfır
  çünkü ortada korunacak gerçek veri yok.
- *Tek adım*: gerçek veri yok (intent'in kilit varsayımı, doğrulandı —
  şema değişikliği bugünkü en düşük riskli an), ve kullanım yoğunluğu
  analizi net bir yön gösteriyor (`seans_takvimi` kazanan). Kademeli
  yaklaşımın tipik gerekçesi ("üretimde veri var, aşamalı geç") burada
  geçerli değil.

**Sonuç: tek adımda temiz kesim önerilir**, aşağıdaki sırayla:

1. **Şema (`script/core/db.py`, `init_db()` / `_ensure_minimum_schema`)**
   - `seans_takvimi` tanımına `alinan_ucret REAL DEFAULT 0`,
     `kalan_borc REAL DEFAULT 0` kolonları eklenir.
   - `odeme_hareketleri` tanımına `seans_id INTEGER` kolonu eklenir
     (mevcut `record_id` bir geçiş dönemi için nullable bırakılabilir ya
     da tek adımda kaldırılabilir — plan.md'de netleşir).
   - `records`, `kayitlar`, `seanslar` `CREATE TABLE IF NOT EXISTS`
     satırları kaldırılır (yeni kurulumlarda hiç oluşmaz). Geliştirme
     ortamındaki mevcut `.db` dosyaları için `DROP TABLE IF EXISTS records`
     / `kayitlar` / `seanslar` içeren tek seferlik bir temizlik betiği
     eklenir (gerçek veri yok, veri taşıma gerekmez — sadece şema
     temizliği).

2. **`script/pipeline.py`** — `records`'a dokunan tüm fonksiyonlar
   `seans_takvimi`'ye yönlendirilir (alan adları aynı kaldığı için SQL
   metni büyük ölçüde `records`→`seans_takvimi` isim değişimi + JOIN
   kaldırma şeklinde): `seans_kayit` (287-382), `kayit_guncelle` (394-448),
   `kayit_sil` (450-486), `odeme_ekle` (496-537), borç haritası (918-935),
   kısmi ödeme dağıtımı (1215-1273), `eski_borc_sil` (642-...),
   `_add_kasa` çağrıları içindeki `record_id` parametreleri `seans_id`'ye
   indirgenir. `personel_ucret_takibi` tarafı değişmez (zaten `seans_id`
   kullanıyor).

3. **`odeme_hareketleri`** — tüm `record_id` referansları (`pipeline.py`
   satır ~340, 526, 684, `app_ui.py` çok sayıda rapor sorgusu) `seans_id`'ye
   çevrilir. Bu, tek gerçek FK-taşıma işi (Bölüm 2.2f).

4. **`kasa_hareketleri`** — `record_id` ile yapılan `JOIN`/`WHERE`'ler
   (`app_ui.py:1493, 1809, 1878, 10004, 10123, 10136, 10147` vb.)
   `seans_id`'ye çevrilir; kolonun kendisi zaten var, şema değişikliği
   gerekmez.

5. **`script/app_ui.py`** genelinde `records`'a doğrudan yazan/okuyan tüm
   noktalar (`FROM/INTO/UPDATE/JOIN records` — toplam ~59 referans)
   `seans_takvimi`'ye taşınır. Özellikle:
   - `_sync_from_record_to_seans` (750-823) ve `_sync_from_seans_to_record`
     (825-883) **tamamen silinir** — artık tek tablo olduğu için senkrona
     gerek kalmaz.
   - Haftalık Takvim hızlı-ekle ekranı (`app_ui.py:10909-10957`)
     `pipeline.seans_kayit`'i çağıracak şekilde yeniden yazılır (ya da en
     azından tam alan setiyle doğrudan `seans_takvimi`'ye yazacak şekilde
     düzeltilir) — böylece bu ekran artık finansal alanları sıfır
     bırakmaz.
   - Ana liste sorguları (`1766-1769`, `1834-1837`, `3428-3431`)
     `LEFT JOIN records r ON r.id = st.record_id OR r.seans_id = st.id`
     kalıbından kurtulur, doğrudan `seans_takvimi` kolonlarını okur.
   - `eski_veri_migration` içindeki tekrar-önleme sorgusu (`9692-9695`)
     `seans_takvimi`'ye yönlendirilir.
   - `eski_veri_migration_legacy` (9784'ten fonksiyon sonuna kadar)
     komple silinir.

6. **Regresyon/manuel doğrulama** — otomatik test olmadığı için (proje
   geneli bilinen eksiklik) plan.md'de en az şu senaryolar elle
   doğrulanmalı: yeni seans oluşturma (tam ücret + kısmi ödeme), ödeme
   ekleme, borcu kapatma, seans silme (kasa/ödeme/personel ücret
   kayıtlarının da silindiğinin kontrolü), borç haritası raporu, personel
   hakediş/maaş hesaplama ekranı, Haftalık Takvim hızlı-ekle, Excel eski
   veri import wizard'ı (uçtan uca, gerçek bir örnek dosyayla).

## 6. Kapsam dışı (bu spec'te YOK)

- `odeme_hareketleri`/`kasa_hareketleri` üzerinden tam normalizasyona
  geçiş (yani `alinan_ucret`/`kalan_borc`'u kolon olarak değil `SUM()`
  ile canlı hesaplamak) — mevcut kod tabanı bu iki alanı yaygın şekilde
  doğrudan kolon olarak okuyor; tam normalizasyon ayrı, daha büyük bir
  mimari iş.
- Parça A'daki para formatı / hata yutma düzeltmeleri (ayrı spec/plan,
  bağımsız ilerleyebilir).
- `personel_ucret_takibi`, `ogrenci_personel_fiyatlandirma` şemalarında
  değişiklik (zaten `seans_id` kullanıyorlar, dokunulmuyor).
- `eski_veri_migration_legacy`'nin hedeflediği "harici eski DB dosyasından
  içe aktarma" özelliğinin yeniden inşası — istenirse ayrı bir intent
  olarak ele alınabilir, bu spec sadece bozuk/kullanılmayan kodu kaldırıyor.
- Yeni otomatik test altyapısı kurulması (P1 kapsamı, intent'te belirtildi)
  — bu spec sadece manuel doğrulama senaryoları listeler.

## 7. Riskler / Bilinen Kısıtlar

- **Geniş, dağınık dokunma yüzeyi.** `records` referansları `app_ui.py`
  (13.000+ satırlık tek dosya) içinde 59+ noktaya, `pipeline.py` içinde
  ~35 noktaya yayılmış. Bunların hepsini bulup doğru şekilde
  `seans_takvimi`'ye çevirmek, tek bir noktayı kaçırma riski taşır —
  özellikle finansal alanlarda (`kalan_borc`, `alinan_ucret`) bir yeri
  atlamak sessiz bir veri tutarsızlığına yol açabilir (tam olarak bu
  intent'in önlemeye çalıştığı sınıf hata). **Azaltma:** değişiklik
  fonksiyon fonksiyon yapılmalı, her fonksiyon sonrası ilgili ekran elle
  test edilmeli; plan.md'de her adım için ayrı doğrulama checkpoint'i
  olmalı.
- **`odeme_hareketleri` FK taşıması** (`record_id` → `seans_id`) tek gerçek
  şema-seviyeli göç; gerçek veri olmadığı için düşük risk ama kod okuyan
  her rapor ekranının (kasa raporları, tahsilat geçmişi) bu değişikliğe
  bağımlı olduğu unutulmamalı.
- **`odeme_ekle` ve borç dağıtımı money-kritik.** Bu fonksiyonlar Parça
  A'daki `format_money`/`parse_money` tutarsızlığıyla da kesişiyor —
  Parça A ve B'nin aynı dosyalarda (`pipeline.py`, `app_ui.py`) çakışması
  olası; **iki spec ayrı ilerlese bile kodlama sırası önemli** (Parça A'nın
  para formatı düzeltmesi önce mi sonra mı yapılacağı plan.md'de
  netleşmeli — aynı satırlara iki ayrı değişiklik gelmesin diye).
- **Otomatik test yok** — bu, en riskli spec kalemlerinden biri çünkü
  finansal doğruluk (kalan borç, alınan ücret, personel hakedişi) elle
  doğrulanacak. Seed veri + elle hesaplama karşılaştırması (`CLAUDE.md`
  kuralı) burada özellikle titiz uygulanmalı.
- **Kişisel veri / kimlik doğrulama / ödeme içeriyor.** `odeme_hareketleri`,
  `kasa_hareketleri`, `records`/`seans_takvimi` üzerindeki finansal alanlar
  gerçek para akışını temsil ediyor. Playbook kuralı gereği bu spec'in
  **`security-reviewer` ajanı tarafından da gözden geçirilmesi öneriliyor**
  — özellikle FK taşıma adımının (adım 3) veri bütünlüğünü bozmadığından
  emin olmak için (dış ödeme sağlayıcısı yok ama iç finansal muhasebe
  bütünlüğü kritik).

## 8. İşaretlenmiş endişeler (açık karar noktaları)

1. **Kaynak tablo kararı software-architect'e bırakıldı** (intent, açık
   soru #2) — bu spec `seans_takvimi`'yi öneriyor ama nihai onay
   Batuhan'ın. Alternatif (`records`'u kazanan yapmak) teknik olarak
   mümkün, sadece daha fazla şema değişikliği (5 kolon + FK taşıma)
   gerektiriyor — Bölüm 3'teki gerekçeyle karşılaştırılıp reddedildi.
2. **İki migration fonksiyonunun "aynı anda menüde durduğu" iddiası
   kod tabanında doğrulanamadı.** Statik grep analizi (`self\.eski_veri_migration`,
   `command=`, `add_command`, `getattr` kalıpları) her iki fonksiyon için de
   sıfır çağrı noktası buldu — şu an ikisi de hiçbir menüden erişilemiyor
   görünüyor. Bu ya (a) önceki bir kısmi temizlikte menü bağlantısı
   kaldırılmış ama fonksiyonlar unutulmuş, ya da (b) çağrı dinamik bir
   yoldan (bu grep'in yakalayamadığı bir kalıp) yapılıyor. Öneri
   (Bölüm 4) bu belirsizlikten etkilenmiyor çünkü karar zaten fonksiyonların
   kendi içeriğine (biri çalışıyor, biri bozuk) dayanıyor — ama Batuhan'ın
   plan.md aşamasında UI'da elle kontrol etmesi (uygulamayı açıp menüde
   gerçekten arayarak) önerilir.
3. **`alinan_ucret`/`kalan_borc`'u `seans_takvimi`'ye denormalize kolon
   olarak taşımak** (Bölüm 3, Not) mı yoksa `odeme_hareketleri`'nden canlı
   hesaplamak mı — bu spec denormalize kolonu öneriyor (daha az kod
   değişikliği, mevcut okuma kalıplarıyla uyumlu) ama bu bir mimari tercih;
   Batuhan farklı düşünürse plan.md'de değişebilir.

## 9. Kaba efor tahmini

Bu iş **CRUD değil** — finansal hesaplama (borç dağıtımı, kısmi ödeme,
personel hakedişi) içeren, 13.000+ satırlık tek bir dosyaya dağılmış ~95+
çağrı noktasını dokunan bir refactor. AI-hızlandırmalı solo geliştirme için
karmaşık iş mantığı çarpanı (1.5-2x) baz alınmalı, CRUD çarpanı (5-10x)
değil — çünkü asıl süre kod yazmakta değil, her adımdan sonra parayı elle
doğrulamakta geçecek (otomatik test yok).

| İş | Tahmini süre |
|---|---|
| Şema değişikliği (`db.py`: 2 yeni kolon, 3 tablo kaldırma, temizlik betiği) | 1-1.5 saat |
| `pipeline.py` refactor (~10 fonksiyon: seans_kayit, kayit_guncelle, kayit_sil, odeme_ekle, borç haritası, kısmi ödeme, eski_borc_sil) | 3-5 saat |
| `odeme_hareketleri` FK taşıması (`record_id`→`seans_id`, tüm bağımlı sorgular) | 1.5-2.5 saat |
| `app_ui.py` refactor (~59 `records` referansı + 2 sync fonksiyonunun silinmesi + Haftalık Takvim ekranı düzeltmesi + ana liste sorguları) | 6-10 saat |
| `eski_veri_migration_legacy` kaldırma + `eski_veri_migration` tekrar-önleme sorgusu güncelleme | 0.5-1 saat |
| Manuel uçtan uca doğrulama (Bölüm 5, adım 6'daki senaryolar — seed veri + elle hesaplama karşılaştırması) | 3-5 saat |
| Regresyon/edge-case düzeltme tamponu (kaçırılan referans, beklenmeyen davranış) | 2-4 saat |
| **Toplam** | **≈ 17-29 saat (≈ 2.5-4 iş günü, tampon dahil)** |

Not: proje `CLAUDE.md`'sinde geçmiş tahmin sapması verisi yok (playbook
ilk kez bootstrap ediliyor) — bu tahmin, benzer "geniş dokunma yüzeyli,
finansal doğruluk gerektiren, test'siz refactor" işleri için gözlemlenen
düşük çarpan aralığına (1.5-2x) dayanıyor; kalibrasyon amaçlı geçmiş veri
yok, bu nedenle iyimser değil temkinli tarafta tutuldu.

---

**Onay noktası:** Bu dosyayı Claude yazar, Batuhan okur / düzeltir /
commit'ler. Kod yazımı ancak bu dosya commit'lendikten ve `plan.md`
onaylandıktan sonra başlar. Finansal veri / ödeme akışı içerdiği için
`security-reviewer` incelemesi önerilir (Bölüm 7).
