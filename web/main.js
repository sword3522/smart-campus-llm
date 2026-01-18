// ============ 对话历史管理 ============
let chatHistory = [];

// 从localStorage加载历史记录
function loadChatHistory() {
    try {
        const saved = localStorage.getItem('chatHistory');
        if (saved) {
            chatHistory = JSON.parse(saved);
            renderChatHistory();
        }
    } catch (err) {
        console.error("加载对话历史失败:", err);
        chatHistory = [];
    }
}

// 保存历史记录到localStorage
function saveChatHistory() {
    try {
        localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
    } catch (err) {
        console.error("保存对话历史失败:", err);
    }
}

// 添加对话到历史记录
function addToChatHistory(question, answer, identity, meta) {
    const chatItem = {
        id: Date.now(),
        question,
        answer,
        identity,
        timestamp: new Date().toISOString(),
        days_referenced: meta.days_referenced || 7,
        answered_at: meta.answered_at || new Date().toISOString()
    };
    
    chatHistory.unshift(chatItem); // 最新的在前面
    
    // 限制历史记录数量（最多保留50条）
    if (chatHistory.length > 50) {
        chatHistory = chatHistory.slice(0, 50);
    }
    
    saveChatHistory();
    renderChatHistory();
}

// 渲染对话历史
function renderChatHistory() {
    const chatHistoryDiv = document.getElementById("chat-history");
    const chatCountSpan = document.getElementById("chat-count");
    
    chatCountSpan.textContent = chatHistory.length;
    
    if (chatHistory.length === 0) {
        chatHistoryDiv.innerHTML = `
            <div class="chat-empty">
                <i class="fas fa-comments"></i>
                <p>还没有对话记录<br>开始提问吧！</p>
            </div>
        `;
        return;
    }
    
    chatHistoryDiv.innerHTML = chatHistory.map(item => {
        const identityText = item.identity === "student" ? "学生" : "教师";
        const time = new Date(item.timestamp).toLocaleString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        // 截断过长的答案（显示前500字符）
        const answerPreview = item.answer.length > 500 
            ? item.answer.substring(0, 500) + '... (点击显示更多)' 
            : item.answer;
        
        return `
            <div class="history-item" data-id="${item.id}">
                <div class="history-item-question">
                    <div class="bubble">
                        ${escapeHtml(item.question)}
                    </div>
                </div>
                <div class="history-item-answer">
                    <div class="bubble">
                        ${escapeHtml(answerPreview).replace(/\n/g, '<br>')}
                    </div>
                </div>
                <div class="history-item-meta">
                    <span><i class="fas fa-clock"></i> ${time}</span>
                    <span><i class="fas fa-calendar"></i> 参考${item.days_referenced}天</span>
                </div>
            </div>
        `;
    }).join('');
    
    // 滚动到底部（最新的在最下面）
    // 注意：flex-direction: column-reverse 使最新的在最上面，所以这里实际上是滚动到顶部
    chatHistoryDiv.scrollTop = 0;
}

// 清空对话历史
function clearChatHistory() {
    if (chatHistory.length === 0) {
        return;
    }
    
    if (confirm('确定要清空所有对话历史吗？')) {
        chatHistory = [];
        saveChatHistory();
        renderChatHistory();
    }
}

// HTML转义函数
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============ 工具函数 ============

// 显示加载状态
function showLoading(element) {
    element.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <span>正在加载中...</span>
        </div>
    `;
    element.classList.add('show');
}

// 显示错误信息
function showError(element, message) {
    element.innerHTML = `
        <div class="content error">
            <i class="fas fa-exclamation-circle"></i>
            ${message}
        </div>
    `;
    element.classList.add('show');
}

// 格式化日期显示
function formatDate(dateStr) {
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
    const weekday = weekdays[date.getDay()];
    return `${year}年${month}月${day}日 ${weekday}`;
}

// ============ 获取历史日报日期列表 ============
async function loadReportDates() {
    try {
        const res = await fetch("/reports");
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        const data = await res.json();
        const select = document.getElementById("report-date");
        select.innerHTML = "";
        
        // 始终添加"今天"的选项，方便用户生成
        // 使用本地时间而不是 UTC 时间
        const now = new Date();
        const availableSet = new Set(data.available_dates || []);
        
        // 生成过去30天的日期列表
        for (let i = 0; i < 30; i++) {
            const d = new Date(now);
            d.setDate(now.getDate() - i);
            
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            const dateStr = `${year}-${month}-${day}`;
            
            const option = document.createElement("option");
            option.value = dateStr;
            
            if (availableSet.has(dateStr)) {
                option.textContent = formatDate(dateStr);
            } else {
                option.textContent = `${formatDate(dateStr)} (未生成)`;
                // 给未生成的选项加一个特殊的标记，也许可以在CSS里置灰
                option.classList.add("not-generated");
            }
            select.appendChild(option);
        }
        
        // 默认选择最新的日期（即今天）
        select.selectedIndex = 0;
    } catch (err) {
        console.error("加载日报列表失败:", err);
        const select = document.getElementById("report-date");
        select.innerHTML = '<option value="">加载失败</option>';
    }
}

// ============ 提交问答 ============
async function askQuestion() {
    const questionInput = document.getElementById("question");
    const question = questionInput.value.trim();
    const identity = document.getElementById("global-identity").value;
    const responseDiv = document.getElementById("answer");
    const askBtn = document.getElementById("ask-btn");
    
    if (!question) {
        responseDiv.innerHTML = `
            <div class="content error">
                <i class="fas fa-exclamation-triangle"></i>
                请输入您的问题！
            </div>
        `;
        responseDiv.classList.add('show');
        questionInput.focus();
        return;
    }

    // 禁用按钮并显示加载状态
    askBtn.disabled = true;
    askBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    showLoading(responseDiv);

    try {
        const res = await fetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                question, 
                identity, 
                days: 7 
            })
        });

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.detail || `请求失败: HTTP ${res.status}`);
        }

        const data = await res.json();
        
        if (data.answer) {
            const identityText = identity === "student" ? "学生" : "教师";
            
            // 添加到对话历史
            addToChatHistory(question, data.answer, identity, {
                days_referenced: data.days_referenced || 7,
                answered_at: data.answered_at
            });
            
            // 清空输入框
            questionInput.value = '';
            
            // 滚动到底部（因为是反向flex，其实是顶部）
            const chatHistoryDiv = document.getElementById("chat-history");
            chatHistoryDiv.scrollTop = 0;
            
        } else {
            // 如果没有回答，显示错误在历史记录区域
            const chatHistoryDiv = document.getElementById("chat-history");
            const errorDiv = document.createElement('div');
            errorDiv.className = 'history-item-answer';
            errorDiv.innerHTML = `<div class="bubble" style="color:red; border-color:red;">未获取到回答，请稍后重试</div>`;
            chatHistoryDiv.prepend(errorDiv);
        }
    } catch (err) {
        console.error("问答请求失败:", err);
        showError(responseDiv, `请求失败: ${err.message}`);
    } finally {
        // 恢复按钮状态
        askBtn.disabled = false;
        askBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
    }
}

// ============ 格式化日报内容 ============
function formatReportContent(text) {
    if (!text) return '';
    
    // 如果包含"今日无重要新闻通知"，直接显示
    if (text.includes("今日无重要新闻") || text.length < 50) {
        return `<div class="empty-news-message">${text}</div>`;
    }

    // 预处理：将 HTML 特殊字符转义
    let safeText = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // 1. 处理加粗 (**text**)
    safeText = safeText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // 2. 分割成不同的新闻块 (基于 ### 标题)
    // 注意：分割后数组第一个元素可能是空或者开头的非标题文本
    const sections = safeText.split(/(?=### )/);
    
    let html = '';
    
    sections.forEach(section => {
        section = section.trim();
        if (!section) return;
        
        // 检查是否是标题块
        if (section.startsWith('### ')) {
            // 提取标题和内容
            const lines = section.split('\n');
            const title = lines[0].replace('### ', '').trim();
            const contentLines = lines.slice(1);
            
            // 处理内容部分的列表
            let bodyHtml = '';
            let inList = false;
            
            contentLines.forEach(line => {
                line = line.trim();
                if (!line) return;
                
                if (line.startsWith('- ')) {
                    if (!inList) {
                        bodyHtml += '<ul class="news-list">';
                        inList = true;
                    }
                    bodyHtml += `<li>${line.substring(2)}</li>`;
                } else {
                    if (inList) {
                        bodyHtml += '</ul>';
                        inList = false;
                    }
                    bodyHtml += `<p>${line}</p>`;
                }
            });
            
            if (inList) bodyHtml += '</ul>';
            
            html += `
                <div class="news-card">
                    <div class="news-title">${title}</div>
                    <div class="news-body">${bodyHtml}</div>
                </div>
            `;
        } else {
            // 普通文本段落（可能是开头介绍）
            html += `<div class="news-intro">${section.replace(/\n/g, '<br>')}</div>`;
        }
    });
    
    return html;
}

// ============ 获取日报 ============
async function getReport() {
    const dateSelect = document.getElementById("report-date");
    const date = dateSelect.value;
    const identity = document.getElementById("global-identity").value;
    const reportDiv = document.getElementById("report");
    const reportBtn = document.getElementById("report-btn");
    
    // 检查是否是"未生成"的日期
    const optionText = dateSelect.options[dateSelect.selectedIndex].text;
    const needsGeneration = optionText.includes("(未生成)");

    if (!date) {
        showError(reportDiv, "请先选择日期！");
        return;
    }

    reportBtn.disabled = true;
    showLoading(reportDiv);

    try {
        // 如果未生成，尝试调用生成接口
        if (needsGeneration) {
            reportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>正在生成...</span>';
            
            // 调用生成接口，传入具体日期
            const jobRes = await fetch(`/daily-job?date=${date}`, { method: "POST" });
            if (!jobRes.ok) {
                 throw new Error("生成日报失败，请稍后重试");
            }
            
            // 生成成功后，更新下拉框文本（去掉"未生成"）
            dateSelect.options[dateSelect.selectedIndex].text = formatDate(date);
            
            // 稍等片刻确保文件写入
            await new Promise(r => setTimeout(r, 1000));
        } else {
             reportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>加载中...</span>';
        }

        const res = await fetch(`/report?date=${date}&identity=${identity}`);
        
        if (!res.ok) {
            if (res.status === 404) {
                 if (needsGeneration) {
                     throw new Error("暂无该日期的新闻或生成失败");
                 }
                 throw new Error(`未找到 ${date} 的日报`);
            }
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.detail || `请求失败: HTTP ${res.status}`);
        }

        const data = await res.json();
        const identityText = identity === "student" ? "学生" : "教师";
        const summary = identity === "student" ? data.student_summary : data.teacher_summary;
        
        if (summary) {
            // 使用新的格式化函数
            const formattedContent = formatReportContent(summary);
            
            reportDiv.innerHTML = `
                <div class="meta">
                    <div class="meta-item">
                        <i class="fas fa-calendar-alt"></i>
                        <span>${formatDate(data.date)}</span>
                    </div>
                    <div class="meta-item">
                        <i class="fas fa-newspaper"></i>
                        <span>累计新闻: ${data.news_count || 0} 条</span>
                    </div>
                    <div class="meta-item">
                        <i class="fas fa-check-circle"></i>
                        <span>有效新闻: ${data.effective_news_count || 0} 条</span>
                    </div>
                    <div class="meta-item">
                        <i class="fas fa-user"></i>
                        <span>${identityText}版</span>
                    </div>
                    ${data.generated_at ? `
                    <div class="meta-item">
                        <i class="fas fa-clock"></i>
                        <span>生成时间: ${new Date(data.generated_at).toLocaleString('zh-CN')}</span>
                    </div>
                    ` : ''}
                </div>
                <div class="content">
                    ${formattedContent}
                </div>
            `;
            reportDiv.classList.add('show');
        } else {
            showError(reportDiv, "该日期暂无日报内容");
        }
    } catch (err) {
        console.error("获取日报失败:", err);
        showError(reportDiv, err.message || "请求失败，请稍后重试");
    } finally {
        reportBtn.disabled = false;
        reportBtn.innerHTML = '<i class="fas fa-eye"></i><span>查看日报</span>';
    }
}

// ============ 获取周报 ============
async function getWeeklyReport() {
    const dateSelect = document.getElementById("report-date");
    const endDateStr = dateSelect.value;
    const identity = document.getElementById("global-identity").value;
    const reportDiv = document.getElementById("report");
    const reportBtn = document.getElementById("weekly-report-btn");
    
    if (!endDateStr) {
        showError(reportDiv, "请先选择结束日期！");
        return;
    }

    reportBtn.disabled = true;
    showLoading(reportDiv);

    try {
        // ... (省略前面的补全逻辑) ...
        const reportsRes = await fetch("/reports");
        const reportsData = await reportsRes.json();
        const availableSet = new Set(reportsData.available_dates || []);

        const endDate = new Date(endDateStr);
        const missingDates = [];
        
        for (let i = 0; i < 7; i++) {
            const d = new Date(endDate);
            d.setDate(endDate.getDate() - i);
            
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            const dateStr = `${year}-${month}-${day}`;
            
            if (!availableSet.has(dateStr)) {
                missingDates.push(dateStr);
            }
        }

        missingDates.reverse();

        for (const missingDate of missingDates) {
            reportBtn.innerHTML = `<i class="fas fa-sync fa-spin"></i><span>正在补全 ${missingDate}...</span>`;
            const loadingSpan = reportDiv.querySelector('.loading span');
            if (loadingSpan) {
                loadingSpan.textContent = `正在抓取并生成 ${missingDate} 的日报...`;
            }

            try {
                const jobRes = await fetch(`/daily-job?date=${missingDate}`, { method: "POST" });
                if (!jobRes.ok) {
                    console.warn(`自动补全 ${missingDate} 失败，继续尝试下一个...`);
                }
            } catch (e) {
                console.warn(`补全请求异常 ${missingDate}:`, e);
            }
        }

        reportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>生成周报总结...</span>';
        const loadingSpan = reportDiv.querySelector('.loading span');
        if (loadingSpan) {
            loadingSpan.textContent = '正在汇总生成周报...';
        }

        const res = await fetch(`/report/weekly?date=${endDateStr}&identity=${identity}`);
        
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.detail || `请求失败: HTTP ${res.status}`);
        }

        const data = await res.json();
        const identityText = identity === "student" ? "学生" : "教师";
        const summary = identity === "student" ? data.student_summary : data.teacher_summary;
        
        if (summary) {
            // 使用新的格式化函数
            const formattedContent = formatReportContent(summary);

            reportDiv.innerHTML = `
                <div class="meta" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
                    <div class="meta-item">
                        <i class="fas fa-calendar-week"></i>
                        <span>周报范围: ${data.date}</span>
                    </div>
                    <div class="meta-item">
                        <i class="fas fa-newspaper"></i>
                        <span>累计新闻: ${data.news_count || 0} 条</span>
                    </div>
                    <div class="meta-item">
                        <i class="fas fa-check-circle"></i>
                        <span>有效新闻: ${data.effective_news_count || 0} 条</span>
                    </div>
                    <div class="meta-item">
                        <i class="fas fa-user"></i>
                        <span>${identityText}版</span>
                    </div>
                </div>
                <div class="content">
                    <h3 style="margin-top: 0; margin-bottom: 16px; color: var(--primary-color);">📅 本周重点汇总</h3>
                    ${formattedContent}
                </div>
            `;
            reportDiv.classList.add('show');
            
            if (missingDates.length > 0) {
                loadReportDates();
            }
            
        } else {
            showError(reportDiv, "本周暂无足够数据生成周报");
        }
    } catch (err) {
        console.error("获取周报失败:", err);
        showError(reportDiv, err.message || "请求失败，请稍后重试");
    } finally {
        reportBtn.disabled = false;
        reportBtn.innerHTML = '<i class="fas fa-calendar-week"></i><span>查看周报</span>';
    }
}

// ============ 页面加载时初始化 ============
window.onload = function() {
    // 加载对话历史
    loadChatHistory();
    
    // 加载日报日期列表
    loadReportDates();
    
    // 为输入框添加回车键支持
    const questionInput = document.getElementById("question");
    questionInput.addEventListener("keypress", function(e) {
        if (e.key === "Enter") {
            askQuestion();
        }
    });
    
    // 添加输入框焦点效果
    questionInput.addEventListener("focus", function() {
        this.parentElement.style.transform = "scale(1.01)";
    });
    
    questionInput.addEventListener("blur", function() {
        this.parentElement.style.transform = "scale(1)";
    });
};
