// extensao_harness.js — validação do JavaScript da extensão Chrome
//
// Corrido por `tests/test_extensao_js.py` (Node; o teste salta se não houver
// Node instalado). Carrega os ficheiros REAIS da extensão num `vm` com stubs
// de `chrome`/`document` e verifica:
//   - onde o content script captura (e onde NÃO captura: o próprio PIPE);
//   - as funções puras do popup (dominioDeUrl, origemConfigurada).
//
// Regressões cobertas: a captura deixava de ser filtrada e aparecia em todos
// os separadores; o content script capturava o login do PIPE local.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const EXT = path.join(__dirname, '..', 'chrome-extension') + path.sep;
let falhas = 0;

function check(nome, cond, extra) {
  if (cond) {
    console.log('  OK   ' + nome);
  } else {
    falhas++;
    console.log('  FALHA ' + nome + (extra ? ' -> ' + extra : ''));
  }
}

// ── content.js: guarda de páginas do próprio PIPE ──
function carregarContent(url, pipeOrigin) {
  const enviados = [];
  const listeners = {};
  const sandbox = {
    URL,
    console,
    window: { location: { href: url } },
    document: { addEventListener: (t, fn) => { listeners[t] = fn; } },
    chrome: {
      runtime: { sendMessage: (m) => enviados.push(m) },
      storage: { local: { get: (k, cb) => cb(pipeOrigin ? { pipeOrigin } : {}) } },
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(EXT + 'content.js', 'utf8'), sandbox);
  return { enviados, listeners };
}

function formLogin() {
  return {
    querySelector: (sel) => {
      if (sel.indexOf('password') >= 0) return { value: 'segredo123' };
      if (sel.indexOf('email') >= 0) return { value: 'felipejn' };
      return null;
    },
    querySelectorAll: (sel) => (sel.indexOf('button') >= 0
      ? []
      : [{ name: 'username', placeholder: '' }]),
  };
}

function submeter(url, pipeOrigin) {
  const { enviados, listeners } = carregarContent(url, pipeOrigin);
  const form = formLogin();
  listeners.submit({ target: { closest: () => form } });
  return enviados;
}

console.log('content.js — onde NÃO deve capturar:');
check('login local do PIPE', submeter('http://127.0.0.1:5000/auth/login').length === 0);
check('página do cofre local', submeter('http://127.0.0.1:5000/passwords/').length === 0);
check('login em produção', submeter('https://felipejn.pythonanywhere.com/auth/login').length === 0);
check('cofre em produção', submeter('https://felipejn.pythonanywhere.com/passwords/x').length === 0);
check('origem custom (localhost:8000)', submeter('http://localhost:8000/auth/login', 'http://localhost:8000').length === 0);
check('outra porta local não é o PIPE', submeter('http://localhost:3000/app/login').length === 1);

console.log('content.js — onde DEVE capturar:');
check('site normal', submeter('https://exemplo.com/login').length === 1);
check('site normal com pipeOrigin local', submeter('https://exemplo.com/login', 'http://127.0.0.1:5000').length === 1);
const capturas = submeter('https://exemplo.com/login');
const cap = capturas[0];
check('payload da captura',
  cap && cap.type === 'FORM_CAPTURE'
  && cap.data.password === 'segredo123'
  && cap.data.username === 'felipejn'
  && cap.data.url === 'https://exemplo.com/login',
  JSON.stringify(cap));

// ── popup.js: dominioDeUrl + origemConfigurada ──
function carregarPopup(pipeOrigin) {
  const sandbox = {
    URL,
    console,
    document: {
      addEventListener: () => {},
      getElementById: () => null,
      createElement: () => ({}),
    },
    navigator: {},
    chrome: {
      storage: {
        local: {
          get: () => Promise.resolve(pipeOrigin === undefined ? {} : { pipeOrigin }),
        },
      },
    },
  };
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(EXT + 'popup.js', 'utf8'), sandbox);
  return sandbox;
}

const p = carregarPopup();
console.log('popup.js — dominioDeUrl:');
check('www + porta', p.dominioDeUrl('https://www.Exemplo.com:8080/login') === 'exemplo.com',
  p.dominioDeUrl('https://www.Exemplo.com:8080/login'));
check('ip local', p.dominioDeUrl('http://127.0.0.1:5000/auth/login') === '127.0.0.1');
check('chrome:// → null', p.dominioDeUrl('chrome://extensions') === null);
check('about:blank → null', p.dominioDeUrl('about:blank') === null);
check('lixo → null', p.dominioDeUrl('nao-e-url') === null);
check('undefined → null', p.dominioDeUrl(undefined) === null);

(async () => {
  console.log('popup.js — origemConfigurada:');
  check('sem storage → produção',
    (await carregarPopup().origemConfigurada()) === 'https://felipejn.pythonanywhere.com');
  check('origem local',
    (await carregarPopup('http://127.0.0.1:5000').origemConfigurada()) === 'http://127.0.0.1:5000');
  check('barra final removida',
    (await carregarPopup('http://127.0.0.1:5000/').origemConfigurada()) === 'http://127.0.0.1:5000');
  check('javascript: rejeitado',
    (await carregarPopup('javascript:alert(1)').origemConfigurada()) === 'https://felipejn.pythonanywhere.com');

  console.log(falhas === 0 ? 'TODOS OS TESTES PASSARAM' : falhas + ' FALHA(S)');
  process.exit(falhas === 0 ? 0 : 1);
})();
