#!/usr/bin/env python3
"""
命理知识库 · 书籍抓取/导入工具

从 books_config.json 中读取书单，对每本书：
- 若配置了 local_path 且文件存在：从本地读取并保存到 knowledge/raw/<id>.txt
- 若配置了 url：请求该 URL，解析 HTML 提取正文，保存到 knowledge/raw/<id>.txt

使用前请在 knowledge/books_config.json 中填写 url 或 local_path。
仅请使用您有权使用的公开来源或自有文件。
"""

import os
import sys
import json
import time
import re

# 保证可导入 knowledge 同级的模块（若需）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

KNOWLEDGE_DIR = os.path.join(BACKEND_DIR, "knowledge")
CONFIG_PATH = os.path.join(KNOWLEDGE_DIR, "books_config.json")
RAW_DIR = os.path.join(KNOWLEDGE_DIR, "raw")


def load_config():
    if not os.path.isfile(CONFIG_PATH):
        print(f"未找到配置: {CONFIG_PATH}")
        return None
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_raw_dir():
    os.makedirs(RAW_DIR, exist_ok=True)


def extract_text_from_html(html: str, url: str = "") -> str:
    """从 HTML 中提取正文，尽量去掉导航、广告等。"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return re.sub(r"<[^>]+>", " ", html).strip()

    soup = BeautifulSoup(html, "html.parser")
    # 常见正文容器
    for selector in ["article", ".content", ".article", "#content", ".post-content", "main", ".chapter"]:
        node = soup.select_one(selector)
        if node:
            text = node.get_text(separator="\n", strip=True)
            if len(text) > 200:
                return _normalize_text(text)
    # 用 body
    body = soup.find("body")
    if body:
        text = body.get_text(separator="\n", strip=True)
        if len(text) > 100:
            return _normalize_text(text)
    return _normalize_text(soup.get_text(separator="\n", strip=True))


def _normalize_text(s: str) -> str:
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def fetch_url(url: str, headers: dict, timeout: int = 30) -> tuple[str, str]:
    """返回 (content, encoding_or_error)。"""
    try:
        import requests
    except ImportError:
        return "", "需要安装 requests: pip install requests"
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        # 优先用 declared encoding，否则用 apparent
        enc = r.encoding or "utf-8"
        if enc.lower() in ("iso-8859-1", "ascii"):
            enc = "utf-8"
        try:
            text = r.content.decode(enc)
        except Exception:
            text = r.content.decode("utf-8", errors="replace")
        return text, ""
    except Exception as e:
        return "", str(e)


def read_local(path: str) -> tuple[str, str]:
    """读取本地文件，返回 (content, error)。仅支持文本类；PDF 需先自行转为 txt 或使用其他工具。"""
    if not os.path.isfile(path):
        return "", f"文件不存在: {path}"
    if path.lower().endswith(".pdf"):
        return "", "本地暂不支持直接读 PDF，请先用其他工具转为 .txt 再指定 local_path"
    try:
        for enc in ("utf-8", "gbk", "gb2312", "utf-8-sig"):
            try:
                with open(path, "r", encoding=enc) as f:
                    return f.read(), ""
            except UnicodeDecodeError:
                continue
        with open(path, "rb") as f:
            raw = f.read()
        return raw.decode("utf-8", errors="replace"), ""
    except Exception as e:
        return "", str(e)


def process_book(book: dict, headers: dict) -> bool:
    bid = book.get("id", "").strip()
    name = book.get("name", "未命名")
    local_path = (book.get("local_path") or "").strip()
    url = (book.get("url") or "").strip()
    urls = book.get("urls") or []
    urls = [u.strip() for u in urls if u and str(u).strip()]

    out_path = os.path.join(RAW_DIR, f"{bid}.txt")
    content = None
    source = ""

    if local_path:
        content, err = read_local(local_path)
        if err:
            print(f"  [跳过] {name} 本地: {err}")
            return False
        source = "local"
    elif urls:
        parts = []
        for i, u in enumerate(urls):
            raw, err = fetch_url(u, headers)
            if err:
                print(f"  [警告] {name} 第{i+1}页 {u[:50]}... 请求失败: {err}")
                continue
            if "<" in (raw[:500] if len(raw) > 500 else raw):
                parts.append(extract_text_from_html(raw, u))
            else:
                parts.append(raw)
            time.sleep(1)
        content = "\n\n".join(p for p in parts if p.strip()) if parts else ""
        source = "urls"
    elif url:
        raw, err = fetch_url(url, headers)
        if err:
            print(f"  [跳过] {name} 请求: {err}")
            return False
        if "text/html" in str(headers.get("Accept", "")) or "<" in raw[:200]:
            content = extract_text_from_html(raw, url)
        else:
            content = raw
        source = "url"
    else:
        print(f"  [跳过] {name} 未配置 url / urls 或 local_path")
        return False

    if not content or len(content.strip()) < 50:
        print(f"  [跳过] {name} 内容过短或为空 (len={len(content or '')})")
        return False

    ensure_raw_dir()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  [OK] {name} -> {out_path} (来源: {source}, 约 {len(content)} 字)")
    return True


def main():
    config = load_config()
    if not config:
        return 1
    books = config.get("books", [])
    headers = config.get("request_headers", {})
    if not books:
        print("books 列表为空，请在 books_config.json 中配置。")
        return 0
    ensure_raw_dir()
    print(f"输出目录: {RAW_DIR}")
    ok = 0
    for i, book in enumerate(books):
        if process_book(book, headers):
            ok += 1
        if (i + 1) < len(books):
            time.sleep(1)
    print(f"完成: {ok}/{len(books)} 本已保存到 raw/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
