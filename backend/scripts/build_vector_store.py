#!/usr/bin/env python3
"""
将 knowledge/chunks 下的白话文 chunk（*baihua*.json）向量化，
保存为 knowledge/vector_store/embeddings.npy 与 meta.json，
供 rag.retrieve() 做语义检索。首次运行或白话 chunk 更新后执行一次即可。
不依赖 Chroma，兼容 Python 3.14。
"""

import os
import json
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
CHUNKS_DIR = os.path.join(BACKEND_DIR, "knowledge", "chunks")
VECTOR_STORE_DIR = os.path.join(BACKEND_DIR, "knowledge", "vector_store")
EMBEDDINGS_FILE = "embeddings.npy"
META_FILE = "meta.json"

sys.path.insert(0, BACKEND_DIR)

from embedding_utils import embed_texts


def load_baihua_chunks():
    """加载所有带 baihua 的 chunk JSON，返回 list[dict]。"""
    chunks = []
    if not os.path.isdir(CHUNKS_DIR):
        return chunks
    for name in sorted(os.listdir(CHUNKS_DIR)):
        if not name.endswith(".json") or "baihua" not in name.lower():
            continue
        path = os.path.join(CHUNKS_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "chunks" in data:
                for c in data["chunks"]:
                    if c.get("content"):
                        chunks.append(c)
            elif data.get("content"):
                chunks.append(data)
        except Exception as e:
            print(f"  跳过 {name}: {e}")
    return chunks


def main():
    print("加载白话文 chunks ...")
    chunks = load_baihua_chunks()
    if not chunks:
        print("未找到任何 *baihua* chunk，请先运行 baihua_to_chunks.py。")
        return 1

    ids = []
    sources = []
    contents = []
    for c in chunks:
        cid = c.get("id", "")
        content = (c.get("content") or "").strip()
        source = c.get("source", "")
        if not cid or not content:
            continue
        ids.append(cid)
        sources.append(source)
        contents.append(content)

    print(f"共 {len(contents)} 条，正在向量化（首次会下载模型）...")
    embeddings = embed_texts(contents)

    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
    import numpy as np
    np.save(os.path.join(VECTOR_STORE_DIR, EMBEDDINGS_FILE), np.array(embeddings, dtype=np.float32))

    meta = [{"id": i, "source": s, "content": c} for i, s, c in zip(ids, sources, contents)]
    with open(os.path.join(VECTOR_STORE_DIR, META_FILE), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=0)

    print(f"已写入 {len(meta)} 条到 {VECTOR_STORE_DIR}")
    return 0


if __name__ == "__main__":
    exit(main())
