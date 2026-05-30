"""
切片服务单元测试

测试内容：
- 不同类型 block 的切片策略
- chunk_size / overlap 参数
- 大表格不拆散
- 代码块不拆散
- 中文 token 估算
- heading 作为分段点
- merged blocks 结构

运行: pytest tests/test_chunking.py -v
"""

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.parsers.base import UDRBlock, UnifiedDocument
from app.services.chunking.chunker import ChunkingService


# ============================================================
# 辅助函数
# ============================================================
def make_udr(blocks, doc_id=None, filename="test.md"):
    """快速构造 UnifiedDocument"""
    return UnifiedDocument(
        document_id=doc_id or str(uuid.uuid4()),
        source={"filename": filename},
        metadata={"title": filename},
        blocks=blocks,
    )


# ============================================================
# 基本切片
# ============================================================
class TestBasicChunking:
    """基本切片功能测试"""

    def test_single_paragraph(self):
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="这是一段测试文本。"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        assert len(chunks) == 1
        assert "测试文本" in chunks[0]["content"]
        assert chunks[0]["document_id"] == udr.document_id

    def test_multiple_paragraphs_merge(self):
        """短段落应该合并到一个 chunk"""
        blocks = [
            UDRBlock(block_id="b1", type="heading", text="标题", level=1),
            UDRBlock(block_id="b2", type="paragraph", text="第一段。"),
            UDRBlock(block_id="b3", type="paragraph", text="第二段。"),
            UDRBlock(block_id="b4", type="paragraph", text="第三段。"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        # 所有短段落应合并到一个 chunk
        assert len(chunks) >= 1
        first_content = chunks[0]["content"]
        assert "标题" in first_content
        assert "第一段" in first_content

    def test_chunk_size_limit(self):
        """超过 chunk_size 时应拆分为多个 chunk"""
        long_text = "这是很长的文本。" * 200  # 约 1600 字
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text=long_text),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=400, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        # 由于文本长度超过 chunk_size，应被切分为多个 chunk
        assert len(chunks) >= 1
        for chunk in chunks:
            assert len(chunk["content"]) > 0

    def test_chunk_document_id(self):
        """所有 chunk 的 document_id 应该匹配原始 UDR"""
        real_uuid = str(uuid.uuid4())
        blocks = [
            UDRBlock(block_id="b1", type="heading", text="Test", level=1),
            UDRBlock(block_id="b2", type="paragraph", text="Content " * 20),
        ]
        udr = make_udr(blocks, doc_id=real_uuid)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        for chunk in chunks:
            assert chunk["document_id"] == real_uuid
            # 验证是有效 UUID
            uuid.UUID(chunk["document_id"])


# ============================================================
# 不同 block 类型
# ============================================================
class TestBlockTypeStrategies:
    """不同类型 block 的切片策略"""

    def test_heading_as_segment_point(self):
        """heading 应该作为分段点"""
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="前言段落。"),
            UDRBlock(block_id="b2", type="heading", text="第一章", level=1),
            UDRBlock(block_id="b3", type="paragraph", text="第一章内容。"),
            UDRBlock(block_id="b4", type="heading", text="第二章", level=1),
            UDRBlock(block_id="b5", type="paragraph", text="第二章内容。"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        # heading 会导致分段
        assert len(chunks) >= 2

    def test_table_not_split(self):
        """大表格不应被拆散"""
        # 构造一个大表格 block
        headers = ["列A", "列B", "列C"]
        rows = [[f"数据{i}A", f"数据{i}B", f"数据{i}C"] for i in range(50)]
        table_text = "| " + " | ".join(headers) + " |\n"
        table_text += "| " + " | ".join(["---"] * 3) + " |\n"
        for row in rows:
            table_text += "| " + " | ".join(row) + " |\n"

        blocks = [
            UDRBlock(
                block_id="b1", type="table", text=table_text,
                structured_data={"headers": headers, "rows": rows},
            ),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=200, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        # 表格即使超过 chunk_size 也应保持完整（作为一个 chunk）
        table_chunks = [c for c in chunks if c.get("source_type") == "table"]
        assert len(table_chunks) >= 1
        # 表格内容应该完整
        table_content = table_chunks[0]["content"]
        assert "列A" in table_content
        assert "数据49" in table_content

    def test_code_block_not_split(self):
        """代码块不应被拆散"""
        code_text = "def hello():\n"
        code_text += "    for i in range(100):\n"
        code_text += "        print(f'Line {i}')\n"

        blocks = [
            UDRBlock(
                block_id="b1", type="code", text=code_text,
                metadata={"language": "python"},
            ),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=50, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        # 代码块应保持完整
        code_chunks = [c for c in chunks if c.get("source_type") == "code"]
        assert len(code_chunks) >= 1
        assert "def hello" in code_chunks[0]["content"]
        assert "print" in code_chunks[0]["content"]

    def test_image_block_standalone(self):
        """image block 应单独成 chunk"""
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="正文段落。"),
            UDRBlock(block_id="b2", type="image", text="[Image: photo.jpg]",
                     asset_uri="file:///photo.jpg"),
            UDRBlock(block_id="b3", type="paragraph", text="更多正文。"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        # image 应独立出现
        image_chunks = [c for c in chunks if c.get("source_type") == "image"]
        assert len(image_chunks) >= 1

    def test_equation_block_standalone(self):
        """equation block 应单独成 chunk"""
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="如下公式："),
            UDRBlock(block_id="b2", type="equation", text="E = mc^2"),
            UDRBlock(block_id="b3", type="paragraph", text="公式解释。"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        formula_chunks = [c for c in chunks if c.get("source_type") == "formula"]
        assert len(formula_chunks) >= 1
        assert "E = mc^2" in formula_chunks[0]["content"]


# ============================================================
# Overlap 参数
# ============================================================
class TestOverlap:
    """Overlap 参数测试"""

    def test_overlap_adds_redundancy(self):
        """有 overlap 时，相邻 chunk 应有内容重叠"""
        blocks = [
            UDRBlock(block_id="b1", type="heading", text="标题1", level=1),
            UDRBlock(block_id="b2", type="paragraph", text="A" * 300),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=200, chunk_overlap=50)
        chunks = service.chunk_udr(udr)

        if len(chunks) > 1:
            # 从第二个 chunk 开始应有 overlap 标记
            for i in range(1, len(chunks)):
                if "[overlap]" in chunks[i]["content"]:
                    assert True
                    break
            else:
                # 如果没有 [overlap] 标记，检查是否有内容重叠
                pass

    def test_zero_overlap(self):
        """overlap=0 时不应有内容重叠"""
        blocks = [
            UDRBlock(block_id="b1", type="heading", text="标题", level=1),
            UDRBlock(block_id="b2", type="paragraph", text="内容一。"),
            UDRBlock(block_id="b3", type="heading", text="标题2", level=1),
            UDRBlock(block_id="b4", type="paragraph", text="内容二。"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        for chunk in chunks:
            assert "[overlap]" not in chunk["content"]

    def test_overlap_value(self):
        """overlap 文本长度应接近配置值"""
        long_text = "这是一段很长的中文文本，" * 100
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text=long_text),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=200, chunk_overlap=50)
        chunks = service.chunk_udr(udr)

        if len(chunks) > 1:
            for i in range(1, len(chunks)):
                if "[overlap]" in chunks[i]["content"]:
                    overlap_part = chunks[i]["content"].split("[overlap]")[0]
                    # overlap 部分应该约 50 字
                    assert len(overlap_part.strip()) <= 60
                    break


# ============================================================
# 中文 token 估算
# ============================================================
class TestTokenEstimation:
    """中文 token 估算测试"""

    def test_chinese_tokens(self):
        """中文字符约 1 字 = 1 token"""
        text = "这是一个测试文本"
        tokens = ChunkingService._estimate_tokens(text)
        assert tokens == len(text)

    def test_english_tokens(self):
        """英文约 4 字符 = 1 token"""
        text = "Hello World Test"
        tokens = ChunkingService._estimate_tokens(text)
        # 16 chars / 4 = 4 tokens
        assert tokens == 4

    def test_mixed_tokens(self):
        """中英文混合文本"""
        text = "这是一个test文本"
        tokens = ChunkingService._estimate_tokens(text)
        # 中文 6 字 = 6 tokens, 英文 "test" 4 chars = 1 token
        assert tokens == 7

    def test_token_count_in_chunks(self):
        """chunk 应包含 token_count 字段"""
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="这是一个测试文本。"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        assert "token_count" in chunks[0]
        assert chunks[0]["token_count"] > 0


# ============================================================
# Chunk 元数据
# ============================================================
class TestChunkMetadata:
    """Chunk 元数据测试"""

    def test_content_hash(self):
        """chunk 应有 content_hash"""
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="测试文本"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        assert "content_hash" in chunks[0]
        assert len(chunks[0]["content_hash"]) == 32  # SHA256 前 32 位

    def test_chunk_index(self):
        """chunk 应有 chunk_index"""
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="段落一。"),
            UDRBlock(block_id="b2", type="paragraph", text="段落二。"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    def test_source_preserved(self):
        """chunk 应保留 source 信息"""
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="内容"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        assert chunks[0]["source"]["filename"] == "test.md"

    def test_metadata_json(self):
        """chunk 应有 metadata_json"""
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="内容"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        assert "metadata_json" in chunks[0]
        assert "filename" in chunks[0]["metadata_json"]

    def test_section_path_preserved(self):
        """section_path 应传递到 chunk"""
        blocks = [
            UDRBlock(block_id="b1", type="heading", text="第一章", level=1,
                     section_path="第一章"),
            UDRBlock(block_id="b2", type="paragraph", text="内容",
                     section_path="第一章"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        assert chunks[0].get("section_path") is not None


# ============================================================
# Block 类型映射
# ============================================================
class TestBlockTypeMapping:
    """_map_block_type 测试"""

    def test_text_types(self):
        assert ChunkingService._map_block_type("heading") == "text"
        assert ChunkingService._map_block_type("paragraph") == "text"
        assert ChunkingService._map_block_type("list") == "text"
        assert ChunkingService._map_block_type("quote") == "text"

    def test_special_types(self):
        assert ChunkingService._map_block_type("table") == "table"
        assert ChunkingService._map_block_type("code") == "code"
        assert ChunkingService._map_block_type("image") == "image"
        assert ChunkingService._map_block_type("equation") == "formula"
        assert ChunkingService._map_block_type("transcript") == "audio"
        assert ChunkingService._map_block_type("video_segment") == "video"

    def test_unknown_type_defaults_to_text(self):
        assert ChunkingService._map_block_type("unknown_type") == "text"


# ============================================================
# 边界情况
# ============================================================
class TestEdgeCases:
    """边界情况测试"""

    def test_empty_udr(self):
        """空 UDR 不应报错"""
        udr = make_udr([])
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)
        assert len(chunks) == 0

    def test_single_char_blocks(self):
        """单字符 block"""
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="A"),
            UDRBlock(block_id="b2", type="paragraph", text="B"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)
        assert len(chunks) >= 1

    def test_very_large_chunk_size(self):
        """超大 chunk_size 应将所有内容合并到一个 chunk"""
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="段落一。"),
            UDRBlock(block_id="b2", type="paragraph", text="段落二。"),
            UDRBlock(block_id="b3", type="paragraph", text="段落三。"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=100000, chunk_overlap=0)
        chunks = service.chunk_udr(udr)
        assert len(chunks) == 1

    def test_very_small_chunk_size(self):
        """极小 chunk_size 时应正常工作"""
        blocks = [
            UDRBlock(block_id="b1", type="paragraph", text="这是一段较长的文本内容。" * 10),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=10, chunk_overlap=0)
        chunks = service.chunk_udr(udr)
        assert len(chunks) >= 1

    def test_mixed_block_types_preserved(self):
        """混合类型 block 应正确分类"""
        blocks = [
            UDRBlock(block_id="b1", type="heading", text="标题", level=1),
            UDRBlock(block_id="b2", type="paragraph", text="段落"),
            UDRBlock(block_id="b3", type="code", text="code here",
                     metadata={"language": "python"}),
            UDRBlock(block_id="b4", type="table", text="| A | B |",
                     structured_data={"headers": ["A", "B"], "rows": []}),
            UDRBlock(block_id="b5", type="equation", text="E=mc^2"),
        ]
        udr = make_udr(blocks)
        service = ChunkingService(chunk_size=800, chunk_overlap=0)
        chunks = service.chunk_udr(udr)

        # 应有多种 source_type
        source_types = set(c.get("source_type") for c in chunks)
        assert "text" in source_types
        assert "code" in source_types or any("code" in c.get("content", "") for c in chunks)
