"""Parser 模块 — 自动注册所有 parser"""

from app.services.parsers.base import BaseParser, ParserRegistry, UnifiedDocument, UDRBlock, UDRAsset, UDRRelation

# 以下导入自动触发 ParserRegistry.register()
from app.services.parsers.markdown_parser import MarkdownParser  # noqa: F401
from app.services.parsers.txt_parser import TXTParser  # noqa: F401
from app.services.parsers.pdf_parser import PDFParser  # noqa: F401
from app.services.parsers.fallback_parser import FallbackParser  # noqa: F401
from app.services.parsers.docx_parser import DOCXParser  # noqa: F401
from app.services.parsers.pptx_parser import PptxParser  # noqa: F401
from app.services.parsers.xlsx_parser import XlsxParser  # noqa: F401
from app.services.parsers.latex_parser import LatexParser  # noqa: F401
from app.services.parsers.image_parser import ImageParser  # noqa: F401
from app.services.parsers.code_parser import CodeParser  # noqa: F401
from app.services.parsers.archive_parser import ArchiveParser  # noqa: F401
from app.services.parsers.audio_parser import AudioParser  # noqa: F401
from app.services.parsers.video_parser import VideoParser  # noqa: F401

__all__ = [
    "BaseParser", "ParserRegistry",
    "UnifiedDocument", "UDRBlock", "UDRAsset", "UDRRelation",
    "MarkdownParser", "TXTParser", "PDFParser", "FallbackParser",
    "DOCXParser", "PptxParser", "XlsxParser", "LatexParser",
    "ImageParser", "CodeParser", "ArchiveParser", "AudioParser", "VideoParser",
]
