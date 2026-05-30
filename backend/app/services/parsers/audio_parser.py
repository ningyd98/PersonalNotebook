"""Audio Parser — 解析音频文件，支持语音转写"""

import uuid
import hashlib
from pathlib import Path
from typing import Optional

from loguru import logger

from app.services.parsers.base import (
    BaseParser, ParserRegistry, UDRAsset, UDRBlock, UnifiedDocument,
)

try:
    from mutagen import File as MutagenFile
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False
    logger.debug("mutagen not installed; audio metadata will be limited")


class AudioParser(BaseParser):
    supported_mime_types = [
        "audio/mpeg", "audio/wav", "audio/ogg", "audio/flac",
        "audio/aac", "audio/mp4", "audio/x-m4a", "audio/webm",
    ]
    supported_extensions = [".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".wma", ".webm"]

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
                ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
                ".flac": "audio/flac", ".aac": "audio/aac", ".m4a": "audio/mp4",
                ".wma": "audio/x-ms-wma", ".webm": "audio/webm",
            }
            mime_type = mime_map.get(ext, "audio/mpeg")

            # Get duration from mutagen
            duration_seconds = None
            audio_metadata = {}
            if HAS_MUTAGEN:
                try:
                    audio = MutagenFile(file_path)
                    if audio is not None:
                        duration_seconds = audio.info.length if hasattr(audio.info, "length") else None
                        if hasattr(audio, "tags") and audio.tags:
                            for key in ["title", "artist", "album", "genre", "date"]:
                                if key in audio.tags:
                                    audio_metadata[key] = str(audio.tags[key])
                except Exception as e:
                    logger.debug(f"Failed to read audio metadata: {e}")

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
                logger.debug(f"Failed to upload audio to MinIO: {e}")

            asset = UDRAsset(
                asset_id=asset_id,
                asset_type="audio",
                asset_uri=asset_uri,
                mime_type=mime_type,
                file_size=file_size,
                duration_seconds=duration_seconds,
                checksum=checksum,
                metadata=audio_metadata,
            )
            assets.append(asset)

            blocks.append(UDRBlock(
                block_id=f"{doc_id}_b0000",
                type="paragraph",
                text=f"[Audio: {filename}]",
                metadata={
                    "duration_seconds": duration_seconds,
                    "mime_type": mime_type,
                    **audio_metadata,
                },
            ))

            # Transcribe if requested
            use_transcription = options.get("audio_transcription", False) or options.get("transcribe", False)
            if use_transcription:
                try:
                    from faster_whisper import WhisperModel
                    model = WhisperModel("base", device="cpu", compute_type="int8")
                    segments, info = model.transcribe(file_path, language="zh")
                    transcript = ""
                    for segment in segments:
                        transcript += segment.text
                        blocks.append(UDRBlock(
                            block_id=f"{doc_id}_b{len(blocks):04d}",
                            type="transcript",
                            text=segment.text.strip(),
                            start_time=segment.start,
                            end_time=segment.end,
                            metadata={"source": "faster_whisper", "language": info.language},
                        ))
                except ImportError:
                    logger.warning("faster-whisper not installed; audio transcription skipped")
                except Exception as e:
                    logger.warning(f"Audio transcription failed: {e}")

            return UnifiedDocument(
                document_id=doc_id,
                source={
                    "filename": filename,
                    "mime_type": mime_type,
                    "source_uri": str(path.absolute()),
                },
                metadata={
                    "title": audio_metadata.get("title", filename),
                    "duration_seconds": duration_seconds,
                    "transcription_enabled": use_transcription,
                    **audio_metadata,
                },
                blocks=blocks,
                assets=assets,
            )

        except Exception as e:
            logger.error(f"Audio parsing failed: {e}")
            return self._fallback_parse(file_path)

    @staticmethod
    def _fallback_parse(file_path: str) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        return UnifiedDocument(
            document_id=doc_id,
            source={
                "filename": path.name,
                "mime_type": "audio/mpeg",
                "source_uri": str(path.absolute()),
            },
            metadata={"title": path.name, "warning": "Audio parsing failed"},
            blocks=[
                UDRBlock(
                    block_id=f"{doc_id}_b0000",
                    type="paragraph",
                    text=f"[Audio file: {path.name}]",
                ),
            ],
        )


# 注册
ParserRegistry.register(AudioParser())
