"""Merkezi loglama yapılandırması.

Bu modül; renkli konsol çıktısı, günlük döndürülen dosya kaydı ve isteğe
bağlı OpenSearch gönderimi içeren tek bir logger üretir. Tüm log kayıtları
``privacy.PIIMaskingFilter`` üzerinden geçirilerek kişisel veriler maskelenir.

KVKK Notu:
    Loglara açık metin kişisel veri veya sır (şifre, API anahtarı)
    yazılmamalıdır. OpenSearch kimlik bilgileri yalnızca ortam
    değişkenlerinden okunur (bkz. ``AI/01_KVKK_AND_SECURITY.md``).
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from colorlog import ColoredFormatter

from privacy import PIIMaskingFilter

#: Varsayılan log formatı (dosya ve OpenSearch için).
DOSYA_FORMATI = (
    "%(asctime)s %(levelname)-8s %(name)s %(funcName)s() "
    "%(pathname)s L%(lineno)-4d %(message)s"
)
#: Konsol için renkli log formatı.
KONSOL_FORMATI = (
    "%(log_color)s[%(asctime)s %(name)-4s - %(levelname)-8s]%(reset)s "
    "%(white)s%(message)s"
)


class ExitOnCriticalHandler(logging.Handler):
    """CRITICAL seviyesinde log geldiğinde uygulamayı sonlandıran handler.

    Konsola yazmaz; yalnızca süreci durdurur. Bu davranış, kritik
    yapılandırma hatalarında uygulamanın yarı çalışır durumda kalmasını
    engellemek için kullanılır.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Kaydı inceler ve CRITICAL ise süreci sonlandırır.

        Args:
            record (logging.LogRecord): İşlenecek log kaydı.

        Raises:
            SystemExit: Kayıt seviyesi ``CRITICAL`` ise.
        """
        if record.levelno >= logging.CRITICAL:
            raise SystemExit(-1)


class OpenSearchHandler(logging.Handler):
    """Log kaydını isteğe bağlı olarak OpenSearch'e gönderen handler.

    Attributes:
        index (str): Yazılacak OpenSearch indeksi.
        client (Any): OpenSearch istemcisi; ``None`` ise gönderim yapılmaz.
    """

    def __init__(self, index: str = "segment-parser", client: Any = None) -> None:
        """Handler'ı hazırlar.

        Args:
            index (str): Yazılacak OpenSearch indeksi.
            client (Any): Hazır OpenSearch istemcisi. ``None`` verilirse
                gönderim devre dışı kalır.
        """
        super().__init__()
        self.index = index
        self.client = client

    def emit(self, record: logging.LogRecord) -> None:
        """Kaydı OpenSearch'e gönderir; hata durumunda sessizce yutar.

        Args:
            record (logging.LogRecord): İşlenecek log kaydı.
        """
        if self.client is None:
            return
        try:
            govde = {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "module": record.name,
                "message": record.getMessage(),
            }
            self.client.index(index=self.index, body=govde, refresh=True)
        except Exception:  # noqa: BLE001 - loglama uygulamayı düşürmemeli
            self.handleError(record)


def _open_search_client() -> Any:
    """Ortam değişkenlerinden OpenSearch istemcisi oluşturur.

    Gerekli değişkenler tanımlı değilse ``None`` döner ve OpenSearch
    gönderimi devre dışı kalır.

    Returns:
        Any: OpenSearch istemcisi veya ``None``.

    KVKK Notu:
        Kimlik bilgileri yalnızca ortam değişkenlerinden okunur; kod
        içerisine gömülmez.
    """
    host = os.getenv("OPENSEARCH_HOST")
    if not host:
        return None
    try:
        from opensearchpy import OpenSearch
    except ImportError:
        logging.getLogger(__name__).warning(
            "opensearch-py kurulu değil; OpenSearch log gönderimi devre dışı."
        )
        return None

    kullanici = os.getenv("OPENSEARCH_USER")
    sifre = os.getenv("OPENSEARCH_PASSWORD")
    http_auth = (kullanici, sifre) if kullanici and sifre else None
    return OpenSearch(
        hosts=[{"host": host, "port": int(os.getenv("OPENSEARCH_PORT", "9200"))}],
        http_auth=http_auth,
        use_ssl=os.getenv("OPENSEARCH_USE_SSL", "true").lower() == "true",
        verify_certs=os.getenv("OPENSEARCH_VERIFY_CERTS", "true").lower() == "true",
    )


class LogYazici:
    """Konsol, dosya ve isteğe bağlı OpenSearch handler'larını kuran logger fabrikası.

    Attributes:
        logger (logging.Logger): Yapılandırılmış logger nesnesi.
    """

    def __init__(
        self,
        logger_ismi: str = "__main__",
        log_file_name: str = "log.log",
        open_search_gondersin_mi: bool = False,
        open_search_client: Any = None,
        open_search_index: str = "segment-parser",
        seviye: int | str | None = None,
    ) -> None:
        """Logger'ı oluşturur ve handler'ları ekler.

        Args:
            logger_ismi (str): Logger adı.
            log_file_name (str): Log dosyasının yolu.
            open_search_gondersin_mi (bool): OpenSearch gönderimi açık mı.
            open_search_client (Any): Hazır OpenSearch istemcisi.
            open_search_index (str): OpenSearch indeks adı.
            seviye (int | str | None): Log seviyesi; ``None`` ise
                ``LOG_LEVEL`` ortam değişkeni veya ``INFO`` kullanılır.
        """
        self.logger = logging.getLogger(logger_ismi)
        self.logger.setLevel(self._seviye_coz(seviye))
        self.logger.propagate = False
        self.open_search_gondersin_mi = open_search_gondersin_mi

        if not self.logger.handlers:
            self.logger.addHandler(self._konsol_handler())
            self.logger.addHandler(self._dosya_handler(log_file_name))
            if open_search_gondersin_mi:
                istemci = open_search_client or _open_search_client()
                self.logger.addHandler(
                    self._json_handler(istemci, open_search_index)
                )
            self.logger.addHandler(ExitOnCriticalHandler())

    @staticmethod
    def _seviye_coz(seviye: int | str | None) -> int:
        """Log seviyesini sayısal değere çevirir.

        Args:
            seviye (int | str | None): Seviye adı veya sayısı.

        Returns:
            int: ``logging`` seviye sabiti.
        """
        if isinstance(seviye, int):
            return seviye
        ham = seviye or os.getenv("LOG_LEVEL", "INFO")
        return getattr(logging, str(ham).upper(), logging.INFO)

    def _konsol_handler(self) -> logging.Handler:
        """Renkli konsol handler'ını oluşturur.

        Returns:
            logging.Handler: Yapılandırılmış konsol handler'ı.
        """
        formatter = ColoredFormatter(
            KONSOL_FORMATI,
            datefmt="%Y-%m-%d %H:%M:%S",
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        handler.addFilter(PIIMaskingFilter())
        return handler

    def _dosya_handler(self, log_file_name: str) -> logging.Handler:
        """Günlük döndürülen dosya handler'ını oluşturur.

        Args:
            log_file_name (str): Log dosyasının yolu.

        Returns:
            logging.Handler: Yapılandırılmış dosya handler'ı.
        """
        handler = TimedRotatingFileHandler(
            log_file_name,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        handler.suffix = "%Y-%m-%d"
        handler.setFormatter(logging.Formatter(DOSYA_FORMATI))
        handler.addFilter(PIIMaskingFilter())
        return handler

    def _json_handler(self, client: Any, index: str) -> logging.Handler:
        """OpenSearch handler'ını oluşturur.

        Args:
            client (Any): OpenSearch istemcisi.
            index (str): OpenSearch indeks adı.

        Returns:
            logging.Handler: Yapılandırılmış OpenSearch handler'ı.
        """
        handler = OpenSearchHandler(index=index, client=client)
        handler.addFilter(PIIMaskingFilter())
        return handler

    def basla(self) -> logging.Logger:
        """Yapılandırılmış logger'ı döndürür.

        Returns:
            logging.Logger: Kullanıma hazır logger.
        """
        return self.logger


def get_logger(name: str = "__main__") -> logging.Logger:
    """Uygulama genelinde kullanılacak logger'ı döndürür.

    Args:
        name (str): Logger adı.

    Returns:
        logging.Logger: Yapılandırılmış logger.
    """
    return LogYazici(
        logger_ismi=name,
        log_file_name=os.getenv("LOG_FILE", "log.log"),
    ).basla()


if __name__ == "__main__":
    logs = get_logger("SegmentParser")
    logs.info("Loglama sistemi hazır.")
    logs.debug("Örnek hata ayıklama kaydı.")
    logs.warning("Örnek uyarı kaydı.")
