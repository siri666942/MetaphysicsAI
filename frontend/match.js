/**
 * 匹配功能前端逻辑
 */

// ============ 全局状态 ============
let currentMatchedUser = null;  // 当前显示的匹配对象
let currentMessageThread = null;  // 当前查看的消息线程
let selectedMbti = null;  // 用户选择的MBTI

// ============ 初始化 ============
document.addEventListener("DOMContentLoaded", () => {
    initMatchFeature();
});

function initMatchFeature() {
    setupTabSwitching();
    setupProfileForm();
    setupMatchIntroModal();
    setupMatchButtons();
    setupMessageFeature();
    
    // 立即更新一次未读消息数
    updateUnreadCount();
    
    // 定期检查未读消息数
    setInterval(updateUnreadCount, 30000);  // 30秒检查一次
}

// ============ Tab切换 ============
function setupTabSwitching() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const viewPanels = document.querySelectorAll('.view-panel');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            
            // 更新tab按钮状态
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // 切换侧边栏内容
            tabContents.forEach(content => {
                if (content.dataset.tab === tab) {
                    content.style.display = 'block';
                    content.classList.add('active');
                } else {
                    content.style.display = 'none';
                    content.classList.remove('active');
                }
            });
            
            // 切换主内容区
            viewPanels.forEach(panel => panel.style.display = 'none');
            
            const inputArea = document.querySelector('.input-area');
            
            if (tab === 'conversations') {
                document.getElementById('chatArea').style.display = 'flex';
                if (inputArea) inputArea.style.display = 'block';
            } else if (tab === 'match') {
                document.getElementById('matchArea').style.display = 'flex';
                if (inputArea) inputArea.style.display = 'none';
                checkProfileAndShowMatch();
                loadMatchHistory();
            } else if (tab === 'messages') {
                document.getElementById('messagesArea').style.display = 'flex';
                if (inputArea) inputArea.style.display = 'none';
                loadMessageThreads();
            }
        });
    });
}

// ============ 检查资料完善状态 ============
async function checkProfileAndShowMatch() {
    try {
        const res = await authFetch(`${API_BASE}/user/profile`);
        const data = await res.json();
        
        const editIntroBtn = document.getElementById('editMatchIntroBtn');
        const editProfileBtn = document.getElementById('editFullProfileBtn');
        if (data.has_profile) {
            // 已完善资料：只进入匹配页，等用户点「开始匹配」再请求 /match/next
            document.getElementById('matchWelcome').style.display = 'flex';
            document.getElementById('matchCardContainer').style.display = 'none';
            if (editIntroBtn) editIntroBtn.style.display = 'inline-block';
            if (editProfileBtn) editProfileBtn.style.display = 'inline-block';
        } else {
            // 未完善资料，显示欢迎界面
            document.getElementById('matchWelcome').style.display = 'flex';
            document.getElementById('matchCardContainer').style.display = 'none';
            if (editIntroBtn) editIntroBtn.style.display = 'none';
            if (editProfileBtn) editProfileBtn.style.display = 'none';
        }
    } catch (err) {
        console.error('检查资料失败:', err);
        document.getElementById('matchWelcome').style.display = 'flex';
        document.getElementById('matchCardContainer').style.display = 'none';
        const editIntroBtn = document.getElementById('editMatchIntroBtn');
        const editProfileBtn = document.getElementById('editFullProfileBtn');
        if (editIntroBtn) editIntroBtn.style.display = 'none';
        if (editProfileBtn) editProfileBtn.style.display = 'none';
    }
}

function setupMatchIntroModal() {
    const modal = document.getElementById('matchIntroModal');
    const closeBtn = document.getElementById('matchIntroModalClose');
    const form = document.getElementById('matchIntroForm');
    const editBtn = document.getElementById('editMatchIntroBtn');

    if (!modal || !form) return;

    const close = () => {
        modal.style.display = 'none';
    };

    closeBtn.addEventListener('click', close);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) close();
    });

    if (editBtn) {
        editBtn.addEventListener('click', async () => {
            const errEl = document.getElementById('matchIntroFormError');
            errEl.textContent = '';
            try {
                const res = await authFetch(`${API_BASE}/user/profile`);
                const data = await res.json();
                if (!data.has_profile || !data.profile) {
                    alert('请先完善资料');
                    return;
                }
                const p = data.profile;
                document.getElementById('matchIntroBio').value = p.bio || '';
                document.getElementById('matchIntroContact').value = p.contact_info || '';
                modal.style.display = 'flex';
            } catch (e) {
                console.error(e);
                alert('加载失败，请稍后重试');
            }
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const errEl = document.getElementById('matchIntroFormError');
        errEl.textContent = '';
        const bio = document.getElementById('matchIntroBio').value.trim();
        const contact_info = document.getElementById('matchIntroContact').value.trim();
        try {
            const res = await authFetch(`${API_BASE}/user/profile/match-intro`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ bio, contact_info }),
            });
            const result = await res.json();
            if (!res.ok) {
                errEl.textContent = result.error || '保存失败';
                return;
            }
            close();
        } catch (err) {
            errEl.textContent = '网络错误，请稍后重试';
            console.error(err);
        }
    });
}

// ============ 资料完善表单 ============
function setupProfileForm() {
    // 生成年份选项（1950-2010）
    const yearSelect = document.getElementById('birthYear');
    for (let year = 2010; year >= 1950; year--) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearSelect.appendChild(option);
    }
    
    // 生成月份选项
    const monthSelect = document.getElementById('birthMonth');
    for (let month = 1; month <= 12; month++) {
        const option = document.createElement('option');
        option.value = month;
        option.textContent = month;
        monthSelect.appendChild(option);
    }
    
    // 生成日期选项
    const daySelect = document.getElementById('birthDay');
    for (let day = 1; day <= 31; day++) {
        const option = document.createElement('option');
        option.value = day;
        option.textContent = day;
        daySelect.appendChild(option);
    }
    
    // 生成时辰选项
    const hourSelect = document.getElementById('birthHour');
    const hours = [
        {value: 0, label: '0时 (子时)'},
        {value: 1, label: '1时 (丑时)'},
        {value: 2, label: '2时 (丑时)'},
        {value: 3, label: '3时 (寅时)'},
        {value: 4, label: '4时 (寅时)'},
        {value: 5, label: '5时 (卯时)'},
        {value: 6, label: '6时 (卯时)'},
        {value: 7, label: '7时 (辰时)'},
        {value: 8, label: '8时 (辰时)'},
        {value: 9, label: '9时 (巳时)'},
        {value: 10, label: '10时 (巳时)'},
        {value: 11, label: '11时 (午时)'},
        {value: 12, label: '12时 (午时)'},
        {value: 13, label: '13时 (未时)'},
        {value: 14, label: '14时 (未时)'},
        {value: 15, label: '15时 (申时)'},
        {value: 16, label: '16时 (申时)'},
        {value: 17, label: '17时 (酉时)'},
        {value: 18, label: '18时 (酉时)'},
        {value: 19, label: '19时 (戌时)'},
        {value: 20, label: '20时 (戌时)'},
        {value: 21, label: '21时 (亥时)'},
        {value: 22, label: '22时 (亥时)'},
        {value: 23, label: '23时 (子时)'},
    ];
    hours.forEach(h => {
        const option = document.createElement('option');
        option.value = h.value;
        option.textContent = h.label;
        hourSelect.appendChild(option);
    });
    
    // 生成MBTI按钮
    const mbtiGrid = document.getElementById('mbtiGrid');
    const mbtiTypes = [
        {type: 'INTJ', name: '建筑师'},
        {type: 'INTP', name: '逻辑学家'},
        {type: 'ENTJ', name: '指挥官'},
        {type: 'ENTP', name: '辩论家'},
        {type: 'INFJ', name: '提倡者'},
        {type: 'INFP', name: '调停者'},
        {type: 'ENFJ', name: '主人公'},
        {type: 'ENFP', name: '竞选者'},
        {type: 'ISTJ', name: '物流师'},
        {type: 'ISFJ', name: '守卫者'},
        {type: 'ESTJ', name: '总经理'},
        {type: 'ESFJ', name: '执政官'},
        {type: 'ISTP', name: '鉴赏家'},
        {type: 'ISFP', name: '探险家'},
        {type: 'ESTP', name: '企业家'},
        {type: 'ESFP', name: '表演者'},
    ];
    
    mbtiTypes.forEach(m => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'mbti-btn';
        btn.dataset.mbti = m.type;
        btn.innerHTML = `<strong>${m.type}</strong><span>${m.name}</span>`;
        btn.addEventListener('click', () => selectMbti(m.type));
        mbtiGrid.appendChild(btn);
    });
    
    // 表单提交
    document.getElementById('profileForm').addEventListener('submit', handleProfileSubmit);
    
    // 关闭按钮
    document.getElementById('profileModalClose').addEventListener('click', () => {
        document.getElementById('profileModal').style.display = 'none';
    });

    document.getElementById('editFullProfileBtn')?.addEventListener('click', () => {
        openProfileModalForEdit();
    });
}

function selectMbti(type) {
    selectedMbti = type;
    document.getElementById('mbtiInput').value = type;
    
    // 更新按钮状态
    document.querySelectorAll('.mbti-btn').forEach(btn => {
        if (btn.dataset.mbti === type) {
            btn.classList.add('selected');
        } else {
            btn.classList.remove('selected');
        }
    });
}

function setProfileModalMode(isEdit) {
    const titleEl = document.getElementById('profileModalTitle');
    const subEl = document.getElementById('profileModalSubtitle');
    const submitBtn = document.getElementById('profileFormSubmitBtn');
    const hintEl = document.getElementById('profileModalEditHint');
    if (titleEl) {
        titleEl.textContent = isEdit ? '修改匹配资料' : '完善资料，开启缘分之旅';
    }
    if (subEl) {
        subEl.textContent = isEdit
            ? '可修改公历生辰、时辰、MBTI、性别与简介（将重新推算八字）'
            : '基于八字五行和MBTI匹配最适合你的人';
    }
    if (submitBtn) {
        submitBtn.textContent = isEdit ? '保存修改' : '开始匹配';
    }
    if (hintEl) {
        hintEl.style.display = isEdit ? 'block' : 'none';
    }
}

function clearProfileForm() {
    const y = document.getElementById('birthYear');
    const m = document.getElementById('birthMonth');
    const d = document.getElementById('birthDay');
    const h = document.getElementById('birthHour');
    if (y) y.value = '';
    if (m) m.value = '';
    if (d) d.value = '';
    if (h) h.value = '';
    const g = document.getElementById('genderSelect');
    if (g) g.value = '';
    const bio = document.getElementById('bioInput');
    const contact = document.getElementById('contactInput');
    if (bio) bio.value = '';
    if (contact) contact.value = '';
    const mbtiIn = document.getElementById('mbtiInput');
    if (mbtiIn) mbtiIn.value = '';
    selectedMbti = null;
    document.querySelectorAll('.mbti-btn').forEach(btn => btn.classList.remove('selected'));
    const errEl = document.getElementById('profileFormError');
    if (errEl) errEl.textContent = '';
}

function prefillProfileForm(p) {
    const y = document.getElementById('birthYear');
    const m = document.getElementById('birthMonth');
    const d = document.getElementById('birthDay');
    const h = document.getElementById('birthHour');
    if (y && p.birth_year != null) y.value = String(p.birth_year);
    if (m && p.birth_month != null) m.value = String(p.birth_month);
    if (d && p.birth_day != null) d.value = String(p.birth_day);
    if (h && p.birth_hour != null) h.value = String(p.birth_hour);
    const g = document.getElementById('genderSelect');
    if (g && p.gender) g.value = p.gender;
    const bio = document.getElementById('bioInput');
    const contact = document.getElementById('contactInput');
    if (bio) bio.value = p.bio || '';
    if (contact) contact.value = p.contact_info || '';
    if (p.mbti) {
        selectMbti(String(p.mbti).toUpperCase());
    }
}

function openProfileModalCreate() {
    setProfileModalMode(false);
    clearProfileForm();
    document.getElementById('profileModal').style.display = 'flex';
}

async function openProfileModalForEdit() {
    const errEl = document.getElementById('profileFormError');
    if (errEl) errEl.textContent = '';
    try {
        const res = await authFetch(`${API_BASE}/user/profile`);
        const data = await res.json();
        if (!data.has_profile || !data.profile) {
            alert('请先完善资料');
            return;
        }
        setProfileModalMode(true);
        clearProfileForm();
        prefillProfileForm(data.profile);
        document.getElementById('profileModal').style.display = 'flex';
    } catch (e) {
        console.error(e);
        alert('加载资料失败，请稍后重试');
    }
}

async function handleProfileSubmit(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        birth_year: formData.get('birth_year'),
        birth_month: formData.get('birth_month'),
        birth_day: formData.get('birth_day'),
        birth_hour: formData.get('birth_hour'),
        mbti: formData.get('mbti'),
        gender: formData.get('gender'),
        bio: formData.get('bio'),
        contact_info: formData.get('contact_info'),
    };
    
    // 验证
    const errEl = document.getElementById('profileFormError');
    errEl.textContent = '';
    
    if (!data.birth_year || !data.birth_month || !data.birth_day || !data.birth_hour) {
        errEl.textContent = '请填写完整的生辰信息';
        return;
    }
    
    if (!data.mbti) {
        errEl.textContent = '请选择你的MBTI类型';
        return;
    }
    
    if (!data.gender) {
        errEl.textContent = '请选择性别';
        return;
    }
    
    try {
        const res = await authFetch(`${API_BASE}/user/profile`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data),
        });
        
        const result = await res.json();
        
        if (!res.ok) {
            errEl.textContent = result.error || '提交失败';
            return;
        }
        
        // 成功，关闭弹窗；同步匹配页展示（需用户点「开始匹配」才会请求匹配）
        document.getElementById('profileModal').style.display = 'none';
        await checkProfileAndShowMatch();
        
    } catch (err) {
        errEl.textContent = '网络错误，请稍后重试';
        console.error(err);
    }
}

// ============ 匹配功能 ============
function setupMatchButtons() {
    document.getElementById('startMatchBtn').addEventListener('click', async () => {
        // 先检查是否已经有资料
        try {
            const res = await authFetch(`${API_BASE}/user/profile`);
            const data = await res.json();
            
            if (data.has_profile) {
                // 已有资料，直接开始匹配
                document.getElementById('matchWelcome').style.display = 'none';
                document.getElementById('matchCardContainer').style.display = 'block';
                await showNextMatch();
            } else {
                // 没有资料，显示资料完善弹窗（新建模式）
                openProfileModalCreate();
            }
        } catch (err) {
            console.error('检查资料失败:', err);
            openProfileModalCreate();
        }
    });
}

async function showNextMatch() {
    const container = document.getElementById('matchCardContainer');
    container.innerHTML = '<div class="loading-spinner">正在寻找缘分...</div>';
    
    try {
        const res = await authFetch(`${API_BASE}/match/next`);
        const match = await res.json();
        
        if (match.no_more) {
            // 如果没有可匹配的用户，回到开始匹配界面
            if (!match.can_reset) {
                // 如果不能重置（说明是第一次匹配或还没跳过任何人），回到欢迎界面
                document.getElementById('matchWelcome').style.display = 'flex';
                document.getElementById('matchCardContainer').style.display = 'none';
                return;
            }
            // 如果可以重置，显示"看完所有人"的提示
            renderNoMoreMatches(match);
            return;
        }
        
        currentMatchedUser = match;
        renderMatchCard(match);
        
    } catch (err) {
        container.innerHTML = '<div class="error-message">获取匹配失败，请稍后重试</div>';
        console.error(err);
    }
}

function renderMatchCard(match) {
    const container = document.getElementById('matchCardContainer');
    
    const safeUsername = escapeHtml(match.username);
    const safeBio = escapeHtml(match.bio || '这个人很神秘，没有留下简介');
    const safeContact = escapeHtml(match.contact_info || '');
    const usernameInitial = safeUsername[0] || '?';
    
    const html = `
        <div class="match-card" data-user-id="${escapeHtml(match.user_id)}">
            <div class="match-score-ring" style="--score: ${match.total_score}">
                <div class="score-inner">${Math.round(match.total_score)}%</div>
            </div>
            
            <div class="match-type-badge">${escapeHtml(match.match_type)}</div>
            
            <div class="match-avatar">
                <div class="avatar-placeholder">${usernameInitial}</div>
            </div>
            
            <h2 class="match-username">${safeUsername}</h2>
            <p class="match-bio">${safeBio}</p>
            
            <div class="match-info-grid">
                <div class="info-item">
                    <span class="info-label">日主</span>
                    <span class="info-value">${escapeHtml(match.rizhu)}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">MBTI</span>
                    <span class="info-value">${escapeHtml(match.mbti)}</span>
                </div>
            </div>
            
            <div class="match-description">
                <p>${escapeHtml(match.description)}</p>
            </div>
            
            <div class="match-reasons">
                <h4>匹配原因</h4>
                <ul>
                    ${match.reasons.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
                </ul>
            </div>
            
            <div class="match-breakdown">
                <div class="breakdown-item">
                    <span class="breakdown-label">八字契合</span>
                    <div class="breakdown-bar">
                        <div class="breakdown-fill" style="width: ${(match.breakdown.wuxing/60*100).toFixed(0)}%"></div>
                    </div>
                    <span class="breakdown-value">${match.breakdown.wuxing.toFixed(0)}/60</span>
                </div>
                <div class="breakdown-item">
                    <span class="breakdown-label">MBTI契合</span>
                    <div class="breakdown-bar">
                        <div class="breakdown-fill" style="width: ${(match.breakdown.mbti/40*100).toFixed(0)}%"></div>
                    </div>
                    <span class="breakdown-value">${match.breakdown.mbti.toFixed(0)}/40</span>
                </div>
            </div>
            
            <div class="match-actions">
                <button class="btn-skip" onclick="skipMatch()">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                    换一个
                </button>
                <button class="btn-message" onclick="openMessageModal('${escapeHtml(match.user_id)}', '${safeUsername}', ${match.total_score}, '${escapeHtml(match.match_type)}')">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                    给TA留言
                </button>
            </div>
            
            <button class="btn-report" onclick="viewMatchReport('${escapeHtml(match.user_id)}')">
                查看AI生成的详细配对报告 →
            </button>
            
            ${match.contact_info ? `
                <div class="contact-info-box">
                    <p>TA的联系方式：<strong>${safeContact}</strong></p>
                    <p class="contact-hint">可直接添加微信/QQ联系</p>
                </div>
            ` : ''}
        </div>
    `;
    
    container.innerHTML = html;
}

function renderNoMoreMatches(data) {
    const container = document.getElementById('matchCardContainer');
    
    let html = `
        <div class="no-more-matches">
            <div class="empty-icon">🌙</div>
            <h3>${data.message}</h3>
    `;
    
    if (data.can_reset) {
        html += `
            <p>想再看一遍之前的人吗？</p>
            <button class="btn-primary" onclick="resetAndMatch()">重新开始</button>
        `;
    } else {
        html += `<p>等其他用户完善资料后再来看看吧</p>`;
    }
    
    html += `</div>`;
    container.innerHTML = html;
}

function skipMatch() {
    showNextMatch();
}

async function resetAndMatch() {
    try {
        await authFetch(`${API_BASE}/match/reset`, {
            method: 'POST',
        });
        showNextMatch();
    } catch (err) {
        alert('重置失败，请稍后重试');
    }
}

// ============ 留言功能 ============
function setupMessageFeature() {
    document.getElementById('messageModalClose').addEventListener('click', () => {
        document.getElementById('messageModal').style.display = 'none';
    });
    
    document.getElementById('sendMessageBtn').addEventListener('click', sendMatchModalMessage);
    
    // Enter发送（Shift+Enter换行）
    document.getElementById('messageTextarea').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMatchModalMessage();
        }
    });
}

function openMessageModal(userId, username, matchScore, matchType) {
    currentMessageThread = {userId, username, matchScore, matchType};
    
    document.getElementById('messageTargetName').textContent = username;
    document.getElementById('messageTargetMeta').textContent = `匹配度: ${Math.round(matchScore)}% · ${matchType}`;
    
    document.getElementById('messageModal').style.display = 'flex';
    document.getElementById('messageTextarea').value = '';
    
    // 加载历史留言
    loadMessageHistory(userId);
}

async function loadMessageHistory(userId) {
    const box = document.getElementById('messageHistoryBox');
    box.innerHTML = '<div class="loading-spinner-small">加载中...</div>';
    
    try {
        const res = await authFetch(`${API_BASE}/match/messages/${userId}`);
        const data = await res.json();
        
        if (data.messages.length === 0) {
            box.innerHTML = '<div class="empty-messages">暂无留言，开启第一句对话吧</div>';
            return;
        }
        
        renderMessageHistory(data.messages);
        
        // 滚动到底部
        setTimeout(() => {
            box.scrollTop = box.scrollHeight;
        }, 100);
        
    } catch (err) {
        box.innerHTML = '<div class="error-message">加载失败</div>';
        console.error(err);
    }
}

function renderMessageHistory(messages) {
    const box = document.getElementById('messageHistoryBox');
    const myUserId = getCurrentUserId();
    
    if (!messages || messages.length === 0) {
        box.innerHTML = '<div class="empty-messages">暂无留言，开启第一句对话吧</div>';
        return;
    }
    
    const html = messages.map(msg => {
        const isMine = msg.from_user_id === myUserId;
        const className = isMine ? 'message-item message-mine' : 'message-item message-theirs';
        
        return `
            <div class="${className}">
                <div class="message-bubble">
                    <p>${escapeHtml(msg.content)}</p>
                    <span class="message-time">${formatTime(msg.created_at)}</span>
                </div>
            </div>
        `;
    }).join('');
    
    box.innerHTML = html;
}

/** 匹配留言弹窗内发送 */
async function sendMatchModalMessage() {
    const textarea = document.getElementById('messageTextarea');
    const content = textarea.value.trim();
    
    if (!content) return;
    if (!currentMessageThread) return;
    
    try {
        const res = await authFetch(`${API_BASE}/match/message`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                to_user_id: currentMessageThread.userId,
                content: content,
            }),
        });
        
        if (!res.ok) {
            const data = await res.json();
            alert(data.error || '发送失败');
            return;
        }
        
        // 清空输入框
        textarea.value = '';
        
        // 重新加载消息
        loadMessageHistory(currentMessageThread.userId);
        
    } catch (err) {
        alert('发送失败，请稍后重试');
        console.error(err);
    }
}

// ============ 消息线程列表 ============
async function loadMessageThreads() {
    const listEl = document.getElementById('messageThreadsList');
    listEl.innerHTML = '<div class="loading-spinner-small">加载中...</div>';
    
    try {
        const res = await authFetch(`${API_BASE}/match/messages/threads`);
        const data = await res.json();
        
        if (data.threads.length === 0) {
            listEl.innerHTML = '<div class="empty-messages">暂无消息</div>';
            return;
        }
        
        const html = data.threads.map(thread => {
            const lastMsg = thread.last_message;
            const preview = lastMsg ? lastMsg.content.substring(0, 30) : '暂无消息';
            
            return `
                <div class="thread-item ${thread.unread_count > 0 ? 'has-unread' : ''}" 
                     onclick="openThreadDetail('${thread.user_id}', '${thread.username}')">
                    <div class="thread-avatar">${thread.username[0]}</div>
                    <div class="thread-info">
                        <div class="thread-header">
                            <h4>${thread.username}</h4>
                            <span class="thread-meta">${thread.rizhu} · ${thread.mbti}</span>
                        </div>
                        <p class="thread-preview">${preview}</p>
                    </div>
                    ${thread.unread_count > 0 ? `<span class="unread-dot">${thread.unread_count}</span>` : ''}
                </div>
            `;
        }).join('');
        
        listEl.innerHTML = html;
        
    } catch (err) {
        listEl.innerHTML = '<div class="error-message">加载失败</div>';
        console.error(err);
    }
}

function openThreadDetail(userId, username) {
    // 在右侧消息区展示详情
    const detailView = document.getElementById('messageDetailView');
    
    detailView.innerHTML = `
        <div class="message-detail-header">
            <h3>${username}</h3>
        </div>
        <div class="message-detail-history" id="threadDetailHistory">
            <div class="loading-spinner-small">加载中...</div>
        </div>
        <div class="message-detail-input">
            <textarea id="threadMessageInput" placeholder="回复..." maxlength="500"></textarea>
            <button onclick="sendThreadMessage('${userId}')">发送</button>
        </div>
    `;
    
    loadThreadMessages(userId);
}

async function loadThreadMessages(userId) {
    const historyEl = document.getElementById('threadDetailHistory');
    
    try {
        const res = await authFetch(`${API_BASE}/match/messages/${userId}`);
        const data = await res.json();
        
        const myUserId = getCurrentUserId();
        
        const html = data.messages.map(msg => {
            const isMine = msg.from_user_id === myUserId;
            const className = isMine ? 'msg-item msg-mine' : 'msg-item msg-theirs';
            
            return `
                <div class="${className}">
                    <div class="msg-bubble">
                        <p>${escapeHtml(msg.content)}</p>
                        <span class="msg-time">${formatTime(msg.created_at)}</span>
                    </div>
                </div>
            `;
        }).join('');
        
        historyEl.innerHTML = html || '<div class="empty-messages">暂无留言</div>';
        
        // 滚动到底部
        setTimeout(() => {
            historyEl.scrollTop = historyEl.scrollHeight;
        }, 100);
        
        // 更新未读数
        updateUnreadCount();
        
    } catch (err) {
        historyEl.innerHTML = '<div class="error-message">加载失败</div>';
        console.error(err);
    }
}

async function sendThreadMessage(userId) {
    const input = document.getElementById('threadMessageInput');
    const content = input.value.trim();
    
    if (!content) return;
    
    try {
        const res = await authFetch(`${API_BASE}/match/message`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                to_user_id: userId,
                content: content,
            }),
        });
        
        if (!res.ok) {
            alert('发送失败');
            return;
        }
        
        input.value = '';
        loadThreadMessages(userId);
        
    } catch (err) {
        alert('发送失败，请稍后重试');
        console.error(err);
    }
}

// ============ AI报告生成 ============
let currentReportText = '';  // 存储当前报告的Markdown原文

async function viewMatchReport(userId) {
    document.getElementById('reportModal').style.display = 'flex';
    const contentEl = document.getElementById('reportContent');
    const copyBtn = document.getElementById('copyReportBtn');
    
    contentEl.innerHTML = '<div class="loading-spinner">AI正在生成专属配对报告...</div>';
    copyBtn.style.display = 'none';  // 加载时隐藏复制按钮
    
    try {
        const res = await authFetch(`${API_BASE}/match/report/${userId}`);
        const data = await res.json();
        
        if (!res.ok) {
            contentEl.innerHTML = `<div class="error-message">${data.error || '生成失败'}</div>`;
            return;
        }
        
        // 保存报告原文
        currentReportText = data.report;
        
        // 用marked渲染markdown
        const reportHtml = marked.parse(data.report);
        contentEl.innerHTML = reportHtml;
        
        // 显示复制按钮
        copyBtn.style.display = 'flex';
        
        // 如果是缓存的报告，可以在控制台输出提示
        if (data.cached) {
            console.log('展示缓存报告，生成时间:', data.generated_at);
        }
        
    } catch (err) {
        contentEl.innerHTML = '<div class="error-message">生成失败，请稍后重试</div>';
        console.error(err);
    }
    
    document.getElementById('reportModalClose').addEventListener('click', () => {
        document.getElementById('reportModal').style.display = 'none';
    }, {once: true});
}

// 复制报告内容
async function copyReport() {
    if (!currentReportText) {
        alert('暂无报告可复制');
        return;
    }
    
    try {
        await navigator.clipboard.writeText(currentReportText);
        
        // 显示复制成功的提示
        const copyBtn = document.getElementById('copyReportBtn');
        const originalHTML = copyBtn.innerHTML;
        
        copyBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span>已复制</span>
        `;
        copyBtn.style.backgroundColor = '#4CAF50';
        
        setTimeout(() => {
            copyBtn.innerHTML = originalHTML;
            copyBtn.style.backgroundColor = '';
        }, 2000);
        
    } catch (err) {
        alert('复制失败，请稍后重试');
        console.error(err);
    }
}

// ============ 未读消息数 ============
async function updateUnreadCount() {
    try {
        const res = await authFetch(`${API_BASE}/match/messages/unread-count`);
        const data = await res.json();
        
        console.log('[未读消息] 当前未读数:', data.unread_count);
        
        const badge = document.getElementById('unreadBadge');
        if (data.unread_count > 0) {
            badge.textContent = data.unread_count;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    } catch (err) {
        console.error('获取未读数失败:', err);
    }
}

// ============ 工具函数 ============
function getCurrentUserId() {
    return getUserId() || '';
}

function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    // 1分钟内
    if (diff < 60000) {
        return '刚刚';
    }
    // 1小时内
    if (diff < 3600000) {
        return `${Math.floor(diff/60000)}分钟前`;
    }
    // 今天
    if (date.toDateString() === now.toDateString()) {
        return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
    }
    // 昨天
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) {
        return '昨天';
    }
    // 更早
    return `${date.getMonth()+1}月${date.getDate()}日`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============ 匹配历史列表 ============
async function loadMatchHistory() {
    const listEl = document.getElementById('matchHistoryList');
    
    try {
        const res = await authFetch(`${API_BASE}/match/history`);
        const data = await res.json();
        
        if (!res.ok) {
            // 如果用户还没有资料，显示提示
            listEl.innerHTML = '<div class="match-history-hint">点击右侧"开始匹配"按钮<br>寻找命中人</div>';
            return;
        }
        
        if (data.history.length === 0) {
            listEl.innerHTML = '<div class="match-history-hint">还没有匹配记录<br>点击右侧开始匹配吧</div>';
            return;
        }
        
        renderMatchHistory(data.history);
        
    } catch (err) {
        console.error('加载匹配历史失败:', err);
        listEl.innerHTML = '<div class="match-history-hint">加载失败<br>请稍后重试</div>';
    }
}

function renderMatchHistory(history) {
    const listEl = document.getElementById('matchHistoryList');
    
    const html = history.map(item => {
        const scoreColor = item.total_score >= 80 ? '#4CAF50' : item.total_score >= 60 ? '#FF9800' : '#999';
        
        return `
            <div class="thread-item" onclick="viewHistoryMatch('${escapeHtml(item.user_id)}')">
                <div class="thread-avatar">${escapeHtml(item.username[0])}</div>
                <div class="thread-info">
                    <div class="thread-header">
                        <h4>${escapeHtml(item.username)}</h4>
                        <span class="thread-meta" style="color: ${scoreColor};">${Math.round(item.total_score)}%</span>
                    </div>
                    <p class="thread-preview">${escapeHtml(item.match_type)} · ${escapeHtml(item.rizhu)} · ${escapeHtml(item.mbti)}</p>
                </div>
            </div>
        `;
    }).join('');
    
    listEl.innerHTML = html;
}

async function viewHistoryMatch(userId) {
    const container = document.getElementById('matchCardContainer');
    container.innerHTML = '<div class="loading-spinner">加载中...</div>';
    
    document.getElementById('matchWelcome').style.display = 'none';
    document.getElementById('matchCardContainer').style.display = 'block';
    
    try {
        const res = await authFetch(`${API_BASE}/match/detail/${userId}`);
        const match = await res.json();
        
        if (!res.ok) {
            container.innerHTML = `<div class="error-message">${match.error || '加载失败'}</div>`;
            return;
        }
        
        currentMatchedUser = match;
        renderMatchCard(match);
        
    } catch (err) {
        container.innerHTML = '<div class="error-message">加载失败，请稍后重试</div>';
        console.error(err);
    }
}
