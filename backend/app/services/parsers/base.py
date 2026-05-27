"""
Parser 基类、UnifiedDocument、ParserRegistry
所有文件解析必须先转换为 UnifiedDocument
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class UDRBlock:
    """Unified Document Representation — 统一文档块"""
    block_id: str
    type: str  # heading | paragraph | table | image | equation | code | transcript | video_segment | list | quote | metadata | annotation
    text: str = ""
    level: Optional[int] = None
    page: Optional[int] = None
    slide: Optional[int] = None
    sheet_name: Optional[str] = None
    cell_range: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    bbox: Optional[dict] = None
    section_path: Optional[str] = None
    asset_uri: Optional[str] = None
    ocr_text: Optional[str] = None
    structured_data: Optional[dict] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class UDRAsset:
    """统一文档资产"""
    asset_id: str
    asset_type: str  # image | audio | video | frame | attachment
    asset_uri: str
    mime_type: str = "application/octet-stream"
    file_size: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    checksum: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class UDRRelation:
    """统一文档关系"""
    source_document_id: str
    target_document_id: str
    relation_type: str  # links_to | cites | mentions | derived_from | attachment_of
    metadata: dict = field(default_factory=dict)


@dataclass
class UnifiedDocument:
    """统一文档表示 — 所有 Parser 的标准输出"""
    document_id: str
    source: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    blocks: list[UDRBlock] = field(default_factory=list)
    assets: list[UDRAsset] = field(default_factory=list)
    relations: list[UDRRelation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "source": self.source,
            "metadata": self.metadata,
            "blocks": [b.to_dict() for b in self.blocks],
            "assets": [asdict(a) for a in self.assets],
            "relations": [asdict(r) for r in self.relations],
        }


class BaseParser(ABC):
    """文档解析器基类"""
    supported_mime_types: list[str] = []
    supported_extensions: list[str] = []

    @abstractmethod
    def parse(self, file_path: str, options: Optional[dict] = None) -> UnifiedDocument:
        """解析文件为 UnifiedDocument"""
        ...


class ParserRegistry:
    """Parser 注册中心，根据 mime_type / extension 自动选择 parser"""

    _parsers: list[BaseParser] = []
    _mime_map: dict[str, BaseParser] = {}
    _ext_map: dict[str, BaseParser] = {}

    @classmethod
    def register(cls, parser: BaseParser) -> None:
        cls._parsers.append(parser)
        for mt in parser.supported_mime_types:
            cls._mime_map[mt] = parser
        for ext in parser.supported_extensions:
            cls._ext_map[ext] = parser

    @classmethod
    def get_parser(
        cls,
        mime_type: Optional[str] = None,
        extension: Optional[str] = None,
    ) -> Optional[BaseParser]:
        """根据 mime_type 或 extension 获取 parser"""
        if mime_type and mime_type in cls._mime_map:
            return cls._mime_map[mime_type]
        if extension:
            ext = extension.lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            if ext in cls._ext_map:
                return cls._ext_map[ext]
        if mime_type:
            # 模糊匹配
            base_type = mime_type.split("/")[0]
            for mt, parser in cls._mime_map.items():
                if mt.startswith(base_type):
                    return parser
        return None

    @classmethod
    def list_parsers(cls) -> list[dict]:
        """列出所有已注册的 parser"""
        return [
            {
                "mime_types": p.supported_mime_types,
                "extensions": p.supported_extensions,
                "class": p.__class__.__name__,
            }
            for p in cls._parsers
        ]
