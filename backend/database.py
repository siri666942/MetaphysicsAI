"""
SQLite 数据库模块 —— 管理对话和消息的持久化存储
"""

import sqlite3
import os
import uuid
from datetime import datetime

# 注意：Python 中用 os.path.join 拼接路径，不像 Java 用 File 对象
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history.db")


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    # 让查询结果可以通过列名访问，类似 Java 的 ResultSet
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_connection()
    cursor = conn.cursor()

    # 对话表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL DEFAULT '新对话',
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

    conn.commit()
    conn.close()


def create_conversation():
    """创建新对话，返回对话信息"""
    conn = get_connection()
    cursor = conn.cursor()

    conv_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO conversations (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (conv_id, "新对话", now, now),
    )

    conn.commit()
    conn.close()

    return {"id": conv_id, "title": "新对话", "created_at": now, "updated_at": now}


def get_all_conversations():
    """获取所有对话列表，按更新时间倒序"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM conversations ORDER BY updated_at DESC")
    # Python 的 dict() 可以直接转换 sqlite3.Row，不需要像 Java 那样手动映射
    rows = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return rows


def get_conversation_messages(conversation_id: str):
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


def add_message(conversation_id: str, role: str, content: str):
    """向对话中添加一条消息"""
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
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


def update_conversation_title(conversation_id: str, title: str):
    """更新对话标题"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE conversations SET title = ? WHERE id = ?",
        (title, conversation_id),
    )

    conn.commit()
    conn.close()


def delete_conversation(conversation_id: str):
    """删除对话及其所有消息"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    conn.commit()
    conn.close()


# 模块被导入时自动初始化数据库
init_db()
