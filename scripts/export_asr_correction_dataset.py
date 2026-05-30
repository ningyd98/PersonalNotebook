#!/usr/bin/env python3
"""
导出 ASR 修正数据集
输出：audio_segment, asr_raw, asr_corrected 的 JSONL
从 media_segments (audio 类型) + document_assets (audio 类型) 中提取
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models.models import MediaSegment, DocumentAsset


def build_db_url() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "personal_kb")
    user = os.getenv("POSTGRES_USER", "kb_user")
    password = os.getenv("POSTGRES_PASSWORD", "kb_password")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


async def export_asr_correction_dataset(output_path: str | None):
    """导出 ASR 修正数据集"""
    db_url = build_db_url()
    engine = create_async_engine(db_url, echo=False, pool_size=5, max_overflow=10)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    records = []

    async with session_factory() as session:
        # 查询所有含 transcript 的音频片段
        seg_stmt = (
            select(MediaSegment)
            .where(
                MediaSegment.segment_type == "audio",
                MediaSegment.transcript.isnot(None),
                MediaSegment.transcript != "",
            )
        )
        seg_result = await session.execute(seg_stmt)
        segments = seg_result.scalars().all()

        # 预加载所有关联的 audio asset
        asset_ids = list({s.asset_id for s in segments if s.asset_id})
        asset_map = {}
        if asset_ids:
            asset_stmt = select(DocumentAsset).where(DocumentAsset.id.in_(asset_ids))
            asset_result = await session.execute(asset_stmt)
            asset_map = {a.id: a for a in asset_result.scalars().all()}

        for seg in segments:
            asr_raw = seg.transcript or ""
            if not asr_raw:
                continue

            # 获取音频 URI
            audio_uri = ""
            if seg.asset_id and seg.asset_id in asset_map:
                audio_uri = asset_map[seg.asset_id].asset_uri or ""

            # corrected 文本：优先从 metadata_json 获取人工修正
            corrected = asr_raw
            if seg.metadata_json and isinstance(seg.metadata_json, dict):
                corrected = seg.metadata_json.get("asr_corrected", seg.metadata_json.get("corrected_transcript", asr_raw))

            records.append({
                "audio_segment": {
                    "segment_id": str(seg.id),
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "audio_uri": audio_uri,
                },
                "asr_raw": asr_raw,
                "asr_corrected": corrected,
            })

        # 也处理视频片段中的音频转录
        video_seg_stmt = (
            select(MediaSegment)
            .where(
                MediaSegment.segment_type == "video",
                MediaSegment.transcript.isnot(None),
                MediaSegment.transcript != "",
            )
        )
        video_seg_result = await session.execute(video_seg_stmt)
        video_segments = video_seg_result.scalars().all()

        for seg in video_segments:
            asr_raw = seg.transcript or ""
            if not asr_raw:
                continue

            audio_uri = ""
            if seg.asset_id and seg.asset_id in asset_map:
                audio_uri = asset_map[seg.asset_id].asset_uri or ""

            corrected = asr_raw
            if seg.metadata_json and isinstance(seg.metadata_json, dict):
                corrected = seg.metadata_json.get("asr_corrected", seg.metadata_json.get("corrected_transcript", asr_raw))

            records.append({
                "audio_segment": {
                    "segment_id": str(seg.id),
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "audio_uri": audio_uri,
                },
                "asr_raw": asr_raw,
                "asr_corrected": corrected,
            })

    await engine.dispose()

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"已导出 {len(records)} 条 ASR 修正数据 → {output_path}", file=sys.stderr)
    else:
        for r in records:
            print(json.dumps(r, ensure_ascii=False))


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="导出 ASR 修正数据集")
    parser.add_argument("-o", "--output", type=str, default=None, help="输出文件路径 (默认 stdout)")
    args = parser.parse_args()

    asyncio.run(export_asr_correction_dataset(args.output))


if __name__ == "__main__":
    main()
