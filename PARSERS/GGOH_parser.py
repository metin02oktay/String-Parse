"""GGOH (Çıktı Başlığı) segmenti parser'ı.

GGOH segmenti, yanıtın başlık bilgilerini taşır. Referans numaraları, hata
tipi ve mesaj kodu bu segmentte yer alır.

KVKK Notu:
    Bu segment referans numaraları gibi takip edilebilir kimlikler içerir.
    Bu değerler loglara açık metin olarak yazılmamalıdır
"""

from __future__ import annotations

import logging
from typing import Any

from .base_parser import BaseSegmentParser

logger = logging.getLogger(__name__)

#: Hata tipi kodlarının Türkçe açıklamaları.
HATA_TIPLERI: dict[str, str] = {
    "0": "girdi onaylandı",
    "1": "girdi hatası, girdiyi düzelt",
    "2": "sistem hatası, daha sonra tekrar dene",
    "3": "sistem hatası, sistem yöneticisiyle temas kur",
    "4": "Uyarı",
}


class GGOHParser(BaseSegmentParser):
    """GGOH (Çıktı Başlığı) segmentini parse eden sınıf.

    Sistem tarafından hiçbir veri sağlanmazsa hata tipi ``0`` (girdi onaylandı)
    ve mesaj kodu ``999`` (veri yok) olarak oluşur. Bu gibi durumlarda çıktı
    başlığının ardından Çıktı Sonu Bilgileri (GGOE) segmenti gelir.

    Attributes:
        raw_txt (str): Segmenti içeren ham metin.
        index (int): Okuma imlecinin konumu.
    """

    SEGMENT_ID = "GGOH"
    HEADER_LENGTH = 12

    def ayirma_islemi(self) -> None:
        """Ham metni sırasına göre alanlara ayırır.

        Alan sırası: kimlik, uzunluk, sıralama, versiyon, sıkıştırma
        göstergesi, ayraç karakter, alt ayraç karakter, hata tipi,
        mesaj kodu, referans no, çıktı referans no.
        """
        self.kimlik()
        self.segment_uzunlugu_()
        self.segment_siralamasi_()
        self.segment_versiyon_no_()
        self.segment_zip_()
        self.ayrac_karakter_()
        self.alt_ayrac_karakter_()
        self.segment_hata()
        self.mesaj_kodu_()
        self.sorgu_ref_no_()
        self.cikti_ref_no_()

    def segment_zip_(self) -> str:
        """Sıkıştırılmış veri göstergesini okur.

        Bu gösterge, sonraki çıktı segmentlerinin sıkıştırılmış olup
        olmadığını belirtir. GGOH segmentinin kendisi asla sıkıştırılmaz.

        Returns:
            str: ``"0"`` sıkıştırılmamış, ``"1"`` sıkıştırılmış.
        """
        self.segment_zip = self._oku(2, "Segment Sıkıştırılması")
        return self.segment_zip

    def ayrac_karakter_(self) -> str:
        """Segmentler sıkıştırıldığında alanları ayıran karakteri okur.

        Returns:
            str: Ayraç karakter.
        """
        self.ayrac_karakter = self._oku(1, "Ayraç Karakter")
        return self.ayrac_karakter

    def alt_ayrac_karakter_(self) -> str:
        """Sıkıştırılmış veri alanında kullanılan alt ayraç karakterini okur.

        Returns:
            str: Alt ayraç karakter.
        """
        self.alt_ayrac_karakter = self._oku(1, "Alt Ayraç Karakter")
        return self.alt_ayrac_karakter

    def segment_hata(self) -> dict[str, str]:
        """Hata tipi alanını okur ve açıklamasıyla eşleştirir.

        Girdi işleminin onaylandığını ya da işlem sırasında bir hata
        olup olmadığını belirtir. Tüm hata durumlarında detay için mesaj
        kodu alanı incelenmelidir.

        Returns:
            dict[str, str]: Hata kodu -> Türkçe açıklama eşlemesi.
        """
        kod = self._oku(1, "Hata Tipi")
        self.hata_kodu: dict[str, str] = {}
        if kod in HATA_TIPLERI:
            self.hata_kodu[kod] = HATA_TIPLERI[kod]
        else:
            logger.warning("Bilinmeyen GGOH hata tipi kodu alındı.")
            self.hata_kodu[kod] = "bilinmeyen hata tipi"
        return self.hata_kodu

    def mesaj_kodu_(self) -> str:
        """Oluşan hatanın detayını belirten mesaj kodunu okur.

        Returns:
            str: Üç karakterlik mesaj kodu.
        """
        self.mesaj_kodu = self._oku(3, "Mesaj Kodu")
        return self.mesaj_kodu

    def sorgu_ref_no_(self) -> str:
        """Üyenin Girdi Başlığı (GGIH) bilgilerinde tanımladığı referans numarasını okur.

        Returns:
            str: 20 karakterlik referans numarası.
        """
        self.sorgu_ref_no = self._oku(20, "Sorgu Ref No")
        return self.sorgu_ref_no

    def cikti_ref_no_(self) -> str:
        """Sistem tarafından üretilen çıktı referans numarasını okur.
        Bu numara, işleme atıfta bulunmak amacıyla sonraki bildirimlerde
        kullanılabilir.

        Returns:
            str: 20 karakterlik çıktı referans numarası.
        """
        self.cikti_ref_no = self._oku(20, "Çıktı Ref No")
        return self.cikti_ref_no

    def get_data(self) -> dict[str, dict[str, Any]]:
        """Segment alanlarını açıklamalarıyla birlikte döndürür.

        Returns:
            dict[str, dict[str, Any]]: Alan adı -> ``{"aciklama", "deger"}`` eşlemesi.
        """
        veri = self._baslik_verisi()
        veri.update(
            {
                "Segment Sıkıştırılması": {
                    "aciklama": self.segment_zip_.__doc__,
                    "deger": self.segment_zip,
                },
                "Ayraç Karakter": {
                    "aciklama": self.ayrac_karakter_.__doc__,
                    "deger": self.ayrac_karakter,
                },
                "Alt Ayraç Karakter": {
                    "aciklama": self.alt_ayrac_karakter_.__doc__,
                    "deger": self.alt_ayrac_karakter,
                },
                "Segment Hatası": {
                    "aciklama": self.segment_hata.__doc__,
                    "deger": str(self.hata_kodu),
                },
                "Mesaj Kodu": {
                    "aciklama": self.mesaj_kodu_.__doc__,
                    "deger": self.mesaj_kodu,
                },
                "Sorgu Ref No": {
                    "aciklama": self.sorgu_ref_no_.__doc__,
                    "deger": self.sorgu_ref_no,
                },
                "Çıktı Ref No": {
                    "aciklama": self.cikti_ref_no_.__doc__,
                    "deger": self.cikti_ref_no,
                },
            }
        )
        return veri


if __name__ == "__main__":
    # Sentetik örnek: 4 + 4 + 2 + 2 + 2 + 1 + 1 + 1 + 3 + 20 + 20 = 60 karakter
    ornek = (
        "GGOH0060"
        + "01"
        + "01"
        + "00"
        + "|"
        + "|"
        + "0"
        + "000"
        + "S" * 20
        + "C" * 20
    )
    print(GGOHParser(ornek).get_data())
