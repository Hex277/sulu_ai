// ═══════════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════════
let logCount = 0; // Xətanın əsas səbəbi budur
let conversationsCache = [];
let currentConvId = null;
let sessionUuid = generateUuid();
let isTyping = false;

// Statistika üçün:
let statRequests = 0;
let statFiles = 0;
let statErrors = 0;
let statTokens = 0;
// ─── MOCK DB: PostgreSQL-ready structure ───
// In production: replace with actual pg queries
const API_URL = "http://localhost:5000";
// ═══════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', async () => {
  document.getElementById('sessionUuid').textContent = sessionUuid;
  addLog('info', 'Sistem başladı', 'AI Bot Control Panel v1.0');
  await checkServerStatus();
  await loadSessionsFromServer();
  addLog('info', 'Sidebar', `${conversationsCache.length} söhbət tapıldı`);
});
// ═══════════════════════════════════════════════
//  UUID
// ═══════════════════════════════════════════════
function generateUuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

// ═══════════════════════════════════════════════
//  LOG SYSTEM
// ═══════════════════════════════════════════════
function addLog(type, label, msg) {
  // Əgər logCount yuxarıda təyin olunmayıbsa, xəta verməməsi üçün:
  if (typeof logCount === 'undefined') window.logCount = 0;
  window.logCount++;

  // "Hələ loq yoxdur" yazısını gizlət
  const empty = document.getElementById('debugEmpty');
  if (empty) empty.style.display = 'none';

  const now = new Date();
  const time = now.toTimeString().slice(0, 8);
  const logs = document.getElementById('debugLogs');
  if (!logs) return;

  const entry = document.createElement('div');
  // Sənin orijinal klass sistemin: log-entry və log-type
  entry.className = `log-entry log-${type}`;
  
  entry.innerHTML = `
    <span class="log-time">${time}</span>
    <div class="log-body">
      <span class="log-tag">${label}</span>
      <span class="log-msg">${msg}</span>
    </div>
  `;

  logs.appendChild(entry);
  
  // Avtomatik aşağı sürüşdür ki, yeni loqlar görünsün
  logs.scrollTop = logs.scrollHeight;
}
function clearLogs() {
  const logs = document.getElementById('debugLogs');
  logs.innerHTML = `
    <div class="debug-empty" id="debugEmpty">
      <div class="debug-empty-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap: round; stroke-linejoin: round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
      </div>
      <span>Loglar burada görünəcək</span>
    </div>
  `;
  addLog('info', 'Console', 'Log tarixçəsi təmizləndi');
}

// ═══════════════════════════════════════════════
//  SIDEBAR
// ═══════════════════════════════════════════════
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  sidebar.classList.toggle('open');
  overlay.classList.toggle('open');
}
function renderSidebar() {
  const container = document.getElementById('sidebarList');
  if (!container) return;
  
  container.innerHTML = '';

  // Əgər söhbət yoxdursa, mərkəzləşdirilmiş boş vəziyyət mesajı
  if (!conversationsCache || conversationsCache.length === 0) {
    container.innerHTML = `
      <div style="padding:32px 16px; text-align:center; font-size:12px; color:var(--text-3); opacity:0.7;">
        <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" 
             stroke-width="1.5" style="margin-bottom:8px; opacity:0.5;">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
        <div>Hələ heç bir söhbət yoxdur</div>
      </div>`;
    return;
  }

  // Sənin orijinal "Söhbət Tarixçəsi" başlığın və ikonu
  const header = document.createElement('div');
  header.className = 'sidebar-section-header';
  header.innerHTML = `
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
    </svg>
    Söhbət Tarixçəsi
  `;
  container.appendChild(header);

  // Söhbətləri tək-tək əlavə et
  // Ən son söhbətin yuxarıda görünməsi üçün reverse() istifadə edə bilərsən
  const sortedConvs = [...conversationsCache].reverse();
  
  sortedConvs.forEach(conv => {
    container.appendChild(createConvItem(conv));
  });
}
function createConvItem(conv) {
  const el = document.createElement('div');
  
  // FİX: ID-ləri string-ə çevirib müqayisə edirik ki, 'active' klassı itməsin
  const isActive = String(currentConvId) === String(conv.id);
  el.className = 'conv-item' + (isActive ? ' active' : '');
  
  el.onclick = () => openConversation(conv.id);

  // Sənin badge dizaynın
  const countBadge = conv.message_count > 0
    ? `<span style="font-size:10px;background:var(--surface-2);border:1px solid var(--border);
                    border-radius:10px;padding:1px 6px;color:var(--text-3);flex-shrink:0">
         ${conv.message_count}
       </span>`
    : '';

  // Sənin orijinal HTML strukturun
  el.innerHTML = `
    <div class="conv-avatar admin-av">AI</div>
    <div class="conv-info">
      <div class="conv-title">${escapeHtml(conv.title || 'Söhbət')}</div>
      <div class="conv-preview">${escapeHtml(conv.preview || '…')}</div>
    </div>
    ${countBadge}
  `;
  
  return el;
}
async function openConversation(sessionId) {
  if (!sessionId) return;
  
  currentConvId = sessionId;
  sessionUuid = sessionId; // AI-yə göndərilən ID artıq köhnə ID olur
  document.getElementById('sessionUuid').textContent = sessionId;

  const container = document.getElementById('chatMessages');
  container.innerHTML = '<div class="loading-status">Mesajlar bərpa olunur...</div>';

  // Sidebar-da başlığı yenilə
  const conv = conversationsCache.find(c => String(c.id) === String(sessionId));
  if (conv) {
    document.getElementById('chatTitle').textContent = conv.title || 'Söhbət';
  }

  try {
    const messages = await fetchSessionMessages(sessionId);
    container.innerHTML = ''; // Loader-i sil

    if (messages.length === 0) {
      appendMessage('bot', 'Bu söhbət boşdur.');
    } else {
      messages.forEach(m => {
        const role = m.role === 'assistant' ? 'bot' : m.role;
        appendMessage(role, m.content, null, false);
      });
    }
    addLog('success', 'PostgreSQL', `Sessiya ${sessionId} yükləndi.`);
  } catch (err) {
    addLog('error', 'History', err.message);
    container.innerHTML = `<div class="error-msg">Xəta: ${err.message}</div>`;
  }

  renderSidebar(); // Active klassını yeniləmək üçün
}
function closeBanner() { startNewChat(); }

// ═══════════════════════════════════════════════
//  CHAT
// ═══════════════════════════════════════════════
function startNewChat() {
    sessionUuid = generateUuid();
    currentConvId = null;
    
    // UI Elementlərini tapırıq
    const uuidEl = document.getElementById('sessionUuid');
    const titleEl = document.getElementById('chatTitle');
    const subEl = document.getElementById('chatSub');
    const container = document.getElementById('chatMessages');

    if (uuidEl) uuidEl.textContent = sessionUuid;
    if (titleEl) titleEl.textContent = 'Yeni Söhbət';
    if (subEl) subEl.textContent = 'AI Bot — Data Search';

    if (container) {
        container.innerHTML = `
            <div class="chat-empty-state" id="emptyState">
                <div class="empty-logo">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#2D6BE4" stroke-width="1.5"
                         stroke-linecap="round" stroke-linejoin="round" style="width:48px; height:48px;">
                        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
                    </svg>
                </div>
                <div class="empty-title">Nə öyrənmək istəyirsən?</div>
                <div class="empty-sub">AI bot data qovluğundakı faylları oxuyaraq suallarına cavab verəcək.</div>
                <div class="empty-hints">
                    <div class="hint-chip" onclick="sendHint(this)">Elvin haqqında məlumat ver</div>
                    <div class="hint-chip" onclick="sendHint(this)">Salam</div>
                    <div class="hint-chip" onclick="sendHint(this)">Sistemdə neçə fayl var?</div>
                </div>
            </div>
        `;
    }

    // Statistikanı sıfırla
    statRequests = 0; statFiles = 0; statErrors = 0; statTokens = 0;
    if (typeof updateStats === 'function') updateStats();

    addLog('info', 'New Session', 'UUID: ' + sessionUuid);
    
    // Sidebar-ı yenilə (active class-ları təmizləmək üçün)
    if (typeof renderSidebar === 'function') renderSidebar();
}
 
function appendMessage(role, content, time, animate = true) {
  const empty = document.getElementById('emptyState');
  if (empty) empty.remove();

  const container = document.getElementById('chatMessages');
  const isUser = role === 'user';
  const t = time || new Date().toTimeString().slice(0, 5);

  // Markdown-u HTML-ə çeviririk (Yalnız botun mesajı üçün)
  // Əgər rol botdursa çevir, user-dirsə olduğu kimi saxla
  const formattedContent = isUser ? content : marked.parse(content);

  const row = document.createElement('div');
  row.className = `msg-row ${isUser ? 'user' : 'bot'}`;
  if (!animate) row.style.animation = 'none';

  row.innerHTML = `
    <div class="msg-avatar ${isUser ? 'user-av' : 'bot-av'}">${isUser ? 'Sən' : 'AI'}</div>
    <div>
      <div class="msg-bubble">${formattedContent}</div>
      <div class="msg-time">${t}</div>
    </div>
  `;
  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

function showTyping() {
  const container = document.getElementById('chatMessages');
  const t = document.createElement('div');
  t.className = 'msg-row bot';
  t.id = 'typingRow';
  t.innerHTML = `
    <div class="msg-avatar bot-av">AI</div>
    <div class="msg-bubble">
      <div class="typing-indicator">
        <div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>
      </div>
    </div>
  `;
  container.appendChild(t);
  container.scrollTop = container.scrollHeight;
}

function hideTyping() {
  const t = document.getElementById('typingRow');
  if (t) t.remove();
}

function sendHint(el) {
  document.getElementById('chatInput').value = el.textContent;
  sendMessage();
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

// ─── MOCK AI RESPONSE SIMULATION ───
const mockResponses = [
  {
    keywords: ['satış', 'hesabat', 'report'],
    files: ['sales_reports/q4_2024_report.csv', 'sales_reports/monthly_2024.xlsx'],
    response: 'data/sales_reports/ qovluğunda <strong>q4_2024_report.csv</strong> faylı tapıldı. Q4 üzrə ümumi satış 1,240,500 AZN-dir. Ətraflı analiz üçün başqa sual ola bilər?'
  },
  {
    keywords: ['müştəri', 'customer'],
    files: ['customers/baku_active_2024.xlsx'],
    response: '<strong>customers/baku_active_2024.xlsx</strong> faylında 234 aktiv müştəri məlumatı mövcuddur. Regiona görə filtrləmək istəyirsənsə bildirə bilərsən.'
  },
  {
    keywords: ['inventar', 'stok', 'stock'],
    files: ['inventory/stock_current.json'],
    response: '<strong>inventory/stock_current.json</strong> faylı oxundu. 89 SKU arasında 12-si kritik minimum həddindədir. Kritik siyahısını görmək istəyirsən?'
  },
  {
    keywords: ['şablon', 'template', 'format'],
    files: ['templates/monthly_report_template.docx'],
    response: '<strong>templates/monthly_report_template.docx</strong> şablon faylı tapıldı. Faylda başlıq, icmal cədvəli, qrafik bölmələri mövcuddur.'
  },
  {
    keywords: ['2024', 'il', 'year'],
    files: ['data_2024/annual_summary.json', 'data_2024/q1.csv', 'data_2024/q2.csv'],
    response: '2024-cü il üzrə <strong>data_2024/</strong> qovluğunda 8 fayl tapıldı. İllik xülasə: ümumi gəlir 4.8M AZN, müştəri sayı 1,240-a çatıb.'
  }
];

function getMockResponse(query) {
  const q = query.toLowerCase();
  for (const r of mockResponses) {
    if (r.keywords.some(k => q.includes(k))) return r;
  }
  return {
    files: [],
    response: 'data/ qovluğundakı heç bir faylda bu sorğuya tam uyğun məlumat tapılmadı. Sorğunu dəqiqləşdirsən daha yaxşı nəticə ola bilər.'
  };
}

async function loadSessionsFromServer() {
  try {
    const res = await fetch(`${API_URL}/api/sessions`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    conversationsCache = data.sessions || [];
    renderSidebar();
  } catch (err) {
    addLog('error', 'Sidebar', `Session-lar yüklənmədi: ${err.message}`);
  }
}
async function fetchSessionMessages(sessionId) {
  const res = await fetch(`${API_URL}/api/history/${sessionId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return data.messages || [];
}
async function checkServerStatus() {
  try {
    const res = await fetch(`${API_URL}/api/status`);
    const data = await res.json();
    if (data.status === 'ok') {
      addLog('info', 'Server', `Bağlı — ${data.file_count} fayl tapıldı`);
      addLog('db', 'PostgreSQL', data.postgres ? 'Aktiv' : 'Mock rejim');
      document.getElementById('statusDot').style.background = '#22C55E';
    }
  } catch {
    addLog('error', 'Server', 'Flask serverlə bağlantı yoxdur — python server.py işləyirmi?');
    document.getElementById('statusDot').style.background = '#F87171';
  }
}
async function sendMessage() {
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg || isTyping) return;

  input.value = '';
  isTyping = true;
  statRequests++;
  updateStats();
  appendMessage('user', msg);
  showTyping();

  try {
    const response = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionUuid, // Mövcud və ya yeni UUID
        message: msg
      })
    });

    const data = await response.json();
    hideTyping();

    if (data.error) throw new Error(data.error);

    // Botun cavabını göstər
    appendMessage('bot', data.answer);

    // SERVERDƏN GƏLƏN ID-ni YADDA SAXLA
    // Bu yeni bir söhbətdirsə, server bizə session_id qaytarmalıdır
    if (data.session_id) {
        sessionUuid = data.session_id;
        currentConvId = data.session_id;
    }

    // Statistika və loqlar
    if (data.tokens) statTokens += data.tokens;
    updateStats();

    // SİDEBAR-I YENİLƏ (Mütləq!)
    await loadSessionsFromServer(); 

  } catch (err) {
    hideTyping();
    addLog('error', 'Chat Xətası', err.message);
    appendMessage('bot', "Xəta baş verdi: " + err.message);
  } finally {
    isTyping = false;
  }
}

// ═══════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════
function updateStats() {
  document.getElementById('statRequests').textContent = statRequests;
  document.getElementById('statFiles').textContent = statFiles;
  document.getElementById('statErrors').textContent = statErrors;
  document.getElementById('statTokens').textContent = statTokens > 999 ? (statTokens / 1000).toFixed(1) + 'k' : statTokens;
}

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

function showNotif(msg) {
  const n = document.getElementById('notif');
  n.textContent = msg;
  n.classList.add('show');
  setTimeout(() => n.classList.remove('show'), 1800);
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
 