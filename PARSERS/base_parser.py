"""Sabit uzunluklu segment parser'ları için ortak okuma altyapısı.

Bu modül, sabit uzunluklu segment metinlerini okuyan tüm parser'ların
(GGOH, GGSS, GGTK ...) paylaştığı imleç yönetimini, alan okuma mantığını
ve ortak başlık alanlarını tek yerde toplar. Böylece her parser aynı hata
davranışını ve aynı doğrulama kurallarını uygular.

KVKK Notu:
    Bu modül kişisel veri işlemez; yalnızca ham metni alanlara böler.
    Ham metin ve alan değerleri loglanmamalıdır
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class SegmentParseError(ValueError):
    """Segment verisi beklenen yapıya uymadığında fırlatılan hata.

    Attributes:
        segment_id (str): Hata alınan segmentin kimliği (örn. ``"GGOH"``).
        alan (str): Hatanın oluştuğu alan adı.
    """

    def __init__(self, mesaj: str, segment_id: str = "", alan: str = "") -> None:
        """Hata nesnesini oluşturur.

        Args:
            mesaj (str): Loga yazılacak açıklama.
            segment_id (str): İlgili segment kimliği.
            alan (str): İlgili alan adı.
        """
        self.segment_id = segment_id
        self.alan = alan
        tam_mesaj = mesaj
        if segment_id:
            tam_mesaj = f"[{segment_id}] {tam_mesaj}"
        if alan:
            tam_mesaj = f"{tam_mesaj} (alan: {alan})"
        super().__init__(tam_mesaj)


class FixedWidthReader:
    """Sabit uzunluklu metni imleç ile okuyan yardımcı sınıf.

    Attributes:
        raw_txt (str): Okunacak ham metin.
        index (int): Okuma imlecinin bulunduğu konum.
    """

    def __init__(self, raw_txt: str) -> None:
        """Okuyucuyu hazırlar.

        Args:
            raw_txt (str): Okunacak ham metin.

        Raises:
            TypeError: ``raw_txt`` metin değilse.
        """
        if not isinstance(raw_txt, str):
            raise TypeError("raw_txt metin (str) olmalıdır.")
        self.raw_txt: str = raw_txt
        self.index: int = 0

    def _oku(self, uzunluk: int, alan_adi: str) -> str:
        """İmleçten belirtilen uzunlukta metin okur ve imleci ilerletir.

        Args:
            uzunluk (int): Okunacak karakter sayısı.
            alan_adi (str): Hata mesajlarında görünecek alan adı.

        Returns:
            str: Okunan ham değer (kırpılmadan).

        Raises:
            SegmentParseError: Kalan veri istenen uzunluktan kısa ise.
        """
        bitis = self.index + uzunluk
        if bitis > len(self.raw_txt):
            raise SegmentParseError(
                f"'{alan_adi}' alanı için {uzunluk} karakter bekleniyordu, "
                f"kalan {max(len(self.raw_txt) - self.index, 0)} karakter.",
                getattr(self, "SEGMENT_ID", ""),
                alan_adi,
            )
        deger = self.raw_txt[self.index : bitis]
        self.index = bitis
        return deger

    def rezerve_al(self, uzunluk: int) -> None:
        """Açıklama yapmaksızın imleci belirtilen uzunluk kadar ilerletir.

        Args:
            uzunluk (int): İlerletilecek karakter sayısı.
        """
        self.index += uzunluk


class BaseSegmentParser(FixedWidthReader, ABC):
    """Sabit uzunluklu segmentleri parse eden sınıfların tabanı.

    Alt sınıflar ``SEGMENT_ID`` ve ``HEADER_LENGTH`` sınıf değişkenlerini
    tanımlamalı ve ``ayirma_islemi`` ile ``get_data`` metodlarını uygulamalıdır.

    Attributes:
        raw_txt (str): Parse edilecek ham segment metni.
        index (int): Okuma imlecinin bulunduğu konum.
    """

    #: Segmentin 4 karakterlik kimliği (örn. ``"GGOH"``).
    SEGMENT_ID: ClassVar[str] = ""
    #: Kimlik + uzunluk + sıralama + versiyon alanlarının toplam uzunluğu.
    HEADER_LENGTH: ClassVar[int] = 12

    def __init__(self, raw_txt: str) -> None:
        """Parser'ı hazırlar ve ayrıştırmayı başlatır.

        Args:
            raw_txt (str): Parse edilecek ham segment metni.

        Raises:
            TypeError: ``raw_txt`` metin değilse.
            SegmentParseError: Metin boşsa veya segment kimliği uyuşmuyorsa.
        """
        super().__init__(raw_txt)
        if not raw_txt:
            raise SegmentParseError("Boş segment verisi parse edilemez.", self.SEGMENT_ID)
        self._dogrula_baslik()
        self.ayirma_islemi()

    def _dogrula_baslik(self) -> None:
        """Segment kimliğini ve minimum uzunluğu doğrular.

        Raises:
            SegmentParseError: Kimlik uyuşmuyor veya veri başlık uzunluğundan kısa ise.
        """
        if self.SEGMENT_ID and not self.raw_txt.startswith(self.SEGMENT_ID):
            raise SegmentParseError(
                f"Beklenen segment kimliği '{self.SEGMENT_ID}', "
                f"gelen '{self.raw_txt[:4]}'.",
                self.SEGMENT_ID,
            )
        if len(self.raw_txt) < self.HEADER_LENGTH:
            raise SegmentParseError(
                f"Segment en az {self.HEADER_LENGTH} karakter olmalı, "
                f"gelen {len(self.raw_txt)}.",
                self.SEGMENT_ID,
            )

    @abstractmethod
    def ayirma_islemi(self) -> None:
        """Ham metni alanlara ayırır. Alt sınıflar tarafından uygulanır."""

    def kimlik(self) -> str:
        """Segmentin 4 karakterlik kimliğini okur.

        Returns:
            str: Segment kimliği (örn. ``"GGOH"``).
        """
        self.segment_kimlik = self._oku(4, "Segment Kimliği")
        return self.segment_kimlik

    def segment_uzunlugu_(self) -> int:
        """Segmentin toplam uzunluğunu okur.

        Returns:
            int: Segment uzunluğu.

        Raises:
            SegmentParseError: Uzunluk alanı sayısal değilse.
        """
        ham = self._oku(4, "Segment Uzunluğu")
        self.segment_uzunlugu = ham
        try:
            return int(ham)
        except ValueError as hata:
            raise SegmentParseError(
                f"Segment uzunluğu sayısal olmalı, gelen '{ham}'.",
                self.SEGMENT_ID,
                "Segment Uzunluğu",
            ) from hata

    def segment_siralamasi_(self) -> str:
        """Segment sıralama numarasını okur.

        Returns:
            str: İki karakterlik sıralama değeri (genellikle ``"01"``).
        """
        self.segment_siralamasi = self._oku(2, "Segment Sıralaması")
        return self.segment_siralamasi

    def segment_versiyon_no_(self) -> int:
        """Segment düzeninin versiyon numarasını okur.

        Returns:
            int: Versiyon numarası.

        Raises:
            SegmentParseError: Versiyon alanı sayısal değilse.
        """
        ham = self._oku(2, "Segment Versiyon No")
        self.segment_versiyon_no = ham
        try:
            return int(ham)
        except ValueError as hata:
            raise SegmentParseError(
                f"Segment versiyon no sayısal olmalı, gelen '{ham}'.",
                self.SEGMENT_ID,
                "Segment Versiyon No",
            ) from hata

    def _baslik_verisi(self) -> dict[str, dict[str, Any]]:
        """Tüm segmentlerde ortak olan başlık alanlarını sözlük olarak döndürür.

        Returns:
            dict[str, dict[str, Any]]: Alan adı -> ``{"aciklama", "deger"}`` eşlemesi.
        """
        return {
            "Segment Kimliği": {
                "aciklama": self.kimlik.__doc__,
                "deger": self.segment_kimlik,
            },
            "Segment Uzunluğu": {
                "aciklama": self.segment_uzunlugu_.__doc__,
                "deger": self.segment_uzunlugu,
            },
            "Segment Sıralaması": {
                "aciklama": self.segment_siralamasi_.__doc__,
                "deger": self.segment_siralamasi,
            },
            "Segment Versiyon No": {
                "aciklama": self.segment_versiyon_no_.__doc__,
                "deger": self.segment_versiyon_no,
            },
        }

    @abstractmethod
    def get_data(self) -> dict[str, dict[str, Any]]:
        """Parse edilen alanları açıklamalarıyla birlikte döndürür.

        Returns:
            dict[str, dict[str, Any]]: Alan adı -> ``{"aciklama", "deger"}`` eşlemesi.
        """

    def __str__(self) -> str:
        """Sınıfın okunabilir adını döndürür.

        Returns:
            str: Örn. ``"GGOHParser"``.
        """
        return type(self).__name__

    def __repr__(self) -> str:
        """Geliştirici dostu gösterimi döndürür.

        Returns:
            str: Sınıf adı, okunan karakter sayısı ve imleç konumu.
        """
        return f"{type(self).__name__}(uzunluk={len(self.raw_txt)}, index={self.index})"
