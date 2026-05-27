"""
智能切片服务

策略：
- 按标题层级切片（保留 section_path）
- 表格不拆散
- 代码块不拆散
- 默认 chunk_size=800 中文字，overlap=120
"""

import hashlib
import re
from typing import Optional

from loguru import logger

from app.core.config import get_settings
from app.services.parsers.base import UDRBlock, UnifiedDocument

settings = get_settings()


class ChunkingService:
    """文档切片服务"""

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def chunk_udr(self, udr: UnifiedDocument) -> list[dict]:
        """
        将 UnifiedDocument 的 blocks 合并、切片。
        返回 chunk 列表，每个 chunk 包含内容和元数据。
        """
        # Step 1: 合并相邻的 paragraph/heading block
        merged_blocks = self._merge_blocks(udr.blocks)

        # Step 2: 按 chunk_size 切片
        chunks = self._split_into_chunks(merged_blocks)

        # Step 3: 计算 overlap
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)

        # Step 4: 计算 hash 和 token count
        for i, chunk in enumerate(chunks):
            content = chunk["content"]
            chunk["chunk_index"] = i
            chunk["content_hash"] = hashlib.sha256(content.encode()).hexdigest()[:32]
            chunk["token_count"] = self._estimate_tokens(content)
            chunk["document_id"] = udr.document_id
            chunk["source"] = udr.source
            chunk["metadata_json"] = {
                "filename": udr.source.get("filename", ""),
                "title": udr.metadata.get("title", ""),
                "source_type": chunk.get("source_type", "text"),
            }

        logger.info(f"Chunked document {udr.document_id}: {len(udr.blocks)} blocks -> {len(chunks)} chunks")
        return chunks

    def _merge_blocks(self, blocks: list[UDRBlock]) -> list[dict]:
        """合并相邻的同类 block"""
        merged = []
        current_text_parts = []
        current_meta = {}

        for block in blocks:
            btype = block.type

            if btype in ("heading", "paragraph", "list", "quote"):
                # 可合并类型
                if btype == "heading":
                    # 标题作为分段点
                    if current_text_parts:
                        merged.append(self._make_merged(current_text_parts, current_meta))
                    current_text_parts = [f"{'#' * (block.level or 1)} {block.text}"]
                    current_meta = {
                        "section_path": block.section_path,
                        "page_number": block.page,
                        "slide_number": block.slide,
                    }
                else:
                    current_text_parts.append(block.text)
                    if block.section_path:
                        current_meta["section_path"] = block.section_path
                    if block.page:
                        current_meta["page_number"] = block.page
                    if block.slide:
                        current_meta["slide_number"] = block.slide

            else:
                # 不合并类型（table/code/image/equation）
                if current_text_parts:
                    merged.append(self._make_merged(current_text_parts, current_meta))
                    current_text_parts = []
                    current_meta = {}

                merged.append({
                    "content": block.text,
                    "block_type": btype,
                    "section_path": block.section_path,
                    "page_number": block.page,
                    "slide_number": block.slide,
                    "sheet_name": block.sheet_name,
                    "cell_range": block.cell_range,
                    "start_time": block.start_time,
                    "end_time": block.end_time,
                    "structured_data": block.structured_data,
                    "source_type": self._map_block_type(btype),
                })

        if current_text_parts:
            merged.append(self._make_merged(current_text_parts, current_meta))

        return merged

    @staticmethod
    def _make_merged(parts: list[str], meta: dict) -> dict:
        return {
            "content": "\n\n".join(parts),
            "block_type": "text",
            "section_path": meta.get("section_path"),
            "page_number": meta.get("page_number"),
            "slide_number": meta.get("slide_number"),
            "source_type": "text",
        }

    def _split_into_chunks(self, merged_blocks: list[dict]) -> list[dict]:
        """按字数切片"""
        chunks = []
        current_text = ""
        current_meta = {}

        for block in merged_blocks:
            content = block["content"]
            # 如果 block 本身很大（表格、代码等），单独成 chunk
            if len(content) > self.chunk_size * 2:
                if current_text:
                    chunks.append({"content": current_text, **current_meta})
                    current_text = ""
                    current_meta = {}
                chunks.append({**block})
                continue

            if len(current_text) + len(content) + 2 <= self.chunk_size:
                if current_text:
                    current_text += "\n\n" + content
                else:
                    current_text = content
                    current_meta = {
                        "section_path": block.get("section_path"),
                        "page_number": block.get("page_number"),
                        "slide_number": block.get("slide_number"),
                        "source_type": block.get("source_type", "text"),
                    }
            else:
                if current_text:
                    chunks.append({"content": current_text, **current_meta})
                current_text = content
                current_meta = {
                    "section_path": block.get("section_path"),
                    "page_number": block.get("page_number"),
                    "slide_number": block.get("slide_number"),
                    "source_type": block.get("source_type", "text"),
                }

        if current_text:
            chunks.append({"content": current_text, **current_meta})

        return chunks

    def _add_overlap(self, chunks: list[dict]) -> list[dict]:
        """为相邻 chunk 添加 overlap"""
        result = [chunks[0]]
        for i in range(1, len(chunks)):
            prev = result[-1]["content"]
            curr = chunks[i]["content"]
            # 从 prev 末尾取 overlap 字数加入 curr 开头
            overlap_text = prev[-self.chunk_overlap:]
            chunks[i]["content"] = overlap_text + "\n\n[overlap]\n\n" + curr
            result.append(chunks[i])
        return result

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """中文约 1 字 = 1 token，英文约 4 字符 = 1 token"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        return chinese_chars + other_chars // 4

    @staticmethod
    def _map_block_type(block_type: str) -> str:
        mapping = {
            "heading": "text", "paragraph": "text", "list": "text", "quote": "text",
            "table": "table", "code": "code", "image": "image",
            "equation": "formula", "transcript": "audio",
            "video_segment": "video",
        }
        return mapping.get(block_type, "text")
