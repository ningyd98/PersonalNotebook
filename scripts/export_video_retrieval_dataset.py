#!/usr/bin/env python3
"""
导出视频片段检索数据集
输出：question, positive_segment, negative_segments 的 JSONL
从 media_segments (video 类型) + 对话中提取
"""

import argparse
import asyncio
import json
import os
import random
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models.models import (
    Message, MediaSegment, Document, DocumentAsset, KnowledgeBase, Conversation,
)


def build_db_url() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "personal_kb")
    user = os.getenv("POSTGRES_USER", "kb_user")
    password = os.getenv("POSTGRES_PASSWORD", "kb_password")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


async def export_video_retrieval_dataset(
    output_path: str | None,
    num_negatives: int = 5,
):
    """导出视频片段检索数据集"""
    db_url = build_db_url()
    engine = create_async_engine(db_url, echo=False, pool_size=5, max_overflow=10)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    records = []

    async with session_factory() as session:
        # 1. 获取所有视频片段
        seg_stmt = select(MediaSegment).where(MediaSegment.segment_type == "video")
        seg_result = await session.execute(seg_stmt)
        video_segments = seg_result.scalars().all()

        if not video_segments:
            print("未找到视频片段数据", file=sys.stderr)
            await engine.dispose()
            return

        # 构建文档ID → 知识库ID 映射
        doc_ids = list({s.document_id for s in video_segments})
        doc_stmt = select(Document).where(Document.id.in_(doc_ids))
        doc_result = await session.execute(doc_stmt)
        doc_kb_map = {d.id: d.kb_id for d in doc_result.scalars().all()}

        # 构建片段信息列表
        segment_info = []
        for seg in video_segments:
            segment_info.append({
                "id": str(seg.id),
                "document_id": str(seg.document_id),
                "kb_id": str(doc_kb_map.get(seg.document_id, "")),
                "start_time": seg.start_time,
                "end_time": seg.end_time,
                "transcript": seg.transcript or "",
                "ocr_text": seg.ocr_text or "",
                "visual_caption": seg.visual_caption or "",
            })

        # 2. 获取视频相关的问题
        video_keywords = ["视频", "录像", "片段", "回放", "讲", "那段"]
        user_stmt = select(Message).where(Message.role == "user").order_by(Message.created_at)
        user_result = await session.execute(user_stmt)
        user_messages = user_result.scalars().all()

        # 获取会话对应知识库
        conv_ids = list({m.conversation_id for m in user_messages})
        conv_stmt = select(Conversation).where(Conversation.id.in_(conv_ids))
        conv_result = await session.execute(conv_stmt)
        conv_kb_map = {c.id: c.kb_id for c in conv_result.scalars().all()}

        # 构建知识库 → 片段 映射
        kb_segments = {}
        for si in segment_info:
            kb_id = si["kb_id"]
            if kb_id not in kb_segments:
                kb_segments[kb_id] = []
            kb_segments[kb_id].append(si)

        for user_msg in user_messages:
            question = user_msg.content.strip()
            if not question:
                continue

            if not any(kw in question.lower() for kw in video_keywords):
                continue

            # 获取该问题对应的知识库
            kb_id = str(conv_kb_map.get(user_msg.conversation_id, ""))
            if not kb_id or kb_id not in kb_segments:
                continue

            # 找到对应的 assistant 回答以确定正例
            asst_stmt = (
                select(Message)
                .where(
                    Message.conversation_id == user_msg.conversation_id,
                    Message.role == "assistant",
                    Message.created_at > user_msg.created_at,
                )
                .order_by(Message.created_at.asc())
                .limit(1)
            )
            asst_result = await session.execute(asst_stmt)
            assistant_msg = asst_result.scalar_one_or_none()
            if not assistant_msg:
                continue

            # 尝试从 citations 中匹配正例片段
            positive_segment = None
            if assistant_msg.citations_json:
                for citation in assistant_msg.citations_json:
                    if isinstance(citation, dict):
                        seg_id = citation.get("segment_id", citation.get("chunk_id", ""))
                        for si in kb_segments[kb_id]:
                            if si["id"] == str(seg_id):
                                positive_segment = si
                                break
                    if positive_segment:
                        break

            # 如果未从引用找到正例，随机选择同知识库的片段作为正例
            if not positive_segment:
                positive_segment = random.choice(kb_segments[kb_id])

            # 负例：从不同知识库或同一知识库不同文档中选择
            all_segments = [si for si in segment_info if si["id"] != positive_segment["id"]]
            negative_pool = all_segments if len(all_segments) > num_negatives else all_segments
            negative_segments = random.sample(negative_pool, min(num_negatives, len(negative_pool)))

            records.append({
                "question": question,
                "positive_segment": {
                    "segment_id": positive_segment["id"],
                    "start_time": positive_segment["start_time"],
                    "end_time": positive_segment["end_time"],
                    "transcript": positive_segment["transcript"],
                    "visual_caption": positive_segment["visual_caption"],
                },
                "negative_segments": [
                    {
                        "segment_id": ns["id"],
                        "start_time": ns["start_time"],
                        "end_time": ns["end_time"],
                        "transcript": ns["transcript"],
                        "visual_caption": ns["visual_caption"],
                    }
                    for ns in negative_segments
                ],
            })

    await engine.dispose()

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"已导出 {len(records)} 条视频检索数据 → {output_path}", file=sys.stderr)
    else:
        for r in records:
            print(json.dumps(r, ensure_ascii=False))


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="导出视频片段检索数据集")
    parser.add_argument("-o", "--output", type=str, default=None, help="输出文件路径 (默认 stdout)")
    parser.add_argument("--num-negatives", type=int, default=5, help="每条正例对应的负例数量 (默认 5)")
    args = parser.parse_args()

    asyncio.run(export_video_retrieval_dataset(args.output, args.num_negatives))


if __name__ == "__main__":
    main()
