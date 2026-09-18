# Intent: Personel Aylık Performans ve Kazanç Takibi
Author: Batuhan. Status: draft.

## Problem
Leta Takip uygulamasını kullanan kurumdan gelen kullanıcı geri bildirimine göre,
elde artık her personel için en az 3 aylık işlem geçmişi (seans, ücret, ödeme)
birikmiş durumda. Ancak bu veri şu anda yalnızca ham, seans bazlı bir liste
olarak görülebiliyor (`Personel Ücret Takibi` ekranı — bkz.
`script/app_ui.py:_build_personel_ucret_takibi_page`). Kurum yöneticisi şu
soruları cevaplayamıyor:

- Bu ay her personel ne kadar seans yaptı, ne kadar ciro getirdi — geçen aya
  göre arttı mı azaldı mı?
- Maaş kuralına göre (`core/env.py:PERSONEL_UCRET_KURALLARI` — sabit ücret ya
  da yüzde) personele ödenen pay düşüldükten sonra kurumda net ne kalıyor,
  personel bazında?

Bu görünürlük eksikliği, personel verimliliğini ve karlılığını ay bazında
karşılaştırmalı şekilde değerlendirmeyi zorlaştırıyor.

## Proposed outcome
`Personel Ücret Takibi` ekranına, mevcut ham liste sekmesinin yanına yeni bir
**"Aylık Özet / Performans"** sekmesi eklenir. Bu sekmede, seçilen personel
(veya "Tümü") ve seçilen ay için:

- **Verim:** o aya ait seans sayısı ve toplam seans ücreti (ciro).
- **Kazanç:** o ay için hem brüt ciro (seans_ucreti toplamı) hem net kurum
  kazancı (seans_ucreti - personel_ucreti toplamı) yan yana gösterilir —
  maaş kuralına (sabit/yüzde) göre hesaplanan personel payı düşülerek.
- **Karşılaştırma:** seçilen ay, kendisinden önceki 2 ay ile birlikte (3 aylık
  pencere) tablo/özet halinde gösterilir; seçili ayın bir önceki aya göre
  değişimi (fark ve % olarak) ayrıca vurgulanır.

Personel dropdown'ı "Tümü" seçeneğini de destekler; bu durumda kurumun o ayki
toplam performansı (tüm personel toplamı) görülür.

Mevcut ham liste sekmesi ve verisi değişmeden kalır — bu, üstüne eklenen bir
özet/rapor katmanıdır, mevcut akışları bozmaz.

## Affected users and systems
- **Kullanıcı:** kurum müdürü / yönetici rolündeki uygulama kullanıcıları
  (mevcut yetki modeline göre `kurum_muduru` rolü, gerekirse diğer roller de
  kendi verilerini görebilir — spec.md'de netleşecek).
- **Sistemler / dosyalar (tahmini, spec.md'de kesinleşecek):**
  - `script/app_ui.py` — `_build_personel_ucret_takibi_page` içine yeni sekme
    UI'ı ve aylık aggregasyon sorgusu/render fonksiyonu.
  - `script/core/db.py` — mevcut `personel_ucret_takibi` tablosu kaynak veri
    olarak kullanılır; yeni tablo/migrasyon gerekmeyebilir (spec.md'de
    doğrulanacak).
  - `script/core/money.py` / `script/core/env.py` — mevcut
    `hesapla_personel_ucreti` ve `PERSONEL_UCRET_KURALLARI` aynen kullanılır,
    değişiklik beklenmiyor.
- Bu, ayrı bir "genel proje/tasarım gözden geçirme" talebinden bağımsız,
  kendi başına tamamlanacak bir özelliktir (o talep ayrı bir intent/akış
  olarak ele alınacak).

## Constraints
- Veri kaynağı `personel_ucret_takibi` tablosudur; aggregasyon ödeme durumundan
  (`odeme_durumu`) bağımsız olarak tüm seansları kapsar — çünkü bu görünüm
  "yapılan iş" performansını ölçer, tahsilatı değil (tahsilat zaten mevcut ham
  listede ödeme durumu filtresiyle izlenebiliyor). Bu varsayım spec.md'de
  Batuhan tarafından teyit edilecek.
- Mevcut playbook kuralları geçerli: bu intent.md Batuhan tarafından
  commit'lenir → sonra `spec.md` yazılır ve onaylanır → sonra `plan.md`
  onaylanır → ancak o zaman kod yazılır. Kodu Claude yazar, commit'i Batuhan
  atar.
- Proje şu ana kadar playbook ile bootstrap edilmemişti (bu `intent/` klasörü
  bu görevle birlikte ilk kez oluşturuldu); `PLAYBOOK.md`, `spec.md`,
  `plan.md`, `REVIEW.md`, `evals/` gibi diğer playbook dosyaları henüz yok —
  bunların bu proje için de kurulup kurulmayacağı Batuhan'ın kararı.
- Uygulama tek kullanıcılı/yerel SQLite masaüstü uygulaması; performans veya
  ölçek kısıtı beklenmiyor (veri hacmi küçük — bir kurumun aylık seans
  sayısı).

## Open questions
(yok — açık soru kalmadı; yukarıdaki varsayımlar spec.md aşamasında Batuhan
tarafından teyit/düzeltme ile netleşecek)

---
**Dosya adı kuralı:** `intent/YYYY-MM-DD-kisa-slug.md`
(ASCII, küçük harf, tire ile ayrılmış)
**Onay noktası:** Bu dosyayı Claude yazar, kullanıcı commit'ler.
