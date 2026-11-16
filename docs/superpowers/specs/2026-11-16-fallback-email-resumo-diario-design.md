# Fallback por email para o Resumo Diário

## Intenção

Evitar que um resumo diário se perca quando o Telegram não é usado pelo utilizador, não está configurado ou falha. O email serve de fallback, respeitando a preferência de email nas entregas automáticas.

## Objetivos e limites

- Tentar Telegram primeiro quando estiver ativo e configurado.
- Enviar por email quando o Telegram estiver inativo, sem chat_id ou falhar, desde que o email esteja ativo.
- Não duplicar o resumo por email quando o Telegram tiver sucesso.
- Marcar o envio diário como concluído após sucesso em qualquer canal; manter por tentar se ambos falharem.
- Criar um template de email específico do Resumo Diário, coerente com o layout PIPE.
- Acrescentar na página do Resumo Diário uma ação manual para testar o envio pelo email com o template real.

## Abordagens consideradas

1. **Fallback estrito (escolhida):** Telegram primeiro; email só se Telegram não for utilizável ou falhar. Evita duplicados e cobre falhas transitórias ou preferência por não usar Telegram.
2. **Envio multicanal:** enviar por ambos sempre que ativos. Aumenta redundância, mas duplica a mensagem nos dias em que o Telegram funciona.

## Decisões de implementação

- O agendamento respeita `telegram_activo`, `telegram_chat_id` e `email_activo`.
- O teste manual por email é explícito, não depende de `email_activo`, mas exige email de destino e canal Zoho configurado; mantém-se coerente com o envio manual por Telegram.
- A mesma mensagem gerada para o resumo é fornecida ao template em HTML e texto simples.
- Sem alteração de base de dados ou dependências prevista.

## Fica ao critério do implementador

- Os nomes internos do tipo de email, da rota de teste e dos elementos da interface, seguindo as convenções existentes.
- Textos de erro específicos para canal não configurado, email ausente e falha do envio.
