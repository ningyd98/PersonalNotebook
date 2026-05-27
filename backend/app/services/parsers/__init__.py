"""Parser 模块 — 自动注册所有 parser"""

from app.services.parsers.base import BaseParser, ParserRegistry, UnifiedDocument, UDRBlock, UDRAsset, UDRRelation
# 以下导入自动触发 ParserRegistry.register()
from app.services.parsers.markdown_parser import MarkdownParser  # noqa: F401
from app.services.parsers.txt_parser import TXTParser  # noqa: F401
from app.services.parsers.pdf_parser import PDFParser  # noqa: F401
from app.services.parsers.fallback_parser import FallbackParser  # noqa: F401

__all__ = [
    "BaseParser", "ParserRegistry",
    "UnifiedDocument", "UDRBlock", "UDRAsset", "UDRRelation",
]
