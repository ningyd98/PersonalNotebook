#!/usr/bin/env python3
"""
重建向量索引
用法：python scripts/rebuild_index.py --kb-id <KB_UUID>
"""

import argparse

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def main():
    parser = argparse.ArgumentParser(description="重建知识库向量索引")
    parser.add_argument("--kb-id", required=True, help="知识库 UUID")
    args = parser.parse_args()

    print(f"正在重建知识库 {args.kb_id} 的向量索引...")
    print("此操作将：")
    print("  1. 删除 Qdrant 中该知识库的所有向量")
    print("  2. 从数据库中读取所有 chunk")
    print("  3. 重新 embedding 并写入 Qdrant")
    print("\n注意：当前为 MVP 阶段，请通过 API 执行重建：")
    print(f"  POST /api/kbs/{args.kb_id}/documents/{args.kb_id}/reembed")


if __name__ == "__main__":
    main()
