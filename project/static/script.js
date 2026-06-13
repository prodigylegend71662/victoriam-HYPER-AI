document.addEventListener('DOMContentLoaded', function () {
  const STORAGE_KEY = 'vhai_sessions';
  const THEME_KEY = 'vhai_theme';
  const SYSTEM_IDENTITY = {
    name: 'Victoriam Hyper AI',
    type: 'Structured research and article-generation engine',
    purpose: 'Convert user queries into clean, encyclopedia-style responses',
    style: 'Neutral, factual, structured paragraphs',
  };

  const queryInput = document.getElementById('queryInput');
  const submitBtn = document.getElementById('submitBtn');
  const messages = document.getElementById('messages');
  const emptyState = document.getElementById('emptyState');
  const chatList = document.getElementById('chatList');
  const newChatBtn = document.getElementById('newChatBtn');
  const toggleSidebar = document.getElementById('toggleSidebar');
  const sidebar = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');
  const sessionTitle = document.getElementById('sessionTitle');
  const sessionMeta = document.getElementById('sessionMeta');
  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const extendedModeBtn = document.getElementById('extendedModeBtn');

  let sessions = [];
  let activeSessionId = null;
  let isSidebarOpen = false;
  let extendedResearch = false;

  function createId() {
    return typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }

  function loadState() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      sessions = saved ? JSON.parse(saved) : [];
    } catch (error) {
      sessions = [];
    }

    extendedResearch = localStorage.getItem('vhai_extended_research') === 'true';

    if (!sessions.length) {
      const session = createSession('New Chat');
      sessions.push(session);
    }

    activeSessionId = sessions[0].id;
    renderSidebar();
    renderSession();
    applyTheme();
    updateExtendedModeButton();
  }

  function saveState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  }

  function setExtendedResearch(value) {
    extendedResearch = value;
    localStorage.setItem('vhai_extended_research', value ? 'true' : 'false');
    updateExtendedModeButton();
    renderSession();
  }

  function updateExtendedModeButton() {
    if (!extendedModeBtn) return;
    extendedModeBtn.classList.toggle('active', extendedResearch);
    extendedModeBtn.innerText = extendedResearch ? 'Extended' : 'Off';
  }

  function toggleExtendedResearch() {
    setExtendedResearch(!extendedResearch);
  }

  function createSession(title = 'New Chat') {
    return {
      id: createId(),
      title,
      createdAt: new Date().toISOString(),
      messages: [],
    };
  }

  function setActiveSession(id) {
    activeSessionId = id;
    renderSidebar();
    renderSession();
    closeSidebar();
  }

  function getActiveSession() {
    return sessions.find((session) => session.id === activeSessionId) || sessions[0];
  }

  function updateSessionTitle(session) {
    if (!session || session.messages.length === 0) {
      session.title = 'New Chat';
      return;
    }
    const firstMessage = session.messages.find((message) => message.role === 'user');
    if (firstMessage) {
      session.title = firstMessage.content.slice(0, 40).trim();
    }
  }

  function appendMessage(role, content) {
    const session = getActiveSession();
    if (!session) return;
    session.messages.push({ role, content, createdAt: new Date().toISOString() });
    if (role === 'user') {
      updateSessionTitle(session);
    }
    saveState();
    renderSession();
  }

  function clearMessages() {
    const session = getActiveSession();
    if (!session) return;
    session.messages = [];
    session.title = 'New Chat';
    saveState();
    renderSession();
  }

  function renderSidebar() {
    chatList.innerHTML = '';
    sessions.forEach((session) => {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = `chat-session${session.id === activeSessionId ? ' active' : ''}`;
      card.innerHTML = `
        <div>
          <div class="chat-session-title">${escapeHtml(session.title)}</div>
          <div class="chat-session-meta">${session.messages.length} messages</div>
        </div>
      `;
      card.addEventListener('click', () => setActiveSession(session.id));
      chatList.appendChild(card);
    });
  }

  function renderSession() {
    const session = getActiveSession();
    if (!session) return;

    sessionTitle.innerText = session.title || 'New Chat';
    sessionMeta.innerText = `${SYSTEM_IDENTITY.type} • ${SYSTEM_IDENTITY.style}${extendedResearch ? ' • Extended research' : ''}`;
    messages.innerHTML = '';

    if (!session.messages.length) {
      emptyState.style.display = 'block';
      return;
    }

    emptyState.style.display = 'none';
    session.messages.forEach((message) => {
      const item = createMessageItem(message);
      messages.appendChild(item);
    });
    scrollToBottom();
  }

  function createMessageItem(message) {
    const li = document.createElement('li');
    li.className = `message ${message.role}`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if (message.role === 'assistant') {
      const copyButton = document.createElement('button');
      copyButton.type = 'button';
      copyButton.className = 'copy-button';
      copyButton.title = 'Copy response';
      copyButton.innerText = 'Copy';
      copyButton.addEventListener('click', () => {
        navigator.clipboard.writeText(message.content).catch(() => {
          copyButton.innerText = 'Failed';
          setTimeout(() => (copyButton.innerText = 'Copy'), 1200);
        });
      });
      bubble.appendChild(copyButton);
    }

    renderMessageContent(message.content, bubble);
    li.appendChild(bubble);
    return li;
  }

  function renderMessageContent(text, container) {
    const blocks = text.replace(/\r/g, '').split(/\n\s*\n/).map((block) => block.trim()).filter(Boolean);

    const parseLineSegments = (line) => {
      const segments = [];
      let remaining = line;
      const headingRegex = /(={2,6})\s*([^=]+?)\s*\1/;

      while (remaining.length) {
        const match = remaining.match(headingRegex);
        if (!match) {
          segments.push({ type: 'text', content: remaining });
          break;
        }

        const index = match.index || 0;
        if (index > 0) {
          segments.push({ type: 'text', content: remaining.slice(0, index) });
        }

        segments.push({
          type: 'header',
          content: match[2].trim(),
          level: Math.min(match[1].length, 6),
        });

        remaining = remaining.slice(index + match[0].length);
      }

      return segments;
    };

    blocks.forEach((block) => {
      const lines = block.split(/\n/);
      let paragraph = null;

      lines.forEach((line) => {
        const segments = parseLineSegments(line);

        segments.forEach((segment) => {
          if (segment.type === 'header') {
            paragraph = null;
            const header = document.createElement(`h${segment.level}`);
            header.innerText = segment.content;
            container.appendChild(header);
            return;
          }

          if (!segment.content.trim()) {
            return;
          }

          if (!paragraph) {
            paragraph = document.createElement('p');
            container.appendChild(paragraph);
          } else {
            paragraph.appendChild(document.createElement('br'));
          }
          paragraph.appendChild(document.createTextNode(segment.content.trim()));
        });
      });
    });
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      messages.scrollTop = messages.scrollHeight;
    });
  }

  function updateEmptyState() {
    const session = getActiveSession();
    emptyState.style.display = session && session.messages.length ? 'none' : 'block';
  }

  async function sendMessage() {
    const text = queryInput.value.trim();
    if (!text) return;

    queryInput.value = '';
    appendMessage('user', text);
    updateEmptyState();

    const placeholderMessage = { role: 'assistant', content: 'Victoriam Hyper AI is thinking...' };
    appendMessage('assistant', placeholderMessage.content);
    renderSession();
    const placeholderIndex = getActiveSession().messages.length - 1;

    submitBtn.disabled = true;
    queryInput.disabled = true;

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, system: { ...SYSTEM_IDENTITY, extendedResearch }, extendedResearch }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const answer = data.result || 'No response returned from the server.';
      const session = getActiveSession();
      if (session && session.messages[placeholderIndex] && session.messages[placeholderIndex].role === 'assistant') {
        session.messages[placeholderIndex].content = answer;
      } else {
        session.messages.push({ role: 'assistant', content: answer, createdAt: new Date().toISOString() });
      }
      saveState();
      renderSession();
    } catch (error) {
      const session = getActiveSession();
      if (session && session.messages[placeholderIndex]) {
        session.messages[placeholderIndex].content = 'Error: could not reach the server. Please try again.';
      }
      saveState();
      renderSession();
    } finally {
      submitBtn.disabled = false;
      queryInput.disabled = false;
      queryInput.focus();
    }
  }

  function createNewChat() {
    const session = createSession();
    sessions.unshift(session);
    setActiveSession(session.id);
    saveState();
  }

  function toggleTheme() {
    const current = localStorage.getItem(THEME_KEY) || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    localStorage.setItem(THEME_KEY, next);
    themeToggleBtn.innerText = next === 'dark' ? '🌙 Dark Mode' : '☀️ Light Mode';
  }

  function applyTheme() {
    const saved = localStorage.getItem(THEME_KEY) || 'dark';
    document.documentElement.dataset.theme = saved;
    themeToggleBtn.innerText = saved === 'dark' ? '🌙 Dark Mode' : '☀️ Light Mode';
  }

  function openSidebar() {
    sidebar.classList.add('open');
    sidebarOverlay.classList.add('visible');
    isSidebarOpen = true;
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('visible');
    isSidebarOpen = false;
  }

  toggleSidebar.addEventListener('click', () => {
    if (isSidebarOpen) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  sidebarOverlay.addEventListener('click', closeSidebar);
  newChatBtn.addEventListener('click', createNewChat);
  themeToggleBtn.addEventListener('click', toggleTheme);
  extendedModeBtn.addEventListener('click', toggleExtendedResearch);
  submitBtn.addEventListener('click', sendMessage);

  queryInput.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  });

  loadState();
});
