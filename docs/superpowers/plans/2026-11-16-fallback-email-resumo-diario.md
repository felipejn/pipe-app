# Plano de Implementação — Fallback por email do Resumo Diário

> **Para agentes:** usar a sub-skill obrigatória `superpowers:executing-plans` e executar as tarefas pela ordem indicada. Os passos usam caixas de verificação (`- [ ]`).

**Goal:** Entregar o Resumo Diário por email quando o Telegram não estiver disponível ou falhar, e permitir testar o envio por email na página do módulo.

**Architecture:** O serviço agendado tenta Telegram primeiro e, em caso de indisponibilidade/falha, chama o canal de email com um tipo de template dedicado. O endpoint manual de teste usa a mesma composição do email e mantém a rota Telegram existente independente.

**Tech Stack:** Flask, SQLAlchemy, Jinja2, Zoho Mail API, pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-fallback-email-resumo-diario-design.md`

## Global Constraints

- Comunicar e escrever documentação em PT-PT.
- Preservar `poupa_mais.png` não rastreado e todas as alterações do utilizador.
- Respeitar preferência `email_activo` no fallback automático; o teste manual explícito pode ignorar essa preferência.
- Não enviar email se o Telegram tiver sucesso.
- Sem alteração de BD ou dependências.

## Review Focus

- Utilizador sem Telegram ativo, com email ativo: envia um email e regista a data do envio.
- Telegram ativo sem chat_id: recorre ao email ativo, em vez de ignorar o utilizador.
- Falha do Telegram: envia email; sucesso do Telegram: não duplica.
- Ambos os canais falham ou estão indisponíveis: não regista o resumo como entregue.
- Email de teste sem endereço/canal configurado ou com falha Zoho: mostra erro sem expor segredos.

---

### Task 1: Template dedicado do Resumo Diário

**Files:**
- Modify: `app/notifications/email_templates.py`
- Modify: `app/templates/emails/email.html`
- Modify: `app/templates/emails/email.txt`
- Test: `tests/test_convites_email.py` ou novo `tests/test_resumo_diario_email.py`

**Interfaces:**
- Produces: `compor_email('resumo_diario', {'nome': ..., 'data': ..., 'texto': ...})` retorna assunto, alternativa texto e HTML.

- [x] Testar assunto/data, nome e conteúdo com caracteres HTML escapados no HTML e preservados no texto.
- [x] Implementar assunto, preheader e blocos HTML/texto com a mensagem e uma ligação para o módulo.
- [x] Executar os testes do template.

### Task 2: Fallback automático por email

**Files:**
- Modify: `app/resumo_diario/services.py`
- Test: `tests/test_resumo_diario.py` e/ou `tests/test_resumo_diario_fase3.py`

**Interfaces:**
- Consumes: `compor_email` via `notification_service.send(..., email_template='resumo_diario', email_context=...)`.
- Preserves: `enviar_resumos_diarios(data=None, simular=False)` retorna IDs cujo envio diário teve sucesso.

- [x] Cobrir elegibilidade para Telegram ativo, email ativo sem Telegram e utilizador sem canais ativos.
- [x] Cobrir fallback por Telegram desativado/sem chat_id, falha Telegram, sucesso Telegram sem duplicação, ambos canais falhados e simulação.
- [x] Atualizar elegibilidade para aceitar um canal utilizável segundo as preferências.
- [x] Implementar tentativa Telegram primeiro e email apenas se Telegram não entregar; registar a data se qualquer canal entregar.
- [x] Executar os testes focados do agendamento.

### Task 3: Teste manual de email na página do módulo

**Files:**
- Modify: `app/resumo_diario/routes.py`
- Modify: `app/templates/resumo_diario/definicoes.html`
- Test: `tests/test_resumo_diario_fase2.py`

**Interfaces:**
- Produces: endpoint autenticado `POST /resumo-diario/api/testar-email` com resposta JSON `{ok, mensagem}`.

- [x] Cobrir envio com canal forçado email, template/contexto corretos, sem endereço ou serviço disponível e falha do envio.
- [x] Implementar endpoint limitado por rate limit, usando o resumo gerado no momento e o template dedicado.
- [x] Adicionar botão separado «Testar envio por email» e encaminhá-lo pela função JS já usada na página.
- [x] Executar os testes focados da rota e verificar a renderização do template.

### Task 4: Revisão e validação

**Files:**
- Verify: `app/resumo_diario/services.py`, `app/resumo_diario/routes.py`, templates e testes alterados.

- [x] Executar a suite focada do Resumo Diário e emails.
- [x] Executar `git diff --check` e rever o diff para confirmar que `poupa_mais.png` não foi incluído.
- [x] Apresentar relatório de alterações e validação para aprovação; após aprovação, atualizar `Estado_Atual.md`/`CHANGELOG.md`, criar commit e fazer push.
