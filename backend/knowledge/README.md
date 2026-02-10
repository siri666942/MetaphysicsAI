# 命理知识库 · 喂书说明

本目录用于存放**结构化命理知识块**，供 RAG（检索增强生成）使用。思路参考《赛博算命的喂书方法》：不直接喂古文原文，而是**白话/注解版 + 标签**，便于检索且避免断章取义。

## 数据块格式

每个概念可单独一个 JSON 文件，放在 `chunks/` 下。格式示例：

```json
{
  "id": "ziwu_chong",
  "source": "渊海子平",
  "tags": ["刑冲合害", "地支", "子午冲"],
  "content": "原文：子午相冲。\n注解：子水午火，水火相冲。\n现代：子午冲主变动、奔波，或心肾不交。"
}
```

- **tags**：用于检索的标签，如 `[十天干]`、`[月令]`、`[长生十二宫]`、`[刑冲合害]`、`[格局]`、`[用神]` 等。
- **content**：一段完整内容，可包含「原文 / 任铁樵注 / 现代翻译」及适用场景。

## 白话文素材（供 RAG）

`baihua/` 目录下为四本命理书的**白话译述** txt，由 `scripts/raw_to_baihua.py` 从 `raw/` 提取并做文言→白话转换生成，可直接作为 RAG 高质量素材：

- 渊海子平_白话.txt  
- 子平真诠评注_白话.txt  
- 三命通会_白话.txt  
- 滴天髓阐微_白话.txt  

重新生成：在 backend 下执行 `python scripts/raw_to_baihua.py`。

## 书籍抓取与切 chunk（可选）

唯一需您提供的是**书源**（在 `books_config.json` 中填每本书的 `url` 或 `local_path`）。填好后在 backend 下执行：

- `python scripts/fetch_books.py` → 输出到 `raw/<书id>.txt`
- `python scripts/raw_to_chunks.py` → 将 raw 切为 chunk 占位到 `chunks/`，可再补 tags 与白话

详见 **FETCH_BOOKS.md**。

## 推荐典籍与整理方式

- 《渊海子平》《滴天髓》《三命通会》：拆成「原文 + 注解 + 白话」数据块并打标签。
- 《子平真诠评注》（徐乐吾版）：逻辑清晰，适合优先整理为知识库。

## 扩展为向量检索（可选）

当前为**关键词/标签匹配**检索。若需更强语义检索，可：

1. 为每个 chunk 计算 embedding（调用 OpenAI 或本地模型）。
2. 存入向量库（Chroma、FAISS、pgvector 等）。
3. 在 `rag.py` 中改为：先向量检索 top_k，再按需过滤标签。

目录与 chunk 格式保持不变，仅替换 `retrieve()` 的实现即可。
