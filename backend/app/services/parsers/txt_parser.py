"""TXT Parser — 纯文本解析"""

import uuid
from pathlib import Path
from typing import Optional

from app.services.parsers.base import (
    BaseParser, ParserRegistry, UDRBlock, UnifiedDocument,
)


class TXTParser(BaseParser):
    supported_mime_types = ["text/plain"]
    supported_extensions = [".txt", ".text", ".log"]

    def parse(self, file_path: str, options: Optional[dict] = None) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        filename = path.name

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # 按双换行分段
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        blocks = []
        for i, para in enumerate(paragraphs):
            blocks.append(UDRBlock(
                block_id=f"{doc_id}_b{i:04d}",
                type="paragraph",
                text=para,
            ))

        return UnifiedDocument(
            document_id=doc_id,
            source={
                "filename": filename,
                "mime_type": "text/plain",
                "source_uri": str(path.absolute()),
            },
            metadata={"title": filename},
            blocks=blocks,
        )


# 注册
ParserRegistry.register(TXTParser())
