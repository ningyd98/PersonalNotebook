"""Archive Parser — 解析压缩包文件，递归解析内部文件"""

import os
import shutil
import tempfile
import uuid
import zipfile
import tarfile
from pathlib import Path
from typing import Optional

from loguru import logger

from app.services.parsers.base import (
    BaseParser, ParserRegistry, UDRBlock, UDRRelation, UnifiedDocument,
)

try:
    import py7zr
    HAS_PY7ZR = True
except ImportError:
    HAS_PY7ZR = False
    logger.warning("py7zr not installed; 7z format will be skipped")


class ArchiveParser(BaseParser):
    supported_mime_types = [
        "application/zip",
        "application/x-tar",
        "application/gzip",
        "application/x-gzip",
        "application/x-bzip2",
        "application/x-xz",
        "application/x-7z-compressed",
    ]
    supported_extensions = [
        ".zip", ".tar", ".tar.gz", ".tgz",
        ".tar.bz2", ".tar.xz", ".7z",
    ]

    # 跳过的目录模式
    SKIP_DIRS = {"__MACOSX", ".git", ".svn", "__pycache__", ".idea", ".vscode"}
    # 跳过的隐藏文件前缀
    SKIP_PREFIXES = {".", "~"}

    # 支持的压缩格式识别
    ARCHIVE_TYPES = {
        ".zip": "zip",
        ".tar": "tar",
        ".tar.gz": "tar_gz",
        ".tgz": "tar_gz",
        ".tar.bz2": "tar_bz2",
        ".tar.xz": "tar_xz",
        ".7z": "7z",
    }

    def parse(self, file_path: str, options: Optional[dict] = None) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        filename = path.name
        options = options or {}

        archive_type = self._detect_archive_type(path)
        mime_type = self._get_mime_type(archive_type)

        blocks: list[UDRBlock] = []
        relations: list[UDRRelation] = []
        inner_file_list: list[str] = []

        tmp_dir = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="archive_parser_")
            logger.info(f"Extracting archive {filename} to {tmp_dir}")

            # 解压
            extracted = self._extract(path, archive_type, tmp_dir)
            if not extracted:
                return self._fallback_parse(file_path, doc_id, filename, mime_type, "Extraction failed")

            # 递归扫描解压后的文件
            for root, dirs, files in os.walk(tmp_dir):
                # 过滤跳过的目录（就地修改 dirs 影响 os.walk 遍历）
                dirs[:] = [
                    d for d in dirs
                    if d not in self.SKIP_DIRS and not d.startswith(".")
                ]

                for fname in files:
                    # 跳过隐藏文件
                    if any(fname.startswith(p) for p in self.SKIP_PREFIXES):
                        continue

                    inner_path = os.path.join(root, fname)
                    # 计算相对路径（在压缩包内的路径）
                    rel_path = os.path.relpath(inner_path, tmp_dir)

                    inner_file_list.append(rel_path)

                    # 创建内部文件 block
                    blocks.append(UDRBlock(
                        block_id=f"{doc_id}_b{len(blocks):04d}",
                        type="paragraph",
                        text=rel_path,
                        metadata={
                            "inner_file": rel_path,
                            "inner_file_size": os.path.getsize(inner_path) if os.path.exists(inner_path) else 0,
                        },
                    ))

                    # 使用 ParserRegistry 递归解析内部文件
                    inner_doc = self._parse_inner_file(inner_path, rel_path, options)
                    if inner_doc:
                        # 将内部文档的 blocks 合并
                        for inner_block in inner_doc.blocks:
                            inner_block.section_path = rel_path
                            blocks.append(inner_block)

                        # 建立 derived_from 关系
                        relations.append(UDRRelation(
                            source_document_id=doc_id,
                            target_document_id=inner_doc.document_id,
                            relation_type="derived_from",
                            metadata={"inner_file": rel_path},
                        ))

            return UnifiedDocument(
                document_id=doc_id,
                source={
                    "filename": filename,
                    "mime_type": mime_type,
                    "source_uri": str(path.absolute()),
                },
                metadata={
                    "title": filename,
                    "archive_type": archive_type,
                    "inner_file_count": len(inner_file_list),
                    "inner_files": inner_file_list,
                },
                blocks=blocks,
                relations=relations,
            )

        except Exception as e:
            logger.error(f"Archive parsing failed: {e}")
            return self._fallback_parse(file_path, doc_id, filename, mime_type, str(e))

        finally:
            # 清理临时目录
            if tmp_dir and os.path.exists(tmp_dir):
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    logger.debug(f"Cleaned up temp directory: {tmp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp directory {tmp_dir}: {e}")

    def _detect_archive_type(self, path: Path) -> str:
        """根据扩展名检测压缩包类型"""
        name = path.name.lower()
        # 按照最长匹配优先
        for ext in sorted(self.ARCHIVE_TYPES.keys(), key=len, reverse=True):
            if name.endswith(ext):
                return self.ARCHIVE_TYPES[ext]
        return "unknown"

    @staticmethod
    def _get_mime_type(archive_type: str) -> str:
        mime_map = {
            "zip": "application/zip",
            "tar": "application/x-tar",
            "tar_gz": "application/gzip",
            "tar_bz2": "application/x-bzip2",
            "tar_xz": "application/x-xz",
            "7z": "application/x-7z-compressed",
        }
        return mime_map.get(archive_type, "application/octet-stream")

    def _extract(self, path: Path, archive_type: str, target_dir: str) -> bool:
        """解压压缩包到目标目录"""
        try:
            if archive_type == "zip":
                return self._extract_zip(path, target_dir)
            elif archive_type == "tar":
                return self._extract_tar(path, target_dir)
            elif archive_type in ("tar_gz", "tar_bz2", "tar_xz"):
                return self._extract_tar_compressed(path, target_dir, archive_type)
            elif archive_type == "7z":
                return self._extract_7z(path, target_dir)
            else:
                logger.warning(f"Unknown archive type: {archive_type}")
                return False
        except Exception as e:
            logger.error(f"Extraction failed for {path.name}: {e}")
            return False

    @staticmethod
    def _extract_zip(path: Path, target_dir: str) -> bool:
        """解压 ZIP 文件"""
        with zipfile.ZipFile(str(path), "r") as zf:
            # 安全检查：防止 zip slip 攻击
            for member in zf.namelist():
                member_path = os.path.join(target_dir, member)
                if not os.path.abspath(member_path).startswith(os.path.abspath(target_dir)):
                    logger.warning(f"Zip slip detected: {member}, skipping")
                    continue
            zf.extractall(target_dir)
        return True

    @staticmethod
    def _extract_tar(path: Path, target_dir: str) -> bool:
        """解压 TAR 文件"""
        with tarfile.open(str(path), "r:") as tf:
            # 安全检查
            for member in tf.getmembers():
                member_path = os.path.join(target_dir, member.name)
                if not os.path.abspath(member_path).startswith(os.path.abspath(target_dir)):
                    logger.warning(f"Tar slip detected: {member.name}, skipping")
                    continue
            tf.extractall(target_dir)
        return True

    @staticmethod
    def _extract_tar_compressed(path: Path, target_dir: str, archive_type: str) -> bool:
        """解压压缩的 TAR 文件（.tar.gz, .tar.bz2, .tar.xz）"""
        mode_map = {
            "tar_gz": "r:gz",
            "tar_bz2": "r:bz2",
            "tar_xz": "r:xz",
        }
        mode = mode_map.get(archive_type, "r:*")
        with tarfile.open(str(path), mode) as tf:
            # 安全检查
            for member in tf.getmembers():
                member_path = os.path.join(target_dir, member.name)
                if not os.path.abspath(member_path).startswith(os.path.abspath(target_dir)):
                    logger.warning(f"Tar slip detected: {member.name}, skipping")
                    continue
            tf.extractall(target_dir)
        return True

    @staticmethod
    def _extract_7z(path: Path, target_dir: str) -> bool:
        """解压 7z 文件"""
        if not HAS_PY7ZR:
            logger.warning("py7zr not installed; skipping 7z extraction")
            return False

        with py7zr.SevenZipFile(str(path), mode="r") as z:
            z.extractall(path=target_dir)
        return True

    @staticmethod
    def _parse_inner_file(
        inner_path: str, rel_path: str, options: dict
    ) -> Optional[UnifiedDocument]:
        """使用 ParserRegistry 递归解析内部文件"""
        try:
            inner = Path(inner_path)
            ext = inner.suffix.lower()

            # 查找合适的 parser
            parser = ParserRegistry.get_parser(extension=ext)
            if parser is None:
                # 尝试通过 MIME 类型查找
                # 简单的扩展名到 MIME 映射
                mime_guess = _guess_mime_by_ext(ext)
                if mime_guess:
                    parser = ParserRegistry.get_parser(mime_type=mime_guess)

            if parser is None:
                logger.debug(f"No parser found for inner file: {rel_path}")
                return None

            inner_doc = parser.parse(inner_path, options)
            return inner_doc

        except Exception as e:
            logger.warning(f"Failed to parse inner file {rel_path}: {e}")
            return None

    @staticmethod
    def _fallback_parse(
        file_path: str,
        doc_id: str,
        filename: str,
        mime_type: str,
        error: str = "",
    ) -> UnifiedDocument:
        """兜底方案"""
        path = Path(file_path)
        return UnifiedDocument(
            document_id=doc_id,
            source={
                "filename": filename,
                "mime_type": mime_type,
                "source_uri": str(path.absolute()),
            },
            metadata={
                "title": filename,
                "warning": "Archive extraction failed",
                "error": error,
            },
            blocks=[
                UDRBlock(
                    block_id=f"{doc_id}_b0000",
                    type="paragraph",
                    text=f"[Archive file: {filename} — extraction failed]",
                ),
            ],
        )


def _guess_mime_by_ext(ext: str) -> Optional[str]:
    """简单扩展名到 MIME 类型映射"""
    mime_map = {
        ".md": "text/markdown",
        ".markdown": "text/markdown",
        ".pdf": "application/pdf",
        ".tex": "text/x-latex",
        ".latex": "text/x-latex",
        ".py": "text/x-python",
        ".js": "text/javascript",
        ".ts": "text/x-typescript",
        ".java": "text/x-java",
        ".go": "text/x-go",
        ".cpp": "text/x-c++src",
        ".c": "text/x-csrc",
        ".rs": "text/x-rust",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".zip": "application/zip",
        ".tar": "application/x-tar",
        ".7z": "application/x-7z-compressed",
    }
    return mime_map.get(ext.lower())


# 注册
ParserRegistry.register(ArchiveParser())
