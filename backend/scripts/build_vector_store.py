#!/usr/bin/env python3
"""
将 knowledge/chunks 下的白话文 chunk（*baihua*.json）向量化，
保存为 knowledge/vector_store/embeddings.npy、meta.json、vocab.json，
供 rag.retrieve() 做语义检索。

使用字符级 n-gram TF-IDF，纯 Python + numpy 实现，
不依赖 sentence-transformers / torch，兼容 Python 3.14 且内存友好。
首次运行或白话 chunk 更新后执行一次即可。
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

    print(f"共 {len(contents)} 条，正在构建词汇表 ...")
    from embedding_utils import build_vocab, embed_texts
    build_vocab(contents)
    print("词汇表构建完成，正在向量化 ...")

    # 分批向量化以节省内存
    import numpy as np
    batch_size = 500
    all_embeddings = []
    for start in range(0, len(contents), batch_size):
        batch = contents[start:start + batch_size]
        embs = embed_texts(batch)
        all_embeddings.extend(embs)
        done = min(start + batch_size, len(contents))
        print(f"  已向量化 {done}/{len(contents)} 条")

    os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
    np.save(
        os.path.join(VECTOR_STORE_DIR, EMBEDDINGS_FILE),
        np.array(all_embeddings, dtype=np.float32),
    )

    meta = [
        {"id": i, "source": s, "content": c}
        for i, s, c in zip(ids, sources, contents)
    ]
    with open(
        os.path.join(VECTOR_STORE_DIR, META_FILE), "w", encoding="utf-8"
    ) as f:
        json.dump(meta, f, ensure_ascii=False, indent=0)

    print(f"已写入 {len(meta)} 条到 {VECTOR_STORE_DIR}")
    return 0


if __name__ == "__main__":
    exit(main())
