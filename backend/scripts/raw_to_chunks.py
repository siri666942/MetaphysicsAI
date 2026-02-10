#!/usr/bin/env python3
"""
将 knowledge/raw/*.txt 按段落或固定长度切分为 chunk 占位 JSON，写入 knowledge/chunks/。
便于后续补 tags、白话。与 fetch_books.py 配合：抓取后运行本脚本即可得到可编辑的 chunk  scaffold。
"""

import os
import re
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
RAW_DIR = os.path.join(BACKEND_DIR, "knowledge", "raw")
CHUNKS_DIR = os.path.join(BACKEND_DIR, "knowledge", "chunks")
MAX_CHARS = 800
MIN_CHARS = 80

# 书名 id -> 显示名（与 books_config 一致）
BOOK_NAMES = {
    "yuanhaiziping": "渊海子平",
    "ditiansui": "滴天髓",
    "sanmingtonghui": "三命通会",
    "zipingzhenquan": "子平真诠评注",
}


def split_into_blocks(text: str) -> list[str]:
    """先按双换行分段，过长的再按 MAX_CHARS 截断。"""
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"\n\s*\n", text)
    blocks = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if len(p) <= MAX_CHARS:
            if len(p) >= MIN_CHARS or not blocks:
                blocks.append(p)
            else:
                blocks[-1] = blocks[-1] + "\n\n" + p
        else:
            start = 0
            while start < len(p):
                end = start + MAX_CHARS
                if end < len(p):
                    for sep in ("。", "！", "？", "\n", "；", " "):
                        idx = p.rfind(sep, start, end + 1)
                        if idx > start:
                            end = idx + 1
                            break
                blocks.append(p[start:end].strip())
                start = end
    return [b for b in blocks if len(b.strip()) >= 20]


def main():
    if not os.path.isdir(RAW_DIR):
        print(f"目录不存在: {RAW_DIR}，请先运行 fetch_books.py 并配置书源。")
        return 1
    os.makedirs(CHUNKS_DIR, exist_ok=True)
    count = 0
    for name in sorted(os.listdir(RAW_DIR)):
        if not name.endswith(".txt"):
            continue
        bid = name[:-4]
        path = os.path.join(RAW_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"跳过 {name}: {e}")
            continue
        blocks = split_into_blocks(text)
        source_name = BOOK_NAMES.get(bid, bid)
        for i, content in enumerate(blocks):
            chunk_id = f"{bid}_chunk_{i+1}"
            obj = {
                "id": chunk_id,
                "source": source_name,
                "tags": [],
                "content": content,
            }
            out_path = os.path.join(CHUNKS_DIR, f"{chunk_id}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            count += 1
        print(f"  {name} -> {len(blocks)} chunks")
    print(f"共写入 {count} 个 chunk 到 {CHUNKS_DIR}")
    return 0


if __name__ == "__main__":
    exit(main())
