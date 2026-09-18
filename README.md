# Leta Takip

**Özel eğitim ve danışmanlık kurumları için masaüstü operasyon paneli** — seans planlama, borç/ödeme, kasa defteri ve personel ücret takibi tek uygulamada.

*Desktop operations panel for education and counseling practices — session scheduling, billing, cash ledger, and staff payouts in one place.*

[![Build](https://github.com/CaptainBlc/Leta-Takip/actions/workflows/build-all-platforms.yml/badge.svg)](https://github.com/CaptainBlc/Leta-Takip/actions/workflows/build-all-platforms.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)

---

## Özellikler / Features

| | TR | EN |
|---|---|---|
| **Seans** | Tarih, saat, oda ve uzmana göre planlama ve kayıt | Schedule and record sessions by date, time, room, and specialist |
| **Muhasebe** | Borç/kalan, ödemeler, haftalık alındı takibi | Client balance, payments, weekly receipt tracking |
| **Kasa** | Günlük gelir–gider ve otomatik bakiye | Daily income/expense with automatic balance |
| **Personel** | Seans bazlı hakediş ve ödeme durumu | Per-session compensation and payment status |
| **Yedekleme** | Açılışta otomatik, rotasyonlu yedek | Automatic backup on startup with rotation |
| **Akıllı varsayılanlar** | Danışan + uzmana göre tutar ve oda önerisi | Suggested fee and room based on client–specialist pairing |

---

## Teknoloji / Tech Stack

- **Python 3.11** · Tkinter · ttkbootstrap · tkcalendar
- **SQLite** — yerel, sunucusuz veri depolama / local, serverless storage
- **pandas** · **openpyxl** · **ReportLab**

---

## Kurulum / Setup

```bash
git clone https://github.com/CaptainBlc/Leta-Takip.git
cd Leta-Takip
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
python -m script.main
```

---

## Proje Yapısı / Project Structure

```
script/
├── main.py          # Giriş noktası / Entry point
├── app_ui.py        # Arayüz / UI layer
├── pipeline.py      # İş mantığı ve veri akışı / Business logic & data flow
└── core/
    ├── db.py        # Veritabanı / Database
    ├── backup.py    # Yedekleme / Backup
    ├── security.py  # Kimlik doğrulama / Auth
    ├── pricing.py   # Fiyatlandırma / Pricing logic
    ├── money.py     # Para işlemleri / Finance utils
    └── ...
```

---

## Geliştirme Süreci / Development Process

Her özellik/düzeltme aynı çizgiden geçer: **intent → spec → plan → kod**.
Bu adımların kayıtları aşağıdaki klasörlerde tutulur (denetim izi olarak):

Every feature/fix follows the same line: **intent → spec → plan → code**.
Records of these stages are kept in the folders below (as an audit trail):

```
intent/   # Problem tanımı: ne, kim için, neden şimdi / Problem statement: what, for whom, why now
spec/     # Çözüm tasarımı: nasıl, hangi dosyalar değişir / Solution design: how, which files change
plan/     # Uygulama sırası: adım adım, doğrulama checklist'i / Implementation order: steps, verification checklist
```

Her dosya adı ilgili özelliğin kısa açıklamasıdır (`intent/`'te tarih
önekiyle). Bir özelliğin tam geçmişini görmek için üç klasörde de aynı
adı arayın.

Each filename is a short slug for that feature (dated in `intent/`). To
see a feature's full history, look for the same name across all three
folders.

---

## Kullanım / Usage

Detaylı kullanım kılavuzu (Türkçe + English): [KULLANIM_KILAVUZU.md](KULLANIM_KILAVUZU.md)

---

## Gizlilik / Privacy

Tüm veriler yalnızca **yerel bilgisayarda** tutulur. Bu repoda gerçek kurum, danışan veya mali kayıt bulunmaz.

*All data stays on the local machine. This repository contains no real institutional or client data.*

---

## Lisans / License

[MIT](LICENSE)
