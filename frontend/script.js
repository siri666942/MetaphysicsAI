/**
 * AI+玄学 · 玄明子命理咨询 —— 前端脚本
 */

// API 地址配置
// 方式1：如果前后端同域，使用相对路径（推荐）
// 方式2：在 index.html 中添加 <script>window.API_BASE = 'https://your-backend.com/api'</script>
// 方式3：开发环境默认使用 localhost
const API_BASE = window.API_BASE || "http://localhost:5000/api";

// ============ 状态管理 ============
let currentConversationId = null;
let isStreaming = false; // 是否正在接收 AI 流式回复
let abortController = null; // 用于中止流式请求 —— 类似 Java 的 Future.cancel()，JS 用 AbortController

// ============ DOM 元素引用 ============
const sidebar = document.getElementById("sidebar");
const menuToggle = document.getElementById("menuToggle");
const overlay = document.getElementById("overlay");
const newChatBtn = document.getElementById("newChatBtn");
const conversationList = document.getElementById("conversationList");
const welcomeScreen = document.getElementById("welcomeScreen");
const messagesContainer = document.getElementById("messagesContainer");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

// ============ 初始化 ============
document.addEventListener("DOMContentLoaded", () => {
    loadConversations();
    setupEventListeners();
});

function setupEventListeners() {
    // 发送按钮（生成时变为停止按钮）
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
        const res = await fetch(`${API_BASE}/conversations`);
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
        const res = await fetch(`${API_BASE}/conversations`, { method: "POST" });
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
        const res = await fetch(`${API_BASE}/conversations/${convId}/messages`);
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
        await fetch(`${API_BASE}/conversations/${convId}`, { method: "DELETE" });

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
        const res = await fetch(`${API_BASE}/conversations`, { method: "POST" });
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
        const response = await fetch(
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
            updateMessageContent(aiMsgEl, "网络请求失败，请检查后端服务是否启动。");
        }
    } finally {
        isStreaming = false;
        abortController = null;
        setSendBtnMode("send");
        messageInput.focus();
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
        await fetch(`${API_BASE}/conversations/${conversationId}/save-partial`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content }),
        });
    } catch (err) {
        console.error("保存中止内容失败:", err);
    }
}

/** 快捷消息（欢迎页卡片点击） */
async function sendQuickMessage(text) {
    messageInput.value = text;
    await sendMessage();
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
