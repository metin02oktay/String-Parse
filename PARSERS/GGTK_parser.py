"""GGTK (Dönem Bazlı Veri Geçmişi) segmenti parser'ı.

GGTK segmenti, bir kayda ait dönem bazlı özet verileri içerir. Segment bir
başlık, bir kayıt referans numarası, dönem adedi ve ardından gelen dönem
bloklarından oluşur.

KVKK Notu:
    Kayıt referans numarası ve tutar alanları kişisel veri niteliğindedir.
    Bu değerler loglara açık metin olarak yazılmamalıdır
"""

from __future__ import annotations

import logging
from typing import Any

from .base_parser import BaseSegmentParser, FixedWidthReader, SegmentParseError

logger = logging.getLogger(__name__)

#: Tek bir dönem bloğunun toplam uzunluğu.
DONEM_UZUNLUGU = 63


class DonemParser(FixedWidthReader):
    """GGTK segmenti altındaki tek bir dönem bloğunu parse eden sınıf.

    Attributes:
        raw_txt (str): Dönem bloğunu içeren ham metin.
        index (int): Okuma imlecinin konumu.
    """

    SEGMENT_ID = "GGTK"

    def __init__(self, raw_txt: str) -> None:
        """Dönem bloğunu hazırlar ve ayrıştırır.

        Args:
            raw_txt (str): 63 karakterlik dönem bloğu.

        Raises:
            SegmentParseError: Blok beklenen uzunlukta değilse.
        """
        super().__init__(raw_txt)
        if len(raw_txt) < DONEM_UZUNLUGU:
            raise SegmentParseError(
                f"Dönem bloğu {DONEM_UZUNLUGU} karakter olmalı, gelen {len(raw_txt)}.",
                self.SEGMENT_ID,
                "Dönem",
            )
        self.ayirma_islemi()

    def ayirma_islemi(self) -> None:
        """Dönem bloğunu sırasına göre alanlara ayırır."""
        self.donem_()
        self.eko_aylik_()
        self.eko_gunluk_()
        self.guncel_durum_gunluk_()
        self.tutar_gostergesi_()
        self.toplam_tutar_()
        self.hesaplama_esas_tutar_()
        self.kalan_toplam_tutar_()
        self.aylik_donem_tutari_()
        self.kaydin_durumu_()
        self.gecikme_gun_sayisi_()
        self.en_buyuk_gecikme_gun_sayisi_()
        self.donem_odeme_orani_()

    def donem_(self) -> str:
        """Verilerin ait olduğu dönem bilgisini okur.

        Returns:
            str: 6 karakterlik dönem (örn. ``"202501"``).
        """
        self.donem = self._oku(6, "Dönem")
        return self.donem

    def eko_aylik_(self) -> str:
        """İlgili dönemdeki en kötü durum kodunu (aylık) okur.

        Returns:
            str: Tek karakterlik durum kodu.
        """
        self.eko_aylik = self._oku(1, "En Kötü Durum (Aylık)")
        return self.eko_aylik

    def eko_gunluk_(self) -> str:
        """İlgili dönemde vadesi geçmiş ancak kapatılmamış tutarı okur.

        Günlük bildirim dönemine geçiş öncesinde kapatılmış ve geçiş
        sonrasında güncellenmemiş kayıtlarda bu alan boş döner.

        Returns:
            str: 9 karakterlik gecikmedeki tutar.
        """
        self.eko_gunluk = self._oku(9, "Gecikmedeki Tutar (Günlük)")
        return self.eko_gunluk

    def guncel_durum_gunluk_(self) -> str:
        """Kaydın en güncel durum kodunu (günlük) okur.

        Returns:
            str: Tek karakterlik durum kodu.
        """
        self.guncel_durum_gunluk = self._oku(1, "Güncel Durum (Günlük)")
        return self.guncel_durum_gunluk

    def tutar_gostergesi_(self) -> str:
        """Toplam tutarın alacak mı yükümlülük mü olduğunu gösteren alanı okur.

        Returns:
            str: Tek karakterlik tutar göstergesi.
        """
        self.tutar_gostergesi = self._oku(1, "Tutar Göstergesi")
        return self.tutar_gostergesi

    def toplam_tutar_(self) -> str:
        """İlgili dönemdeki toplam tutarı okur.

        Güncelleme tarihindeki toplam tutarı veya kalan anapara tutarını
        belirtir.

        Returns:
            str: 9 karakterlik toplam tutar.
        """
        self.toplam_tutar = self._oku(9, "Toplam Tutar")
        return self.toplam_tutar

    def hesaplama_esas_tutar_(self) -> str:
        """Hesaplamaya esas olan tutarı okur.

        Yalnızca belirli kayıt türleri için kullanılır.

        Returns:
            str: 9 karakterlik hesaplamaya esas tutar.
        """
        self.hesaplama_esas_tutar = self._oku(9, "Hesaplamaya Esas Tutar")
        return self.hesaplama_esas_tutar

    def kalan_toplam_tutar_(self) -> str:
        """Gelecek dönemlere ait toplam tutarı okur.

        Returns:
            str: 9 karakterlik kalan toplam tutar.
        """
        self.kalan_toplam_tutar = self._oku(9, "Kalan Toplam Tutar")
        return self.kalan_toplam_tutar

    def aylik_donem_tutari_(self) -> str:
        """Aylık dönem tutarını okur.

        Değişken tutarlı kayıtlarda son hareketin tutarını, haftalık
        hareketlerde haftalık tutarın 4 ile çarpımını belirtir. Düzenli
        hareketi olmayan kayıtlarda boş döner.

        Returns:
            str: 9 karakterlik aylık dönem tutarı.
        """
        self.aylik_donem_tutari = self._oku(9, "Aylık Dönem Tutarı")
        return self.aylik_donem_tutari

    def kaydin_durumu_(self) -> str:
        """Kaydın durumunu (açık, hareketsiz, kapanmış, takipte vb.) okur.

        Returns:
            str: 2 karakterlik durum kodu.
        """
        self.kaydin_durumu = self._oku(2, "Kaydın Durumu")
        return self.kaydin_durumu

    def gecikme_gun_sayisi_(self) -> str:
        """Dönem içindeki en büyük gecikme gün sayısını okur.

        Returns:
            str: 2 karakterlik gecikme gün sayısı.
        """
        self.gecikme_gun_sayisi = self._oku(2, "Dönem İçi En Büyük Gecikme Gün Sayısı")
        return self.gecikme_gun_sayisi

    def en_buyuk_gecikme_gun_sayisi_(self) -> str:
        """Kayıt gecikmedeyse gecikmede olduğu gün sayısını okur.

        Returns:
            str: 2 karakterlik gecikme gün sayısı.
        """
        self.en_buyuk_gecikme_gun_sayisi = self._oku(2, "Gecikme Gün Sayısı")
        return self.en_buyuk_gecikme_gun_sayisi

    def donem_odeme_orani_(self) -> str:
        """Dönem ödeme oranını okur.

        Returns:
            str: 3 karakterlik dönem ödeme oranı.
        """
        self.donem_odeme_orani = self._oku(3, "Dönem Ödeme Oranı")
        return self.donem_odeme_orani

    def get_data(self) -> dict[str, dict[str, Any]]:
        """Dönem alanlarını açıklamalarıyla birlikte döndürür.

        Returns:
            dict[str, dict[str, Any]]: Alan adı -> ``{"aciklama", "deger"}`` eşlemesi.
        """
        return {
            "Dönem": {"aciklama": self.donem_.__doc__, "deger": self.donem},
            "En Kötü Durum (Aylık)": {
                "aciklama": self.eko_aylik_.__doc__,
                "deger": self.eko_aylik,
            },
            "Gecikmedeki Tutar (Günlük)": {
                "aciklama": self.eko_gunluk_.__doc__,
                "deger": self.eko_gunluk,
            },
            "Güncel Durum (Günlük)": {
                "aciklama": self.guncel_durum_gunluk_.__doc__,
                "deger": self.guncel_durum_gunluk,
            },
            "Tutar Göstergesi": {
                "aciklama": self.tutar_gostergesi_.__doc__,
                "deger": self.tutar_gostergesi,
            },
            "Toplam Tutar": {
                "aciklama": self.toplam_tutar_.__doc__,
                "deger": self.toplam_tutar,
            },
            "Hesaplamaya Esas Tutar": {
                "aciklama": self.hesaplama_esas_tutar_.__doc__,
                "deger": self.hesaplama_esas_tutar,
            },
            "Kalan Toplam Tutar": {
                "aciklama": self.kalan_toplam_tutar_.__doc__,
                "deger": self.kalan_toplam_tutar,
            },
            "Aylık Dönem Tutarı": {
                "aciklama": self.aylik_donem_tutari_.__doc__,
                "deger": self.aylik_donem_tutari,
            },
            "Kaydın Durumu": {
                "aciklama": self.kaydin_durumu_.__doc__,
                "deger": self.kaydin_durumu,
            },
            "Dönem İçi En Büyük Gecikme Gün Sayısı": {
                "aciklama": self.gecikme_gun_sayisi_.__doc__,
                "deger": self.gecikme_gun_sayisi,
            },
            "Gecikme Gün Sayısı": {
                "aciklama": self.en_buyuk_gecikme_gun_sayisi_.__doc__,
                "deger": self.en_buyuk_gecikme_gun_sayisi,
            },
            "Dönem Ödeme Oranı": {
                "aciklama": self.donem_odeme_orani_.__doc__,
                "deger": self.donem_odeme_orani,
            },
        }


class GGTKParser(BaseSegmentParser):
    """GGTK (Dönem Bazlı Veri Geçmişi) segmentini parse eden sınıf.

    Attributes:
        raw_txt (str): Segmenti içeren ham metin.
        index (int): Okuma imlecinin konumu.
        donemler (list[DonemParser]): Parse edilen dönem blokları.
    """

    SEGMENT_ID = "GGTK"
    HEADER_LENGTH = 12

    def ayirma_islemi(self) -> None:
        """Segmenti başlık, referans no, dönem adedi ve dönem bloklarına ayırır.

        Raises:
            SegmentParseError: Dönem adedi sayısal değilse veya dönem blokları
                için yeterli veri yoksa.
        """
        self.kimlik()
        self.segment_uzunlugu_()
        self.segment_siralamasi_()
        self.segment_versiyon_no_()
        self.ref_no_()
        self.donem_adedi_()
        self.donemler_()

    def ref_no_(self) -> str:
        """Kaydın tekil referans numarasını okur.

        Returns:
            str: 14 karakterlik referans numarası.
        """
        self.ref_no = self._oku(14, "Referans No")
        return self.ref_no

    def donem_adedi_(self) -> int:
        """Segment içinde iletilecek dönem sayısını okur.

        Returns:
            int: Dönem adedi (en fazla 12).

        Raises:
            SegmentParseError: Dönem adedi sayısal değilse.
        """
        ham = self._oku(2, "Dönem Adedi")
        self.donem_adedi = ham
        try:
            return int(ham)
        except ValueError as hata:
            raise SegmentParseError(
                f"Dönem adedi sayısal olmalı, gelen '{ham}'.",
                self.SEGMENT_ID,
                "Dönem Adedi",
            ) from hata

    def donemler_(self) -> list[DonemParser]:
        """Dönem adedine göre dönem bloklarını sırayla parse eder.

        Returns:
            list[DonemParser]: Parse edilen dönem blokları.

        Raises:
            SegmentParseError: Kalan veri dönem bloklarını karşılamıyorsa.
        """
        adet = int(self.donem_adedi)
        self.donemler: list[DonemParser] = []
        for sira in range(adet):
            kalan = len(self.raw_txt) - self.index
            if kalan < DONEM_UZUNLUGU:
                raise SegmentParseError(
                    f"{sira + 1}. dönem bloğu için {DONEM_UZUNLUGU} karakter "
                    f"bekleniyordu, kalan {kalan}.",
                    self.SEGMENT_ID,
                    "Dönem",
                )
            blok = self.raw_txt[self.index : self.index + DONEM_UZUNLUGU]
            self.index += DONEM_UZUNLUGU
            self.donemler.append(DonemParser(blok))
        return self.donemler

    def get_data(self) -> dict[str, Any]:
        """Segment alanlarını ve dönem bloklarını açıklamalarıyla döndürür.

        Returns:
            dict[str, Any]: Başlık alanları, referans no, dönem adedi ve
            ``"Dönemler"`` anahtarı altında dönem listesi.
        """
        veri: dict[str, Any] = self._baslik_verisi()
        veri.update(
            {
                "Referans No": {
                    "aciklama": self.ref_no_.__doc__,
                    "deger": self.ref_no,
                },
                "Dönem Adedi": {
                    "aciklama": self.donem_adedi_.__doc__,
                    "deger": self.donem_adedi,
                },
                "Dönemler": {
                    "aciklama": self.donemler_.__doc__,
                    "deger": [donem.get_data() for donem in self.donemler],
                },
            }
        )
        return veri


if __name__ == "__main__":
    # Sentetik örnek: 12 (başlık) + 14 (ref no) + 2 (dönem adedi) + 63 (tek dönem)
    donem = "202501" + "0" + "0" * 9 + "0" + "0" + "0" * 9 * 4 + "00" + "00" + "00" + "000"
    ornek = "GGTK0091" + "01" + "01" + "R" * 14 + "01" + donem
    print(GGTKParser(ornek).get_data())
