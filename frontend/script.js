/**
 * AI+玄学 · 玄明子命理咨询 —— 前端脚本
 */

// API_BASE 在 config.js 中定义（需要在 index.html 中先引入 config.js）

// ============ 状态管理 ============
let currentConversationId = null;
let isStreaming = false; // 是否正在接收 AI 流式回复
let abortController = null; // 用于中止流式请求 —— 类似 Java 的 Future.cancel()，JS 用 AbortController

// ============ DOM 元素引用 ============
const authOverlay = document.getElementById("authOverlay");
const appContainer = document.getElementById("appContainer");
const sidebar = document.getElementById("sidebar");
const menuToggle = document.getElementById("menuToggle");
const overlay = document.getElementById("overlay");
const newChatBtn = document.getElementById("newChatBtn");
const conversationList = document.getElementById("conversationList");
const welcomeScreen = document.getElementById("welcomeScreen");
const messagesContainer = document.getElementById("messagesContainer");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

// ============ Token 管理 ============
// localStorage 类似 Java 的 SharedPreferences，可持久化键值对

function getToken() { return localStorage.getItem("token"); }
function setToken(token) { localStorage.setItem("token", token); }
function clearToken() { localStorage.removeItem("token"); }

function getUsername() { return localStorage.getItem("username"); }
function setUsername(name) { localStorage.setItem("username", name); }
function clearUsername() { localStorage.removeItem("username"); }

function getUserId() { return localStorage.getItem("user_id"); }
function setUserId(id) { localStorage.setItem("user_id", id); }
function clearUserId() { localStorage.removeItem("user_id"); }

/** 站点公告：版本号变更后可对新公告再次展示 */
const SITE_ANNOUNCE_STORAGE_VERSION = "cyber_match_v1";

function getSiteAnnounceStorageKey() {
    const uid = getUserId();
    if (!uid) return null;
    return `beingecho_site_announce_${SITE_ANNOUNCE_STORAGE_VERSION}_${uid}`;
}

function dismissSiteAnnouncement() {
    const key = getSiteAnnounceStorageKey();
    if (key) localStorage.setItem(key, "1");
    const modal = document.getElementById("siteAnnounceModal");
    if (modal) modal.style.display = "none";
}

function maybeShowSiteAnnouncement() {
    const key = getSiteAnnounceStorageKey();
    if (!key || localStorage.getItem(key)) return;
    const modal = document.getElementById("siteAnnounceModal");
    if (!modal) return;
    modal.style.display = "flex";
}

/**
 * 带认证的 fetch 封装
 * 自动在请求头中添加 Bearer Token；如果收到 401，自动跳转登录
 */
async function authFetch(url, options = {}) {
    const token = getToken();
    if (token) {
        options.headers = {
            ...options.headers,
            Authorization: `Bearer ${token}`,
        };
    }
    const res = await fetch(url, options);
    if (res.status === 401) {
        clearToken();
        clearUsername();
        clearUserId();
        showAuthOverlay();
        throw new Error("登录已过期，请重新登录");
    }
    return res;
}

// ============ 初始化 ============
document.addEventListener("DOMContentLoaded", () => {
    setupEventListeners();
    fixMobileViewportHeight();   // 修复移动端视口高度
    checkAuth();
});

/**
 * 修复移动端浏览器 100vh 包含地址栏/底部导航栏的问题
 * 通过 JS 获取真实可视高度并设置 CSS 变量 --vh
 * 对不支持 dvh 的旧浏览器作为兜底方案
 */
function fixMobileViewportHeight() {
    function setVh() {
        const vh = window.innerHeight * 0.01;
        document.documentElement.style.setProperty('--vh', `${vh}px`);
    }
    setVh();
    // 浏览器地址栏显示/隐藏、键盘弹出都会触发 resize
    window.addEventListener('resize', setVh);
    // iOS Safari 特殊处理：滚动时地址栏收起也会改变视口
    window.addEventListener('orientationchange', () => {
        setTimeout(setVh, 100);
    });
}

function checkAuth() {
    const token = getToken();
    if (!token) {
        showAuthOverlay();
    } else {
        // 验证 token 有效性
        authFetch(`${API_BASE}/auth/me`)
            .then((res) => {
                if (res.ok) {
                    return res.json();
                }
                throw new Error("Token invalid");
            })
            .then((user) => {
                setUsername(user.username);
                setUserId(user.id);
                showApp();
            })
            .catch(() => {
                clearToken();
                clearUsername();
                clearUserId();
                showAuthOverlay();
            });
    }
}

function showAuthOverlay() {
    authOverlay.style.display = "flex";
    appContainer.style.display = "none";
}

function showApp() {
    authOverlay.style.display = "none";
    appContainer.style.display = "flex";
    document.getElementById("currentUserName").textContent = getUsername() || "用户";
    loadConversations();
    
    // 更新未读消息数（如果match.js已加载）
    if (typeof updateUnreadCount === 'function') {
        updateUnreadCount();
    }

    maybeShowSiteAnnouncement();
}

// ============ 认证事件 ============

function setupEventListeners() {
    // ---- 登录 ----
    const loginUsernameEl = document.getElementById("loginUsername");
    const loginPasswordEl = document.getElementById("loginPassword");
    // 快速登陆：用户名填 s 时去掉密码必填，避免浏览器在点登录时弹「请填写此字段」
    loginUsernameEl.addEventListener("input", () => {
        if (loginUsernameEl.value.trim() === "s") {
            loginPasswordEl.removeAttribute("required");
        } else {
            loginPasswordEl.setAttribute("required", "");
        }
    });

    document.getElementById("loginForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const errEl = document.getElementById("loginError");
        errEl.textContent = "";
        const username = loginUsernameEl.value.trim();
        const password = loginPasswordEl.value;

        if (!username) { errEl.textContent = "请输入用户名"; return; }
        if (!password && username !== "s") { errEl.textContent = "请输入密码"; return; }

        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });
            const data = await res.json();
            if (!res.ok) { errEl.textContent = data.error || "登录失败"; return; }
            setToken(data.token);
            setUsername(data.user.username);
            setUserId(data.user.id);
            showApp();
        } catch (err) {
            errEl.textContent = "网络错误，请检查后端是否启动";
        }
    });

    // ---- 注册 ----
    document.getElementById("registerForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const errEl = document.getElementById("regError");
        errEl.textContent = "";
        const username = document.getElementById("regUsername").value.trim();
        const password = document.getElementById("regPassword").value;
        const confirm = document.getElementById("regPasswordConfirm").value;

        if (!username || !password) { errEl.textContent = "请填写所有字段"; return; }
        if (password !== confirm) { errEl.textContent = "两次密码不一致"; return; }
        if (password.length < 6) { errEl.textContent = "密码至少 6 位"; return; }

        try {
            const res = await fetch(`${API_BASE}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });
            const data = await res.json();
            if (!res.ok) { errEl.textContent = data.error || "注册失败"; return; }
            setToken(data.token);
            setUsername(data.user.username);
            setUserId(data.user.id);
            showApp();
        } catch (err) {
            errEl.textContent = "网络错误，请检查后端是否启动";
        }
    });

    // ---- 密码可见性切换（眼睛按钮） ----
    // querySelectorAll 返回 NodeList，可以用 forEach 遍历（Java 中类似 List.forEach）
    document.querySelectorAll(".password-toggle").forEach((btn) => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            const input = document.getElementById(targetId);
            const eyeOff = btn.querySelector(".eye-off");
            const eyeOn = btn.querySelector(".eye-on");

            if (input.type === "password") {
                input.type = "text";           // 切换为明文
                eyeOff.style.display = "none";
                eyeOn.style.display = "block";
            } else {
                input.type = "password";       // 切换为密文
                eyeOff.style.display = "block";
                eyeOn.style.display = "none";
            }
        });
    });

    // ---- 切换登录/注册 ----
    document.getElementById("switchToRegister").addEventListener("click", () => {
        document.getElementById("loginForm").style.display = "none";
        document.getElementById("registerForm").style.display = "flex";
        document.getElementById("switchToRegister").style.display = "none";
        document.getElementById("switchToLogin").style.display = "inline";
    });
    document.getElementById("switchToLogin").addEventListener("click", () => {
        document.getElementById("loginForm").style.display = "flex";
        document.getElementById("registerForm").style.display = "none";
        document.getElementById("switchToRegister").style.display = "inline";
        document.getElementById("switchToLogin").style.display = "none";
    });

    // ---- 退出登录 ----
    document.getElementById("logoutBtn").addEventListener("click", () => {
        clearToken();
        clearUsername();
        clearUserId();
        currentConversationId = null;
        showAuthOverlay();
    });

    // ---- 打赏 / 联系我弹窗 ----
    document.getElementById("donateBtn").addEventListener("click", () => {
        document.getElementById("donateModal").classList.add("active");
    });
    document.getElementById("donateClose").addEventListener("click", () => {
        document.getElementById("donateModal").classList.remove("active");
    });
    document.getElementById("donateBackdrop").addEventListener("click", () => {
        document.getElementById("donateModal").classList.remove("active");
    });

    document.getElementById("contactBtn").addEventListener("click", () => {
        document.getElementById("contactModal").classList.add("active");
    });
    document.getElementById("contactClose").addEventListener("click", () => {
        document.getElementById("contactModal").classList.remove("active");
    });
    document.getElementById("contactBackdrop").addEventListener("click", () => {
        document.getElementById("contactModal").classList.remove("active");
    });

    // ---- 站点公告（登录后主界面，每账号本地仅展示一次） ----
    const siteAnnounceModal = document.getElementById("siteAnnounceModal");
    if (siteAnnounceModal) {
        siteAnnounceModal.addEventListener("click", (e) => {
            if (e.target === siteAnnounceModal) dismissSiteAnnouncement();
        });
        document.getElementById("siteAnnounceClose").addEventListener("click", dismissSiteAnnouncement);
        document.getElementById("siteAnnounceOk").addEventListener("click", dismissSiteAnnouncement);
    }
    document.addEventListener("keydown", (e) => {
        if (e.key !== "Escape") return;
        const m = document.getElementById("siteAnnounceModal");
        if (m && m.style.display === "flex") dismissSiteAnnouncement();
    });

    // ---- 发送 / 停止按钮 ----
    sendBtn.addEventListener("click", () => {
        if (isStreaming) {
            stopStreaming();
        } else {
            sendMessage();
        }
    });

    // 回车发送（Shift+Enter 换行）—— 注意：Java Swing 里键盘事件处理方式不同，JS 用 addEventListener
    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // 文本框自动调整高度
    messageInput.addEventListener("input", autoResize);

    // 新建对话
    newChatBtn.addEventListener("click", createNewConversation);

    // 移动端菜单
    menuToggle.addEventListener("click", () => {
        sidebar.classList.toggle("open");
        overlay.classList.toggle("active");
    });

    overlay.addEventListener("click", () => {
        sidebar.classList.remove("open");
        overlay.classList.remove("active");
    });
}

function autoResize() {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + "px";
}

// ============ 对话管理 ============

/** 加载所有对话列表 */
async function loadConversations() {
    try {
        const res = await authFetch(`${API_BASE}/conversations`);
        const conversations = await res.json();
        renderConversationList(conversations);
    } catch (err) {
        console.error("加载对话列表失败:", err);
    }
}

/** 渲染对话列表 */
function renderConversationList(conversations) {
    conversationList.innerHTML = "";

    if (conversations.length === 0) {
        conversationList.innerHTML = `
            <div style="text-align:center; padding:20px; color:var(--text-muted); font-size:13px;">
                暂无对话记录<br>点击上方按钮开始
            </div>`;
        return;
    }

    conversations.forEach((conv) => {
        const item = document.createElement("div");
        item.className = `conv-item${conv.id === currentConversationId ? " active" : ""}`;
        item.innerHTML = `
            <span class="conv-item-title">${escapeHtml(conv.title)}</span>
            <button class="conv-item-delete" title="删除对话" onclick="event.stopPropagation(); deleteConversation('${conv.id}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>`;
        item.addEventListener("click", () => switchConversation(conv.id));
        conversationList.appendChild(item);
    });
}

/** 创建新对话 */
async function createNewConversation() {
    try {
        const res = await authFetch(`${API_BASE}/conversations`, { method: "POST" });
        const conv = await res.json();
        currentConversationId = conv.id;
        await loadConversations();
        showChatView([]);
        messageInput.focus();

        // 移动端关闭侧边栏
        sidebar.classList.remove("open");
        overlay.classList.remove("active");
    } catch (err) {
        console.error("创建对话失败:", err);
    }
}

/** 切换到指定对话 */
async function switchConversation(convId) {
    if (convId === currentConversationId) return;

    currentConversationId = convId;
    await loadConversations(); // 刷新列表高亮

    try {
        const res = await authFetch(`${API_BASE}/conversations/${convId}/messages`);
        const messages = await res.json();
        showChatView(messages);
    } catch (err) {
        console.error("加载消息失败:", err);
    }

    // 移动端关闭侧边栏
    sidebar.classList.remove("open");
    overlay.classList.remove("active");
}

/** 删除对话 */
async function deleteConversation(convId) {
    if (!confirm("确定要删除这个对话吗？")) return;

    try {
        await authFetch(`${API_BASE}/conversations/${convId}`, { method: "DELETE" });

        if (convId === currentConversationId) {
            currentConversationId = null;
            showWelcome();
        }

        await loadConversations();
    } catch (err) {
        console.error("删除对话失败:", err);
    }
}

// ============ 界面切换 ============

function showWelcome() {
    welcomeScreen.style.display = "flex";
    messagesContainer.style.display = "none";
}

function showChatView(messages) {
    welcomeScreen.style.display = "none";
    messagesContainer.style.display = "flex";
    messagesContainer.innerHTML = "";

    messages.forEach((msg) => {
        appendMessage(msg.role, msg.content, false);
    });

    scrollToBottom();
}

// ============ 消息发送与接收 ============

/** 发送用户消息 */
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isStreaming) return;

    // 如果没有当前对话，先创建一个
    if (!currentConversationId) {
        const res = await authFetch(`${API_BASE}/conversations`, { method: "POST" });
        const conv = await res.json();
        currentConversationId = conv.id;
        showChatView([]);
        await loadConversations();
    }

    // 清空输入框
    messageInput.value = "";
    messageInput.style.height = "auto";

    // 显示用户消息
    appendMessage("user", text, false);
    scrollToBottom();

    // 创建 AI 消息占位（带打字动画）
    const aiMsgEl = appendMessage("assistant", "", true);
    scrollToBottom();

    // 切换为"生成中"状态，按钮变为停止按钮
    isStreaming = true;
    abortController = new AbortController();
    setSendBtnMode("stop");

    let fullContent = "";

    try {
        // 使用 SSE 接收流式回复
        const response = await authFetch(
            `${API_BASE}/conversations/${currentConversationId}/chat`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text }),
                signal: abortController.signal, // 关联 AbortController，允许中途取消
            }
        );

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // 解析 SSE 数据行
            const lines = buffer.split("\n");
            buffer = lines.pop(); // 保留未完成的行

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const data = line.slice(6);

                if (data === "[DONE]") continue;

                try {
                    const parsed = JSON.parse(data);

                    if (parsed.content) {
                        fullContent += parsed.content;
                        updateMessageContent(aiMsgEl, fullContent);
                        scrollToBottom(false); // 流式生成时不强制滚动，尊重用户阅读位置
                    }

                    if (parsed.title_update) {
                        // 对话标题更新
                        loadConversations();
                    }

                    if (parsed.error) {
                        updateMessageContent(aiMsgEl, parsed.error);
                    }
                } catch (e) {
                    // 忽略解析错误
                }
            }
        }
    } catch (err) {
        if (err.name === "AbortError") {
            // 用户主动停止，保存已生成的部分内容
            console.log("用户中止了生成");
            if (fullContent) {
                // 通知后端保存已生成的不完整回复
                savePartialResponse(currentConversationId, fullContent);
            }
        } else {
            console.error("请求失败:", err);
            if (!err.message.includes("登录已过期")) {
                updateMessageContent(aiMsgEl, "网络请求失败，请检查后端服务是否启动。");
            }
        }
    } finally {
        isStreaming = false;
        abortController = null;
        setSendBtnMode("send");
        // 回答完毕后不自动 focus 输入框，避免移动端强制弹出键盘
    }
}

/** 停止 AI 生成 */
function stopStreaming() {
    if (abortController) {
        abortController.abort();
    }
}

/** 切换发送按钮的外观：send（发送）/ stop（停止） */
function setSendBtnMode(mode) {
    if (mode === "stop") {
        sendBtn.disabled = false;
        sendBtn.classList.add("stop-mode");
        sendBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none">
                <rect x="6" y="6" width="12" height="12" rx="2"></rect>
            </svg>`;
        sendBtn.title = "停止生成";
    } else {
        sendBtn.disabled = false;
        sendBtn.classList.remove("stop-mode");
        sendBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>`;
        sendBtn.title = "发送";
    }
}

/** 通知后端保存用户中止后的不完整回复 */
async function savePartialResponse(conversationId, content) {
    try {
        await authFetch(`${API_BASE}/conversations/${conversationId}/save-partial`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content }),
        });
    } catch (err) {
        console.error("保存中止内容失败:", err);
    }
}

// ============ 话题引导（卡片点击） ============

/** 各话题的 AI 引导话术 */
const TOPIC_GREETINGS = {
    bazi: {
        title: "八字命理分析",
        message: `你好呀！我是玄明子，很高兴为你进行**八字命理分析**。

八字又称"四柱"，是根据出生时间推算命运的传统命理方法。为了给你做准确的分析，我需要你提供以下信息：

1. **性别**：男 / 女
2. **出生日期**：年、月、日（请注明是**阳历**还是**阴历/农历**）
3. **出生时间**：尽量精确到时辰（如：上午10点左右）
   - 如果不确定具体时辰也没关系，可以告诉我大概时间段，我来帮你推算

> 💡 举个例子："我是男生，阳历1995年7月28日，上午10点左右出生的"

请把你的信息告诉我吧～`
    },
    meihua: {
        title: "梅花易数起卦",
        message: `你好呀！我是玄明子，很高兴为你进行**梅花易数起卦**。

梅花易数是一种灵活的占卜方式，可以针对你当下关心的具体问题来起卦解读。起卦方式有以下几种，你可以选择一种：

**方式一：报数起卦（推荐）**
- 请随意说出 **三个数字**（0-999 之间均可），心中默想你要问的事情

**方式二：时间起卦**
- 告诉我你想问的事情，我用当前时间为你起卦

**方式三：文字起卦**
- 随意说一个词或一句话，我根据字数笔画起卦

> 💡 起卦时最重要的是**心诚意专**，心里想着你关心的那件事。比如："我想问一下最近的工作发展，数字是 5、8、3"

请告诉我你想问什么，以及选择哪种起卦方式吧～`
    },
    liuyao: {
        title: "六爻占卜",
        message: `你好呀！我是玄明子，很高兴为你进行**六爻占卜**。

六爻占卜源自《周易》，是中国传统占卜术中最为严谨精密的方法之一，尤其擅长预测具体事件的吉凶走向。

**起卦方式：**

**方式一：报数起卦（推荐）**
- 请随意说出 **三个数字**（1-999 之间均可），心中默念你要问的事情

**方式二：时间起卦**
- 告诉我你想问的事情，我用当前时间为你起卦

> 💡 起卦要领：心诚则灵。起卦前请先静心片刻，心中专注于你想问的那一件事，然后报出三个数字。
>
> 比如："我想问最近的感情运势，数字是 7、3、5"

请告诉我你想问什么，以及你的三个数字吧～`
    },
    name: {
        title: "姓名五行分析",
        message: `你好呀！我是玄明子，很高兴为你进行**姓名五行分析**。

中国传统姓名学认为，名字的笔画和五行配置会对人的运势产生影响。为了给你做详细的分析，我需要以下信息：

1. **完整姓名**：姓 + 名（请用规范汉字）
2. **性别**：男 / 女
3. **分析目的**（可选）：
   - 想了解现有名字的五行吉凶？
   - 还是想取名/改名，需要建议？

如果是帮宝宝取名，还需要提供：
- 宝宝的**出生日期和时间**（用于结合八字分析）
- 有没有特别希望/避免的字？

> 💡 举个例子："我叫李明辉，男，想看看这个名字的五行怎么样"

请把你的信息告诉我吧～`
    },
    zeday: {
        title: "择日择吉咨询",
        message: `你好呀！我是玄明子，很高兴为你提供**择日择吉**咨询。

中国传统择日学讲究"天时地利人和"，选择合适的日子办事可以顺风顺水。为了给你挑选吉日，我需要以下信息：

1. **要办什么事？** 例如：
   - 🏠 搬家入宅
   - 💒 结婚订婚
   - 🏪 开业开张
   - 🚗 提车出行
   - 📋 签约合作
   - 其他事项也可以说
2. **大致的时间范围**：希望在哪个月份或哪段时间内？
3. **你的生肖或出生年份**：用于避开个人冲煞

> 💡 举个例子："我属虎的，打算3月份搬家，帮我挑几个好日子"

请告诉我你的具体需求吧～`
    }
};

/**
 * 话题引导入口 —— 点击卡片后由 AI 先开口引导用户
 * @param {string} topic - 话题 key（bazi / meihua / liuyao / name / zeday）
 */
async function startTopicChat(topic) {
    const topicInfo = TOPIC_GREETINGS[topic];
    if (!topicInfo) return;

    // 1. 创建新对话
    try {
        const res = await authFetch(`${API_BASE}/conversations`, { method: "POST" });
        const conv = await res.json();
        currentConversationId = conv.id;
    } catch (err) {
        console.error("创建对话失败:", err);
        return;
    }

    // 2. 切换到聊天视图，显示 AI 的引导消息
    showChatView([]);
    appendMessage("assistant", topicInfo.message, false);
    scrollToBottom();
    await loadConversations();

    // 3. 保存 AI 引导消息到后端（持久化）
    try {
        await authFetch(`${API_BASE}/conversations/${currentConversationId}/save-partial`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: topicInfo.message }),
        });
        // 用话题名作为对话标题
        await authFetch(`${API_BASE}/conversations/${currentConversationId}/title`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: topicInfo.title }),
        });
        await loadConversations();
    } catch (err) {
        console.error("保存引导消息失败:", err);
    }

    // 移动端关闭侧边栏
    sidebar.classList.remove("open");
    overlay.classList.remove("active");
    messageInput.focus();
}

// ============ DOM 操作 ============

/**
 * 添加一条消息到聊天区
 * @param {string} role - "user" 或 "assistant"
 * @param {string} content - 消息内容
 * @param {boolean} isTyping - 是否显示打字动画
 * @returns {HTMLElement} 消息内容元素
 */
function appendMessage(role, content, isTyping) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}`;

    const avatar = role === "assistant" ? "🔮" : "👤";

    msgDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            ${isTyping
                ? '<div class="typing-indicator"><span></span><span></span><span></span></div>'
                : renderMarkdown(content)
            }
        </div>`;

    messagesContainer.appendChild(msgDiv);

    return msgDiv.querySelector(".message-content");
}

/**
 * 更新消息内容（流式输出时持续调用）
 */
function updateMessageContent(el, content) {
    el.innerHTML = renderMarkdown(content);
}

/** Markdown 渲染 */
function renderMarkdown(text) {
    if (!text) return "";
    // marked 是通过 CDN 引入的全局库
    if (typeof marked !== "undefined") {
        // marked v5+ 用 marked.parse()
        return marked.parse(text);
    }
    // 降级：简单换行处理
    return text.replace(/\n/g, "<br>");
}

/**
 * 判断消息容器是否已滚动到底部附近（50px 容差）
 */
function isNearBottom() {
    const threshold = 50;
    return (
        messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight < threshold
    );
}

/**
 * 滚动到底部
 * @param {boolean} force - 为 true 时强制滚动（如用户发消息），为 false 时仅在已处于底部才滚动
 */
function scrollToBottom(force = true) {
    if (!force && !isNearBottom()) return; // 用户正在上方阅读，不打扰
    requestAnimationFrame(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });
}

/** HTML 转义（防 XSS） */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
