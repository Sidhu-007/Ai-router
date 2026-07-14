// Global State
let sessions = [];
let currentSessionId = null;
let currentUser = null; // Contains { email, uid }
let isSignUpMode = false;
let pendingFiles = [];
let activeReader = null;

document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const promptInput = document.getElementById('prompt-input');
    const newChatBtn = document.getElementById('new-chat-btn');
    const attachBtn = document.getElementById('attach-btn');
    const fileInput = document.getElementById('file-input');
    const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
    const sidebar = document.querySelector('.sidebar');
    const chatFeed = document.getElementById('chat-feed');
    const attachmentPreview = document.getElementById('attachment-preview');

    // Check if user session already exists in localStorage
    const savedUser = localStorage.getItem("router_user");
    if (savedUser) {
        try {
            currentUser = JSON.parse(savedUser);
        } catch (e) {
            currentUser = null;
        }
    }

    // Bind General Events
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Cancel streaming if active
        if (activeReader) {
            try {
                await activeReader.cancel();
            } catch (err) {
                console.error("Stream cancellation error:", err);
            }
            activeReader = null;
            setInputState(true);
            return;
        }
        
        let promptText = promptInput.value.trim();
        if (!promptText && pendingFiles.length > 0) {
            const names = pendingFiles.map(f => f.name).join(', ');
            promptText = `Explain these files: [Attachments: ${names}]`;
        }
        if (!promptText) return;

        promptInput.value = '';
        await processPrompt(promptText);
    });

    toggleSidebarBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
    });

    // Tap to dismiss sidebar overlay on mobile
    chatFeed.addEventListener('click', () => {
        if (window.innerWidth <= 768 && !sidebar.classList.contains('collapsed')) {
            sidebar.classList.add('collapsed');
        }
    });

    attachBtn.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            for (let i = 0; i < fileInput.files.length; i++) {
                const file = fileInput.files[i];
                if (!pendingFiles.some(f => f.name === file.name && f.size === file.size)) {
                    pendingFiles.push(file);
                }
            }
            renderAttachmentPreview();
            fileInput.value = '';
        }
    });

    newChatBtn.addEventListener('click', () => {
        createSession();
        // Auto-close sidebar on mobile after starting new chat
        if (window.innerWidth <= 768) {
            sidebar.classList.add('collapsed');
        }
    });

    // Initialize Auth UI & Load Data
    setupAuthUI();
    loadCatalog();
});

// --- Auth UI Management ---
function setupAuthUI() {
    const authModal = document.getElementById('auth-modal');
    const closeAuthBtn = document.getElementById('close-auth-btn');
    const authForm = document.getElementById('auth-form');
    const authToggleLink = document.getElementById('auth-toggle-link');
    const authTitle = document.getElementById('auth-title');
    const authSubmitBtn = document.getElementById('auth-submit-btn');

    // Header Buttons Triggers
    document.getElementById('header-login-btn').addEventListener('click', () => {
        openAuthModal(false);
    });
    document.getElementById('header-signup-btn').addEventListener('click', () => {
        openAuthModal(true);
    });

    closeAuthBtn.addEventListener('click', () => {
        authModal.style.display = 'none';
    });

    authToggleLink.addEventListener('click', () => {
        isSignUpMode = !isSignUpMode;
        authTitle.innerText = isSignUpMode ? "Sign Up" : "Sign In";
        authSubmitBtn.innerText = isSignUpMode ? "Sign Up" : "Sign In";
        authToggleLink.innerText = isSignUpMode ? "Sign In" : "Sign Up";
        document.querySelector('.auth-toggle-text').innerHTML = isSignUpMode
            ? `Already have an account? <span id="auth-toggle-link" style="color:#ffffff;cursor:pointer;font-weight:600;text-decoration:underline;">Sign In</span>`
            : `Don't have an account? <span id="auth-toggle-link" style="color:#ffffff;cursor:pointer;font-weight:600;text-decoration:underline;">Sign Up</span>`;

        // Re-bind click listener on dynamic span update
        document.getElementById('auth-toggle-link').addEventListener('click', () => {
            authToggleLink.click();
        });
    });

    authForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('auth-email').value.trim();
        const password = document.getElementById('auth-password').value;

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (!res.ok) {
                throw new Error(await res.text());
            }

            const user = await res.json();
            currentUser = user;
            localStorage.setItem("router_user", JSON.stringify(currentUser));

            authModal.style.display = 'none';
            authForm.reset();

            updateProfileState();
            await loadSessionsFromBackend();
        } catch (error) {
            alert("Auth failed: " + error.message);
        }
    });

    updateProfileState();

    if (currentUser) {
        loadSessionsFromBackend();
    } else {
        loadSessionsFromLocalStorage();
    }
}

function openAuthModal(isSignUp) {
    const authModal = document.getElementById('auth-modal');
    const authTitle = document.getElementById('auth-title');
    const authSubmitBtn = document.getElementById('auth-submit-btn');
    const authToggleLink = document.getElementById('auth-toggle-link');
    const sidebar = document.querySelector('.sidebar');

    isSignUpMode = isSignUp;
    authTitle.innerText = isSignUp ? "Sign Up" : "Sign In";
    authSubmitBtn.innerText = isSignUp ? "Sign Up" : "Sign In";
    authToggleLink.innerText = isSignUp ? "Sign In" : "Sign Up";
    document.querySelector('.auth-toggle-text').innerHTML = isSignUp
        ? `Already have an account? <span id="auth-toggle-link" style="color:#ffffff;cursor:pointer;font-weight:600;text-decoration:underline;">Sign In</span>`
        : `Don't have an account? <span id="auth-toggle-link" style="color:#ffffff;cursor:pointer;font-weight:600;text-decoration:underline;">Sign Up</span>`;

    authModal.style.display = 'flex';

    // Auto-close sidebar on mobile when launching auth modals
    if (window.innerWidth <= 768) {
        sidebar.classList.add('collapsed');
    }
}

function updateProfileState() {
    const profileContainer = document.getElementById('user-profile-section');
    const headerAuthContainer = document.getElementById('header-auth-buttons');

    if (currentUser) {
        profileContainer.innerHTML = `
            <div class="profile-card">
                <div class="profile-details">
                    <span class="profile-name">${currentUser.email}</span>
                    <span class="profile-status">Signed In (Cloud Sync)</span>
                </div>
                <button id="auth-signout-btn" class="auth-action-btn">Logout</button>
            </div>
        `;
        document.getElementById('auth-signout-btn').addEventListener('click', () => {
            currentUser = null;
            localStorage.removeItem("router_user");
            updateProfileState();
            loadSessionsFromLocalStorage();
        });
        headerAuthContainer.style.display = 'none';
    } else {
        profileContainer.innerHTML = `
            <div class="sidebar-promo-card">
                <span class="sidebar-promo-title">Get responses tailored to you</span>
                <span class="sidebar-promo-desc">Log in to get answers based on saved chats, plus upload files.</span>
                <button id="sidebar-login-btn" class="sidebar-login-btn">Log in</button>
            </div>
        `;
        document.getElementById('sidebar-login-btn').addEventListener('click', () => {
            openAuthModal(false);
        });
        headerAuthContainer.style.display = 'flex';
    }
}

// --- Session History Storage & Sync ---
async function saveSessionsState() {
    if (currentUser) {
        try {
            await fetch('/api/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: currentUser.email,
                    sessions: sessions
                })
            });
        } catch (e) {
            console.error("Failed to sync to Firestore:", e);
        }
    } else {
        localStorage.setItem("router_sessions", JSON.stringify(sessions));
    }
}

async function loadSessionsFromBackend() {
    if (!currentUser) return;

    try {
        const res = await fetch(`/api/sessions?email=${encodeURIComponent(currentUser.email)}`);
        if (!res.ok) throw new Error("Failed to fetch cloud sessions");

        sessions = await res.json();

        if (sessions.length === 0) {
            createSession();
        } else {
            currentSessionId = sessions[0].id;
            loadSession(currentSessionId);
        }
    } catch (e) {
        console.error("Failed to load from cloud, falling back to local storage:", e);
        loadSessionsFromLocalStorage();
    }
}

function loadSessionsFromLocalStorage() {
    try {
        const stored = localStorage.getItem("router_sessions");
        if (stored) {
            sessions = JSON.parse(stored);
        } else {
            sessions = [];
        }
    } catch (e) {
        sessions = [];
    }

    if (sessions.length === 0) {
        createSession();
    } else {
        currentSessionId = sessions[0].id;
        loadSession(currentSessionId);
    }
}

// --- Chat Actions ---
function createSession() {
    const id = Date.now().toString();
    const newSession = {
        id: id,
        title: 'New Chat',
        history: [],
        stats: { requests: 0, success_rate: 1.0, cost: 0.0 }
    };
    sessions.unshift(newSession);
    currentSessionId = id;
    saveSessionsState();
    loadSession(id);
}

function loadSession(id) {
    const sidebar = document.querySelector('.sidebar');
    currentSessionId = id;
    const session = sessions.find(s => s.id === id);
    if (!session) return;

    const chatFeed = document.getElementById('chat-feed');
    chatFeed.innerHTML = '';

    if (session.history.length === 0) {
        chatFeed.innerHTML = `
            <div class="message assistant-message">
                <div class="bubble">
                    Hi there! 👋 How can I help you today?
                </div>
            </div>
        `;
    } else {
        session.history.forEach(msg => {
            appendMessageToFeed(msg.content, msg.role, msg.meta);
        });
    }

    updateSidebarStats(session.stats);
    renderSessionsList();

    // Auto-close sidebar drawer on mobile after switching sessions
    if (window.innerWidth <= 768) {
        sidebar.classList.add('collapsed');
    }
}

// Custom touch/scroll handler for bottom feed alignment
function scrollToBottom() {
    const chatFeed = document.getElementById('chat-feed');
    chatFeed.scrollTop = chatFeed.scrollHeight;
}

function deleteSession(id, event) {
    if (event) event.stopPropagation(); // Prevent loading session on delete click

    const index = sessions.findIndex(s => s.id === id);
    if (index === -1) return;

    sessions.splice(index, 1);

    if (sessions.length === 0) {
        createSession();
    } else {
        if (currentSessionId === id) {
            currentSessionId = sessions[0].id;
            loadSession(currentSessionId);
        } else {
            renderSessionsList();
        }
    }
    saveSessionsState();
}

function renderSessionsList() {
    const list = document.getElementById('sessions-list');
    if (!list) return;
    list.innerHTML = '';
    sessions.forEach(s => {
        const li = document.createElement('li');
        li.className = `session-item ${s.id === currentSessionId ? 'active' : ''}`;
        li.innerHTML = `
            <svg class="session-icon" viewBox="0 0 24 24" width="16" height="16">
                <path fill="currentColor" d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 9h12v2H6V9zm8 5H6v-2h8v2zm4-6H6V6h12v2z"/>
            </svg>
            <span class="session-title">${s.title}</span>
            <button class="delete-session-btn" title="Delete conversation">
                <svg viewBox="0 0 24 24" width="14" height="14">
                    <path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                </svg>
            </button>
        `;

        li.addEventListener('click', () => {
            loadSession(s.id);
        });

        li.querySelector('.delete-session-btn').addEventListener('click', (e) => {
            deleteSession(s.id, e);
        });

        list.appendChild(li);
    });
}

async function processPrompt(prompt) {
    const session = sessions.find(s => s.id === currentSessionId);
    if (!session) return;

    const filesToParse = [...pendingFiles];
    pendingFiles = [];
    renderAttachmentPreview();
    
    // Disable input fields while generating
    setInputState(false);

    let userDisplayPrompt = prompt;
    if (filesToParse.length > 0) {
        const namesStr = filesToParse.map(f => f.name).join(', ');
        userDisplayPrompt = `${prompt} [Attachments: ${namesStr}]`;
    }
    appendMessageToFeed(userDisplayPrompt, 'user');

    const typingIndicator = appendTypingIndicator();
    scrollToBottom();

    let apiPrompt = prompt;

    // Parse all files in parallel
    if (filesToParse.length > 0) {
        try {
            const parsedResults = await Promise.all(filesToParse.map(async (file) => {
                const formData = new FormData();
                formData.append('file', file);
                
                const parseRes = await fetch('/api/parse-file', {
                    method: 'POST',
                    body: formData
                });
                
                if (!parseRes.ok) {
                    throw new Error(`Failed to parse ${file.name}: ${await parseRes.text()}`);
                }
                
                const parseData = await parseRes.json();
                return { name: file.name, text: parseData.content };
            }));
            
            parsedResults.forEach((res) => {
                apiPrompt += `\n\n[File Attachment: ${res.name}]\n${res.text}`;
            });
        } catch (parseErr) {
            console.error("Failed to parse files:", parseErr);
            typingIndicator.remove();
            appendMessageToFeed(`[Error parsing files: ${parseErr.message || 'File extraction failed'}]`, 'assistant');
            setInputState(true);
            scrollToBottom();
            return;
        }
    }

    const historyForAPI = session.history.map(h => ({ role: h.role, content: h.content }));

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: apiPrompt,
                history: historyForAPI
            })
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        typingIndicator.remove();

        const chatFeed = document.getElementById('chat-feed');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message assistant-message';
        
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        messageDiv.appendChild(bubble);
        chatFeed.appendChild(messageDiv);

        // Blinking streaming cursor
        const cursorSpan = document.createElement('span');
        cursorSpan.className = 'streaming-cursor';
        bubble.appendChild(cursorSpan);
        scrollToBottom();

        const reader = response.body.getReader();
        activeReader = reader; // Store reference globally for cancellation
        const decoder = new TextDecoder();
        let finished = false;

        let accumulatedResponse = "";
        let meta = {
            model: "DeepSeek V4 Flash",
            domain: "General Chat",
            difficulty: "Easy",
            context: "Medium",
            cost: 0.0,
            latency: 0.0
        };

        while (!finished) {
            const { value, done } = await reader.read();
            if (done) {
                finished = true;
                break;
            }

            const chunkStr = decoder.decode(value, { stream: true });
            const lines = chunkStr.split('\n');

            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed.startsWith('data: ')) {
                    try {
                        const eventData = JSON.parse(trimmed.substring(6));

                        if (eventData.type === 'meta') {
                            meta.model = eventData.model;
                            meta.domain = eventData.domain;
                            meta.difficulty = eventData.difficulty;
                            meta.context = eventData.context;
                        } else if (eventData.type === 'token') {
                            accumulatedResponse += eventData.text;
                            
                            // Only auto-scroll if the user is already near the bottom (respect manual scroll up)
                            const isAtBottom = (chatFeed.scrollHeight - chatFeed.scrollTop - chatFeed.clientHeight) <= 80;
                            
                            bubble.innerHTML = renderMarkdownAndLaTeX(accumulatedResponse);
                            
                            const cur = document.createElement('span');
                            cur.className = 'streaming-cursor';
                            bubble.appendChild(cur);
                            
                            if (isAtBottom) {
                                scrollToBottom();
                            }
                        } else if (eventData.type === 'stats') {
                            meta.cost = eventData.cost;
                            meta.latency = eventData.latency;
                        } else if (eventData.type === 'error') {
                            accumulatedResponse += `\n[Error: ${eventData.text}]`;
                            bubble.innerHTML = renderMarkdownAndLaTeX(accumulatedResponse);
                            scrollToBottom();
                        }
                    } catch (e) {
                        // ignore parse errors
                    }
                }
            }
        }

        const wasCancelled = (activeReader === null);
        activeReader = null;
        setInputState(true);

        // Final clean render
        bubble.innerHTML = renderMarkdownAndLaTeX(accumulatedResponse + (wasCancelled ? " *[Generation Stopped]*" : ""));
        scrollToBottom();

        // Render diagnostics panel
        renderAccordionForMessage(messageDiv, meta);

        if (session.title === 'New Chat') {
            session.title = prompt.length > 22 ? prompt.substring(0, 22) + '...' : prompt;
        }
        session.history.push({ role: 'user', content: userDisplayPrompt });
        session.history.push({ role: 'assistant', content: accumulatedResponse + (wasCancelled ? " [Generation Stopped]" : ""), meta: meta });

        session.stats.requests += 1;
        session.stats.cost += meta.cost;

        updateSidebarStats(session.stats);
        renderSessionsList();
        saveSessionsState();

    } catch (err) {
        activeReader = null;
        setInputState(true);
        typingIndicator.remove();
        appendMessageToFeed(`[Error: ${err.message || 'Failed to process request'}]`, 'assistant');
    }

    scrollToBottom();
}

function appendMessageToFeed(text, sender, meta = null) {
    const chatFeed = document.getElementById('chat-feed');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = renderMarkdownAndLaTeX(text);
    messageDiv.appendChild(bubble);

    if (meta) {
        renderAccordionForMessage(messageDiv, meta);
    }

    chatFeed.appendChild(messageDiv);
}

function renderAccordionForMessage(messageDiv, meta) {
    if (!meta) return;

    const accordion = document.createElement('div');
    accordion.className = 'routing-metadata';

    const header = document.createElement('div');
    header.className = 'routing-header';
    header.innerHTML = `
        <span><strong>Routing Diagnostics</strong> (${meta.model})</span>
        <span class="chevron">▼</span>
    `;

    const details = document.createElement('div');
    details.className = 'routing-details';
    details.style.display = 'none';
    details.innerHTML = `
        <div class="routing-pill">
            <span class="pill-label">Domain</span>
            <span class="pill-value">${meta.domain}</span>
        </div>
        <div class="routing-pill">
            <span class="pill-label">Difficulty</span>
            <span class="pill-value">${meta.difficulty}</span>
        </div>
        <div class="routing-pill">
            <span class="pill-label">Context</span>
            <span class="pill-value">${meta.context}</span>
        </div>
        <div class="routing-pill">
            <span class="pill-label">Selected Model</span>
            <span class="pill-value model-highlight">${meta.model}</span>
        </div>
        <div class="routing-pill">
            <span class="pill-label">Transaction Cost</span>
            <span class="pill-value cost-highlight">$${meta.cost.toFixed(6)}</span>
        </div>
        <div class="routing-pill">
            <span class="pill-label">API Latency</span>
            <span class="pill-value">${meta.latency.toFixed(2)}s</span>
        </div>
    `;

    header.addEventListener('click', () => {
        const isVisible = details.style.display === 'grid';
        details.style.display = isVisible ? 'none' : 'grid';
        header.querySelector('.chevron').innerText = isVisible ? '▼' : '▲';
    });

    accordion.appendChild(header);
    accordion.appendChild(details);
    messageDiv.appendChild(accordion);
}


function appendTypingIndicator() {
    const chatFeed = document.getElementById('chat-feed');
    const indicatorDiv = document.createElement('div');
    indicatorDiv.className = 'message assistant-message typing-container';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    const typing = document.createElement('div');
    typing.className = 'typing-indicator';
    typing.innerHTML = `
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    `;

    bubble.appendChild(typing);
    indicatorDiv.appendChild(bubble);
    chatFeed.appendChild(indicatorDiv);
    return indicatorDiv;
}

function updateSidebarStats(stats) {
    const r = document.getElementById('stat-requests');
    const s = document.getElementById('stat-success');
    const c = document.getElementById('stat-cost');
    if (r) r.innerText = stats.requests;
    if (s) s.innerText = stats.requests > 0 ? '100%' : '0%';
    if (c) c.innerText = `$${stats.cost.toFixed(4)}`;
}

async function loadCatalog() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        const catalogList = document.getElementById('catalog-list');
        if (catalogList && catalogList.children.length === 0 && data.model_costs) {
            Object.entries(data.model_costs).forEach(([name, cost]) => {
                const li = document.createElement('li');
                li.className = 'catalog-item';
                li.innerHTML = `
                    <span class="catalog-name">${name}</span>
                    <span class="catalog-cost">$${cost.toFixed(2)}/1M</span>
                `;
                catalogList.appendChild(li);
            });
        }
    } catch (err) {
        console.error('Failed to load catalog:', err);
    }
}

function useSuggestion(text) {
    document.getElementById('prompt-input').value = text;
    document.getElementById('chat-form').dispatchEvent(new Event('submit'));
}

// --- Markdown and LaTeX Renderer ---
function renderMarkdownAndLaTeX(text) {
    if (!text) return '';

    // Configure marked to handle soft line breaks as <br>
    if (typeof marked !== 'undefined' && typeof marked.use === 'function') {
        marked.use({
            breaks: true,
            gfm: true
        });
    }

    const mathBlocks = [];
    let processedText = text;

    // Replace display math block markers \[ ... \]
    processedText = processedText.replace(/\\\[([\s\S]*?)\\\]/g, (match, p1) => {
        const placeholder = `MATHDISPINDEX${mathBlocks.length}`;
        mathBlocks.push({ id: placeholder, type: 'display', tex: p1 });
        return placeholder;
    });

    // Replace display math block markers $$ ... $$
    processedText = processedText.replace(/\$\$([\s\S]*?)\$\$/g, (match, p1) => {
        const placeholder = `MATHDISPINDEX${mathBlocks.length}`;
        mathBlocks.push({ id: placeholder, type: 'display', tex: p1 });
        return placeholder;
    });

    // Replace inline math markers \( ... \)
    processedText = processedText.replace(/\\\(([\s\S]*?)\\\)/g, (match, p1) => {
        const placeholder = `MATHINLINDEX${mathBlocks.length}`;
        mathBlocks.push({ id: placeholder, type: 'inline', tex: p1 });
        return placeholder;
    });

    // Replace inline math markers $ ... $ (ensuring it's not a multiline text match)
    processedText = processedText.replace(/\$([^\$\n]+?)\$/g, (match, p1) => {
        const placeholder = `MATHINLINDEX${mathBlocks.length}`;
        mathBlocks.push({ id: placeholder, type: 'inline', tex: p1 });
        return placeholder;
    });

    // Render the markdown structure
    let renderedHtml = "";
    try {
        renderedHtml = marked.parse(processedText);
    } catch (e) {
        console.error("Marked parsing error:", e);
        renderedHtml = processedText;
    }

    // Substitute back with typeset KaTeX HTML
    for (const block of mathBlocks) {
        try {
            const isDisplay = block.type === 'display';
            const mathHtml = katex.renderToString(block.tex, {
                displayMode: isDisplay,
                throwOnError: false
            });
            renderedHtml = renderedHtml.replace(block.id, mathHtml);
        } catch (err) {
            console.error("KaTeX rendering error:", err);
            const originalMath = block.type === 'display' ? `\\[${block.tex}\\]` : `\\(${block.tex}\\)`;
            renderedHtml = renderedHtml.replace(block.id, originalMath);
        }
    }

    return renderedHtml;
}

// --- Multi-File Upload & Input Disabling Helpers ---
function renderAttachmentPreview() {
    const previewContainer = document.getElementById('attachment-preview');
    const promptInput = document.getElementById('prompt-input');
    if (!previewContainer) return;
    
    previewContainer.innerHTML = '';
    
    if (pendingFiles.length === 0) {
        previewContainer.style.display = 'none';
        if (promptInput) promptInput.placeholder = "Type a prompt or attach a file to route...";
        return;
    }
    
    previewContainer.style.display = 'flex';
    if (promptInput) promptInput.placeholder = `Explain these files or type a prompt...`;
    
    pendingFiles.forEach((file, index) => {
        const chip = document.createElement('div');
        chip.className = 'attachment-chip';
        chip.innerHTML = `
            <svg class="file-icon" viewBox="0 0 24 24" width="16" height="16">
                <path fill="currentColor" d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
            </svg>
            <span class="file-name-text" style="max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${file.name}</span>
            <button type="button" class="remove-chip-btn" data-index="${index}">&times;</button>
        `;
        
        chip.querySelector('.remove-chip-btn').addEventListener('click', (e) => {
            const idx = parseInt(e.target.getAttribute('data-index'));
            pendingFiles.splice(idx, 1);
            renderAttachmentPreview();
        });
        
        previewContainer.appendChild(chip);
    });
}

function setInputState(isEnabled) {
    const promptInput = document.getElementById('prompt-input');
    const attachBtn = document.getElementById('attach-btn');
    const sendBtn = document.querySelector('.send-btn');
    
    if (promptInput) promptInput.disabled = !isEnabled;
    if (attachBtn) attachBtn.disabled = !isEnabled;
    
    if (sendBtn) {
        if (!isEnabled) {
            sendBtn.classList.add('streaming');
            sendBtn.innerHTML = `
                <svg viewBox="0 0 24 24" width="18" height="18" style="margin: 3px;">
                    <rect x="4" y="4" width="16" height="16" fill="currentColor"/>
                </svg>
            `;
            sendBtn.title = "Stop generating";
        } else {
            sendBtn.classList.remove('streaming');
            sendBtn.innerHTML = `
                <svg viewBox="0 0 24 24" width="24" height="24">
                    <path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
            `;
            sendBtn.title = "Send message";
        }
    }
}
