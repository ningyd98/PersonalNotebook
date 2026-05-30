"""Code Parser — 解析源代码文件"""

import uuid
from pathlib import Path
from typing import Optional

from loguru import logger

from app.services.parsers.base import (
    BaseParser, ParserRegistry, UDRBlock, UnifiedDocument,
)

# Extension to language mapping
EXT_LANG_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".java": "java", ".cpp": "cpp", ".c": "c", ".h": "c",
    ".hpp": "cpp", ".cs": "csharp", ".go": "go", ".rs": "rust",
    ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin",
    ".scala": "scala", ".r": "r", ".R": "r", ".m": "matlab",
    ".sql": "sql", ".sh": "bash", ".bash": "bash", ".zsh": "zsh",
    ".ps1": "powershell", ".lua": "lua", ".pl": "perl",
    ".dart": "dart", ".elm": "elm", ".clj": "clojure", ".ex": "elixir",
    ".exs": "elixir", ".erl": "erlang", ".hs": "haskell",
    ".ml": "ocaml", ".fs": "fsharp", ".vb": "visualbasic",
}

MIME_LANG_MAP = {
    "text/x-python": "python", "text/x-javascript": "javascript",
    "text/x-java": "java", "text/x-c": "c", "text/x-c++": "cpp",
    "text/x-go": "go", "text/x-rust": "rust",
}


class CodeParser(BaseParser):
    supported_mime_types = list(MIME_LANG_MAP.keys()) + ["text/x-script"]
    supported_extensions = list(EXT_LANG_MAP.keys())

    def parse(self, file_path: str, options: Optional[dict] = None) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        filename = path.name
        options = options or {}

        blocks: list[UDRBlock] = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Detect language
            ext = path.suffix.lower()
            language = EXT_LANG_MAP.get(ext, "")

            # File-level heading
            blocks.append(UDRBlock(
                block_id=f"{doc_id}_b0000",
                type="heading",
                text=f"{filename}",
                level=1,
                metadata={"language": language},
            ))

            # Split by functions/classes if possible
            lines = content.split("\n")
            current_chunk: list[str] = []
            chunk_start_line = 1

            def flush_chunk(start_line: int, chunk_lines: list[str]) -> UDRBlock | None:
                text = "\n".join(chunk_lines)
                if not text.strip():
                    return None
                return UDRBlock(
                    block_id=f"{doc_id}_b{len(blocks):04d}",
                    type="code",
                    text=text,
                    metadata={
                        "language": language,
                        "start_line": start_line,
                        "end_line": start_line + len(chunk_lines) - 1,
                    },
                )

            # Simple heuristic: split on top-level function/class definitions
            if language in ("python",):
                def_pattern = __import__("re").compile(r"^(class |def |async def )\w+")
            else:
                def_pattern = __import__("re").compile(r"^(public |private |protected |static |class |function |func |fn |def )")

            for i, line in enumerate(lines, 1):
                if def_pattern.match(line.strip()) and current_chunk:
                    block = flush_chunk(chunk_start_line, current_chunk)
                    if block:
                        blocks.append(block)
                    current_chunk = [line]
                    chunk_start_line = i
                else:
                    current_chunk.append(line)

            # Flush remaining
            if current_chunk:
                block = flush_chunk(chunk_start_line, current_chunk)
                if block:
                    blocks.append(block)

            # If no blocks were added, treat entire file as one code block
            if len(blocks) <= 1:
                blocks = [
                    UDRBlock(
                        block_id=f"{doc_id}_b0000",
                        type="heading",
                        text=filename,
                        level=1,
                        metadata={"language": language},
                    ),
                    UDRBlock(
                        block_id=f"{doc_id}_b0001",
                        type="code",
                        text=content,
                        metadata={"language": language, "start_line": 1, "end_line": len(lines)},
                    ),
                ]

            return UnifiedDocument(
                document_id=doc_id,
                source={
                    "filename": filename,
                    "mime_type": "text/x-script",
                    "source_uri": str(path.absolute()),
                },
                metadata={
                    "title": filename,
                    "language": language,
                    "line_count": len(lines),
                },
                blocks=blocks,
            )

        except Exception as e:
            logger.error(f"Code parsing failed: {e}")
            return self._fallback_parse(file_path)

    @staticmethod
    def _fallback_parse(file_path: str) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        return UnifiedDocument(
            document_id=doc_id,
            source={
                "filename": path.name,
                "mime_type": "text/x-script",
                "source_uri": str(path.absolute()),
            },
            metadata={"title": path.name, "warning": "Code parsing failed"},
            blocks=[
                UDRBlock(
                    block_id=f"{doc_id}_b0000",
                    type="code",
                    text=f"[Code file: {path.name}]",
                ),
            ],
        )


# 注册
ParserRegistry.register(CodeParser())
