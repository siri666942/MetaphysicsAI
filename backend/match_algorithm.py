"""
匹配算法模块 - 基于八字五行互补和MBTI心理契合的用户匹配算法
理论基础：
1. 八字合婚理论（五行互补、日主相生相合）
2. MBTI认知功能理论（理想配对、互补平衡）
"""

import json


# ============================================================
#  五行关系定义
# ============================================================

# 五行相生：金生水、水生木、木生火、火生土、土生金
WUXING_SHENG = {'金': '水', '水': '木', '木': '火', '火': '土', '土': '金'}

# 五行相克：金克木、木克土、土克水、水克火、火克金
WUXING_KE = {'金': '木', '木': '土', '土': '水', '水': '火', '火': '金'}

# 天干五合（甲己合土、乙庚合金、丙辛合水、丁壬合木、戊癸合火）
TIANGAN_HE = {
    '甲': '己', '己': '甲',
    '乙': '庚', '庚': '乙',
    '丙': '辛', '辛': '丙',
    '丁': '壬', '壬': '丁',
    '戊': '癸', '癸': '戊',
}


# ============================================================
#  MBTI理想配对映射（基于认知功能研究）
# ============================================================

MBTI_IDEAL_PAIRS = {
    'INTJ': ['ENFP', 'ENTP'],
    'INTP': ['ENFJ', 'ENTJ'],
    'ENTJ': ['INFP', 'INTP'],
    'ENTP': ['INFJ', 'INTJ'],
    'INFJ': ['ENFP', 'ENTP'],
    'INFP': ['ENFJ', 'ENTJ'],
    'ENFJ': ['INFP', 'INTP'],
    'ENFP': ['INFJ', 'INTJ'],
    'ISTJ': ['ESFP', 'ESTP'],
    'ISFJ': ['ESFP', 'ESTP'],
    'ESTJ': ['ISFP', 'ISTP'],
    'ESFJ': ['ISFP', 'ISTP'],
    'ISTP': ['ESFJ', 'ESTJ'],
    'ISFP': ['ESFJ', 'ESTJ'],
    'ESTP': ['ISFJ', 'ISTJ'],
    'ESFP': ['ISFJ', 'ISTJ'],
}


# ============================================================
#  子算法1: 五行互补匹配（权重60%，满分60分）
# ============================================================

def calculate_wuxing_score(profile_a, profile_b):
    """
    五行互补匹配算法
    评分规则：
    1. 缺失互补(40分)：我缺的你旺(>=2个) → 20分/次，双向最多40分
    2. 日主相生(15分)：金→水→木→火→土→金
    3. 日主相合(10分)：甲己合、乙庚合等天干五合
    4. 日主比和(8分)：同五行，惺惺相惜
    5. 日主相克(-8分)：金克木、木克土等（扣分）
    
    返回: (分数0-60, 匹配原因列表)
    """
    score = 0
    reasons = []
    
    # 解析JSON字段
    missing_a = json.loads(profile_a['wuxing_missing'])
    missing_b = json.loads(profile_b['wuxing_missing'])
    count_a = json.loads(profile_a['wuxing_count'])
    count_b = json.loads(profile_b['wuxing_count'])
    
    # 1. 缺失互补（双向检查，各20分）
    for wx in missing_a:
        if count_b[wx] >= 2:
            score += 20
            reasons.append(f"你缺{wx}，TA {wx}旺，天然互补")
    
    for wx in missing_b:
        if count_a[wx] >= 2:
            score += 20
            reasons.append(f"TA缺{wx}，你{wx}旺，相互成就")
    
    # 2. 日主五行关系
    wx_a = profile_a['rizhu_wuxing']
    wx_b = profile_b['rizhu_wuxing']
    
    if WUXING_SHENG.get(wx_a) == wx_b:
        score += 15
        reasons.append(f"你的{wx_a}生TA的{wx_b}，滋养有情")
    elif WUXING_SHENG.get(wx_b) == wx_a:
        score += 15
        reasons.append(f"TA的{wx_b}生你的{wx_a}，相扶相助")
    elif wx_a == wx_b:
        score += 8
        reasons.append(f"日主同属{wx_a}，比和之象")
    elif WUXING_KE.get(wx_a) == wx_b:
        score -= 8
        reasons.append(f"你的{wx_a}克TA的{wx_b}，需注意包容")
    elif WUXING_KE.get(wx_b) == wx_a:
        score -= 8
        reasons.append(f"TA的{wx_b}克你的{wx_a}，可能有压力")
    
    # 3. 日主天干相合（如有）
    rizhu_a = profile_a['rizhu'][:1]  # 取第一个字，如"甲木"→"甲"
    rizhu_b = profile_b['rizhu'][:1]
    
    if TIANGAN_HE.get(rizhu_a) == rizhu_b:
        score += 10
        reasons.append(f"日主{rizhu_a}{rizhu_b}相合，天作之合")
    
    return max(0, min(60, score)), reasons


# ============================================================
#  子算法2: MBTI心理契合（权重40%，满分40分）
# ============================================================

def calculate_mbti_score(mbti_a, mbti_b):
    """
    MBTI匹配算法
    评分规则：
    1. 理想配对(40分)：INFJ↔ENFP, INTJ↔ENTP 等经典组合
    2. 互补平衡(28-32分)：2-3个维度相反
    3. 高度相似(26分)：1个维度相反
    4. 完全相同(22分)：惺惺相惜
    5. 对立较大(15分)：4个维度全反
    
    返回: (分数0-40, 匹配原因)
    """
    # 理想配对 → 满分40
    if mbti_b in MBTI_IDEAL_PAIRS.get(mbti_a, []):
        return 40, f"MBTI理想配对({mbti_a}×{mbti_b})"
    
    # 计算4个维度的差异数 (E/I, S/N, T/F, J/P)
    diff_count = sum([mbti_a[i] != mbti_b[i] for i in range(4)])
    
    # 根据差异数评分
    score_map = {
        0: (22, "完全相同，惺惺相惜"),
        1: (26, "高度相似，默契十足"),
        2: (32, "互补平衡，相得益彰"),
        3: (28, "差异较大，需要磨合"),
        4: (15, "性格对立，挑战较多")
    }
    
    score, desc = score_map.get(diff_count, (20, "一般契合"))
    reason = f"{desc}({mbti_a}×{mbti_b})"
    
    return score, reason


# ============================================================
#  综合匹配算法（主函数）
# ============================================================

def calculate_match_score(profile_a, profile_b):
    """
    计算两个用户的综合匹配度
    
    参数:
        profile_a: 用户A的档案(dict)
        profile_b: 用户B的档案(dict)
    
    返回: {
        'total_score': 85.5,  # 总分0-100
        'breakdown': {
            'wuxing': 51,     # 五行互补得分
            'mbti': 34.5      # MBTI契合得分
        },
        'reasons': [...],     # 匹配原因列表
        'match_type': '水火既济型',  # 缘分类型标签
        'description': '...'  # 一句话诗意描述
    }
    """
    # 1. 五行互补得分（0-60分）
    wuxing_score, wuxing_reasons = calculate_wuxing_score(profile_a, profile_b)
    
    # 2. MBTI心理契合得分（0-40分）
    mbti_score, mbti_reason = calculate_mbti_score(
        profile_a['mbti'],
        profile_b['mbti']
    )
    
    # 3. 总分
    total_score = wuxing_score + mbti_score
    
    # 4. 合并原因
    all_reasons = wuxing_reasons + [mbti_reason]
    
    # 5. 确定缘分类型标签
    match_type = determine_match_type(profile_a, profile_b, wuxing_score, mbti_score)
    
    # 6. 生成诗意描述
    description = generate_match_description(profile_a, profile_b, match_type)
    
    return {
        'total_score': round(total_score, 1),
        'breakdown': {
            'wuxing': round(wuxing_score, 1),
            'mbti': round(mbti_score, 1),
        },
        'reasons': all_reasons,
        'match_type': match_type,
        'description': description,
    }


# ============================================================
#  缘分类型判定
# ============================================================

def determine_match_type(profile_a, profile_b, wuxing_score, mbti_score):
    """
    根据五行组合和总分判定缘分类型标签
    返回: 缘分类型字符串（带emoji）
    """
    wx_a = profile_a['rizhu_wuxing']
    wx_b = profile_b['rizhu_wuxing']
    total = wuxing_score + mbti_score
    
    # 五行组合特殊命名
    pair = tuple(sorted([wx_a, wx_b]))
    
    # 五行特色类型
    wuxing_types = {
        ('水', '火'): "🔥💧 水火既济型",
        ('木', '金'): "⚔️🌳 金木相交型",
        ('土', '木'): "🌳🏔️ 木土共生型",
        ('金', '水'): "💎💧 金水相涵型",
        ('火', '木'): "🔥🌳 木火通明型",
        ('火', '土'): "🔥🏔️ 火土生辉型",
        ('土', '金'): "💎🏔️ 土金相生型",
        ('水', '木'): "💧🌳 水木清华型",
        ('水', '土'): "💧🏔️ 水土相克型",
    }
    
    # 同五行类型
    if wx_a == wx_b:
        same_types = {
            '金': f"✨ 双金并立型",
            '木': f"🌳 双木成林型",
            '水': f"💧 双水汇流型",
            '火': f"🔥 双火相映型",
            '土': f"🏔️ 双土厚载型",
        }
        return same_types.get(wx_a, "✨ 同源共鸣型")
    
    # 五行组合类型
    if pair in wuxing_types:
        base_type = wuxing_types[pair]
        # 根据总分追加等级
        if total >= 80:
            return base_type.replace('型', '·天作之合')
        return base_type
    
    # 通用类型（按总分划分）
    if total >= 85:
        return "🌟 灵魂伴侣型"
    elif total >= 75:
        return "💫 天作之合型"
    elif total >= 65:
        return "🎭 互补共生型"
    elif total >= 50:
        return "🌱 缘分初现型"
    else:
        return "🍃 缘浅需惜型"


# ============================================================
#  诗意描述生成
# ============================================================

def generate_match_description(profile_a, profile_b, match_type):
    """
    根据五行组合生成一句话诗意描述
    """
    wx_a = profile_a['rizhu_wuxing']
    wx_b = profile_b['rizhu_wuxing']
    
    # 五行诗意描述库（基于《周易》哲学）
    descriptions = {
        ('水', '火'): "你的火照亮黑暗，TA的水滋润干涸。水火既济，阴阳调和。",
        ('火', '水'): "你的水平息燥热，TA的火温暖寒凉。相互成就，平衡有道。",
        ('木', '金'): "金虽克木，却能雕琢成器。需彼此理解，终成大器。",
        ('金', '木'): "你金质坚韧，TA木性灵动。刚柔并济，各展其长。",
        ('土', '木'): "木需土培，土需木疏。根深蒂固，共同成长。",
        ('木', '土'): "你木秀挺拔，TA土厚载物。相得益彰，生生不息。",
        ('金', '水'): "金生丽水，水养金华。相生有情，温润如玉。",
        ('水', '金'): "你水清灵动，TA金坚不移。相生相助，流水不腐。",
        ('木', '火'): "木助火势，火炼木材。薪火相传，光明炽烈。",
        ('火', '木'): "你火热激情，TA木蕴生机。木火通明，相得益彰。",
        ('火', '土'): "火生土暖，土载火安。相互依存，稳固温情。",
        ('土', '火'): "你土实稳重，TA火热真诚。火土相生，厚德载福。",
        ('土', '金'): "土生金矿，金固土基。厚积薄发，坚韧绵长。",
        ('金', '土'): "你金质纯粹，TA土性敦厚。相生相成，金石之盟。",
        ('水', '木'): "水润木秀，木疏水流。生生不息，灵动自在。",
        ('木', '水'): "你木向阳生，TA水润无声。水木清华，秀美天成。",
        ('水', '土'): "水土相交，需知进退。若能平衡，方得其所。",
        ('土', '水'): "你土厚稳重，TA水善变通。土克水险，需多理解。",
    }
    
    # 同五行描述
    same_descriptions = {
        '金': "双金并峙，坚韧果敢。惺惺相惜，志同道合。",
        '木': "双木成林，生机勃发。同气连枝，共同成长。",
        '水': "双水汇流，智慧深邃。心意相通，波澜不惊。",
        '火': "双火相映，热情洋溢。理想共鸣，光芒万丈。",
        '土': "双土厚载，踏实稳重。脚踏实地，相濡以沫。",
    }
    
    # 同五行
    if wx_a == wx_b:
        return same_descriptions.get(wx_a, "同属一源，心意相通。")
    
    # 不同五行
    pair = (wx_a, wx_b)
    if pair in descriptions:
        return descriptions[pair]
    
    # 默认文案
    return "命理相牵，缘分天定。相遇即是修行，珍惜当下人。"


# ============================================================
#  工具函数：解析八字结果文本
# ============================================================

def parse_bazi_text(bazi_text):
    """
    从 compute_bazi() 返回的文本中提取关键数据
    返回: {
        'rizhu': '甲木',
        'rizhu_wuxing': '木',
        'wuxing_count': {'金':1, '木':3, '水':2, '火':1, '土':1},
        'wuxing_missing': ['火'],
        'sizhu': {'year':'甲子', 'month':'丙寅', ...}
    }
    """
    import re
    
    result = {
        'rizhu': '',
        'rizhu_wuxing': '',
        'wuxing_count': {},
        'wuxing_missing': [],
        'sizhu': {}
    }
    
    # 提取日主
    match = re.search(r'日主：(\S)（(\S)）', bazi_text)
    if match:
        gan = match.group(1)
        wx = match.group(2)
        result['rizhu'] = f"{gan}{wx}"
        result['rizhu_wuxing'] = wx
    
    # 提取五行分布（如："五行分布：金1  木3  水2  火1  土1"）
    match = re.search(r'五行分布：(.+)', bazi_text)
    if match:
        wx_line = match.group(1)
        for wx in ['金', '木', '水', '火', '土']:
            count_match = re.search(rf'{wx}(\d+)', wx_line)
            if count_match:
                result['wuxing_count'][wx] = int(count_match.group(1))
            else:
                result['wuxing_count'][wx] = 0
    
    # 提取五行缺失
    match = re.search(r'五行缺失：(.+)', bazi_text)
    if match:
        missing_str = match.group(1).strip()
        if missing_str != '五行俱全':
            result['wuxing_missing'] = missing_str.replace('、', ',').split(',')
        else:
            result['wuxing_missing'] = []
    
    # 提取四柱
    year_match = re.search(r'年柱：(\S+)（', bazi_text)
    month_match = re.search(r'月柱：(\S+)（', bazi_text)
    day_match = re.search(r'日柱：(\S+)（', bazi_text)
    hour_match = re.search(r'时柱：(\S+)（', bazi_text)
    
    if year_match:
        result['sizhu']['year'] = year_match.group(1)
    if month_match:
        result['sizhu']['month'] = month_match.group(1)
    if day_match:
        result['sizhu']['day'] = day_match.group(1)
    if hour_match:
        result['sizhu']['hour'] = hour_match.group(1)
    
    return result
