"""KVKK/GDPR uyumlu kişisel veri (PII) maskeleme yardımcıları.

Bu modül, loglara veya dış servislere gönderilecek metinlerdeki kişisel
verileri yer tutucularla maskeler. Amaç, açık metin kişisel verinin
hiçbir çıktı kanalına sızmamasıdır.

KVKK Notu:
    Bu modülün kendisi kişisel veri işler; maskeleme yapılmadan hiçbir
    metin loglanmamalı veya dış API'ye gönderilmemelidir
    
"""

from __future__ import annotations

import logging
import re
from typing import Final

logger = logging.getLogger(__name__)

#: T.C. Kimlik Numarası deseni (11 hane, 0 ile başlamaz).
TCKN_PATTERN: Final[re.Pattern[str]] = re.compile(r"\b[1-9]\d{10}\b")
#: E-posta adresi deseni.
EMAIL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.IGNORECASE
)
#: Türkiye telefon numarası deseni (+90 5xx ..., 05xx ..., 5xx ...).
PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<!\d)(?:\+?90[\s-]?)?0?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}(?!\d)"
)
#: IPv4 adresi deseni.
IPV4_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)
#: IBAN deseni (TR + 24 hane).
IBAN_PATTERN: Final[re.Pattern[str]] = re.compile(r"\bTR\d{24}\b", re.IGNORECASE)


def mask_text(text: str) -> str:
    """Metindeki yaygın kişisel verileri yer tutucularla maskeler.

    Sırasıyla IBAN, TCKN, e-posta, telefon ve IPv4 desenleri maskelenir.
    Maskeleme sırası önemlidir: IBAN ve TCKN gibi uzun sayısal desenler,
    telefon deseninden önce işlenmelidir.

    Args:
        text (str): Maskelenecek metin.

    Returns:
        str: Kişisel verileri ``<IBAN_1>``, ``<TCKN_1>``, ``<EMAIL_1>``,
        ``<PHONE_1>``, ``<IP_1>`` gibi yer tutucularla değiştirilmiş metin.

    Raises:
        TypeError: ``text`` metin değilse.

    KVKK Notu:
        Bu fonksiyon, dış servislere veya loglara gönderilecek tüm serbest
        metinler için zorunludur.
    """
    if not isinstance(text, str):
        raise TypeError("text metin (str) olmalıdır.")

    masked = text
    for etiket, desen in (
        ("IBAN", IBAN_PATTERN),
        ("TCKN", TCKN_PATTERN),
        ("EMAIL", EMAIL_PATTERN),
        ("PHONE", PHONE_PATTERN),
        ("IP", IPV4_PATTERN),
    ):
        sayac = 0

        def _degistir(eslesme: re.Match[str], etiket: str = etiket) -> str:
            nonlocal sayac
            sayac += 1
            return f"<{etiket}_{sayac}>"

        masked = desen.sub(_degistir, masked)
    return masked


def mask_value(value: object) -> object:
    """Tek bir değeri maskeler; metin değilse olduğu gibi döndürür.

    Args:
        value (object): Maskelenecek değer.

    Returns:
        object: Metin ise maskelenmiş hâli, değilse aynı değer.

    KVKK Notu:
        Log kayıtlarındaki tüm serbest metin alanları bu fonksiyondan
        geçirilmelidir.
    """
    if isinstance(value, str):
        return mask_text(value)
    return value


class PIIMaskingFilter(logging.Filter):
    """Log kayıtlarındaki kişisel verileri maskeleyen logging filtresi.

    Filtre, kaydın mesajını ve ``extra`` ile eklenen metin alanlarını
    maskeler. Böylece hiçbir handler açık metin kişisel veri yazmaz.

    Attributes:
        alanlar (tuple[str, ...]): Maskelenecek ek (extra) alan adları.
    """

    def __init__(self, alanlar: tuple[str, ...] = ("correlation_id",)) -> None:
        """Filtreyi hazırlar.

        Args:
            alanlar (tuple[str, ...]): Ek olarak maskelenecek alan adları.
        """
        super().__init__()
        self.alanlar = alanlar

    def filter(self, record: logging.LogRecord) -> bool:
        """Log kaydını yerinde maskeleyerek geçişine izin verir.

        Args:
            record (logging.LogRecord): İşlenecek log kaydı.

        Returns:
            bool: Her zaman ``True`` (kayıt engellenmez, yalnızca maskelenir).
        """
        try:
            if isinstance(record.msg, str):
                record.msg = mask_text(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        anahtar: mask_value(deger)
                        for anahtar, deger in record.args.items()
                    }
                else:
                    record.args = tuple(mask_value(arg) for arg in record.args)
            for alan in self.alanlar:
                if hasattr(record, alan):
                    setattr(record, alan, mask_value(getattr(record, alan)))
        except Exception:  # noqa: BLE001 - loglama asla uygulamayı düşürmemeli
            logger.debug("Log kaydı maskelenirken hata oluştu, kayıt olduğu gibi geçti.")
        return True
