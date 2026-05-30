#!/usr/bin/env python3
"""
导出 SFT 微调数据集
从 conversations + messages + feedback 中提取高质量对话对 (rating >= 4)
格式：instruction / input / output 的 JSONL
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

# 将 backend 目录加入 sys.path 以便导入项目模块
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models.models import Conversation, Message, Feedback


def build_db_url() -> str:
    """从环境变量构建数据库连接 URL"""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "personal_kb")
    user = os.getenv("POSTGRES_USER", "kb_user")
    password = os.getenv("POSTGRES_PASSWORD", "kb_password")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


async def export_sft_dataset(output_path: str | None, min_rating: int = 4):
    """导出 SFT 数据集"""
    db_url = build_db_url()
    engine = create_async_engine(db_url, echo=False, pool_size=5, max_overflow=10)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    records = []

    async with session_factory() as session:
        # 查询所有 rating >= min_rating 的 feedback
        stmt = (
            select(Feedback, Message, Conversation)
            .join(Message, Feedback.message_id == Message.id)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(Feedback.rating >= min_rating, Message.role == "assistant")
            .order_by(Conversation.id, Message.created_at)
        )
        result = await session.execute(stmt)
        rows = result.all()

        for feedback, assistant_msg, conversation in rows:
            # 找同一会话中该 assistant 消息之前的最近一条 user 消息
            user_stmt = (
                select(Message)
                .where(
                    Message.conversation_id == assistant_msg.conversation_id,
                    Message.role == "user",
                    Message.created_at < assistant_msg.created_at,
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            user_result = await session.execute(user_stmt)
            user_msg = user_result.scalar_one_or_none()

            if not user_msg:
                continue

            # 构造 input：问题 + 引用资料
            question = user_msg.content
            evidence_parts = []

            if assistant_msg.citations_json:
                for citation in assistant_msg.citations_json:
                    if isinstance(citation, dict):
                        content = citation.get("content", citation.get("text", ""))
                        if content:
                            evidence_parts.append(content)
                    elif isinstance(citation, str):
                        evidence_parts.append(citation)

            evidence_content = "\n".join(evidence_parts) if evidence_parts else "（无引用资料）"

            record = {
                "instruction": "根据知识库回答问题，并给出引用。",
                "input": f"问题：{question}\n资料：{evidence_content}",
                "output": assistant_msg.content,
            }
            records.append(record)

    await engine.dispose()

    # 输出
    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"已导出 {len(records)} 条 SFT 训练数据 → {output_path}", file=sys.stderr)
    else:
        for r in records:
            print(json.dumps(r, ensure_ascii=False))


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="导出 SFT 微调数据集")
    parser.add_argument("-o", "--output", type=str, default=None, help="输出文件路径 (默认 stdout)")
    parser.add_argument("--min-rating", type=int, default=4, help="最低评分阈值 (默认 4)")
    args = parser.parse_args()

    asyncio.run(export_sft_dataset(args.output, args.min_rating))


if __name__ == "__main__":
    main()
