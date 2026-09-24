# PIPE — Cofre de Passwords + Extensão Chrome — PLANO DE CORRECÇÃO

## Contexto

O plano original para o cofre de passwords contém 5 problemas (2 críticos, 2 médios, 1 menor) que, se não corrigidos, comprometem a segurança, a usabilidade ou o funcionamento da extensão. Este documento actualiza o plano com as correcções definitivas.

**Problemas corrigidos:**

| # | Gravidade | Problema | Solução |
|---|-----------|----------|---------|
| 1 | 🔴 Crítico | Chave AES na sessão Flask cookie (signing ≠ encryption) | Flask-Session filesystem — chave nunca no browser |
| 2 | 🔴 Crítico | CORS `origins: "*"` + `credentials: True` é inválido/breve | Origin restrito a `chrome-extension://<id>` |
| 3 | 🟡 Médio | Sem aviso de perda permanente se esquecer master password | Aviso explícito no modal de activação |
| 4 | 🟡 Médio | Captura activa em todos os forms com password | Filtro heurístico: só forms de login |
| 5 | 🔵 Menor | Dedup CSV usa domínio mas Chrome exporta URL | Função `extrair_dominio()` consistente |

---

## Mudanças ao plano original

### Secções afectadas: Fase 0, Fase 3, Fase 4, Fase 5

O fluxo geral mantém-se (crypto → modelos → API → frontend → extensão), mas com alterações profundas na forma como a chave é guardada e como o CORS funciona.

---

## Fase 0 — Dependências e Configuração

### `requirements.txt` — adicionar
```
cryptography==43.0.1
flask-cors==5.0.0
bcrypt==4.2.0
Flask-Session==0.5.0
```

### `config.py` — adicionar ao `Config`
```python
# --- Cofre ---
COFRE_KDF_ITERATIONS = 600000
COFRE_SESSION_TIMEOUT = 900  # 15 minutos
COFRE_CORS_ORIGINS = os.environ.get('COFRE_CORS_ORIGINS', '')  # "chrome-extension://abc123,chrome-extension://def456"
```

**Nota:** `COFRE_CORS_ORIGINS` é uma string com IDs da extensão separados por vírgula. O utilizador descobre o ID em `chrome://extensions` → Load unpacked → mostra-se na página da extensão. Sem valor, a API cofre recusa CORS (não funciona com extensão).

### `app/__init__.py` — três alterações

**1. Importar e inicializar Flask-Session ANTES de db.init_app:**
```python
from flask_session import Session
```
Depois de `app.config.from_object(config[config_name])`:
```python
# Sessões server-side para o cofre (chave nunca no browser)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(BASE_DIR, 'instance', 'flask_session')
app.config['SESSION_FILE_THRESHOLD'] = 500
Session(app)
```

**2. Inicializar CORS com origins restritos:**
```python
from flask_cors import CORS

# Parse de COFRE_CORS_ORIGINS
_cofre_origins_env = app.config.get('COFRE_CORS_ORIGINS', '')
_cofre_origins = [o.strip() for o in _cofre_origins_env.split(',') if o.strip()] if _cofre_origins_env else []

if _cofre_origins:
    CORS(app, resources={
        r"/passwords/api/cofre/*": {"origins": _cofre_origins, "supports_credentials": True},
        r"/passwords/api/csrf-token": {"origins": _cofre_origins, "supports_credentials": True},
    })
```

**Importante:** O padrão `/passwords/api/cofre/*` NÃO cobre `/passwords/api/csrf-token` (prefixo `/cofre/`). Se o CSRF token ficar fora do namespace do cofre, o browser bloqueia o fetch do background.js por CORS e a extensão nunca consegue autenticar-se. **Alternativa:** mover o endpoint para `GET /passwords/api/cofre/csrf-token` para ficar dentro do padrão.

**3. Importar modelos antes de `db.create_all()`:**
```python
from app.passwords.models import CofrePassword, CofreConfig
```

### `app/templates/base.html` — meta tag CSRF
```html
<meta name="csrf-token" content="{{ csrf_token() }}">
```

**Nota:** A meta tag CSRF serve para as páginas PIPE (templates). A extensão Chrome NÃO tem acesso a `window.CSRF_TOKEN` porque `popup.html` corre num contexto isolado da extensão, sem acesso ao DOM da aba do PIPE. O CSRF token para a extensão obtém-se sempre via `GET /passwords/api/csrf-token`.

---

## Fase 1 — Módulo de Criptografia

**Novo ficheiro: `app/passwords/crypto.py`**

Funções:
- `gerar_salt()` → 32 bytes aleatórios
- `derivar_chave(password, salt, iterations)` → chave AES-256 via PBKDF2-SHA256
- `hash_password_mestre(password)` → bcrypt hash para verificação
- `verificar_password_mestre(password, hash)` → bool
- `cifrar(chave, texto)` → (ciphertext, iv, tag) — AES-256-GCM, nonce 96-bit
- `decifrar(chave, ciphertext, iv, tag)` → texto plano
- `bytes_para_b64(data)` / `b64_para_bytes(data)` — conversão para sessão
- `extrair_dominio(url)` → str — Normaliza e extrai o domínio de uma URL. **Única fonte de verdade** para deduplicação e lookup.
  - Normalização: `urlparse(url).hostname` (não `netloc` — exclui porta e user-info), `.lower()`, strip de `www.`
  - Exemplo: `https://www.Exemplo.com:8080/user` → `exemplo.com`

A função `extrair_dominio()` é a **única fonte de verdade** para todo o sistema:
- **Backend**: usa para dedup CSV, lookup de entrada por domínio, query `?dominio=X`
- **Extensão**: envia **sempre a URL completa** ao backend (`/passwords/api/cofre/entradas?url=...` ou no body do POST). O backend chama `extrair_dominio()` internamente. A extensão **nunca** calcula o domínio no browser (nem `new URL().hostname`, nem nada). Isto garante que Python e JS nunca divergem.
- **Popup**: envia a URL do separador activo ao backend para obter entradas — o servidor filtra por domínio.

**Porquê:** `urlparse().netloc` (Python) inclui porta e user-info; `location.hostname` (JS) não. Além disso, sem normalização, `www.exemplo.com` e `exemplo.com` ficam como domínios diferentes no cofre, causando duplicados e falhas de lookup. Normalizar tudo no backend elimina ambos os problemas.

**Aviso:** Qualquer lógica de domínio no lado do cliente (extensão) deve ser evitada. A extensão envia URL, o servidor decide o domínio.

---

## Fase 2 — Modelos de Base de Dados

**Novo ficheiro: `app/passwords/models.py`**

### `CofreConfig` (cofre_configs)
| Campo | Tipo | Notas |
|---|---|---|
| id | Integer PK | |
| user_id | Integer FK → utilizadores.id | unique |
| master_pw_hash | String(256) | bcrypt hash (verificação) |
| salt | String(64) | base64-encoded salt para PBKDF2 |
| kdf_iterations | Integer | default 600000 |
| ativo | Boolean | default True |
| data_criacao | DateTime | |

### `CofrePassword` (cofre_passwords)
| Campo | Tipo | Notas |
|---|---|---|
| id | Integer PK | |
| user_id | Integer FK → utilizadores.id | index |
| titulo | String(128) | |
| url | String(512) | nullable |
| dominio | String(256) | nullable, index (para lookup da extensão) |
| username | String(256) | nullable |
| password_cifrada | LargeBinary | ciphertext AES-256-GCM |
| iv | LargeBinary | 12 bytes |
| tag | LargeBinary | 16 bytes |
| notas | Text | nullable |
| favorito | Boolean | default False |
| data_criacao | DateTime | |
| data_atualizacao | DateTime | |

Método `para_dict(chave_derivada=None)` — se chave fornecida, decifra e inclui password em claro.

**Protecção IDOR (OBRIGATÓRIO em todas as operações):**
Todos os endpoints que acedem a `CofrePassword` devem filtrar por `user_id=current_user.id`, nunca só por `id`. Os IDs são sequenciais (Integer PK) — qualquer utilizador autenticado pode enumerar. Exemplos:
```python
# CORRECTO
entrada = CofrePassword.query.filter_by(id=id, user_id=current_user.id).first()
# WRONG — permite aceder a entradas de outros utilizadores
entrada = CofrePassword.query.get(id)
```
Isto aplica-se a:
- `GET /entradas/<id>` — lookup
- `PUT /entradas/<id>` — edição
- `DELETE /entradas/<id>` — apagamento
- `POST /entradas` — verificação de duplicado (dominio+username) DEVE ser filtrada por `user_id=current_user.id`
- `GET /entradas` (listagem) — sempre filtrar por `user_id=current_user.id`

---

## Fase 3 — Endpoints API

**Modificar: `app/passwords/routes.py`** (adicionar abaixo das rotas existentes)

### Sessão do cofre (CORRECÇÃO)
A chave derivada fica em **sessão server-side Flask-Session** (filesystem em `instance/flask_session/`), NÃO no cookie. O cookie do browser contém apenas um session ID opaco assinado. A chave nunca é transmitida nem armazenada no browser.

Helper: `_obter_chave_cofre()` → devolve chave ou None se bloqueado/expirado (verifica `session.get('cofre_chave')` + timestamp `session.get('cofre_chave_ts')`).

### Endpoints

| Método | Rota | Rate Limit | Descrição |
|---|---|---|---|
| GET | `/passwords/api/cofre/estado` | — | Estado do cofre (activado? desbloqueado?) |
| POST | `/passwords/api/cofre/activar` | 5/h | Definir password mestra, criar CofreConfig |
| POST | `/passwords/api/cofre/desbloquear` | 10/h | Verificar password, desbloquear sessão |
| POST | `/passwords/api/cofre/bloquear` | — | Limpar chave da sessão server-side |
| POST | `/passwords/api/cofre/alterar-password` | 5/h | Re-cifrar tudo com nova password |
| GET | `/passwords/api/cofre/entradas` | 60/min | Listar entradas (decifradas). `?url=X` (URL completa, servidor extrai domínio) |
| POST | `/passwords/api/cofre/entradas` | 30/min | Criar entrada |
| PUT | `/passwords/api/cofre/entradas/<id>` | 30/min | Editar entrada |
| DELETE | `/passwords/api/cofre/entradas/<id>` | 30/min | Apagar entrada |
| POST | `/passwords/api/cofre/importar-csv` | 10/h | Importar CSV do Chrome |
| GET | `/passwords/api/csrf-token` | 30/min | CSRF token para extensão (CORS coberto na Fase 0) |

### Fluxo de activação (COM AVISO)
1. Validar password (mín 8 chars) + confirmação
2. **Mostrar aviso vermelho obrigatório:** *"ATENÇÃO: Se esquecer a password mestra, os dados ficarão permanentemente inacessíveis. Não há recuperação — guarda esta password em segurança."*
3. `gerar_salt()` → `derivar_chave(pw, salt)` → `hash_password_mestre(pw)`
4. Criar `CofreConfig` na BD
5. Guardar chave na sessão **server-side** (Flask-Session): `session['cofre_chave'] = chave`, `session['cofre_chave_ts'] = time.time()`

### Fluxo de desbloqueio
1. Verificar password contra bcrypt hash
2. Derivar chave com salt guardado
3. Guardar na sessão server-side

### Fluxo de alteração de password mestra
1. Verificar password actual
2. Derivar chave antiga + gerar nova salt + derivar nova chave
3. **Transacção atómica:** decifrar cada entrada com chave antiga, re-cifrar com nova, actualizar hash/salt em CofreConfig
4. Se qualquer entrada falhar → rollback total

### Importação CSV (Chrome export) — CORRECÇÃO DEDUPLICAÇÃO
Formato Chrome: `name,url,username,password`
- Ler CSV com `csv.DictReader`
- Para cada linha:
  - Extrair domínio com `extrair_dominio(url)` (normalização: hostname lower, strip www.)
  - Verificar duplicado: `dominio + username`
- Verificar duplicados (dominio + username) — saltar se existir
- Devolver `{importadas: N, duplicadas: M, erros: [...]}`

**Nota:** `extrair_dominio()` aqui e na captura activa da extensão são a **mesma função Python**, garantindo consistência. A extensão nunca computa o domínio.

---

## Fase 4 — Frontend (Template)

**Modificar: `app/templates/passwords/index.html`**

O passa a ter duas secções:

### 1. Gerador (existente, inalterado)
- Tabs Password/Passphrase/PIN, gerar, copiar

### 2. Cofre (novo, abaixo do gerador)

**Estados do cofre:**
- **Não activado**: cartão "O teu cofre ainda não está activado" + botão "Activar Cofre" → modal com password + confirmação + **AVISO VERMELHO**: *"Esquecer a password mestra significa perda permanente dos dados — não há recuperação."*
- **Bloqueado**: campo de master password + botão "Desbloquear"
- **Desbloqueado**: barra de busca, botões "Nova entrada" / "Importar CSV" / "Bloquear cofre" / "Alterar password mestra", lista de entradas como cartões

**Cada entrada mostra:** título, domínio, username, password mascarada com botão copiar, botões editar/apagar, favorito

**Modais:**
- `modal-activar` — password mestra + confirmação + **aviso de perda permanente**
- `modal-desbloquear` — password mestra
- `modal-entrada` — titulo, url, username, password (com botão "Gerar" que usa o gerador existente), notas, favorito toggle
- `modal-alterar-pw` — password actual + nova + confirmação

**JS inline** (IIFE, padrão PIPE): funções `cofreAPI()`, `verificarEstado()`, `activarCofre()`, `desbloquearCofre()`, `carregarEntradas()`, `criarEntrada()`, `editarEntrada()`, `apagarEntrada()`, `importarCSV()`, `alterarPasswordMestre()`, `renderizarCofre()`

**Nota sobre CSRF para extensão:** A extensão obtém o CSRF token exclusivamente via `GET /passwords/api/csrf-token`. O `popup.html` corre num contexto isolado da extensão e **não tem acesso** a `window.CSRF_TOKEN` da página PIPE. O `background.js` faz um `fetch` para esse endpoint e usa o token no header `X-CSRFToken` nos pedidos subsequentes.

---

## Fase 5 — Extensão Chrome (Manifest V3)

**Novo directório: `chrome-extension/`**

### `manifest.json`
- `manifest_version: 3`
- `permissions: ["activeTab", "storage"]`
- **Sem `scripting`**: o `content_scripts` com `<all_urls>` já injecta `content.js`; o preenchimento usa `chrome.tabs.sendMessage` para o content script já activo, sem necessidade de `chrome.scripting.executeScript`.
- `host_permissions: ["https://felipejn.pythonanywhere.com/*"]`
- `action.default_popup: "popup.html"`
- `background.service_worker: "background.js"`
- `content_scripts: [{matches: ["<all_urls>"], js: ["content.js"], run_at: "document_idle"}]`

### `background.js`
- Comunicação com PIPE via `fetch()` + `credentials: 'include'`
- Obtém CSRF token via `GET /passwords/api/csrf-token`
- Message handlers para popup/content scripts: `getEntries`, `unlock`, `saveEntry`, `captureForm`
- **Importante:** O ID da extensão (`chrome-extension://<id>`) é gerado pelo Chrome ao fazer Load unpacked. O utilizador deve copiar esse ID para a variável `COFRE_CORS_ORIGINS` no `.env` do servidor PIPE para que o CORS funcione. Documentar este passo.

### `popup.html` + `popup.js`
- **Não logado**: "Inicia sessão no PIPE" + link
- **Cofre bloqueado**: campo master password + "Desbloquear"
- **Cofre desbloqueado**: lista de passwords do site actual (envia URL do separador ao backend → servidor extrai domínio), botão "Preencher" por entrada, botão "Guardar esta página"

### `content.js` — CORRECÇÃO CAPTURA ACTIVA
**Princípio:** A extensão envia a **URL completa** ao backend. Nunca calcula o domínio no browser. O backend chama `extrair_dominio()` como única fonte de verdade.

**Antes de perguntar guardar**, aplicar heurística:

1. **Ignorar forms de registo**: se o form contém campos como `nome`, `email`, `password` E o botão submit diz "Registar", "Criar conta", "Sign up", **não perguntar guardar**
2. **Só capturar em forms de login**: form tem `input[type=password]` + pelo menos um `input[type=text]` ou `input[type=email]` com placeholder/name sugestivo (`username`, `email`, `login`, `user`)
3. **Enviar URL completa ao backend**: no POST ao endpoint de entrada, incluir `url: tab.url` no body. O backend extrai o domínio com `extrair_dominio(url)`.
4. **Verificar duplicado via backend**: verificar se já existe entrada com o mesmo domínio + username no cofre com a mesma password (o backend faz a comparação usando `extrair_dominio()` normalizado).
5. **Perguntar explicitamente**: popup de confirmação "Guardar password para [domínio]?" com botões "Guardar" / "Não"

Fluxo:
```
submit form → verificar heurística → é login? → sim → enviar URL ao backend → backend extrai domínio → verificar duplicado → perguntar "guardar?" → guardar
```

**Nota sobre `?dominio=X`**: Quando o popup pede entradas do site actual, envia `?url=<URL_completa_do_separador>`, nunca `?dominio=<hostname>`. O backend chama `extrair_dominio(url)` e filtra por esse resultado.

### Distribuição
Pasta no repositório para instalação manual (`chrome://extensions` → Load unpacked). Sem build/bundling.

**Passo obrigatório pós-instalação:** Após Load unpacked, anotar o ID da extensão (`chrome://extensions` → detalhes) e configurar `COFRE_CORS_ORIGINS=chrome-extension://<ID>` no `.env` do servidor.

---

## Fase 6 — Actualização da Loja de Módulos

**Modificar: `app/modulos/config.py`**
Actualizar a descrição do módulo passwords para mencionar o cofre:
```python
'descricao': 'Gerador de passwords e cofre seguro com extensão Chrome.'
```

---

## Ordem de Implementação

1. **Dependências** — requirements.txt, config.py, Flask-Session, CORS em __init__.py
2. **Crypto** — app/passwords/crypto.py (standalone, inclui `extrair_dominio()`)
3. **Modelos** — app/passwords/models.py + import em __init__.py
4. **API** — endpoints em routes.py + csrf-token endpoint + helpers de sessão server-side
5. **Frontend** — template index.html com secção cofre + modais + JS + aviso de perda permanente
6. **Extensão** — chrome-extension/ (6 ficheiros + heurística de captura)
7. **Loja** — actualizar descrição em modulos/config.py
8. **Testes** — tests/test_cofre.py (crypto, modelos, API, CSV import, deduplicação, normalização de domínio)

---

## Ficheiros a criar/modificar

| Ficheiro | Acção | Alterações vs. plano original |
|---|---|---|
| `requirements.txt` | Modificar — adicionar `Flask-Session==0.5.0` | **Novo** |
| `config.py` | Modificar — adicionar constantes cofre + `COFRE_CORS_ORIGINS` | **Alterado** |
| `app/__init__.py` | Modificar — Flask-Session + CORS restrito + modelos | **Alterado** (CORS e Session) |
| `app/templates/base.html` | Modificar — meta tag CSRF (remover `window.CSRF_TOKEN`) | **Alterado** |
| `app/passwords/crypto.py` | **Novo** | **Alterado** — inclui `extrair_dominio()` |
| `app/passwords/models.py` | **Novo** | Igual |
| `app/passwords/routes.py` | Modificar — endpoints cofre | **Alterado** — sessão server-side + protecção IDOR em todas as queries |
| `app/templates/passwords/index.html` | Modificar — secção cofre + modais | **Alterado** — aviso perda permanente |
| `app/modulos/config.py` | Modificar — descrição | Igual |
| `chrome-extension/manifest.json` | **Novo** | **Alterado** — sem permissão `scripting` |
| `chrome-extension/background.js` | **Novo** | Igual |
| `chrome-extension/popup.html` | **Novo** | Igual |
| `chrome-extension/popup.js` | **Novo** | Igual |
| `chrome-extension/content.js` | **Novo** | **Alterado** — heurística de captura |
| `tests/test_cofre.py` | **Novo** | **Alterado** — incluir teste dedup + sessão |

---

## Verificação

1. `pip install -r requirements.txt` — instalar deps (inclui Flask-Session)
2. `pytest tests/test_cofre.py` — testes unitários (crypto, modelos, API, dedup)
3. Verificar que `session['cofre_chave']` não está no cookie do browser (DevTools → Application → Cookies)
4. Verificar que CORS devolve 403 para origins não autorizadas
5. Teste de `extrair_dominio()` — confirmar que `www.Exemplo.com`, `EXEMPLO.COM` e `exemplo.com` dão o mesmo resultado
6. Teste manual: activar cofre → criar entrada → ver lista → editar → apagar → alterar password mestra → bloquear/desbloquear
6. Teste CSV: exportar passwords do Chrome, importar via UI, verificar dedup por domínio
7. Extensão: instalar em `chrome://extensions` → Load unpacked → anotar ID → configurar `COFRE_CORS_ORIGINS` → login no PIPE → desbloquear cofre → visitar site com login guardado → captura activa só em forms de login → ver popup com password → preencher

### Checklist de segurança pós-implementação
- [ ] DevTools → Application → Cookies → verificar que `cofre_chave` NÃO aparece no cookie
- [ ] DevTools → Network → verificar `Access-Control-Allow-Origin` devolve `chrome-extension://<id>` (não `*`)
- [ ] Testar com origin errado → deve receber 403
- [ ] Testar esquecimento de master password → confirmar que não há recuperação possível
- [ ] Testar captura activa em form de registo → confirmar que NÃO oferece guardar
