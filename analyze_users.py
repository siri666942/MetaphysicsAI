#!/usr/bin/env python3
"""
用户聊天数据分析脚本
分析用户聊天轮次分布
"""
import sqlite3
from collections import defaultdict

# 用户消息轮次区间：0 单独；其余等宽分桶，便于对比
ROUND_BUCKET_WIDTH = 5


def equal_round_buckets(max_rounds: int, width: int = ROUND_BUCKET_WIDTH):
    """生成等距区间标签，覆盖 0..max_rounds。"""
    ranges: list[tuple[int, int, str]] = [(0, 0, "0轮（未聊天）")]
    if max_rounds < 1:
        return ranges
    lo = 1
    while lo <= max_rounds:
        hi = min(lo + width - 1, max_rounds)
        label = f"{lo}-{hi}轮" if hi > lo else f"{lo}轮"
        ranges.append((lo, hi, label))
        lo = hi + 1
    return ranges


def analyze_chat_data():
    # 连接数据库
    conn = sqlite3.connect('/root/sites/beingecho.tech/data/chat_history.db')
    cursor = conn.cursor()
    
    # 查看表结构
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("=== 数据库表结构 ===")
    for table in tables:
        print(table[0])
        print()
    
    # 获取所有消息
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [row[0] for row in cursor.fetchall()]
    print(f"数据库中的表: {table_names}\n")
    
    # 尝试查询消息表
    if 'messages' in table_names:
        # 按用户分组统计消息数（通过conversations表关联）
        cursor.execute("""
            SELECT c.user_id, m.role, COUNT(*) as count
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.user_id IS NOT NULL
            GROUP BY c.user_id, m.role
            ORDER BY c.user_id, m.role
        """)
        
        user_messages = defaultdict(lambda: {'user': 0, 'assistant': 0})
        
        for row in cursor.fetchall():
            user_id, role, count = row
            if role in ['user', 'assistant']:
                user_messages[user_id][role] = count
        
        # 添加注册但未聊天的用户
        cursor.execute("SELECT id FROM users")
        all_users = {row[0] for row in cursor.fetchall()}
        for user_id in all_users:
            if user_id not in user_messages:
                user_messages[user_id] = {'user': 0, 'assistant': 0}
        
        print(f"=== 用户总数: {len(user_messages)} ===\n")
        
        # 分析聊天轮次分布
        # 用户发送的消息数代表聊天轮次
        rounds_distribution = defaultdict(int)
        zero_chat_users = 0
        
        for user_id, messages in user_messages.items():
            user_rounds = messages['user']
            if user_rounds == 0:
                zero_chat_users += 1
            rounds_distribution[user_rounds] += 1
        
        print(f"=== 聊天轮次分布 ===")
        print(f"只注册未聊天（0轮）: {zero_chat_users} 人")
        print()
        
        print("聊天轮次统计:")
        for rounds in sorted(rounds_distribution.keys()):
            count = rounds_distribution[rounds]
            percentage = (count / len(user_messages)) * 100
            bar = '█' * int(percentage / 2)
            print(f"{rounds:4d} 轮: {count:4d} 人 ({percentage:5.2f}%) {bar}")
        
        print()
        
        max_rounds_observed = max(rounds_distribution.keys()) if rounds_distribution else 0
        ranges = equal_round_buckets(max_rounds_observed, ROUND_BUCKET_WIDTH)

        print(f"=== 聊天轮次区间分布（等宽，每档 {ROUND_BUCKET_WIDTH} 轮）===")
        for min_rounds, max_rounds, label in ranges:
            count = sum(
                rounds_distribution[r]
                for r in rounds_distribution.keys()
                if min_rounds <= r <= max_rounds
            )
            percentage = (count / len(user_messages)) * 100 if user_messages else 0
            bar = "█" * int(percentage / 2)
            print(f"{label:18s}: {count:4d} 人 ({percentage:5.2f}%) {bar}")
        
        print()
        
        # 基本统计
        total_user_messages = sum(m['user'] for m in user_messages.values())
        total_assistant_messages = sum(m['assistant'] for m in user_messages.values())
        avg_rounds = total_user_messages / len(user_messages) if user_messages else 0
        
        print("=== 整体统计 ===")
        print(f"总用户数: {len(user_messages)}")
        print(f"用户总消息数: {total_user_messages}")
        print(f"助手总回复数: {total_assistant_messages}")
        print(f"平均每用户聊天轮次: {avg_rounds:.2f}")
        print(f"活跃用户数（至少1轮）: {len(user_messages) - zero_chat_users}")
        print(f"活跃率: {((len(user_messages) - zero_chat_users) / len(user_messages) * 100):.2f}%")
        
        # 显示前10个最活跃的用户
        print("\n=== 前10活跃用户 ===")
        sorted_users = sorted(user_messages.items(), 
                            key=lambda x: x[1]['user'], 
                            reverse=True)[:10]
        for i, (user_id, messages) in enumerate(sorted_users, 1):
            print(f"{i:2d}. 用户 {user_id[:8]}... : {messages['user']} 轮")
    
    else:
        print("未找到 messages 表")
    
    conn.close()

if __name__ == '__main__':
    analyze_chat_data()
