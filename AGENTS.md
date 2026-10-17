# Instruções de trabalho para o Codex

- Comunicar e produzir documentação em português europeu (PT-PT), salvo pedido explícito em contrário.
- Antes de iniciar alterações, confirmar que a cópia local está actualizada face ao repositório remoto. Consultar o estado e a diferença entre a branch local e a remota; se não for possível actualizar a referência remota, indicar essa limitação antes de avançar.
- Antes de editar, verificar o estado do Git e preservar alterações locais do utilizador; não as descartar nem as incluir no commit sem autorização explícita.
- Antes de alterar o projecto, ler `Estado_Atual.md` e `CHANGELOG.md` para compreender o estado e o histórico documentados.
- Após cada alteração, executar os testes adequados à alteração e, quando viável, a suite completa. Apresentar um relatório conciso do que foi feito e dos resultados; se não for possível executar algum teste, explicar o motivo e indicar o que ficou por validar.
- Não incluir no commit segredos, credenciais, `.env`, bases de dados locais ou artefactos gerados.
- Depois de apresentar o relatório da alteração, a aprovação do utilizador autoriza a actualização de `Estado_Atual.md` e `CHANGELOG.md` segundo a estrutura, o estilo e as convenções de versão/data existentes, seguida de commit no padrão do histórico e push para o remoto. Não pedir uma aprovação separada para estes passos. Apresentar o relatório final com testes, documentação, commit e push.
