"""
AI+玄学 后端服务
基于 Flask 提供 RESTful API，调用大模型实现命理对话
"""

from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import os
import json
import jwt  # PyJWT —— 注意：Python 里 import 名是 jwt，包名是 PyJWT

import database as db
import rag
from divination import (
    get_time_context, compute_bazi,
    compute_meihua, compute_meihua_by_time,
    compute_liuyao, compute_liuyao_by_time,
    now_local,
)
from inspiration import get_inspiration_samples
from match_algorithm import calculate_match_score, parse_bazi_text

# 加载 .env（从上级目录）
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

app = Flask(__name__)
CORS(app)  # 允许前端跨域请求

# JWT 密钥（生产环境请通过 .env 设置 JWT_SECRET）
JWT_SECRET = os.getenv("JWT_SECRET", "siri-universe-secret-key-change-me")

# 初始化 OpenAI 兼容客户端（SophNet）
client = OpenAI(
    api_key=os.getenv("SOPHNET_API_KEY"),
    base_url=os.getenv("SOPHNET_BASE_URL"),
)

# ============================================================
#  系统提示词 —— 命理师 Agent 的灵魂（含 CoT 八字分析 SOP）
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
8. **周公解梦**：精通《周公解梦》典籍，结合现代心理学（弗洛伊德、荣格）解析梦境象征、情绪映射与吉凶预兆
9. **缘分姓名趣味推演**：在用户主动问起时，可结合八字喜忌、姓名学五行与卦象意象，推测「未来另一半名字」的风格或若干示例字/名（见下专节，须免责声明）。

## 排盘必须用工具（严禁自行推算）
- **八字**：当用户提供出生日期（年/月/日/时）时，你必须调用 `get_bazi` 工具获取准确排盘，不得自行推算八字。LLM 不擅长农历与节气换算，自行推算会导致错误。
- **梅花易数/六爻**：用户要求起卦时，可调用 `get_meihua` 或 `get_liuyao`（用户给数字则传数字，否则用时间起卦）获取准确卦象后再解读。
- **当前时间**：当需要「当前时间」「现在几点」「今天什么日子」或按时间起卦时，必须调用 `get_current_time` 工具由 Python 获取真实时间，切勿自行推测。

## 八字分析标准步骤（SOP，严禁跳步）
在分析八字命盘时，必须按以下顺序展开，并在回复中体现逻辑链：
1. **定真假**：先看节气，确认月令深浅（是否换月、是否节气前后）。
2. **找格局**：根据月令透干，确定格局（如正官格、七杀格、食神格等）。
3. **看强弱**：分析日主在月令的状态（旺相休囚死），结合通根、透干情况。
4. **取用神**：根据旺衰与格局，找出八字最需要的五行（调候、扶抑等）。
5. **断大运**：结合前四步，分析当前大运的喜忌及流年注意点。
最后再分维度（性格、事业、感情、健康等）给出结论与建议。

## 交互规则（SOP）

### 第一步：信息收集
- 当用户首次提问时，先亲切问候，然后根据其需求引导收集必要信息：
  - **八字分析**：需要出生年、月、日、时（尽量精确到时辰），以及性别。一旦用户给出日期，立即调用 `get_bazi` 获取排盘，再进行分析。
  - **起卦占卜**：请用户报三个数字，或使用当前提问时间起卦（可调用 `get_meihua` / `get_liuyao`）。
  - **风水咨询**：了解户型朝向、所在楼层等基础信息
  - **姓名分析**：需要完整姓名及性别
  - **择日**：了解具体事项和大致时间范围
  - **周公解梦**：引导用户详细描述梦境元素（人物、场景、情绪、近期生活状态），从「传统象征」「心理映射」「吉凶预兆」「建议指引」四个维度展开分析
  - **缘分姓名趣味猜名**：若用户想猜未来对象可能叫什么、从八字/名字推姻缘名等，收集其**本名、性别、生辰（以便排盘）**或已知的卦象/喜好；信息不足时先引导补充再推演。
- 如果用户不清楚自己的出生时辰，提供推时辰的引导方法

### 第二步：专业分析
- 排盘一律基于工具返回的【八字排盘结果】【梅花易数排盘】【六爻排卦】进行解读，不得自行推算。
- 八字分析必须遵循「定真假→找格局→看强弱→取用神→断大运」的顺序。
- 逐步展开分析，先总论后分论；维度包括：性格特质、事业财运、感情婚姻、健康运势；结合大运流年给出建议。

### 第三步：建议指导
- 根据分析结果给出具体可操作的趋吉避凶建议
- 建议涵盖：有利方位、有利颜色、有利数字、需注意的月份等
- 语气积极正面，即使看到不利信息也要以建设性方式表达
- **八字分析时**：若排盘工具返回中带有【启示语参考·必做】段落，回复**必须**在最后单独写一段「启示赠言」，仿照参考的现代文或七言体风格（带悖论、留白，忌常规励志句如「命由天定运由己造」）。

## 未来伴侣姓名（趣味推演，对话内完成即可）
- 用户若问「猜猜我未来另一半叫什么」「从八字看对象名字」等，基于其提供的**姓名、八字（必须先调用 `get_bazi` 得盘）、喜用神/调候五行、生肖、或梅花易数/六爻卦象**等，用姓名学（五行补益、音韵意象、与日主十神相合的象征）给出**推测性**结论：可列 2～5 个**示例名或偏旁/五行倾向**，并简短说明每条依据。
- 无八字时可先用本名五格/五行或起一卦或者mbti以及他对话中提及的信息推测；能排盘时以工具盘为准，与姓名学结合表述。

## 语言风格
- 使用温和、专业的语气，偶尔引用经典命理典籍增添韵味
- 适当使用传统命理术语，但务必附带通俗解释
- 对话自然流畅，避免机械罗列
- 适时使用比喻和生活化的例子帮助理解
- 用 Markdown 格式组织较长的分析内容，使排版清晰

## 开场白
当用户第一次开始对话时，请用以下风格打招呼：
"你好呀，我是玄明子，一位命理咨询师。无论是八字命理、紫微斗数、起卦占卜，还是风水姓名、择日择吉，若想趣味猜猜缘分里另一半名字的意象，也可以说说你的名字或生辰，我按传统姓名学与盘局帮你推演一二。请问今天想了解什么呢？"
"""


# ============================================================
#  认证相关（JWT）
# ============================================================

def generate_token(user_id, username):
    """生成 JWT Token"""
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def verify_token(token):
    """验证 JWT Token，返回 payload 或 None"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def login_required(f):
    """装饰器：要求登录（检查 Authorization 头中的 Bearer Token）"""
    # Python 装饰器类似 Java 的注解(@Annotation)，但更灵活——它实际上是高阶函数
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else ''
        if not token:
            return jsonify({'error': '请先登录'}), 401
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': '登录已过期，请重新登录'}), 401
        request.user_id = payload['user_id']
        request.username = payload['username']
        return f(*args, **kwargs)
    return decorated


# ============================================================
#  认证 API
# ============================================================

@app.route("/api/auth/register", methods=["POST"])
def register():
    """用户注册"""
    data = request.get_json()
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    if len(username) < 2 or len(username) > 20:
        return jsonify({"error": "用户名长度应为 2-20 个字符"}), 400
    if len(password) < 6:
        return jsonify({"error": "密码长度至少 6 位"}), 400

    # 检查用户名是否已存在
    if db.get_user_by_username(username):
        return jsonify({"error": "该用户名已被注册"}), 409

    password_hash = generate_password_hash(password)
    user = db.create_user(username, password_hash)
    token = generate_token(user['id'], user['username'])

    return jsonify({
        "token": token,
        "user": {"id": user['id'], "username": user['username']},
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    """用户登录"""
    data = request.get_json()
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    # 快速登陆：用户名 s、密码不填，直接放行（仅方便本地测试）
    if username == "s" and not password:
        user = db.get_user_by_username("s")
        if not user:
            user = db.create_user("s", generate_password_hash(""))
        token = generate_token(user['id'], user['username'])
        return jsonify({
            "token": token,
            "user": {"id": user['id'], "username": user['username']},
        })

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400

    user = db.get_user_by_username(username)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"error": "用户名或密码错误"}), 401

    token = generate_token(user['id'], user['username'])

    return jsonify({
        "token": token,
        "user": {"id": user['id'], "username": user['username']},
    })


@app.route("/api/auth/me", methods=["GET"])
@login_required
def auth_me():
    """获取当前登录用户信息（顺便验证 token 有效性）"""
    user = db.get_user_by_id(request.user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404
    return jsonify({"id": user['id'], "username": user['username']})


# ============================================================
#  对话 API（需要登录）
# ============================================================

@app.route("/api/conversations", methods=["GET"])
@login_required
def list_conversations():
    """获取当前用户的所有对话列表"""
    conversations = db.get_all_conversations(user_id=request.user_id)
    return jsonify(conversations)


@app.route("/api/conversations", methods=["POST"])
@login_required
def create_conversation():
    """创建新对话（关联当前用户）"""
    conv = db.create_conversation(user_id=request.user_id)
    return jsonify(conv), 201


@app.route("/api/conversations/<conversation_id>", methods=["DELETE"])
@login_required
def delete_conversation(conversation_id):
    """删除对话"""
    if not db.conversation_belongs_to_user(conversation_id, request.user_id):
        return jsonify({"error": "无权操作"}), 403
    db.delete_conversation(conversation_id)
    return jsonify({"success": True})


@app.route("/api/conversations/<conversation_id>/title", methods=["PUT"])
@login_required
def update_title(conversation_id):
    """更新对话标题"""
    if not db.conversation_belongs_to_user(conversation_id, request.user_id):
        return jsonify({"error": "无权操作"}), 403
    data = request.get_json()
    title = data.get("title", "").strip()
    if title:
        db.update_conversation_title(conversation_id, title)
    return jsonify({"success": True})


@app.route("/api/conversations/<conversation_id>/messages", methods=["GET"])
@login_required
def get_messages(conversation_id):
    """获取对话的所有消息"""
    if not db.conversation_belongs_to_user(conversation_id, request.user_id):
        return jsonify({"error": "无权操作"}), 403
    messages = db.get_conversation_messages(conversation_id)
    return jsonify(messages)


@app.route("/api/conversations/<conversation_id>/save-partial", methods=["POST"])
@login_required
def save_partial(conversation_id):
    """保存用户中止生成后的不完整 AI 回复"""
    if not db.conversation_belongs_to_user(conversation_id, request.user_id):
        return jsonify({"error": "无权操作"}), 403
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


# ============================================================
#  Function Calling 工具定义（第三层：排盘由代码计算，AI 只解读）
# ============================================================

DIVINATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_bazi",
            "description": "根据用户提供的出生日期时间计算八字排盘。当用户说出出生年月日（及可选时辰、性别）时必须调用此工具获取准确八字，切勿自行推算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "出生年，如 1990"},
                    "month": {"type": "integer", "description": "出生月，1-12"},
                    "day": {"type": "integer", "description": "出生日"},
                    "hour": {"type": "integer", "description": "出生时辰（0-23），不确知时可传 12"},
                    "minute": {"type": "integer", "description": "出生分钟，默认 0"},
                    "is_male": {"type": "boolean", "description": "是否男命，默认 true"},
                    "is_solar": {"type": "boolean", "description": "year/month/day 是否为公历，默认 true"},
                },
                "required": ["year", "month", "day"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_meihua",
            "description": "梅花易数起卦。用户提供三个数字时传 numbers；否则用当前时间起卦，不传参数或传 by_time=true。",
            "parameters": {
                "type": "object",
                "properties": {
                    "numbers": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "三个数字 [上卦数, 下卦数, 动爻相关]，如 [3, 5, 7]",
                    },
                    "by_time": {"type": "boolean", "description": "为 true 时按当前时间起卦"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_liuyao",
            "description": "六爻排卦。用户提供三个数字时传 numbers；否则用当前时间起卦。",
            "parameters": {
                "type": "object",
                "properties": {
                    "numbers": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "三个数字，如 [2, 6, 9]",
                    },
                    "by_time": {"type": "boolean", "description": "为 true 时按当前时间起卦"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取服务器当前时间（由 Python 计算，非猜测）。在需用「当前时间」起卦、或回答「现在几点了」「今天是什么日子」等场景时必须调用此工具。切勿自行推测时间。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def run_divination_tool(name, arguments):
    """执行命理工具并返回字符串结果（供 Function Calling 使用）"""
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
        if name == "get_bazi":
            result = compute_bazi(
                year=int(args.get("year", 2000)),
                month=int(args.get("month", 1)),
                day=int(args.get("day", 1)),
                hour=int(args.get("hour", 12)),
                minute=int(args.get("minute", 0)),
                is_male=args.get("is_male", True),
                is_solar=args.get("is_solar", True),
            )
            result += "\n\n" + get_inspiration_samples()
            return result
        if name == "get_meihua":
            if args.get("numbers") and len(args["numbers"]) >= 3:
                result = compute_meihua(
                    args["numbers"][0], args["numbers"][1], args["numbers"][2]
                )
            else:
                result = compute_meihua_by_time()
            return result
        if name == "get_liuyao":
            if args.get("numbers") and len(args["numbers"]) >= 3:
                result = compute_liuyao(
                    args["numbers"][0], args["numbers"][1], args["numbers"][2]
                )
            else:
                result = compute_liuyao_by_time()
            return result
        if name == "get_current_time":
            now = now_local()
            return (
                f"当前时间（北京时间，已由系统 UTC 转换）：\n"
                f"- 公历：{now.strftime('%Y年%m月%d日 %H:%M:%S')}\n"
                f"- 星期：{['一','二','三','四','五','六','日'][now.weekday()]}\n"
                f"- Unix 时间戳：{int(now.timestamp())}\n"
                f"- 年/月/日/时/分（便于起卦）：year={now.year}, month={now.month}, day={now.day}, hour={now.hour}, minute={now.minute}"
            )
        return f"未知工具: {name}"
    except Exception as e:
        return f"工具执行出错: {str(e)}"


@app.route("/api/conversations/<conversation_id>/chat", methods=["POST"])
@login_required
def chat(conversation_id):
    """
    发送消息并获取 AI 流式回复
    支持 Function Calling：AI 可主动调用 get_bazi / get_meihua / get_liuyao 获取准确排盘后再解读
    使用 SSE (Server-Sent Events) 实现流式输出
    """
    if not db.conversation_belongs_to_user(conversation_id, request.user_id):
        return jsonify({"error": "无权操作"}), 403

    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    # 保存用户消息
    db.add_message(conversation_id, "user", user_message)

    # 获取该对话的历史消息，构建上下文
    history = db.get_conversation_messages(conversation_id)

    # ---- 动态构建系统提示词：时间上下文 + RAG 知识库检索（第一层「喂书」）----
    time_ctx = get_time_context()
    system_content = SYSTEM_PROMPT + "\n\n" + time_ctx
    # 根据用户问题检索命理知识库，若有结果则注入供模型参考
    knowledge_ref = rag.retrieve(user_message, top_k=5)
    if knowledge_ref:
        system_content += "\n\n" + knowledge_ref

    # 构建发送给大模型的消息列表
    messages = [{"role": "system", "content": system_content}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    def generate():
        """生成器函数，用于流式返回 AI 回复；内部可能先执行工具再流式输出"""
        full_response = ""
        try:
            # 第一轮：带 tools 的非流式调用，以便处理 tool_calls
            resp = client.chat.completions.create(
                model="step-3.5-flash",
                messages=messages,
                stream=False,
                temperature=0.8,
                max_tokens=2000,
                tools=DIVINATION_TOOLS,
                tool_choice="auto",
            )
            choice = resp.choices[0] if resp.choices else None
            if not choice:
                yield f"data: {json.dumps({'error': '模型未返回有效内容'}, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
                return

            message = choice.message
            # 若有 tool_calls，执行工具并把结果加入消息，再请求一轮（流式）
            while getattr(message, "tool_calls", None):
                tool_calls = message.tool_calls
                # 将 assistant 的 tool_calls 消息加入列表（OpenAI 格式）
                assistant_msg = {
                    "role": "assistant",
                    "content": message.content or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in tool_calls
                    ],
                }
                messages.append(assistant_msg)

                for tc in tool_calls:
                    name = tc.function.name
                    args_str = tc.function.arguments or "{}"
                    result = run_divination_tool(name, args_str)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

                # 继续请求，可能再次返回 tool_calls 或最终文本
                resp = client.chat.completions.create(
                    model="step-3.5-flash",
                    messages=messages,
                    stream=False,
                    temperature=0.8,
                    max_tokens=2000,
                    tools=DIVINATION_TOOLS,
                    tool_choice="auto",
                )
                choice = resp.choices[0] if resp.choices else None
                if not choice:
                    break
                message = choice.message

            # 最终回复内容
            final_content = getattr(message, "content", None) or ""
            if final_content:
                # 流式模拟：按小块发送，前端可逐段渲染
                chunk_size = 80
                for i in range(0, len(final_content), chunk_size):
                    chunk = final_content[i : i + chunk_size]
                    full_response += chunk
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"

            if full_response:
                db.add_message(conversation_id, "assistant", full_response)
                if len(history) == 1:
                    title = user_message[:20] + ("..." if len(user_message) > 20 else "")
                    db.update_conversation_title(conversation_id, title)
                    yield f"data: {json.dumps({'title_update': title}, ensure_ascii=False)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            error_msg = f"抱歉，AI 服务暂时出现问题：{str(e)}"
            yield f"data: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
#  占卜计算 API（供前端调用或测试）
# ============================================================

@app.route("/api/divination/bazi", methods=["POST"])
@login_required
def api_bazi():
    """八字排盘"""
    data = request.get_json()
    result = compute_bazi(
        year=data.get("year", 2000),
        month=data.get("month", 1),
        day=data.get("day", 1),
        hour=data.get("hour", 12),
        minute=data.get("minute", 0),
        is_male=data.get("is_male", True),
        is_solar=data.get("is_solar", True),
    )
    return jsonify({"result": result})


@app.route("/api/divination/meihua", methods=["POST"])
@login_required
def api_meihua():
    """梅花易数起卦"""
    data = request.get_json()
    nums = data.get("numbers", [])
    if len(nums) >= 3:
        result = compute_meihua(nums[0], nums[1], nums[2])
    else:
        result = compute_meihua_by_time()
    return jsonify({"result": result})


@app.route("/api/divination/liuyao", methods=["POST"])
@login_required
def api_liuyao():
    """六爻排卦"""
    data = request.get_json()
    nums = data.get("numbers", [])
    if len(nums) >= 3:
        result = compute_liuyao(nums[0], nums[1], nums[2])
    else:
        result = compute_liuyao_by_time()
    return jsonify({"result": result})


@app.route("/api/divination/time-context", methods=["GET"])
@login_required
def api_time_context():
    """获取当前时间上下文（测试用）"""
    return jsonify({"result": get_time_context()})


# ============================================================
#  匹配功能 API
# ============================================================

@app.route("/api/user/profile", methods=["GET"])
@login_required
def get_profile():
    """获取用户档案（可选参数user_id获取其他用户资料）"""
    target_user_id = request.args.get('user_id')
    
    if target_user_id:
        # 获取其他用户的资料（需要先检查是否在匹配历史中）
        shown_ids = db.get_shown_user_ids(request.user_id)
        if target_user_id not in shown_ids:
            return jsonify({"error": "无权查看该用户资料"}), 403
        
        profile = db.get_user_profile(target_user_id)
        user = db.get_user_by_id(target_user_id)
        
        if not profile or not user:
            return jsonify({"error": "用户不存在"}), 404
        
        # 合并用户名到资料中
        profile['username'] = user['username']
        return jsonify({"has_profile": True, "profile": profile})
    else:
        # 获取当前用户的资料
        profile = db.get_user_profile(request.user_id)
        if not profile:
            return jsonify({"has_profile": False})
        return jsonify({"has_profile": True, "profile": profile})


@app.route("/api/user/profile", methods=["POST"])
@login_required
def update_profile():
    """
    用户完善资料
    1. 接收前端表单数据
    2. 调用 compute_bazi() 计算八字
    3. 解析五行分布
    4. 存入 user_profiles 表
    """
    data = request.get_json()
    
    # 验证必填字段
    required_fields = ['birth_year', 'birth_month', 'birth_day', 'birth_hour', 'mbti', 'gender']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"缺少必填字段: {field}"}), 400
    
    # 调用八字计算
    bazi_result_text = compute_bazi(
        year=int(data['birth_year']),
        month=int(data['birth_month']),
        day=int(data['birth_day']),
        hour=int(data['birth_hour']),
        minute=0,
        is_male=(data['gender'] == 'male'),
        is_solar=True,
    )
    
    # 解析八字数据
    bazi_data = parse_bazi_text(bazi_result_text)
    
    # 保存到数据库
    db.save_user_profile(
        user_id=request.user_id,
        birth_year=int(data['birth_year']),
        birth_month=int(data['birth_month']),
        birth_day=int(data['birth_day']),
        birth_hour=int(data['birth_hour']),
        rizhu=bazi_data['rizhu'],
        rizhu_wuxing=bazi_data['rizhu_wuxing'],
        wuxing_count=bazi_data['wuxing_count'],
        wuxing_missing=bazi_data['wuxing_missing'],
        sizhu_data=bazi_data['sizhu'],
        mbti=data['mbti'].upper(),
        gender=data['gender'],
        bio=data.get('bio', ''),
        contact_info=data.get('contact_info', ''),
    )
    
    return jsonify({
        "success": True,
        "bazi_preview": {
            "rizhu": bazi_data['rizhu'],
            "wuxing": bazi_data['rizhu_wuxing'],
        }
    }), 201


@app.route("/api/user/profile/match-intro", methods=["PATCH"])
@login_required
def update_match_intro():
    """更新用于缘分匹配展示的简介与联系方式（不改生辰/MBTI）"""
    data = request.get_json() or {}
    bio = data.get("bio", "")
    contact_info = data.get("contact_info", "")
    if not isinstance(bio, str):
        bio = str(bio) if bio is not None else ""
    if not isinstance(contact_info, str):
        contact_info = str(contact_info) if contact_info is not None else ""
    bio = bio.strip()
    contact_info = contact_info.strip()
    if len(bio) > 100:
        return jsonify({"error": "个人简介最多100字"}), 400
    if len(contact_info) > 50:
        return jsonify({"error": "联系方式最多50字"}), 400

    prof = db.get_user_profile(request.user_id)
    if not prof or not prof.get("is_profile_complete"):
        return jsonify({"error": "请先完善匹配资料"}), 400

    if not db.update_user_match_intro(request.user_id, bio, contact_info):
        return jsonify({"error": "更新失败"}), 400

    return jsonify({"success": True, "bio": bio, "contact_info": contact_info})


@app.route("/api/match/entitlement", methods=["GET"])
@login_required
def match_entitlement():
    """缘分匹配权益（当前为全员免费，保留接口便于以后扩展）"""
    return jsonify({
        "match_premium": 1,
        "match_free_used": 0,
        "free_limit": None,
        "free_remaining": None,
        "price_fen": 0,
        "price_yuan": 0,
        "pay_configured": False,
    })


@app.route("/api/match/next", methods=["GET"])
@login_required
def get_next_match():
    """
    获取下一个匹配对象（探探式单次推荐）
    1. 获取当前用户profile
    2. 查询候选池（排除已展示+异性筛选）
    3. 计算所有候选的匹配度
    4. 返回分数最高的那个
    5. 记录到match_history
    """
    # 检查用户是否完善了资料
    my_profile = db.get_user_profile(request.user_id)
    if not my_profile or not my_profile.get('is_profile_complete'):
        return jsonify({"error": "请先完善个人资料"}), 400
    
    # 获取已展示过的用户ID列表
    shown_ids = db.get_shown_user_ids(request.user_id)
    
    # 获取候选池（异性+未展示+已完善资料）
    candidates = db.get_match_candidates(
        exclude_user_id=request.user_id,
        my_gender=my_profile['gender'],
        shown_ids=shown_ids
    )
    
    # 如果候选池空了
    if not candidates:
        # 检查是否是第一次（没有历史记录）
        if not shown_ids:
            return jsonify({
                "no_more": True,
                "message": "当前暂无可匹配的用户",
                "reason": "empty"
            })
        else:
            return jsonify({
                "no_more": True,
                "message": "已经看完所有人了！可以重新开始",
                "reason": "exhausted",
                "can_reset": True
            })
    
    # 计算每个候选的匹配度
    best_match = None
    best_score_data = None
    
    for candidate in candidates:
        score_data = calculate_match_score(my_profile, candidate)
        if not best_match or score_data['total_score'] > best_score_data['total_score']:
            best_match = candidate
            best_score_data = score_data
    
    # 记录历史
    db.add_match_history(request.user_id, best_match['user_id'], 'viewed')
    
    # 构建返回数据（脱敏处理）
    result = {
        "user_id": best_match['user_id'],
        "username": best_match.get('username') or '匿名用户',
        "bio": best_match.get('bio') or '',
        "rizhu": best_match['rizhu'],
        "rizhu_wuxing": best_match['rizhu_wuxing'],
        "mbti": best_match['mbti'],
        "gender": best_match['gender'],
        "contact_info": best_match.get('contact_info') or '',
        **best_score_data  # 展开匹配分数、原因等
    }
    
    return jsonify(result)


@app.route("/api/match/reset", methods=["POST"])
@login_required
def reset_matches():
    """重置匹配历史（用户刷完后可以重新开始）"""
    db.reset_match_history(request.user_id)
    return jsonify({"success": True, "message": "已重置，可以重新匹配了"})


@app.route("/api/match/history", methods=["GET"])
@login_required
def get_match_history():
    """获取用户的匹配历史列表"""
    my_profile = db.get_user_profile(request.user_id)
    if not my_profile:
        return jsonify({"error": "请先完善资料"}), 400
    
    # 获取匹配历史
    history = db.get_match_history(request.user_id)
    
    # 为每个历史记录计算匹配度
    result = []
    for item in history:
        matched_profile = {
            'user_id': item['shown_user_id'],
            'gender': item['gender'],
            'mbti': item['mbti'],
            'rizhu': item['rizhu'],
            'rizhu_wuxing': item['rizhu_wuxing'],
            'wuxing_count': item['wuxing_count'],
            'wuxing_missing': item['wuxing_missing'],
        }
        
        score_data = calculate_match_score(my_profile, matched_profile)
        
        result.append({
            'user_id': item['shown_user_id'],
            'username': item['username'],
            'bio': item['bio'] or '',
            'rizhu': item['rizhu'],
            'mbti': item['mbti'],
            'total_score': score_data['total_score'],
            'match_type': score_data['match_type'],
            'shown_at': item['shown_at'],
            'action': item['action']
        })
    
    return jsonify({"history": result})


@app.route("/api/match/detail/<matched_user_id>", methods=["GET"])
@login_required
def get_match_detail(matched_user_id):
    """获取匹配历史中某个用户的详细信息"""
    # 检查是否在匹配历史中
    shown_ids = db.get_shown_user_ids(request.user_id)
    if matched_user_id not in shown_ids:
        return jsonify({"error": "无权查看该用户资料"}), 403
    
    # 获取双方资料
    my_profile = db.get_user_profile(request.user_id)
    match_profile = db.get_user_profile(matched_user_id)
    
    if not match_profile:
        return jsonify({"error": "用户不存在"}), 404
    
    # 获取对方用户信息
    match_user = db.get_user_by_id(matched_user_id)
    
    # 计算匹配度
    score_data = calculate_match_score(my_profile, match_profile)
    
    # 构建返回数据
    result = {
        "user_id": matched_user_id,
        "username": match_user.get('username') or '匿名用户',
        "bio": match_profile.get('bio') or '',
        "rizhu": match_profile['rizhu'],
        "rizhu_wuxing": match_profile['rizhu_wuxing'],
        "mbti": match_profile['mbti'],
        "gender": match_profile['gender'],
        "contact_info": match_profile.get('contact_info') or '',
        **score_data
    }
    
    return jsonify(result)


@app.route("/api/match/message", methods=["POST"])
@login_required
def send_match_message():
    """发送留言给匹配对象"""
    data = request.get_json()
    
    to_user_id = data.get('to_user_id', '').strip()
    content = data.get('content', '').strip()
    
    if not to_user_id or not content:
        return jsonify({"error": "收件人和内容不能为空"}), 400
    
    if len(content) > 500:
        return jsonify({"error": "留言不能超过500字"}), 400
    
    # 检查对方是否存在
    target_user = db.get_user_by_id(to_user_id)
    if not target_user:
        return jsonify({"error": "用户不存在"}), 404
    
    # 保存留言
    msg = db.save_match_message(request.user_id, to_user_id, content)
    
    # 更新匹配历史（标记为已发消息）
    db.add_match_history(request.user_id, to_user_id, 'messaged')
    
    return jsonify({"success": True, "message_id": msg['id']}), 201


@app.route("/api/match/messages/threads", methods=["GET"])
@login_required
def get_message_threads():
    """获取所有留言对话线程"""
    threads = db.get_message_threads(request.user_id)
    return jsonify({"threads": threads})


@app.route("/api/match/messages/<other_user_id>", methods=["GET"])
@login_required
def get_messages_with(other_user_id):
    """获取与某个用户的所有留言"""
    messages = db.get_messages_with_user(request.user_id, other_user_id)
    
    # 标记为已读
    db.mark_messages_as_read(request.user_id, other_user_id)
    
    return jsonify({"messages": messages})


@app.route("/api/match/messages/unread-count", methods=["GET"])
@login_required
def get_unread_count():
    """获取未读留言数"""
    count = db.get_unread_message_count(request.user_id)
    app.logger.info(f"[未读消息] 用户ID: {request.user_id[:8]}..., 未读数: {count}")
    return jsonify({"unread_count": count})


@app.route("/api/match/report/<matched_user_id>", methods=["GET"])
@login_required
def generate_match_report(matched_user_id):
    """
    获取个性化配对报告
    优先返回缓存的报告，如果没有缓存则调用AI生成并缓存
    """
    # 先检查是否有缓存的报告
    cached = db.get_cached_report(request.user_id, matched_user_id)
    if cached:
        app.logger.info(f"[报告缓存] 用户 {request.user_id[:8]}... 查看与 {matched_user_id[:8]}... 的缓存报告")
        return jsonify({
            "report": cached['report_content'],
            "match_score": cached['match_score'],
            "match_type": cached['match_type'],
            "cached": True,
            "generated_at": cached['created_at']
        })
    
    # 没有缓存，生成新报告
    app.logger.info(f"[AI报告] 用户 {request.user_id[:8]}... 首次查看与 {matched_user_id[:8]}... 的报告，调用AI生成")
    
    # 获取双方资料
    my_profile = db.get_user_profile(request.user_id)
    match_profile = db.get_user_profile(matched_user_id)
    
    if not my_profile or not match_profile:
        return jsonify({"error": "用户资料不完整"}), 400
    
    # 获取对方用户名
    match_user = db.get_user_by_id(matched_user_id)
    
    # 计算匹配度（用于报告中引用）
    score_data = calculate_match_score(my_profile, match_profile)
    
    # 构建AI提示词
    system_prompt = """你是玄明子，一位资深命理师。现在需要为两位匹配成功的用户生成一份专属配对分析报告。

要求：
1. 字数800字左右
2. 包含：五行互补分析、MBTI契合度、相处建议、需注意事项
3. 语气要有诗意和玄学氛围，引用易经典籍
4. 多用比喻，少用术语堆砌
5. 以Markdown格式输出，包含标题和分段

输出结构：
## 缘分天注定·双人合盘分析

### 一、命理相性（八字合婚）
分析五行互补关系、日主相生相克

### 二、心理契合（MBTI分析）
分析性格互补与相处模式

### 三、相处之道
给出具体的相处建议

### 四、玄明子赠言
一段诗意的祝福语（引用易经或古诗词）"""
    
    # 构建用户提示词
    user_prompt = f"""请为以下两位用户生成配对报告：

**用户A（咨询者）：**
- 日主：{my_profile['rizhu']}（{my_profile['rizhu_wuxing']}）
- 五行分布：{my_profile['wuxing_count']}
- 五行缺失：{my_profile['wuxing_missing']}
- MBTI：{my_profile['mbti']}

**用户B（匹配对象 {match_user['username']}）：**
- 日主：{match_profile['rizhu']}（{match_profile['rizhu_wuxing']}）
- 五行分布：{match_profile['wuxing_count']}
- 五行缺失：{match_profile['wuxing_missing']}
- MBTI：{match_profile['mbti']}

**综合匹配度：{score_data['total_score']}分**
**缘分类型：{score_data['match_type']}**

请生成报告。注意称呼用户A为"你"，用户B为"TA"或"{match_user['username']}"。"""
    
    try:
        # 调用大模型生成报告（非流式）
        response = client.chat.completions.create(
            model="step-3.5-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=2000,
        )
        
        report = response.choices[0].message.content
        
        # 保存到缓存
        db.save_match_report(
            request.user_id, 
            matched_user_id, 
            report, 
            score_data['total_score'], 
            score_data['match_type']
        )
        
        return jsonify({
            "report": report,
            "match_score": score_data['total_score'],
            "match_type": score_data['match_type'],
            "cached": False
        })
    
    except Exception as e:
        return jsonify({"error": f"AI服务暂时出现问题：{str(e)}"}), 500


# ============================================================
#  静态前端（Docker / 同源部署时由 Flask 提供页面）
# ============================================================
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")


def _no_cache_headers(resp):
    """禁止缓存，确保部署后用户拿到最新 HTML/JS"""
    resp.headers["Cache-Control"] = "no-store, no-cache, max-age=0, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    return resp


@app.route("/")
def frontend_index():
    """首页：前端 SPA"""
    r = send_from_directory(_FRONTEND_DIR, "index.html")
    return _no_cache_headers(r)


@app.route("/<path:path>")
def frontend_static(path):
    """前端静态资源（仅当不是 /api 时；/api 已被上面路由处理）"""
    if path.startswith("api/"):
        return {"error": "Not Found"}, 404
    r = send_from_directory(_FRONTEND_DIR, path)
    if path in ("index.html", "script.js", "config.js"):
        _no_cache_headers(r)
    return r


# ============================================================
#  启动
# ============================================================

if __name__ == "__main__":
    # Zeabur / Railway 等平台通过 PORT 环境变量指定端口
    port = int(os.getenv("PORT", 5000))
    print("🔮 AI+玄学 后端服务启动中...")
    print(f"📡 API 地址: http://localhost:{port}")
    app.run(debug=True, port=port, host="0.0.0.0")
