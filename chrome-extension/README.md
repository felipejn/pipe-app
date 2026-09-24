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

1. Inicia sessão no PIPE (`https://felipejn.pythonanywhere.com`, ou o servidor local configurado em `chrome.storage.local.pipeOrigin`)
2. Activa o cofre na página de Passwords
3. Clica no ícone da extensão → desbloqueia com password mestra
4. Visita um site com login → o popup mostra as entradas guardadas desse domínio
5. Ao submeter um form de login, a extensão pergunta se queres guardar — **sabendo que a captura só é oferecida no site onde foi feita** (noutros sites aparece só como nota) e que expira ao fim de 15 minutos
6. Se o domínio + utilizador já existir, o popup mostra «Já existe uma entrada» e oferece **Actualizar entrada** (o `POST /passwords/api/cofre/entradas` devolve 409 com o `id` da existente)
7. Erros e confirmações aparecem **dentro do popup** (`#mensagem`) — o popup não usa `alert()`
8. A extensão **não captura no próprio PIPE** (produção, `pipeOrigin` e rotas `/auth`|`/passwords` em `localhost`/`127.0.0.1`)

## Ficheiros

| Ficheiro | Função |
|---|---|
| `manifest.json` | Configuração Manifest V3 (versão 1.0.1) |
| `background.js` | Service worker — API calls, CSRF e captura |
| `popup.html` | Interface do popup (inclui zona `#mensagem`) |
| `popup.js` | Lógica do popup (estado, captura, guardar/actualizar) |
| `content.js` | Content script — captura de forms (ignora o PIPE) |
| `icon48.png` / `icon128.png` | Ícones gerados por `scripts/gerar_icones_extensao.py` |

## Segurança

- A password mestra **nunca** é guardada no browser
- A chave AES fica no servidor (Flask-Session filesystem)
- A extensão envia a URL completa ao backend — o servidor extrai o domínio
- CSRF token obtido via `GET /passwords/api/csrf-token`
- `chrome.tabs.sendMessage` usado para preencher (sem permissão `scripting`)
