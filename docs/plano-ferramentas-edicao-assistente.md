# Plano: edição de tarefas e compromissos pelo Assistente IA

## Objectivo

Permitir que o Assistente IA altere tarefas e compromissos existentes, incluindo prazos e datas, através de ferramentas de escrita seguras e coerentes com os módulos Tarefas e Calendário.

## Estado deste documento

Implementação concluída na v1.8.16 (2026-10-18). A ferramenta `atualizar_tarefa`, o reforço de `atualizar_evento` e as instruções do modo de escrita foram integrados em `app/assistente/`; os testes estão em `tests/test_assistente_edicao.py`. Este diagnóstico fica como registo do plano executado.

## Diagnóstico verificado

- O Assistente separa ferramentas de leitura e escrita em `app/assistente/ferramentas.py`. `DEFINICOES_FERRAMENTAS_ESCRITA` combina as ferramentas de leitura com `DEFINICOES_FERRAMENTAS_ESCRITA_EXTRA`; `REGISTO_FERRAMENTAS` associa nomes de ferramentas a funções Python; `executar_ferramenta` só permite mutações em modo `escrita` e aplica limite por sessão.
- Para tarefas já existem `get_tarefas`, `criar_tarefa`, `alternar_tarefa` e `apagar_tarefa`. **Não existe `atualizar_tarefa`** na definição, no registo, no conjunto de escrita ou na implementação. Por isso o Assistente não consegue mudar prazo, texto, prioridade, lista, notas ou etiquetas de uma tarefa existente.
- Para compromissos/eventos já existem `get_eventos`, `criar_evento`, `atualizar_evento` e `apagar_evento`. A ferramenta `atualizar_evento` está registada como escrita e é exposta ao modelo em modo de execução. Permite alterar título, início/fim, descrição, localização, cor, dia inteiro e notificação.
- A função `atualizar_evento` filtra por `evento_id` e `user_id`, preserva valores omitidos, analisa datas ISO 8601, valida `data_fim >= data_inicio` e repõe `notificado_em`. A definição da ferramenta deve ser revista para garantir que o modelo compreende bem actualizações parciais de data: uma alteração apenas de início/fim pode falhar se o outro extremo mantido tornar o intervalo inválido.
- O modelo `Tarefa` (`app/tarefas/models.py`) inclui `texto`, `prioridade` (`baixa`, `media`, `alta`), `data_limite` (`Date`, anulável), `notas`, `notificada_em`, `lista_id`, `user_id` e relação `tags`. A rota normal de edição (`app/tarefas/routes.py`, `editar_tarefa`) valida a lista do utilizador, edita esses campos e limpa `notificada_em`.
- O modelo `Evento` (`app/calendario/models.py`) inclui `titulo`, `descricao`, `localizacao`, `data_inicio`, `data_fim`, `dia_inteiro`, `cor`, `notificar`, `notificado_em` e `user_id`. A rota normal de edição está em `app/calendario/routes.py`.
- As instruções do Assistente estão em `app/assistente/contexto.py`. No modo de escrita já exigem IDs vindos das ferramentas e descrevem a execução de acções; devem incluir uma regra clara para consultar primeiro o registo pretendido, escolher o ID exacto e só enviar campos que o utilizador pediu para alterar.
- A suite existente inclui `tests/test_assistente_contexto.py`, mas não foi encontrada suite dedicada à edição de tarefas/eventos. Procurar os testes de ferramentas existentes durante a implementação antes de decidir se criar novo ficheiro ou estender outro.

## Plano de implementação executado

### 1. Adicionar edição segura de tarefas

Em `app/assistente/ferramentas.py`:

1. Criar a definição OpenAI Function Calling `atualizar_tarefa`, com `tarefa_id` obrigatório e os campos opcionais `texto`, `prioridade`, `data_limite`, `lista_nome`, `notas` e `tags`.
2. Distinguir campo omitido de campo explicitamente nulo/vazio. Em particular, aceitar `data_limite: null` para remover o prazo. Documentar esta semântica na definição da ferramenta para evitar que o modelo omita acidentalmente dados existentes.
3. Implementar `atualizar_tarefa(user_id, tarefa_id, ...)` filtrando a tarefa por ambos `id` e `user_id`. Para lista, resolver apenas uma lista pertencente ao utilizador e devolver erro claro se não existir; não criar listas implicitamente ao editar, salvo decisão explícita em contrário.
4. Validar prioridade contra `Tarefa.PRIORIDADES`, prazo em `AAAA-MM-DD` (mais `null` para limpar), limites de comprimento existentes e argumentos de etiquetas. Não alterar nem gravar nenhum campo se algum valor falhar validação.
5. Reutilizar `_obter_ou_criar_tags` para as etiquetas se for adequado ao comportamento da interface; definir explicitamente se `tags` vazio limpa todas as tags e se tags não indicadas permanecem intactas. Recomenda-se: campo omitido preserva; string/lista vazia limpa.
6. Se o prazo for fornecido e alterado, definir `tarefa.notificada_em = None`, tal como a rota normal. Confirmar se a rota sempre limpa actualmente mesmo quando prazo não mudou e optar pela semântica consistente necessária.
7. Adicionar `atualizar_tarefa` a `FERRAMENTAS_ESCRITA`, `DEFINICOES_FERRAMENTAS_ESCRITA_EXTRA` e `REGISTO_FERRAMENTAS`.

### 2. Rever edição de compromissos

1. Manter `atualizar_evento` como ferramenta de alteração existente; não duplicar ferramenta sem necessidade.
2. Melhorar a descrição/esquema para indicar que só os campos pretendidos devem ser fornecidos e que `data_inicio`/`data_fim` são ISO 8601.
3. Decidir e documentar como deslocar parcialmente um compromisso: (a) o modelo envia ambos início e fim com o intervalo actualizado; ou (b) a ferramenta desloca automaticamente a outra extremidade mantendo a duração. Recomenda-se começar por (a), instruindo o modelo a consultar o evento e enviar ambas as datas quando uma mudança de data/hora possa invalidar o intervalo. Não inferir duração sem validação do utilizador.
4. Confirmar que datas inválidas, fim anterior ao início e evento pertencente a outro utilizador devolvem erro sem persistência. Preservar a reposição de `notificado_em` quando o evento é editado.

### 3. Melhorar instruções de utilização

Em `app/assistente/contexto.py`, nas instruções de escrita:

- Para editar tarefa ou compromisso, consultar primeiro usando `get_tarefas`/`get_eventos`, identificar o registo sem ambiguidade e reutilizar o ID devolvido.
- Alterar apenas os campos pedidos. Se houver vários registos com nomes semelhantes, pedir clarificação ao utilizador em vez de escolher arbitrariamente.
- Interpretar datas relativas usando a data/hora actual já fornecida no contexto e enviar formato absoluto exigido pela ferramenta.
- Para remover prazo da tarefa, enviar o valor nulo previsto no esquema; não tratar omissão como remoção.
- Para eventos, garantir início e fim coerentes ao alterar a data/hora; não declarar sucesso quando a ferramenta devolver erro.

### 4. Testes

Adicionar testes unitários/integrados usando a configuração de teste da aplicação (nunca a base de dados local de ficheiro):

- Definição, registo e disponibilidade de `atualizar_tarefa` em modo de escrita; rejeição em modo de leitura.
- Actualização de prazo e de cada campo editável; preservação dos campos omitidos.
- Remoção explícita do prazo; distinção entre campo omitido e nulo.
- Reset de `notificada_em` na mudança de prazo.
- Erros para data inválida, prioridade inválida, tarefa inexistente/de outro utilizador e lista inexistente/de outro utilizador; confirmar que não há gravação parcial.
- Semântica das etiquetas: omitidas preservam; vazias limpam (se esta decisão for adoptada); novos nomes seguem as regras de tags actuais.
- Eventos: edição parcial de campos não temporais; mudança válida de data; intervalo inválido e datas ISO inválidas sem persistência; isolamento por `user_id`; reset da notificação.
- Fluxo do contexto: quando o modelo pede uma ferramenta de edição, `executar_ferramenta` recebe o nome, argumentos e modo correctos. Testar prompt/instruções se houver teste apropriado.

Executar primeiro os testes focados do Assistente e depois a suite completa, se viável. Nunca executar testes contra `instance/pipe.db`; usar `create_app('testing')`/fixtures existentes.

## Ficheiros a inspeccionar/alterar na implementação

- `app/assistente/ferramentas.py` — esquema das ferramentas, funções, registo e controlo de escrita.
- `app/assistente/contexto.py` — instruções do modelo para edição segura.
- `tests/` — testes das ferramentas do Assistente, tarefas e calendário; localizar os existentes antes de criar novos.
- `Estado_Atual.md` e `CHANGELOG.md` — actualizar apenas após relatório da alteração e aprovação do utilizador, conforme as instruções do projecto.

Não se prevê alteração de modelo ou esquema de base de dados; confirmar durante implementação.

## Contexto Git e trabalho paralelo (verificado em 2026-10-17)

- Branch: `main`, HEAD `968c262` (`feat: reformular emails com modelos visuais PIPE`). Tracking indica `origin/main`; comparação local reportada: `0 0`.
- A tentativa de `git fetch origin` falhou com `error: cannot open '.git/FETCH_HEAD': Permission denied`. Portanto, a igualdade com `origin/main` é apenas face à referência remota local; não foi possível confirmar o estado actual do servidor remoto.
- No primeiro diagnóstico, `git status` estava limpo. Na verificação seguinte, surgiram alterações paralelas locais. **Estas alterações não pertencem a este plano e devem ser preservadas:**
  - Modificados: `app/auth/forms.py`, `app/auth/models.py`, `app/auth/routes.py`, `app/settings/routes.py`, vários templates em `app/templates/`, `scripts/pipe_tasks.py`, `tests/test_security_hardening.py`, `tests/test_tarefas_listas_predefinidas.py`.
  - Novo: `migrations/versions/d7a4c91e2f60_adiciona_nomes_e_login_por_email.py`.
- Antes da implementação, executar `git status --short --branch`, rever o diff e coordenar sobreposição, em particular alterações em testes de tarefas/auth. Não fazer checkout, reset, stash, commit ou inclusão destas alterações sem autorização explícita.
- Ler novamente `Estado_Atual.md` e `CHANGELOG.md` antes de implementar. O estado consultado indicava v1.8.10.

## Critérios de conclusão

- O assistente consegue alterar o prazo de uma tarefa existente e confirmar a alteração apenas após sucesso da ferramenta.
- O assistente consegue alterar compromissos existentes através da ferramenta já disponível, com intervalo temporal coerente.
- Nenhuma ferramenta consegue aceder ou alterar objectos pertencentes a outro utilizador.
- Argumentos inválidos não provocam gravações parciais e notificações são reabertas conforme as regras do módulo.
- Testes focados e suite aplicável passam; documentação do estado/histórico é actualizada após aprovação do relatório.
