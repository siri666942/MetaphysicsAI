# -*- coding: utf-8 -*-
"""
从 knowledge/raw 读取四本命理书，提取正文并做文言→白话转换，输出到 knowledge/baihua/。
供 RAG 检索使用。
"""
import re
import html
from pathlib import Path

# 项目内 raw / baihua 路径（脚本在 backend/scripts/ 运行则用 ..）
BASE = Path(__file__).resolve().parent.parent
RAW_DIR = BASE / "knowledge" / "raw"
BAIHUA_DIR = BASE / "knowledge" / "baihua"

# 文言 → 白话 常用替换（按长度降序，避免短词先匹配）
# 命理术语如 四柱、月令、用神、格局、身旺、身弱、大运 等保留不译，便于 RAG 检索
WENYAN_TO_BAIHUA = [
    # 句首/连接
    ("夫大运者", "说到大运"),
    ("夫疾病者", "说到疾病"),
    ("夫正官者", "说到正官"),
    ("夫偏官者", "说到偏官"),
    ("夫七杀者", "说到七杀"),
    ("夫印绶者", "说到印绶"),
    ("夫阳刃者", "说到阳刃"),
    ("夫魁罡者", "说到魁罡"),
    ("夫金神者", "说到金神"),
    ("夫六亲者", "说到六亲"),
    ("夫倒食者", "说到倒食"),
    ("夫干犹木之干", "天干好比树木的树干"),
    ("夫支犹木之枝", "地支好比树木的枝条"),
    ("月令者，提纲也", "月令就是提纲"),
    ("月令者，天元也", "月令就是天元"),
    ("大抵", "一般来说"),
    ("何也？", "为什么呢？"),
    ("何也；", "为什么呢；"),
    ("何也。", "为什么呢。"),
    ("何以言之？", "为什么这么说呢？"),
    ("何谓之", "什么叫作"),
    ("谓之", "叫作"),
    ("乃", "是"),
    ("盖", "原来、因为"),
    ("故", "所以"),
    ("故云", "所以说"),
    ("经云", "经书上说"),
    ("经曰", "经书上说"),
    ("曰", "说"),
    ("主", "主指、代表"),
    ("忌", "不宜、忌讳"),
    ("喜", "宜、喜用"),
    ("克", "克制、克伤"),
    ("曰官", "叫作官"),
    ("曰杀", "叫作杀"),
    ("曰财", "叫作财"),
    ("曰印", "叫作印"),
    ("曰食神", "叫作食神"),
    ("曰伤官", "叫作伤官"),
    ("曰劫财", "叫作劫财"),
    ("曰阳刃", "叫作阳刃"),
    ("日乾", "日干"),
    ("天乾", "天干"),
    ("支乾", "支干"),
    ("乾旺", "干旺"),
    ("乾弱", "干弱"),
    ("乾同", "干同"),
    ("乾克", "干克"),
    ("年乾", "年干"),
    ("岁乾", "岁干"),
    ("馀", "余"),
    ("僞", "伪"),
    ("衆", "众"),
    ("穀", "谷"),
    ("體", "体"),
    ("無", "无"),
    ("猶", "犹"),
    ("於", "于"),
    ("爲", "为"),
    ("異", "异"),
    ("盡", "尽"),
    ("發", "发"),
    ("見", "见"),
    ("論", "论"),
    ("運", "运"),
    ("歲", "岁"),
    ("時", "时"),
    ("陰", "阴"),
    ("陽", "阳"),
    ("氣", "气"),
    ("機", "机"),
    ("關", "关"),
    ("殺", "杀"),
    ("脈", "脉"),
    ("臟", "脏"),
    ("臟腑", "脏腑"),
    ("窮", "穷"),
    ("變", "变"),
    ("萬", "万"),
    ("與", "与"),
    ("惡", "恶"),
    ("聖", "圣"),
    ("書", "书"),
    ("當", "当"),
    ("處", "处"),
    ("貴", "贵"),
    ("賤", "贱"),
    ("壽", "寿"),
    ("夭", "夭"),
    ("禍", "祸"),
    ("災", "灾"),
    ("驗", "验"),
    ("詳", "详"),
    ("靈", "灵"),
    ("顯", "显"),
    ("際", "际"),
]


def unescape_and_clean(text: str) -> str:
    """解码 HTML 实体并做基本清理。"""
    try:
        text = html.unescape(text)
    except Exception:
        pass
    # 去掉首尾空白、多余空行
    text = re.sub(r"\r\n", "\n", text)
    text = text.strip()
    return text


def extract_ctext_body(text: str) -> str:
    """从 ctext 抓取页中提取正文：从《书名》或 1 开头到 .urnlabel 或 URN 之前。"""
    # 找《渊海子平》或《子平真诠》或 "1 " 开头的内容块
    for start in ["《渊海子平》", "《子平真诠评注》", "1       渊海子平", "1       《子平真诠评注》"]:
        i = text.find(start)
        if i != -1:
            break
    else:
        # 退而求其次：从第一个 "1 " 数字+空格+中文 开始
        m = re.search(r"\d+\s+[^\d\s].{2,50}", text)
        if m:
            i = m.start()
        else:
            i = 0
    # 结束：.urnlabel 或 URN :
    end_m = re.search(r"\.urnlabel|URN\s*:", text[i:], re.I)
    end = i + end_m.start() if end_m else len(text)
    body = text[i:end]
    # 去掉行内多余空格，保留换行
    body = re.sub(r"  +", " ", body)
    return body.strip()


def wen_to_baihua(s: str) -> str:
    """对字符串做文言→白话替换（按词条顺序，长词优先）。"""
    for w, b in WENYAN_TO_BAIHUA:
        s = s.replace(w, b)
    return s


def process_yuanhaiziping() -> str:
    raw_path = RAW_DIR / "yuanhaiziping.txt"
    text = raw_path.read_text(encoding="utf-8", errors="replace")
    text = unescape_and_clean(text)
    body = extract_ctext_body(text)
    return wen_to_baihua(body)


def process_zipingzhenquan() -> str:
    raw_path = RAW_DIR / "zipingzhenquan.txt"
    text = raw_path.read_text(encoding="utf-8", errors="replace")
    text = unescape_and_clean(text)
    body = extract_ctext_body(text)
    return wen_to_baihua(body)


def process_sanmingtonghui() -> str:
    raw_path = RAW_DIR / "三命通會.txt"
    text = raw_path.read_text(encoding="utf-8", errors="replace")
    text = unescape_and_clean(text)
    # 去掉维基导出说明等，保留从「论五行生成」或「卷一」起的正文
    for marker in ["论五行生成", "卷一", "目錄 三命通會"]:
        i = text.find(marker)
        if i != -1:
            text = text[i:]
            break
    return wen_to_baihua(text)


def process_ditiansui() -> str:
    raw_path = RAW_DIR / "滴天髓闡微.txt"
    text = raw_path.read_text(encoding="utf-8", errors="replace")
    text = unescape_and_clean(text)
    for marker in ["通神论", "一、天道", "欲识三元"]:
        i = text.find(marker)
        if i != -1:
            text = text[i:]
            break
    return wen_to_baihua(text)


def main():
    BAIHUA_DIR.mkdir(parents=True, exist_ok=True)

    # 每本书前加一行说明，便于 RAG 识别
    def write_baihua(filename: str, content: str, title: str):
        header = f"【{title}】白话译述，供 RAG 检索。以下为正文。\n\n"
        (BAIHUA_DIR / filename).write_text(header + content, encoding="utf-8")
        print(f"  写入 {len(header) + len(content)} 字")

    print("处理 渊海子平...")
    out = process_yuanhaiziping()
    write_baihua("渊海子平_白话.txt", out, "渊海子平")

    print("处理 子平真诠评注...")
    out = process_zipingzhenquan()
    write_baihua("子平真诠评注_白话.txt", out, "子平真诠评注")

    print("处理 三命通会...")
    out = process_sanmingtonghui()
    write_baihua("三命通会_白话.txt", out, "三命通会")

    print("处理 滴天髓阐微...")
    out = process_ditiansui()
    write_baihua("滴天髓阐微_白话.txt", out, "滴天髓阐微")

    print("全部完成，输出目录:", BAIHUA_DIR)


if __name__ == "__main__":
    main()
