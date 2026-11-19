# Migração da meteorologia para OpenWeather

## Intenção

Substituir Open-Meteo pela OpenWeather no módulo Meteorologia usando a chave já configurada pelo utilizador e os endpoints gratuitos de tempo actual e previsão de cinco dias com intervalos de três horas.

## Objectivos

- Pesquisar localidades pela Geocoding API da OpenWeather.
- Obter dados actuais e previsão com `data/2.5/weather` e `data/2.5/forecast`.
- Preservar o payload normalizado consumido pelo módulo, Assistente e Resumo Diário.
- Agregar os dados de três em três horas em resumos diários, incluindo temperaturas, probabilidade e precipitação.
- Manter cache, fallback e idioma PT-PT.
- Indicar a fonte OpenWeather e o alcance verdadeiro de até cinco dias.

## Fora de âmbito

- API paga One Call ou previsões de sete dias.
- Alterações à base de dados ou dependências.
- Expor ou registar a chave API.

## Abordagens consideradas

- Endpoints gratuitos actuais + previsão 5 dias/3 horas: escolhida; usa a chave existente e exige indicar o limite de cinco dias.
- One Call com previsão de sete dias: excluída por requerer subscrição não confirmada.

## Restrições

- Preservar alterações locais existentes em `.env.example` e `config.py`.
- A chave é lida da configuração Flask; testes usam chave fictícia.
- O payload mantém as chaves internas já consumidas, ainda que `codigo_wmo` permaneça por compatibilidade.
- Sem alterações de BD/dependências; deploy no PythonAnywhere requer `git pull`, configurar `OPENWEATHER_API_KEY` e Reload.
