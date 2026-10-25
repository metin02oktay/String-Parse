"""GGSS (Özet Bilgi) segmenti parser'ı.

Özet veriler istenmişse, bu segment özet setindeki ilk segment olur. Özet
setlerinin sayısı, bulunan eşleşme seviyelerinin tipine bağlıdır (aynı kişi,
aynı grup, ortaklıklar, rumuzlar vb.). Bu segmentlerin her birinin ardından,
döndürülen verilere bağlı olarak bir takım veri özeti segmentleri gelir.

KVKK Notu:
    Başvuru referans numarası takip edilebilir bir kimliktir; loglara açık
    metin olarak yazılmamalıdır.
"""

from __future__ import annotations

from typing import Any

from .base_parser import BaseSegmentParser


class GGSSParser(BaseSegmentParser):
    """GGSS (Özet Bilgi) segmentini parse eden sınıf.

    Attributes:
        raw_txt (str): Segmenti içeren ham metin.
        index (int): Okuma imlecinin konumu.
    """

    SEGMENT_ID = "GGSS"
    HEADER_LENGTH = 12

    def ayirma_islemi(self) -> None:
        """Ham metni sırasına göre alanlara ayırır.

        Alan sırası: kimlik, uzunluk, sıralama, versiyon, rezerve (2),
        başvuru referans no, benzerlik oranı, özet bilgiler, önemli uyarılar.        """
        self.kimlik()
        self.segment_uzunlugu_()
        self.segment_siralamasi_()
        self.segment_versiyon_no_()
        self.rezerve_al(2)
        self.basvuru_ref_no_()
        self.benzerlik_orani_()
        self.ozet_bilgiler_()
        self.onemli_uyarilar_()

    def basvuru_ref_no_(self) -> str:
        """Üyenin Girdi Başlığı (GGIH) bilgilerinde belirttiği referans numarasını okur.

        Returns:
            str: 20 karakterlik başvuru referans numarası.
        """
        self.basvuru_ref_no = self._oku(20, "Başvuru Referans No")
        return self.basvuru_ref_no

    def benzerlik_orani_(self) -> str:
        """Başvuru sahibine ait verinin döndürülme nedenini (eşleşme seviyesi) okur.
        Returns:
            str: Tek karakterlik eşleşme seviyesi kodu.
        """
        self.benzerlik_orani = self._oku(1, "Benzerlik Oranı")
        return self.benzerlik_orani

    def ozet_bilgiler_(self) -> str:
        """Özetleme sonucunda dönen özet veri göstergelerini okur.

        20 hanelik set; ``0`` = hiçbir veri bulunmadı, ``1`` = veri bulundu,
        ``2`` = veri gerekli değil. Kalan haneler ileride kullanılmak üzere
        rezerve edilmiştir.

        Returns:
            str: 20 karakterlik özet bilgi göstergeleri.
        """
        self.ozet_bilgiler = self._oku(20, "Özet Bilgiler")
        return self.ozet_bilgiler

    def onemli_uyarilar_(self) -> str:
        """Uyarı üreten verilerin varlığını gösteren göstergeleri okur.

        20 göstergelik set; ``0`` = uyarı yok, ``1`` = uyarı var.

        Returns:
            str: 20 karakterlik önemli uyarı göstergeleri.
        """
        self.onemli_uyarilar = self._oku(20, "Önemli Uyarılar")
        return self.onemli_uyarilar

    def get_data(self) -> dict[str, dict[str, Any]]:
        """Segment alanlarını açıklamalarıyla birlikte döndürür.

        Returns:
            dict[str, dict[str, Any]]: Alan adı -> ``{"aciklama", "deger"}`` eşlemesi.
        """
        veri = self._baslik_verisi()
        veri.update(
            {
                "Başvuru Referans No": {
                    "aciklama": self.basvuru_ref_no_.__doc__,
                    "deger": self.basvuru_ref_no,
                },
                "Benzerlik Oranı": {
                    "aciklama": self.benzerlik_orani_.__doc__,
                    "deger": self.benzerlik_orani,
                },
                "Özet Bilgiler": {
                    "aciklama": self.ozet_bilgiler_.__doc__,
                    "deger": self.ozet_bilgiler,
                },
                "Önemli Uyarılar": {
                    "aciklama": self.onemli_uyarilar_.__doc__,
                    "deger": self.onemli_uyarilar,
                },
            }
        )
        return veri


if __name__ == "__main__":
    # Sentetik örnek: 4 + 4 + 2 + 2 + 2 + 20 + 1 + 20 + 20 = 75 karakter
    ornek = "GGSS0075" + "01" + "01" + "  " + "B" * 20 + "1" + "1" * 20 + "0" * 20
    print(GGSSParser(ornek).get_data())
