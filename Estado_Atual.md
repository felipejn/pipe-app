# PIPE — Estado Actual do Projecto — v1.8.33

## Versão v1.8.33 — 2026-10-22

- Corrigida a centragem da janela de leitura das notas no PythonAnywhere: o CSS (`pipe.css`) era servido em cache com a versão antiga e o Service Worker mantinha o ficheiro anterior, deixando a janela sem as regras de centragem.
- Alterado o cache-buster do CSS de `?v=7` para `?v=8` em `base.html` e a versão do Service Worker de `pipe-v3` para `pipe-v4` (`sw.js`), forçando a busca da nova versão nos clientes.
- Validação: `tests/test_notas_visualizacao.py` — 6 testes aprovados; `git diff --check` sem erros.
- Sem alterações de base de dados ou dependências. Em PythonAnywhere, actualizar com `git pull` e executar Reload.

## Versão v1.8.32 — 2026-10-22

- Na grelha de notas, clicar num cartão abre uma janela de leitura com o conteúdo completo, etiquetas e todos os itens da checklist; a edição fica numa acção explícita.
- Checklists podem ser marcadas na janela por donos e utilizadores com permissão de edição. O acesso de leitura partilhado mantém-se sem escrita; os dados da nota são servidos sem cache.
- Validação: `tests/test_notas_visualizacao.py` + `tests/test_partilha.py` — 26 testes aprovados; suite restante, excluindo `tests/test_assistente_combustiveis.py` e `tests/test_criar_admin.py` — 419 testes aprovados, 1 ignorado e 33 subtestes aprovados; sintaxe JavaScript, compilação Python e `git diff --check` sem erros. O primeiro teste da suite completa falha por não haver preços activos na fixture de Combustíveis; não houve validação visual interactiva por falta de navegador.
- Sem alterações de base de dados ou dependências. Em PythonAnywhere, actualizar com `git pull` e executar Reload.

## Versão v1.8.31 — 2026-10-21

- A eliminação de um utilizador na administração remove primeiro as partilhas criadas e recebidas, evitando violação da restrição `NOT NULL` em `partilha_recurso.dono_id`; recursos de outros utilizadores são preservados.
- Validação: `tests/test_partilha.py` — 20 testes aprovados; `git diff --check` sem erros. `tests/test_convites_email.py` e a suite completa ficaram por validar devido a erros de acesso às pastas temporárias no ambiente.
- Sem alterações de base de dados ou dependências. Em PythonAnywhere, actualizar com `git pull` e executar Reload.

## Versão v1.8.30 — 2026-10-21

- O Assistente IA usa `minimax/minimax-m3.1-flash:free` por omissão; Cohere e os restantes modelos actuais mantêm-se como fallbacks.
- Validação: `pytest tests/test_assistente_cliente.py -q` — 25 testes aprovados; `git diff --check` sem erros.
- Sem alterações de base de dados ou dependências. No PythonAnywhere, actualizar `OPENROUTER_MODEL` para o MiniMax, fazer `git pull` e executar Reload.

## Versão v1.8.29 — 2026-10-21

- Emails de partilha usam o design padrão do PIPE, com assunto conciso, permissão traduzida e ligação para gerir convites.
- A página de gestão apresenta «Leitura» e «Edição» em vez dos identificadores internos; os testes de partilha bloqueiam envios reais pelo Zoho.
- Validação: `pytest tests/test_partilha.py tests/test_convites_email.py -q` — 35 testes aprovados; `git diff --check` sem erros. A suite completa não foi executada.
- Sem alterações de base de dados ou dependências. Em PythonAnywhere, actualizar com `git pull` e executar Reload.

## Versão v1.8.28 — 2026-10-21

- Melhorada a página de gestão de partilhas: texto introdutório mais claro, estados visuais explícitos e acções responsivas em ecrãs estreitos.
- O carregamento das listas é independente; uma falha numa secção apresenta erro e opção de nova tentativa sem bloquear as restantes.
- Validação: `pytest tests/test_partilha.py -q` (17 testes); suite abrangente (409 testes, 1 ignorado e 33 subtestes), excluindo os testes conhecidos dependentes de janela de dados externos e API; `git diff --check` sem erros.
- Verificação visual em Chrome, em vistas desktop e móvel; a navegação global continua cortada no ecrã estreito e não foi alterada nesta revisão.
- Sem alterações de base de dados ou dependências. Em PythonAnywhere, actualizar com `git pull` e executar Reload.

## Versão v1.8.27 — 2026-10-20

- Reforçada a resiliência da recolha de combustíveis: pedidos repetidos em falhas de ligação/timeout e respostas HTTP 429/5xx; páginas com JSON inválido também são repetidas.
- Falhas de estrutura ou processamento ficam isoladas por combustível, sem manter escritas parciais; falhas no commit fazem rollback e são registadas no estado quando a base de dados continua disponível.
- Sem alteração de BD ou dependências.
- Validação: testes de resiliência, seed e deduplicação — **22 passaram**; compilação Python e `git diff --check` limpos. A suite completa não terminou dentro do tempo disponível; `tests/test_assistente_combustiveis.py` mantém falhas conhecidas devido a fixtures fora da janela de preços activos.

## Versão v1.8.26 — 2026-10-19

- `README.md` do GitHub reescrito em inglês, orientado a recrutadores: hero com badges (versão, Python, Flask, 434 testes, deploy), índice de âncoras, overview/highlights, tabela com os 12 módulos (antes só 8), spotlights do Cofre, Assistente IA, Meteorologia e Partilha, tabela de segurança, stack actualizada (Flask 3.1.3, Flask-Migrate, Flask-Session), diagrama de arquitectura, testes, quickstart completo com variáveis de ambiente, deploy em 3 passos, links à documentação e nota de licença (sem `LICENSE` no repositório).
- Substituídos o «versão 1.0» desactualizado, o placeholder de screenshot e as referências obsoletas; corrigido «SMTP» para envio por API (Zoho Mail OAuth 2.0).
- Sem alteração de código nem de BD.
- Validação: `pytest --collect-only -q` — **434 testes recolhidos**; suite em sandbox com `--basetemp` local — **396 passaram, 33 subtests** (excluídos `tests/test_assistente_combustiveis.py`, falhas conhecidas por fixtures de preços, e `tests/test_criar_admin.py`, dependente da API Aberta); subconjuntos focados (partilha, notificações Telegram, resumo diário, segurança, convites) — **64 passaram**; `git diff --check` limpo; links internos do README verificados.

## Versão v1.8.25 — 2026-10-19

- O Resumo Diário usa o primeiro nome do utilizador na saudação; o modelo recebe instruções explícitas de português europeu, tom caloroso e conversacional, e hora local de Lisboa para escolher uma saudação coerente.
- As mensagens do Resumo Diário no Telegram são enviadas sem cabeçalho/assunto, tanto manualmente como na tarefa automática.
- Sem alteração de BD.
- Validação: `tests/test_resumo_diario.py`, `tests/test_resumo_diario_fase2.py` e `tests/test_resumo_diario_fase4.py` — 65 testes passaram; em conjunto com `tests/test_notifications_telegram.py` — 91 testes passaram; `git diff --check` limpo.

## Versão v1.8.24 — 2026-10-19

- Adicionado `AGENTS.md` à raiz do repositório com instruções persistentes para o Codex: comunicação e documentação em PT-PT, aprovação prévia do plano, validação e aprovação após implementação, documentação/commit/push após aprovação, salvaguarda de alterações locais e segredos, e indicação dos passos de deploy.
- Sem alteração funcional da aplicação ou da base de dados.
- Validação: `git diff --check`; testes de aplicação não aplicáveis a uma alteração apenas documental.

## Versão v1.8.23 — 2026-10-19

- **Partilha de recursos:** implementação completa da funcionalidade de partilha de tarefas (`tarefa`), notas (`nota`) e compromissos (`evento`) entre utilizadores, preservando anonimato (partilha feita via email/login, sem lista de utilizadores).
- Novo módulo `app/partilha/` com modelo `PartilhaRecurso` (tabela `partilha_recurso`), helpers de autorização (`obter_recurso_ou_404`, `pode_aceder_recurso`), blueprint com endpoints `/partilha/<tipo>/<id>`, `/partilha/<id>/aceitar`, `/partilha/minhas`, `/partilha/criadas`, `/partilha/<id>` (DELETE).
- Rotas existentes de tarefas (`tarefas/routes.py`), notas (`notas/routes.py`) e calendário (`calendario/routes.py`) atualizadas para aceitar acesso por dono ou partilha aceita (nível mínimo `edicao` para escrita).
- Migração Alembic `c43fd13b2c0b` (`adiciona_tabela_partilha_recurso`).
- Testes `tests/test_partilha.py`: **11 testes passaram** (criar, aceitar, acesso, negação, nível edição, listar partilhados, remover, auto-partilha, email inexistente, email vazio).
- **Com alteração de BD.**
- **Validação:** `tests/test_partilha.py` — 11/11; `tests/test_partilha.py` + `tests/test_tarefas.py` + `tests/test_notas.py` — sem regressões; `git diff --check` limpo.

## Versão v1.8.22 — 2026-10-18

- Removidos os scripts históricos `scripts/verificar_mailjet.py` e `scripts/migrar_convites_mailjet.py`, deixando de existir ferramentas obsoletas que chamavam a API Mailjet ou recriavam colunas antigas.
- O `README.md` apresenta agora o Zoho Mail como canal de email e documenta as variáveis `ZOHO_*` em vez das antigas `MAILJET_*`.
- Mantêm-se os briefings em `docs/historico/`, os registos do CHANGELOG, os avisos históricos de `Estado_Atual.md` e as migrations como referência da migração Mailjet → Zoho.
- **Sem alteração de BD.**
- **Validação:** `tests/test_convites_email.py` — **17 testes passaram**; `git diff --check` limpo; sem referências a `Mailjet` no `README.md`.

## Versão v1.8.21 — 2026-10-18

- **Resiliência da Meteorologia:** quando a API Open-Meteo está em baixo, o módulo, o Assistente e o Resumo Diário servem a última previsão com sucesso guardada (até 24 h), marcada como `de_cache`; a UI mostra aviso e intitula a secção «Horas guardadas» para não rotular horas passadas como futuras. Sem cache válida, mantém-se o comportamento de indisponível.
- Nova tabela `meteorologia_previsao_cache` (uma linha por coordenadas ~1 km, payload JSON, `obtida_em` indexado). Migração `a91e7c30d4b2` (down: `fd5793bc73bf`).
- **Com alteração de BD.**
- **Validação:** testes focados da Meteorologia: 42 passaram; Assistente + Resumo Diário: 22 passaram; `git diff --check` limpo. Suite completa ver no CHANGELOG.

## Versão v1.8.20 — 2026-10-18

- Validações de produção concluídas para segurança, autenticação, 2FA, notificações, Meteorologia, Resumo Diário, Calendário e restantes itens de deploy documentados.
- Mantém-se pendente apenas o teste ponta a ponta da extensão Chrome do Cofre, incluindo CORS, preenchimento de credenciais, ausência da chave nos cookies e expiração da captura pendente.
- **Sem alteração de BD.**
- **Validação:** confirmação manual do utilizador em produção.

## Versão v1.8.19 — 2026-10-18

- O Assistente apresenta apenas tarefas em aberto por omissão, incluindo nas agendas semanais; pedidos explícitos por tarefas concluídas ou por todas as tarefas continuam disponíveis.
- **Sem alteração de BD.**
- **Validação:** 37 testes focados passaram, 6 subtestes passaram; `git diff --check` limpo.


## Versão v1.8.18 — 2026-10-18

- O Assistente apresenta compromissos e tarefas da semana com datas, dias da semana, estados e totais calculados directamente dos dados; respostas de agenda reconhecidas são determinísticas e não dependem do modelo para calcular contagens ou dias.
- As ferramentas de leitura de tarefas e eventos aceitam filtros semanais e intervalos explícitos; resultados truncados preservam metadados de total e incompletude.
- Datas ISO com fuso são normalizadas para Europe/Lisbon ao criar/editar eventos pelo Assistente e pela API do Calendário.
- Mensagens do Assistente acima de 3.000 caracteres são rejeitadas. O cliente regista bytes da entrada e tokens reportados pelo OpenRouter após respostas bem-sucedidas e apresenta erro específico quando os modelos rejeitam o contexto. A contagem exacta prévia varia por modelo e não é conhecida localmente.
- **Sem alteração de BD.**
- **Validação:** testes focados do Assistente: 61 passaram, 6 subtestes passaram; selecção do Assistente: 95 passaram, 33 subtestes passaram. Suite completa: 387 passaram, 1 ignorado, 25 falharam em `tests/test_assistente_combustiveis.py` devido a fixtures de preços fora da janela activa de 30 dias. `git diff --check` limpo.


## Versão v1.8.17 — 2026-10-18

- Removido do email de teste de notificações o botão «Ver resultados» do Euromilhões, que já não se relaciona com a configuração geral de email.
- **Sem alteração de BD.**
- **Validação:** teste do utilizador aprovado; teste de regressão acrescentado para garantir que o email não inclui o link ou botão do Euromilhões.

## O que é o PIPE

Plataforma Inteligente Pessoal e Expansível — aplicação web Flask modular.
O nome é simultaneamente um acrónimo e o apelido do utilizador (Felipe = Pipe).
O módulo Euromilhões é o primeiro módulo, o módulo Tarefas é o segundo, o módulo Notas é o terceiro, o módulo Passwords é o quarto. O módulo Loja de Módulos é o sistema de personalização. O módulo Calendário é o oitavo módulo. O módulo Combustíveis é o nono módulo. O módulo Meteorologia é o décimo primeiro e o Resumo Diário é o décimo segundo. A arquitectura suporta adição de novos módulos com a mesma identidade visual.

---

## Estrutura do projecto

```
pipe-app/
├── app/
│   ├── __init__.py          # create_app, app factory + security headers
│   ├── extensions.py        # Limiter (Flask-Limiter, X-Forwarded-For para PA)
│   ├── static/
│   │   ├── css/pipe.css     # design system (tema escuro + tema claro via tokens semânticos) + cores de eventos do Calendário + navegação secundária
│   │   ├── icons/           # icon-192.png, icon-512.png (PWA)
│   │   ├── manifest.json    # PWA — manifest
│   │   ├── sw.js            # PWA — service worker (network-first para CSS/JS/HTML, cache pipe-v3)
│   │   └── js/
│   │       └── pipe.js      # JS base (alertas + alternância de tema claro/escuro)
│   ├── templates/
│   │   ├── base.html        # navbar + alternador de tema 🌙/☀️ + anti-FOUC + barra secundária «Voltar/Home» (oculta no dashboard) + meta `csrf-token` (cofre/extensão)
│   │   ├── dashboard.html   # dashboard — grelha híbrida de cards com resumos por provider (Tarefas + Calendário); fallback clássico automático se não houver provider
│   │   ├── emails/          # layout responsivo e templates HTML + texto simples dos emails PIPE
│   │   ├── assistente/
│   │   │   └── index.html   # interface de chat do Assistente IA
│   │   ├── auth/            # login, registo (por convite), 2FA, reset password
│   │   ├── euromilhoes/     # registo de jogos e comparação com sorteios
│   │   ├── meteorologia/    # Previsão do tempo (Etapa A: localização; Etapa B: previsão Open-Meteo)
│   │   │   ├── index.html   # vista de previsão: local, temperatura, sensação, 24h + 7 dias
│   │   │   └── localizacao.html  # pesquisa e confirmação da localização geográfica
│   │   ├── resumo_diario/   # resumo determinístico, configuração e envio manual por Telegram
│   │   │   └── definicoes.html  # opções, pré-visualização e envio
│   │   ├── tarefas/
│   │   │   ├── index.html   # vistas lista/detalhe + sidebar de tags
│   │   │   └── partials/    # items, form, sidebar
│   │   ├── notas/           # grelha de cartões, etiquetas, checklist
│   │   ├── passwords/       # gerador + cofre (desbloqueio) + exportação
│   │   ├── conversoes/      # conversor de ficheiros (HEIC→JPG, PNG/JPG→ICO)
│   │   ├── cambio/          # conversor de moedas (Wise v3 + fallback)
│   │   ├── cores/           # conversor HEX↔RGB↔HSL para Flutter
│   │   ├── modulos/
│   │   │   └── loja.html    # Loja de Módulos — ativar/desativar módulos
│   │   └── calendario/      # vista mensal + vista de agenda
│   ├── auth/                # Blueprint Auth
│   │   ├── __init__.py
│   │   ├── forms.py         # LoginForm, RegistoForm, 2FA, reset
│   │   ├── models.py        # User + Convite
│   │   └── routes.py        # /auth/*
│   ├── euromilhoes/         # Blueprint Euromilhões
│   │   ├── __init__.py
│   │   ├── models.py        # Jogo
│   │   └── routes.py        # /euromilhoes/
│   ├── tarefas/             # Blueprint Tarefas
│   │   ├── __init__.py
│   │   ├── models.py        # Lista, Tarefa, TagTarefa
│   │   ├── forms.py         # ListaForm, TarefaForm
│   │   ├── seed.py          # semear_listas_predefinidas (v1.5.7)
│   │   └── routes.py        # /tarefas/
│   ├── notas/               # Blueprint Notas
│   │   ├── __init__.py
│   │   ├── models.py        # Nota, ItemChecklist, EtiquetaNota
│   │   └── routes.py        # /notas/
│   ├── passwords/           # Blueprint Passwords (gerador + cofre)
│   │   ├── __init__.py
│   │   ├── crypto.py        # AES-256-GCM + PBKDF2-SHA256 (600 000 it.) + bcrypt da password mestra
│   │   ├── models.py        # CofreConfig, CofrePassword + extrair_dominio() (dedup por domínio)
│   │   ├── wordlist.py      # lista PT ~200 palavras para passphrases
│   │   ├── generator.py     # geração com secrets + cálculo de força por entropia
│   │   └── routes.py        # /passwords/ + /passwords/api/cofre/* + /passwords/api/csrf-token
│   ├── cambio/              # Blueprint Câmbio
│   │   ├── __init__.py
│   │   ├── service.py       # MOEDAS + obter_taxa (Wise v3 + fallback, partilhado com Assistente IA)
│   │   └── routes.py        # /cambio/ — stateless, delega no service.py
│   ├── cores/               # Blueprint Cores Flutter
│   │   ├── __init__.py
│   │   └── routes.py        # /cores/ — stateless, HEX/RGB/HSL/CMYK para Flutter
│   ├── conversoes/          # Blueprint Conversões
│   │   ├── __init__.py
│   │   ├── models.py        # modelo Conversao (histórico, sem ficheiros)
│   │   └── routes.py        # /conversoes/ — HEIC→JPG + PNG/JPG→ICO
│   ├── assistente/          # Blueprint Assistente IA
│   │   ├── __init__.py
│   │   ├── cliente.py       # OpenRouter API, retry + fallback entre modelos
│   │   ├── contexto.py      # orquestração do fluxo, histórico em sessão, tool use
│   │   ├── ferramentas.py   # 8 ferramentas de leitura + 10 de escrita
│   │   └── routes.py        # /assistente/ + /assistente/api/*
│   ├── modulos/             # Blueprint Loja de Módulos
│   │   ├── __init__.py
│   │   ├── models.py        # UserModulo
│   │   ├── routes.py        # /modulos/loja
│   │   └── config.py        # MODULOS_DISPONIVEIS (12 módulos: Resumo Diário adicionado na v1.8.0)
│   ├── resumo_diario/       # Blueprint Resumo Diário, serviços e configuração por utilizador
│   │   ├── models.py        # ConfiguracaoResumoDiario (`resumo_diario_configuracoes`)
│   │   ├── routes.py        # definições, pré-visualização e envio manual
│   │   └── services.py      # recolha e composição determinística do resumo
│   ├── dashboard/           # Camada de resumos por provider (v1.7.0)
│   │   ├── base.py          # Contrato: `Estado`, `Metrica`, `DashboardProvider` (ABC)
│   │   ├── registry.py      # Registry explícito de providers + `carregar_providers()` em `create_app()`
│   │   ├── calendario.py    # (registo) -> provider em `app/calendario/dashboard.py`
│   │   └── tarefas.py       # (registo) -> provider em `app/tarefas/dashboard.py`
│   ├── calendario/          # Blueprint Calendário
│   │   ├── __init__.py
│   │   ├── models.py        # Evento
│   │   └── routes.py        # /calendario/ + /calendario/api/eventos
│   ├── combustiveis/        # Blueprint Combustíveis
│   │   ├── __init__.py
│   │   ├── models.py        # 5 tabelas (postos, preços, utilizador_concelho, utilizador_combustivel, estado_atualizacao)
│   │   ├── routes.py        # /combustiveis/ (dashboard, concelhos, tipos de combustível, actualização)
│   │   ├── services.py      # API Aberta (api.apiaberta.pt), obsolescência de postos, dedup
│   │   └── seed.py          # semear_concelhos_predefinidos (Braga, Vila Verde, Amares) — seed no criar_admin.py
│   ├── notifications/       # Sistema de notificações
│   │   ├── __init__.py
│   │   ├── models.py        # UserNotificationPreferences
│   │   ├── service.py       # orquestração de canais (Telegram + Email) + `ultimo_erro()`
│   │   └── channels/        # TelegramChannel (motivo + retry transitório), EmailChannel
│   └── admin/               # Blueprint de administração
│       ├── __init__.py
│       ├── decorators.py    # @admin_required
│       └── routes.py        # /admin/ — gestão de convites
├── chrome-extension/        # extensão Chrome MV3 do Cofre (com ícones)
│   ├── manifest.json        # MV3 — activeTab, storage, tabs; host_permissions <all_urls>
│   ├── background.js        # service worker — API do PIPE + captura (origem configurável)
│   ├── popup.html / popup.js # popup — estado, desbloquear, listar/copiar/actualizar
│   ├── content.js           # content script — captura apenas em forms de login (ignora o PIPE)
│   ├── icon48.png / icon128.png # ícones gerados por scripts/gerar_icones_extensao.py
│   └── README.md            # instalação, permissões e fluxo de uso
├── docs/
│   ├── guia-extensao-chrome.md    # guia passo a passo da extensão (instalar e usar)
│   └── historico/           # briefings e relatórios antigos
│       └── plano-cofre-passwords.md  # plano de correcção do Cofre
├── scripts/
│   ├── __init__.py                # package marker (permite import em testes)
│   ├── criar_admin.py            # cria admin + seed de listas/concelhos/recolha de postos
│   ├── promover_admin.py
│   ├── pipe_tasks.py            # única scheduled task do PythonAnywhere
│   ├── popular_combustiveis.py  # recolha manual de combustíveis (helper)
│   ├── remover_postos_ignorados.py  # limpeza dos postos em services.NOMES_IGNORADOS
│   ├── reset_postos_combustiveis.py  # reset das tabelas de postos/histórico (combustíveis)
│   ├── testar_assistente.py     # smoke test do Assistente IA contra a OpenRouter
│   ├── backup_bd.py             # cópia de segurança de instance/pipe.db (mantém as últimas 10)
│   ├── gerar_icones_extensao.py # gera icon48/icon128 da extensão Chrome (Pillow, sem Flask)
│   ├── verificar_telegram.py    # diagnóstico do canal Telegram: getMe + getChat + `--enviar-teste`
│   └── smoke_combustiveis.py    # smoke test da ferramenta get_combustiveis (Assistente IA)
├── tests/
│   ├── conftest.py              # guarda-civil: bloqueia `db.drop_all()` com BD de ficheiro (obrigatório create_app('testing'))
│   ├── conftest_utils.py        # helpers de fixture de app
│   ├── test_cofre.py            # 32 testes
│   ├── test_convites_email.py   # 14 testes
│   ├── test_pipe_tasks.py       # 16 testes (tarefas, calendário e integração do resumo)
│   ├── test_tarefas_listas_predefinidas.py  # 3 testes
│   ├── test_extensao_js.py      # 1 teste
│   ├── test_extensao_distribuicao.py  # 8 testes
│   ├── test_isolamento_bd.py    # 1 teste
│   ├── test_assistente_cliente.py     # 13 testes
│   ├── test_assistente_combustiveis.py# 31 testes
│   ├── test_assistente_contexto.py    # 9 testes
│   ├── test_assistente_contexto_truncagem.py # 10 testes
│   ├── test_assistente_meteorologia.py  # 14 testes (ferramenta get_meteorologia)
│   ├── test_assistente_registo.py       # 8 testes (invariante registo↔definições + regressão criar_tarefa)
│   ├── test_combustiveis_dedup.py     # 11 testes
│   ├── test_combustiveis_seed.py      # 3 testes (seed de concelhos predefinidos)
│   ├── test_criar_admin.py            # 7 testes (criar admin + seed + recolha inicial)
│   ├── test_modulos_security.py       # 1 teste (isolamento da activação de módulos)
│   ├── test_resumo_diario.py          # 8 testes (serviço, isolamento, datas e limite de texto)
│   ├── test_resumo_diario_fase2.py     # 16 testes (configuração, rotas, Telegram e rate limits)
│   ├── test_resumo_diario_fase3.py     # 8 testes (elegibilidade, envio automático, simulação e datas)
│   └── smoke/                 # smoke tests (ex.: test smoke api de conversoes)
├── migrations/             # Flask-Migrate — baseline + revisões incrementais
│   └── versions/           # baseline 3b14f5bd26a5; c420a200f2f2 (Meteorologia); 3058f716df40 + 8f3b90a1c2d4 (Resumo Diário)
├── .env.example
├── requirements.txt
└── README.md

```

---

## Módulos

### Módulo Auth (`app/auth/`)

- Registo por convite apenas — `Convite` com token único, validade de 7 dias e contador de usos (`convites_usados`)
- Login por email com `@login_required` (Flask-Login); `username` mantém-se como identificador interno de compatibilidade
- Perfil guarda nome próprio e apelido (`utilizadores.nome`, `utilizadores.apelido`); campos opcionais para contas antigas e pedidos no registo por convite
- Saudações do dashboard, Assistente e comunicações usam o nome próprio, com fallback para contas antigas
- 2FA: **Telegram, Email e TOTP** — métodos configuráveis e simultâneos (`UserNotificationPreferences`, `pyotp` + `qrcode`)
- Reset de password por email
- Rotas: `/auth/login`, `/auth/register`, `/auth/2fa/*`, `/auth/reset/*`
- Rotas críticas protegidas por rate limiting (`Flask-Limiter`); falhas de login registadas com `app.logger.warning` (email + IP)

### Módulo Euromilhões (`app/euromilhoes/`)

- Modelo `Jogo` — `jogos_euromilhoes` (numeros, estrelas, data_sorteio, filtrado por `user_id`)
- Interface de registo de combinações e visualização do histórico; cálculo do próximo sorteio

### Módulo Tarefas (`app/tarefas/`)

- Modelos: `Lista`, `Tarefa`, `TagTarefa`
- Formulários Flask-WTF (`ListaForm`, `TarefaForm`); semente de listas predefinidas (`tarefas.seed`)
- Vistas de lista e de detalhe com busca e filtros por etiquetas; apoio ao teclado (atalhos de navegação)
- Notificações: no dia do prazo e em todos os dias de atraso até conclusão

### Módulo Loja de Módulos (`app/modulos/`)

- Modelo `UserModulo` (`user_modulos`) — ativação/desativação de módulos por utilizador
- `MODULOS_DISPONIVEIS` em `app/modulos/config.py` com 12 módulos (inclui Meteorologia e Resumo Diário)
- Rotas: `/modulos/loja` (loja), `/modulos/api/toggle` (AJAX `POST` com `request.get_json()`); a identidade vem de `current_user.id`, nunca do `user_id` do browser (correcção de segurança v1.7.6, sem alteração de BD)

### Módulo Notas (`app/notas/`)

- Modelos: `Nota`, `ItemChecklist`, `EtiquetaNota`
- Cartões com 8 cores (paleta do Google Keep), fixar/arquivar, busca em tempo real, checklist inline e etiquetas

### Módulo Passwords (`app/passwords/`)

- **Gerador (stateless):** modos Password (8–64 chars), Passphrase (3–10 palavras PT), PIN (4–12 dígitos); barra de força por entropia; cópia para a área de transferência
- **Cofre (com BD — `cofre_configs`, `cofre_passwords`):** AES-256-GCM com chave derivada por PBKDF2-SHA256 (`COFRE_KDF_ITERATIONS`, 600 000) da password mestra (verificação por bcrypt); a chave existe apenas em sessão server-side (Flask-Session filesystem em `instance/flask_session/`) e nunca no cookie; expira ao fim de `COFRE_SESSION_TIMEOUT` (900 s), bloqueando apenas o cofre — a sessão de login mantém-se; entradas deduplicadas por domínio normalizado (`extrair_dominio()`, única fonte de verdade) + username; importação de CSV do Chrome; todas as queries filtradas por `user_id` (anti-IDOR)
- **API:** `/passwords/api/cofre/*` (estado, activar, desbloquear, bloquear, alterar-password, CRUD de entradas, importar-csv) e `GET /passwords/api/csrf-token`, que devolve o token CSRF assinado (usado pelo JS do cofre e pela extensão Chrome — nunca `session['csrf_token']`, que é o valor cru); CORS restrito por `COFRE_CORS_ORIGINS`
- **Extensão Chrome (MV3):** `chrome-extension/` — popup (estado, desbloquear, listar/preencher) e content script com heurística de captura (só forms de login); origem do servidor configurável em `chrome.storage.local.pipeOrigin` (default: PythonAnywhere)

### Módulo Câmbio (`app/cambio/`)

- `service.py`: constante `MOEDAS` e função `obter_taxa(origem, destino, valor)` — API Wise v3 + fallback ExchangeRate-API, stateless
- Rotas: `/cambio/` (interface de conversão), `/cambio/api/convert` (AJAX `POST` `request.get_json()`)

### Módulo Cores (`app/cores/`)

- Swatches Material Design; conversão HEX↔RGB↔HSL↔CMYK com output para código Flutter
- Rotas: `/cores/` + `/cores/api/convert`

### Módulo Conversões (`app/conversoes/`)

- HEIC→JPG (`pillow_heif`) e PNG/JPG→ICO (`PIL`)
- Limites: `MAX_FICHEIROS = 20`, `MAX_TAMANHO_MB = 10`, `MAX_TAMANHO_BYTES = 10 485 760`; ficheiros processados em memória (sem persistência), histórico em `conversoes`
- Rotas: `/conversoes/` + `/conversoes/api/convert`

### Módulo Calendário (`app/calendario/`)

- Modelo `Evento` (`evento`) — `user_id`, `titulo`, `data_inicio`, `data_fim`, `descricao`, `localizacao`, `dia_inteiro`, `cor`, `notificar`
- Rotas: `/calendario/` (vista mensal + agenda), `/calendario/api/eventos` (GET com filtros `inicio`/`fim`; POST com `request.get_json()` — criar evento), rate limit 60/min
- Vistas de calendário com navegação mensal/agenda, cores de evento (tomate → grafite, 11 classes `.evento-*`)
- **Esquema:** a tabela `evento` está coberta pela baseline do Flask-Migrate `3b14f5bd26a5` (v1.6.0) — não existe migração manual a executar no PythonAnywhere; o `db.create_all()` só corre em testes. Alterações futuras de esquema seguem o procedimento Flask-Migrate (ver «Procedimento de deploy no PythonAnywhere»)

### Módulo Combustíveis (`app/combustiveis/`)

- Modelos: `combustiveis_postos`, `combustiveis_precos_historico`, `combustiveis_utilizador_concelho`, `combustiveis_utilizador_combustivel`, `combustiveis_estado_atualizacao` — FK de utilizador apontam para `utilizadores.id`; as 5 tabelas estão cobertas pela baseline `3b14f5bd26a5` (v1.6.0) — o `db.create_all()` só corre em testes
- `services.py`: recolha via API Aberta (`api.apiaberta.pt`) com paginação por tipo de combustível; arquivamento automático de postos ausentes (`LIMIAR_CICLOS_AUSENTE = 2` ciclos); dedup conservadora por `nome+morada+concelho` (`obter_ids_duplicados`) com exclusão apenas em leitura; blocklist `NOMES_IGNORADOS`
- Rotas: `/combustiveis/` (dashboard + `POST /combustiveis/atualizar`, rate limit 6/hora), `/combustiveis/concelhos`, `/combustiveis/tipos`
- Scripts auxiliares: `reset_postos_combustiveis.py` (drop + `db.create_all()` + repovoamento; cria colunas `ativo`/`ciclos_ausente` que o `create_all()` não acrescenta a uma BD existente), `remover_postos_ignorados.py` (idempotente), `popular_combustiveis.py` (recolha manual) — os dois primeiros são **históricos/obsoletos** desde a v1.6.0 (o baseline cobre o schema); não executar (ver «Armadilhas conhecidas»)
- `seed.py`: `semear_concelhos_predefinidos` — cria concelhos por defeito (Braga, Vila Verde, Amares) para o primeiro admin (idempotente, não sobrescreve concelhos existentes)
- `scripts/criar_admin.py`: cria o admin + aplica seed de listas + concelhos + recolha inicial de postos (API Aberta, se tabela vazia e `APIABERTA_API_KEY` definida)
### Módulo Meteorologia (`app/meteorologia/`)

- Previsão do tempo em tempo real, com **Open-Meteo** (APIs de geocoding + forecast públicas, sem chave de API).
- **Etapa A — Localização:** modelo `LocalizacaoMeteorologia` (`meteorologia_localizacao`): `user_id` (FK, único), `nome`, `latitude`, `longitude`, `pais`, `regiao`, `timezone` (default `Europe/Lisbon`), `atualizada_em`; **1 localização por utilizador**; pesquisa por localidade com normalização (aceita "Gerês, Braga" para desambiguar) e confirmação.
- **Etapa B — Previsão:** `services.py` com funções puras `pesquisar_locais`, `guardar_localizacao`, `obter_previsao`, `obter_previsao_utilizador`; payload devolve `atual` (12 campos: temperatura, sensação térmica, humidade, precipitação, probabilidade de precipitação, código WMO, vento (velocidade + direção + ponto cardeal), UV, máx/mín do dia), `horaria` (próximas 24h) e `diaria` (próximos 7 dias); mapeamento WMO → descrição PT + emoji.
- **Resiliência:** API indisponível/timeout → mensagem amigável (200, nunca 500); campos ausentes → "—"; sem localização guardada → estado vazio com botão "Definir localização"; `timeout=8`s + `User-Agent` próprio (`PIPE-Meteorologia/1.0`).
- **Rotas:** `GET /meteorologia/` (previsão), `GET /meteorologia/localizacao` (Etapa A), `GET /meteorologia/api/pesquisar?q=` (rate limit 30/min), `POST /meteorologia/api/localizacao` (rate limit 10/min) — todas `@login_required`, filtradas por `user_id` (anti-IDOR).
- **Template:** server-side puro (Jinja) em `app/templates/meteorologia/` — previsão renderizada no servidor; AJAX com `'X-CSRFToken'` só na pesquisa/gravação da localização. Design com tokens claro/escuro, cards e botões no padrão PIPE.
- **Esquema:** migração `c420a200f2f2` (baseline `3b14f5bd26a5` → `c420a200f2f2`, criada com Flask-Migrate) — adiciona a tabela `meteorologia_localizacao`; aplicar no PythonAnywhere antes de abrir o módulo.
- **Testes:** `tests/test_meteorologia.py` (36 testes).

### Módulo Resumo Diário (`app/resumo_diario/`)

- Serviço determinístico em PT-PT que reúne meteorologia Open-Meteo, eventos, tarefas em prazo/atraso e, nos dias definidos, combustíveis e previsão/eventos de fim de semana. O texto final é redigido por LLM (fase 4) com validação estrita e fallback determinístico permanente. Envio automático diário apenas por Telegram para utilizadores com módulo instalado, chat_id e Telegram activo; guarda a data do último envio bem-sucedido em Europe/Lisbon.
- **Redacção por LLM (fase 4)** — `app/resumo_diario/redacao.py` reutiliza o cliente do Assistente (`chamar_llm(mensagens, prazo_total=…)`, sem ferramentas) para reescrever o texto determinístico: **tom de assistente pessoal real** (cumprimento pelo nome do dia, linguagem natural e descontraída com expressões do dia-a-dia, transições suaves, sem rótulos de secção), PT-PT, ≤ 900 caracteres, só os dados, sem inventar números nem recomendações; títulos de eventos/tarefas são dados (instruções neles são ignoradas). **Cobertura condicional (v1.8.3):** todos os tópicos PRESENTES nos dados têm de aparecer; se um tópico não está nos dados, não o menciona — e nunca escreve frases de ausência («não há…», «sem…») nem usa as palavras «dados», «secção» ou «resumo». A saudação de abertura varia de dia para dia — o prompt não fixa formato nem exemplos concretos, deixando o LLM escolher o tom natural. **Validação obrigatória antes de usar:** não vazia, dentro do limite, sem URLs, sem HTML (tags reais — `<A&B>` num título é legítimo), sem markdown (`**`, `` ` ``, `#` só no início de linha; `*` simples permitido), sem metalinguagem de ausência («sem dados», «fornecido/fornecida», «secção/seção», «tópico» — versão estreita: negações legítimas como «não há chuva» passam; palavras dessas famílias vindas de um título do utilizador, ex. «Limpar base de dados», são isentas), dia da semana coerente com a data do resumo (mencionar um dia fora dos cobertos — hoje/amanhã/fim-de-semana — cai no determinístico com `dia da semana errado`), todos os números existem nos dados (vírgula ≡ ponto; nomes de mês e «14h» contam como número; além disso: dia/mês/ano das datas cobertas — hoje, amanhã e, à sexta, sábado e domingo — e nomes de dias da semana) **e nenhum número dos dados se perde** (completude — ex.: largar a meteorologia cai no determinístico com `número em falta`) e as **palavras-chave** dos títulos dos dados sobrevivem à redacção numa maioria ≥50% (stopwords PT — de, com, o, ao… — não contam, mínimo 1 palavra; ex.: «Revisar… e enviar ao supervisor» ≡ «rever… e enviá-lo ao supervisor» — substantivos sobrevivem, verbos flexionam; uma tarefa omitida por completo, 0 palavras, é detectada; título só com stopwords exige a ocorrência literal). **Fallback garantido:** modelos todos em falha, `timeout`, validação, chave em falta ou interruptor desligado → texto determinístico; o resumo nunca falha por causa do LLM. Interruptor `RESUMO_LLM_ATIVO` (omissão: ligado; `0/false/off/desligado` desliga); orçamentos `RESUMO_LLM_ORCAMENTO_WEB` (10 s — pré-visualizar/enviar, `modo='web'`) e `RESUMO_LLM_ORCAMENTO_TASK` (30 s — task e simulação), configuráveis por variável de ambiente e impostos pelo cliente via parâmetro aditivo `prazo_total` (corta backoffs e limita o timeout de cada pedido ao tempo restante; levanta `PrazoExcedidoError`). Origem e motivo (e modelo, para calibrar a taxa de fallback) registados em log; a pré-visualização (JSON `origem`/`motivo` + linha de estado via `textContent`) e a simulação indicam a origem. Sem secções → não chama o LLM. O texto final do LLM passa pelo mesmo escape HTML do canal Telegram. **Sem alteração de BD.**
- A scheduled task executa combustíveis → resumo diário → avisos de tarefas → avisos de calendário. Quem recebeu o resumo nesse dia salta os dois avisos antigos; falhas mantêm a degradação graciosa.
- Configuração por utilizador: meteorologia, tarefas, eventos, combustíveis e fim de semana; todos activos por omissão. A ausência de linha equivale aos defaults; a leitura não grava. A tabela `resumo_diario_configuracoes` tem uma constraint única em `user_id` e é criada ao guardar as definições.
- Página `/resumo-diario/definicoes` com guardar, pré-visualização sem envio e envio manual apenas por Telegram. O envio manual aceita `chat_id` mesmo quando `telegram_activo` está desligado. Pré-visualização: 10/minuto; envio manual: 5/hora. A task permite `--so-resumo` e `--simular-resumo`, mais `--data AAAA-MM-DD` apenas com `--simular-resumo` (erro e saída caso contrário; nunca num envio real). Bloco de tarefas com rótulos «Vencem hoje»/«Em atraso (prazo)»; linha de meteorologia omite «precipitação 0%»; combustíveis em formato PT-PT (vírgula decimal, `Última recolha: dd/mm/aaaa hh:mm`).
- **Esquema:** migration `3058f716df40_adiciona_configuracao_resumo_diario.py` (`c420a200f2f2` → `3058f716df40`) e `8f3b90a1c2d4_regista_ultimo_envio_resumo.py`; baseline e revisões anteriores inalteradas.
- **Testes:** `tests/test_resumo_diario.py` (8), `tests/test_resumo_diario_fase2.py` (16), `tests/test_resumo_diario_fase3.py` (8, envio automático/idempotência), `tests/test_resumo_diario_texto.py` (13, ajustes de texto: 2ª execução não reenvia, Telegram desligado preserva avisos antigos, task completa suprime avisos antigos, rótulos, precipitação 0% omitida, formato PT-PT) e `tests/test_resumo_diario_fase4.py` (38, redacção LLM: resposta válida, prompt com data/dia do resumo e saudação variada, orçamentos, fallback por número inventado/em falta/longa/vazia/falha/timeout, interruptor, dia da semana errado/correcto/sem dia, títulos reescritos/condensados por palavras-chave (maioria ≥50%), metalinguagem/anti-metalinguagem e isenção de títulos, títulos como dados e completude, números PT/datas/dias, formas alternativas, escape no envio, origem na simulação e no log, sem secções). Mais 5 do prazo em `tests/test_assistente_cliente.py` e 4 da validação de argumentos em `tests/test_pipe_tasks.py` (regra `--data` só com `--simular-resumo`). O conftest desliga o LLM por omissão nos testes (`RESUMO_LLM_ATIVO=0`) — nenhum teste vai à rede.

### Assistente IA (`app/assistente/`)

- **Edição segura (v1.8.16):** nova ferramenta de escrita `atualizar_tarefa` para alterar texto, prioridade, prazo, lista, notas e etiquetas. Campos omitidos são preservados; `data_limite=null`, notas vazias/nulas e etiquetas vazias limpam os respectivos valores. Validação completa antes de gravar, listas limitadas ao utilizador e reinício de `notificada_em` quando o prazo muda. O modo de escrita orienta a consultar primeiro e usar o ID exacto. `atualizar_evento` valida campos, preserva os omitidos e normaliza datas ISO 8601 com fuso para Europe/Lisbon.

- **Cliente** (`cliente.py`): `chamar_llm(mensagens, ferramentas=None, prazo_total=None)` — HTTP POST para `openrouter.ai/api/v1/chat/completions`. Modelo principal via `OPENROUTER_MODEL` (default: `cohere/north-mini-code:free`) — **5 modelos no total (1 principal + 4 fallbacks)**. Fila de fallback: `nvidia/nemotron-3-super-120b-a12b:free`, `liquid/lfm-2.5-2.6b:free`, `dots-studio/dots-3-note-preview:free`, `poolside/laguna-s-2.1:free`. Auth por `OPENROUTER_API_KEY`; retry com backoff (3 tentativas: 2s, 5s, 10s) + fallback imediato em qualquer falha de provider (incluindo respostas HTTP 200 com `{"error": ...}` no corpo — detetadas por `_classificar_resposta()`, com classes `RateLimitError`/`ServicoIndisponivelError`; v1.8.0 acrescenta `PrazoExcedidoError` e o parâmetro aditivo `prazo_total` (segundos, opcional): prazo total da chamada entre tentativas e entre modelos — corta os backoffs e limita o timeout de cada pedido ao tempo restante; `None` (omissão) mantém o comportamento do Assistente. Usado pelo Resumo Diário (fase 4) para não prender a task nem o pedido web.)
- **Contexto** (`contexto.py`): `processar_mensagem_assistente(mensagem_utilizador, user_id, historico=None, modo=None, nome_completo=None)` — orquestra o fluxo: monta prompt + histórico, chama LLM, executa tool calls (máx. 4 iterações), guarda resposta. Inclui o nome completo do perfil autenticado no prompt, com instrução para usar o primeiro nome por padrão e o nome completo apenas quando relevante ou solicitado (v1.8.13). Histórico em Flask session (20 mensagens = 10 trocas, tecto de 3000 chars/mensagem e 8000 chars no total). `_contexto_temporal()` usa `datetime.now(ZoneInfo('Europe/Lisbon'))` para devolver a data/hora de Portugal — sem este fuso, o servidor (UTC no PythonAnywhere) devolveria o dia errado e o modelo resolveria "amanhã" incorrectamente (v1.8.7)
- **Ferramentas** (`ferramentas.py`): tool use com **8 funções de leitura** (`get_tarefas`, `get_notas`, `get_euromilhoes`, `get_resumo_geral`, `get_eventos`, `get_cambio`, `get_combustiveis`, `get_meteorologia`) e **11 de escrita** (`criar_tarefa`, `atualizar_tarefa`, `alternar_tarefa`, `apagar_tarefa`, `criar_nota`, `alternar_nota_acao`, `apagar_nota`, `criar_evento`, `atualizar_evento`, `apagar_evento`, `gerar_credencial`). Todas filtram por `user_id` (obrigatório, injetado pelo caller); `get_combustiveis` aceita `tipo_combustivel`, `concelho`, `posto` (nome **ou** marca, insensível a acentos e maiúsculas), `apenas_mais_barato` e `limite`; `get_meteorologia` recebe `detalhado` (bool) e consulta a previsão da localização guardada em Meteorologia. **Invariante (v1.7.4):** `REGISTO_FERRAMENTAS` tem de conter exactamente as ferramentas anunciadas nas definições — garantido por `tests/test_assistente_registo.py` (em v1.7.2 a adição de `get_meteorologia` apagou por engano a entrada de `criar_tarefa`, e o despachante devolvia "Ferramenta desconhecida")
- **Rotas** (`routes.py`):
  - `GET /assistente` — página de chat (tema claro/escuro)
  - `POST /assistente/api/chat` — AJAX `{mensagem: "..."}` → `{resposta: "..."}` (rate limit 30/min)
  - `POST /assistente/api/modo` — alterna modo leitura/escrita (rate limit 10/min)
  - `POST /assistente/api/limpar` — limpa histórico da sessão (rate limit 10/min)
- **System prompt:** PT-PT; capacidades limitadas à leitura em modo leitura (não sugere acções que não pode executar — encaminha para o módulo respectivo); nunca inventar dados; tom formal e conciso. **Anti-alucinação de meteorologia (08/10/2026):** qualquer pergunta sobre tempo obriga a chamar primeiro `get_meteorologia`, proibido apresentar valores sem resultado da ferramenta no turno, obrigatório citar local + fonte (Open-Meteo) + `meta.atualizada_em`, horizonte de 7 dias rolantes; garantido por `tests/test_assistente_prompt_meteorologia.py`
- Testes: `test_assistente_cliente.py` (13), `test_assistente_combustiveis.py` (31), `test_assistente_contexto.py` (9), `test_assistente_contexto_truncagem.py` (10), `test_assistente_meteorologia.py` (14), `test_assistente_registo.py` (8 — invariante registo↔definições + regressão `criar_tarefa`), `test_assistente_edicao.py` (14)

### Sistema de notificações (`app/notifications/`)

- Modelo `UserNotificationPreferences` (`notificacao_preferencias`) — preferências por canal (Telegram, Email, Tarefas, Calendário)
- `service.py` orquestra o envio; canais: `TelegramChannel` (python-telegram-bot) e `EmailChannel` (Zoho Mail API REST)
- **Emails PIPE (v1.8.15):** `email_templates.py` compõe assunto, HTML e texto simples para convite, recuperação de palavra-passe, 2FA, teste, Euromilhões, tarefas e Calendário; `EmailChannel` envia pela API Zoho Mail com OAuth 2.0. O token tem cache em `instance/zoho_access_token.json`, partilhada entre processos da aplicação e tarefas agendadas. `ZOHO_FROM_EMAIL` é enviado tal como configurado e aceita `PIPE <endereço@domínio>` para nome apresentado. `PIPE_PUBLIC_URL` define a origem dos links em tarefas agendadas (por omissão `https://felipejn.pythonanywhere.com`).
- **Convites por email (v1.8.15):** regista o resultado simples (`enviado`/`falhou`) e o `messageId` opcional; já não consulta estados de entrega. A migration `fd5793bc73bf` renomeia a coluna do ID Mailjet para `email_message_id`, preservando os IDs, e remove `email_verificado_em`. `scripts/verificar_mailjet.py` e `scripts/migrar_convites_mailjet.py` mantêm-se inalterados como referências históricas obsoletas; não executar.
- **Diagnóstico de falhas (v1.8.4):** ambos os canais guardam o motivo do último envio em `ultimo_resultado` (`{'sucesso', 'message_id', 'erro'}`), no mesmo contrato — o retorno continua `bool` para não partir os chamadores antigos (2FA, definições, resumo diário). `notification_service.ultimo_erro(canal)` expõe o motivo e `_registar_falhas()` escreve-o no log sempre que um canal devolve `False`. **`False` e `None` não são o mesmo:** `None` é canal não activo ou destinatário sem contacto (silencioso, esperado); `False` é o canal a correr e a falhar — e traz motivo.
- **Canal Telegram** — valida o `ok` do corpo da resposta (a Bot API devolve `{"ok": false, "error_code", "description"}`; `description` vive no **topo** do corpo, ao contrário da OpenRouter, que a aninha em `error`). O motivo fica em `ultimo_resultado['erro']` como `HTTP <error_code> — <description>` (ex.: `HTTP 403 — Forbidden: bot was blocked by the user`), `Erro de rede: …` ou `Destinatário sem chat_id de Telegram.`; o sucesso guarda o `message_id`. **Retry só em falhas transitórias:** rede, 408/425/429/500/502/503/504 repetem uma vez (2 s); 4xx permanentes (400/401/403/404/409) falham de imediato.
- **Log da scheduled task** — `_descrever(resultado, canal)` traduz cada canal para `ok` / `não activo` / `FALHOU (<motivo>)` nas linhas de Euromilhões, Tarefas e Calendário; o Resumo Diário distingue os dois casos de ausência.
- **Script `scripts/verificar_telegram.py`** — diagnóstico de ponta a ponta: `getMe` (token válido + identidade do bot), `getChat` por `chat_id` de cada utilizador da BD (detecta «bot was blocked» e «chat not found») e `--enviar-teste` (sendMessage real); aceita `--chat <id>`. Corre na consola do PA sem depender do log da task.
- **Testes:** `tests/test_notifications_telegram.py` (26: motivo por status/descrição, 200 com `ok: false`, corpo não-JSON, retry selectivo, escape HTML preservado, conselho por tipo de erro) mais 2 em `test_resumo_diario_fase3.py` e 2 em `test_pipe_tasks.py`.
- **Conselho por tipo de erro (`/settings/notificacoes`)** — o botão «Testar Telegram» mostra o motivo exacto e o conselho correspondente (`_conselho_telegram()`): `401`/`Unauthorized` → corrige `TELEGRAM_BOT_TOKEN` no `.env` e faz **Reload**; `ProxyError`/rede → falha do servidor, não do `chat_id`; `403`/`blocked` → envia primeiro uma mensagem ao bot; `chat not found`/`400` → confirma o `chat_id`.
- **Armadilha do `.env` (v1.8.6):** `config.py` faz `load_dotenv()` no import do módulo — corre **uma vez**, no arranque do processo. Alterar `TELEGRAM_BOT_TOKEN` (ou outra variável) **exige Reload** no PythonAnywhere; sem Reload a app usa o valor antigo e a API devolve `401`.

### Scheduled task (`scripts/pipe_tasks.py`)

- Única scheduled task do PythonAnywhere: `python /home/felipejn/pipe-app/scripts/pipe_tasks.py`
- Configuração: comando acima, **hora 07:00**, recorrência diária
- Módulos activos:
  | Tarefa | Frequência | Descrição |
  |---|---|---|
  | `tarefa_euromilhoes` | Terças e sextas | Verifica resultados dos sorteios |
  | `tarefa_tarefas` | Todos os dias | Notifica tarefas com prazo para hoje («Vencem hoje») e em atraso — 1×/dia enquanto persistirem |
  | `tarefa_combustiveis` | Terças-feiras | Actualiza preços dos postos (via API Aberta), respeitando o intervalo mínimo de 1x/dia por terça |
  | `tarefa_calendario` | Todos os dias | Lembretes de eventos no dia anterior («Amanhã») e no dia («Hoje»); ignora eventos já iniciados e respeita o toggle `notificar` |

### Autenticação 2FA

- Telegram, Email, TOTP (`pyotp` + `qrcode`)
- Múltiplos métodos em simultâneo — utilizador escolhe no login

### Design System (`app/static/css/pipe.css`)

- Tema escuro (por defeito) e tema claro — acentos âmbar/dourado mantêm-se nos dois
- **Tokens semânticos em `:root`:** superfícies, bordas, texto, estados, prioridades, `--cor-overlay-hover`, `--sombra` — ~23 cores fixas substituídas por variáveis
- **Tema claro via `[data-theme="light"]`** — sobrepõe apenas os tokens; o `data-theme` é definido no `<html>` antes do CSS (script anti-FOUC no `base.html`)
- Cores de identidade preservadas nos dois temas: âmbar (`--cor-primaria`), 11 classes `.evento-*` do Calendário, bolas do Euromilhões, `#1a1000` sobre âmbar no `.btn-primario`
- Componentes: navbar, cartões, formulários, botões, alertas, skeleton loader, toggles, modais
- Componentes Euromilhões: bolas, barras de frequência, badges de resultado
- Componentes Tarefas: sidebar, items, check circular, busca, badges, estado vazio, selector mobile
- Componentes Notas: grelha de cartões, palete de cores, checklist, sidebar de etiquetas, 8 cores alinhadas à paleta Google Keep
- Componentes Combustíveis: dashboard de preços, grelha de postos, selector de concelho/tipo, badge de última actualização
- Componentes Assistente IA: balões de chat (`chat-bubble`, `--user` âmbar, `--assistant` `#2a2f47`/`#2b3149`), faixa lateral âmbar nos balões do assistente, classes `cartao-novo` + `badge-novo` para destaque de módulos no dashboard
- Componentes Calendário: 11 cores de evento (`.evento-tomate` … `.evento-grafite`)

### Interface / Navegação (frontend)

- **Dashboard** — grelha híbrida de cartões dos módulos activos; lida com `MODULOS_DISPONIVEIS` e, para cada módulo activo, consulta o provider correspondente em `app/dashboard/registry.py` e exibe um resumo de métricas (`resumo` de Tarefas e Calendário na v1.7.0 — quando há dados: contagens como "3 Pendentes", "12 Total"; sem dados: card fica só com ícone + nome). O **badge de estado foi removido** — os três estados (`ok` / `nao_configurado` / `indisponivel`) mantêm-se a ser calculados internamente pelos providers, mas deixam de ser exibidos porque são redundantes: a própria presença das contagens confirma que o módulo está activo. Módulos sem provider ficam no layout clássico; renderização 100 % SQL local, sem HTTP externo. Card clássico com fallback automático (sem parâmetro `resumos`) — regressão zero.
- **Padrão AJAX/fetch no PIPE:**
  - Passar sempre `'X-CSRFToken': '{{ csrf_token() }}'` no header do fetch
  - Backend usa `request.get_json()` — não usa `validate_on_submit()`
- **Padrão de imports nos blueprints:**
  - `from app import db` — para SQLAlchemy
  - `from app.extensions import limiter` — para rate limiting

---

## Segurança

| Medida | Implementação | Ficheiro |
|---|---|---|
| CSRF | Flask-WTF CSRFProtect em todos os formulários | `app/__init__.py` |
| Rate limiting | Flask-Limiter nas rotas críticas | `app/auth/routes.py`, `app/combustiveis/routes.py`, `app/assistente/routes.py`, `app/extensions.py` |
| Logging de login falhado | `app.logger.warning` com username e IP | `app/auth/routes.py` |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` | `app/__init__.py` |
| CSP e HSTS | Content Security Policy; HSTS quando os cookies seguros estão activos | `app/__init__.py` |
| Segredo da aplicação | produção falha no arranque sem `SECRET_KEY`; desenvolvimento/testes geram chave aleatória se faltar | `app/__init__.py`, `config.py` |
| 2FA | código aleatório seguro, limitação de envio/reenvio e rejeição de contas inactivas | `app/auth/routes.py`, `app/auth/models.py` |
| Limites de upload | limite global, conversões, dimensões de imagem, CSV e número de linhas | `config.py`, `app/conversoes/routes.py`, `app/passwords/routes.py` |
| Password hashing | Werkzeug `generate_password_hash` / `check_password_hash` | `app/auth/models.py` |
| Controlo de acesso | `@login_required` e `@admin_required` | rotas protegidas |
| Configuração IP PA | `X-Forwarded-For` no Limiter | `app/extensions.py` |
| CORS do cofre | `COFRE_CORS_ORIGINS` (apenas `chrome-extension://<ID>`): origem autorizada recebe `Access-Control-Allow-Origin` + `Allow-Credentials`; origem errada não recebe o header | `app/__init__.py`, `config.py` |
| Cookie de sessão cross-site (extensão Chrome) | `SameSite=None` + `Secure` em produção (obrigatório para os `fetch` a partir de `chrome-extension://`); `Lax` em desenvolvimento | `config.py`, `app/__init__.py` |
| Sessão do cofre | chave AES só em Flask-Session server-side (`instance/flask_session/`); expira em `COFRE_SESSION_TIMEOUT` (900 s), bloqueando apenas o cofre | `app/passwords/routes.py` |

---

## Testes

- **Validação da v1.8.16 (2026-10-18):** `test_assistente_edicao.py` + `test_assistente_registo.py`: **22 passaram, 25 subtests passaram**. Suite integral: **371 passaram, 1 ignorado, 25 falharam** (todas em `test_assistente_combustiveis.py`); 33 subtests passaram. `git diff --check` limpo. A referência remota não pôde ser actualizada por falta de permissão em `.git/FETCH_HEAD`.

- Execução:
  - `pytest --collect-only -q` — recolhe os testes
  - `pytest -q` — executa a suite completa
- **Validação desta revisão (2026-10-17, já com `origin/main` integrado):** suite integral — **379 passaram, 1 ignorado**, 26 subtests passaram (60,79 s); `git diff --check` limpo. O ambiente `.venv` local aponta para um Python removido; a suite foi executada com Python 3.14 disponível.
- **Aviso do `conftest.py`:** nenhum teste pode tocar na BD real do PIPE. O `drop_all_seguro` intercepta `flask_sqlalchemy.SQLAlchemy.drop_all` e levanta `RuntimeError` sempre que a URI da BD não for `:memory:` — criar a app com `create_app('testing')` (SQLite em memória + sessões temporárias). A reatribuição de `SQLALCHEMY_DATABASE_URI` depois de `create_app()` não altera o engine já inicializado.

---

## Deploy no PythonAnywhere

### Estado

- **App online** em `https://felipejn.pythonanywhere.com` ✅
- **WSGI configurado** ✅
- **Static files** configurados ✅
- **Scheduled task** — `python /home/felipejn/pipe-app/scripts/pipe_tasks.py` às **07:00** ✅ (configuração confirmada no painel Tasks do PythonAnywhere)
- **Flask-Migrate — baseline `3b14f5bd26a5`** ✅: a produção foi **stamped** para `3b14f5bd26a5` em 2026-10-06 (a baseline **não** foi executada sobre os dados existentes — o esquema em produção já continha todas as tabelas e colunas); confirmar com `flask db current` (produção: `3b14f5bd26a5 (head)`; depois do deploy do Meteorologia: `c420a200f2f2 (head)`) e `flask db check` (limpo).
- **Esquema (Calendário, Cofre, Combustíveis, Convites)** ✅ — a baseline imutável `3b14f5bd26a5` registou o esquema histórico; a migration `fd5793bc73bf` converte o resultado de email e substitui as colunas Mailjet por `email_message_id`.
- **Configuração de produção** (pacotes via `pip install -r requirements.txt`, variáveis do `.env` como `COFRE_CORS_ORIGINS`, cookies `SameSite=None`/`Secure`) — não é verificável a partir do repositório; confirmar no painel/terminal do PythonAnywhere se ainda não foi feito
- **Extensão Chrome do Cofre** ⚠️: teste de ponta a ponta em produção pendente (ver «Pendências de deploy»)

### Migrations (Flask-Migrate)

A baseline `3b14f5bd26a5` cobre todas as tabelas e colunas actuais (incluindo `evento`); **exceto a migração pendente `c420a200f2f2` (Meteorologia)**; no PythonAnywhere não há outros comandos manuais de migração a executar. Novas alterações de esquema seguem o procedimento descrito em «Procedimento de deploy no PythonAnywhere».
- **Migração pendente — Meteorologia (`c420a200f2f2_adiciona_meteorologia_localizacao.py`):** aplica a tabela `meteorologia_localizacao` (Etapa A: uma localização por utilizador) antes de usar o módulo; executar `flask db upgrade` no PythonAnywhere, depois confirmar `flask db current` (deve indicar `c420a200f2f2 (head)`) e `flask db check` (limpo).


### WSGI

```python
import sys, os
from dotenv import load_dotenv

project_home = '/home/felipejn/pipe-app'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

load_dotenv(os.path.join(project_home, '.env'))

from app import create_app
application = create_app()
```

### Variáveis de ambiente no PA (`.env`)

```
FLASK_ENV=production
SECRET_KEY=<gerado com secrets.token_hex(32)>
TELEGRAM_BOT_TOKEN=...
ZOHO_CLIENT_ID=...
ZOHO_CLIENT_SECRET=...
ZOHO_REFRESH_TOKEN=...
ZOHO_ACCOUNT_ID=...
ZOHO_FROM_EMAIL=...
ZOHO_DC=eu
WISE_API_KEY=...
APIABERTA_API_KEY=...
COFRE_CORS_ORIGINS=chrome-extension://<ID da extensão>
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=cohere/north-mini-code:free
```

### Cópia de segurança da BD

`python scripts/backup_bd.py` copia `instance/pipe.db` para `instance/backups/pipe-AAAAMMDD-HHMMSS.db` (mantém as últimas 10). Correr antes de operações de risco (reset de tabelas, migrações manuais).

---

## Pendências de deploy
- **Módulo Meteorologia:** migration `c420a200f2f2` e validação em produção concluídas.

- **Calendário, Cofre, Combustíveis, Convites/Mailjet** — ✅ **resolvido pela baseline do Flask-Migrate** (`3b14f5bd26a5`, stamped no PA em 2026-10-06); os scripts manuais (`migrar_convites_mailjet.py`, `reset_postos_combustiveis.py`, `remover_postos_ignorados.py`) são históricos e **não devem ser executados**
- **Extensão Chrome do Cofre:** teste de ponta a ponta em produção seguindo `docs/guia-extensao-chrome.md` (login no PIPE → desbloquear cofre → visitar site com login guardado → preencher); confirmar CORS e que a chave do cofre não aparece nos cookies; recarregar ⟳ o cartão da extensão em `chrome://extensions` depois das alterações
- ⚠️ **Antes de qualquer operação de risco sobre a BD (ex.: `flask db upgrade`), correr:** `python scripts/backup_bd.py` e descarregar a cópia para a máquina local

---

## Procedimento de deploy no PythonAnywhere

### Deploy sem mudança de esquema (maioria dos deploys)

1. `python scripts/backup_bd.py` (recomendado)
2. `git pull`
3. `pip install -r requirements.txt`
4. Reload da aplicação
5. `flask db check` — deve continuar a devolver "No new upgrade operations detected."

### Alterações de esquema (Flask-Migrate)

A baseline `3b14f5bd26a5` é **imutável**: nunca editar nem reescrever migrations antigas; alterações futuras criam **novas revisions** a partir dela.

**Adopção inicial da baseline (já executada em 2026-10-06):**
`flask db check` → `flask db stamp 3b14f5bd26a5`

O `stamp` foi usado apenas uma vez, para registar que a BD de produção já correspondia ao esquema da baseline (a baseline não foi executada sobre os dados existentes). **Não** é o procedimento normal para futuras migrations.

**Fluxo normal para futuras alterações de schema:**

1. Alterar os modelos em `app/<módulo>/models.py`
2. `flask db migrate -m "descrição"` (em ambiente local)
3. Rever o diff da migration gerada em `migrations/versions/`
4. Testar (`pytest -q`) e validar o `flask db upgrade` numa BD vazia, se aplicável
5. `python scripts/backup_bd.py` **e descarregar a cópia** de `instance/backups/` para a máquina local
6. No PythonAnywhere: `git pull` → `pip install -r requirements.txt` → `flask db upgrade`
7. Confirmar com `flask db current` (revisão esperada) e `flask db check` (limpo)
8. Reload da aplicação

**Migração v1.8.11:** `flask db upgrade` aplica `d7a4c91e2f60` (colunas `nome` e `apelido` em `utilizadores`); confirmar `flask db current` em `d7a4c91e2f60` e executar Reload. A base SQLite configurada localmente foi migrada durante a validação desta alteração.

**Primeira instalação (v1.8.12):** executar `flask --app run db upgrade` antes de `python scripts/criar_admin.py`. O script pede username interno, email, nome próprio, apelido e palavra-passe. Se o username já existir, promove essa conta a administradora, preenche apenas os nomes em falta e mantém o email e a palavra-passe existentes.

### Restauro de backup

Com a **app parada**, copiar o ficheiro mais recente de `instance/backups/` para `instance/pipe.db` e arrancar a app.

---

## Armadilhas conhecidas

- **Variáveis do `.env` exigem Reload (v1.8.6)** — `config.py` faz `load_dotenv()` **no import do módulo**, ou seja uma única vez, no arranque do processo. Alterar `TELEGRAM_BOT_TOKEN` (ou qualquer variável) no ficheiro **não tem efeito** na app já a correr: o worker continua com o valor antigo. No PythonAnywhere é obrigatório **Reload** depois de escrever o `.env`. Sem isso, um token revogado e substituído continua a dar `HTTP 401 — Unauthorized` — que foi o que aconteceu em 14/10/2026. Nas *scheduled tasks* o efeito é imediato (cada execução é um processo novo), o que torna a armadilha ainda mais enganadora: a task vê o valor novo e a app web não.
- **`create_all()` só corre em testes (v1.6.0)** — nunca altera uma BD existente (não faz `ALTER TABLE`); o esquema evolui com Flask-Migrate: alterar o modelo → `flask db migrate -m "..."` → rever o diff → `python scripts/backup_bd.py` → `flask db upgrade`. BD local perdida ou para recriar de zero: `del instance\pipe.db` → `flask db upgrade` → `python scripts/criar_admin.py`
- **Scripts de migração manuais são históricos** — `scripts/migrar_convites_mailjet.py` (e outros `migrar_*.py`) e `scripts/reset_postos_combustiveis.py` estão **OBSOLETOS** desde a v1.6.0 (o baseline do Flask-Migrate cobre o schema); `scripts/verificar_mailjet.py` está **OBSOLETO** desde a v1.8.15. Ficam só como documentação — **NÃO alterar nem executar estes scripts**
- **Engine fixado em `db.init_app()`** — atribuir `app.config['SQLALCHEMY_DATABASE_URI']` **depois** de `create_app()` não tem efeito sobre o engine já construído; por isso os testes têm de usar `create_app('testing')` antes de qualquer reatribuição (o conftest bloqueia `db.drop_all()` com BD de ficheiro)
- **Cache do nginx do PythonAnywhere** — serve ficheiros estáticos com cache de longo prazo e **ignora parâmetros de query**; quando se altera o CSS é preciso actualizar o `cache-buster` em `base.html` (`?v=...`) para forçar o reload no browser
- **OpenRouter pode devolver HTTP 200 com erro** — quando o provider upstream falha, o corpo é `{"error": ...}`; o código do Assistente IA deve usar `_classificar_resposta()` em vez de confiar só em `raise_for_status()`; há fila de fallback de modelos gratuitos
- **`db` não está em `app.extensions`** — o objeto SQLAlchemy vive em `app/__init__.py` (importar via `from app import db`)

---

## Arquitectura de módulos

1. Criar `app/<modulo>/` com `__init__.py` + `routes.py` (+ `models.py` se BD)
2. Registar blueprint em `app/__init__.py`
3. Adicionar entrada em `app/modulos/config.py` (`MODULOS_DISPONIVEIS`) — o card aparece **automaticamente** na dashboard (layout híbrido de v1.7.0, sem editar `dashboard.html`)
4. Se o módulo quiser um resumo no dashboard (como Tarefas/Calendário): implementar provider em `app/<modulo>/dashboard.py` e registá-lo em `app/dashboard/registry.py::carregar_providers()`
5. Se precisa de scheduled task: adicionar em `scripts/pipe_tasks.py`

Padrões: AJAX via `'X-CSRFToken': '{{ csrf_token() }}'` + `request.get_json()`; imports `from app import db` e `from app.extensions import limiter`; rate limiting nas rotas críticas; tudo filtrado por `user_id` (anti-IDOR), exceto os `Posto` do Combustíveis que são globais.

---

## Próximos passos

1. **Extensão Chrome do Cofre:** concluir o teste ponta a ponta em produção — iniciar sessão no PIPE, desbloquear o Cofre, preencher credenciais num site, confirmar CORS e que a chave do Cofre não aparece nos cookies; validar também a expiração da captura pendente após 15 minutos.
2. Futuras alterações de schema seguem Flask-Migrate; nunca editar a baseline `3b14f5bd26a5`.
3. Manter `CHANGELOG.md` actualizado com cada versão.

---

## Dependências

- Flask 3.0, Flask-Login, Flask-WTF, Flask-SQLAlchemy, Flask-Limiter, Flask-Session
- Werkzeug, SQLAlchemy, python-dotenv
- pyotp, qrcode
- requests, python-telegram-bot
- Pillow, pillow_heif
- cryptography, bcrypt, flask-cors

## Contexto técnico

- Deploy em PythonAnywhere (plano free) por trás do nginx; base de dados SQLite em `instance/pipe.db`
- Modelo app factory: `create_app(config_name)` com ambiente `testing` para testes (SQLite em memória)
- Frontend vanilla JS inline nos templates; sem ficheiros JS externos por módulo
- PWA: `manifest.json` + `sw.js` (service worker, cache `pipe-v3`)
- Autenticação de dois fatores via Telegram, email e TOTP; convites com validade de 7 dias para registo

---

**Histórico de versões: ver [CHANGELOG.md](CHANGELOG.md)**
Documentação atualizada: v1.8.23 (partilha completa — backend + frontend)
- Correcção z-index 1001 + design btn secundario (calendario/index.html, partilha/modal_partilhar.html) — aprovado 2026-10-19
