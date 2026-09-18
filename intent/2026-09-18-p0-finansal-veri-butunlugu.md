# Intent: P0 — Finansal Veri Bütünlüğü Düzeltme Paketi
Author: Batuhan. Status: draft.

## Problem
Önceki denetimde (3 ajan: UX, kod sağlığı, fonksiyonel risk) ve bu oturumdaki
testlerde doğrulanan, kurumun gerçek parasını/verisini etkileyebilecek 6
madde `product-owner` tarafından P0 (hemen) olarak önceliklendirildi. Henüz
gerçek veri girilmediği için (ne kurumda ne Batuhan'da), bu düzeltmeler
şimdi yapılırsa veri kaybı/bozulma riski sıfıra yakın — ertelendikçe risk
büyür.

İki farklı risk profili var, bu yüzden iki alt parçaya ayrılıyor:

**Parça A — bağımsız, düşük riskli, mekanik düzeltmeler:**
1. `format_money`/`parse_money` tutarsızlığı ([core/money.py:12](script/core/money.py:12)
   ve [:21](script/core/money.py:21)) — biri TR (`,`=ondalık) biri EN
   (`.`=ondalık) format varsayıyor. Ekrana yazılan bir tutar değiştirilmeden
   geri okunursa ~1000 kat yanlış çıkabilir.
3. `hesapla_personel_ucreti` ([core/money.py:31-46](script/core/money.py:31))
   hata durumunda sessizce %40 varsayılan orana düşüyor — config'te ufak bir
   yazım hatası, personele yanlış maaş hesaplanmasına yol açar, hiçbir iz
   bırakmadan.
4. DB bozuksa açılışta sessizce devam ediliyor ([core/backup.py](script/core/backup.py)'de
   artık durum dosyasına yazılıyor ama uygulama akışı hâlâ hatayı
   kullanıcıya göstermiyor) + borç/bakiye hesaplama akışlarında (`app_ui.py`
   içinde ~230+ örnek) yaygın `except Exception: pass` — özellikle veri
   bütünlüğünü etkileyen noktalarda (borç haritası, bakiye hesaplama) hata
   tamamen sessiz.
5. `assets_dir()` ([core/paths.py:53](script/core/paths.py:53)) çift
   `"script/script"` yolu üretiyor — `KULLANIM_KILAVUZU.txt` hiçbir zaman
   bulunamıyor (her açılışta loglanıyor, doğrulandı).

**Parça B — daha büyük, mimari bir karar gerektiren konsolidasyon:**
2. `records` ↔ `seans_takvimi` çift veri kaynağı; `_sync_from_record_to_seans`
   ([app_ui.py:750](script/app_ui.py:750)) ve `_sync_from_seans_to_record`
   ([app_ui.py:825](script/app_ui.py:825)) ile elle iki yönlü senkronize
   ediliyor. Tamamlanmamış bir migrasyonun kanıtı — yeni bir özellik ikisini
   de güncellemeyi unutursa veri tutarsızlığı (kayıp seans/ödeme) kaçınılmaz.
10. İki ayrı "eski veri migration" fonksiyonu aynı anda menüde duruyor
    (`eski_veri_migration` [app_ui.py:9272](script/app_ui.py:9272) ve
    `eski_veri_migration_legacy` [app_ui.py:9784](script/app_ui.py:9784)) —
    hangisinin gerçekten kullanılması gerektiği belirsiz; yanlış seçilirse
    veri kaybı riski var. Bu, #2'nin aynı kararına bağlı (hangi tablo
    "doğru" kaynak, hangi migration ona göre tasarlanmalı).

## Proposed outcome
**Parça A tamamlandığında:** para formatı her yerde tutarlı (TR formatı tek
standart), ücret hesaplama hatası sessizce yanlış bir varsayılana düşmek
yerine görünür/loglanır hale gelir, kritik hata yutma noktaları en azından
iz bırakır (popup ile kullanıcıyı bunaltmadan ama tamamen sessiz de
kalmadan — mevcut UX'i bozmayan bir denge, spec.md'de netleşecek),
`KULLANIM_KILAVUZU.txt` gerçekten bulunur.

**Parça B tamamlandığında:** tek bir "doğru" seans/kayıt veri kaynağı olur
(hangisinin kalacağı — `records` mı `seans_takvimi` mi — spec.md'de
software-architect tarafından mevcut kullanım yoğunluğuna bakılarak
kararlaştırılır), elle iki yönlü senkron kodu kaldırılır, tek bir migration
yolu kalır.

## Affected users and systems
- **Kullanıcı:** tüm uygulama kullanıcıları (kurum personeli) — finansal
  veri görünürlüğü ve doğruluğu herkesi etkiliyor.
- **Sistemler / dosyalar (tahmini, spec.md'de kesinleşecek):**
  - Parça A: `script/core/money.py`, `script/core/paths.py`,
    `script/app_ui.py` (hata yutma noktaları — kapsam spec.md'de
    somutlaşacak, "hepsini değiştir" değil "kritik olanları" hedefleniyor).
  - Parça B: `script/core/db.py` (şema), `script/pipeline.py`,
    `script/app_ui.py` (`_sync_from_*`, `eski_veri_migration*`,
    ilgili tüm CRUD noktaları) — geniş etkili, dikkatli spec/plan gerektirir.

## Constraints
- **Henüz gerçek veri yok** (kurumda da Batuhan'da da) — Parça B'nin şema
  konsolidasyonu için bu, riskin en düşük olduğu an. Gerçek veri girildikten
  sonra bu iş çok daha riskli/pahalı olur.
- **Test başarısız olursa testi değil kodu düzelt** kuralı burada özellikle
  önemli — para hesaplama değişiklikleri test edilmeden "bitti" sayılmaz.
  Otomatik test bu projede hiç yok (P1'de ayrı ele alınacak); bu demektir ki
  Parça A ve B için manuel doğrulama senaryoları plan.md'de özellikle
  titiz olmalı (önceki iki özellikte yapıldığı gibi, seed veri + elle
  hesaplama karşılaştırması).
- Playbook onay noktaları aynen geçerli: intent → Batuhan onaylar → spec/plan
  → Batuhan onaylar → ancak sonra kod. Commit'i Batuhan atar.
- Parça A ve Parça B **ayrı spec.md/plan.md** ile ilerleyebilir (farklı risk
  profilleri) — ya da Batuhan tek bir spec/plan tercih ederse öyle de
  yapılabilir; bu spec.md aşamasında netleşecek bir tercih, açık soru olarak
  aşağıda bırakıldı.

## Open questions
1. Parça A ve Parça B ayrı spec.md/plan.md ile mi ilerlesin (önerilen —
   düşük riskli mekanik düzeltmeler, riskli şema konsolidasyonunu
   beklemeden tamamlanabilir), yoksa tek bir spec/plan mı tercih edilir?
2. Parça B'de "doğru" kaynak tablo olarak `records` mi `seans_takvimi` mi
   seçilsin — yoksa bu kararı software-architect'in mevcut kod kullanım
   analizine göre önermesi mi istenir (önerilen)?

---
**Dosya adı kuralı:** `intent/YYYY-MM-DD-kisa-slug.md`
(ASCII, küçük harf, tire ile ayrılmış)
**Onay noktası:** Bu dosyayı Claude yazar, kullanıcı commit'ler.
