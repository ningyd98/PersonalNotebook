"""Image Parser — 解析图片文件，支持 OCR、EXIF 提取和缩略图生成"""

import uuid
import hashlib
import io
from pathlib import Path
from typing import Optional

from loguru import logger

from app.services.parsers.base import (
    BaseParser, ParserRegistry, UDRAsset, UDRBlock, UnifiedDocument,
)

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("Pillow not installed; Image parsing will be limited")


class ImageParser(BaseParser):
    supported_mime_types = [
        "image/png", "image/jpeg", "image/gif", "image/bmp",
        "image/webp", "image/tiff", "image/svg+xml",
    ]
    supported_extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".svg"]

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
                ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".gif": "image/gif", ".bmp": "image/bmp", ".webp": "image/webp",
                ".tiff": "image/tiff", ".tif": "image/tiff", ".svg": "image/svg+xml",
            }
            mime_type = mime_map.get(ext, "image/png")

            # Get image dimensions if possible
            width, height = None, None
            exif_data = {}
            if HAS_PIL and ext != ".svg":
                try:
                    with PILImage.open(file_path) as img:
                        width, height = img.size
                        # Extract EXIF data
                        raw_exif = img._getexif() if hasattr(img, "_getexif") else None
                        if raw_exif:
                            from PIL import ExifTags
                            for tag_id, value in raw_exif.items():
                                tag = ExifTags.TAGS.get(tag_id, tag_id)
                                if isinstance(value, bytes):
                                    try:
                                        value = value.decode("utf-8", errors="replace")
                                    except Exception:
                                        continue
                                exif_data[str(tag)] = value
                except Exception:
                    pass

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
                logger.debug(f"Failed to upload image to MinIO: {e}")

            asset = UDRAsset(
                asset_id=asset_id,
                asset_type="image",
                asset_uri=asset_uri,
                mime_type=mime_type,
                file_size=file_size,
                width=width,
                height=height,
                checksum=checksum,
                metadata=exif_data if exif_data else None,
            )
            assets.append(asset)

            # Generate thumbnail (max 300x300)
            thumbnail_uri = None
            if HAS_PIL and ext != ".svg":
                try:
                    with PILImage.open(file_path) as img:
                        img.thumbnail((300, 300))
                        thumb_buf = io.BytesIO()
                        save_format = "JPEG" if ext.lower() in (".jpg", ".jpeg") else "PNG"
                        img.save(thumb_buf, format=save_format)
                        thumb_buf.seek(0)
                        thumb_data = thumb_buf.read()

                        thumb_asset_id = f"asset_{uuid.uuid4().hex[:8]}"
                        thumb_ext = ".jpg" if save_format == "JPEG" else ".png"
                        thumb_object_name = f"parsed_assets/{doc_id}/thumbnails/{thumb_asset_id}{thumb_ext}"

                        try:
                            from app.services.storage import minio_storage
                            minio_storage.upload_file(
                                object_name=thumb_object_name,
                                data=thumb_data,
                                content_type=f"image/{save_format.lower()}",
                            )
                            thumbnail_uri = f"minio://{minio_storage.client._base_url.host}/{thumb_object_name}"
                        except Exception as e:
                            logger.debug(f"Failed to upload thumbnail to MinIO: {e}")
                            thumbnail_uri = f"inline://{thumb_asset_id}"

                        thumb_asset = UDRAsset(
                            asset_id=thumb_asset_id,
                            asset_type="thumbnail",
                            asset_uri=thumbnail_uri,
                            mime_type=f"image/{save_format.lower()}",
                            file_size=len(thumb_data),
                        )
                        assets.append(thumb_asset)
                except Exception as e:
                    logger.debug(f"Thumbnail generation failed: {e}")

            # Image block
            image_block_metadata = {
                "asset_id": asset_id,
                "width": width,
                "height": height,
                "mime_type": mime_type,
            }
            if thumbnail_uri:
                image_block_metadata["thumbnail_uri"] = thumbnail_uri
            if exif_data:
                image_block_metadata["exif"] = exif_data
            blocks.append(UDRBlock(
                block_id=f"{doc_id}_b0000",
                type="image",
                text=f"[Image: {filename}]",
                asset_uri=asset_uri,
                metadata=image_block_metadata,
            ))

            # OCR if requested
            use_ocr = options.get("ocr", False) or options.get("image_ocr", False)
            ocr_text = ""
            if use_ocr:
                # Try PaddleOCR first, fallback to pytesseract
                try:
                    from paddleocr import PaddleOCR
                    ocr = PaddleOCR(use_angle_cls=True, lang="ch")
                    result = ocr.ocr(file_path, cls=True)
                    if result and result[0]:
                        for line in result[0]:
                            ocr_text += line[1][0] + "\n"
                except ImportError:
                    # fallback to pytesseract
                    try:
                        import pytesseract
                        if HAS_PIL:
                            with PILImage.open(file_path) as img:
                                ocr_text = pytesseract.image_to_string(img, lang="chi_sim+eng")
                    except ImportError:
                        logger.warning("Neither paddleocr nor pytesseract installed; OCR skipped")
                    except Exception as e:
                        logger.warning(f"OCR (pytesseract) failed: {e}")
                except Exception as e:
                    logger.warning(f"OCR (PaddleOCR) failed: {e}")

                if ocr_text.strip():
                    blocks.append(UDRBlock(
                        block_id=f"{doc_id}_b{len(blocks):04d}",
                        type="paragraph",
                        text=ocr_text.strip(),
                        ocr_text=ocr_text.strip(),
                        metadata={"source": "ocr"},
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
                    "width": width,
                    "height": height,
                    "ocr_enabled": use_ocr,
                    "ocr_text_length": len(ocr_text) if ocr_text else 0,
                },
                blocks=blocks,
                assets=assets,
            )

        except Exception as e:
            logger.error(f"Image parsing failed: {e}")
            return self._fallback_parse(file_path)

    @staticmethod
    def _fallback_parse(file_path: str) -> UnifiedDocument:
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        path = Path(file_path)
        return UnifiedDocument(
            document_id=doc_id,
            source={
                "filename": path.name,
                "mime_type": "image/png",
                "source_uri": str(path.absolute()),
            },
            metadata={"title": path.name, "warning": "Image parsing failed"},
            blocks=[
                UDRBlock(
                    block_id=f"{doc_id}_b0000",
                    type="image",
                    text=f"[Image file: {path.name}]",
                ),
            ],
        )


# 注册
ParserRegistry.register(ImageParser())
