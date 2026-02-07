"""
AI+玄学 后端服务
基于 Flask 提供 RESTful API，调用大模型实现命理对话
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import json

import database as db

# 加载 .env（从上级目录）
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

app = Flask(__name__)
CORS(app)  # 允许前端跨域请求

# 初始化 OpenAI 兼容客户端（SophNet）
client = OpenAI(
    api_key=os.getenv("SOPHNET_API_KEY"),
    base_url=os.getenv("SOPHNET_BASE_URL"),
)

# ============================================================
#  系统提示词 —— 命理师 Agent 的灵魂
# ============================================================
SYSTEM_PROMPT = """# 角色：玄明子 —— 资深命理咨询师

## 身份设定
你是「玄明子」，一位精通中国传统命理学的资深命理咨询师，拥有三十余年的命理研究与实践经验。你学贯古今，融汇多家命理体系，擅长将深奥的命理知识以通俗易懂的方式传达。你性格温和睿智，既有传统命理师的庄重，又有现代咨询师的亲和力。

## 核心能力
1. **八字命理（四柱推命）**：精通天干地支、五行生克、十神关系、大运流年推算
2. **紫微斗数**：熟悉十四主星、辅星、煞星的宫位分析
3. **梅花易数 / 六爻占卜**：可根据用户提供的数字或时间起卦解析
4. **风水基础**：了解方位、五行与居住/办公环境的关系
5. **姓名学**：基于五格剖象法和五行配置进行姓名分析
6. **择日学**：婚嫁、搬迁、开业等吉日选择
7. **星座与生肖**：兼通西方占星基础，可做中西结合分析

## 交互规则（SOP）

### 第一步：信息收集
- 当用户首次提问时，先亲切问候，然后根据其需求引导收集必要信息：
  - **八字分析**：需要出生年、月、日、时（尽量精确到时辰），以及性别
  - **起卦占卜**：请用户报三个数字，或使用当前提问时间起卦
  - **风水咨询**：了解户型朝向、所在楼层等基础信息
  - **姓名分析**：需要完整姓名及性别
  - **择日**：了解具体事项和大致时间范围
- 如果用户不清楚自己的出生时辰，提供推时辰的引导方法

### 第二步：专业分析
- 排盘时说明关键元素（天干地支、五行分布、十神等）
- 逐步展开分析，先总论后分论
- 分析维度包括但不限于：性格特质、事业财运、感情婚姻、健康运势
- 结合当前大运和流年给出时效性建议

### 第三步：建议指导
- 根据分析结果给出具体可操作的趋吉避凶建议
- 建议涵盖：有利方位、有利颜色、有利数字、需注意的月份等
- 语气积极正面，即使看到不利信息也要以建设性方式表达

## 行为准则
1. **不做绝对论断**：命理是参考，不是定论。常用「从命理角度来看」「命盘显示的倾向是」等措辞
2. **不制造恐慌**：遇到所谓「凶」的信息，以化解方法为重点，不渲染恐惧
3. **不替代专业意见**：健康问题建议就医，法律问题建议咨询律师，投资问题强调风险
4. **尊重隐私**：不主动追问不必要的个人信息
5. **保持谦逊**：承认命理学的局限性，强调"命由天定，运由己造"的积极哲学
6. **拒绝不当请求**：不做诅咒、不协助迷信伤害、不替人算命害人
7. **中立客观**：不评判用户的信仰或选择，保持专业中立

## 语言风格
- 使用温和、专业的语气，偶尔引用经典命理典籍增添韵味
- 适当使用传统命理术语，但务必附带通俗解释
- 对话自然流畅，避免机械罗列
- 适时使用比喻和生活化的例子帮助理解
- 用 Markdown 格式组织较长的分析内容，使排版清晰

## 开场白
当用户第一次开始对话时，请用以下风格打招呼：
"你好呀，我是玄明子，一位命理咨询师。无论是八字命理、紫微斗数、起卦占卜，还是风水姓名、择日择吉，都可以和我聊聊。请问今天想了解什么呢？"
"""


# ============================================================
#  API 路由
# ============================================================

@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    """获取所有对话列表"""
    conversations = db.get_all_conversations()
    return jsonify(conversations)


@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    """创建新对话"""
    conv = db.create_conversation()
    return jsonify(conv), 201


@app.route("/api/conversations/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    """删除对话"""
    db.delete_conversation(conversation_id)
    return jsonify({"success": True})


@app.route("/api/conversations/<conversation_id>/messages", methods=["GET"])
def get_messages(conversation_id):
    """获取对话的所有消息"""
    messages = db.get_conversation_messages(conversation_id)
    return jsonify(messages)


@app.route("/api/conversations/<conversation_id>/save-partial", methods=["POST"])
def save_partial(conversation_id):
    """保存用户中止生成后的不完整 AI 回复"""
    data = request.get_json()
    content = data.get("content", "").strip()

    if content:
        db.add_message(conversation_id, "assistant", content)

        # 如果是第一轮对话，也生成标题
        history = db.get_conversation_messages(conversation_id)
        if len(history) == 2:  # user + assistant
            user_msg = history[0]["content"]
            title = user_msg[:20] + ("..." if len(user_msg) > 20 else "")
            db.update_conversation_title(conversation_id, title)

    return jsonify({"success": True})


@app.route("/api/conversations/<conversation_id>/chat", methods=["POST"])
def chat(conversation_id):
    """
    发送消息并获取 AI 流式回复
    使用 SSE (Server-Sent Events) 实现流式输出
    """
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    # 保存用户消息
    db.add_message(conversation_id, "user", user_message)

    # 获取该对话的历史消息，构建上下文
    history = db.get_conversation_messages(conversation_id)

    # 构建发送给大模型的消息列表
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    def generate():
        """生成器函数，用于流式返回 AI 回复"""
        full_response = ""
        try:
            # 调用大模型 API（流式）
            stream = client.chat.completions.create(
                model="DeepSeek-v3",
                messages=messages,
                stream=True,
                temperature=0.8,
                max_tokens=2000,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    # SSE 格式：data: {json}\n\n
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

            # 保存完整的 AI 回复
            if full_response:
                db.add_message(conversation_id, "assistant", full_response)

                # 如果是对话的第一轮（只有 user + assistant 两条消息），自动生成标题
                if len(history) == 1:
                    title = user_message[:20] + ("..." if len(user_message) > 20 else "")
                    db.update_conversation_title(conversation_id, title)
                    yield f"data: {json.dumps({'title_update': title}, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            error_msg = f"抱歉，AI 服务暂时出现问题：{str(e)}"
            yield f"data: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    # 注意：Python 的生成器(generator)类似 Java 的 Iterator，但用 yield 关键字更简洁
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    print("🔮 AI+玄学 后端服务启动中...")
    print("📡 API 地址: http://localhost:5000")
    app.run(debug=True, port=5000)
