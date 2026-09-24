// popup.js — Lógica do popup do PIPE Cofre

// Origem por omissão (produção). Pode ser trocada em
// chrome.storage.local.pipeOrigin (servidor local) — ver docs/guia-extensao-chrome.md.
const ORIGEM_DEFAULT = 'https://felipejn.pythonanywhere.com';

// Capturas mais antigas do que isto são descartadas (alinhado com o
// COFRE_SESSION_TIMEOUT do cofre: 900 s).
const CAPTURA_TTL_MS = 15 * 60 * 1000;

// Estado do popup (vive o tempo da abertura do popup):
//   capturaDoSite   — captura feita no site do separador actual
//   capturaOutroSite— captura feita noutro site (mostrada como nota)
//   conflito        — entrada já existente (409) à espera de confirmação
let capturaDoSite = null;
let capturaOutroSite = null;
let conflito = null;

// NOTA: não se usa `alert()` neste popup — no popup de uma extensão do Chrome
// o alert fecha o popup e pode aparecer uma janela vazia, sem texto legível.
// Todas as mensagens vão para #mensagem (ver popup.html).

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
        await renderUnlocked(response.url, response.entries || []);
      } else {
        renderError(response.error);
      }
    } catch (e) {
      renderError(e.message);
    }
  }

  // ─── Não activado ───
  async function renderNotActivated() {
    const origem = await origemConfigurada();
    container.innerHTML = `
      <h2>🔒 PIPE Cofre</h2>
      <div class="status status-not-set">
        Cofre não activado. Inicia sessão no PIPE para activar o cofre seguro.
      </div>
      <a href="${esc(origem)}/auth/login" class="login-link">Iniciar sessão no PIPE →</a>
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
  async function renderUnlocked(url, entries = []) {
    const dominio = dominioDeUrl(url);

    // Captura pendente do content script: só é oferecida para guardar se for
    // DESTE site. Uma captura de outro site aparece como nota (não é apagada
    // em silêncio) — antes era mostrada em todos os separadores, o que fazia
    // parecer que qualquer site tinha um login pendente.
    const captura = await lerCapturaPendente();
    const dominioCaptura = captura ? dominioDeUrl(captura.url) : null;
    capturaDoSite = (captura && dominioCaptura && dominioCaptura === dominio) ? captura : null;
    capturaOutroSite = (captura && !capturaDoSite) ? captura : null;

    let listHtml = '';
    if (entries.length > 0) {
      // Sem `onclick` inline: a CSP das páginas de extensão (MV3) bloqueia
      // handlers inline. Os listeners são ligados por JS (ver abaixo) e a
      // password nunca é interpolada em HTML (só o id, que é numérico).
      listHtml = entries.map(e => `
        <div class="entry-item">
          <div>
            <strong>${esc(e.titulo)}</strong>
            <div>${esc(e.username || '')}</div>
          </div>
          <div class="entry-actions">
            <button class="btn-copiar" data-id="${e.id}" title="Copiar password">📋</button>
          </div>
        </div>
      `).join('');
    }

    let vazioHtml = '';
    if (entries.length === 0) {
      vazioHtml = dominio
        ? '<div class="nota" style="text-align:center;padding:12px;">Sem entradas para este site.</div>'
        : '<div class="nota" style="text-align:center;padding:12px;">Este separador não é um site (http/https).</div>';
    }

    container.innerHTML = `
      <h2>🔓 PIPE Cofre</h2>
      <div class="status status-unlocked">Cofre desbloqueado${dominio ? ' — ' + esc(dominio) : ''}</div>
      <div id="entries-list">${listHtml}</div>
      ${vazioHtml}
      ${htmlCaptura()}
      ${htmlCapturaOutroSite()}
      <button id="refresh-btn" class="btn btn-secondary btn-block" style="margin-top:8px;">↻ Actualizar lista</button>
    `;

    document.getElementById('refresh-btn').addEventListener('click', async () => {
      limparMensagem();
      await loadEntries();
      if (document.getElementById('entries-list')) mostrarMensagem('Lista actualizada.', 'ok');
    });

    // Copiar password (um listener por entrada, com a password vinda do objecto
    // da entrada — nunca do HTML)
    container.querySelectorAll('.btn-copiar').forEach((botao) => {
      botao.addEventListener('click', () => {
        const entrada = entries.find(x => String(x.id) === botao.dataset.id);
        if (entrada) copyToClipboard(entrada.password || '');
      });
    });

    const acceptBtn = document.getElementById('capture-accept-btn');
    if (acceptBtn) acceptBtn.addEventListener('click', () => guardarCaptura(capturaDoSite));

    const updateBtn = document.getElementById('capture-update-btn');
    if (updateBtn) updateBtn.addEventListener('click', () => actualizarEntradaExistente(conflito.id));

    const denyBtn = document.getElementById('capture-deny-btn');
    if (denyBtn) denyBtn.addEventListener('click', async () => {
      await apagarCapturaPendente();
      limparMensagem();
      await loadEntries();
    });
  }

  // ─── HTML da captura pendente ───
  function htmlCaptura() {
    if (!capturaDoSite) return '';
    if (conflito) {
      return `
        <div class="status status-locked" style="margin-top:8px;">
          ⚠️ Já existe uma entrada para <strong>${esc(conflito.username || '')}</strong> neste site.<br>
          Actualizo a password guardada?
        </div>
        <button id="capture-update-btn" class="btn btn-primary btn-block" style="margin-top:6px;">Actualizar entrada</button>
        <button id="capture-deny-btn" class="btn btn-secondary btn-block" style="margin-top:4px;">Não</button>
      `;
    }
    return `
      <div class="status status-locked" style="margin-top:8px;">
        📝 Login capturado em <strong>${esc(dominioDeUrl(capturaDoSite.url) || '')}</strong>.<br>
        Guardar para <strong>${esc(capturaDoSite.username || '')}</strong>?
      </div>
      <button id="capture-accept-btn" class="btn btn-primary btn-block" style="margin-top:6px;">Guardar</button>
      <button id="capture-deny-btn" class="btn btn-secondary btn-block" style="margin-top:4px;">Não</button>
    `;
  }

  // ─── HTML de captura feita noutro site (informativo) ───
  function htmlCapturaOutroSite() {
    if (!capturaOutroSite || conflito) return '';
    return `
      <div class="nota" style="margin-top:10px;">
        📝 Há um login capturado em <strong>${esc(dominioDeUrl(capturaOutroSite.url) || '')}</strong>.
        Abre esse site para o guardar.
      </div>
      <button id="capture-deny-btn" class="btn btn-secondary btn-block" style="margin-top:4px;">Descartar essa captura</button>
    `;
  }

  // ─── Desbloquear ───
  async function unlock() {
    const pw = document.getElementById('unlock-pw').value;
    if (!pw) return;

    const btn = document.getElementById('unlock-btn');
    btn.disabled = true;
    btn.textContent = 'A desbloquear…';
    limparMensagem();

    try {
      const response = await chrome.runtime.sendMessage({ type: 'UNLOCK', password: pw });
      if (response.success) {
        init();
        return;
      }
      mostrarMensagem(response.error || 'Password incorreta.', 'erro');
    } catch (e) {
      mostrarMensagem(e.message, 'erro');
    }
    btn.disabled = false;
    btn.textContent = 'Desbloquear';
  }

  // ─── Captura pendente (chrome.storage.local) ───
  async function lerCapturaPendente() {
    try {
      const resultado = await chrome.storage.local.get('pendingCapture');
      const captura = resultado.pendingCapture || null;
      if (!captura) return null;
      if (!captura.ts || Date.now() - captura.ts > CAPTURA_TTL_MS) {
        await chrome.storage.local.remove('pendingCapture');
        return null;
      }
      return captura;
    } catch (e) {
      return null;
    }
  }

  async function apagarCapturaPendente() {
    try {
      await chrome.storage.local.remove('pendingCapture');
    } catch (e) {
      // storage indisponível — o estado em memória é limpo na mesma
    }
    capturaDoSite = null;
    capturaOutroSite = null;
    conflito = null;
  }

  // ─── Guardar a captura (POST) ───
  async function guardarCaptura(captura) {
    if (!captura || !captura.url) return;

    const btn = document.getElementById('capture-accept-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'A guardar…'; }
    limparMensagem();

    try {
      const response = await chrome.runtime.sendMessage({
        type: 'SAVE_ENTRY',
        entry: {
          titulo: captura.url.replace(/^https?:\/\//, ''),
          url: captura.url,
          username: captura.username || '',
          password: captura.password || '',
        }
      });

      if (response.success) {
        await apagarCapturaPendente();
        mostrarMensagem('Entrada guardada.', 'ok');
        await loadEntries();
        return;
      }

      // 409: já existe entrada com o mesmo domínio + username. O servidor
      // devolve o id da existente e o popup oferece actualizá-la (antes só
      // mostrava o erro e a captura ficava pendente para sempre).
      if (response.status === 409 && response.dados && response.dados.id) {
        conflito = {
          id: response.dados.id,
          username: response.dados.username || captura.username || '',
        };
        mostrarMensagem('Essa entrada já existe no cofre.', 'erro');
        await loadEntries();
        return;
      }

      mostrarMensagem('Erro ao guardar: ' + response.error, 'erro');
    } catch (e) {
      mostrarMensagem('Erro ao guardar: ' + e.message, 'erro');
    }

    if (btn) { btn.disabled = false; btn.textContent = 'Guardar'; }
  }

  // ─── Actualizar a entrada existente (PUT, depois de um 409) ───
  async function actualizarEntradaExistente(id) {
    if (!id || !capturaDoSite) return;

    const btn = document.getElementById('capture-update-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'A actualizar…'; }
    limparMensagem();

    try {
      const response = await chrome.runtime.sendMessage({
        type: 'UPDATE_ENTRY',
        id: id,
        entry: {
          url: capturaDoSite.url,
          username: capturaDoSite.username || '',
          password: capturaDoSite.password || '',
        }
      });

      if (response.success) {
        await apagarCapturaPendente();
        mostrarMensagem('Entrada actualizada.', 'ok');
      } else {
        mostrarMensagem('Erro ao actualizar: ' + response.error, 'erro');
      }
    } catch (e) {
      mostrarMensagem('Erro ao actualizar: ' + e.message, 'erro');
    }
    await loadEntries();
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
  async function renderNotLoggedIn() {
    const origem = await origemConfigurada();
    container.innerHTML = `
      <h2>🔒 PIPE Cofre</h2>
      <div class="status status-not-set">Inicia sessão no PIPE para usar o cofre.</div>
      <a href="${esc(origem)}/auth/login" class="login-link">Iniciar sessão →</a>
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

// Domínio (host) de uma URL http(s). null para chrome://, about:, ficheiros…
// — é o mesmo critério que o backend usa em extrair_dominio(), para o popup
// não oferecer capturas de separadores que não são sites.
function dominioDeUrl(url) {
  try {
    const u = new URL(url);
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return null;
    return u.hostname.replace(/^www\./, '') || null;
  } catch (e) {
    return null;
  }
}

// Origem do servidor PIPE: chrome.storage.local.pipeOrigin (teste local) ou produção
async function origemConfigurada() {
  let origem = ORIGEM_DEFAULT;
  try {
    const r = await chrome.storage.local.get('pipeOrigin');
    const guardado = r && r.pipeOrigin ? String(r.pipeOrigin) : '';
    if (/^https?:\/\/[^"'<>\s]+$/.test(guardado)) origem = guardado.replace(/\/+$/, '');
  } catch (e) {
    // storage indisponível — fica o default
  }
  return origem;
}

// ─── Mensagens inline (substituem o alert — ver nota no topo do ficheiro) ───
function mostrarMensagem(texto, tipo) {
  const zona = document.getElementById('mensagem');
  if (!zona) return;
  zona.className = 'status status-' + (tipo || 'ok');
  zona.textContent = texto;
  zona.style.display = 'block';
}

function limparMensagem() {
  const zona = document.getElementById('mensagem');
  if (!zona) return;
  zona.textContent = '';
  zona.style.display = 'none';
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    mostrarMensagem('Password copiada.', 'ok');
  }).catch(() => {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    mostrarMensagem('Password copiada.', 'ok');
  });
}
