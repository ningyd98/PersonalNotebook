"""PDF Parser — 使用 PyMuPDF 解析文本、表格、图片"""

import uuid
from pathlib import Path
from typing import Optional

from loguru import logger

from app.services.parsers.base import (
    BaseParser, ParserRegistry, UDRAsset, UDRBlock, UnifiedDocument,
)

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    logger.warning("PyMuPDF not installed; PDF parsing will be limited")


class PDFParser(BaseParser):
    supported_mime_types = ["application/pdf"]
    supported_extensions = [".pdf"]

    def parse(self, file_path: str, options: Optional[dict] = None) -> UnifiedDocument:
        if not HAS_PYMUPDF:
            return self._fallback_parse(file_path)

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        filename = path.name
        options = options or {}

        blocks = []
        assets: list[UDRAsset] = []

        try:
            pdf_doc = fitz.open(file_path)
            metadata = pdf_doc.metadata or {}

            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                page_num_display = page_num + 1

                # 提取文本块
                text_blocks = page.get_text("blocks")
                for b_idx, tb in enumerate(text_blocks):
                    x0, y0, x1, y1, text, block_type, _ = tb
                    text = text.strip()
                    if not text:
                        continue

                    block_type_str = "paragraph"
                    if block_type == 0:
                        block_type_str = "paragraph"
                    elif block_type == 1:
                        block_type_str = "image"

                    blocks.append(UDRBlock(
                        block_id=f"{doc_id}_b{len(blocks):04d}",
                        type=block_type_str,
                        text=text,
                        page=page_num_display,
                        bbox={"x0": x0, "y0": y0, "x1": x1, "y1": y1},
                    ))

                # 提取表格
                try:
                    tables = page.find_tables()
                    for t_idx, table in enumerate(tables):
                        cells = table.extract()
                        if cells:
                            headers = cells[0] if cells else []
                            rows = cells[1:] if len(cells) > 1 else []
                            table_text = self._table_to_text(headers, rows)
                            blocks.append(UDRBlock(
                                block_id=f"{doc_id}_b{len(blocks):04d}",
                                type="table",
                                text=table_text,
                                page=page_num_display,
                                structured_data={
                                    "headers": headers,
                                    "rows": rows,
                                },
                            ))
                except Exception as e:
                    logger.debug(f"PDF table extraction failed page {page_num_display}: {e}")

            pdf_doc.close()

            return UnifiedDocument(
                document_id=doc_id,
                source={
                    "filename": filename,
                    "mime_type": "application/pdf",
                    "source_uri": str(path.absolute()),
                },
                metadata={
                    "title": metadata.get("title", filename),
                    "author": metadata.get("author", ""),
                    "page_count": len(blocks),
                },
                blocks=blocks,
                assets=assets,
            )

        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            return self._fallback_parse(file_path)

    def _fallback_parse(self, file_path: str) -> UnifiedDocument:
        """PyMuPDF 不可用时的兜底方案"""
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        return UnifiedDocument(
            document_id=doc_id,
            source={
                "filename": path.name,
                "mime_type": "application/pdf",
                "source_uri": str(path.absolute()),
            },
            metadata={"title": path.name, "warning": "PDF parsing library not available"},
            blocks=[
                UDRBlock(
                    block_id=f"{doc_id}_b0000",
                    type="paragraph",
                    text=f"[PDF file: {path.name} — install PyMuPDF for full parsing]",
                ),
            ],
        )

    @staticmethod
    def _table_to_text(headers: list, rows: list) -> str:
        lines = [" | ".join(str(h) for h in headers)]
        lines.append(" | ".join(["---"] * len(headers)))
        for row in rows:
            lines.append(" | ".join(str(cell) for cell in row))
        return "\n".join(lines)


# 注册
ParserRegistry.register(PDFParser())
