#!/usr/bin/env python3
"""
导出 Reranker 微调数据集
格式：query-positive-negative
"""

import json
import os

SAMPLE_DATA = [
    {
        "query": "Q-learning 的更新公式是什么？",
        "positive": "Q-learning 更新公式为 Q(s,a) ← Q(s,a) + α[r + γ max_a' Q(s',a') - Q(s,a)]，其中 α 是学习率，γ 是折扣因子。",
        "negative": "蒙特卡洛方法通过完整轨迹估计回报，需要等到回合结束才能更新。",
    },
    {
        "query": "什么是 Embedding？",
        "positive": "Embedding 是将离散的词语、句子或文档映射到连续向量空间的技术，语义相近的文本在向量空间中距离更近。",
        "negative": "Transformer 架构由 Vaswani 等人在 2017 年提出，使用自注意力机制替代循环神经网络。",
    },
    {
        "query": "Python 中如何读取 CSV 文件？",
        "positive": "使用 pandas 库的 read_csv() 函数可以方便地读取 CSV 文件：df = pd.read_csv('file.csv')。也可以使用 Python 内置的 csv 模块。",
        "negative": "Docker 是一个容器化平台，允许开发者将应用和依赖打包到轻量级容器中运行。",
    },
]


def main():
    output_path = os.path.join(os.path.dirname(__file__), "..", "datasets", "rerank", "rerank_train.jsonl")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        for item in SAMPLE_DATA:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"已导出 {len(SAMPLE_DATA)} 条 Rerank 训练数据 → {output_path}")


if __name__ == "__main__":
    main()
