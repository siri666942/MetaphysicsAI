"""
命理知识库向量化：使用 sentence-transformers 多语言模型生成 embedding，
供本地向量库（npy + meta.json）存储与语义检索。
"""

from __future__ import annotations

from typing import List

# 多语言模型，中英文均适用，体积适中
DEFAULT_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_model = None


def get_model():
    """懒加载 SentenceTransformer 模型，避免启动时即加载。"""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(DEFAULT_EMBED_MODEL)
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """对多段文本生成向量，返回 list of list of float。"""
    if not texts:
        return []
    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [emb.tolist() for emb in embeddings]


def embed_query(text: str) -> List[float]:
    """对单条查询生成向量。"""
    return embed_texts([text])[0]


class SentenceTransformerEmbeddingFunction:
    """
    Chroma 使用的 EmbeddingFunction：接收 Documents（List[str]），返回 Embeddings。
    """

    def __init__(self, model_name: str = DEFAULT_EMBED_MODEL):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def __call__(self, input: List[str]) -> List[List[float]]:
        if not input:
            return []
        model = self._get_model()
        embeddings = model.encode(input, convert_to_numpy=True)
        return [emb.tolist() for emb in embeddings]
