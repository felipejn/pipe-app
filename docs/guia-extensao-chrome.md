# PIPE — Guia rápido: instalar a extensão do Cofre no Chrome

Guia simplificado, passo a passo, para pôr a extensão `chrome-extension/` a funcionar no **Chrome** (o processo é igual no Edge/Brave, mudando apenas `chrome://extensions` por `edge://extensions`).

**Tempo:** ~10 minutos. **Sem loja e sem build:** a extensão é carregada directamente da pasta do projecto («Load unpacked»).

Para o detalhe técnico ver `chrome-extension/README.md` e `docs/plano-cofre-passwords.md`.

---

## Antes de começar

| Precisas de | Onde |
|---|---|
| Chrome actualizado | — |
| Conta no PIPE com sessão iniciada | https://felipejn.pythonanywhere.com/auth/login |
| Cofre activado com password mestra | https://felipejn.pythonanywhere.com/passwords/ |
| Acesso ao `.env` do servidor | PythonAnywhere (produção) ou `.env` local |
| Os ícones `icon48.png` / `icon128.png` | Já incluídos na pasta (Passo 2 só se faltarem) |

> **Regra de ouro:** a extensão só consegue falar com o servidor se este a autorizar por CORS (`COFRE_CORS_ORIGINS`). Sem isso o popup mostra erro de rede/CORS — Passos 4 e 5.

> **Testar primeiro, deploy depois:** podes experimentar tudo **localmente, sem deploy** — ver o Passo 8.

---

## Passo 1 — Activar o cofre no PIPE

1. Inicia sessão no PIPE.
2. Abre o módulo **Passwords** (dashboard → card Passwords) e desce até à secção **Cofre**.
3. Clica **Activar cofre** e define a **password mestra** (mínimo 8 caracteres).
4. ⚠️ **A password mestra não é recuperável.** Não há botão de recuperação: se a esqueceres, o conteúdo cifrado perde-se.
5. Confirma que o card do cofre fica **activado** e **desbloqueado** (é desbloqueado automaticamente logo após a activação).

---

## Passo 2 — Ícones (só se faltarem)

Os ícones `icon48.png` e `icon128.png` estão **já incluídos** na pasta `chrome-extension/` (gerados por `scripts/gerar_icones_extensao.py`). Se existirem, **salta este passo**. Se faltarem, escolhe **uma** das opções:

**Opção A (recomendada) — gerar os ícones** na raiz do projecto, com o venv activo:
```bash
python scripts/gerar_icones_extensao.py
```
Cria `chrome-extension/icon48.png` e `chrome-extension/icon128.png` (quadrado azul `#4361ee` com um cadeado branco, usando o Pillow que já está nas dependências).

**Opção B — usar o ícone genérico:** apaga a chave `icons` do `chrome-extension/manifest.json` (atenção à vírgula que fica pendente na linha anterior):
```json
  "icons": {
    "48": "icon48.png",
    "128": "icon128.png"
  }
```

---

## Passo 3 — Carregar a extensão no Chrome

1. Escreve `chrome://extensions` na barra de endereço.
2. Liga o **Modo de programador** (canto superior direito).
3. Clica **Load unpacked** (*Carregar sem compactação*).
4. Escolhe a pasta `chrome-extension/` do projecto (é a pasta que contém o `manifest.json`).
5. A extensão aparece na lista. Se o ícone não estiver na barra de ferramentas, clica no ícone de puzzle 🧩 → 📌 **Fixar**.

---

## Passo 4 — Copiar o ID da extensão

No cartão da extensão (em `chrome://extensions`) aparece **ID: `abcdefghijklmnopabcdefghijklmnop`**. Clica em copiar — é esse valor (e só esse) que o servidor tem de autorizar no passo seguinte.

---

## Passo 5 — Autorizar a extensão no servidor (obrigatório)

Edita o `.env` do servidor e acrescenta a linha (a variável já existe vazia no `.env.example`):
```
COFRE_CORS_ORIGINS=chrome-extension://<ID copiado no Passo 4>
```
- Vários IDs (ex.: Chrome + Edge, ou vários PCs): separados por vírgula, sem espaços.
- **Produção (PythonAnywhere):** guardar o `.env` → aba **Web** → **Reload** `felipejn.pythonanywhere.com`.
- **Servidor local:** guardar o `.env` → reiniciar `python run.py`.

---

## Passo 6 — Cookies de sessão (porque é que isto funciona)

A extensão faz pedidos a partir de `chrome-extension://`, que o Chrome considera um contexto diferente do servidor. Ainda assim o cookie de sessão chega à extensão, por dois mecanismos:

1. **Host permissions (é o que faz funcionar em local).** O `chrome-extension/manifest.json` declara `"host_permissions": ["<all_urls>"]` e o Chrome trata os pedidos feitos por uma extensão como *same-site* quando esta tem host permissions para o destino — logo um cookie `SameSite=Lax` é enviado. Fonte: *Chrome for Developers → Storage and cookies* («Requests from an extension to a third-party are treated as same-site if the extension has host permissions for the third-party») e o *SameSite FAQ* do Chromium.
2. **Em produção, explícito.** O `ProductionConfig` declara:
   ```python
   SESSION_COOKIE_SAMESITE = 'None'
   SESSION_COOKIE_SECURE = True
   ```
   `None` é a forma documentada de autorizar um cookie cross-site e não depende da isenção do ponto 1. Exige HTTPS, que o PythonAnywhere já serve — **não é preciso mexer em nada**. O CSRF continua protegido pelo token assinado em todos os POSTs, incluindo os da extensão.

⚠️ **Se o popup disser «Sem sessão no PIPE»:** confirma se tens **bloqueio de cookies de terceiros** activo nas definições do Chrome — nesse caso a isenção do ponto 1 não se aplica. Soluções: permitir cookies para o site do PIPE, ou servir o PIPE por HTTPS com `SameSite=None` (ver Passo 8).

---

## Passo 7 — Usar

1. Com a sessão do PIPE iniciada neste Chrome, clica no ícone **PIPE Cofre**.
2. O popup mostra **Cofre bloqueado** → escreve a password mestra → **Desbloquear** (fica desbloqueado 15 minutos — `COFRE_SESSION_TIMEOUT`). Erros aparecem dentro do popup (não há janelas/`alert`).
3. Abre o site onde tens conta → clica no ícone → o popup lista as entradas guardadas desse domínio → **📋** copia a password («Password copiada.» aparece no topo do popup).
4. Ao submeteres um form de login, a extensão captura os dados (aparece um 📝 no ícone) e o popup — **só quando estás no site da captura** — pergunta «Guardar para *&lt;utilizador&gt;*?» → **Guardar**.
5. **Se já existir uma entrada** para esse domínio + utilizador, o popup não falha: mostra «Já existe uma entrada» e o botão **Actualizar entrada**, que grava a password capturada por cima da antiga.
6. Só forms de **login** são capturados — registos e alterações de password são ignorados, e a extensão **não captura no próprio PIPE** (produção nem servidor local) para não guardar as credenciais do PIPE em si.
7. Botões do popup: **↻ Actualizar lista** recarrega as entradas do site actual; **Não** descarta a captura pendente. Uma captura feita noutro site aparece só como nota («Abre esse site para o guardar») — nunca fica pendente para sempre: expira ao fim de 15 minutos.
8. Em separadores que não são sites (`chrome://`, ficheiros, …) o popup diz «Este separador não é um site» — não há entradas a mostrar.

---

## Passo 8 — Testar localmente (sem deploy)

**Não precisas de deploy para experimentar a extensão.** O servidor local tem tudo o que ela precisa: a BD (`instance/pipe.db`, cujas tabelas do cofre são criadas no arranque por `db.create_all()`), a API do cofre e o CORS (lido do `.env`).

Checklist (~5 minutos):

1. **Ícones** — se ainda não fizeste o Passo 2: `python scripts/gerar_icones_extensao.py`.
2. **Carrega a extensão** (Passo 3) e copia o **ID** (Passo 4).
3. **`.env` local** — acrescenta o ID e reinicia o servidor com `python run.py` (fica em `http://127.0.0.1:5000`):
   ```
   COFRE_CORS_ORIGINS=chrome-extension://<ID>
   ```
   Confirma que o `.env` local tem `FLASK_ENV=development` — com `production`, o cookie sai com `Secure` e, sobre HTTP, o browser descarta-o (deixas de conseguir iniciar sessão).
4. **Aponta a extensão ao servidor local** — `chrome://extensions` → cartão da extensão → link **service worker** (abre o DevTools) → consola:
   ```js
   chrome.storage.local.set({ pipeOrigin: 'http://127.0.0.1:5000' })
   ```
5. **Testa** — inicia sessão em `http://127.0.0.1:5000/auth/login`, abre `/passwords/` → secção Cofre, desbloqueia no popup com a password mestra e experimenta: listar/copiar entradas do domínio da aba e capturar um login num site de teste.

**Voltar a produção** (a extensão volta a `https://felipejn.pythonanywhere.com`):
```js
chrome.storage.local.remove('pipeOrigin')
```

| Armadilha local | Efeito | O que fazer |
|---|---|---|
| Servidor noutra porta (5000 ocupada) | a extensão fala com o sítio errado | usar a mesma porta no `pipeOrigin` |
| `FLASK_ENV=production` no `.env` local | cookie `Secure` sobre HTTP → «Sem sessão» | manter `development` |
| Link «Iniciar sessão» do popup | segue o `pipeOrigin` configurado | já resolvido em v1.5.1 — abrir directamente em `http://127.0.0.1:5000/auth/login` se a extensão estiver apontada ao local |
| Bloqueio de cookies de terceiros | o cookie não viaja (Passo 6) | permitir cookies para o site, ou HTTPS + `SameSite=None` |
| Não captura o login | o content script só roda em páginas carregadas após o reload | recarregar a aba do site de teste |

> O **deploy** (definir `COFRE_CORS_ORIGINS` no `.env` de produção — Passo 5 —, `pip install -r requirements.txt` e `db.create_all()`) só é preciso para usar a extensão contra a **produção**. Para o cofre normal no browser (sem extensão), o deploy é o habitual da app.

---

## Actualizar a extensão depois de alterar o código

1. `chrome://extensions` → cartão da extensão → botão **Recarregar** ⟳.
2. Recarrega também (F5) a aba do site em teste — o content script só é injectado em páginas carregadas depois do reload.

---

## Problemas comuns

| Sintoma no popup | Causa provável | Solução |
|---|---|---|
| Erro de rede / CORS | ID em falta ou errado em `COFRE_CORS_ORIGINS`; servidor não recarregado | refazer Passos 4–5 (copiar o ID outra vez) e **Reload** da app / reiniciar o servidor |
| «Sem sessão no PIPE» | sessão terminada; `FLASK_ENV=production` no `.env` local (cookie `Secure` sobre HTTP); ou bloqueio de cookies de terceiros | iniciar sessão em `/auth/login`; ver Passos 6 e 8 |
| «Cofre não activado» | o cofre nunca foi activado (o cofre é **por utilizador**) | Passo 1 |
| «Cofre bloqueado» | passaram 15 minutos desde o desbloqueio | desbloquear outra vez (a sessão de login mantém-se) |
| «Password incorreta» | password mestra errada | — (não há recuperação possível) |
| A extensão não carrega / ícone em falta | `icon48.png` / `icon128.png` ausentes (não deveria acontecer: já vêm na pasta) | Passo 2 |
| A captura não aparece | feita noutro site; form de registo; login dentro de iframe; ou página aberta antes do reload | abrir **o site da captura**; secção «Actualizar a extensão»; guardar à mão no PIPE |
| «Já existe uma entrada» | mesma password guardada duas vezes para o mesmo domínio + utilizador | clicar **Actualizar entrada** (grava a password capturada) |
| A captura desapareceu | passaram 15 minutos (TTL da captura) | submeter o login outra vez |

---

## Verificação de segurança (2 minutos)

- **Cookies:** DevTools → Application → Cookies → não deve existir nenhum cookie com a chave do cofre (só o cookie `session`). A chave vive no servidor, em `instance/flask_session/`.
- **CORS:** DevTools → Network → `Access-Control-Allow-Origin` deve devolver `chrome-extension://<ID>` e **nunca** `*`.
- **Origem não autorizada:** tira temporariamente o ID do `.env` e confirma que o pedido falha (não deve haver resposta utilizável).

---

## Desinstalar

1. `chrome://extensions` → **Remove**.
2. Retira o ID de `COFRE_CORS_ORIGINS` no `.env` e faz **Reload** do servidor.

As entradas continuam no PIPE — a extensão não guarda nada localmente além da captura pendente (`chrome.storage.local`).

---

*Contexto técnico e decisões de segurança: `docs/plano-cofre-passwords.md`. Referência da extensão: `chrome-extension/README.md`.*


