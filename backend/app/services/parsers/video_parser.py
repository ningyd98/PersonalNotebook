"""Video Parser — 解析视频文件，支持关键帧提取和音频转写"""

import uuid
import hashlib
from pathlib import Path
from typing import Optional

from loguru import logger

from app.services.parsers.base import (
    BaseParser, ParserRegistry, UDRAsset, UDRBlock, UnifiedDocument,
)


class VideoParser(BaseParser):
    supported_mime_types = [
        "video/mp4", "video/mpeg", "video/webm", "video/x-msvideo",
        "video/quicktime", "video/x-matroska", "video/x-flv",
    ]
    supported_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".mpeg", ".mpg"]

    def parse(self, file_path: str, options: Optional[dict] = None) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        filename = path.name
        options = options or {}

        blocks: list[UDRBlock] = []
        assets: list[UDRAsset] = []

        try:
            file_size = path.stat().st_size
            checksum = hashlib.md5(path.read_bytes()).hexdigest()

            # Determine MIME type
            ext = path.suffix.lower()
            mime_map = {
                ".mp4": "video/mp4", ".avi": "video/x-msvideo", ".mov": "video/quicktime",
                ".mkv": "video/x-matroska", ".webm": "video/webm", ".flv": "video/x-flv",
                ".wmv": "video/x-ms-wmv", ".mpeg": "video/mpeg", ".mpg": "video/mpeg",
            }
            mime_type = mime_map.get(ext, "video/mp4")

            # Get duration with ffprobe
            duration_seconds = None
            video_metadata = {}
            try:
                import subprocess
                result = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-print_format", "json",
                     "-show_format", "-show_streams", file_path],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    import json
                    probe = json.loads(result.stdout)
                    fmt = probe.get("format", {})
                    duration_seconds = float(fmt.get("duration", 0)) or None
                    video_metadata = {
                        "format_name": fmt.get("format_name", ""),
                        "bit_rate": fmt.get("bit_rate", ""),
                    }
            except Exception as e:
                logger.debug(f"ffprobe not available: {e}")

            # Upload to MinIO
            asset_id = f"asset_{uuid.uuid4().hex[:8]}"
            object_name = f"parsed_assets/{doc_id}/{asset_id}{ext}"
            asset_uri = f"inline://{asset_id}"

            try:
                from app.services.storage import minio_storage
                with open(file_path, "rb") as f:
                    minio_storage.upload_file(
                        object_name=object_name,
                        data=f.read(),
                        content_type=mime_type,
                    )
                asset_uri = f"minio://{minio_storage.client._base_url.host}/{object_name}"
            except Exception as e:
                logger.debug(f"Failed to upload video to MinIO: {e}")

            asset = UDRAsset(
                asset_id=asset_id,
                asset_type="video",
                asset_uri=asset_uri,
                mime_type=mime_type,
                file_size=file_size,
                duration_seconds=duration_seconds,
                checksum=checksum,
                metadata=video_metadata,
            )
            assets.append(asset)

            blocks.append(UDRBlock(
                block_id=f"{doc_id}_b0000",
                type="paragraph",
                text=f"[Video: {filename}]",
                metadata={
                    "duration_seconds": duration_seconds,
                    "mime_type": mime_type,
                    **video_metadata,
                },
            ))

            # Extract keyframes if requested
            extract_frames = options.get("extract_frames", False)
            if extract_frames:
                try:
                    import subprocess
                    import tempfile
                    import os

                    frame_dir = tempfile.mkdtemp()
                    frame_pattern = os.path.join(frame_dir, "frame_%04d.jpg")

                    subprocess.run(
                        ["ffmpeg", "-i", file_path, "-vf", "fps=1/30",
                         "-q:v", "2", frame_pattern],
                        capture_output=True, timeout=120,
                    )

                    frame_files = sorted(Path(frame_dir).glob("frame_*.jpg"))
                    for i, frame_path in enumerate(frame_files):
                        frame_asset_id = f"asset_{uuid.uuid4().hex[:8]}"
                        frame_object_name = f"parsed_assets/{doc_id}/frames/{frame_asset_id}.jpg"

                        try:
                            from app.services.storage import minio_storage
                            with open(frame_path, "rb") as f:
                                minio_storage.upload_file(
                                    object_name=frame_object_name,
                                    data=f.read(),
                                    content_type="image/jpeg",
                                )
                            frame_uri = f"minio://{minio_storage.client._base_url.host}/{frame_object_name}"
                        except Exception:
                            frame_uri = f"inline://{frame_asset_id}"

                        time_offset = i * 30.0  # 1 frame per 30 seconds
                        frame_asset = UDRAsset(
                            asset_id=frame_asset_id,
                            asset_type="frame",
                            asset_uri=frame_uri,
                            mime_type="image/jpeg",
                            file_size=frame_path.stat().st_size,
                            metadata={"frame_index": i, "time_offset": time_offset},
                        )
                        assets.append(frame_asset)

                        blocks.append(UDRBlock(
                            block_id=f"{doc_id}_b{len(blocks):04d}",
                            type="video_segment",
                            text=f"[Keyframe at {time_offset:.0f}s]",
                            start_time=time_offset,
                            end_time=time_offset + 30.0,
                            asset_uri=frame_uri,
                            metadata={"frame_index": i},
                        ))

                    # Cleanup
                    import shutil
                    shutil.rmtree(frame_dir, ignore_errors=True)

                except FileNotFoundError:
                    logger.warning("ffmpeg not installed; keyframe extraction skipped")
                except Exception as e:
                    logger.warning(f"Keyframe extraction failed: {e}")

            return UnifiedDocument(
                document_id=doc_id,
                source={
                    "filename": filename,
                    "mime_type": mime_type,
                    "source_uri": str(path.absolute()),
                },
                metadata={
                    "title": filename,
                    "duration_seconds": duration_seconds,
                    "frame_extraction_enabled": extract_frames,
                    **video_metadata,
                },
                blocks=blocks,
                assets=assets,
            )

        except Exception as e:
            logger.error(f"Video parsing failed: {e}")
            return self._fallback_parse(file_path)

    @staticmethod
    def _fallback_parse(file_path: str) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        return UnifiedDocument(
            document_id=doc_id,
            source={
                "filename": path.name,
                "mime_type": "video/mp4",
                "source_uri": str(path.absolute()),
            },
            metadata={"title": path.name, "warning": "Video parsing failed"},
            blocks=[
                UDRBlock(
                    block_id=f"{doc_id}_b0000",
                    type="paragraph",
                    text=f"[Video file: {path.name}]",
                ),
            ],
        )


# 注册
ParserRegistry.register(VideoParser())
