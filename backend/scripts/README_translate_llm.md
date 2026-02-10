# LLM 全书重译：raw → baihua

## 脚本

- **`translate_raw_to_baihua_llm.py`**：从 `knowledge/raw` 读取四本命理书，按段并发调用 LLM 做「文言→现代白话」全书重译，输出到 `knowledge/baihua/`。

## 环境变量

- **必选**：`SOPHNET_API_KEY` 或 `OPENAI_API_KEY`
- **可选**：`SOPHNET_BASE_URL` / `OPENAI_BASE_URL`（不设则用 OpenAI 默认）
- **可选**：`SOPHNET_MODEL`（默认 `DeepSeek-V3.2-Exp`）

`.env` 放在项目根或 `backend/` 下即可，脚本会自动加载。

## 用法

```bash
cd backend
# 全书重译（四本，高并发 8）
python scripts/translate_raw_to_baihua_llm.py

# 断点续跑（中断后再次执行）
python scripts/translate_raw_to_baihua_llm.py --resume

# 只译某一本
python scripts/translate_raw_to_baihua_llm.py --book "滴天髓闡微.txt"

# 试跑：只译前 2 段
python scripts/translate_raw_to_baihua_llm.py --book "滴天髓闡微.txt" --limit 2
```

## 提示词

- **翻译大师 + 玄学大师** 已合并为脚本内系统提示词：既要求「文言→现代白话、专有名词统一、保留结构」，又要求「熟悉子平典籍、术语一致、不编造」。
- 如需修改，编辑 `translate_raw_to_baihua_llm.py` 中的 `SYSTEM_PROMPT`。

## 进度与重跑

- 每本书的进度保存在 `knowledge/progress_llm/<书名>.json`。
- 断点续跑：用 `--resume`，会从未完成段继续。
- **从头重译**：删掉 `knowledge/progress_llm/` 下对应书的 `.json`，再运行（不加 `--resume`）。

## 并发与性能

- 并发数：脚本内 `CONCURRENCY = 8`，在尽量缩短时间与不压爆电脑之间折中。
- 单段约 1200 字以内，过长会按行再切。
- 预计：四本书全部译完约数小时（视 API 与网络而定）。
