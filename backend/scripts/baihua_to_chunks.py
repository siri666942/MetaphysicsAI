#!/usr/bin/env python3
"""
从 knowledge/baihua/*.txt 按段落或固定长度切分为 chunk JSON，写入 knowledge/chunks/。
用白话文做 RAG 源可提升检索到的内容可读性，便于模型利用。
与 raw_to_chunks.py 共用切分逻辑；输出 id 带 _baihua_ 以区分原文 chunk。
"""

import os
import re
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
BAIHUA_DIR = os.path.join(BACKEND_DIR, "knowledge", "baihua")
CHUNKS_DIR = os.path.join(BACKEND_DIR, "knowledge", "chunks")
MAX_CHARS = 800
MIN_CHARS = 80

# 白话文件名（去掉 _白话.txt）-> 书 id，用于 chunk id 与 source 显示
# 例如 三命通会_白话.txt -> sanmingtonghui
BAIHUA_FILE_TO_BID = {
    "渊海子平": "yuanhaiziping",
    "子平真诠评注": "zipingzhenquan",
    "三命通会": "sanmingtonghui",
    "滴天髓阐微": "ditiansui",
}
BOOK_DISPLAY = {
    "yuanhaiziping": "渊海子平",
    "zipingzhenquan": "子平真诠评注",
    "sanmingtonghui": "三命通会",
    "ditiansui": "滴天髓阐微",
}


def split_into_blocks(text: str) -> list[str]:
    """先按双换行分段，过长的再按 MAX_CHARS 截断。与 raw_to_chunks 一致。"""
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
    if not os.path.isdir(BAIHUA_DIR):
        print(f"目录不存在: {BAIHUA_DIR}，请先运行 raw_to_baihua.py 生成白话文。")
        return 1
    os.makedirs(CHUNKS_DIR, exist_ok=True)
    count = 0
    for name in sorted(os.listdir(BAIHUA_DIR)):
        if not name.endswith(".txt") or "_白话" not in name:
            continue
        # 例如 三命通会_白话.txt -> 三命通会
        base_name = name.replace("_白话.txt", "").replace(".txt", "")
        bid = BAIHUA_FILE_TO_BID.get(base_name)
        if not bid:
            print(f"  跳过未知书名: {name}")
            continue
        path = os.path.join(BAIHUA_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"跳过 {name}: {e}")
            continue
        # 去掉首行说明头（若有）
        if text.startswith("#") or "说明：" in text[:200]:
            first_line_end = text.find("\n")
            if first_line_end > 0:
                text = text[first_line_end:].lstrip()
        blocks = split_into_blocks(text)
        source_name = BOOK_DISPLAY.get(bid, bid) + "（白话）"
        for i, content in enumerate(blocks):
            chunk_id = f"{bid}_baihua_chunk_{i+1}"
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
    print(f"共写入 {count} 个白话 chunk 到 {CHUNKS_DIR}")
    return 0


if __name__ == "__main__":
    exit(main())
