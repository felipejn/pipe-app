// popup.js — Lógica do popup do PIPE Cofre

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('state-container');

  // ─── Verificar estado ───
  init();

  async function init() {
    try {
      const response = await chrome.runtime.sendMessage({ type: 'GET_STATE' });
      if (response.success) {
        renderState(response.state);
      } else {
        renderError(response.error);
      }
    } catch (e) {
      renderNotLoggedIn();
    }
  }

  // ─── Renderizar estado ───
  function renderState(state) {
    if (!state.activado) {
      renderNotActivated();
      return;
    }
    if (!state.desbloqueado) {
      renderLocked();
      return;
    }
    loadEntries();
  }

  // ─── Obter entradas do separador actual ───
  async function loadEntries() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.url) {
        renderNoTab();
        return;
      }
      const response = await chrome.runtime.sendMessage({
        type: 'GET_ENTRIES_BY_TAB',
        tabId: tab.id
      });
      if (response.success) {
        renderUnlocked(response.url, response.entries || []);
      } else {
        renderError(response.error);
      }
    } catch (e) {
      renderError(e.message);
    }
  }

  // ─── Não activado ───
  function renderNotActivated() {
    container.innerHTML = `
      <h2>🔒 PIPE Cofre</h2>
      <div class="status status-not-set">
        Cofre não activado. Inicia sessão no PIPE para activar o cofre seguro.
      </div>
      <a href="https://felipejn.pythonanywhere.com/auth/login" class="login-link">Iniciar sessão no PIPE →</a>
    `;
  }

  // ─── Bloqueado ───
  function renderLocked() {
    container.innerHTML = `
      <h2>🔒 PIPE Cofre</h2>
      <div class="status status-locked">Cofre bloqueado. Introduz a password mestra para desbloquear.</div>
      <div class="section">
        <input type="password" id="unlock-pw" placeholder="Password mestra" autocomplete="off">
      </div>
      <button id="unlock-btn" class="btn btn-primary btn-block">Desbloquear</button>
    `;

    document.getElementById('unlock-btn').addEventListener('click', unlock);
    document.getElementById('unlock-pw').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') unlock();
    });
  }

  // ─── Desbloqueado com entradas ───
  function renderUnlocked(url, entries = []) {
    const domain = url ? url.replace(/^https?:\/\//, '').split('/')[0] : '';

    let listHtml = '';
    if (entries.length > 0) {
      listHtml = entries.map(e => `
        <div class="entry-item">
          <div>
            <strong>${esc(e.titulo)}</strong>
            <div>${esc(e.username || '')}</div>
          </div>
          <div class="entry-actions">
            <button onclick="copyToClipboard('${esc(e.password || '')}')" title="Copiar password">📋</button>
          </div>
        </div>
      `).join('');
    }

    const emptyHtml = entries.length === 0
      ? '<div id="entries-empty" style="text-align:center;color:#6c757d;padding:12px;">Sem entradas para este site.</div>'
      : '';

    // Verificar captura pendente
    checkPendingCapture().then(pending => {
      const pendingHtml = pending ? `
        <div class="status status-locked" style="margin-top:8px;">
          📝 Captura detectada em <strong>${esc(pending.url || '')}</strong>.<br>
          Guardar para <strong>${esc(pending.username || '')}</strong>?
        </div>
        <button id="capture-accept-btn" class="btn btn-primary btn-block" style="margin-top:6px;">Guardar</button>
        <button id="capture-deny-btn" class="btn btn-secondary btn-block" style="margin-top:4px;">Não</button>
      ` : '';

      container.innerHTML = `
        <h2>🔓 PIPE Cofre</h2>
        <div class="status status-unlocked">Cofre desbloqueado${domain ? ' — ' + esc(domain) : ''}</div>
        <div id="entries-list">${listHtml}</div>
        ${emptyHtml}
        ${pendingHtml}
        <button id="refresh-btn" class="btn btn-secondary btn-block" style="margin-top:8px;">Actualizar</button>
      `;

      document.getElementById('refresh-btn').addEventListener('click', loadEntries);

      const acceptBtn = document.getElementById('capture-accept-btn');
      const denyBtn = document.getElementById('capture-deny-btn');
      if (acceptBtn) acceptBtn.addEventListener('click', () => acceptCapture(pending));
      if (denyBtn) denyBtn.addEventListener('click', () => clearPendingCapture());
    });
  }

  // ─── Desbloquear ───
  async function unlock() {
    const pw = document.getElementById('unlock-pw').value;
    if (!pw) return;

    const btn = document.getElementById('unlock-btn');
    btn.disabled = true;
    btn.textContent = 'A desbloquear…';

    try {
      const response = await chrome.runtime.sendMessage({ type: 'UNLOCK', password: pw });
      if (response.success) {
        init();
      } else {
        alert('Password incorreta.');
        btn.disabled = false;
        btn.textContent = 'Desbloquear';
      }
    } catch (e) {
      alert(e.message);
      btn.disabled = false;
      btn.textContent = 'Desbloquear';
    }
  }

  // ─── Captura ───
  async function checkPendingCapture() {
    try {
      const result = await chrome.storage.local.get('pendingCapture');
      return result.pendingCapture || null;
    } catch { return null; }
  }

  async function acceptCapture(pending) {
    if (!pending || !pending.url) return;
    try {
      const response = await chrome.runtime.sendMessage({
        type: 'SAVE_ENTRY',
        entry: {
          titulo: pending.url.replace(/^https?:\/\//, ''),
          url: pending.url,
          username: pending.username || '',
          password: pending.password || '',
        }
      });
      if (response.success) {
        await chrome.storage.local.remove('pendingCapture');
        loadEntries();
      } else {
        alert('Erro ao guardar: ' + response.error);
      }
    } catch (e) {
      alert(e.message);
    }
  }

  async function clearPendingCapture() {
    await chrome.storage.local.remove('pendingCapture');
    loadEntries();
  }

  // ─── Erro ───
  function renderError(err) {
    container.innerHTML = `
      <h2>🔒 PIPE Cofre</h2>
      <div class="status status-not-set">Erro: ${esc(err)}</div>
    `;
  }

  // ─── Sem tab ───
  function renderNoTab() {
    container.innerHTML = `
      <h2>🔒 PIPE Cofre</h2>
      <div class="status status-not-set">Sem separador activo.</div>
    `;
  }

  // ─── Não logado ───
  function renderNotLoggedIn() {
    container.innerHTML = `
      <h2>🔒 PIPE Cofre</h2>
      <div class="status status-not-set">Inicia sessão no PIPE para usar o cofre.</div>
      <a href="https://felipejn.pythonanywhere.com/auth/login" class="login-link">Iniciar sessão →</a>
    `;
  }
});

// ─── Funções globais ───
function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    alert('Password copiada!');
  }).catch(() => {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    alert('Password copiada!');
  });
}
