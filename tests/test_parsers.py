"""Parser'lar için birim testleri.

Tüm örnek veriler sentetiktir; gerçek kişisel veri içermez.
"""

from __future__ import annotations

import pytest

from PARSERS import GGOHParser, GGSSParser, GGTKParser, SegmentParseError
from PARSERS.GGTK_parser import DONEM_UZUNLUGU, DonemParser

GGOH_ORNEK = "GGOH0060  01    0000                    20250729000752974892"
GGSS_ORNEK = "GGSS00750101                      011                  1                   "


def _donem_blok() -> str:
    """63 karakterlik sentetik bir dönem bloğu üretir.

    Returns:
        str: Sentetik dönem bloğu.
    """
    return "202501" + "0" + "0" * 9 + "0" + "0" + "0" * 36 + "00" + "00" + "00" + "000"


def _ggtk_ornek(donem_adedi: int = 1) -> str:
    """Sentetik GGTK segmenti üretir.

    Args:
        donem_adedi (int): Eklenecek dönem bloğu sayısı.

    Returns:
        str: Sentetik GGTK segmenti.
    """
    govde = "R" * 14 + f"{donem_adedi:02d}" + _donem_blok() * donem_adedi
    return f"GGTK{12 + len(govde):04d}" + "01" + "01" + govde


class TestGGOHParser:
    """GGOH parser davranışları."""

    def test_alanlar_dogru_okunur(self) -> None:
        """Örnek segmentteki temel alanlar beklenen değerleri döndürmelidir."""
        veri = GGOHParser(GGOH_ORNEK).get_data()

        assert veri["Segment Kimliği"]["deger"] == "GGOH"
        assert veri["Segment Uzunluğu"]["deger"] == "0060"
        assert veri["Mesaj Kodu"]["deger"] == "000"
        assert veri["Çıktı Ref No"]["deger"] == "20250729000752974892"

    def test_hata_tipi_aciklamaya_cevrilir(self) -> None:
        """Hata tipi kodu Türkçe açıklamasına eşlenmelidir."""
        veri = GGOHParser(GGOH_ORNEK).get_data()

        assert "girdi onaylandı" in veri["Segment Hatası"]["deger"]

    def test_yanlis_kimlik_hata_verir(self) -> None:
        """Farklı segment kimliği ile parse edilirse hata fırlatılmalıdır."""
        with pytest.raises(SegmentParseError):
            GGOHParser("GGSS" + GGOH_ORNEK[4:])

    def test_kisa_veri_hata_verir(self) -> None:
        """Başlıktan kısa veri hata fırlatmalıdır."""
        with pytest.raises(SegmentParseError):
            GGOHParser("GGOH")

    def test_metin_olmayan_girdi_hata_verir(self) -> None:
        """Metin olmayan girdi ``TypeError`` fırlatmalıdır."""
        with pytest.raises(TypeError):
            GGOHParser(123)  # type: ignore[arg-type]


class TestGGSSParser:
    """GGSS parser davranışları."""

    def test_alanlar_dogru_okunur(self) -> None:
        """Örnek segmentteki alanlar beklenen değerleri döndürmelidir."""
        veri = GGSSParser(GGSS_ORNEK).get_data()

        assert veri["Segment Kimliği"]["deger"] == "GGSS"
        assert veri["Benzerlik Oranı"]["deger"] == "0"
        assert veri["Özet Bilgiler"]["deger"].startswith("11")
        assert len(veri["Önemli Uyarılar"]["deger"]) == 20

    def test_tum_alanlar_aciklama_icerir(self) -> None:
        """Her alan ``aciklama`` ve ``deger`` anahtarlarını içermelidir."""
        veri = GGSSParser(GGSS_ORNEK).get_data()

        for alan, icerik in veri.items():
            assert set(icerik) == {"aciklama", "deger"}, alan


class TestGGTKParser:
    """GGTK parser davranışları."""

    def test_donem_sayisi_kadar_blok_okunur(self) -> None:
        """Dönem adedi kadar dönem bloğu parse edilmelidir."""
        veri = GGTKParser(_ggtk_ornek(2)).get_data()

        assert veri["Dönem Adedi"]["deger"] == "02"
        assert len(veri["Dönemler"]["deger"]) == 2

    def test_donem_blogu_alanlari(self) -> None:
        """Dönem bloğu beklenen alanları içermelidir."""
        donem = DonemParser(_donem_blok()).get_data()

        assert donem["Dönem"]["deger"] == "202501"
        assert donem["Kaydın Durumu"]["deger"] == "00"

    def test_eksik_donem_blogu_hata_verir(self) -> None:
        """Dönem adedi veriyle uyuşmazsa hata fırlatılmalıdır."""
        eksik = "GGTK0030" + "01" + "01" + "R" * 14 + "02" + _donem_blok()
        with pytest.raises(SegmentParseError):
            GGTKParser(eksik)

    def test_donem_blogu_kisa_veri_hata_verir(self) -> None:
        """63 karakterden kısa dönem bloğu hata fırlatmalıdır."""
        with pytest.raises(SegmentParseError):
            DonemParser("2025")

    def test_donem_uzunlugu_sabiti(self) -> None:
        """Dönem bloğu uzunluğu 63 karakter olmalıdır."""
        assert DONEM_UZUNLUGU == 63
        assert len(_donem_blok()) == DONEM_UZUNLUGU
