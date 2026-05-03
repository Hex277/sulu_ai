// ═══════════════════════════════════════════════
//  STATE
// ═══════════════════════════════════════════════
let sessionUuid = generateUuid();
let statRequests = 0, statFiles = 0, statErrors = 0, statTokens = 0;
let isTyping = false;
let currentConvId = null;
let logCount = 0;

// ─── MOCK DB: PostgreSQL-ready structure ───
// In production: replace with actual pg queries
const db = {
  conversations: [
    {
      id: 'conv-001',
      userId: 'admin-uuid-0001',
      userLabel: 'Admin',
      userType: 'admin',
      title: 'Satış məlumatları 2024',
      preview: 'Q4 satış hesabatı hansı faylda...',
      date: '2025-05-02',
      time: '14:32',
      messages: [
        { role: 'user', content: 'Q4 satış hesabatı hansı faylda?', time: '14:30' },
        { role: 'bot', content: 'sales_reports/ qovluğunda <strong>q4_2024_report.csv</strong> faylı tapıldı. Həmin faylda Oktyabr–Dekabr dövrü üzrə ümumi satış 1,240,500 AZN təşkil edir.', time: '14:30' },
        { role: 'user', content: 'Ən çox satan məhsul hansıdır?', time: '14:32' },
        { role: 'bot', content: 'Məlumatların analizi nəticəsində <strong>Məhsul A</strong> ən çox satılan kateqoriya olaraq müəyyən edildi — 340 ədəd, ümumi gəlir 127,800 AZN.', time: '14:32' }
      ]
    },
    {
      id: 'conv-002',
      userId: 'admin-uuid-0001',
      userLabel: 'Admin',
      userType: 'admin',
      title: 'Müştəri siyahısı sorğusu',
      preview: 'Bakı regionu üzrə müştərilər...',
      date: '2025-05-01',
      time: '10:15',
      messages: [
        { role: 'user', content: 'Bakı regionu üzrə aktiv müştərilər', time: '10:14' },
        { role: 'bot', content: '<strong>customers/baku_active_2024.xlsx</strong> faylında 234 aktiv müştəri məlumatı var. Ən böyük 3 hesab: TechAZ MMC, GreenBuild SC, Prime Logistika.', time: '10:15' }
      ]
    },
    {
      id: 'conv-003',
      userId: 'user-uuid-9f2a',
      userLabel: 'İstifadəçi #9f2a',
      userType: 'user',
      title: 'İnventar yoxlaması',
      preview: 'Stokda olan mallar...',
      date: '2025-05-02',
      time: '09:45',
      messages: [
        { role: 'user', content: 'Stokda olan malların siyahısı', time: '09:44' },
        { role: 'bot', content: '<strong>inventory/stock_current.json</strong> faylına müraciət edildi. Cəmi 89 SKU mövcuddur, 12-si kritik minimum həddindədir.', time: '09:45' }
      ]
    },
    {
      id: 'conv-004',
      userId: 'user-uuid-3c7e',
      userLabel: 'İstifadəçi #3c7e',
      userType: 'user',
      title: 'Hesabat şablonu sualı',
      preview: 'Aylıq hesabat formatı...',
      date: '2025-04-30',
      time: '16:20',
      messages: [
        { role: 'user', content: 'Aylıq hesabat formatı necədir?', time: '16:19' },
        { role: 'bot', content: '<strong>templates/monthly_report_template.docx</strong> faylında standart hesabat şablonu tapıldı. Faylda başlıq, icmal cədvəli, qrafik sahələri və imza bölməsi mövcuddur.', time: '16:20' }
      ]
    }
  ]
};

// ═══════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('sessionUuid').textContent = sessionUuid;
  addLog('info', 'Sistem başladı', 'AI Bot Control Panel v1.0');
  addLog('db', 'PostgreSQL', 'Mock rejim aktivdir — real inteqrasiya üçün pg modulu qoşun');
  addLog('info', 'Session', 'UUID: ' + sessionUuid);
  addLog('info', 'Data qovluğu', 'data/ → 24 fayl tapıldı (mock)');
  renderSidebar();
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
  const empty = document.getElementById('debugEmpty');
  if (empty) empty.style.display = 'none';

  logCount++;
  const now = new Date();
  const time = now.toTimeString().slice(0, 8);
  const logs = document.getElementById('debugLogs');

  const entry = document.createElement('div');
  entry.className = `log-entry log-${type}`;
  entry.innerHTML = `
    <span class="log-time">${time}</span>
    <div class="log-body">
      <span class="log-tag">${label}</span>
      <span class="log-msg">${msg}</span>
    </div>
  `;
  logs.appendChild(entry);
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
  container.innerHTML = '';

  const adminConvs = db.conversations.filter(c => c.userType === 'admin');
  const userConvs = db.conversations.filter(c => c.userType === 'user');

  if (adminConvs.length) {
    const h1 = document.createElement('div');
    h1.className = 'sidebar-section-header';
    h1.innerHTML = `<svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> Mənim Söhbətlərim`;
    container.appendChild(h1);
    adminConvs.forEach(c => container.appendChild(createConvItem(c)));
  }

  if (userConvs.length) {
    const h2 = document.createElement('div');
    h2.className = 'sidebar-section-header';
    h2.innerHTML = `<svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg> İstifadəçi Söhbətləri`;
    container.appendChild(h2);
    userConvs.forEach(c => container.appendChild(createConvItem(c)));
  }
}

function createConvItem(conv) {
  const el = document.createElement('div');
  el.className = 'conv-item' + (currentConvId === conv.id ? ' active' : '');
  el.onclick = () => openConversation(conv.id);

  const initials = conv.userType === 'admin' ? 'AD' : conv.userLabel.slice(-4, -2).toUpperCase() || 'US';
  el.innerHTML = `
    <div class="conv-avatar ${conv.userType === 'admin' ? 'admin-av' : 'user-av'}">${initials}</div>
    <div class="conv-info">
      <div class="conv-title">${conv.title}</div>
      <div class="conv-preview">${conv.preview}</div>
    </div>
    <span class="conv-time">${conv.time}</span>
  `;
  return el;
}

function openConversation(convId) {
  currentConvId = convId;
  const conv = db.conversations.find(c => c.id === convId);
  if (!conv) return;

  document.getElementById('chatTitle').textContent = conv.title;
  document.getElementById('chatSub').textContent = conv.userLabel + ' · ' + conv.date;

  const container = document.getElementById('chatMessages');
  container.innerHTML = '';

  // Detail header banner
  const banner = document.createElement('div');
  banner.className = 'conv-detail-header';
  banner.innerHTML = `
    <svg viewBox="0 0 24 24" onclick="closeBanner()" title="Bağla"><polyline points="15 18 9 12 15 6"/></svg>
    <div class="conv-detail-info">
      <div class="conv-detail-title">${conv.title}</div>
      <div class="conv-detail-sub">${conv.userLabel} · ${conv.date} ${conv.time} · ${conv.messages.length} mesaj</div>
    </div>
  `;
  container.appendChild(banner);

  conv.messages.forEach(m => appendMessage(m.role, m.content, m.time, false));
  renderSidebar();

  addLog('db', 'PG Query', `SELECT * FROM messages WHERE conv_id='${convId}' ORDER BY ts ASC`);
  toggleSidebar();
}

function closeBanner() { startNewChat(); }

// ═══════════════════════════════════════════════
//  CHAT
// ═══════════════════════════════════════════════
function startNewChat() {
  sessionUuid = generateUuid();
  document.getElementById('sessionUuid').textContent = sessionUuid;
  currentConvId = null;
  document.getElementById('chatTitle').textContent = 'Yeni Söhbət';
  document.getElementById('chatSub').textContent = 'AI Bot — Data Search';
  const container = document.getElementById('chatMessages');
  container.innerHTML = `
    <div class="chat-empty-state" id="emptyState">
      <div class="empty-logo">
        <svg viewBox="0 0 24 24" fill="none" stroke="#2D6BE4" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
      </div>
      <div class="empty-title">Nə öyrənmək istəyirsən?</div>
      <div class="empty-sub">AI bot data qovluğundakı faylları oxuyaraq suallarına cavab verəcək.</div>
      <div class="empty-hints">
        <div class="hint-chip" onclick="sendHint(this)">Satış hesabatı hansı faylda?</div>
        <div class="hint-chip" onclick="sendHint(this)">2024-cü il məlumatları</div>
        <div class="hint-chip" onclick="sendHint(this)">Müştəri siyahısı</div>
        <div class="hint-chip" onclick="sendHint(this)">Son əməliyyatlar</div>
      </div>
    </div>
  `;
  statRequests = 0; statFiles = 0; statErrors = 0; statTokens = 0;
  updateStats();
  addLog('info', 'New Session', 'UUID: ' + sessionUuid);
  addLog('db', 'PG Insert', `INSERT INTO sessions (uuid, created_at) VALUES ('${sessionUuid}', NOW())`);
  renderSidebar();
}

function appendMessage(role, content, time, animate = true) {
  const empty = document.getElementById('emptyState');
  if (empty) empty.remove();

  const container = document.getElementById('chatMessages');
  const isUser = role === 'user';
  const t = time || new Date().toTimeString().slice(0, 5);

  const row = document.createElement('div');
  row.className = `msg-row ${isUser ? 'user' : 'bot'}`;
  if (!animate) row.style.animation = 'none';

  row.innerHTML = `
    <div class="msg-avatar ${isUser ? 'user-av' : 'bot-av'}">${isUser ? 'Sən' : 'AI'}</div>
    <div>
      <div class="msg-bubble">${content}</div>
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

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg || isTyping) return;

  input.value = '';
  input.style.height = 'auto';
  isTyping = true;
  statRequests++;
  updateStats();

  appendMessage('user', msg);

  addLog('query', 'Sorğu', msg);
  addLog('info', 'Fayl tarama', 'data/ qovluğu oxunur...');

  showTyping();

  // Simulate processing delay with logs
  await delay(400);
  const mock = getMockResponse(msg);

  if (mock.files.length > 0) {
    mock.files.forEach(f => {
      addLog('file', 'Fayl tapıldı', f);
      statFiles++;
    });
    updateStats();
    await delay(300);
    addLog('info', 'OpenAI', `Mətn hazırlanır — model: gpt-4o`);
    await delay(300);
    const tokens = Math.floor(Math.random() * 400) + 200;
    statTokens += tokens;
    addLog('info', 'Tokens', `Prompt: ~${tokens - 80} · Response: ~80 · Cəmi: ${tokens}`);
  } else {
    addLog('error', 'Fayl tapılmadı', 'Uyğun fayl aşkarlanmadı');
    statErrors++;
    updateStats();
    await delay(300);
    addLog('info', 'OpenAI', 'Ümumi cavab generasiyası');
  }

  await delay(600);
  addLog('db', 'PG Insert', `INSERT INTO messages (session_id, role, content, ts) VALUES (...)`);

  hideTyping();
  appendMessage('bot', mock.response);

  isTyping = false;
  showNotif('Mesaj göndərildi');
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