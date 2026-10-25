# Katkı Rehberi

Bu projeye katkı sağladığınız için teşekkürler. Katkı öncesinde aşağıdaki
kuralları okuyun.


## Geliştirme Ortamı

```bash
uv sync
uv run pytest -q
uv run ruff check .
```

## Kod Standartları

- Tüm fonksiyon parametreleri ve dönüş değerleri tip ipuçlarıyla belirtilmelidir.
- `print()` kullanılmaz; merkezi logger (`log_yapisi.get_logger`) kullanılır.
- Yeni segment parser'ları `BaseSegmentParser` tabanından türetilmelidir.
- Yeni özellikler için `tests/` altında birim testi eklenmelidir.

## Gizlilik Kuralları (Zorunlu)

- Gerçek kişisel veri, API anahtarı veya şifre commit edilmez.
- Testlerde yalnızca sentetik veri kullanılır.
- Loglara ham segment verisi yazılmaz.


## Pull Request Süreci

1. Değişikliklerinizi konuya özel bir dalda geliştirin.
2. `.github/PULL_REQUEST_TEMPLATE.md` şablonunu doldurun.
3. CI (ruff + pytest) yeşil olmalıdır.
