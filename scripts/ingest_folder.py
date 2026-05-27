#!/usr/bin/env python3
"""
批量导入文件夹到知识库
用法：python scripts/ingest_folder.py --kb-id <KB_UUID> --path /path/to/folder
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.connectors.base import LocalFolderConnector


def main():
    parser = argparse.ArgumentParser(description="导入文件夹到 Personal-KB")
    parser.add_argument("--kb-id", required=True, help="知识库 UUID")
    parser.add_argument("--path", required=True, help="要导入的文件夹路径")
    parser.add_argument("--recursive", action="store_true", default=True)
    args = parser.parse_args()

    connector = LocalFolderConnector()
    files = connector.scan({"path": args.path, "recursive": args.recursive})

    print(f"发现 {len(files)} 个文件：")
    for f in files[:20]:
        print(f"  {f.filename} ({f.mime_type}, {f.size} bytes)")

    if len(files) > 20:
        print(f"  ... 还有 {len(files) - 20} 个文件")

    print(f"\n请通过 API 提交导入任务：")
    print(f"POST /api/kbs/{args.kb_id}/documents/import-folder")
    print(f'Body: {{"source_type": "local_folder", "source_path": "{args.path}"}}')


if __name__ == "__main__":
    main()
