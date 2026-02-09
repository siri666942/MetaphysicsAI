"""
占卜计算模块 —— 提供时间上下文、八字排盘、梅花易数、六爻排卦功能
使用 lunar_python 库进行农历/干支/节气计算
"""

from datetime import datetime

try:
    from lunar_python import Solar, Lunar
    HAS_LUNAR = True
except ImportError:
    HAS_LUNAR = False


# ============================================================
#  基础数据
# ============================================================

# 先天八卦数序（梅花易数用）
# lines: (初爻, 中爻, 上爻) —— 从下到上，1=阳，0=阴
BAGUA = {
    1: {'name': '乾', 'nature': '天', 'wuxing': '金', 'symbol': '☰', 'lines': (1, 1, 1)},
    2: {'name': '兑', 'nature': '泽', 'wuxing': '金', 'symbol': '☱', 'lines': (1, 1, 0)},
    3: {'name': '离', 'nature': '火', 'wuxing': '火', 'symbol': '☲', 'lines': (1, 0, 1)},
    4: {'name': '震', 'nature': '雷', 'wuxing': '木', 'symbol': '☳', 'lines': (1, 0, 0)},
    5: {'name': '巽', 'nature': '风', 'wuxing': '木', 'symbol': '☴', 'lines': (0, 1, 1)},
    6: {'name': '坎', 'nature': '水', 'wuxing': '水', 'symbol': '☵', 'lines': (0, 1, 0)},
    7: {'name': '艮', 'nature': '山', 'wuxing': '土', 'symbol': '☶', 'lines': (0, 0, 1)},
    8: {'name': '坤', 'nature': '地', 'wuxing': '土', 'symbol': '☷', 'lines': (0, 0, 0)},
}

# 六十四卦名 —— (上卦数, 下卦数) → 卦名
HEXAGRAM_NAMES = {
    (1, 1): '乾为天',   (1, 2): '天泽履',   (1, 3): '天火同人', (1, 4): '天雷无妄',
    (1, 5): '天风姤',   (1, 6): '天水讼',   (1, 7): '天山遁',   (1, 8): '天地否',
    (2, 1): '泽天夬',   (2, 2): '兑为泽',   (2, 3): '泽火革',   (2, 4): '泽雷随',
    (2, 5): '泽风大过', (2, 6): '泽水困',   (2, 7): '泽山咸',   (2, 8): '泽地萃',
    (3, 1): '火天大有', (3, 2): '火泽睽',   (3, 3): '离为火',   (3, 4): '火雷噬嗑',
    (3, 5): '火风鼎',   (3, 6): '火水未济', (3, 7): '火山旅',   (3, 8): '火地晋',
    (4, 1): '雷天大壮', (4, 2): '雷泽归妹', (4, 3): '雷火丰',   (4, 4): '震为雷',
    (4, 5): '雷风恒',   (4, 6): '雷水解',   (4, 7): '雷山小过', (4, 8): '雷地豫',
    (5, 1): '风天小畜', (5, 2): '风泽中孚', (5, 3): '风火家人', (5, 4): '风雷益',
    (5, 5): '巽为风',   (5, 6): '风水涣',   (5, 7): '风山渐',   (5, 8): '风地观',
    (6, 1): '水天需',   (6, 2): '水泽节',   (6, 3): '水火既济', (6, 4): '水雷屯',
    (6, 5): '水风井',   (6, 6): '坎为水',   (6, 7): '水山蹇',   (6, 8): '水地比',
    (7, 1): '山天大畜', (7, 2): '山泽损',   (7, 3): '山火贲',   (7, 4): '山雷颐',
    (7, 5): '山风蛊',   (7, 6): '山水蒙',   (7, 7): '艮为山',   (7, 8): '山地剥',
    (8, 1): '地天泰',   (8, 2): '地泽临',   (8, 3): '地火明夷', (8, 4): '地雷复',
    (8, 5): '地风升',   (8, 6): '地水师',   (8, 7): '地山谦',   (8, 8): '坤为地',
}

# 五行生克
WUXING_SHENG = {'金': '水', '水': '木', '木': '火', '火': '土', '土': '金'}
WUXING_KE = {'金': '木', '木': '土', '土': '水', '水': '火', '火': '金'}

# 天干五行
TIANGAN_WUXING = {
    '甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土',
    '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水',
}

# 地支五行
DIZHI_WUXING = {
    '子': '水', '丑': '土', '寅': '木', '卯': '木', '辰': '土', '巳': '火',
    '午': '火', '未': '土', '申': '金', '酉': '金', '戌': '土', '亥': '水',
}

WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']


# ============================================================
#  时间上下文（注入到系统提示词）
# ============================================================

def get_time_context():
    """获取当前时间的完整上下文信息，用于注入系统提示词"""
    now = datetime.now()

    if not HAS_LUNAR:
        return (
            f"【当前时间】\n"
            f"公历：{now.year}年{now.month}月{now.day}日 "
            f"星期{WEEKDAYS[now.weekday()]} {now.hour}:{now.minute:02d}\n"
            f"（注：lunar_python 库未安装，农历/节气信息暂不可用）"
        )

    try:
        solar = Solar.fromYmdHms(now.year, now.month, now.day,
                                 now.hour, now.minute, now.second)
        lunar = solar.getLunar()
        eight = lunar.getEightChar()

        lines = [
            "【当前时间信息 —— 所有时间相关推算请基于此数据】",
            f"公历：{now.year}年{now.month}月{now.day}日 "
            f"星期{WEEKDAYS[now.weekday()]} {now.hour}:{now.minute:02d}",
            f"农历：{lunar.getYearInGanZhi()}年（{lunar.getYearShengXiao()}年）"
            f"{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}",
            f"四柱（当前时刻）：{eight.getYear()} {eight.getMonth()} "
            f"{eight.getDay()} {eight.getTime()}",
            f"纳音：{eight.getYearNaYin()} {eight.getMonthNaYin()} "
            f"{eight.getDayNaYin()} {eight.getTimeNaYin()}",
        ]

        # 节气
        try:
            jie_qi = lunar.getCurrentJieQi()
            if jie_qi:
                lines.append(f"当前节气：{jie_qi.getName()}")
            next_jie = lunar.getNextJie()
            next_qi = lunar.getNextQi()
            if next_jie:
                lines.append(f"下一节：{next_jie.getName()}")
            if next_qi:
                lines.append(f"下一气：{next_qi.getName()}")
        except Exception:
            pass

        # 宜忌
        try:
            yi_list = lunar.getDayYi()
            ji_list = lunar.getDayJi()
            if yi_list:
                lines.append(f"今日宜：{'、'.join(yi_list[:10])}")
            if ji_list:
                lines.append(f"今日忌：{'、'.join(ji_list[:10])}")
        except Exception:
            pass

        return '\n'.join(lines)

    except Exception as e:
        return (
            f"【当前时间】\n"
            f"公历：{now.year}年{now.month}月{now.day}日 "
            f"星期{WEEKDAYS[now.weekday()]} {now.hour}:{now.minute:02d}\n"
            f"（详细农历信息获取异常: {e}）"
        )


# ============================================================
#  八字排盘
# ============================================================

def compute_bazi(year, month, day, hour, minute=0,
                 is_male=True, is_solar=True):
    """
    计算八字排盘，返回格式化文本供大模型解读
    :param is_solar: True=输入的是公历，False=输入的是农历
    """
    if not HAS_LUNAR:
        return "八字排盘功能需要安装 lunar_python 库"

    try:
        if is_solar:
            solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
            lunar = solar.getLunar()
        else:
            # 农历 → 取 Lunar 对象再转 Solar
            lunar = Lunar.fromYmdHms(year, month, day, hour, minute, 0)
            solar = lunar.getSolar()

        eight = lunar.getEightChar()
        gender = "男命" if is_male else "女命"

        # 日主天干
        day_gan = eight.getDay()[0]
        day_wx = TIANGAN_WUXING.get(day_gan, '?')

        # 五行统计
        all_chars = (eight.getYear() + eight.getMonth()
                     + eight.getDay() + eight.getTime())
        wx_count = {'金': 0, '木': 0, '水': 0, '火': 0, '土': 0}
        for ch in all_chars:
            if ch in TIANGAN_WUXING:
                wx_count[TIANGAN_WUXING[ch]] += 1
            elif ch in DIZHI_WUXING:
                wx_count[DIZHI_WUXING[ch]] += 1
        wx_str = '  '.join([f"{k}{v}" for k, v in wx_count.items()])
        missing = [k for k, v in wx_count.items() if v == 0]
        missing_str = '、'.join(missing) if missing else '五行俱全'

        result = f"""【八字排盘结果】
{gender}
出生公历：{solar.getYear()}年{solar.getMonth()}月{solar.getDay()}日 {hour}时{minute}分
出生农历：{lunar.getYearInGanZhi()}年 {lunar.getMonthInChinese()}月{lunar.getDayInChinese()} {lunar.getYearShengXiao()}年

四柱八字：
  年柱：{eight.getYear()}（{eight.getYearNaYin()}）
  月柱：{eight.getMonth()}（{eight.getMonthNaYin()}）
  日柱：{eight.getDay()}（{eight.getDayNaYin()}）
  时柱：{eight.getTime()}（{eight.getTimeNaYin()}）

日主：{day_gan}（{day_wx}）
五行分布：{wx_str}
五行缺失：{missing_str}

请根据以上排盘数据，为问卜者做详细的八字命理分析，包括但不限于：
性格特质、事业财运、感情婚姻、健康运势，并给出趋吉避凶建议。"""

        return result

    except Exception as e:
        return f"八字排盘出错：{str(e)}"


# ============================================================
#  内部工具函数
# ============================================================

def _flip_trigram_yao(gua_num, yao_pos):
    """翻转三画卦中指定爻位（1=初爻, 2=中爻, 3=上爻），返回新卦数"""
    lines = list(BAGUA[gua_num]['lines'])
    lines[yao_pos - 1] = 1 - lines[yao_pos - 1]
    target = tuple(lines)
    for num, data in BAGUA.items():
        if data['lines'] == target:
            return num
    return gua_num  # fallback


def _lines_to_gua(lines_tuple):
    """将三爻线型 (初,中,上) 转换为八卦数（1-8），找不到返回 None"""
    for num, data in BAGUA.items():
        if data['lines'] == lines_tuple:
            return num
    return None


def _analyze_ti_yong(ti_wx, yong_wx):
    """分析梅花易数中体用五行生克关系"""
    if ti_wx == yong_wx:
        return '比和', '体用五行相同，比和之象，事可顺遂'
    if WUXING_SHENG.get(yong_wx) == ti_wx:
        return '用生体', '用卦生助体卦，大吉，主有贵人相助、收获丰厚'
    if WUXING_SHENG.get(ti_wx) == yong_wx:
        return '体生用', '体卦生出用卦，泄气之象，主付出多、消耗心力'
    if WUXING_KE.get(ti_wx) == yong_wx:
        return '体克用', '体卦克制用卦，小吉，事可成但需费些周折'
    if WUXING_KE.get(yong_wx) == ti_wx:
        return '用克体', '用卦克制体卦，不利，主阻碍、压力较大'
    return '待定', '需进一步分析'


def _draw_hexagram(all_lines, dong_yao):
    """
    绘制六爻卦象文本图
    all_lines: 长度为 6 的列表，从初爻到上爻 (下→上)
    """
    yao_names = ['初', '二', '三', '四', '五', '上']
    result = []
    # 从上往下画（第6爻在最上面）
    for i in range(5, -1, -1):
        yao_num = i + 1
        is_yang = all_lines[i] == 1
        is_dong = yao_num == dong_yao

        line_str = "━━━━━━━━━" if is_yang else "━━━━ ━━━━"
        mark = " ◀ 动" if is_dong else ""
        result.append(f"  {yao_names[i]}爻  {line_str}{mark}")

    return '\n'.join(result)


# ============================================================
#  梅花易数
# ============================================================

def compute_meihua(num1, num2, num3):
    """
    梅花易数 · 数字起卦
    num1 → 上卦, num2 → 下卦, (num1+num2+num3) → 动爻
    返回格式化排盘文本
    """
    upper = num1 % 8 or 8
    lower = num2 % 8 or 8
    dong_yao = (num1 + num2 + num3) % 6 or 6

    return _format_meihua(upper, lower, dong_yao,
                          method=f"数字起卦（{num1}、{num2}、{num3}）")


def compute_meihua_by_time():
    """梅花易数 · 时间起卦（用当前农历时间）"""
    now = datetime.now()

    if HAS_LUNAR:
        try:
            solar = Solar.fromYmdHms(now.year, now.month, now.day,
                                     now.hour, now.minute, now.second)
            lunar = solar.getLunar()
            year_zhi = lunar.getYearZhiIndex() + 1   # 地支序号 1-12
            month_num = abs(lunar.getMonth())         # 农历月（1-12）
            day_num = lunar.getDay()                  # 农历日
            # 时辰序号: 子(1) 丑(2)...亥(12)
            hour_zhi = (now.hour + 1) // 2 % 12 or 12
        except Exception:
            year_zhi = now.year % 12 or 12
            month_num = now.month
            day_num = now.day
            hour_zhi = (now.hour + 1) // 2 % 12 or 12
    else:
        year_zhi = now.year % 12 or 12
        month_num = now.month
        day_num = now.day
        hour_zhi = (now.hour + 1) // 2 % 12 or 12

    upper = (year_zhi + month_num + day_num) % 8 or 8
    lower = (year_zhi + month_num + day_num + hour_zhi) % 8 or 8
    dong_yao = (year_zhi + month_num + day_num + hour_zhi) % 6 or 6

    return _format_meihua(upper, lower, dong_yao, method="时间起卦")


def _format_meihua(upper, lower, dong_yao, method=""):
    """格式化梅花易数排盘结果"""
    upper_info = BAGUA[upper]
    lower_info = BAGUA[lower]
    ben_name = HEXAGRAM_NAMES.get((upper, lower), '未知卦')

    # 变卦
    if dong_yao <= 3:
        new_lower = _flip_trigram_yao(lower, dong_yao)
        bian_upper, bian_lower = upper, new_lower
        ti_num, yong_num = upper, lower
    else:
        new_upper = _flip_trigram_yao(upper, dong_yao - 3)
        bian_upper, bian_lower = new_upper, lower
        ti_num, yong_num = lower, upper

    bian_name = HEXAGRAM_NAMES.get((bian_upper, bian_lower), '未知卦')
    bian_upper_info = BAGUA[bian_upper]
    bian_lower_info = BAGUA[bian_lower]

    # 互卦
    all_lines = list(lower_info['lines']) + list(upper_info['lines'])
    hu_lower = _lines_to_gua(tuple(all_lines[1:4]))
    hu_upper = _lines_to_gua(tuple(all_lines[2:5]))
    hu_name = '未知'
    if hu_upper and hu_lower:
        hu_name = HEXAGRAM_NAMES.get((hu_upper, hu_lower), '未知卦')

    # 体用分析
    ti_info = BAGUA[ti_num]
    yong_info = BAGUA[yong_num]
    relation, analysis = _analyze_ti_yong(ti_info['wuxing'], yong_info['wuxing'])

    dong_pos = '下卦' if dong_yao <= 3 else '上卦'

    return f"""【梅花易数排盘】
起卦方式：{method}
━━━━━━━━━━━━━━━━━━━━

本 卦：{ben_name}
  上卦：{upper_info['symbol']} {upper_info['name']}（{upper_info['nature']}·{upper_info['wuxing']}）
  下卦：{lower_info['symbol']} {lower_info['name']}（{lower_info['nature']}·{lower_info['wuxing']}）

动 爻：第{dong_yao}爻（位于{dong_pos}）

变 卦：{bian_name}
  上卦：{bian_upper_info['symbol']} {bian_upper_info['name']}（{bian_upper_info['nature']}·{bian_upper_info['wuxing']}）
  下卦：{bian_lower_info['symbol']} {bian_lower_info['name']}（{bian_lower_info['nature']}·{bian_lower_info['wuxing']}）

互 卦：{hu_name}

体用分析：
  体卦：{ti_info['symbol']} {ti_info['name']}（{ti_info['wuxing']}）
  用卦：{yong_info['symbol']} {yong_info['name']}（{yong_info['wuxing']}）
  关系：{relation} —— {analysis}

请根据以上排盘，结合问卜者的具体问题，进行详细的梅花易数解读，包括：
卦象含义、体用生克分析、互卦参考、变卦趋势、综合判断与建议。"""


# ============================================================
#  六爻排卦（数字起卦·简化版）
# ============================================================

def compute_liuyao(num1, num2, num3):
    """
    六爻 · 数字起卦
    确定本卦、变卦、动爻，提供给大模型用纳甲法解读
    """
    upper = num1 % 8 or 8
    lower = num2 % 8 or 8
    dong_yao = (num1 + num2 + num3) % 6 or 6

    return _format_liuyao(upper, lower, dong_yao,
                          method=f"数字起卦（{num1}、{num2}、{num3}）")


def compute_liuyao_by_time():
    """六爻 · 时间起卦"""
    now = datetime.now()

    if HAS_LUNAR:
        try:
            solar = Solar.fromYmdHms(now.year, now.month, now.day,
                                     now.hour, now.minute, now.second)
            lunar = solar.getLunar()
            year_zhi = lunar.getYearZhiIndex() + 1
            month_num = abs(lunar.getMonth())
            day_num = lunar.getDay()
            hour_zhi = (now.hour + 1) // 2 % 12 or 12
        except Exception:
            year_zhi = now.year % 12 or 12
            month_num = now.month
            day_num = now.day
            hour_zhi = (now.hour + 1) // 2 % 12 or 12
    else:
        year_zhi = now.year % 12 or 12
        month_num = now.month
        day_num = now.day
        hour_zhi = (now.hour + 1) // 2 % 12 or 12

    upper = (year_zhi + month_num + day_num) % 8 or 8
    lower = (year_zhi + month_num + day_num + hour_zhi) % 8 or 8
    dong_yao = (year_zhi + month_num + day_num + hour_zhi) % 6 or 6

    return _format_liuyao(upper, lower, dong_yao, method="时间起卦")


def _format_liuyao(upper, lower, dong_yao, method=""):
    """格式化六爻排卦结果"""
    upper_info = BAGUA[upper]
    lower_info = BAGUA[lower]
    ben_name = HEXAGRAM_NAMES.get((upper, lower), '未知卦')

    # 变卦
    if dong_yao <= 3:
        new_lower = _flip_trigram_yao(lower, dong_yao)
        bian_upper, bian_lower = upper, new_lower
    else:
        new_upper = _flip_trigram_yao(upper, dong_yao - 3)
        bian_upper, bian_lower = new_upper, lower

    bian_name = HEXAGRAM_NAMES.get((bian_upper, bian_lower), '未知卦')

    # 画卦象
    all_lines = list(lower_info['lines']) + list(upper_info['lines'])
    gua_drawing = _draw_hexagram(all_lines, dong_yao)

    return f"""【六爻排卦】
起卦方式：{method}
━━━━━━━━━━━━━━━━━━━━

本 卦：{ben_name}
  上卦：{upper_info['symbol']} {upper_info['name']}（{upper_info['nature']}·{upper_info['wuxing']}）
  下卦：{lower_info['symbol']} {lower_info['name']}（{lower_info['nature']}·{lower_info['wuxing']}）

动 爻：第{dong_yao}爻

变 卦：{bian_name}

卦象（从上到下）：
{gua_drawing}

请用六爻纳甲法进行详细解读，包括但不限于：
1. 确定本卦所属宫位
2. 装纳甲（每爻天干地支）
3. 定世应（世爻、应爻位置）
4. 配六亲（父母、兄弟、子孙、妻财、官鬼）
5. 配六兽（青龙、朱雀、勾陈、螣蛇、白虎、玄武）
6. 分析动爻变化、五行生克，结合问卜者的问题给出断卦结论与建议。"""
