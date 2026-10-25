"""Segment parser web uygulaması.

Bu modül, sabit uzunluklu segment metnini segmentlere ayırıp her segmenti
ilgili parser ile çözen bir Flask uygulaması sağlar. Sonuçlar JSON olarak
döndürülür ve ``templates/index.html`` arayüzünde gösterilir.

KVKK Notu:
    Gönderilen ham metin kişisel/hassas veri içerebilir. Bu metin
    loglanmaz; yalnızca segment kimlikleri ve hata bilgileri loglanır
    (bkz. ``AI/01_KVKK_AND_SECURITY.md``).
"""

from __future__ import annotations

import os
from typing import Any, Final

from flask import Flask, Response, jsonify, render_template, request

from log_yapisi import LogYazici
from PARSERS import (
    BaseSegmentParser,
    GGOHParser,
    GGSSParser,
    GGTKParser,
    SegmentParseError,
)

#: Segment kimliği -> parser sınıfı eşlemesi.
PARSERLAR: Final[dict[str, type[BaseSegmentParser]]] = {
    "GGOH": GGOHParser,
    "GGSS": GGSSParser,
    "GGTK": GGTKParser,
}

#: Segment kimliği ve uzunluk alanlarının toplam uzunluğu.
BASLIK_UZUNLUGU: Final[int] = 8
#: Kabul edilen en büyük istek gövdesi (bayt).
MAKS_ISTEK_BOYUTU: Final[int] = 5 * 1024 * 1024

logger = LogYazici(
    logger_ismi="SegmentParser",
    log_file_name=os.getenv("LOG_FILE", "log.log"),
).basla()


def replace_range(text: str, start: int, end: int, replace_char: str = "_") -> str:
    """Belirtilen aralıktaki karakterleri verilen karakter ile değiştirir.

    Args:
        text (str): Değiştirilecek orijinal metin.
        start (int): Değiştirmenin başlayacağı indeks (dahil).
        end (int): Değiştirmenin biteceği indeks (hariç).
        replace_char (str): Yerine yazılacak karakter (varsayılan ``"_"``).

    Returns:
        str: Belirtilen aralığı değiştirilmiş yeni metin.

    Raises:
        ValueError: Başlangıç/bitiş indeksleri geçersizse veya
            ``replace_char`` tek karakter değilse.

    KVKK Notu:
        Bu fonksiyon, hassas alanları çıktıdan gizlemek için kullanılabilir.
    """
    if not (0 <= start <= end <= len(text)):
        raise ValueError(
            "Başlangıç ve bitiş indeksleri metin uzunluğu içinde ve sıralı olmalıdır."
        )
    if len(replace_char) != 1:
        raise ValueError("replace_char tek karakter olmalıdır.")
    return text[:start] + replace_char * (end - start) + text[end:]


def _benzersiz_anahtar(anahtarlar: dict[str, Any], segment_adi: str) -> str:
    """Sözlükte çakışmayan bir segment anahtarı üretir.

    Args:
        anahtarlar (dict[str, Any]): Mevcut anahtarları içeren sözlük.
        segment_adi (str): Segment kimliği (örn. ``"GGOH"``).

    Returns:
        str: ``"GGOH"``, ``"GGOH_1"``, ``"GGOH_2"`` ... biçiminde benzersiz anahtar.
    """
    if segment_adi not in anahtarlar:
        return segment_adi
    sayac = 1
    while f"{segment_adi}_{sayac}" in anahtarlar:
        sayac += 1
    return f"{segment_adi}_{sayac}"


def esletirme(raw_txt: str) -> dict[str, Any]:
    """Ham metni segmentlere ayırır ve her segmenti parse eder.

    Metin içinde ``"GG"`` ile başlayan her segment başlığı bulunur; 4
    karakterlik kimlik ve 4 karakterlik uzunluk okunarak segment dilimi
    çıkarılır. Tanımlı bir parser varsa segment çözülür, yoksa atlanır.

    Args:
        raw_txt (str): Ham segment metni.

    Returns:
        dict[str, Any]: Segment anahtarı -> parse edilmiş alan sözlüğü.
        Aynı kimlikten birden fazla varsa ``"GGOH_1"`` gibi sonek eklenir.

    Raises:
        TypeError: ``raw_txt`` metin değilse.

    KVKK Notu:
        Ham metin ve alan değerleri loglanmaz; yalnızca segment kimliği ve
        sayaç bilgisi loglanır.
    """
    if not isinstance(raw_txt, str):
        raise TypeError("raw_txt metin (str) olmalıdır.")

    sonuc: dict[str, Any] = {}
    index = raw_txt.find("GG")
    while index != -1:
        segment_adi = raw_txt[index : index + 4]
        uzunluk_ham = raw_txt[index + 4 : index + BASLIK_UZUNLUGU]

        if len(segment_adi) < 4 or not uzunluk_ham.isdigit():
            index = raw_txt.find("GG", index + 2)
            continue

        segment_uzunlugu = int(uzunluk_ham)
        if segment_uzunlugu < BASLIK_UZUNLUGU:
            logger.warning("Geçersiz segment uzunluğu atlandı: %s", segment_adi)
            index = raw_txt.find("GG", index + 2)
            continue

        segment_raw_txt = raw_txt[index : index + segment_uzunlugu]
        parser_sinifi = PARSERLAR.get(segment_adi)

        if parser_sinifi is None:
            logger.info("Tanımlı parser bulunamadı, segment atlandı: %s", segment_adi)
        else:
            try:
                parse_dict = parser_sinifi(segment_raw_txt).get_data()
            except SegmentParseError as hata:
                logger.warning("Segment parse edilemedi: %s", hata)
            else:
                anahtar = _benzersiz_anahtar(sonuc, segment_adi)
                sonuc[anahtar] = parse_dict
                logger.info("Segment parse edildi: %s", anahtar)

        index = raw_txt.find("GG", index + 2)

    return sonuc


def create_app() -> Flask:
    """Flask uygulamasını oluşturur ve rotaları tanımlar.

    Returns:
        Flask: Yapılandırılmış Flask uygulaması.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["MAX_CONTENT_LENGTH"] = MAKS_ISTEK_BOYUTU
    app.config["JSON_AS_ASCII"] = False

    @app.route("/", methods=["GET"])
    def homepage() -> str:
        """Ana sayfayı (parser arayüzü) döndürür.

        Returns:
            str: Render edilmiş HTML sayfası.
        """
        return render_template("index.html")

    @app.route("/health", methods=["GET"])
    def health() -> Response:
        """Servisin ayakta olduğunu bildiren sağlık kontrolü.

        Returns:
            Response: ``{"status": "ok"}`` JSON yanıtı.
        """
        return jsonify({"status": "ok"})

    @app.route("/parse_et", methods=["POST"])
    def parse_et() -> tuple[Response, int] | Response:
        """Gönderilen ham metni segmentlere ayırıp JSON olarak döndürür.

        Returns:
            tuple[Response, int] | Response: Parse sonucu veya hata mesajı.

        KVKK Notu:
            Hata durumunda ham metin yanıta/loga yazılmaz.
        """
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Geçersiz JSON gövdesi."}), 400

        raw_text = data.get("raw_text", "")
        if not isinstance(raw_text, str) or not raw_text.strip():
            return jsonify({"error": "Boş veri gönderildi."}), 400

        try:
            return jsonify(esletirme(raw_text))
        except SegmentParseError as hata:
            logger.warning("Parse hatası: %s", hata)
            return jsonify({"error": str(hata)}), 400
        except Exception:  # noqa: BLE001 - kullanıcıya iç detay sızdırılmaz
            logger.exception("Beklenmeyen parse hatası.")
            return jsonify({"error": "Sunucu tarafında beklenmeyen bir hata oluştu."}), 500

    @app.errorhandler(413)
    def istek_cok_buyuk(_: Exception) -> tuple[Response, int]:
        """İstek gövdesi sınırı aşıldığında Türkçe hata döndürür.

        Args:
            _ (Exception): Flask tarafından sağlanan hata nesnesi.

        Returns:
            tuple[Response, int]: Hata mesajı ve 413 durum kodu.
        """
        return jsonify({"error": "Gönderilen veri izin verilen boyutu aşıyor."}), 413

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "5000")),
        debug=os.getenv("APP_ENV", "development") == "development",
    )
