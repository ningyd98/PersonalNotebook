#!/usr/bin/env python3
"""
RAG 评测脚本
加载评测集，对每个 case 运行 RAG 问答，计算：
  - Recall@K
  - MRR
  - Citation Accuracy
  - Hallucination Rate
输出评测报告
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models.models import EvalDataset, EvalCase


def build_db_url() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "personal_kb")
    user = os.getenv("POSTGRES_USER", "kb_user")
    password = os.getenv("POSTGRES_PASSWORD", "kb_password")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


# ---------------------------------------------------------------------------
# 指标计算
# ---------------------------------------------------------------------------

def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """Recall@K：前 K 个检索结果中相关文档的比例"""
    if not relevant_ids:
        return 0.0
    retrieved_set = set(retrieved_ids[:k])
    relevant_set = set(relevant_ids)
    hits = len(retrieved_set & retrieved_set)
    return hits / len(relevant_set)


def mrr(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """MRR：第一个相关文档的排名倒数的均值"""
    if not relevant_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_set:
            return 1.0 / rank
    return 0.0


def citation_accuracy(cited_ids: list[str], relevant_ids: list[str]) -> float:
    """Citation Accuracy：引用中相关文档的比例"""
    if not cited_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    if not relevant_set:
        return 0.0
    hits = sum(1 for cid in cited_ids if cid in relevant_set)
    return hits / len(cited_ids)


def hallucination_rate(
    answer: str,
    cited_ids: list[str],
    relevant_ids: list[str],
) -> float:
    """
    幻觉率启发式估算：
    如果回答中有引用但引用全部不在相关文档中，视为潜在幻觉；
    如果回答无引用但有 expected 答案，也视为潜在幻觉。
    返回 0.0 或 1.0 (逐条二值判断，最后取均值)
    """
    relevant_set = set(relevant_ids)

    if cited_ids:
        # 有引用：检查引用是否全部不在相关集合中
        any_relevant = any(cid in relevant_set for cid in cited_ids)
        return 0.0 if any_relevant else 1.0
    else:
        # 无引用：如果有期望答案则视为幻觉，否则无法判断
        return 1.0 if relevant_set else 0.0


# ---------------------------------------------------------------------------
# RAG 问答调用（模拟 / 可替换为真实 API）
# ---------------------------------------------------------------------------

async def run_rag_query(question: str, kb_id: str) -> dict:
    """
    对一个问题执行 RAG 问答，返回检索结果和回答。
    实际部署时替换为真实 RAG API 调用。
    """
    gateway_url = os.getenv("MODEL_GATEWAY_URL", "http://localhost:8900")
    default_llm = os.getenv("DEFAULT_LLM", "qwen3:8b")

    # ---- 尝试调用后端 API ----
    try:
        import httpx
        base_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{base_url}/api/v1/chat",
                json={"question": question, "kb_id": kb_id},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "answer": data.get("answer", ""),
                    "retrieved_ids": data.get("retrieved_ids", []),
                    "cited_ids": data.get("cited_ids", []),
                }
    except Exception:
        pass

    # ---- Fallback：使用空结果（仅用于离线评测已有结果） ----
    return {
        "answer": "",
        "retrieved_ids": [],
        "cited_ids": [],
    }


# ---------------------------------------------------------------------------
# 主评测流程
# ---------------------------------------------------------------------------

async def eval_rag(
    dataset_name: Optional[str] = None,
    dataset_id: Optional[str] = None,
    output_path: Optional[str] = None,
    ks: list[int] | None = None,
):
    if ks is None:
        ks = [1, 3, 5, 10]

    db_url = build_db_url()
    engine = create_async_engine(db_url, echo=False, pool_size=5, max_overflow=10)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    results_per_case = []

    async with session_factory() as session:
        # 加载评测集
        if dataset_id:
            ds_stmt = select(EvalDataset).where(EvalDataset.id == dataset_id)
        elif dataset_name:
            ds_stmt = select(EvalDataset).where(EvalDataset.name == dataset_name)
        else:
            ds_stmt = select(EvalDataset).limit(1)

        ds_result = await session.execute(ds_stmt)
        dataset = ds_result.scalar_one_or_none()

        if not dataset:
            print("未找到评测集，请指定 --dataset-name 或 --dataset-id", file=sys.stderr)
            await engine.dispose()
            return

        # 加载评测用例
        cases_stmt = select(EvalCase).where(EvalCase.dataset_id == dataset.id)
        cases_result = await session.execute(cases_stmt)
        cases = cases_result.scalars().all()

        if not cases:
            print(f"评测集 '{dataset.name}' 中没有用例", file=sys.stderr)
            await engine.dispose()
            return

        print(f"评测集: {dataset.name} | 用例数: {len(cases)}", file=sys.stderr)

        for idx, case in enumerate(cases, 1):
            question = case.question
            expected_doc_ids = case.expected_docs_json or []
            expected_chunk_ids = case.expected_chunks_json or []
            reference_answer = case.reference_answer or ""

            # 运行 RAG 或使用已有结果
            if case.model_answer and case.retrieval_results_json:
                # 使用已保存的结果
                rag_result = {
                    "answer": case.model_answer,
                    "retrieved_ids": case.retrieval_results_json.get("retrieved_ids", []),
                    "cited_ids": case.retrieval_results_json.get("cited_ids", []),
                }
            else:
                kb_id = str(dataset.kb_id) if dataset.kb_id else ""
                rag_result = await run_rag_query(question, kb_id)

            retrieved_ids = rag_result["retrieved_ids"]
            cited_ids = rag_result["cited_ids"]
            answer = rag_result["answer"]

            # 计算指标
            case_metrics = {"question": question}

            # Recall@K (基于 expected_docs)
            for k in ks:
                case_metrics[f"recall@{k}"] = recall_at_k(retrieved_ids, expected_doc_ids, k)

            # MRR
            case_metrics["mrr"] = mrr(retrieved_ids, expected_doc_ids)

            # Citation Accuracy
            case_metrics["citation_accuracy"] = citation_accuracy(cited_ids, expected_doc_ids)

            # Hallucination Rate
            case_metrics["hallucination"] = hallucination_rate(answer, cited_ids, expected_doc_ids)

            results_per_case.append(case_metrics)

            if idx % 10 == 0:
                print(f"  已处理 {idx}/{len(cases)} 条用例", file=sys.stderr)

    await engine.dispose()

    # 汇总
    n = len(results_per_case)
    if n == 0:
        print("无评测结果", file=sys.stderr)
        return

    summary = {"dataset": dataset.name, "total_cases": n, "cases": results_per_case}

    # 计算均值
    metric_keys = [k for k in results_per_case[0] if k != "question"]
    averages = {}
    for mk in metric_keys:
        values = [c[mk] for c in results_per_case if mk in c]
        averages[mk] = round(sum(values) / len(values), 4) if values else 0.0

    summary["averages"] = averages

    # 输出
    output_json = json.dumps(summary, ensure_ascii=False, indent=2)

    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"评测报告已写入 → {output_path}", file=sys.stderr)
    else:
        print(output_json)

    # 打印摘要
    print("\n===== 评测摘要 =====", file=sys.stderr)
    for mk, val in averages.items():
        print(f"  {mk}: {val}", file=sys.stderr)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="RAG 评测脚本")
    parser.add_argument("--dataset-name", type=str, default=None, help="评测集名称")
    parser.add_argument("--dataset-id", type=str, default=None, help="评测集 ID")
    parser.add_argument("-o", "--output", type=str, default=None, help="输出报告文件路径 (默认 stdout)")
    parser.add_argument("--ks", type=str, default="1,3,5,10", help="Recall@K 的 K 值列表 (逗号分隔)")
    args = parser.parse_args()

    ks = [int(k.strip()) for k in args.ks.split(",")]
    asyncio.run(eval_rag(args.dataset_name, args.dataset_id, args.output, ks))


if __name__ == "__main__":
    main()
