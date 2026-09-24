# PIPE Cofre — Extensão Chrome (Manifest V3)

> **Instalação passo a passo (simplificada): `docs/guia-extensao-chrome.md`.** Este ficheiro é a referência técnica da pasta.

## Instalação

1. Abra `chrome://extensions/`
2. Activa **Modo de programador** (canto superior direito)
3. Clique **Load unpacked**
4. Selecciona a pasta `chrome-extension/`
5. Anota o **ID da extensão** (mostrado na página da extensão)
6. Configura a variável de ambiente no servidor PIPE:
   ```
   COFRE_CORS_ORIGINS=chrome-extension://<ID_DA_EXTENSÃO>
   ```
7. Reinicia o servidor PIPE

> Para testar contra o servidor **local** (sem deploy): `docs/guia-extensao-chrome.md` → Passo 8.

## Permissões

- `activeTab` — acesso à aba activa
- `storage` — guardar captura pendente
- `tabs` — obter URL do separador activo

## Fluxo de uso

1. Inicia sessão no PIPE (`https://felipejn.pythonanywhere.com`)
2. Activa o cofre na página de Passwords
3. Clica no ícone da extensão → desbloqueia com password mestra
4. Visita um site com login → o popup mostra as entradas guardadas
5. Ao submeter um form de login, a extensão pergunta se queres guardar

## Ficheiros

| Ficheiro | Função |
|---|---|
| `manifest.json` | Configuração Manifest V3 |
| `background.js` | Service worker — API calls e captura |
| `popup.html` | Interface do popup |
| `popup.js` | Lógica do popup |
| `content.js` | Content script — captura de forms |

## Segurança

- A password mestra **nunca** é guardada no browser
- A chave AES fica no servidor (Flask-Session filesystem)
- A extensão envia a URL completa ao backend — o servidor extrai o domínio
- CSRF token obtido via `GET /passwords/api/csrf-token`
- `chrome.tabs.sendMessage` usado para preencher (sem permissão `scripting`)
