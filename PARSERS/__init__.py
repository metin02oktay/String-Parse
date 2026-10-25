"""Segment parser'ları.

Bu paket, sabit uzunluklu segment metinlerini (GGOH, GGSS, GGTK ...)
Python sözlüklerine dönüştürür.

KVKK Notu:
    Parse edilen değerler kişisel/hassas veri içerebilir. Bu değerler
    loglara açık metin olarak yazılmamalıdır
"""

from .base_parser import BaseSegmentParser, FixedWidthReader, SegmentParseError
from .GGOH_parser import GGOHParser
from .GGSS_parser import GGSSParser
from .GGTK_parser import DonemParser, GGTKParser

__all__ = [
    "BaseSegmentParser",
    "FixedWidthReader",
    "SegmentParseError",
    "GGOHParser",
    "GGSSParser",
    "GGTKParser",
    "DonemParser",
]
