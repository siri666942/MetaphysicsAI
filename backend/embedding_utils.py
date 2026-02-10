"""
命理知识库向量化：使用字符级 n-gram TF-IDF 生成 embedding，
纯 Python + numpy 实现，不依赖外部 ML 库，兼容 Python 3.14 且内存友好。
供 build_vector_store.py 构建向量库，rag.py 做语义检索。
"""

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from typing import List, Optional

import numpy as np

# ---------- 配置 ----------
# n-gram 范围：使用 1-gram 和 2-gram（中文字符）
NGRAM_RANGE = (1, 2)
# 最大词汇表大小
MAX_VOCAB = 8000
# 最小文档频率（出现不到 2 次的 n-gram 丢弃）
MIN_DF = 2
# 最大文档频率比例（超过 80% 文档都出现的 n-gram 丢弃）
MAX_DF_RATIO = 0.80

# ---------- 向量库路径 ----------
_VECTOR_STORE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "knowledge", "vector_store",
)
_VOCAB_FILE = os.path.join(_VECTOR_STORE_DIR, "vocab.json")

# ---------- 缓存 ----------
_vocab: Optional[dict] = None   # token -> index
_idf: Optional[np.ndarray] = None  # shape (vocab_size,)


def _tokenize(text: str) -> List[str]:
    """将文本拆分为字符级 n-gram tokens。
    保留中文字符和少量标点，去除纯空白和英文。"""
    # 只保留中文字符、数字和少量标点
    text = re.sub(r"[a-zA-Z]", "", text)
    text = re.sub(r"\s+", "", text)
    chars = list(text)
    tokens = []
    for n in range(NGRAM_RANGE[0], NGRAM_RANGE[1] + 1):
        for i in range(len(chars) - n + 1):
            gram = "".join(chars[i:i + n])
            if len(gram.strip()) >= n:
                tokens.append(gram)
    return tokens


def build_vocab(texts: List[str]):
    """从语料构建词汇表和 IDF 权重，保存到 vocab.json。"""
    n_docs = len(texts)
    # 统计文档频率
    df = Counter()
    for text in texts:
        unique_tokens = set(_tokenize(text))
        for tok in unique_tokens:
            df[tok] += 1

    # 过滤：去掉太稀有和太常见的 token
    min_df_count = MIN_DF
    max_df_count = int(n_docs * MAX_DF_RATIO)
    filtered = {
        tok: freq for tok, freq in df.items()
        if min_df_count <= freq <= max_df_count
    }
    # 按频率排序，取 top MAX_VOCAB
    sorted_tokens = sorted(
        filtered.items(), key=lambda x: x[1], reverse=True
    )[:MAX_VOCAB]
    vocab = {tok: idx for idx, (tok, _) in enumerate(sorted_tokens)}

    # 计算 IDF: log(N / df) + 1
    idf_values = np.zeros(len(vocab), dtype=np.float32)
    for tok, idx in vocab.items():
        idf_values[idx] = math.log(n_docs / df[tok]) + 1.0

    # 保存
    os.makedirs(_VECTOR_STORE_DIR, exist_ok=True)
    with open(_VOCAB_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"vocab": vocab, "idf": idf_values.tolist()},
            f, ensure_ascii=False,
        )

    global _vocab, _idf
    _vocab = vocab
    _idf = idf_values
    return vocab, idf_values


def _load_vocab():
    """懒加载词汇表和 IDF 权重。"""
    global _vocab, _idf
    if _vocab is not None and _idf is not None:
        return
    if not os.path.exists(_VOCAB_FILE):
        raise FileNotFoundError(
            f"词汇表文件不存在: {_VOCAB_FILE}，请先运行 build_vector_store.py"
        )
    with open(_VOCAB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    _vocab = data["vocab"]
    _idf = np.array(data["idf"], dtype=np.float32)


def _text_to_tfidf(text: str) -> np.ndarray:
    """将单条文本转为 TF-IDF 向量（L2 归一化）。"""
    _load_vocab()
    tokens = _tokenize(text)
    tf = Counter(tokens)
    vec = np.zeros(len(_vocab), dtype=np.float32)
    for tok, count in tf.items():
        idx = _vocab.get(tok)
        if idx is not None:
            # TF 使用 sublinear: 1 + log(tf)
            vec[idx] = (1.0 + math.log(count)) * _idf[idx]
    # L2 归一化
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def embed_texts(texts: List[str]) -> List[List[float]]:
    """对多段文本生成 TF-IDF 向量，返回 list of list of float。"""
    if not texts:
        return []
    _load_vocab()
    results = []
    for text in texts:
        vec = _text_to_tfidf(text)
        results.append(vec.tolist())
    return results


def embed_query(text: str) -> List[float]:
    """对单条查询生成 TF-IDF 向量。"""
    return _text_to_tfidf(text).tolist()
