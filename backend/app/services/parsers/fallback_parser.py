"""Fallback Parser — 当专用 parser 不可用时兜底"""

import uuid
from pathlib import Path
from typing import Optional

from loguru import logger

from app.services.parsers.base import (
    BaseParser, ParserRegistry, UDRBlock, UnifiedDocument,
)


class FallbackParser(BaseParser):
    """兜底解析器：尝试纯文本读取"""

    supported_mime_types = ["*/*"]
    supported_extensions = ["*"]

    def parse(self, file_path: str, options: Optional[dict] = None) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        filename = path.name

        # 尝试所有编码
        content = ""
        for encoding in ["utf-8", "gbk", "gb2312", "latin-1"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, Exception):
                continue

        if not content:
            # 二进制文件无法文本解析
            blocks = [
                UDRBlock(
                    block_id=f"{doc_id}_b0000",
                    type="metadata",
                    text=f"[Binary file: {filename} — no text parser available]",
                    metadata={"warning": "binary_file_no_parser"},
                )
            ]
        else:
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            blocks = [
                UDRBlock(
                    block_id=f"{doc_id}_b{i:04d}",
                    type="paragraph",
                    text=para,
                )
                for i, para in enumerate(paragraphs[:500])  # 限制 500 段
            ]

        return UnifiedDocument(
            document_id=doc_id,
            source={
                "filename": filename,
                "mime_type": "application/octet-stream",
                "source_uri": str(path.absolute()),
            },
            metadata={
                "title": filename,
                "warning": "Used fallback parser",
            },
            blocks=blocks,
        )


# 注册为最低优先级
ParserRegistry.register(FallbackParser())
