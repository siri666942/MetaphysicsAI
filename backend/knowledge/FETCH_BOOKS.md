# 命理书抓取与切 chunk

## 直接抓取网页

脚本会**直接请求** `books_config.json` 里配置的 **url**，解析 HTML 提取正文并保存到 `knowledge/raw/<书id>.txt`。当前已预填中国哲学书电子化计划（ctext.org）的示例页：渊海子平、三命通会、子平真诠评注各一页；滴天髓 ctext 暂无，若需请填其他公开 url 或 `local_path`。

在 **backend** 目录执行：

```bash
python scripts/fetch_books.py
```

再将 raw 切为 RAG 用 chunk（占位，可后续补 tags/白话）：

```bash
python scripts/raw_to_chunks.py
```

chunk 会写入 `knowledge/chunks/`，与现有 ziwu_chong 等格式一致；可按需编辑 JSON 补 tags、注解、白话。

## 配置说明

- **books_config.json**：`books` 里每项可填 `url`（单页）、`urls`（多页顺序抓取）、`local_path`（本地 .txt；有则优先于 url）。  
- PDF 需先自行转为 .txt 再填 `local_path`。  
- 请仅填写您有权使用的来源。

## 当前书单

渊海子平、滴天髓、三命通会、子平真诠评注（徐乐吾版）。  
书名与 id 见 `books_config.json`。
