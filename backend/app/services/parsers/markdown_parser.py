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
        """按标题层级、表格、代码块解析"""
        blocks = []
        lines = content.split("\n")
        current_section = []
        section_path = ""
        heading_stack = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 标题
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                if current_section:
                    blocks.append(self._make_paragraph_block(doc_id, len(blocks), current_section, section_path))
                    current_section = []
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, heading_text))
                section_path = " > ".join(h[1] for h in heading_stack)
                blocks.append(UDRBlock(
                    block_id=f"{doc_id}_b{len(blocks):04d}", type="heading",
                    text=heading_text, level=level, section_path=section_path,
                ))
                i += 1
                continue

            # 代码块 ```
            if line.strip().startswith("```"):
                if current_section:
                    blocks.append(self._make_paragraph_block(doc_id, len(blocks), current_section, section_path))
                    current_section = []
                lang = line.strip()[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines):
                    if lines[i].strip().startswith("```"):
                        i += 1
                        break
                    code_lines.append(lines[i])
                    i += 1
                code_text = "\n".join(code_lines)
                if code_text.strip():
                    blocks.append(UDRBlock(
                        block_id=f"{doc_id}_b{len(blocks):04d}", type="code",
                        text=code_text, section_path=section_path,
                        metadata={"language": lang} if lang else {},
                    ))
                continue

            # 表格 (连续 |...| 行)
            if line.strip().startswith("|") and line.strip().endswith("|"):
                if current_section:
                    blocks.append(self._make_paragraph_block(doc_id, len(blocks), current_section, section_path))
                    current_section = []
                table_lines = []
                while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                # Parse table: extract headers and rows
                rows = []
                for tl in table_lines:
                    cells = [c.strip() for c in tl.strip().strip("|").split("|")]
                    # Skip separator rows like |---|---|
                    if all(re.match(r"^[-:]+$", c) for c in cells):
                        continue
                    rows.append(cells)
                if rows:
                    headers = rows[0] if len(rows) > 0 else []
                    data_rows = rows[1:] if len(rows) > 1 else []
                    table_text = "\n".join(table_lines)
                    blocks.append(UDRBlock(
                        block_id=f"{doc_id}_b{len(blocks):04d}", type="table",
                        text=table_text, section_path=section_path,
                        structured_data={"headers": headers, "rows": data_rows},
                    ))
                continue

            # 任务列表
            task_match = re.match(r"^(\s*)[-*+]\s+\[([ x])\]\s+(.+)$", line)
            if task_match:
                if current_section:
                    blocks.append(self._make_paragraph_block(doc_id, len(blocks), current_section, section_path))
                    current_section = []
                checked = task_match.group(2) == "x"
                blocks.append(UDRBlock(
                    block_id=f"{doc_id}_b{len(blocks):04d}", type="list",
                    text=task_match.group(3), section_path=section_path,
                    metadata={"checked": checked, "list_type": "task"},
                ))
                i += 1
                continue

            # 空行 = 段落边界
            if not line.strip():
                if current_section:
                    blocks.append(self._make_paragraph_block(doc_id, len(blocks), current_section, section_path))
                    current_section = []
                i += 1
                continue

            current_section.append(line)
            i += 1

        if current_section:
            blocks.append(self._make_paragraph_block(doc_id, len(blocks), current_section, section_path))

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
