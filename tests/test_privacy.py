"""PII maskeleme ve log filtresi testleri.

Tüm örnek veriler sentetiktir; gerçek kişisel veri içermez.
"""

from __future__ import annotations

import logging

import pytest

from privacy import PIIMaskingFilter, mask_text, mask_value


class TestMaskText:
    """``mask_text`` fonksiyonu davranışları."""

    def test_tckn_maskelenir(self) -> None:
        """11 haneli TCKN yer tutucuya dönüşmelidir."""
        assert mask_text("TCKN: 12345678901") == "TCKN: <TCKN_1>"

    def test_email_maskelenir(self) -> None:
        """E-posta adresi yer tutucuya dönüşmelidir."""
        assert mask_text("iletisim: test@example.com") == "iletisim: <EMAIL_1>"

    def test_telefon_maskelenir(self) -> None:
        """Telefon numarası yer tutucuya dönüşmelidir."""
        assert mask_text("Tel: 0555 123 45 67") == "Tel: <PHONE_1>"

    def test_ip_maskelenir(self) -> None:
        """IPv4 adresi yer tutucuya dönüşmelidir."""
        assert mask_text("IP: 192.168.1.10") == "IP: <IP_1>"

    def test_iban_maskelenir(self) -> None:
        """IBAN yer tutucuya dönüşmelidir."""
        assert mask_text("TR" + "1" * 24) == "<IBAN_1>"

    def test_ayni_desenden_ikisi_numaralanir(self) -> None:
        """Aynı desendeki birden fazla eşleşme sırayla numaralanmalıdır."""
        sonuc = mask_text("a@b.com ve c@d.com")

        assert sonuc == "<EMAIL_1> ve <EMAIL_2>"

    def test_temiz_metin_degismez(self) -> None:
        """Kişisel veri içermeyen metin aynen dönmelidir."""
        assert mask_text("GGOH segmenti parse edildi.") == "GGOH segmenti parse edildi."

    def test_metin_olmayan_girdi_hata_verir(self) -> None:
        """Metin olmayan girdi ``TypeError`` fırlatmalıdır."""
        with pytest.raises(TypeError):
            mask_text(None)  # type: ignore[arg-type]


class TestMaskValue:
    """``mask_value`` fonksiyonu davranışları."""

    def test_metin_maskelenir(self) -> None:
        """Metin değer maskelenmelidir."""
        assert mask_value("test@example.com") == "<EMAIL_1>"

    def test_metin_olmayan_deger_aynen_doner(self) -> None:
        """Sayı gibi metin olmayan değerler değişmemelidir."""
        assert mask_value(42) == 42


class TestPIIMaskingFilter:
    """``PIIMaskingFilter`` davranışları."""

    def test_mesaj_maskelenir(self) -> None:
        """Filtre, kayıt mesajındaki kişisel veriyi maskelemelidir."""
        kayit = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Kullanıcı e-postası: test@example.com",
            args=(),
            exc_info=None,
        )

        assert PIIMaskingFilter().filter(kayit) is True
        assert kayit.msg == "Kullanıcı e-postası: <EMAIL_1>"

    def test_args_maskelenir(self) -> None:
        """Filtre, format argümanlarındaki kişisel veriyi maskelemelidir."""
        kayit = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Telefon: %s",
            args=("0555 123 45 67",),
            exc_info=None,
        )

        PIIMaskingFilter().filter(kayit)
        assert kayit.args == ("<PHONE_1>",)
        assert kayit.getMessage() == "Telefon: <PHONE_1>"
