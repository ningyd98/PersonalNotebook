"""Markdown Parser — 支持 Obsidian 语法、frontmatter、wikilinks"""

import re
import uuid
from pathlib import Path
from typing import Optional

import frontmatter
from loguru import logger

from app.services.parsers.base import (
    BaseParser, ParserRegistry, UDRBlock, UnifiedDocument,
)


class MarkdownParser(BaseParser):
    supported_mime_types = ["text/markdown", "text/x-markdown"]
    supported_extensions = [".md", ".markdown"]

    def parse(self, file_path: str, options: Optional[dict] = None) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        filename = path.name

        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # 解析 frontmatter
        try:
            post = frontmatter.loads(raw_text)
            fm_meta = dict(post.metadata)
            content = post.content
        except Exception:
            fm_meta = {}
            content = raw_text

        blocks = self._parse_content(content, doc_id)
        title = fm_meta.get("title", filename)
        tags = fm_meta.get("tags", [])

        udr = UnifiedDocument(
            document_id=doc_id,
            source={
                "filename": filename,
                "mime_type": "text/markdown",
                "source_uri": str(path.absolute()),
            },
            metadata={
                "title": title,
                "author": fm_meta.get("author", ""),
                "tags": tags if isinstance(tags, list) else [tags],
                "frontmatter": fm_meta,
            },
            blocks=blocks,
        )

        # 提取 wikilinks 关系
        relations = self._extract_wikilinks(content, doc_id)
        udr.relations = relations

        return udr

    def _parse_content(self, content: str, doc_id: str) -> list[UDRBlock]:
        """按标题层级和段落解析"""
        blocks = []
        lines = content.split("\n")
        current_section = []
        current_heading = ""
        section_path = ""
        heading_stack = []

        for line in lines:
            # 检测标题
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                # 先保存当前段落
                if current_section:
                    blocks.append(self._make_paragraph_block(
                        doc_id, len(blocks), current_section, section_path
                    ))
                    current_section = []

                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                # 更新 section_path
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, heading_text))
                section_path = " > ".join(h[1] for h in heading_stack)

                blocks.append(UDRBlock(
                    block_id=f"{doc_id}_b{len(blocks):04d}",
                    type="heading",
                    text=heading_text,
                    level=level,
                    section_path=section_path,
                ))
                current_heading = heading_text
                continue

            # 检测表格
            if line.startswith("|") and line.endswith("|"):
                if current_section:
                    blocks.append(self._make_paragraph_block(
                        doc_id, len(blocks), current_section, section_path
                    ))
                    current_section = []
                # 表格检测在外部处理
                continue

            # 检测代码块
            if line.startswith("```"):
                if current_section:
                    blocks.append(self._make_paragraph_block(
                        doc_id, len(blocks), current_section, section_path
                    ))
                    current_section = []
                # 简化处理：跳过代码块边界标记
                continue

            # 检测任务列表
            task_match = re.match(r"^(\s*)[-*+]\s+\[([ x])\]\s+(.+)$", line)
            if task_match:
                if current_section:
                    blocks.append(self._make_paragraph_block(
                        doc_id, len(blocks), current_section, section_path
                    ))
                    current_section = []
                task_text = task_match.group(3)
                checked = task_match.group(2) == "x"
                blocks.append(UDRBlock(
                    block_id=f"{doc_id}_b{len(blocks):04d}",
                    type="list",
                    text=task_text,
                    section_path=section_path,
                    metadata={"checked": checked, "list_type": "task"},
                ))
                continue

            # 空行：段落边界
            if not line.strip():
                if current_section:
                    blocks.append(self._make_paragraph_block(
                        doc_id, len(blocks), current_section, section_path
                    ))
                    current_section = []
                continue

            current_section.append(line)

        # 处理最后一段
        if current_section:
            blocks.append(self._make_paragraph_block(
                doc_id, len(blocks), current_section, section_path
            ))

        return blocks

    @staticmethod
    def _make_paragraph_block(
        doc_id: str, idx: int, lines: list[str], section_path: str
    ) -> UDRBlock:
        text = "\n".join(lines).strip()
        return UDRBlock(
            block_id=f"{doc_id}_b{idx:04d}",
            type="paragraph",
            text=text,
            section_path=section_path,
        )

    @staticmethod
    def _extract_wikilinks(content: str, doc_id: str) -> list:
        """提取 Obsidian 双链 [[link]]"""
        from app.services.parsers.base import UDRRelation
        relations = []
        pattern = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]+)?\]\]")
        for match in pattern.finditer(content):
            target = match.group(1).strip()
            relations.append(UDRRelation(
                source_document_id=doc_id,
                target_document_id=target,
                relation_type="links_to",
            ))
        return relations


# 注册
ParserRegistry.register(MarkdownParser())
