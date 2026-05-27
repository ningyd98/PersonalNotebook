"""
数据源 Connector 基类与实现

Connector 负责扫描数据源并返回 FileObject 列表。
"""

import hashlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger


@dataclass
class FileObject:
    """扫描到的文件对象"""
    source_type: str
    source_uri: str
    file_path: str
    filename: str
    mime_type: str
    size: int
    modified_at: str
    checksum: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class BaseConnector(ABC):
    """数据源扫描器基类"""

    @abstractmethod
    def scan(self, config: dict) -> list[FileObject]:
        """扫描数据源，返回 FileObject 列表"""
        ...


# ============================================================
# Upload Connector
# ============================================================
class UploadConnector(BaseConnector):
    """处理上传文件的 Connector"""

    def scan(self, config: dict) -> list[FileObject]:
        """处理上传的文件列表"""
        files = config.get("files", [])
        results = []
        for file_info in files:
            fobj = self._create_file_object(file_info)
            if fobj:
                results.append(fobj)
        return results

    def _create_file_object(self, file_info: dict) -> Optional[FileObject]:
        file_path = file_info.get("file_path", "")
        filename = file_info.get("filename", "") or os.path.basename(file_path)
        mime_type = file_info.get("mime_type", "application/octet-stream")
        size = file_info.get("size", 0)
        checksum = file_info.get("checksum", "")

        if not checksum and os.path.exists(file_path):
            checksum = self._checksum_file(file_path)

        return FileObject(
            source_type="upload",
            source_uri=file_path,
            file_path=file_path,
            filename=filename,
            mime_type=mime_type,
            size=size,
            modified_at=datetime.now().isoformat(),
            checksum=checksum,
            metadata=file_info.get("metadata", {}),
        )

    @staticmethod
    def _checksum_file(file_path: str) -> str:
        try:
            sha = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha.update(chunk)
            return f"sha256:{sha.hexdigest()}"
        except Exception:
            return ""


# ============================================================
# Local Folder Connector
# ============================================================
class LocalFolderConnector(BaseConnector):
    """扫描本地目录"""

    def scan(self, config: dict) -> list[FileObject]:
        path = config.get("path", "")
        recursive = config.get("recursive", True)
        exclude_patterns = config.get("exclude_patterns", [])
        root = Path(path)

        if not root.exists():
            logger.error(f"Path does not exist: {path}")
            return []

        results = []
        pattern = "**/*" if recursive else "*"
        for file_path in root.glob(pattern):
            if not file_path.is_file():
                continue
            if self._should_exclude(file_path, exclude_patterns):
                continue

            fobj = self._create_file_object(str(file_path))
            if fobj:
                results.append(fobj)

        logger.info(f"Scanned {len(results)} files from {path}")
        return results

    @staticmethod
    def _should_exclude(file_path: Path, patterns: list[str]) -> bool:
        for p in patterns:
            if file_path.match(p):
                return True
        return False

    def _create_file_object(self, file_path: str) -> FileObject:
        path = Path(file_path)
        stat = path.stat()
        return FileObject(
            source_type="local_folder",
            source_uri=str(path.parent),
            file_path=str(path),
            filename=path.name,
            mime_type=self._guess_mime_type(path),
            size=stat.st_size,
            modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            checksum=self._checksum_file(file_path),
            metadata={"folder": str(path.parent)},
        )

    @staticmethod
    def _guess_mime_type(path: Path) -> str:
        ext_map = {
            ".md": "text/markdown", ".txt": "text/plain",
            ".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".tex": "application/x-latex", ".html": "text/html",
            ".py": "text/x-python", ".js": "text/javascript", ".ts": "text/typescript",
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
            ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
            ".mp4": "video/mp4", ".mov": "video/quicktime",
            ".zip": "application/zip", ".tar.gz": "application/gzip",
        }
        suffix = path.suffix.lower()
        return ext_map.get(suffix, "application/octet-stream")

    @staticmethod
    def _checksum_file(file_path: str) -> str:
        try:
            sha = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha.update(chunk)
            return f"sha256:{sha.hexdigest()}"
        except Exception:
            return ""


# ============================================================
# NAS Connector
# ============================================================
class NASConnector(LocalFolderConnector):
    """NAS 挂载目录扫描器（继承自 LocalFolderConnector）"""

    def scan(self, config: dict) -> list[FileObject]:
        # 强制使用 source_type = "nas"
        results = super().scan(config)
        for r in results:
            r.source_type = "nas"
        return results


# ============================================================
# Obsidian Connector
# ============================================================
class ObsidianConnector(LocalFolderConnector):
    """Obsidian Vault 扫描器"""

    def scan(self, config: dict) -> list[FileObject]:
        vault_path = config.get("path", "")
        results = super().scan({
            "path": vault_path,
            "recursive": True,
            "exclude_patterns": [".git/*", ".obsidian/*", ".trash/*"],
        })
        for r in results:
            r.source_type = "obsidian"
        return results


# ============================================================
# Connector Registry
# ============================================================
_connector_registry: dict[str, BaseConnector] = {
    "upload": UploadConnector(),
    "local_folder": LocalFolderConnector(),
    "nas": NASConnector(),
    "obsidian": ObsidianConnector(),
}


def get_connector(source_type: str) -> BaseConnector:
    """获取指定类型的 Connector"""
    connector = _connector_registry.get(source_type)
    if connector is None:
        raise ValueError(f"Unknown connector type: {source_type}")
    return connector
