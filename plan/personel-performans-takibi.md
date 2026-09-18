# Plan: Personel Aylık Performans ve Kazanç Takibi

Kaynak spec: `spec.md` (onaylı).
Durum: taslak — Batuhan onayı bekliyor. Onaylanmadan kod yazımı başlamaz.

Tek dosyalı, tek özellik değişikliği (`script/app_ui.py`). Ağır bir proje
yönetimi süreci gerekmiyor — aşağıdaki sıra, spec Bölüm 4'teki 4 yeni + 1
değişen fonksiyonu bağımlılık sırasına göre dizer: önce veri katmanı, sonra
mevcut sayfanın iç Notebook'a bölünmesi, sonra yeni sekmenin iskeleti, en
son veri↔UI bağlanması ve vurgu mantığı.

Süre dağılımı spec Bölüm 7'deki toplam tahminden (≈5.5-8 saat) türetildi.

## Uygulama sırası

1. **`_ay_listesi_getir(self) -> list[str]`** (yeni, küçük yardımcı)
   - Ne: `personel_ucret_takibi` tablosundan `DISTINCT strftime('%Y-%m',
     tarih)` ile mevcut ayları DESC sırayla çeker. Ay combobox'ının veri
     kaynağı; sonraki adımlar buna bağımlı, önce yazılmalı.
   - Dosya/fonksiyon: `script/app_ui.py`, yeni fonksiyon.
   - Tahmini süre: ~0.5 saat.

2. **`_personel_performans_hesapla(self, personel_adi: str, ay: str) -> dict`**
   (yeni)
   - Ne: spec Bölüm 2'deki SQL'i çalıştırır (seçili ay + önceki 2 ay
     penceresi, iptal seans hariç, personel filtresi opsiyonel), sonucu
     `{ay: {seans_sayisi, brut_ciro, personel_payi, net_kazanc}}` sözlüğüne
     çevirir; eksik ayları 0 ile doldurur. Hata durumunda boş dict döner +
     mevcut `log_exception` kalıbı kullanılır.
   - Dosya/fonksiyon: `script/app_ui.py`, yeni fonksiyon. Bağımlılık:
     adım 1 (ay hesaplama için referans alınabilir ama esas mantık
     `datetime` ile bağımsız da kurulabilir — combobox'tan gelen `ay`
     parametresini kullanır).
   - Tahmini süre: ~1 saat (adım 1 ile birlikte spec'teki "veri katmanı"
     bloğu 1-1.5 saat içinde).

3. **`_build_personel_ucret_takibi_page` değişikliği** (mevcut fonksiyon)
   - Ne: Gövde aynen korunur, ama artık doğrudan `parent`'a değil, yeni
     kurulan iç `ttk.Notebook`'un ilk sayfasına (`page_ham_liste`) render
     edilir. İkinci sayfa boş bırakılır (adım 4'te doldurulacak).
   - Dosya/fonksiyon: `script/app_ui.py`,
     `_build_personel_ucret_takibi_page(self, parent)`.
   - Bağımlılık: yok (bağımsız yapısal değişiklik), ama adım 4'ten önce
     bitmiş olmalı çünkü ikinci sekmeyi bu Notebook barındıracak.
   - Tahmini süre: ~0.5-1 saat.

4. **`_build_personel_performans_sekmesi(self, parent)`** (yeni)
   - Ne: Filtre satırı (Personel combobox — "Tümü" + aktif personel
     listesi; Ay combobox — adım 1'in çıktısı; Yenile/Göster butonu),
     Verim/Kazanç kartları (`ttk.Labelframe` ikilisi) ve 3 Aylık
     Karşılaştırma Treeview'ini kurar. İlk yüklemeyi tetikler (adım 2 +
     adım 5'i çağırarak).
   - Dosya/fonksiyon: `script/app_ui.py`, yeni fonksiyon. Adım 3'ün
     tamamlanmış Notebook yapısına eklenir.
   - Tahmini süre: ~1-1.5 saat (adım 3 ile birlikte spec'teki "UI iskeleti"
     bloğu 1.5-2 saat).

5. **`_personel_performans_render(self, parent, veri: dict, secili_ay: str)`**
   (yeni)
   - Ne: Adım 2'nin döndürdüğü veriyi kart etiketlerine ve Treeview'e
     yazar; seçili ay ile bir önceki ay arasındaki fark/% değişimini
     hesaplayıp vurgu satırını (yeşil/kırmızı) günceller; önceki ay verisi
     yoksa veya net kazanç 0 ise "—" / bilgi mesajı gösterir; seçili ay
     satırını `tag_configure` ile vurgular.
   - Dosya/fonksiyon: `script/app_ui.py`, yeni fonksiyon. Bağımlılık: adım
     2 (veri sözlüğü) ve adım 4 (widget referansları) tamamlanmış olmalı.
   - Tahmini süre: ~1.5-2 saat (spec'teki "karşılaştırma tablosu + fark/%
     vurgusu" bloğu).

6. **Manuel uçtan uca test** (aşağıdaki checklist)
   - Tahmini süre: ~1-1.5 saat.

7. **Küçük düzeltmeler / stil tutarlılığı** (mevcut `Strong.Treeview`,
   `bootstyle` renk kalıplarıyla son karşılaştırma, kod temizliği)
   - Tahmini süre: ~0.5-1 saat.

**Toplam: ≈5.5-8 saat** (spec Bölüm 7 ile aynı, 1 iş günü içinde bitebilir).

## Manuel doğrulama checklist'i

Otomatik test yok (proje geneli bilinen eksiklik, spec Bölüm 6'da kabul
edilmiş). Aşağıdaki senaryolar kod tamamlandıktan sonra elle çalıştırılıp
sonuç burada/PR notunda teyit edilmeli:

- [ ] **Ham liste sekmesi bozulmadı mı:** "📋 Ham Liste" iç sekmesi açılıyor,
  mevcut filtreler/liste eskisi gibi çalışıyor (regresyon kontrolü, adım 3
  sonrası).
- [ ] **Tekli personel + veri olan ay:** Bir personel + üzerinde seans
  kaydı olan bir ay seçilir; kartlardaki seans sayısı/brüt ciro/personel
  payı/net kazanç elle (DB'den veya ham listeden) doğrulanan toplamlarla
  eşleşiyor mu.
- [ ] **"Tümü" personel + veri olan ay:** Personel filtresi "Tümü" iken
  gösterilen toplamlar, o ay için tüm personelin ham liste toplamının
  toplamına eşit mi.
- [ ] **Veri olmayan ay:** Henüz hiç seans kaydı olmayan bir ay (ör. gelecek
  ay, eğer combobox'ta seçilebiliyorsa) veya seçili personelin o ay hiç
  seansı yoksa — kartlar/tablo hata vermeden 0 gösteriyor mu ("veri yok"
  değil, 0 değeri; spec Bölüm 3.4).
- [ ] **3 aylık pencerenin bir kısmı boş:** Sadece son 1-2 aydır kaydı olan
  bir personel seçildiğinde, eksik aylar tabloya 0 satır olarak düşüyor mu
  (satır sayısı hep 3 mü).
- [ ] **Önceki ay verisi yok:** Seçili ayın bir öncesinde hiç kayıt yoksa
  vurgu satırında "Karşılaştırma için önceki ay verisi yok" mesajı çıkıyor
  mu (hata/exception yok).
- [ ] **Önceki ay net kazanç = 0:** % değişim hesaplanırken bölme hatası
  (ZeroDivisionError) oluşmuyor, "—" gösteriliyor mu.
- [ ] **İptal edilmiş seans içeren ay:** `seans_takvimi.durum = 'iptal'`
  olan bir seans, seans sayısı/toplamlara dahil edilmiyor mu (spec Bölüm 2
  aggregasyon kuralı — Batuhan'ın onayladığı varsayım).
- [ ] **Personel dropdown kaynağı:** Sadece `settings.is_active=1` olan
  personel isimleri listede görünüyor mu (pasif personel yok).
- [ ] **Ay dropdown varsayılanı:** Sekme ilk açıldığında en son (en güncel)
  ay otomatik seçili geliyor mu, liste DESC sıralı mı.
- [ ] **Seçili ay vurgusu:** Karşılaştırma tablosunda seçili aya karşılık
  gelen satır görsel olarak (ör. açık mavi arka plan) diğer 2 satırdan
  ayırt ediliyor mu.
- [ ] **Filtre değiştirme / Yenile butonu:** Personel veya ay değiştirilip
  "Yenile/Göster"e basıldığında eski verinin ekranda kalmadığı, yeni
  filtreye göre kart+tablo+vurgunun tam güncellendiği kontrol ediliyor mu.
- [ ] **Sessiz hata kontrolü:** Normal kullanım akışında (yukarıdaki
  senaryolar) uygulama loglarında `log_exception` tetiklenmediği kontrol
  ediliyor mu (varsa kök neden düzeltilmeden "bitti" sayılmaz).

## Commit noktası

Bu `plan.md` Batuhan tarafından onaylanmadan kod yazımına başlanmaz (spec
Bölüm son satırıyla tutarlı). Kod tamamlanıp yukarıdaki checklist elle
çalıştırılıp sonuçlar teyit edildikten sonra **tek commit noktası**: iş
bittiğinde **Batuhan commit atar** — Claude hiçbir aşamada commit atmaz
(proje geneli değişmez kural). Ara adımlarda (1-7) otomatik/ara commit
yoktur; tüm değişiklikler tek dosyada (`script/app_ui.py`) biriktirilip
manuel doğrulama tamamlandıktan sonra Batuhan'a teslim edilir.

---

**Onay noktası:** Bu dosyayı Claude yazar, Batuhan okur / düzeltir /
onaylar. Kod yazımı ancak bu dosya onaylandıktan sonra başlar.
