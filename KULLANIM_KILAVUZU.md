# Kullanım Kılavuzu / User Guide

---

## Türkçe

### Veriler nerede saklanır?

Uygulama tüm verileri yalnızca yerel bilgisayarda tutar — hiçbir veri dışarıya gönderilmez.

| İşletim Sistemi | Veri Klasörü |
|---|---|
| Windows | `%LOCALAPPDATA%\LetaYonetim\` |
| macOS | `~/Library/Application Support/LetaYonetim/` |
| Linux | `~/.local/share/LetaYonetim/` |

### Kurum logosu (isteğe bağlı)

`logo.png` adlı dosyayı uygulama ile aynı klasöre ya da veri klasörüne koyun; program açılışta otomatik olarak gösterir.

### 1 — İlk kurulum (yalnızca bir kez)

1. Uygulamayı açın.
2. "İLK KURULUM (Kurum Müdürü Oluştur)" butonuna tıklayın.
3. Kurum Müdürü hesabını oluşturun. Bu hesap tüm yetkilere sahiptir.

### 2 — Kullanıcı kaydı ve girişi

1. Giriş ekranında "KAYIT OL" ile çalışan hesabı oluşturun (varsayılan rol: eğitim görevlisi).
2. "GİRİŞ YAP" ile sisteme girin.

### 3 — Seans kaydı

- **SEANS TAKİP** ekranında: Tarih, Danışan, Uzman, Hizmet Bedeli ve Not alanlarını doldurun.
- "KAYDET" ile kaydı tamamlayın.

### 4 — Ödeme ekleme

- Listeden kaydı seçin → Sağ tık → "Ödeme Ekle"
- Eklenen tutar kalan borca otomatik yansır; aynı zamanda Kasa Defteri'ne "Giren" olarak işlenir.

### 5 — Haftalık takip

1. Menü: **Muhasebe → Haftalık Ders/Ücret Takip**
2. Hafta başlangıcını seçin → "Göster"
3. Her seans için seans ve ücret alındı/alınmadı durumunu işaretleyin.
4. İsterseniz "Excel'e Aktar" ile rapor alın.

### 6 — Günlük kasa

- Menü: **Muhasebe → Kasa Defteri (Günlük)**
- Tarihi seçin; giren/çıkan hareketler, devreden bakiye ve güncel kasa mevcudu otomatik hesaplanır.
- Kurum Müdürü "Gelir Ekle" / "Gider Ekle" ile manuel kayıt girebilir.

### 7 — Ayarlar

- Kurum Müdürü hesabıyla girişte **AYARLAR** sekmesi görünür.
- Buradan uzman ekleyebilir/silebilir, oda ve kullanıcı rollerini yönetebilirsiniz.

### 8 — Sistemi sıfırlama

- Yalnızca Kurum Müdürü yapabilir.
- **Dosya İşlemleri → Sistemi Sıfırla (DB Sil)**
- Program önce otomatik yedek alır, ardından veritabanını silerek ilk kurulum ekranına döner.

### Sorun giderme

Uygulama açılmıyor veya hata veriyorsa veri klasöründeki `leta_error.log` dosyasını inceleyin.

---

## English

### Where is data stored?

All data is stored locally on the machine — nothing is sent to any external server.

| Operating System | Data Folder |
|---|---|
| Windows | `%LOCALAPPDATA%\LetaYonetim\` |
| macOS | `~/Library/Application Support/LetaYonetim/` |
| Linux | `~/.local/share/LetaYonetim/` |

### Institution logo (optional)

Place a file named `logo.png` in the same folder as the application or inside the data folder. The app will display it automatically on startup.

### 1 — First-time setup (once only)

1. Launch the application.
2. Click "İLK KURULUM (Kurum Müdürü Oluştur)" (First Setup / Create Admin).
3. Create the Admin account. This account has full system access.

### 2 — User registration and login

1. On the login screen, click "KAYIT OL" (Register) to create a staff account (default role: instructor).
2. Click "GİRİŞ YAP" (Login) to enter the system.

### 3 — Recording a session

- On the **Session Tracking** screen: fill in Date, Client, Specialist, Fee, and Notes.
- Click "KAYDET" (Save) to confirm.

### 4 — Adding a payment

- Select a record from the list → Right-click → "Ödeme Ekle" (Add Payment)
- The amount is automatically deducted from the remaining balance and logged as income in the Cash Ledger.

### 5 — Weekly tracking

1. Menu: **Accounting → Weekly Session/Fee Tracking**
2. Select the start of the week → "Göster" (Show)
3. Mark each session and fee as received or not.
4. Export to Excel if needed.

### 6 — Daily cash ledger

- Menu: **Accounting → Daily Cash Ledger**
- Select a date; incoming/outgoing entries, carried-over balance, and current cash total are calculated automatically.
- The Admin can add manual income or expense entries.

### 7 — Settings

- The **Settings** tab is visible when logged in as Admin.
- Add or remove specialists, manage rooms and user roles.

### 8 — System reset

- Admin only.
- **File Operations → Reset System (Delete DB)**
- The app creates an automatic backup first, then deletes the database and returns to the first-time setup screen.

### Troubleshooting

If the application does not start or shows an error, check `leta_error.log` in the data folder.
