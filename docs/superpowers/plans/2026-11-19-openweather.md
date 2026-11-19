# Migração OpenWeather Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrar a meteorologia para OpenWeather gratuita, mantendo o payload consumido pela aplicação e limitando-o a cinco dias.

**Architecture:** A pesquisa geográfica usa a Geocoding API. A previsão combina Current Weather e Forecast 5 day/3 hour, normalizando dados no serviço existente e preservando cache e fallback.

**Tech Stack:** Python, Flask, requests, pytest.

**Spec:** `docs/superpowers/specs/2026-11-19-openweather.md`

## Global Constraints

- Não alterar nem ler `.env`.
- Preservar alterações locais em `.env.example` e `config.py`.
- Não mudar o formato público normalizado sem necessidade.
- Não declarar sete dias quando a API fornece cinco.

## Review Focus

- Chave em falta: falha controlada e cache existente continua disponível.
- Erro de qualquer endpoint: fallback cache ou indisponível sem payload parcial.
- Campos opcionais ausentes: payload continua válido.
- Mudança de dia/timezone: agrupamento diário respeita `dt_txt` local da OpenWeather.
- Chuva/neve: precipitação agregada não é confundida com probabilidade `pop`.

---

### Task 1: Geocoding OpenWeather

**Files:** `app/meteorologia/services.py`, `tests/test_meteorologia.py`

- [x] Adaptar primeiro os testes da pesquisa para `q`, `limit`, `appid` e resposta OpenWeather.
- [x] Executar os testes alterados e confirmar falha esperada.
- [x] Normalizar `local_names.pt`/`name`, `lat`, `lon`, `country`, `state` e timezone predefinido.
- [x] Executar os testes da pesquisa.

### Task 2: Previsão e normalização

**Files:** `config.py`, `app/meteorologia/services.py`, `tests/test_meteorologia.py`, `tests/test_assistente_meteorologia.py`

- [x] Criar fixtures OpenWeather para tempo actual e entradas forecast de 3 horas; testar os dois pedidos, unidades, chave, normalização, agregação e falhas.
- [x] Executar testes alterados e confirmar falha esperada.
- [x] Ler a chave na configuração geral; mapear códigos OpenWeather; normalizar campos; calcular diários até cinco dias e cache.
- [x] Actualizar fixtures/fontes e executar testes meteorológicos e do Assistente.

### Task 3: Contratos de texto

**Files:** `app/templates/meteorologia/index.html`, `app/assistente/contexto.py`, `app/assistente/ferramentas.py`, `app/meteorologia/models.py`

- [x] Actualizar rótulos e instruções de Open-Meteo/7 dias para OpenWeather/até 5 dias.
- [x] Rever as referências documentais de provider no módulo.

### Task 4: Verificação

- [x] Executar os testes focados de Meteorologia, Assistente, prompts e Resumo Diário.
- [x] Executar a suite completa, `python -m compileall -q app config.py` e `git diff --check`.
- [x] Rever o diff para garantir que `.env` e as alterações locais iniciais não foram expostas ou descartadas.
