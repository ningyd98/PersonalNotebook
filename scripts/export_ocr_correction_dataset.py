#!/usr/bin/env python3
"""
导出 OCR 修正数据集
输出：image, ocr_raw, ocr_corrected 的 JSONL
从 document_assets (image 类型) + document_blocks (image 类型含 ocr_text) 中提取
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models.models import DocumentAsset, DocumentBlock, Message, Feedback


def build_db_url() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "personal_kb")
    user = os.getenv("POSTGRES_USER", "kb_user")
    password = os.getenv("POSTGRES_PASSWORD", "kb_password")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


async def export_ocr_correction_dataset(output_path: str | None):
    """导出 OCR 修正数据集"""
    db_url = build_db_url()
    engine = create_async_engine(db_url, echo=False, pool_size=5, max_overflow=10)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    records = []

    async with session_factory() as session:
        # 策略 1：从 document_blocks 中找含 image 类型的 block，
        # 其中 text 字段可能是 OCR 原始结果，关联 asset 获取图片路径
        block_stmt = (
            select(DocumentBlock, DocumentAsset)
            .join(DocumentAsset, DocumentBlock.asset_id == DocumentAsset.id, isouter=True)
            .where(DocumentBlock.block_type == "image")
        )
        block_result = await session.execute(block_stmt)
        block_rows = block_result.all()

        for block, asset in block_rows:
            ocr_raw = block.text or ""
            if not ocr_raw:
                continue

            image_uri = ""
            if asset:
                image_uri = asset.asset_uri or ""

            # corrected 文本：尝试从 metadata_json 中获取人工修正
            corrected = ocr_raw  # 默认与原始相同
            if block.metadata_json and isinstance(block.metadata_json, dict):
                corrected = block.metadata_json.get("ocr_corrected", block.metadata_json.get("corrected_text", ocr_raw))

            records.append({
                "image": image_uri,
                "ocr_raw": ocr_raw,
                "ocr_corrected": corrected,
            })

        # 策略 2：从 media_segments 中获取含 ocr_text 的视频帧
        from app.models.models import MediaSegment
        seg_stmt = select(MediaSegment).where(MediaSegment.ocr_text.isnot(None), MediaSegment.ocr_text != "")
        seg_result = await session.execute(seg_stmt)
        segments = seg_result.scalars().all()

        for seg in segments:
            ocr_raw = seg.ocr_text or ""
            if not ocr_raw:
                continue

            # 获取关联的 asset URI
            image_uri = ""
            if seg.asset_id:
                asset_stmt = select(DocumentAsset).where(DocumentAsset.id == seg.asset_id)
                asset_result = await session.execute(asset_stmt)
                asset = asset_result.scalar_one_or_none()
                if asset:
                    image_uri = asset.asset_uri or ""

            corrected = ocr_raw
            if seg.metadata_json and isinstance(seg.metadata_json, dict):
                corrected = seg.metadata_json.get("ocr_corrected", ocr_raw)

            records.append({
                "image": image_uri,
                "ocr_raw": ocr_raw,
                "ocr_corrected": corrected,
            })

    await engine.dispose()

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"已导出 {len(records)} 条 OCR 修正数据 → {output_path}", file=sys.stderr)
    else:
        for r in records:
            print(json.dumps(r, ensure_ascii=False))


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="导出 OCR 修正数据集")
    parser.add_argument("-o", "--output", type=str, default=None, help="输出文件路径 (默认 stdout)")
    args = parser.parse_args()

    asyncio.run(export_ocr_correction_dataset(args.output))


if __name__ == "__main__":
    main()
