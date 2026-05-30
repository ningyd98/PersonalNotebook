"""LaTeX Parser — 解析 LaTeX 文档"""

import uuid
import re
from pathlib import Path
from typing import Optional

from loguru import logger

from app.services.parsers.base import (
    BaseParser, ParserRegistry, UDRBlock, UnifiedDocument,
)


class LatexParser(BaseParser):
    supported_mime_types = ["application/x-latex", "text/x-latex"]
    supported_extensions = [".tex", ".latex"]

    def parse(self, file_path: str, options: Optional[dict] = None) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        filename = path.name
        options = options or {}

        blocks: list[UDRBlock] = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Remove comments
            content_no_comments = re.sub(r'(?<!\\)%.*$', '', content, flags=re.MULTILINE)

            # Extract equations
            for eq_match in re.finditer(r'\\begin\{equation\*?\}(.*?)\\end\{equation\*?\}', content_no_comments, re.DOTALL):
                blocks.append(UDRBlock(
                    block_id=f"{doc_id}_b{len(blocks):04d}",
                    type="equation",
                    text=eq_match.group(0),
                    metadata={"source": "latex_equation"},
                ))

            # Extract theorem environments
            theorem_envs = ["theorem", "definition", "lemma", "proof", "corollary", "proposition"]
            for env in theorem_envs:
                for m in re.finditer(rf'\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}', content_no_comments, re.DOTALL):
                    blocks.append(UDRBlock(
                        block_id=f"{doc_id}_b{len(blocks):04d}",
                        type="annotation",
                        text=m.group(0),
                        metadata={"env_type": env},
                    ))

            # Extract labels, refs, cites
            labels = re.findall(r'\\label\{([^}]*)\}', content_no_comments)
            refs = re.findall(r'\\ref\{([^}]*)\}', content_no_comments)
            cites = re.findall(r'\\cite\{([^}]*)\}', content_no_comments)

            # Extract title
            title_match = re.search(r'\\title\{([^}]*)\}', content_no_comments)
            title = title_match.group(1) if title_match else filename

            # Extract sections
            section_pattern = re.compile(
                r'\\(part|chapter|section|subsection|subsubsection)\*?\{([^}]*)\}'
            )

            last_end = 0
            headings = []
            for match in section_pattern.finditer(content_no_comments):
                # Add content before this heading as paragraph
                pre_text = content_no_comments[last_end:match.start()].strip()
                if pre_text:
                    # Clean LaTeX commands for display
                    clean_text = self._clean_latex(pre_text)
                    if clean_text.strip():
                        blocks.append(UDRBlock(
                            block_id=f"{doc_id}_b{len(blocks):04d}",
                            type="paragraph",
                            text=clean_text.strip(),
                            section_path=" > ".join(h[1] for h in headings),
                        ))

                cmd = match.group(1)
                heading_text = match.group(2)
                level_map = {"part": 1, "chapter": 1, "section": 2, "subsection": 3, "subsubsection": 4}
                level = level_map.get(cmd, 2)

                # Update heading stack
                while headings and headings[-1][0] >= level:
                    headings.pop()
                headings.append((level, heading_text))

                blocks.append(UDRBlock(
                    block_id=f"{doc_id}_b{len(blocks):04d}",
                    type="heading",
                    text=heading_text,
                    level=level,
                    section_path=" > ".join(h[1] for h in headings),
                ))

                last_end = match.end()

            # Remaining content
            remaining = content_no_comments[last_end:].strip()
            if remaining:
                clean_text = self._clean_latex(remaining)
                if clean_text.strip():
                    blocks.append(UDRBlock(
                        block_id=f"{doc_id}_b{len(blocks):04d}",
                        type="paragraph",
                        text=clean_text.strip(),
                    ))

            # If no structured content found, treat entire file as paragraphs
            if not blocks:
                clean_text = self._clean_latex(content_no_comments)
                paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
                for i, para in enumerate(paragraphs):
                    blocks.append(UDRBlock(
                        block_id=f"{doc_id}_b{len(blocks):04d}",
                        type="paragraph",
                        text=para,
                    ))

            return UnifiedDocument(
                document_id=doc_id,
                source={
                    "filename": filename,
                    "mime_type": "application/x-latex",
                    "source_uri": str(path.absolute()),
                },
                metadata={
                    "title": title,
                    "labels": labels,
                    "refs": refs,
                    "cites": cites,
                },
                blocks=blocks,
            )

        except Exception as e:
            logger.error(f"LaTeX parsing failed: {e}")
            return self._fallback_parse(file_path)

    @staticmethod
    def _clean_latex(text: str) -> str:
        """Basic LaTeX command removal for readable text"""
        # Remove common commands but keep their arguments
        text = re.sub(r'\\(?:textbf|textit|emph|underline)\{([^}]*)\}', r'\1', text)
        text = re.sub(r'\\(?:ref|label|cite)\{[^}]*\}', '', text)
        text = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', text)
        # Remove remaining commands
        text = re.sub(r'\\[a-zA-Z]+', '', text)
        # Remove braces
        text = re.sub(r'[{}]', '', text)
        # Remove math delimiters
        text = re.sub(r'\$+', '', text)
        # Remove environments
        text = re.sub(r'\\begin\{[^}]*\}', '', text)
        text = re.sub(r'\\end\{[^}]*\}', '', text)
        return text.strip()

    @staticmethod
    def _fallback_parse(file_path: str) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        return UnifiedDocument(
            document_id=doc_id,
            source={
                "filename": path.name,
                "mime_type": "application/x-latex",
                "source_uri": str(path.absolute()),
            },
            metadata={"title": path.name, "warning": "LaTeX parsing failed"},
            blocks=[
                UDRBlock(
                    block_id=f"{doc_id}_b0000",
                    type="paragraph",
                    text=f"[LaTeX file: {path.name} — parsing error]",
                ),
            ],
        )


# 注册
ParserRegistry.register(LatexParser())
