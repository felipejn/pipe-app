# CHANGELOG — PIPE

Todas as mudanças notáveis deste projecto estão documentadas aqui. A fonte de verdade é o histórico Git (https://github.com/felipejn/pipe-app); as descrições de versão foram extraídas e condensadas de `Estado_Atual.md`, e as datas correspondem à data do commit no Git (a menos que indicado).

**Notas de deploy:** todas as alterações de BD requerem um script manual no PythonAnywhere — indicado em `Notas de deploy`. Onde diz "Sem alteração de BD — no PA basta o push + Reload", a versão está no GitHub e o deploy consiste num push seguido de Reload da aplicação no PythonAnywhere.

---

## [v1.5.10] — 2026-10-02
Combustíveis — heurística de deduplicação de postos pela chave conservadora nome+morada+concelho.

**Adicionado**
- Nova função `combustiveis/services.py::obter_ids_duplicados()` — identifica postos que são o **mesmo posto físico** devolvido pela API Aberta sob IDs diferentes (re-atribuição DGEG), com chave conservadora `nome+morada+concelho` normalizados (`casefold` + colapso de espaços) e um vencedor por grupo (activo > posto com preços > recolha mais recente > ID mais baixo).

**Corrigido**
- A exclusão de duplicados passou a ser só no ambiente de leitura (`obter_precos_para_concelhos`, `obter_tipos_combustivel_disponiveis`, contagem `total_postos` do dashboard), complementando `obter_ids_postos_obsoletos()` (dados congelados), sem alteração de BD e reversível sem perda de histórico.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.
- Os "Santos da Cunha 6 - Logística e Transportes, Lda." (IDs `65182`/`65183`/`65184`/`65771`) são **4 estações físicas distintas** do mesmo operador — confirmadas no site do operador — e não são fundidas.
- O par `66475` "E.S. FERREIROS" / `95233` "Posto Ferreiros- ESO305" já estava coberto pelo blocklist `NOMES_IGNORADOS`.
- Uma heurística por *morada+concelho* (como sugeria a pendência original) teria fundido erroneamente estações gémeas reais: "Ilídio Mota - Palmeira 1/2", "CEPSA ÓRFÃOS - I/II" e "REPSOL - BRAGA - PISCINAS I/II". Por isso a chave exige os **três** campos.
- Verificação nos 75 postos reais: 0 duplicados detectados; `sha256` da BD inalterado.
- Novos testes: `tests/test_combustiveis_dedup.py` (11 testes). Suite total: 146 testes pytest.

---

## [v1.5.9.1] — 2026-10-01
Ajuste visual — Assistente IA: cores e contraste dos balões de conversa (claro e escuro).

**Adicionado**
- Novos tokens semânticos no `app/static/css/pipe.css`: `--cor-balao-assistente` (escuro `#2b3149`, claro `#eff2f8`) + `--cor-balao-assistente-borda` (escuro: tinte âmbar `rgba(245,158,11,0.45)`, claro `#c9cdd8`), faixa lateral âmbar de 3px (`border-left`) e relevo subtil (`box-shadow`).
- Tema claro: overrides `[data-theme="light"]` para os balões.
- O balão do utilizador mantém-se âmbar (`#f59e0b`), o assistente não partilha mais `--cor-superficie-2` e fica invisível sobre a superfície do chat.

**Alterado**
- Cache-buster em `app/templates/base.html` passou de `?v=6` para `?v=7`.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload (alteração só no `pipe.css`).
- Validação: CSS com profundidade de chaves equilibrada + **53 testes pytest do Assistente IA** a passar, sem regressão.

---

## [v1.5.9] — 2026-10-01
Calendário — janela de detalhe do evento (read-only) ao clicar no evento.

**Adicionado**
- Novo modal read-only `#modal-detalhe` (`app/templates/calendario/index.html`): barra de cor, título, data pt-PT (duas datas se multi-dia), intervalo `HH:MM – HH:MM` ou "Dia inteiro", localização, descrição e badge de notificação; botões **Editar** (fecha o detalhe e abre o modal de edição), **Apagar** (`confirm` + `DELETE`) e **Fechar**.
- Funções inline: `abrirDetalhe()`, `editarEDetalhe()`, `apagarEDetalhe()`, `fecharDetalhe()`/`fecharDetalheOverlay()`, `formatarDataDetalhe()`, `formatarHoraDetalhe()`.
- Gatilho trocado: clicar na pílula (vista Mensal) ou linha (vista Agenda) abre o detalhe; os botões rápidos ✏️/🗑️ mantêm-se com `event.stopPropagation()`.
- CSS `.detalhe-*` no tema escuro + overrides `[data-theme="light"]` (paleta Google Calendar).

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload (sem bump do cache-buster — alterações só no `<style>`/`<script>` inline do template; os dados vêm da API `GET /calendario/api/eventos` já existente).
- Validação: 135 testes pytest a passar + renderização de `GET /calendario/` com os marcadores do modal presentes + `node --check` no JS inline (exit 0).

---

## [v1.5.8] — 2026-10-01
Notificações — avisos de tarefas no dia do prazo + lembretes de eventos no calendário (`pipe_tasks.py`).

**Adicionado**
- `tarefa_tarefas()`: avisar também **no dia do prazo** (`data_limite <= hoje`) e em todos os dias de atraso até concluir (1 mensagem por utilizador: secções "Vencem hoje" / "Em atraso", `tipo='tarefa_lembrete'`).
- Nova `tarefa_calendario()`: lembretes de eventos **no dia anterior** ("Amanhã") e **no dia** ("Hoje"), agrupados por utilizador (`tipo='evento_lembrete'`), ignorando eventos já iniciados e respeitando o toggle `notificar`.

**Alterado**
- Campo único `Evento.notificado_em` cobre os dois avisos: véspera grava D−1, dia do evento grava D — **sem migração de BD**.
- `app = create_app()` movido para dentro de `if __name__ == '__main__'` (importar o script não cria mais a app com a BD real).
- Hora da scheduled task corrigida para **07:00** em todo o lado (docstring e `Estado_Atual.md` diziam 23:00/08:00).

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.
- Novo `tests/test_pipe_tasks.py` (13 testes, `notification_service.send` mockado).

---

## [v1.5.7] — 2026-10-01
Tarefas — listas predefinidas no registo de contas novas.

**Adicionado**
- Novo ficheiro `app/tarefas/seed.py` com a constante `LISTAS_PREDEFINIDAS` (Pessoal 📌, Casa 🏠, Trabalho 💼, Compras 🛒 — ordem 0–3, emoji em `String(8)`) e a função `semear_listas_predefinidas(user_id)`.
- A função é chamada por `registo_com_convite` (`app/auth/routes.py`) logo após o `flush()` do utilizador — num único commit, tudo ou nada. É idempotente: só semeia se o utilizador não tiver **nenhuma** lista (nunca apaga nem duplica).

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.
- Só afecta contas novas; contas existentes mantêm as listas (decisão: semear apenas no registo).
- Novo `tests/test_tarefas_listas_predefinidas.py` (registo ponta a ponta via convite + não-alteração de listas existentes + idempotência). Suite total: 122 testes.

---

## [v1.5.6] — 2026-10-01
Calendário e Tarefas — ajustes de frontend: vista mensal por defeito, modo claro estilo Google Calendar, concluídas ocultas.

**Alterado**
- **Calendário — vista Mensal por defeito:** tab «Mensal» activa, `#vista-agenda` oculto, `vistaActual = 'mensal'`, init a chamar `mudarVista('mensal')`.
- **Calendário — modo claro estilo Google Calendar:** nova secção prefixada `[data-theme="light"]` no template (superfícies brancas, bordas `#dadce0`, texto `#3c4043`/`#70757a`, hover `#f1f3f4`, overlay `rgba(32,33,36,0.55)`), mantendo acentos âmbar PIPE; anel do selector de cor passa de branco para âmbar.
- **Calendário — cores:** 11 overrides `[data-theme="light"] .cal-pilula.evento-<cor>` no `pipe.css` (fundo tintado + texto escuro, pares estilo Google/Material), aplicados apenas às pílulas; botão Apagar do modal em vermelho Google `#c5221f`.
- **Tarefas — concluídas ocultas:** `#lista-concluidas` arranca com `display:none` e botão "▸ mostrar", aberto apenas quando `filtro == 'concluidas'`; `filtrarTarefas()` ganha `FILTRO_ACTUAL` via `tojson`.

**Alterado**
- Cache-buster em `base.html` de `?v=5` para `?v=6`.
- Modo escuro intocado.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload (service worker network-first para CSS/HTML).
- Validação: 119 testes pytest + smoke de 22 verificações com `create_app('testing')`.

---

## [v1.5.5] — 2026-09-30
Assistente IA — filtro por posto em `get_combustiveis` e entrega de resultados grandes.

**Adicionado**
- Novo argumento `posto` em `get_combustiveis` (`app/assistente/ferramentas.py`): compara com **nome e marca**, insensível a acentos/maiúsculas; aplica-se antes de `apenas_mais_barato`; error orientador com até 15 postos sugeridos (`LIMIAR_POSTOS_SUGERIDOS = 15`) quando não encontra.
- `get_resumo_geral` alarga (concelhos de combustíveis, nº de postos com preço, mais barato por combustível ou nota de que falta configurar).

**Corrigido**
- Serialização de resultados degradável progressivamente (`LIMITES_ITENS_DEGRADACAO` = 10 → 8 → 5 → 3 → 1 itens) em vez de descartar o resultado inteiro quando excede o tecto `LIMITE_CHARS_TOOL_RESULT` (2000).
- Payload de `get_combustiveis` sem `morada`/`data_recolha` por registo (frescura global em `recolha`; DGEG em `data_dgeg`): 14 registos = 2 294 chars, lista do concelho chega com 8 de 14 registos sem aviso.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.
- Validação: 119 testes pytest (novo `tests/test_assistente_contexto_truncagem.py` + 11 casos de `posto`) + smoke real contra a BD (75 postos): "Pingo Doce de Vila Verde" + gasóleo → `PD VILA VERDE` a 2,129 €/L; sem filtros, 213 registos em 1 759 chars (antes: aviso, zero dados).

---

## [v1.5.4] — 2026-09-30
Cofre — distribuição da extensão Chrome a partir do próprio PIPE.

**Adicionado**
- Rotas `GET /passwords/extensao/download` (ambos `@login_required`, `app/passwords/routes.py`): gera ZIP em memória da pasta `chrome-extension/` (nome `pipe-cofre-extensao-<versão>.zip`, prefixo `chrome-extension/` em cada entrada) e página do guia em HTML (`app/templates/passwords/guia_extensao.html`, conversão de `docs/guia-extensao-chrome.md`).
- Bloco CSS escopado `.guia-extensao`/`.guia-nota` no `pipe.css` e entrada na página `/passwords/` com os botões de download e guia.
- Novo `tests/test_extensao_distribuicao.py` (8 testes: conteúdo do ZIP, manifest MV3, exigência de sessão, guia, entry point).

**Corrigido**
- Constantes do Assistente IA (`MODELO_DEFAULT`/`_MODELOS_FALLBACK_BRUTOS` em `tests/test_assistente_cliente.py`) actualizadas para a fila da v1.5.3 — correção pré-existente do commit `ecf154d`.

**Alterado**
- Cache-buster em `base.html` de `?v=4` para `?v=5` (lição da v1.4.14 — nginx do PA cacheia estáticos).

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload (a pasta `chrome-extension/` já vem no repositório).
- Suite total: 98 testes pytest (eram 90).

---

## [v1.5.3] — 2026-09-29
Assistente IA — fila de modelos reordenada.

**Alterado**
- Modelo principal: `inclusionai/ling-3.0-flash-sante:free` (default em `app/assistente/cliente.py` e via `OPENROUTER_MODEL` no `.env`).
- Removidos `nex-agi/nex-n2.5-mini:free` e `inclusionai/ling-3.0-flash-fin:free`; adicionado `poolside/laguna-s-2.1:free` como 2.º fallback.
- Nova ordem: `ling-3.0-flash-sante` → `poolside/laguna-s-2.1` → `liquid/lfm-2.5-2.6b` → `nvidia/nemotron-3-super-120b` → `nvidia/nemotron-3-ultra-550b`.
- `dots-studio/dots-3-note-preview:free` testado (erro de tool calls 4.75%, structured outputs 25.08%) e descartado.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.

---

## [v1.5.2] — 2026-09-25
Convites — confirmação de entrega dos emails no Mailjet + verificação no painel.

**Adicionado**
- `EmailChannel.enviar()` guarda o resultado em `self.ultimo_resultado` (`MessageID` + motivo de falha; retorno bool mantém-se); ganha `consultar_estado(message_id)` (consulta `/REST/messagehistory/{id}` + `/REST/message/{id}`, com estado, cronologia de eventos e motivo do bounce).
- Modelo `Convite`: 3 colunas novas (`mailjet_message_id`, `email_estado`, `email_verificado_em`) + método `estado_email()`.
- Novo endpoint `GET /admin/convites/<id>/estado-email` (400 sem ID, 502 se o Mailjet falhar, nunca destrói estado anterior; guarda `email_verificado_em`); a tabela `/admin/convites` ganha coluna "Email (Mailjet)" com badge + botão 🔄 (hover com cronologia + motivo).
- Script `scripts/verificar_mailjet.py --ligar-convites` liga convites antigos sem ID (pareamento por email + proximidade ≤ 2h) — os 2 convites existentes já estão ligados (`gardengate` → `1152921544892419067`, `yahoo` → `288230416497838458`, ambos `sent`).
- Scripts de migração/diagnóstico com stdout UTF-8 corrigidos (bug do Windows cp1252) e `try/except` de rede em `_email_do_contacto`.

**Corrigido**
- Causa raiz da deliverability: `MAILJET_FROM_EMAIL=pipe.notificacoes@outlook.com` não estava alinhado com SPF/DKIM → DMARC falha → Gmail rejeita (`550 5.7.40`) e o resto vai para spam. **Resolvido** fora do CHANGELOG: domínio próprio autenticado no Mailjet + `MAILJET_FROM_EMAIL=pipe@<domínio-próprio>` — os emails de convite já não caem em spam.

**Notas de deploy**
- **Alteração de BD — obrigatório no PythonAnywhere após o deploy:** `python scripts/migrar_convites_mailjet.py` (adiciona as 3 colunas em `convites`; idempotente — o `create_all()` não faz `ALTER TABLE`, e sem as colunas as queries ao modelo rebentam com `no such column`).
- Novo `tests/test_convites_email.py` (+14 testes: canal, geração, endpoint, renderização da página, caminhos de falha). Suite total: 90 testes pytest + `node --check` no JS extraído do template.

---

## [v1.5.1] — 2026-09-24
Extensão Chrome do Cofre — quatro correções de captura/409/alerts.

**Corrigido**
- **Captura presa em todos os separadores:** `pendingCapture` passou a ser limitado ao site de origem (comparação por domínio via `dominioDeUrl()`) com TTL de 15 min (`COFRE_SESSION_TIMEOUT`); noutros sites aparece só como nota informativa com opção de descartar.
- **O PIPE era capturado:** `content.js` agora ignora a origem configurada (`pipeOrigin`), a produção e as rotas `/auth`|`/passwords` do servidor local (`localhost`/`127.0.0.1`, qualquer porta).
- **«Guardar» falhava sem saída:** 409 passa a devolver `id`/`dominio`/`username` → popup oferece "Actualizar entrada" (PUT) em vez de erro.
- **`alert()` no popup:** todos substituídos por mensagens inline em `#mensagem`; botão 📋 copiar corrigido (`onclick` inline bloqueado pela CSP MV3 → listeners por JS); botão de refresh renomeado para "↻ Actualizar lista"; links de login seguem `pipeOrigin` configurado; `background.js` propaga `status`/`dados` dos erros.

**Alterado**
- `manifest.json` → versão **1.0.1**; ícones `icon48.png`/`icon128.png` incluídos (gerados por `scripts/gerar_icones_extensao.py`).
- Novo teste de regressão `tests/test_cofre.py::test_duplicado_devolve_id_e_actualiza_pela_extensao` + `tests/test_extensao_js.py` (harness Node: 22 verificações sobre content script e funções puras do popup).

**Notas de deploy**
- **Sem alteração de BD** (apenas um campo novo no JSON do 409). No PythonAnywhere: push + Reload.
- Suite total: 76 testes pytest (eram 74).

---

## [v1.5.0] — 2026-09-24
Cofre de Passwords com extensão Chrome MV3.

**Adicionado**
- Módulo Passwords deixou de ser stateless: novas tabelas `cofre_configs` + `cofre_passwords`; novo `app/passwords/crypto.py` (AES-256-GCM, chave de 32 bytes derivada por PBKDF2-SHA256 com `COFRE_KDF_ITERATIONS = 600 000`, verificação da password mestra por bcrypt).
- Chave cifrada só em Flask-Session server-side (`SESSION_TYPE='filesystem'`, `instance/flask_session/`), expira em `COFRE_SESSION_TIMEOUT = 900 s`; expira apenas as chaves do cofre (`session.pop`), sem deslogar o utilizador.
- API `/passwords/api/cofre/*` (estado, activar, desbloquear, bloquear, alterar-password, CRUD, importar-CSV do Chrome), sempre filtrada por `user_id` (anti-IDOR) + deduplicação por domínio normalizado (`extrair_dominio()`, única fonte de verdade).
- Novo `GET /passwords/api/csrf-token` (token **assinado**, `generate_csrf()`) para o JS do cofre e a extensão; `base.html` expõe o token por `<meta name="csrf-token">`.
- Segurança cross-site: CORS restrito por `COFRE_CORS_ORIGINS` (`chrome-extension://<ID>`), `SESSION_COOKIE_SAMESITE='None'` + `Secure=True` em produção (`Lax` em desenvolvimento).
- Extensão Chrome MV3 em `chrome-extension/` (manifest, service worker, popup, content script com heurística de captura só em forms de login; origem configurável em `chrome.storage.local.pipeOrigin`, default PythonAnywhere).

**Corrigido**
- Regressão de BD: um `pytest` apagou `instance/pipe.db` (`test_cofre.py` reescrevia `SQLALCHEMY_DATABASE_URI` depois de `create_app()` — engine fixado em `db.init_app()`; `drop_all()` apagou 21 tabelas). Correções: `TestingConfig` define tudo o que é lido em `create_app()` (SQLite em memória + `SESSION_FILE_DIR` temporário), `tests/conftest.py` bloqueia `db.drop_all()` com BD de ficheiro, regressão em `tests/test_isolamento_bd.py`, `scripts/criar_admin.py` passa a criar com `is_admin=True` (sem isso ficava-se sem acesso), novo `scripts/backup_bd.py` (mantém as últimas 10 cópias em `instance/backups/`). `sha256` da BD verificado inalterado em corridas completas.

**Notas de deploy**
- **Alteração de BD — obrigatório no PythonAnywhere:** `pip install -r requirements.txt` (Flask-Session, flask-cors, cryptography, bcrypt) + `db.create_all()` (cria `cofre_configs`/`cofre_passwords` no primeiro reload) + `COFRE_CORS_ORIGINS` no `.env` + Reload. Confirmar `SESSION_COOKIE_SAMESITE=None` em produção.
- Novo `tests/test_cofre.py` (31 testes — ciclo completo: activar, desbloquear, CRUD, alterar-password, dedup, bloqueio por inactividade, isolamento) + plano de correcção em `docs/plano-cofre-passwords.md`. Suite total: 74 testes pytest (eram 42).

---

## [v1.4.15] — 2026-09-23
Assistente IA — limites de caracteres no histórico de sessão.

**Adicionado**
- `MAX_CHARS_POR_MENSAGEM = 3000` (cada mensagem truncada) e `MAX_CHARS_HISTORICO_TOTAL = 8000` (orçamento total do histórico em sessão, com remoção automática das mensagens antigas); `max_tokens: 1000` no payload da OpenRouter.
- Funções auxiliares em `assistente/contexto.py`: `_truncar_listas()` (corte estrutural de listas, evita JSON inválido), `_serializar_resultado_tool()` (tecto final de 2000 chars no JSON das tool results), `_limpar_historico()` (3 cortes sucessivos: por mensagem, remoção de antigas, orçamento total) e `_tamanho_historico()`.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.
- O corte só afeta o que fica guardado para pedidos seguintes, nunca a resposta actual.

---

## [v1.4.14 (fix)] — 2026-09-21
Caching estático — correção do cache-buster no PythonAnywhere.

**Corrigido**
- O nginx do PythonAnywhere cacheia ficheiros estáticos ignorando query params; o `pipe.css` com as regras de tabelas Markdown foi actualizado mas o `base.html` ainda usava `?v=3` → a produção carregava o CSS antigo sem as regras. Incrementado para `?v=4` no `<link>` do CSS e no `<script>` do JS.
- Commit `70a8d12`. Lição: bumpar o cache-buster **e** verificar em produção (o service worker também precisa de bump).

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.

---

## [v1.4.13] — 2026-09-21
Assistente IA — renderização de **tabelas** Markdown no chat.

**Adicionado**
- Função `processarTabela()` inline em `app/templates/assistente/index.html` (~40 linhas de regex vanilla): detecta blocos Markdown (`| cabeçalho |`, `|---|`, `| dados |`) e converte em `<table>` com `<thead>`/`<tbody>`.
- Regras CSS em `app/static/css/pipe.css` para `.chat-bubble table`, `th`, `td`, `tr:hover` — respeitam tokens claro/escuro.
- O parsing de tabelas ocorre **antes** do de parágrafos, capturando primeiro os blocos de tabela.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.

---

## [v1.4.12] — 2026-09-21
Assistente IA + Combustíveis — ferramenta `get_combustiveis` e boas-vindas curtas.

**Adicionado**
- Nova ferramenta de leitura `get_combustiveis(user_id, tipo_combustivel=None, concelho=None, apenas_mais_barato=False, limite=20)` (`app/assistente/ferramentas.py`): delega em `combustiveis_services.obter_precos_para_concelhos` (herda exclusão de postos arquivados/obsoletos e `NOMES_IGNORADOS); normalização de acentos via `_normalizar_texto()` (NFD + remoção de diacríticos) para match de concelhos e combustíveis; resposta inclui sempre `recolha` (`ultima_atualizacao`, `ultima_execucao_sucesso`, `mensagem_erro`).
- `get_resumo_geral` alarga (concelhos, nº de postos com preço, mais barato).
- System prompts (`SYSTEM_PROMPT_LEITURA`/`SYSTEM_PROMPT_ESCRITA`) mencionam combustíveis (regra: nunca inventar postos/preços/concelhos, €/L com 3 casas, citar data da recolha).

**Alterado**
- Boas-vindas do chat de 9 linhas para 3 (saudação + estado do modo + "Em que posso ajudar?"); capacidades移 para o subtítulo do cabeçalho.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.
- Validação: `tests/test_assistente_combustiveis.py` (20 testes, 42 no total); smoke directo contra BD real (Vila Verde, mais barato `PD VILA VERDE` a 2,113 €/L) + smoke ponta a ponta contra a OpenRouter ("Onde está o gasóleo mais barato?" → tool call correcta; "preço em Lisboa?" → encaminha para Definições).
- **Combustíveis fase 1.3.x:** este é o ponto em que o módulo é integrado no Assistente IA (o módulo foi introduzido na v1.4.2).

---

## [v1.4.11] — 2026-09-21
Assistente IA — renderização de **Markdown** no chat.

**Adicionado**
- Função `markdownToHtml()` inline em `app/templates/assistente/index.html` (~60 linhas de regex vanilla): converte `**negrito**`, `*itálico*`, `# headers`, `- listas`, ```blocos de código```, ``inline``, `> citações`, links em HTML, aplicado a `wrapper.innerHTML`.
- Fluxo: `escaparHtml(texto)` (XSS) → `markdownToHtml()` (sintaxe).
- Regras CSS em `pipe.css` para `.chat-bubble strong`, `em`, `code`, `pre`, `ul`, `li`, `blockquote`, `h3/h4/h5`, `a` — tokens claro/escuro.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.

---

## [v1.4.10] — 2026-09-18
Combustíveis — regra geral de obsolescência (30 dias) + inclusão do DJB no blocklist.

**Adicionado**
- Constante `MAX_DIAS_PRECO_ATIVO = 30` e helper `obter_ids_postos_obsoletos()` — exclui no ambiente de leitura (`obter_precos_para_concelhos`, `obter_tipos_combustivel_disponiveis`, contagem `total_postos` do dashboard) postos cuja actualização DGEG tem mais de 30 dias ou cujo nome está bloqueado.

**Corrigido**
- `DJB COMBUSTIVEIS` (id 69288, dados de Abr/2026) incluído em `services.NOMES_IGNORADOS`; `scripts/remover_postos_ignorados.py` agora também limpa o DJB.
- Abordagem por ignorar (não arquivar), intencional: estes postos voltam em todas as recolhas (`ciclos_ausente=0`), o arquivamento automático não os apanha e um `ativo=False` seria revertido; a regra também cobre casos futuros sem lista manual, é reversível e preserva o histórico.

**Notas de deploy**
- **Alteração de BD — obrigatório no PythonAnywhere após o deploy, antes de abrir o dashboard:** `python scripts/remover_postos_ignorados.py` (idempotente; pode correr antes ou depois do reset).
- Validação: recolha forçada confirma 76 → 75 postos, sem regressão dos nomes bloqueados nem dos 4 homólogos frescos; mínimo gasolina 95 passa de 1,935 € (DJB) para 1,959 € (PLENERGY - BRAGA I); deteta um posto falso com dados de 8 meses; rollback confirma BD inalterada. 22 testes pytest.

---

## [v1.4.9] — 2026-09-18
Combustíveis — blocklist de postos obsoletos (fase 1.3.3) e limpeza na BD.

**Adicionado**
- Constante `NOMES_IGNORADOS` em `services.py` (E.S. FERREIROS, E.S. BRAGA PISCINAS I, E.S. BRAGA PISCINAS II, BP Braga João 21) + auxiliar `_nome_ignorado()` (comparação normalizada, insensível a caixa e espaços nas pontas).

**Corrigido**
- O filtro é a **primeira instrução** do ciclo de registos — os postos da lista nunca são criados, actualizados nem reactivados; se já existirem na BD, não contando como vistos, o arquivamento automático esconde-os ao 2.º ciclo (auto-curativo).
- Limpeza: `scripts/remover_postos_ignorados.py` (apaga os postos ignorados e o respectivo histórico por causa da FK; idempotente) — 80 → 76 postos, 12 registos de preço.

**Notas de deploy**
- **Sem alteração de BD** (a limpeza é um script de manutenção, não uma migração de esquema). No PythonAnywhere: `python scripts/remover_postos_ignorados.py`.
- Validação: recolha forçada após a limpeza confirma 76 → 76; card de gasóleo simples corrigido de 1,919 € (falso, Jul/2026) para 2,049 € (hoje). "DJB COMBUSTIVEIS" mantido por decisão explícita (não é duplicado; lidera o card de gasolina 95 com dados de Abril/2026 — polui o card e deve ser removido manualmente se necessário). 22 testes pytest.

---

## [v1.4.8] — 2026-09-18
Combustíveis — arquivamento automático de postos ausentes (fase 1.3.2) + reinício das tabelas.

**Adicionado**
- Novos campos `Posto.ativo` (Boolean, default `True`) e `Posto.ciclos_ausente` (Integer, default 0); constante `LIMIAR_CICLOS_AUSENTE = 2`.
- Cada recolha incrementa `ciclos_ausente` dos activos que não vieram na resposta; ao atingir 2 o posto vai para `ativo=False`. Reactivação automática ao reaparecer (`ativo=True`, `ciclos_ausente=0`).
- Arquivamento condicionado a recolhas sem erros (`len(erros) == 0`); filtro `Posto.ativo == True` em `obter_precos_para_concelhos` e na contagem do dashboard; chave `postos_arquivados` no retorno e no flash (com concordância singular/plural).

**Alterado**
- Reinício completo das tabelas de postos e histórico com `scripts/reset_postos_combustiveis.py` — preservando as definições do utilizador (95 → 80 postos).

**Notas de deploy**
- **Alteração de BD — obrigatório no PythonAnywhere após o deploy, antes de abrir o dashboard:** `python scripts/reset_postos_combustiveis.py` (drop das tabelas `combustiveis_precos_historico` + `combustiveis_postos` + `db.create_all()` + repovoamento imediato; cria as colunas `ativo`/`ciclos_ausente` que o `create_all()` sozinho não acrescenta; não toca em `combustiveis_utilizador_concelho` nem em `combustiveis_utilizador_combustivel`).
- Validação: 22 testes pytest + testes manuais (arquivamento ao 2.º ciclo, reactivação, 2.ª recolha sem subir contadores, render do dashboard e flash).

---

## [v1.4.7] — 2026-09-18
Assistente IA — ferramenta `get_cambio` com taxas em tempo real.

**Adicionado**
- Nova ferramenta de leitura `get_cambio(user_id, origem, destino, valor)` (`app/assistente/ferramentas.py`): converte entre moedas com taxas Wise v3 + fallback ExchangeRate-API (stateless, validação case-insensitive contra `MOEDAS`, `valor > 0`, erros em PT-PT).

**Alterado**
- Refactor do módulo Câmbio: lógica extraída de `routes.py` para o serviço partilhado `app/cambio/service.py` (`MOEDAS` + `obter_taxa()`); rota `/cambio/api/convert` sem alteração de comportamento; prompts e chat actualizados a mencionar câmbios.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.
- Validação: 22 testes pytest + smoke real via `executar_ferramenta('get_cambio', EUR→USD)` → resultado 3.92, taxa 0.784; casos de erro (moeda inválida, valor ≤ 0/não numérico, serviço indisponível) devolvem `{'erro': ...}`.

---

## [v1.4.6] — 2026-09-18
Assistente IA — correção da lentidão (modelos agentic-only e ID inválido).

**Corrigido**
- Causa raiz: `OPENROUTER_MODEL` em `.env` apontava para `thinkingmachines/inkling-small:free` (restrito a *agentic harnesses*, HTTP 403 em aplicações comuns); cada pergunta perdia tempo nessa falha antes de cair no fallback.
- `.env` e `.env.example` e o default em `app/assistente/cliente.py` actualizados para `inclusionai/ling-3.0-flash-fin:free` (os dois coerentes).
- Removidos `thinkingmachines/*` de `_MODELOS_FALLBACK`; ID inválido `liquid/lfm2.5-2.6b:free` corrigido para `liquid/lfm-2.5-2.6b:free` (hífen em falta).

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.
- IDs confirmados no catálogo do OpenRouter (`/api/v1/models`) e por smoke test real (resposta em 0.9s com tool call, PT-PT). 22 testes unitários a passar.
- Pós-deploy: `ling-3.0-flash-fin` sofre limites intermitentes por upstream (HTTP 429) — o fallback assume automaticamente, comportamento esperado, sem perda de resposta. Descartado desactivar o *reasoning* globalmente (o `liquid/lfm-2.5-2.6b` exige-o por HTTP 400).

---

## [v1.4.5] — 2026-09-17
Assistente IA — ferramenta `get_eventos` e auditoria de ficheiros.

**Adicionado**
- Quinta ferramenta de leitura `get_eventos(user_id, data=None, futuros=False)` (`app/assistente/ferramentas.py`): preenche a lacuna do Calendário (query filtrada por `user_id`, data específica `AAAA-MM-DD`, eventos futuros).
- Indicador visual do modelo utilizado no chat (`<small class="chat-modelo">`).

**Corrigido**
- Import `from datetime import date, datetime, timedelta` (correcção de import).
- Auditoria de ficheiros: removidos código morto/residual (`app/static/js/passwords.js`, scripts de depuração de rede da OpenRouter) e briefings antigos movidos para `docs/historico/`.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.
- Validação: 22 testes pytest.

---

## [v1.4.4] — 2026-09-17
Assistente IA — correção de bug crítico do fallback.

**Corrigido**
- Sintoma: `processar_mensagem_assistente('cria um evento para amanhã: "Cortar cabelo" às 9 horas')` devolvia "Não consegui gerar uma resposta".
- Causa: o OpenRouter devolve **HTTP 200 com corpo `{"error": ...}`** quando o provider upstream falha; o código original só chamava `raise_for_status()` (200 passava como sucesso) e a chamada estava **fora do `try`**, abortando a cadeia de fallback.
- Correção em `app/assistente/cliente.py`: classes `RateLimitError` e `ServicoIndisponivelError`, constante `_MODELOS_FALLBACK`, função `_classificar_resposta()` que valida HTTP e corpo (distinguindo `rate_limit` / `modelo_indisponivel` / `servico` / `ok`), `chamar_llm()` com fallback imediato em qualquer falha de provider e backoff apenas para exceções de rede.
- Reforço em `app/assistente/contexto.py`: parsing defensivo de `choices` (verificação de tipo), `tool_calls` com validação de tipo, `content` vazio aceite, `argumentos` aceita `str` ou `dict`, `ServicoIndisponivelError` tratado no ciclo.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.
- Validação: 21 testes unitários offline; smoke test real contra OpenRouter com `cohere/north-mini-code:free` criou evento com sucesso (ID 4).

---

## [v1.4.3] — 2026-09-16
Caching — fix pós-deploy (Service Worker + cache HTTP + cache-buster).

**Corrigido**
- CSS e alternância de tema não chegavam aos utilizadores após deploy (SW `pipe-v2` e cache HTTP de 12h serviam ficheiros antigos). Três alterações:
  1. `app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0` em `app/__init__.py` (desactiva cache HTTP de estáticos).
  2. Service Worker `pipe-v2` → `pipe-v3` (`activate` handler já tinha `skipWaiting()` + `clients.claim()`).
  3. Cache-busting `?v=3` no link do CSS em `app/templates/base.html` (+ `?v=3` no JS, commit `8ccf4c9`).

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.

---

## [v1.4.2] — 2026-09-16
Calendário + Combustíveis (fase 1.3.x) + paleta Keep no notas + contraste.

**Adicionado**
- **Calendário (v1.2):** vistas Agenda + Mensal, CRUD completo via API (`/calendario/api/eventos`), modal único de criar/editar, paleta de 11 cores, integração na Loja de Módulos (`app/calendario/`, `app/templates/calendario/`, `tests/test_calendario.py` implícito).
- **Combustíveis (fase 1.3.x):** recolha via **API Aberta** (`api.apiaberta.pt/v1/fuel/stations`, autenticada com `X-API-Key`) para Braga/Vila Verde/Amares; dashboard filtrado; definições de concelhos+combustíveis; tarefa agendada `tarefa_combustiveis` (terças) em `scripts/pipe_tasks.py`; primeira recolha completa com 95 postos.
- **Notas:** paleta Google Keep — 8 cores vibrantes aplicáveis em tema claro e escuro.

**Corrigido**
- **Combustíveis (fase 1.3.1):** bug de paginação corrigido (`return` dentro do `while` em `_paginar_fuel` devolvendo apenas a página 1 — só 4 de 95 postos); `return` ao nível da função + guarda `PAGINAS_MAX = 60`; filtro `district=Braga` (a API não honra `municipality`/`concelho`); deduplicação de histórico (só grava quando `preco` ou `data_atualizacao_dgeg` mudam); retorno honesto ("X postos verificados, Y registos novos" vs "sem alterações"); `ultima_atualizacao` marcada só em sucesso (retry no mesmo dia); rate limit 6/hora em `POST /combustiveis/atualizar`.
- **Notas (fix de contraste, v1.4.2):** texto forçado a preto em cartões coloridos via `.nota-com-cor` + fallback `var(--nota-texto, var(--cor-texto))` nas classes do editor (`NotaEditartitulo`, `nota-editar-textarea`, `checklist-editar-input`) em ambos os temas.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload.
- `Estado_Atual.md` agrupa Calendário + Combustíveis + paleta Keep + contraste na v1.4.2 (a fase 1.3.1 dos Combustíveis entra aqui).

---

## [v1.4.1] — 2026-09-16
Notas — paleta de cores Google Keep.

**Alterado**
- Módulo Notas: cores escuras substituídas pela paleta Google Keep (8 cores: `#F28B82`, `#FBBC05`, `#FFF475`, `#CCFF90`, `#CBF0F8`, `#D7AEFB`, `#E8EAED`) — aplicáveis em tema claro e escuro.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload (`Nota.CORES`, `_cartao.html`, `index.html` actualizados; `editar.html` reutiliza a mesma fonte via `tojson`).

---

## [v1.4.0] — 2026-09-16
Tema claro/escuro concluído e navegação secundária.

**Adicionado**
- Tema claro/escuro: tokens semânticos em `:root` (~23 cores fixas substituídas por variáveis) + sobreposição via `[data-theme="light"]`; alternador 🌙/☀️ em `.navbar-utilizador` (`pipe.js`, IIFE com guarda), persistido em `localStorage['pipe-tema']` (default `dark`); anti-FOUC no `<head>` do `base.html`; service worker network-first para CSS/JS/HTML (cache `pipe-v2`).
- Navegação secundária "Voltar / Home" em `base.html` (todas as páginas excepto dashboard; `javascript:history.back()` + `url_for('dashboard')`).
- PWA: `manifest.json`, `sw.js` (network-first com cache `pipe-v2`, cache-first offline), ícones `icons/icon-192.png`/`icon-512.png`, `theme-color` âmbar, modo standalone iOS.

**Notas de deploy**
- **Sem alteração de BD.** No PythonAnywhere: push + Reload + recarregar a página 2 vezes no browser para o service worker novo activar.
- Validação: tema e ícone alternam; escolha persiste após reload; anti-FOUC sem flash; 22 testes pytest.

---

## Histórico anterior (antes de 2026-09-16) — referências Git

A `Estado_Atual.md` não descreve versões "v1.x" para este período; ficam registados os marcos mais relevantes extraídos directamente do Git:

- **2026-03-13 — Scaffold (`ce025d2`):** módulo Euromilhões.
- **2026-03-13 a 2026-03-18 — Módulos básicos:** Tarefas (`app/tarefas/`), Notícias (`app/notes/` — depois Notas), ficheiros PWA (`5c09d27`), PWA Ponto (`3510510`).
- **2026-03-14 a 2026-03-17 — Auth & admin:** sistema de notificações (Telegram + SendGrid), 2FA (Telegram, Email, TOTP via `pyotp`), recuperação de password por email, área admin com gestão de utilizadores, campo `is_admin`, área admin com gestão de utilizadores, campo `is_admin`, área admin com gestão de utilizadores, campo `is_admin`, área admin com gestão de utilizadores, campo `is_admin`.
- **2026-03-24 a 2026-04-06 — Módulos de utilidade:** Passwords (`app/passwords/`), Cores Flutter (091fb028), Conversões HEIC→JPG, Câmbio (EWRATE-API → Wise API v3 com fallback), Loja de Módulos (`app/modulos/`).
- **2026-04-06 — v1.0 (`c32a2a5`):** rate limiting (`Flask-Limiter`), security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`), login event logging (`app.logger.warning`).
- **2026-04-07 — Assistente IA (`5e12780`):** chat com OpenRouter + tool use.
- **2026-04-07 — Sistema de convites (`6bbc5e8`):** registo restrito por token de convite (7 dias).
- **2026-04-15 — Loja de Módulos (`ab7777c`).**
- **2026-04-16 — v1.2 (Calendário):** 7f6e871, 2026-04-16.

---

## Incidentes e lições aprendidas

1. **2026-09-23 — BD local apagada por uma corrida de `pytest` (regredido na v1.5.0).**
   - **Causa:** `tests/test_cofre.py` criava a app com a config de produção e chamava `db.drop_all()`; reescrever `SQLALCHEMY_DATABASE_URI` **depois** de `create_app()` não tem efeito, porque o engine é fixado em `db.init_app()` — o `drop_all()` correu contra `instance/pipe.db` e apagou as 21 tabelas.
   - **Correcção:** `create_app('testing')` (SQLite em memória + sessões em pasta temporária), `tests/conftest.py` bloqueia `db.drop_all()` com BD de ficheiro, regressão em `tests/test_isolamento_bd.py`, `scripts/criar_admin.py` passa a criar o administrador com `is_admin=True`, novo `scripts/backup_bd.py`.
   - **Lições:** nunca testar contra uma BD de ficheiro real; garantir que `SQLALCHEMY_DATABASE_URI` está configurado **antes** da inicialização da app; verificar `sha256` da BD antes/depois de corridas completas.

2. **v1.4.4 — OpenRouter devolve HTTP 200 com corpo de erro.**
   - **Causa:** quando o provider upstream falha, o OpenRouter devolve `HTTP 200` + `{"error": ...}`; o código só chamava `raise_for_status()` (200 passa como sucesso) e essa chamada estava fora do `try`, abortando a cadeia de fallback com a mensagem genérica "Não consegui gerar uma resposta".
   - **Correcção:** validação conjunta do HTTP e do corpo (`_classificar_resposta` — `rate_limit` / `modelo_indisponivel` / `servico` / `ok`), fallback imediato a qualquer falha de provider, exceções de rede com backoff, parsing defensivo no `contexto.py`.
   - **Lições:** um 200 não é sucesso quando o body contém erro; tratar sempre o corpo da resposta; nunca colocar a chamada de rede fora do `try` que envolve os fallbacks.

3. **v1.4.14 — cache do nginx do PythonAnywhere ignora query params.**
   - **Causa:** o nginx do PA cacheia ficheiros estáticos e ignora query strings; o `pipe.css` actualizado ficou inacessível porque o `base.html` ainda usava `?v=3`.
   - **Correcção:** incrementar o cache-buster para `?v=4` no link CSS **e** no script JS.
   - **Lições:** quando se altera CSS/JS estáticos, bumpar o cache-buster em **todos** os locais (`base.html`); testar em produção após o deploy; o service worker também precisa de bump (pipe-v2 → pipe-v3 na v1.4.3).

4. **`db.create_all()` não faz `ALTER TABLE`.**
   - **Facto:** o `create_all()` do SQLAlchemy cria tabelas inexistentes, mas não acrescenta colunas a tabelas existentes.
   - **Impacto:** as colunas `mailjet_message_id`, `email_estado`, `email_verificado_em` (v1.5.2) e `ativo`, `ciclos_ausente` (v1.3.2/v1.4.8) não apareceriam numa BD já criada — as queries ao modelo rebentariam com `no such column`.
   - **Solução:** scripts de migração explícitos e idempotentes (`scripts/migrar_convites_mailjet.py`, `scripts/reset_postos_combustiveis.py`, `scripts/remover_postos_ignorados.py`) executados manualmente no PA após o deploy.
   - **Lições:** para BDs em produção, nunca confiar no `create_all()` para evoluir o esquema; preferir scripts de migração explícitos (e, no futuro, avaliar Flask-Migrate).

---

## Verificação — versões incluídas

Todas as entradas "Versão vX" da `Estado_Atual.md` têm entrada correspondente no CHANGELOG. Mapeamento:

| Versão do documento | Entrada no CHANGELOG | Notas |
|---|---|---|
| v1.5.9.1 | v1.5.9.1 — 2026-10-01 | ✅ balões alta contraste (`--cor-balao-assistente*`, `?v=7`) |
| v1.5.10 | v1.5.10 — 2026-10-02 | ✅ dedup postos (`obter_ids_duplicados`) |
| v1.5.9 | v1.5.9 — 2026-10-01 | ✅ detalhe read-only Calendário |
| v1.5.8 | v1.5.8 — 2026-10-01 | ✅ tarefas dia prazo + calendário lembretes |
| v1.5.7 | v1.5.7 — 2026-10-01 | ✅ listas predefinidas |
| v1.5.6 | v1.5.6 — 2026-10-01 | ✅ mensal defeito, modo claro GC, concluídas ocultas |
| v1.5.5 | v1.5.5 — 2026-09-30 | ✅ filtro posto + resultados degradáveis |
| v1.5.4 | v1.5.4 — 2026-09-30 | ✅ ZIP/guia da extensão |
| v1.5.3 | v1.5.3 — 2026-09-29 | ✅ fila de modelos |
| v1.5.2 | v1.5.2 — 2026-09-25 | ✅ Mailjet + colunas (ALTER BD) |
| v1.5.1 | v1.5.1 — 2026-09-24 | ✅ captura/409/alerts |
| v1.5.0 | v1.5.0 — 2026-09-24 | ✅ cofre + extensão (ALTER BD) |
| v1.4.15 | v1.4.15 — 2026-09-23 | ✅ limites de caracteres (**duplicação removida**: a entrada duplicada da `Estado_Atual.md` aparece uma única vez) |
| v1.4.14 | v1.4.14 (fix) — 2026-09-21 | ✅ cache-buster `?v=4` |
| v1.4.13 | v1.4.13 — 2026-09-21 | ✅ tabelas Markdown |
| v1.4.12 | v1.4.12 — 2026-09-21 | ✅ `get_combustiveis` |
| v1.4.11 | v1.4.11 — 2026-09-21 | ✅ Markdown (`markdownToHtml`) |
| v1.4.10 | v1.4.10 — 2026-09-18 | ✅ obsolescência 30 dias (Combustíveis) |
| v1.4.9 | v1.4.9 — 2026-09-18 | ✅ blocklist (Combustíveis 1.3.3) |
| v1.4.8 | v1.4.8 — 2026-09-18 | ✅ arquivamento automático (Combustíveis 1.3.2) |
| v1.4.7 | v1.4.7 — 2026-09-18 | ✅ `get_cambio` |
| v1.4.6 | v1.4.6 — 2026-09-18 | ✅ fix lentidão |
| v1.4.5 | v1.4.5 — 2026-09-17 | ✅ `get_eventos` |
| v1.4.4 | v1.4.4 — 2026-09-17 | ✅ bug crítico fallback |
| v1.4.3 | v1.4.3 — 2026-09-16 | ✅ fix cache |
| v1.4.2 | v1.4.2 — 2026-09-16 | ✅ Calendário + Combustíveis 1.3.x + paleta Keep + contraste |
| v1.4.1 | v1.4.1 — 2026-09-16 | ✅ paleta Keep |
| v1.4.0 | v1.4.0 — 2026-09-16 | ✅ tema claro/escuro |

**Total: 28 versões incluídas (v1.4.0 a v1.5.10), todas com entrada.**

**Resoluções de inconsistências aplicadas:**
- **(a)** A v1.4.10 pertence à **obsolescência de postos** (commit `c0f20b8`, 2026-09-18); a **renderização Markdown** (plain) pertence à v1.4.11 (`f6575d2`); as **tabelas Markdown** pertencem à v1.4.13 (`ab83a6a`) — confirmado pelo histórico Git, igual ao documento.
- **(b)** A v1.4.15 está duplicada na `Estado_Atual.md`; aparece **uma única vez** (commit `34ff462`).
- **(c)** As fases dos Combustíveis mapeadas para o número do projeto: **v1.3** (implementação + API Aberta) → v1.4.2; **v1.3.1** (bug paginação, blocklist, dedup, rate limit) → v1.4.2; **v1.3.2** (arquivamento automático, colunas `ativo`/`ciclos_ausente`) → v1.4.8; **v1.3.3** (blocklist `NOMES_IGNORADOS`) → v1.4.9. Identificadas como "Combustíveis fase 1.3.x" dentro de cada entrada.
- **(d)** Versões ordenadas **da mais recente para a mais antiga** por data de commit.
- **(e)** Última versão real confirmada pelo Git: **v1.5.10** (HEAD `9990f4b`, 2026-10-02); o commit `f1e7c61` (2026-10-01) é a **v1.5.9.1**, numerada entre a v1.5.9 e a v1.5.10 por ordem de implementação.

**Versões do documento SEM entrada directa:** v1.2 (Calendário) e v1.3 (Combustíveis) — não são secções "Versão vX" autónomas na `Estado_Atual.md`, foram integradas como "fase 1.3.x" dentro da v1.4.2 e referidas no Histórico anterior. Nenhuma informação foi omitida.
