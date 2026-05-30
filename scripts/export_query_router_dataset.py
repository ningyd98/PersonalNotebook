#!/usr/bin/env python3
"""
导出问题路由分类数据集
从 messages 中提取用户问题，使用 _classify_query 分类
输出：question + label 的 JSONL
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

from app.models.models import Message


def build_db_url() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "personal_kb")
    user = os.getenv("POSTGRES_USER", "kb_user")
    password = os.getenv("POSTGRES_PASSWORD", "kb_password")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def classify_query(query: str) -> str:
    """问题类型分类（与 RetrievalService._classify_query 一致）"""
    query_lower = query.lower()

    table_keywords = ["表格", "表", "统计", "多少", "总计", "合计", "sheet", "excel", "xlsx",
                      "数据", "支出", "收入", "预算", "金额", "数量"]
    image_keywords = ["图片", "截图", "照片", "图像", "图中", "图示", "如图"]
    video_keywords = ["视频", "录像", "片段", "回放", "讲", "那段"]
    audio_keywords = ["录音", "音频", "语音", "说了"]
    code_keywords = ["代码", "函数", "class", "方法", "报错", "bug", "error"]
    formula_keywords = ["公式", "方程", "数学", "推导", "证明", "定理"]

    if any(kw in query_lower for kw in table_keywords):
        return "table"
    if any(kw in query_lower for kw in image_keywords):
        return "image"
    if any(kw in query_lower for kw in video_keywords):
        return "video"
    if any(kw in query_lower for kw in audio_keywords):
        return "audio"
    if any(kw in query_lower for kw in code_keywords):
        return "code"
    if any(kw in query_lower for kw in formula_keywords):
        return "formula"

    # 检查是否为混合类型（同时包含多个类别的关键词）
    category_hits = 0
    for keywords in [table_keywords, image_keywords, video_keywords,
                     audio_keywords, code_keywords, formula_keywords]:
        if any(kw in query_lower for kw in keywords):
            category_hits += 1
    if category_hits >= 2:
        return "mixed"

    return "text"


async def export_query_router_dataset(output_path: str | None, limit: int = 0):
    """导出问题路由分类数据"""
    db_url = build_db_url()
    engine = create_async_engine(db_url, echo=False, pool_size=5, max_overflow=10)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    records = []

    async with session_factory() as session:
        stmt = select(Message).where(Message.role == "user").order_by(Message.created_at)
        if limit > 0:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        messages = result.scalars().all()

        for msg in messages:
            question = msg.content.strip()
            if not question:
                continue

            label = classify_query(question)
            records.append({
                "question": question,
                "label": label,
            })

    await engine.dispose()

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"已导出 {len(records)} 条问题路由数据 → {output_path}", file=sys.stderr)
    else:
        for r in records:
            print(json.dumps(r, ensure_ascii=False))


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="导出问题路由分类数据集")
    parser.add_argument("-o", "--output", type=str, default=None, help="输出文件路径 (默认 stdout)")
    parser.add_argument("--limit", type=int, default=0, help="限制导出数量 (0=全部)")
    args = parser.parse_args()

    asyncio.run(export_query_router_dataset(args.output, args.limit))


if __name__ == "__main__":
    main()
