# Plan: Personel Performans — Günlük / Aylık / Yıllık Dönem Seçici

Kaynak spec: `spec/personel-performans-donem-secici.md` (onaylı).
Durum: taslak — Batuhan onayı bekliyor. Onaylanmadan kod yazımı başlamaz.

Tek dosyalı değişiklik (`script/app_ui.py`), mevcut çalışan bir özelliğin
genelleştirilmesi. En kritik risk **regresyon**: mevcut aylık görünüm halen
üretimde kullanılabilir durumda ve test edilmiş — bu yüzden sıralama, önce
"aylık davranışı bire bir koruyarak" veri katmanını genelleştirmek, en son
da UI'ya dönem tipi seçici eklemek şeklinde kurgulandı.

## Uygulama sırası

1. **Veri katmanı genellemesi** (`_personel_performans_donem_format`,
   `_donem_listesi_getir`, `_personel_performans_pencere_hesapla`,
   `_personel_performans_hesapla` güncellemesi)
   - Ne: spec Bölüm 2'deki 4 fonksiyon yazılır/güncellenir.
   - **Ara doğrulama (kod yazımı bitince, UI'ya dokunmadan önce):**
     `_personel_performans_hesapla(personel, "aylik", "2026-09")` çağrısının
     eski `_personel_performans_hesapla(personel, "2026-09")` ile **birebir
     aynı sözlüğü** döndürdüğü elle (bir Python betiğiyle, önceki oturumda
     yapıldığı gibi seed veri + sorgu karşılaştırması) doğrulanır. Bu adım
     geçmeden UI'ya geçilmez.
   - Tahmini süre: ~1.5-2 saat (doğrulama dahil).

2. **`_build_personel_performans_sekmesi` — dönem tipi radiobutton grubu**
   - Ne: "Dönem: Günlük / Aylık / Yıllık" radiobutton satırı eklenir
     (Kasa Defteri rapor tipi seçicisiyle aynı görsel kalıp). Varsayılan
     seçili değer **"aylik"** (mevcut davranışla aynı ilk görünüm).
   - Bağımlılık: adım 1.
   - Tahmini süre: ~1 saat.

3. **Dinamik etiketler ve "Dönem" combobox'ının yeniden beslenmesi**
   - Ne: radiobutton değişince "Personel/Ay" filtre etiketi "Gün"/"Ay"/"Yıl"
     olarak güncellenir; "Dönem" combobox'ı `_donem_listesi_getir(yeni_tip)`
     ile yeniden doldurulur; karşılaştırma tablosunun ilk kolon başlığı
     güncellenir.
   - Bağımlılık: adım 2.
   - Tahmini süre: ~1 saat.

4. **`_personel_performans_yukle` / `_personel_performans_render` güncellemesi**
   - Ne: `_personel_performans_yukle` artık seçili `donem_tipi`'ni okuyup
     `_personel_performans_hesapla`'ya iletir; `_personel_performans_render`
     "önceki X'e göre" metnini dönem tipine göre üretir
     (`{"gunluk": "güne", "aylik": "aya", "yillik": "yıla"}` gibi bir
     eşleme).
   - Bağımlılık: adım 1, 3.
   - Tahmini süre: ~1 saat.

5. **Manuel uçtan uca test** (aşağıdaki checklist).
   - Tahmini süre: ~1-1.5 saat.

**Toplam: ≈ 5.5-6.5 saat** (spec'teki 3.5-5.5 saatlik tahminden biraz
yüksek — adım 1'deki ara doğrulama adımı eklendiği için; regresyon riski
düşünülünce bu fazladan süre haklı görülüyor).

## Manuel doğrulama checklist'i

- [ ] **Regresyon — Aylık davranış birebir korunuyor mu:** Uygulama ilk
  açıldığında "Aylık" varsayılan seçili geliyor mu, önceki oturumda
  doğrulanan senaryolar (Pervin Hoca/Arif Hoca/Tümü, 2026-09) **aynı
  sayılarla** tekrar üretilebiliyor mu (seed veri script'i tekrar
  kullanılabilir).
- [ ] **Günlük — veri olan gün:** Bir personel + üzerinde seans kaydı olan
  bir gün seçilir, kartlardaki değerler DB'den doğrulanan toplamlarla
  eşleşiyor mu.
- [ ] **Günlük — veri olmayan gün:** Seans olmayan bir gün seçilince 0
  gösteriliyor mu (hata yok).
- [ ] **Yıllık — veri olan yıl:** Bir yıl seçilir, o yıla ait TÜM aylardaki
  seansların toplamı doğru mu (aylık verinin yıl bazında doğru
  toplandığının kontrolü).
- [ ] **Yıllık — önceki yıl karşılaştırması:** Fark/% hesaplaması yıllık
  bazda da doğru çalışıyor mu (aylık ile aynı formül, farklı pencere).
- [ ] **Dönem tipi değiştirme:** Aylık'tan Günlük'e, Günlük'ten Yıllık'a
  geçişte eski verinin ekranda kalmadığı, "Dönem" combobox'ının doğru
  yeniden dolduğu, varsayılan seçimin en güncel dönem olduğu kontrol
  ediliyor mu.
- [ ] **İptal edilmiş seans hariç tutma:** Her üç dönem tipinde de aynı
  şekilde çalışıyor mu (bu mantık değişmedi, ama regresyon kontrolü için
  tekrar bakılmalı).
- [ ] **Sessiz hata kontrolü:** Yukarıdaki senaryolarda `log_exception`
  tetiklenmiyor.

## Commit noktası

Kod tamamlanıp checklist elle çalıştırılıp teyit edildikten sonra **tek
commit noktası**: Batuhan commit atar — Claude commit atmaz (proje geneli
değişmez kural).

---

**Onay noktası:** Bu dosyayı Claude yazar, Batuhan okur / düzeltir /
onaylar. Kod yazımı ancak bu dosya onaylandıktan sonra başlar.
