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
| Os ícones `icon48.png` / `icon128.png` | Passo 2 ⚠️ |

> **Regra de ouro:** a extensão só consegue falar com o servidor se este a autorizar por CORS (`COFRE_CORS_ORIGINS`). Sem isso o popup mostra erro de rede/CORS — Passos 4 e 5.

---

## Passo 1 — Activar o cofre no PIPE

1. Inicia sessão no PIPE.
2. Abre o módulo **Passwords** (dashboard → card Passwords) e desce até à secção **Cofre**.
3. Clica **Activar cofre** e define a **password mestra** (mínimo 8 caracteres).
4. ⚠️ **A password mestra não é recuperável.** Não há botão de recuperação: se a esqueceres, o conteúdo cifrado perde-se.
5. Confirma que o card do cofre fica **activado** e **desbloqueado** (é desbloqueado automaticamente logo após a activação).

---

## Passo 2 — Criar os ícones que faltam ⚠️

O `manifest.json` declara `icon48.png` e `icon128.png`, mas esses ficheiros ainda não existem na pasta `chrome-extension/` — o Chrome assinala ícone em falta ao carregar a extensão. Escolhe **uma** das opções:

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

## Passo 6 — Confirmar o cookie de sessão (só produção)

A extensão faz pedidos **cross-site** (`chrome-extension://` → servidor), pelo que o cookie de sessão tem de viajar com `SameSite=None` (que exige HTTPS). O `ProductionConfig` já traz:
```python
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True
```
e o PythonAnywhere serve por HTTPS — **não é preciso mexer em nada**. Este passo serve apenas para saberes onde olhar se um dia o popup disser «Sem sessão no PIPE».

---

## Passo 7 — Usar

1. Com a sessão do PIPE iniciada neste Chrome, clica no ícone **PIPE Cofre**.
2. O popup mostra **Cofre bloqueado** → escreve a password mestra → **Desbloquear** (fica desbloqueado 15 minutos — `COFRE_SESSION_TIMEOUT`).
3. Abre o site onde tens conta → clica no ícone → o popup lista as entradas guardadas desse domínio → **📋** copia a password.
4. Ao submeteres um form de login, a extensão captura os dados (aparece um 📝 no ícone) e o popup pergunta «Guardar para *&lt;utilizador&gt;*?» → **Guardar**.
5. Só forms de **login** são capturados — registos e alterações de password são ignorados, e a extensão ignora o próprio PIPE.

---

## Passo 8 (opcional) — apontar a extensão para um servidor local

Por omissão a extensão fala com `https://felipejn.pythonanywhere.com`. Para a apontar a `http://127.0.0.1:5000`:

1. `chrome://extensions` → cartão da extensão → link **service worker** (abre o DevTools da extensão).
2. Na consola do DevTools:
   ```js
   chrome.storage.local.set({ pipeOrigin: 'http://127.0.0.1:5000' })
   ```
3. Para voltar ao default:
   ```js
   chrome.storage.local.remove('pipeOrigin')
   ```

⚠️ **Limitação importante:** em desenvolvimento o PIPE usa `SESSION_COOKIE_SAMESITE='Lax'` e o browser **não** envia cookies `Lax` em pedidos cross-site, pelo que o popup responde «Sem sessão no PIPE» mesmo com a sessão iniciada em `127.0.0.1:5000`. Para testar localmente seria preciso servir o PIPE por **HTTPS** com `SameSite=None` (ex.: túnel tipo ngrok/cloudflared). Na prática: **testa contra a produção**.

---

## Actualizar a extensão depois de alterar o código

1. `chrome://extensions` → cartão da extensão → botão **Recarregar** ⟳.
2. Recarrega também (F5) a aba do site em teste — o content script só é injectado em páginas carregadas depois do reload.

---

## Problemas comuns

| Sintoma no popup | Causa provável | Solução |
|---|---|---|
| Erro de rede / CORS | ID em falta ou errado em `COFRE_CORS_ORIGINS`; servidor não recarregado | refazer Passos 4–5 (copiar o ID outra vez) e **Reload** da app / reiniciar o servidor |
| «Sem sessão no PIPE» | sessão do PIPE terminada, ou servidor local com cookie `Lax` | iniciar sessão em `/auth/login`; testar contra a produção |
| «Cofre não activado» | o cofre nunca foi activado (o cofre é **por utilizador**) | Passo 1 |
| «Cofre bloqueado» | passaram 15 minutos desde o desbloqueio | desbloquear outra vez (a sessão de login mantém-se) |
| «Password incorreta» | password mestra errada | — (não há recuperação possível) |
| A extensão não carrega / ícone em falta | `icon48.png` / `icon128.png` ausentes | Passo 2 |
| Não aparece a captura | form de registo, login dentro de iframe, ou página aberta antes do reload | secção «Actualizar a extensão»; guardar à mão no PIPE |

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


