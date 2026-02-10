# -*- coding: utf-8 -*-
"""
从 knowledge/raw 读取四本命理书，按段调用 LLM 做「文言→现代白话」全书重译，
输出到 knowledge/baihua/。支持高并发与断点续跑。
使用环境变量：SOPHNET_API_KEY / SOPHNET_BASE_URL，或 OPENAI_API_KEY / OPENAI_BASE_URL。
"""
from __future__ import annotations

import asyncio
import html
import json
import os
import re
import sys
from pathlib import Path

# 项目路径
BASE = Path(__file__).resolve().parent.parent
RAW_DIR = BASE / "knowledge" / "raw"
BAIHUA_DIR = BASE / "knowledge" / "baihua"
PROGRESS_DIR = BASE / "knowledge" / "progress_llm"

# 并发数（在允许范围内尽量高，不把电脑搞爆）
CONCURRENCY = 8
# 单段最大字符数，避免超长导致超 context
MAX_CHARS_PER_SEGMENT = 1200
# 最小段落长度，过短的与下一段合并
MIN_SEGMENT_CHARS = 80

# 翻译大师 + 玄学大师 合并系统提示词（用户全部采纳）
SYSTEM_PROMPT = """你是专业古籍翻译专家，擅长将中国古代命理、子平类文献从文言译成现代汉语白话。你同时熟悉《滴天髓》《三命通会》《渊海子平》《子平真诠》等典籍，能准确理解八字、十神、格局、用神、大运流年等概念，在译文中保持术语一致、含义不偏。

要求：
1. 仅做翻译，不增删原意：把文言/半文言逐句译成通顺的现代汉语，不添加个人解释或评论。
2. 专有名词保留并统一：天干地支、十神（正官、偏官、正财、偏财、印绶、食神、伤官等）、格局名、神煞名等照写，必要时首次出现可加简短括号说明。
3. 保留结构：原文的分段、小标题、诗诀的换行与分行尽量保持，便于与原文对照。
4. 若遇无法确定的字词，保留原字并标注[存疑]；不要编造内容。
5. 输出仅含该段白话译文，不要重复原文，不要输出「译文：」等前缀。
"""

# 四本书配置：(raw 文件名, baihua 文件名, 书名, 正文起始 marker 列表)
BOOKS = [
    ("滴天髓闡微.txt", "滴天髓阐微_白话.txt", "滴天髓阐微", ["通神论", "一、天道", "欲识三元"]),
    ("三命通會.txt", "三命通会_白话.txt", "三命通会", ["论五行生成", "卷一", "目錄 三命通會"]),
    ("yuanhaiziping.txt", "渊海子平_白话.txt", "渊海子平", ["《渊海子平》", "1       渊海子平"]),
    ("zipingzhenquan.txt", "子平真诠评注_白话.txt", "子平真诠评注", ["《子平真诠评注》", "1       《子平真诠评注》"]),
]


def unescape_and_clean(text: str) -> str:
    try:
        text = html.unescape(text)
    except Exception:
        pass
    text = re.sub(r"\r\n", "\n", text)
    return text.strip()


def extract_ctext_body(text: str, start_markers: list[str]) -> str:
    """从 ctext 或维基导出中截取正文。"""
    start = 0
    for m in start_markers:
        i = text.find(m)
        if i != -1:
            start = i
            break
    # 渊海/子平：结束在 .urnlabel 或 URN
    end_m = re.search(r"\.urnlabel|URN\s*:", text[start:], re.I)
    end = start + end_m.start() if end_m else len(text)
    body = text[start:end]
    body = re.sub(r"  +", " ", body)
    return body.strip()


def split_into_segments(body: str) -> list[str]:
    """将正文按段落切分为若干段，单段过长时按行再切。"""
    blocks = re.split(r"\n\s*\n", body)
    segments = []
    current: list[str] = []
    current_len = 0

    for blk in blocks:
        blk = blk.strip()
        if not blk:
            continue
        blk_len = len(blk)
        if blk_len <= MAX_CHARS_PER_SEGMENT:
            if current and current_len + blk_len + 2 <= MAX_CHARS_PER_SEGMENT and current_len < MIN_SEGMENT_CHARS:
                current.append(blk)
                current_len += blk_len + 2
            else:
                if current:
                    segments.append("\n\n".join(current))
                    current, current_len = [], 0
                if blk_len >= MIN_SEGMENT_CHARS:
                    segments.append(blk)
                else:
                    current.append(blk)
                    current_len = blk_len + 2
        else:
            if current:
                segments.append("\n\n".join(current))
                current, current_len = [], 0
            lines = [s.strip() for s in blk.split("\n") if s.strip()]
            buf, buf_len = [], 0
            for line in lines:
                need = len(line) + (1 if buf else 0)
                if buf_len + need <= MAX_CHARS_PER_SEGMENT:
                    buf.append(line)
                    buf_len += need
                else:
                    if buf:
                        segments.append("\n".join(buf))
                    buf = [line]
                    buf_len = len(line) + 1
                    if len(line) > MAX_CHARS_PER_SEGMENT:
                        segments.append(line)
                        buf, buf_len = [], 0
            if buf:
                segments.append("\n".join(buf))
    if current:
        segments.append("\n\n".join(current))
    return segments


def load_raw_book(raw_name: str, start_markers: list[str]) -> str:
    path = RAW_DIR / raw_name
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    text = unescape_and_clean(text)
    if "zipingzhenquan" in raw_name or "yuanhaiziping" in raw_name:
        return extract_ctext_body(text, start_markers)
    for m in start_markers:
        i = text.find(m)
        if i != -1:
            return text[i:]
    return text


async def translate_one(client, segment: str, sem: asyncio.Semaphore) -> str:
    """调用 LLM 翻译一段，带并发限制与重试。"""
    async with sem:
        for attempt in range(3):
            try:
                resp = await client.chat.completions.create(
                    model=os.getenv("SOPHNET_MODEL", "DeepSeek-v3"),
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": "将以下文言段落译成现代汉语白话，只输出译文，不要重复原文：\n\n" + segment},
                    ],
                    max_tokens=4096,
                    temperature=0.2,
                )
                choice = resp.choices[0]
                out = (choice.message.content or "").strip()
                return out or segment
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    await asyncio.sleep(2 ** attempt + 1)
                    continue
                raise
        return segment


def get_progress_path(book_key: str) -> Path:
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    return PROGRESS_DIR / f"{book_key}.json"


def load_progress(book_key: str) -> list[str]:
    p = get_progress_path(book_key)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("results", [])
    except Exception:
        return []


def save_progress(book_key: str, results: list[str]):
    p = get_progress_path(book_key)
    p.write_text(json.dumps({"results": results}, ensure_ascii=False, indent=0), encoding="utf-8")


async def translate_book(
    raw_name: str,
    baihua_name: str,
    title: str,
    start_markers: list[str],
    resume: bool,
    sem: asyncio.Semaphore,
    limit: int = 0,
):
    """翻译一本书，支持断点续跑。"""
    from openai import AsyncOpenAI

    api_key = os.getenv("SOPHNET_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("SOPHNET_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    if not api_key:
        print("错误：请设置环境变量 SOPHNET_API_KEY 或 OPENAI_API_KEY", file=sys.stderr)
        return

    body = load_raw_book(raw_name, start_markers)
    segments = split_into_segments(body)
    if limit > 0:
        segments = segments[:limit]
    total = len(segments)
    print(f"  [{title}] 共 {total} 段" + (f"（仅前 {limit} 段试跑）" if limit else ""))

    book_key = Path(raw_name).stem
    if resume:
        prev = load_progress(book_key)
        results = (prev + [""] * total)[:total]
    else:
        results = [""] * total
    start_idx = next((i for i in range(total) if not results[i]), total)
    if start_idx >= total:
        print(f"  [{title}] 已全部完成，跳过")
        write_baihua(baihua_name, title, results)
        return

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def task(i: int):
        if results[i]:
            return
        out = await translate_one(client, segments[i], sem)
        results[i] = out

    todo = list(range(start_idx, total))
    for i in range(0, len(todo), CONCURRENCY):
        batch = todo[i : i + CONCURRENCY]
        await asyncio.gather(*[task(j) for j in batch])
        save_progress(book_key, results)
        done = sum(1 for r in results if r)
        print(f"  [{title}] 已完成 {done}/{total} 段")

    for i in range(total):
        if not results[i]:
            results[i] = segments[i]
    save_progress(book_key, results)
    write_baihua(baihua_name, title, results)
    print(f"  [{title}] 已写入 {baihua_name}")


def write_baihua(baihua_name: str, title: str, results: list[str]):
    BAIHUA_DIR.mkdir(parents=True, exist_ok=True)
    header = f"【{title}】白话译述（LLM 全书重译），供 RAG 检索。以下为正文。\n\n"
    content = "\n\n".join(results)
    (BAIHUA_DIR / baihua_name).write_text(header + content, encoding="utf-8")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LLM 全书重译 raw -> baihua")
    parser.add_argument("--resume", action="store_true", help="断点续跑")
    parser.add_argument("--book", type=str, help="只翻译指定书（raw 文件名，如 滴天髓闡微.txt）")
    parser.add_argument("--limit", type=int, default=0, help="仅翻译前 N 段（试跑用，0=不限制）")
    args = parser.parse_args()

    # 加载 .env（backend 或项目根）
    for d in [BASE, BASE.parent]:
        env = d / ".env"
        if env.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env)
            except Exception:
                pass
            break

    books = BOOKS
    if args.book:
        books = [b for b in BOOKS if b[0] == args.book]
        if not books:
            print("未找到该书:", args.book, file=sys.stderr)
            sys.exit(1)

    sem = asyncio.Semaphore(CONCURRENCY)
    async def run():
        for raw_name, baihua_name, title, markers in books:
            await translate_book(raw_name, baihua_name, title, markers, args.resume, sem, args.limit)

    asyncio.run(run())
    print("全部完成，输出目录:", BAIHUA_DIR)


if __name__ == "__main__":
    main()
