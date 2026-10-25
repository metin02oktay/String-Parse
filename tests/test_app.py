"""Flask uygulaması ve segment eşleştirme testleri.

Tüm örnek veriler sentetiktir; gerçek kişisel veri içermez.
"""

from __future__ import annotations

import pytest

from main import create_app, esletirme, replace_range

GGOH_ORNEK = "GGOH0060  01    0000                    20250729000752974892"
GGSS_ORNEK = "GGSS00750101                      011                  1                   "


@pytest.fixture()
def istemci():
    """Test için Flask test istemcisi üretir.

    Yields:
        flask.testing.FlaskClient: Test istemcisi.
    """
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


class TestReplaceRange:
    """``replace_range`` fonksiyonu davranışları."""

    def test_aralik_degistirilir(self) -> None:
        """Belirtilen aralık verilen karakterle doldurulmalıdır."""
        assert replace_range("abcdef", 1, 4) == "a___ef"

    def test_ozel_karakter_kullanilir(self) -> None:
        """Verilen karakter aralığa yazılmalıdır."""
        assert replace_range("abcdef", 0, 2, "*") == "**cdef"

    def test_gecersiz_aralik_hata_verir(self) -> None:
        """Geçersiz aralık ``ValueError`` fırlatmalıdır."""
        with pytest.raises(ValueError):
            replace_range("abc", 2, 1)

    def test_cok_karakterli_dolgu_hata_verir(self) -> None:
        """Birden fazla karakterli dolgu ``ValueError`` fırlatmalıdır."""
        with pytest.raises(ValueError):
            replace_range("abc", 0, 1, "**")


class TestEsletirme:
    """``esletirme`` fonksiyonu davranışları."""

    def test_tek_segment_parse_edilir(self) -> None:
        """Tek segment içeren metin doğru anahtarla dönmelidir."""
        sonuc = esletirme(GGOH_ORNEK)

        assert list(sonuc) == ["GGOH"]
        assert sonuc["GGOH"]["Segment Kimliği"]["deger"] == "GGOH"

    def test_ayni_segment_numaralanir(self) -> None:
        """Aynı kimlikten iki segment geldiğinde anahtarlar benzersiz olmalıdır."""
        sonuc = esletirme(GGOH_ORNEK + GGSS_ORNEK + GGSS_ORNEK)

        assert set(sonuc) == {"GGOH", "GGSS", "GGSS_1"}

    def test_bilinmeyen_segment_atlanir(self) -> None:
        """Tanımlı parser'ı olmayan segment sonuca eklenmemelidir."""
        sonuc = esletirme("GGXX0012" + "01" + "01" + "0000")

        assert sonuc == {}

    def test_gecersiz_uzunluk_atlanir(self) -> None:
        """Uzunluk alanı sayısal değilse segment atlanmalıdır."""
        assert esletirme("GGOHabcd" + "x" * 20) == {}

    def test_bos_metin_bos_sozluk_doner(self) -> None:
        """Segment içermeyen metin boş sözlük döndürmelidir."""
        assert esletirme("") == {}

    def test_metin_olmayan_girdi_hata_verir(self) -> None:
        """Metin olmayan girdi ``TypeError`` fırlatmalıdır."""
        with pytest.raises(TypeError):
            esletirme(None)  # type: ignore[arg-type]


class TestRotalar:
    """HTTP rotaları davranışları."""

    def test_ana_sayfa_acilir(self, istemci) -> None:
        """Ana sayfa 200 dönmelidir."""
        yanit = istemci.get("/")

        assert yanit.status_code == 200
        assert b"Segment Parser" in yanit.data

    def test_saglik_kontrolu(self, istemci) -> None:
        """Sağlık kontrolü ``ok`` dönmelidir."""
        yanit = istemci.get("/health")

        assert yanit.status_code == 200
        assert yanit.get_json() == {"status": "ok"}

    def test_parse_et_basarili(self, istemci) -> None:
        """Geçerli metin parse edilip JSON dönmelidir."""
        yanit = istemci.post("/parse_et", json={"raw_text": GGOH_ORNEK})

        assert yanit.status_code == 200
        assert "GGOH" in yanit.get_json()

    def test_parse_et_bos_veri_reddedilir(self, istemci) -> None:
        """Boş metin 400 ile reddedilmelidir."""
        yanit = istemci.post("/parse_et", json={"raw_text": "   "})

        assert yanit.status_code == 400
        assert "error" in yanit.get_json()

    def test_parse_et_gecersiz_json_reddedilir(self, istemci) -> None:
        """JSON olmayan gövde 400 ile reddedilmelidir."""
        yanit = istemci.post(
            "/parse_et", data="raw_text=abc", content_type="text/plain"
        )

        assert yanit.status_code == 400

    def test_parse_et_yanlis_metot(self, istemci) -> None:
        """GET isteği 405 dönmelidir."""
        assert istemci.get("/parse_et").status_code == 405
