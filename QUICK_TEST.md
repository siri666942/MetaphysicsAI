# 缘分匹配功能快速测试指南

## 测试前准备

### 1. 确保依赖已安装

如果在本地测试（非Docker），需要先安装Python依赖：

```bash
# 方式1：使用虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 方式2：系统级安装（需加参数）
pip install -r requirements.txt --break-system-packages
```

### 2. 配置环境变量

确认`.env`文件存在且配置正确：

```
OPENAI_API_KEY=你的API密钥
OPENAI_API_BASE=https://api.sophnet.link/v1
```

---

## 启动服务

### 本地开发

```bash
# 终端1：启动后端
cd backend
python app.py
# 预期输出：🔮 AI+玄学 后端服务启动中...

# 终端2：启动前端
cd frontend
python -m http.server 3000
# 访问 http://localhost:3000
```

### Docker部署

```bash
docker-compose up -d
# 访问 http://localhost:3000
```

---

## 功能测试流程

### 第一步：创建测试账号

1. 打开浏览器访问 http://localhost:3000
2. 点击"立即注册"
3. 创建两个测试账号：
   - 账号A：`test_user_a` / `123456`
   - 账号B：`test_user_b` / `123456`

### 第二步：完善用户A的资料

1. 使用`test_user_a`登录
2. 点击侧边栏的"匹配"tab（❤️图标）
3. 点击"开始匹配"按钮
4. 填写资料：
   ```
   生辰: 1995年3月15日12时
   MBTI: INFJ（点击选择）
   性别: 男
   个人简介: 热爱技术的开发者
   联系方式: wx123456（可选）
   ```
5. 点击"开始匹配"
6. 此时会提示"当前暂无可匹配的用户"（因为还没有异性用户完善资料）

### 第三步：完善用户B的资料

1. 退出登录（点击右下角"退出"）
2. 使用`test_user_b`登录
3. 点击"匹配"tab
4. 点击"开始匹配"
5. 填写资料：
   ```
   生辰: 1996年8月20日14时
   MBTI: ENFP（点击选择）
   性别: 女
   个人简介: 热爱生活的设计师
   联系方式: qq789012（可选）
   ```
6. 点击"开始匹配"

### 第四步：查看匹配结果

1. **查看用户A的匹配**
   - 退出，用`test_user_a`重新登录
   - 点击"匹配"tab
   - 应该能看到用户B的匹配卡片，显示：
     - 匹配度百分比（环形进度条）
     - 缘分类型标签（如"水火既济型"）
     - 日主、MBTI信息
     - 诗意描述
     - 详细匹配原因
     - 五行互补和MBTI契合的分数条
     - 联系方式（如果填写了）

2. **测试核心功能**
   - ✅ 点击"换一个"：应该提示"已经看完所有人了"
   - ✅ 点击"查看AI生成的详细配对报告"：弹窗展示800字Markdown格式的专属报告
   - ✅ 点击"给TA留言"：打开留言弹窗

### 第五步：测试留言功能

1. 在留言弹窗中输入消息："你好，缘分让我们相遇！"
2. 点击"发送"
3. 退出，用`test_user_b`登录
4. 点击"消息"tab
5. 应该看到：
   - 侧边栏有1个未读消息红点
   - 消息线程列表显示`test_user_a`的对话
   - 预览最后一条消息
6. 点击线程，右侧展示完整对话
7. 回复消息："很高兴认识你！"
8. 切换回`test_user_a`，在消息tab查看回复

---

## 预期效果验证清单

### 后端API（使用Postman或curl测试）

- [ ] POST `/api/user/profile` - 返回201和success:true
- [ ] GET `/api/user/profile` - 返回has_profile:true和profile对象
- [ ] GET `/api/match/next` - 返回匹配对象JSON（含total_score等字段）
- [ ] POST `/api/match/message` - 返回201和message_id
- [ ] GET `/api/match/messages/threads` - 返回threads数组
- [ ] GET `/api/match/messages/<user_id>` - 返回messages数组
- [ ] GET `/api/match/messages/unread-count` - 返回unread_count
- [ ] GET `/api/match/report/<user_id>` - 返回report（Markdown文本）

### 前端UI

- [ ] 侧边栏显示3个Tab（对话/匹配/消息）
- [ ] 点击"匹配"tab，显示"开始匹配"按钮
- [ ] 资料完善表单：
  - [ ] 年份1950-2010可选
  - [ ] 月份1-12、日期1-31、时辰0-23可选
  - [ ] 16个MBTI按钮，点击变蓝
  - [ ] 性别下拉框
  - [ ] 简介和联系方式输入框
- [ ] 匹配卡片展示：
  - [ ] 右上角环形分数（彩色进度圈）
  - [ ] 缘分类型标签带emoji
  - [ ] 头像占位符（用户名首字母）
  - [ ] 日主、MBTI信息卡片
  - [ ] 诗意描述（带边框高亮）
  - [ ] 匹配原因列表（带✓图标）
  - [ ] 五行互补和MBTI契合的横向进度条
  - [ ] "换一个"和"给TA留言"按钮
  - [ ] "查看AI报告"按钮
  - [ ] 联系方式展示（如果有）
- [ ] 留言弹窗：
  - [ ] 显示对方用户名和匹配度
  - [ ] 消息气泡（自己的在右边，对方的在左边）
  - [ ] 时间戳显示
  - [ ] 输入框和发送按钮
- [ ] 消息tab：
  - [ ] 未读数红点
  - [ ] 线程列表展示
  - [ ] 点击线程，右侧展示详情
- [ ] AI报告弹窗：
  - [ ] Markdown渲染
  - [ ] 包含四个章节（命理相性、心理契合、相处之道、玄明子赠言）

---

## 常见问题排查

### 问题1：匹配页面显示"请先完善个人资料"

**原因**：用户档案未完善或`is_profile_complete`为0

**解决**：检查数据库`user_profiles`表，确认该用户的记录存在且`is_profile_complete=1`

```bash
sqlite3 data/chat_history.db "SELECT * FROM user_profiles WHERE user_id='xxx';"
```

### 问题2：点击"查看报告"后一直loading

**原因**：AI API调用失败或超时

**解决**：
1. 检查`.env`中的`OPENAI_API_KEY`是否正确
2. 检查后端控制台是否有错误日志
3. 测试API连通性：`curl -H "Authorization: Bearer 你的key" https://api.sophnet.link/v1/models`

### 问题3：未读消息数不更新

**原因**：`updateUnreadCount()`未被定期调用

**解决**：
1. 确认`match.js`已正确引入
2. 确认登录后`showApp()`中调用了`updateUnreadCount()`
3. 检查浏览器控制台是否有JS错误

### 问题4：留言发送后没有显示

**原因**：消息保存到数据库了，但前端渲染逻辑有问题

**解决**：
1. 检查数据库：`sqlite3 data/chat_history.db "SELECT * FROM match_messages;"`
2. 检查API响应：打开浏览器Network面板，查看`/api/match/message`的响应
3. 检查`renderMessageHistory()`函数逻辑

---

## 性能监控建议

### 数据库查询优化

如果用户量增长到1000+，建议添加索引：

```sql
CREATE INDEX idx_match_candidates ON user_profiles(gender, is_profile_complete, allow_match);
CREATE INDEX idx_match_history ON match_history(user_id, shown_at);
CREATE INDEX idx_messages_unread ON match_messages(to_user_id, is_read);
```

### 缓存策略

可以使用Redis缓存匹配分数：

```python
# 伪代码
cache_key = f"match_score:{user_a_id}:{user_b_id}"
cached = redis.get(cache_key)
if cached:
    return json.loads(cached)
else:
    score = calculate_match_score(profile_a, profile_b)
    redis.setex(cache_key, 3600, json.dumps(score))  # 缓存1小时
    return score
```

---

## 祝测试顺利！🎉

有任何问题，查看`MATCH_FEATURE.md`了解更多细节。
