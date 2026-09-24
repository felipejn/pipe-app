// background.js — Service Worker do PIPE Cofre
// Comunicação com o backend PIPE via fetch com credentials: 'include'
//
// NOTA: no service worker de uma extensão o URL é chrome-extension://<id>/…,
// pelo que um caminho relativo ('/passwords') apontaria para a própria
// extensão. O servidor tem de ser indicado por URL absoluta.
// Para testar contra um servidor local:
//   chrome.storage.local.set({ pipeOrigin: 'http://127.0.0.1:5000' })

const PIPE_ORIGIN_DEFAULT = 'https://felipejn.pythonanywhere.com';
let _apiBase = null;

async function getApiBase() {
  if (_apiBase) return _apiBase;
  let origem = PIPE_ORIGIN_DEFAULT;
  try {
    const guardado = await chrome.storage.local.get('pipeOrigin');
    if (guardado && guardado.pipeOrigin) origem = guardado.pipeOrigin;
  } catch (e) {
    // storage indisponível — usa o default
  }
  _apiBase = origem.replace(/\/+$/, '') + '/passwords';
  return _apiBase;
}

// ─── Obter CSRF Token ───
async function getCsrfToken() {
  const base = await getApiBase();
  const res = await fetch(base + '/api/csrf-token', {
    credentials: 'include',
  });
  // Sem sessão PIPE, o Flask-Login redirecciona para /auth/login (HTML) —
  // detecta-o e devolve uma mensagem útil ao popup em vez de falhar a ler JSON.
  if (!res.ok || res.redirected) {
    throw new Error(
      'Sem sessão no PIPE. Inicia sessão em ' + base.replace('/passwords', '') + ' e tenta de novo.'
    );
  }
  const data = await res.json();
  return data.csrfToken || '';
}

// ─── API Helper ───
async function apiFetch(endpoint, method = 'GET', body = null) {
  const base = await getApiBase();
  const token = await getCsrfToken();
  const opts = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': token,
    },
    credentials: 'include',
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(base + '/api/' + endpoint, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.erro || 'Erro de servidor');
  }
  return res.json();
}

// ─── Message Handler ───
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  switch (msg.type) {
    case 'GET_ENTRIES':
      apiFetch('cofre/entradas?url=' + encodeURIComponent(msg.url), 'GET')
        .then(d => sendResponse({ success: true, entries: d }))
        .catch(e => sendResponse({ success: false, error: e.message }));
      return true;

    case 'GET_ENTRIES_BY_TAB':
      // Recebe o tab ID, obtém a URL, e devolve as entradas
      chrome.tabs.get(msg.tabId, (tab) => {
        if (chrome.runtime.lastError || !tab || !tab.url) {
          sendResponse({ success: false, error: 'Não foi possível obter a URL do separador.' });
          return;
        }
        apiFetch('cofre/entradas?url=' + encodeURIComponent(tab.url), 'GET')
          .then(d => sendResponse({ success: true, entries: d, url: tab.url }))
          .catch(e => sendResponse({ success: false, error: e.message }));
      });
      return true;

    case 'UNLOCK':
      apiFetch('cofre/desbloquear', 'POST', { password: msg.password })
        .then(d => sendResponse({ success: true }))
        .catch(e => sendResponse({ success: false, error: e.message }));
      return true;

    case 'SAVE_ENTRY':
      apiFetch('cofre/entradas', 'POST', msg.entry)
        .then(d => sendResponse({ success: true, id: d.id }))
        .catch(e => sendResponse({ success: false, error: e.message }));
      return true;

    case 'GET_STATE':
      apiFetch('cofre/estado', 'GET')
        .then(d => sendResponse({ success: true, state: d }))
        .catch(e => sendResponse({ success: false, error: e.message }));
      return true;

    case 'FORM_CAPTURE':
      // Guarda a captura pendente no session storage para o popup ler
      chrome.storage.local.set({ pendingCapture: msg.data });
      chrome.action.setBadgeText({ text: '📝' });
      setTimeout(() => {
        chrome.action.setBadgeText({ text: '' });
      }, 3000);
      return true;
  }
  return false;
});
