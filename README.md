# String Parse

[![CI](https://github.com/metin02oktay/string-parse/actions/workflows/ci.yml/badge.svg)](https://github.com/metin02oktay/string-parse/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)

Sabit uzunluklu (fixed-width) segment metinlerini okuyup anlamlandırılmış
JSON'a dönüştüren, KVKK/GDPR uyumlu açık kaynak bir araçtır.

*[English summary below](#english-summary)*

---

## 🇹🇷 Türkçe

### Özellikler

- **Segment ayrıştırma:** Ham metindeki `GGxx` başlıklarını uzunluk alanına göre
  dilimler, aynı segmentten birden fazla varsa `GGSS_1`, `GGSS_2` şeklinde
  numaralandırır.
- **Genişletilebilir parser mimarisi:** Tüm parser'lar ortak
  `BaseSegmentParser` tabanından türer; yeni segment eklemek birkaç satırdır.
- **Türkçe docstring ve açıklamalar:** Her alanın açıklaması API yanıtında
  `aciklama` olarak döner.
- **KVKK/GDPR uyumu:** Log kayıtları `PIIMaskingFilter` ile maskelenir; ham
  segment verisi hiçbir loga yazılmaz.
- **Merkezi loglama:** Renkli konsol, günlük döndürülen dosya ve isteğe bağlı
  OpenSearch gönderimi.
- **Test ve CI:** `pytest` birim testleri ve GitHub Actions iş akışı.

### Desteklenen Segmentler

| Segment | Açıklama |
| --- | --- |
| `GGOH` | Çıktı başlığı: hata tipi, mesaj kodu, sorgu/çıktı referans numaraları |
| `GGSS` | Sorgu özeti: başvuru referans no, benzerlik oranı, özet ve uyarı göstergeleri |
| `GGTK` | Dönem bazlı veri geçmişi: kayıt referans no ve dönem blokları |

### Kurulum

```bash
git clone https://github.com/metin02oktay/string-parse.git
cd string-parse
uv sync            # veya: python -m venv .venv && pip install -e ".[dev]"
cp .env.example .env
```

### Çalıştırma

```bash
uv run python main.py
# veya
python main.py
```

Ardından <http://127.0.0.1:5000> adresini açın.

### API

**`POST /parse_et`**

```json
{ "raw_text": "GGOH0060  01    0000                    20250729000752974892" }
```

Yanıt:

```json
{
  "GGOH": {
    "Segment Kimliği": { "aciklama": "...", "deger": "GGOH" },
    "Mesaj Kodu": { "aciklama": "...", "deger": "000" }
  }
}
```

**`GET /health`** → `{"status": "ok"}`

Hata durumları: `400` geçersiz/boş gövde, `413` çok büyük gövde,
`500` beklenmeyen sunucu hatası.

### Kütüphane Olarak Kullanım

```python
from PARSERS import GGOHParser

veri = GGOHParser("GGOH0060  01    0000                    20250729000752974892").get_data()
print(veri["Mesaj Kodu"]["deger"])
```

### Testler

```bash
uv run pytest -q
uv run ruff check .
```

### Proje Yapısı

```text
.
├── AI/                     # AI ajanları için modüler bağlam ve kurallar
├── PARSERS/                # Segment parser'ları ve ortak taban sınıf
├── static/                 # jQuery
├── templates/              # Arayüz
├── tests/                  # Birim testleri (sentetik veri)
├── log_yapisi.py           # Merkezi loglama
├── main.py                 # Flask uygulaması
└── privacy.py              # PII maskeleme
```

### Gizlilik ve Güvenlik

- Depoda hiçbir gerçek kişisel veri, API anahtarı veya şifre bulunmaz.
- Tüm yapılandırma ortam değişkenlerinden okunur (`.env.example`).
- Güvenlik açığı bildirimi için [SECURITY.md](SECURITY.md) dosyasına bakın.

### Katkı

Katkı kuralları ve kod standartları için [CONTRIBUTING.md](CONTRIBUTING.md)
dosyasına bakın. Tüm iletişim ve dokümantasyon dili Türkçe, kod isimlendirmesi
İngilizcedir.

### Lisans

[MIT](LICENSE)

---

## English Summary

A KVKK/GDPR-compliant, open-source parser for fixed-width segment text. It
splits raw text into `GGxx` segments, parses each with a dedicated parser
(`GGOH`, `GGSS`, `GGTK`), and exposes the result as JSON through a small Flask
app. All logs pass through a PII masking filter, and no raw segment data is
ever logged.

```bash
uv sync
uv run python main.py   # http://127.0.0.1:5000
uv run pytest -q
```

Licensed under the [MIT License](LICENSE).
