#!/usr/bin/env python3
"""
导出表格问答数据集
输出：question, table_id, sql(预留), answer 的 JSONL
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

from app.models.models import (
    Message, Feedback, Conversation, TableObject, Document, KnowledgeBase,
)


def build_db_url() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "personal_kb")
    user = os.getenv("POSTGRES_USER", "kb_user")
    password = os.getenv("POSTGRES_PASSWORD", "kb_password")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


async def export_table_qa_dataset(output_path: str | None, min_rating: int = 0):
    """导出表格问答数据集"""
    db_url = build_db_url()
    engine = create_async_engine(db_url, echo=False, pool_size=5, max_overflow=10)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    records = []

    async with session_factory() as session:
        # 1. 获取所有表格对象
        table_stmt = select(TableObject)
        table_result = await session.execute(table_stmt)
        tables = table_result.scalars().all()

        # 构建文档ID → 知识库ID 映射
        doc_ids = list({t.document_id for t in tables})
        doc_stmt = select(Document).where(Document.id.in_(doc_ids))
        doc_result = await session.execute(doc_stmt)
        doc_kb_map = {d.id: d.kb_id for d in doc_result.scalars().all()}

        # 2. 查找涉及表格的对话
        # 从 feedback 高质量回答 + 包含表格相关关键词的 user 消息中提取
        user_stmt = select(Message).where(Message.role == "user").order_by(Message.created_at)
        user_result = await session.execute(user_stmt)
        user_messages = user_result.scalars().all()

        # 表格相关关键词
        table_keywords = ["表格", "表", "统计", "多少", "总计", "合计", "sheet", "excel",
                          "数据", "支出", "收入", "预算", "金额", "数量", "行", "列"]

        for user_msg in user_messages:
            question = user_msg.content.strip()
            if not question:
                continue

            # 过滤：问题必须包含表格相关关键词
            if not any(kw in question.lower() for kw in table_keywords):
                continue

            # 找到对应的 assistant 回答
            conv_id = user_msg.conversation_id
            asst_stmt = (
                select(Message)
                .where(
                    Message.conversation_id == conv_id,
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

            # 可选：只保留高质量反馈
            if min_rating > 0:
                fb_stmt = select(Feedback).where(Feedback.message_id == assistant_msg.id)
                fb_result = await session.execute(fb_stmt)
                fb = fb_result.scalar_one_or_none()
                if not fb or not fb.rating or fb.rating < min_rating:
                    continue

            # 获取会话对应的知识库
            conv_stmt = select(Conversation).where(Conversation.id == conv_id)
            conv_result = await session.execute(conv_stmt)
            conv = conv_result.scalar_one_or_none()
            kb_id = conv.kb_id if conv else None

            # 查找该知识库下最近的表格对象
            matched_table_id = None
            if kb_id:
                for table in tables:
                    t_doc_id = table.document_id
                    if doc_kb_map.get(t_doc_id) == kb_id:
                        matched_table_id = str(table.id)
                        break

            if not matched_table_id:
                continue

            records.append({
                "question": question,
                "table_id": matched_table_id,
                "sql": "",  # 预留字段
                "answer": assistant_msg.content,
            })

    await engine.dispose()

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"已导出 {len(records)} 条表格问答数据 → {output_path}", file=sys.stderr)
    else:
        for r in records:
            print(json.dumps(r, ensure_ascii=False))


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="导出表格问答数据集")
    parser.add_argument("-o", "--output", type=str, default=None, help="输出文件路径 (默认 stdout)")
    parser.add_argument("--min-rating", type=int, default=0, help="最低评分阈值 (0=不过滤)")
    args = parser.parse_args()

    asyncio.run(export_table_qa_dataset(args.output, args.min_rating))


if __name__ == "__main__":
    main()
