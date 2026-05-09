"""
SQLite 数据库模块 —— 管理用户、对话和消息的持久化存储
"""

import sqlite3
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量（确保在获取 DB_PATH 之前）
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# 支持通过环境变量指定数据库路径，便于 Zeabur 等平台挂载 Volume 做持久化
# 若未设置，则使用 backend 目录下的 chat_history.db
DB_PATH = os.getenv("DATABASE_PATH") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "chat_history.db"
)


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    # 让查询结果可以通过列名访问，类似 Java 的 ResultSet
    conn.row_factory = sqlite3.Row
    # 开启外键支持
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """初始化数据库表结构（含用户表）"""
    conn = get_connection()
    cursor = conn.cursor()

    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # 对话表（user_id 可为空，兼容旧数据）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '新对话',
            user_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # 消息表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)

    # 用户档案表（匹配功能）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            birth_year INTEGER,
            birth_month INTEGER,
            birth_day INTEGER,
            birth_hour INTEGER,
            rizhu TEXT,
            rizhu_wuxing TEXT,
            wuxing_count TEXT,
            wuxing_missing TEXT,
            sizhu_data TEXT,
            mbti TEXT,
            gender TEXT,
            bio TEXT,
            contact_info TEXT,
            allow_match BOOLEAN DEFAULT 1,
            is_profile_complete BOOLEAN DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # 匹配历史表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_history (
            user_id TEXT,
            shown_user_id TEXT,
            shown_at TEXT,
            action TEXT,
            PRIMARY KEY (user_id, shown_user_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (shown_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # 留言表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_messages (
            id TEXT PRIMARY KEY,
            from_user_id TEXT,
            to_user_id TEXT,
            content TEXT,
            is_read BOOLEAN DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY (from_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (to_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # AI配对报告缓存表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS match_reports (
            user_id TEXT,
            matched_user_id TEXT,
            report_content TEXT,
            match_score REAL,
            match_type TEXT,
            created_at TEXT,
            PRIMARY KEY (user_id, matched_user_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (matched_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # 微信支付订单（Native 扫码）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wechat_pay_orders (
            out_trade_no TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount_fen INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            transaction_id TEXT,
            created_at TEXT NOT NULL,
            paid_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # 检查 conversations 表是否有 user_id 列（兼容旧数据库）
    cursor.execute("PRAGMA table_info(conversations)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'user_id' not in columns:
        cursor.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")

    conn.commit()
    conn.close()


# ============================================================
#  用户相关
# ============================================================

def create_user(username, password_hash):
    """创建新用户，返回用户信息"""
    conn = get_connection()
    cursor = conn.cursor()

    user_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO users (id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (user_id, username, password_hash, now),
    )

    conn.commit()
    conn.close()

    return {"id": user_id, "username": username, "created_at": now}


def get_user_by_username(username):
    """根据用户名查询用户，不存在返回 None"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()

    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    """根据 ID 查询用户"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()

    conn.close()
    return dict(row) if row else None


# ============================================================
#  对话相关
# ============================================================

def create_conversation(user_id=None):
    """创建新对话，返回对话信息"""
    conn = get_connection()
    cursor = conn.cursor()

    conv_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO conversations (id, title, user_id, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (conv_id, "新对话", user_id, now, now),
    )

    conn.commit()
    conn.close()

    return {"id": conv_id, "title": "新对话", "created_at": now, "updated_at": now}


def get_all_conversations(user_id=None):
    """获取对话列表，按更新时间倒序。传入 user_id 则只返回该用户的对话"""
    conn = get_connection()
    cursor = conn.cursor()

    if user_id:
        cursor.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        )
    else:
        cursor.execute("SELECT * FROM conversations ORDER BY updated_at DESC")

    # Python 的 dict() 可以直接转换 sqlite3.Row，不需要像 Java 那样手动映射
    rows = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return rows


def get_conversation_messages(conversation_id):
    """获取指定对话的所有消息"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return rows


def add_message(conversation_id, role, content):
    """向对话中添加一条消息"""
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) "
        "VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, now),
    )

    # 更新对话的最后修改时间
    cursor.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (now, conversation_id),
    )

    conn.commit()
    conn.close()

    return {"role": role, "content": content, "created_at": now}


def update_conversation_title(conversation_id, title):
    """更新对话标题"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE conversations SET title = ? WHERE id = ?",
        (title, conversation_id),
    )

    conn.commit()
    conn.close()


def delete_conversation(conversation_id):
    """删除对话及其所有消息"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    conn.commit()
    conn.close()


def conversation_belongs_to_user(conversation_id, user_id):
    """检查对话是否属于指定用户"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM conversations WHERE id = ?", (conversation_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return False
    return row['user_id'] == user_id


# ============================================================
#  匹配功能 - 用户档案相关
# ============================================================

def save_user_profile(user_id, birth_year, birth_month, birth_day, birth_hour,
                      rizhu, rizhu_wuxing, wuxing_count, wuxing_missing,
                      sizhu_data, mbti, gender, bio='', contact_info=''):
    """保存或更新用户档案"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    import json
    wuxing_count_json = json.dumps(wuxing_count, ensure_ascii=False)
    wuxing_missing_json = json.dumps(wuxing_missing, ensure_ascii=False)
    sizhu_data_json = json.dumps(sizhu_data, ensure_ascii=False)
    
    cursor.execute("SELECT user_id FROM user_profiles WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()
    
    if exists:
        cursor.execute("""
            UPDATE user_profiles SET
                birth_year=?, birth_month=?, birth_day=?, birth_hour=?,
                rizhu=?, rizhu_wuxing=?, wuxing_count=?, wuxing_missing=?,
                sizhu_data=?, mbti=?, gender=?, bio=?, contact_info=?,
                is_profile_complete=1, updated_at=?
            WHERE user_id=?
        """, (birth_year, birth_month, birth_day, birth_hour,
              rizhu, rizhu_wuxing, wuxing_count_json, wuxing_missing_json,
              sizhu_data_json, mbti, gender, bio, contact_info, now, user_id))
    else:
        cursor.execute("""
            INSERT INTO user_profiles (
                user_id, birth_year, birth_month, birth_day, birth_hour,
                rizhu, rizhu_wuxing, wuxing_count, wuxing_missing,
                sizhu_data, mbti, gender, bio, contact_info,
                is_profile_complete, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (user_id, birth_year, birth_month, birth_day, birth_hour,
              rizhu, rizhu_wuxing, wuxing_count_json, wuxing_missing_json,
              sizhu_data_json, mbti, gender, bio, contact_info, now, now))
    
    conn.commit()
    conn.close()


def get_user_profile(user_id):
    """获取用户档案（含八字+MBTI）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None


def update_user_match_intro(user_id, bio, contact_info):
    """仅更新匹配展示用简介与联系方式（需已完善资料）"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute(
        """
        UPDATE user_profiles SET bio=?, contact_info=?, updated_at=?
        WHERE user_id=? AND is_profile_complete=1
        """,
        (bio, contact_info, now, user_id),
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_match_candidates(exclude_user_id, my_gender, shown_ids):
    """
    获取匹配候选池
    - 排除自己
    - 异性筛选
    - 排除已展示过的
    - 只返回完善了资料的用户
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 构建排除列表的占位符
    exclude_list = [exclude_user_id] + shown_ids
    placeholders = ','.join('?' * len(exclude_list))
    
    # 异性筛选：如果我是male，找female；如果我是female，找male
    target_gender = 'female' if my_gender == 'male' else 'male'
    
    query = f"""
        SELECT p.*, u.username
        FROM user_profiles p
        JOIN users u ON p.user_id = u.id
        WHERE p.user_id NOT IN ({placeholders})
        AND p.gender = ?
        AND p.allow_match = 1
        AND p.is_profile_complete = 1
        LIMIT 50
    """
    
    cursor.execute(query, exclude_list + [target_gender])
    rows = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return rows


def get_shown_user_ids(user_id):
    """获取已经展示过的用户ID列表"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT shown_user_id FROM match_history WHERE user_id = ?",
        (user_id,)
    )
    rows = cursor.fetchall()
    
    conn.close()
    return [row['shown_user_id'] for row in rows]


def add_match_history(user_id, shown_user_id, action='viewed'):
    """记录匹配历史"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT OR REPLACE INTO match_history (user_id, shown_user_id, shown_at, action)
        VALUES (?, ?, ?, ?)
    """, (user_id, shown_user_id, now, action))
    
    conn.commit()
    conn.close()


def reset_match_history(user_id):
    """重置用户的匹配历史（刷完后可重新开始）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM match_history WHERE user_id = ?", (user_id,))
    
    conn.commit()
    conn.close()


def get_match_history(user_id):
    """获取用户的匹配历史列表（已查看过的用户）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            mh.shown_user_id,
            mh.shown_at,
            mh.action,
            u.username,
            up.gender,
            up.mbti,
            up.rizhu,
            up.rizhu_wuxing,
            up.wuxing_count,
            up.wuxing_missing,
            up.bio,
            up.contact_info
        FROM match_history mh
        JOIN users u ON mh.shown_user_id = u.id
        LEFT JOIN user_profiles up ON mh.shown_user_id = up.user_id
        WHERE mh.user_id = ?
        ORDER BY mh.shown_at DESC
    """, (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


# ============================================================
#  匹配功能 - 留言板相关
# ============================================================

def save_match_message(from_user_id, to_user_id, content):
    """保存留言"""
    conn = get_connection()
    cursor = conn.cursor()
    
    msg_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO match_messages (id, from_user_id, to_user_id, content, is_read, created_at)
        VALUES (?, ?, ?, ?, 0, ?)
    """, (msg_id, from_user_id, to_user_id, content, now))
    
    conn.commit()
    conn.close()
    
    return {"id": msg_id, "created_at": now}


def get_messages_with_user(my_user_id, other_user_id):
    """获取与某个用户的所有留言（双向）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT m.*, u.username as from_username
        FROM match_messages m
        JOIN users u ON m.from_user_id = u.id
        WHERE (m.from_user_id = ? AND m.to_user_id = ?)
           OR (m.from_user_id = ? AND m.to_user_id = ?)
        ORDER BY m.created_at ASC
    """, (my_user_id, other_user_id, other_user_id, my_user_id))
    
    rows = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return rows


def get_message_threads(user_id):
    """
    获取该用户的所有留言对话线程
    返回：与该用户有过留言往来的所有其他用户列表
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT 
            CASE 
                WHEN from_user_id = ? THEN to_user_id
                ELSE from_user_id
            END as other_user_id
        FROM match_messages
        WHERE from_user_id = ? OR to_user_id = ?
    """, (user_id, user_id, user_id))
    
    # 过滤掉自己（防止自己发给自己的消息导致bug）
    other_user_ids = [row['other_user_id'] for row in cursor.fetchall() if row['other_user_id'] != user_id]
    
    # 获取每个对话的最后一条消息和未读数
    threads = []
    for other_id in other_user_ids:
        # 获取对方的基本信息
        cursor.execute("""
            SELECT u.id, u.username, p.rizhu, p.mbti
            FROM users u
            LEFT JOIN user_profiles p ON u.id = p.user_id
            WHERE u.id = ?
        """, (other_id,))
        user_row = cursor.fetchone()
        
        if not user_row:
            continue
        
        # 获取最后一条消息
        cursor.execute("""
            SELECT content, created_at, from_user_id
            FROM match_messages
            WHERE (from_user_id = ? AND to_user_id = ?)
               OR (from_user_id = ? AND to_user_id = ?)
            ORDER BY created_at DESC
            LIMIT 1
        """, (user_id, other_id, other_id, user_id))
        last_msg = cursor.fetchone()
        
        # 获取未读数
        cursor.execute("""
            SELECT COUNT(*) as unread_count
            FROM match_messages
            WHERE to_user_id = ? AND from_user_id = ? AND is_read = 0
        """, (user_id, other_id))
        unread_row = cursor.fetchone()
        
        threads.append({
            'user_id': user_row['id'],
            'username': user_row['username'],
            'rizhu': user_row['rizhu'] or '未知',
            'mbti': user_row['mbti'] or 'N/A',
            'last_message': dict(last_msg) if last_msg else None,
            'unread_count': unread_row['unread_count'] if unread_row else 0
        })
    
    conn.close()
    
    # 按最后消息时间排序
    threads.sort(key=lambda x: x['last_message']['created_at'] if x['last_message'] else '', reverse=True)
    
    return threads


def mark_messages_as_read(to_user_id, from_user_id):
    """将某个用户发来的所有消息标记为已读"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE match_messages
        SET is_read = 1
        WHERE to_user_id = ? AND from_user_id = ?
    """, (to_user_id, from_user_id))
    
    conn.commit()
    conn.close()


def get_unread_message_count(user_id):
    """获取未读留言总数"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM match_messages
        WHERE to_user_id = ? AND is_read = 0
    """, (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row['count'] if row else 0


# ============================================================
#  匹配报告缓存相关
# ============================================================

def get_cached_report(user_id, matched_user_id):
    """获取缓存的配对报告"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT report_content, match_score, match_type, created_at
        FROM match_reports
        WHERE user_id = ? AND matched_user_id = ?
    """, (user_id, matched_user_id))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def save_match_report(user_id, matched_user_id, report_content, match_score, match_type):
    """保存生成的配对报告"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT OR REPLACE INTO match_reports 
        (user_id, matched_user_id, report_content, match_score, match_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, matched_user_id, report_content, match_score, match_type, now))
    
    conn.commit()
    conn.close()


# 缘分匹配：免费次数与付费解锁（与 reset 无关，按账号累计）
MATCH_FREE_LIMIT = 3
MATCH_UNLOCK_PRICE_FEN = 99  # 0.99 元


def get_match_entitlement(user_id):
    """返回 { match_premium, match_free_used, free_limit, free_remaining }"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT match_premium, match_free_used FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    premium = int(row["match_premium"] or 0)
    used = int(row["match_free_used"] or 0)
    remaining = max(0, MATCH_FREE_LIMIT - used) if not premium else None
    return {
        "match_premium": premium,
        "match_free_used": used,
        "free_limit": MATCH_FREE_LIMIT,
        "free_remaining": remaining,
        "price_fen": MATCH_UNLOCK_PRICE_FEN,
    }


def increment_match_free_used(user_id):
    """成功展示一名新匹配对象后调用（未付费用户）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET match_free_used = COALESCE(match_free_used, 0) + 1 WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()


def create_wechat_pay_order(out_trade_no, user_id, amount_fen):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT INTO wechat_pay_orders (out_trade_no, user_id, amount_fen, status, created_at)
        VALUES (?, ?, ?, 'pending', ?)
        """,
        (out_trade_no, user_id, amount_fen, now),
    )
    conn.commit()
    conn.close()


def get_wechat_pay_order(out_trade_no):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wechat_pay_orders WHERE out_trade_no = ?", (out_trade_no,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def fulfill_match_payment(out_trade_no, transaction_id, expected_amount_fen):
    """
    支付成功回调：幂等更新订单并解锁 match_premium。
    返回 (success: bool, reason: str)
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    try:
        cursor.execute(
            "SELECT user_id, amount_fen, status FROM wechat_pay_orders WHERE out_trade_no = ?",
            (out_trade_no,),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "order_not_found"
        if row["status"] == "paid":
            conn.close()
            return True, "already_paid"
        if int(row["amount_fen"]) != int(expected_amount_fen):
            conn.close()
            return False, "amount_mismatch"
        cursor.execute(
            """
            UPDATE wechat_pay_orders
            SET status = 'paid', transaction_id = ?, paid_at = ?
            WHERE out_trade_no = ?
            """,
            (transaction_id, now, out_trade_no),
        )
        cursor.execute(
            "UPDATE users SET match_premium = 1 WHERE id = ?",
            (row["user_id"],),
        )
        conn.commit()
    finally:
        conn.close()
    return True, "ok"


def dev_mock_unlock_match(user_id):
    """仅开发：直接解锁，不经过微信"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET match_premium = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


# 检查 conversations 表是否有 user_id 列（兼容旧数据库）
def _check_and_migrate():
    """检查并迁移旧表结构"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(conversations)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'user_id' not in columns:
        cursor.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")

    cursor.execute("PRAGMA table_info(users)")
    user_cols = [col[1] for col in cursor.fetchall()]
    if "match_premium" not in user_cols:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN match_premium INTEGER NOT NULL DEFAULT 0"
        )
    if "match_free_used" not in user_cols:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN match_free_used INTEGER NOT NULL DEFAULT 0"
        )
    
    conn.commit()
    conn.close()


# 模块被导入时自动初始化数据库
init_db()
_check_and_migrate()
