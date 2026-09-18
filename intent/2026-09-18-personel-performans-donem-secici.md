# Intent: Personel Performans — Günlük / Aylık / Yıllık Dönem Seçici
Author: Batuhan. Status: draft.

## Problem
"Personel Aylık Performans ve Kazanç Takibi" özelliği (bkz.
`intent/2026-09-18-personel-performans-takibi.md`, uygulandı ve test edildi)
şu an yalnızca **aylık** granülerlikte çalışıyor: seçili ay + önceki 2 ay
karşılaştırması. Kullanıcı, aynı görünümün **günlük** ve **yıllık**
periyotlarda da kullanılabilmesini istiyor — örn. bir günün diğer günlerle,
ya da bir yılın önceki yıllarla karşılaştırılması.

## Proposed outcome
"📈 Aylık Özet / Performans" sekmesine bir **"Dönem: Günlük / Aylık / Yıllık"**
seçici eklenir. Seçilen dönem tipine göre:

- **Günlük:** seçili gün + önceki 2 gün karşılaştırılır (`tarih` doğrudan
  gün bazında gruplanır, `strftime('%Y-%m-%d', tarih)`).
- **Aylık:** mevcut davranış aynen korunur (`strftime('%Y-%m', tarih)`).
- **Yıllık:** seçili yıl + önceki 2 yıl karşılaştırılır
  (`strftime('%Y', tarih)`).

Her üç dönem tipinde de aynı 3'lü pencere karşılaştırma mantığı, aynı
kart/tablo tasarımı (Verim, Kazanç, önceki döneme göre fark/%, 3 satırlık
karşılaştırma tablosu) kullanılır — sadece gruplama birimi ve dönem
seçici/etiketleri değişir. Personel filtresi ("Tümü" dahil) aynen kalır.

## Affected users and systems
- **Kullanıcı:** aynı — kurum müdürü / yönetici rolü.
- **Sistemler / dosyalar (tahmini, spec.md'de kesinleşecek):**
  - `script/app_ui.py` — `_build_personel_performans_sekmesi`,
    `_personel_performans_hesapla`, `_personel_performans_render`,
    `_ay_listesi_getir` fonksiyonları dönem tipine göre genelleştirilecek
    (muhtemelen `_ay_listesi_getir` yerine `_donem_listesi_getir(donem_tipi)`
    gibi bir genelleme, `_personel_performans_hesapla`'nın `strftime` formatı
    parametreleştirilecek).
  - Veri kaynağı aynı: `personel_ucret_takibi` tablosu, yeni tablo/migrasyon
    gerekmiyor.

## Constraints
- Mevcut aylık davranış **regresyona uğramamalı** — bu özelliğin
  üzerine inşa edilen bir genelleme, yeniden yazım değil.
- Playbook onay noktaları aynen geçerli: bu intent.md → Batuhan onaylar →
  `spec.md`/`plan.md` yazılır ve onaylanır → ancak sonra kod yazılır.
- "Günlük" görünümde veri hacmi (bir kurumun günlük seans sayısı) küçük
  olduğundan performans endişesi yok.

## Open questions
(yok — karşılaştırma mantığı Batuhan tarafından onaylandı: her üç dönem
tipinde de aynı 3'lü pencere yaklaşımı kullanılacak)

---
**Dosya adı kuralı:** `intent/YYYY-MM-DD-kisa-slug.md`
(ASCII, küçük harf, tire ile ayrılmış)
**Onay noktası:** Bu dosyayı Claude yazar, kullanıcı commit'ler.
