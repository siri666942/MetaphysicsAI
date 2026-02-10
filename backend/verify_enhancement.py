# 玄学工具增强 · 验证脚本（验证后可删除）
import sys
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

errors = []

# 1. RAG 检索
import rag
r = rag.retrieve("我八字里子午冲代表什么", top_k=3)
if not r or ("子午" not in r and "冲" not in r):
    errors.append("RAG: retrieve 对「子午冲」应返回知识库内容")
else:
    print("RAG retrieve: OK, len=%d" % len(r))

# 2. 工具执行 get_bazi
from app import run_divination_tool
bazi = run_divination_tool("get_bazi", '{"year":1990,"month":5,"day":1}')
if "八字" not in bazi or "四柱" not in bazi:
    errors.append("run_divination_tool(get_bazi) 应返回含八字、四柱的排盘文本")
else:
    print("run_divination_tool(get_bazi): OK")

# 3. 工具执行 get_meihua（时间起卦）
meihua = run_divination_tool("get_meihua", '{"by_time": true}')
if "梅花" not in meihua and "卦" not in meihua:
    errors.append("run_divination_tool(get_meihua) 应返回梅花易数排盘")
else:
    print("run_divination_tool(get_meihua): OK")

if errors:
    print("FAIL:", errors)
    sys.exit(1)
print("All checks passed.")
sys.exit(0)
