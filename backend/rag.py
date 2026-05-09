"""
RAG 检索模块 —— 第一层「喂书」：从命理知识库中检索相关片段，供大模型参考
优先使用白话文向量库（embeddings.npy + meta.json）语义检索；无向量库时回退到关键词匹配
"""

import os
import json

_BASE = os.path.dirname(os.path.abspath(__file__))
_CHUNKS_DIR = os.path.join(_BASE, "knowledge", "chunks")
_VECTOR_STORE_DIR = os.path.join(_BASE, "knowledge", "vector_store")
_EMBEDDINGS_FILE = "embeddings.npy"
_META_FILE = "meta.json"

_vector_embeddings = None
_vector_meta = None


def _load_vector_store():
    """懒加载向量库：embeddings 数组与 meta 列表。未构建则返回 (None, None)。"""
    global _vector_embeddings, _vector_meta
    if _vector_embeddings is not None:
        return _vector_embeddings, _vector_meta
    emb_path = os.path.join(_VECTOR_STORE_DIR, _EMBEDDINGS_FILE)
    meta_path = os.path.join(_VECTOR_STORE_DIR, _META_FILE)
    if not os.path.isfile(emb_path) or not os.path.isfile(meta_path):
        return None, None
    try:
        import numpy as np
        _vector_embeddings = np.load(emb_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            _vector_meta = json.load(f)
        if len(_vector_meta) == 0 or _vector_embeddings.shape[0] != len(_vector_meta):
            _vector_embeddings = None
            _vector_meta = None
            return None, None
        return _vector_embeddings, _vector_meta
    except Exception:
        return None, None

# 命理术语同义/扩展：query 中出现任一词则加入整组，提高召回
_QUERY_EXPAND_TERMS = [
    ["八字", "四柱", "命局", "命造"],
    ["格局", "格", "局", "取格"],
    ["用神", "取用", "喜用", "喜神", "忌神"],
    ["月令", "月建", "提纲", "月支"],
    ["冲", "六冲", "子午冲", "卯酉冲", "寅申冲", "巳亥冲", "辰戌冲", "丑未冲", "刑冲合害"],
    ["刑", "三刑", "无恩之刑", "恃势之刑", "无礼之刑"],
    ["合", "六合", "三合", "半合", "天干五合", "地支六合"],
    ["害", "六害"],
    ["大运", "运", "运程", "行运"],
    ["流年", "岁", "太岁", "岁运"],
    ["十神", "正官", "偏官", "七杀", "正财", "偏财", "正印", "偏印", "食神", "伤官", "比肩", "劫财"],
    ["日主", "日干", "日元", "身"],
    ["身旺", "身强", "旺"],
    ["身弱", "身衰", "弱", "衰"],
    ["五行", "金木水火土", "木火土金水"],
    ["伤官", "食神", "伤官见官"],
    ["财", "财星", "正财", "偏财"],
    ["官", "官星", "正官", "偏官", "七杀"],
    ["印", "印星", "正印", "偏印", "枭神"],
]


def _load_chunks():
    """加载 chunks 目录下所有 JSON 文件，返回 list[dict]"""
    chunks = []
    if not os.path.isdir(_CHUNKS_DIR):
        return chunks
    for name in os.listdir(_CHUNKS_DIR):
        if not name.endswith(".json"):
            continue
        path = os.path.join(_CHUNKS_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 支持单对象或 {"chunks": [...]}
                if "chunks" in data:
                    chunks.extend(data["chunks"])
                else:
                    chunks.append(data)
        except Exception:
            continue
    return chunks


def _retrieve_vector(query: str, top_k: int) -> str:
    """使用本地向量库（npy + meta）语义检索白话文知识库。"""
    emb, meta = _load_vector_store()
    if emb is None or not meta:
        return ""
    q = query.strip()
    if not q:
        return ""
    try:
        from embedding_utils import embed_query
        import numpy as np
        q_vec = np.array(embed_query(q), dtype=np.float32).reshape(1, -1)
        # 余弦相似度：emb (N,d) @ q_vec.T (d,1) -> (N,1)，再归一化
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms[norms == 0] = 1e-9
        emb_n = emb / norms
        q_n = q_vec / (np.linalg.norm(q_vec) or 1e-9)
        scores = emb_n @ q_n.T
        scores = scores.flatten()
        top_idx = np.argsort(-scores)[:top_k]
        lines = ["【命理知识库参考】"]
        for i in top_idx:
            m = meta[i]
            source = m.get("source", "")
            content = (m.get("content") or "").strip()
            if content:
                lines.append(f"来源：{source}\n{content}\n")
        return "\n".join(lines) if len(lines) > 1 else ""
    except Exception:
        return ""


def _retrieve_keyword(query: str, top_k: int) -> str:
    """关键词/标签匹配检索（回退方案）。"""
    chunks = _load_chunks()
    if not chunks:
        return ""

    query_lower = query.strip().lower()
    query_words = set()
    for w in query_lower.replace("，", " ").replace("。", " ").split():
        if len(w) >= 2:
            query_words.add(w)
    for group in _QUERY_EXPAND_TERMS:
        if any(t in query_lower for t in group):
            query_words.update(group)

    scored = []
    for c in chunks:
        tags = " ".join(c.get("tags", []))
        content = (c.get("content") or "")
        text = (tags + " " + content).lower()
        score = sum(1 for w in query_words if w in text)
        if score > 0:
            scored.append((score, c))

    scored.sort(key=lambda x: -x[0])
    selected = [c for _, c in scored[:top_k]]

    if not selected:
        return ""

    lines = ["【命理知识库参考】"]
    for c in selected:
        source = c.get("source", "")
        content = (c.get("content") or "").strip()
        lines.append(f"来源：{source}\n{content}\n")
    return "\n".join(lines)


def retrieve(query: str, top_k: int = 5) -> str:
    """
    根据用户问题从知识库检索相关片段，返回拼接后的参考文本。
    优先使用白话文向量库语义检索；无向量库或无结果时回退到关键词检索。
    """
    ref = _retrieve_vector(query, top_k)
    if ref:
        return ref
    return _retrieve_keyword(query, top_k)
