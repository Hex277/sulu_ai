
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
  addLog('info', 'Server', 'Flask serverə göndərilir...');
  showTyping();

  try {
    // Flask serverə sorğu göndər
    const response = await fetch(`${API_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionUuid,
        message: msg
      })
    });

    if (!response.ok) {
      throw new Error(`Server xətası: ${response.status}`);
    }

    const data = await response.json();

    // Serverdən gələn logları debug panelinə əlavə et
    if (data.logs) {
      for (const log of data.logs) {
        addLog(log.type, log.label, log.msg);
        if (log.type === 'file') statFiles++;
        if (log.type === 'error') statErrors++;
        await delay(80); // loglar bir-bir görünsün
      }
    }

    if (data.tokens) {
      statTokens += data.tokens;
    }

    updateStats();
    hideTyping();
    appendMessage('bot', data.answer || data.error);

  } catch (err) {
    hideTyping();
    addLog('error', 'Bağlantı xətası', err.message);
    statErrors++;
    updateStats();
    appendMessage('bot', `⚠️ Server ilə bağlantı qurulmadı. <br><small>server.py işləyirmi? <code>python server.py</code></small>`);
  }

  isTyping = false;
}

// ═══════════════════════════════════════════════════════════
// BU FUNKSIYANI DA ƏLAVƏ ET (server vəziyyətini yoxlayır):
// startNewChat() funksiyasının yanına əlavə et
// ═══════════════════════════════════════════════════════════

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
