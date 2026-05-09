# 缘分匹配功能使用说明

## 功能概述

基于**八字五行互补**和**MBTI心理契合**的用户匹配系统，帮助用户找到命中人。

## 核心算法

### 匹配维度（总分100分）

1. **八字五行互补（60分）**
   - 缺失互补：我缺的你旺 → 20分/次，双向最多40分
   - 日主相生：金→水→木→火→土 → 15分
   - 日主相合：天干五合（甲己、乙庚等） → 10分
   - 日主比和：同五行 → 8分
   - 日主相克：相克关系 → -8分（扣分）

2. **MBTI心理契合（40分）**
   - 理想配对：INFJ×ENFP、INTJ×ENTP等 → 40分
   - 互补平衡：2-3个维度相反 → 28-32分
   - 高度相似：1个维度相反 → 26分
   - 完全相同：惺惺相惜 → 22分
   - 对立较大：4个维度全反 → 15分

## 使用流程

### 1. 用户完善资料

用户首次点击"缘分匹配"时，需要填写：

- **生辰信息**：年月日时（公历）
- **MBTI类型**：16种人格类型选一
- **性别**：用于异性筛选
- **个人简介**：可选，30字内
- **联系方式**：可选（微信/QQ号）

系统会自动计算八字，提取日主、五行分布、五行缺失等数据。

### 2. 探探式匹配

- **单次推荐**：每次显示1个最合适的匹配对象
- **异性筛选**：只推荐异性用户
- **去重机制**：不会重复推荐已展示过的用户
- **重置功能**：刷完后可以重新开始

### 3. 留言互动

- **异步留言板**：类似QQ消息，不需要在线
- **查看历史**：可以查看与每个人的完整对话
- **未读提醒**：消息tab显示未读数红点

### 4. AI详细报告

- **按需生成**：用户点击"查看报告"时才调用AI生成
- **专属分析**：800字左右的Markdown格式报告
- **内容包含**：
  - 五行互补分析
  - MBTI契合度
  - 相处建议
  - 需注意事项
  - 易经典籍引用

## 数据库表结构

### user_profiles（用户档案表）

```sql
CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    birth_year INTEGER,
    birth_month INTEGER,
    birth_day INTEGER,
    birth_hour INTEGER,
    rizhu TEXT,              -- 日主（如"甲木"）
    rizhu_wuxing TEXT,       -- 日主五行（如"木"）
    wuxing_count TEXT,       -- 五行分布JSON（如{"金":1,"木":3,...}）
    wuxing_missing TEXT,     -- 五行缺失JSON（如["火"]）
    sizhu_data TEXT,         -- 完整四柱JSON
    mbti TEXT,               -- MBTI类型（如"INFJ"）
    gender TEXT,             -- 性别（male/female）
    bio TEXT,                -- 个人简介
    contact_info TEXT,       -- 联系方式
    allow_match BOOLEAN DEFAULT 1,
    is_profile_complete BOOLEAN DEFAULT 0,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### match_history（匹配历史表）

```sql
CREATE TABLE match_history (
    user_id TEXT,            -- 当前用户
    shown_user_id TEXT,      -- 被展示的用户
    shown_at TEXT,           -- 展示时间
    action TEXT,             -- 操作类型（viewed/messaged）
    PRIMARY KEY (user_id, shown_user_id)
);
```

### match_messages（留言表）

```sql
CREATE TABLE match_messages (
    id TEXT PRIMARY KEY,
    from_user_id TEXT,
    to_user_id TEXT,
    content TEXT,
    is_read BOOLEAN DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY (from_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (to_user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

## API端点

### 用户资料

- `GET /api/user/profile` - 获取当前用户档案
- `POST /api/user/profile` - 完善用户资料

### 匹配功能

- `GET /api/match/next` - 获取下一个匹配对象
- `POST /api/match/reset` - 重置匹配历史

### 留言功能

- `POST /api/match/message` - 发送留言
- `GET /api/match/messages/threads` - 获取所有留言线程
- `GET /api/match/messages/<user_id>` - 获取与某人的所有留言
- `GET /api/match/messages/unread-count` - 获取未读留言数

### AI报告

- `GET /api/match/report/<user_id>` - 生成AI配对报告

## 文件结构

```
backend/
├── app.py                 # Flask主应用（已添加匹配API路由）
├── database.py            # 数据库操作（已添加匹配相关表和函数）
├── match_algorithm.py     # 匹配算法模块（新增）
└── ...

frontend/
├── index.html            # 主页面（已添加匹配页面和弹窗）
├── script.js             # 主应用逻辑（已添加user_id存储）
├── match.js              # 匹配功能逻辑（新增）
└── style.css             # 样式表（已添加匹配相关样式）
```

## 使用注意事项

1. **成本控制**：AI报告仅在用户主动点击时生成，避免批量调用
2. **性能优化**：
   - 候选池限制50人，避免全量计算
   - 去重机制减少重复计算
   - 可添加Redis缓存进一步优化
3. **用户体验**：
   - 单次推荐，降低选择疲劳
   - 异步留言，无需双方在线
   - 提供联系方式展示，方便线下联系

## 启动方式

### 开发环境

```bash
# 安装依赖（如未安装）
pip install -r requirements.txt

# 启动后端（端口5000）
cd backend
python app.py

# 启动前端（端口3000）
cd frontend
python -m http.server 3000
```

### Docker部署

```bash
docker-compose up -d
```

访问 http://localhost:3000 即可使用。

## 功能演示流程

1. 登录/注册账号
2. 点击侧边栏"匹配"tab
3. 点击"开始匹配"，填写资料
4. 系统自动推荐最合适的匹配对象
5. 查看匹配度、原因、AI报告
6. 给TA留言或换下一个
7. 在"消息"tab查看所有留言对话

## 未来优化方向

- 添加Redis缓存匹配分数
- 预计算热门用户的匹配数据
- 增加更多筛选维度（年龄、地区等）
- 添加"超级喜欢"功能（双向喜欢才能看联系方式）
- 增加匹配成功率统计
