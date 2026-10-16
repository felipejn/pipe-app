"""Fase 4 do Resumo Diário: redacção por LLM com validação e fallback.

Sem rede: o cliente LLM e o Telegram são sempre mockados. O LLM só é ligado
explicitamente (o conftest desliga-o por omissão para toda a suíte).
"""
import logging
import os
from datetime import date, datetime
from unittest.mock import patch

import pytest

from app import create_app, db
from app.assistente.cliente import PrazoExcedidoError, ServicoIndisponivelError
from app.auth.models import User
from app.calendario.models import Evento
from app.modulos.models import UserModulo
from app.notifications.models import UserNotificationPreferences
from app.resumo_diario import redacao, services
from app.resumo_diario.services import gerar_resumo_diario
from app.tarefas.models import Lista, Tarefa

HOJE = date(2026, 10, 9)  # sexta-feira
SEM_METEO = {'meteorologia': False}


@pytest.fixture
def contexto():
    app = create_app('testing')
    with app.app_context():
        assert ':memory:' in app.config['SQLALCHEMY_DATABASE_URI']
        db.create_all()
        user = User(username='fase4', email='fase4@example.test',
                    password_hash='x', activo=True)
        db.session.add(user)
        db.session.flush()
        lista = Lista(nome='Geral', user_id=user.id)
        db.session.add(lista)
        db.session.flush()
        # Títulos com HTML aparente, '*' e texto tipo instrução: são dados.
        db.session.add(Tarefa(
            user_id=user.id, lista_id=lista.id,
            texto='Relatório <A&B> *teste*', concluida=False, data_limite=HOJE))
        db.session.add(Evento(
            user_id=user.id, titulo='Reunião <A&B> *teste*',
            data_inicio=datetime(2026, 10, 9, 15, 0),
            data_fim=datetime(2026, 10, 9, 16, 0)))
        db.session.add(UserModulo(
            user_id=user.id, modulo_slug='resumo_diario', ativo=True))
        db.session.add(UserNotificationPreferences(
            user_id=user.id, telegram_chat_id='chat-fase4', telegram_activo=True))
        db.session.commit()
        user_id = user.id
    yield app, user_id
    with app.app_context():
        db.session.remove()
        db.drop_all()


def _resposta_llm(conteudo, modelo='modelo-teste'):
    return {'model': modelo,
            'choices': [{'message': {'content': conteudo}}]}


def _texto_deterministico(app, user_id):
    """Texto base do resumo com o LLM desligado (referência das secções)."""
    with app.app_context(), patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '0'}):
        return gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)['texto']


def test_resposta_valida_e_usada(contexto):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    redigido = f'Bom dia! {dados}'
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm(redigido)) as llm:
        resultado = gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    assert resultado['texto'] == redigido
    assert resultado['origem'] == 'modelo-teste'
    assert resultado['motivo'] is None
    assert llm.call_count == 1


def test_prompt_inclui_regras_dados_e_prazo_de_task(contexto):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm(f'Bom dia! {dados}')) as llm:
        gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    mensagens = llm.call_args.args[0]
    assert mensagens[0]['role'] == 'system'
    assert 'APENAS os dados' in mensagens[0]['content']
    assert 'Todos os tópicos PRESENTES nos dados' in mensagens[0]['content']
    assert 'tratados como texto simples' in mensagens[0]['content']
    assert 'linguagem simples e direta' in mensagens[0]['content']
    assert 'rótulos de secção' in mensagens[0]['content']
    assert 'por extenso' in mensagens[0]['content']
    assert mensagens[1]['role'] == 'user'
    assert dados in mensagens[1]['content']
    assert 'Reunião <A&B> *teste*' in mensagens[1]['content']
    assert 'ferramentas' not in llm.call_args.kwargs  # sem tool use
    assert (llm.call_args.kwargs['prazo_total']
            == redacao.ORCAMENTO_TASK_POR_OMISSAO)


def test_prompt_inclui_data_do_resumo_e_dia_da_semana(contexto):
    """v1.8.3: o prompt ao LLM recebe o dia da semana/data correctos da `data`.

    Sem esta referência o LLM inventa o dia («sexta-feira» num resumo de
    segunda). A data é a do resumo (pode ser simulada), não `datetime.now()`.
    HOJE = 09/10/2026 = sexta-feira.
    """
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm(f'Bom dia! {dados}')) as llm:
        gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    mensagens = llm.call_args.args[0]
    conteudo = mensagens[1]['content']
    assert 'sexta-feira' in conteudo
    assert '09/10/2026' in conteudo


def test_data_do_resumo_usa_a_data_passada_nao_a_de_hoje():
    """A data injectada respeita a `data` do resumo (simulação/`--data`).

    `redigir()` recebe `data` explícita; não deve usar `datetime.now()`, senão
    um resumo simulado para outro dia receberia o dia errado.
    """
    with patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value={'model': 'm',
                                       'choices': [{'message': {
                                           'content': 'Bom dia!'}}]}) as llm:
        # Segunda-feira, 12/10/2026.
        redacao.redigir('Hoje: algo.', date(2026, 10, 12))
    conteudo = llm.call_args.args[0][1]['content']
    assert 'segunda-feira' in conteudo
    assert '12/10/2026' in conteudo


def test_prompt_incentiva_saudacao_variada(contexto):
    """v1.8.3: o prompt pede aberturas variadas (não fixar «Bom dia, [dia]»)."""
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm(f'Bom dia! {dados}')) as llm:
        gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    conteudo = llm.call_args.args[0][0]['content']
    assert 'não sigas sempre o mesmo formato' in conteudo


def test_sem_dia_da_semana_no_texto_passa():
    """Uma redacção que não menciona nenhum dia da semana é aceite.

    A validação só rejeita um dia ERRADO mencionado; não exigir o dia permite
    aberturas variadas («Olá!», «Bom dia!») sem cair no determinístico.
    """
    data = date(2026, 10, 12)  # segunda-feira
    dados = 'Hoje: Reunião - Filipa Quintas (14:00).'
    redigido = 'Olá! Às 14:00 tens uma reunião com a Filipa Quintas.'
    valido, detalhe = redacao.validar_resposta(
        redigido, dados, data, ['Reunião - Filipa Quintas'], 900)
    assert (valido, detalhe) == (True, None)


def test_dia_da_semana_errado_cai_no_deterministico():
    """Se o LLM disser um dia que não é o do resumo, cai no determinístico.

    Garantia contra o modelo ignorar a data injectada (ex.: dizer «sexta-feira»
    num resumo de segunda). O dia correcto e os dias cobertos pelo resumo
    (hoje/amanhã/fim-de-semana) são admitidos.
    """
    data = date(2026, 10, 12)  # segunda-feira
    dados = 'Hoje: Reunião - Filipa Quintas (14:00).'
    # Diz «sexta-feira» — dia errado para segunda.
    redigido = 'Bom dia, sexta-feira! Às 14:00 tens uma reunião.'
    valido, detalhe = redacao.validar_resposta(
        redigido, dados, data, ['Reunião - Filipa Quintas'], 900)
    assert valido is False
    assert detalhe == 'dia da semana errado'


def test_dia_da_semana_correcto_passa():
    """O dia correcto do resumo é admitido na redacção."""
    data = date(2026, 10, 12)  # segunda-feira
    dados = 'Hoje: Reunião - Filipa Quintas (14:00).'
    redigido = ('Bom dia, segunda-feira! Às 14:00 tens uma reunião com a '
                'Filipa Quintas.')
    valido, detalhe = redacao.validar_resposta(
        redigido, dados, data, ['Reunião - Filipa Quintas'], 900)
    assert (valido, detalhe) == (True, None)


def test_modo_web_usa_orcamento_curto(contexto):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm(f'Bom dia! {dados}')) as llm:
        gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO, modo='web')
    assert (llm.call_args.kwargs['prazo_total']
            == redacao.ORCAMENTO_WEB_POR_OMISSAO)
    assert (redacao.ORCAMENTO_WEB_POR_OMISSAO
            < redacao.ORCAMENTO_TASK_POR_OMISSAO)


def test_orcamento_configuravel_por_variavel_de_ambiente(contexto):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1',
                                    'RESUMO_LLM_ORCAMENTO_TASK': '5'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm(f'Bom dia! {dados}')) as llm:
        gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    assert llm.call_args.kwargs['prazo_total'] == 5.0


def test_numero_inventado_cai_no_deterministico(contexto):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm(
                             f'Bom dia! {dados} Pressão de 42 hPa.')):
        resultado = gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    assert resultado['texto'] == dados
    assert resultado['origem'] == 'deterministico'
    assert resultado['motivo'] == 'validação (número inventado (42))'


def test_resposta_demasiado_longa_cai_no_deterministico(contexto):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm('A' * 901)):
        resultado = gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    assert resultado['texto'] == dados
    assert resultado['motivo'] == 'validação (demasiado longa)'


def test_resposta_vazia_cai_no_deterministico(contexto):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm('   ')):
        resultado = gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    assert resultado['texto'] == dados
    assert resultado['motivo'] == 'validação (vazia)'

def test_todos_os_modelos_a_falhar_cai_no_deterministico(contexto):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         side_effect=ServicoIndisponivelError('sem modelos')):
        resultado = gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    assert resultado['texto'] == dados
    assert resultado['origem'] == 'deterministico'
    assert resultado['motivo'] == 'falha'


def test_timeout_cai_no_deterministico(contexto):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         side_effect=PrazoExcedidoError('prazo')):
        resultado = gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    assert resultado['texto'] == dados
    assert resultado['motivo'] == 'timeout'


@pytest.mark.parametrize('valor', ['0', 'false', 'off', 'desligado'])
def test_interruptor_desligado_nao_chama_llm(contexto, valor):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': valor}), \
            patch.object(redacao, 'chamar_llm') as llm:
        resultado = gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    llm.assert_not_called()
    assert resultado['texto'] == dados
    assert resultado['origem'] == 'deterministico'
    assert resultado['motivo'] == 'desligado'


def test_titulo_em_falta_na_saida_cai_no_deterministico(contexto):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    # Sem nenhum dos títulos dos dados: incompleto.
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm('Bom dia! Hoje: nada de novo.')):
        resultado = gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    assert resultado['texto'] == dados
    assert resultado['motivo'] == 'validação (título em falta)'


def test_titulo_reescrito_em_prosa_passa():
    """v1.8.3: o LLM pode reescrever o título; as palavras-chave bastam.

    Antes exigia-se a frase exacta («Reunião - Filipa Quintas»), pelo que uma
    redacção natural («uma reunião com a Filipa Quintas») caía no
    determinístico mesmo sendo boa. Agora sobreviver às palavras-chave chega.
    """
    data = date(2026, 10, 12)
    dados = 'Hoje: Reunião - Filipa Quintas (14:00).'
    redigido = 'Bom dia! Às 14:00 tens uma reunião com a Filipa Quintas.'
    valido, detalhe = redacao.validar_resposta(
        redigido, dados, data, ['Reunião - Filipa Quintas'], 900)
    assert (valido, detalhe) == (True, None)


def test_titulo_realmente_ausente_cai():
    """Se nenhuma palavra-chave do título aparece, é título em falta."""
    data = date(2026, 10, 12)
    dados = 'Hoje: Reunião - Filipa Quintas (14:00).'
    redigido = 'Bom dia! Hoje não tens nada marcado.'
    valido, detalhe = redacao.validar_resposta(
        redigido, dados, data, ['Reunião - Filipa Quintas'], 900)
    assert valido is False
    assert detalhe == 'título em falta'


def test_titulo_longo_condensado_passa():
    """v1.8.3: nome longo condensado pelo LLM passa (maioria das palavras-chave).

    Caso real: «Revisar o relatório financeiro do trimestre e enviar ao
    supervisor» onde o LLM reescreve verbos («rever», «enviá-lo»). Sobrevivem
    relatório/financeiro/trimestre/supervisor — 4 de 6, acima do limiar.
    """
    data = date(2026, 10, 12)
    dados = ('Tarefas\nEm atraso (09/10): Revisar o relatório financeiro '
             'do trimestre e enviar ao supervisor')
    redigido = ('Bom dia! Em atraso desde 09/10, rever o relatório '
                'financeiro do trimestre e enviá-lo ao supervisor.')
    valido, detalhe = redacao.validar_resposta(
        redigido, dados, data,
        ['Revisar o relatório financeiro do trimestre e enviar ao supervisor'],
        900)
    assert (valido, detalhe) == (True, None)


def test_tarefa_inteira_omitida_cai():
    """Uma tarefa de que não sobrevive nenhuma palavra-chave é omissão real."""
    data = date(2026, 10, 12)
    dados = ('Tarefas\nVencem hoje: Revisar o relatório financeiro\n'
             'Vencem hoje: Organizar a garagem')
    # Só fala de uma delas; a garagem desapareceu por completo.
    redigido = ('Bom dia! Revisa o relatório financeiro hoje, não te '
                'esqueças.')
    valido, detalhe = redacao.validar_resposta(
        redigido, dados, data,
        ['Revisar o relatório financeiro', 'Organizar a garagem'], 900)
    assert valido is False
    assert detalhe == 'título em falta'



def test_metalinguagem_cai_no_deterministico():
    """v1.8.3: frases de ausência/metalinguagem rejeitam a resposta.

    Versão estreita: só metalinguagem (falar dos dados/secções). Negações
    legítimas («não há chuva») continuam a passar — ver o teste seguinte.
    """
    data = date(2026, 10, 12)
    dados = 'Hoje: Reunião - Filipa Quintas (14:00).'
    frases = [
        'Bom dia! Meteorologia: sem dados disponíveis.',
        'Bom dia! A meteorologia não foi fornecida.',
        'Bom dia! Como vês na secção seguinte, nada de novo.',
        'Bom dia! Este tópico ficou de fora.',
    ]
    for redigido in frases:
        valido, detalhe = redacao.validar_resposta(
            redigido, dados, data, ['Reunião - Filipa Quintas'], 900)
        assert valido is False, redigido
        assert detalhe == 'metalinguagem', redigido


def test_negacao_legitima_passa():
    """«não há chuva» não é metalinguagem — tem de passar."""
    data = date(2026, 10, 12)
    dados = 'Meteorologia: 13 a 23 °C, sem chuva.'
    redigido = 'Bom dia! Entre 13 e 23 °C e não há chuva.'
    valido, detalhe = redacao.validar_resposta(redigido, dados, data, [], 900)
    assert (valido, detalhe) == (True, None)


def test_titulo_com_palavra_da_denylist_e_isento():
    """Um título legítimo «Limpar base de dados» não dispara metalinguagem."""
    data = date(2026, 10, 12)
    dados = 'Tarefas\nVencem hoje: Limpar base de dados.'
    redigido = 'Bom dia! Hoje tens de limpar a base de dados.'
    valido, detalhe = redacao.validar_resposta(
        redigido, dados, data, ['Limpar base de dados'], 900)
    assert (valido, detalhe) == (True, None)


def test_titulo_com_sec_ou_topico_e_isento():
    """Título com «secção»/«tópico» é dado do utilizador — não é metalinguagem."""
    data = date(2026, 10, 12)
    dados = 'Tarefas\nVencem hoje: Rever secção de código.'
    redigido = 'Bom dia! Tens de rever a secção de código hoje.'
    valido, detalhe = redacao.validar_resposta(
        redigido, dados, data, ['Rever secção de código'], 900)
    assert (valido, detalhe) == (True, None)


def test_titulo_como_instrucao_e_dado_nao_instrucao(contexto):
    """O título «Relatório <A&B> *teste*» é dado: passa o prompt e a validação."""
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    assert 'Relatório <A&B> *teste*' in dados  # o '*' e o '<' não rejeitam
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm(f'Olá! {dados}')):
        resultado = gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    assert resultado['origem'] == 'modelo-teste'


def test_extrair_numeros_normaliza_virgula_e_ponto():
    assert redacao.extrair_numeros('1,978 €/L e 1.978 °C às 07:00') == {
        1.978, 7.0, 0.0}


def test_numeros_pt_datas_e_dias_da_semana_aceites():
    """Formato PT (vírgula, intervalos, datas) e dia/mês/ano do resumo."""
    data = date(2026, 10, 13)  # terça-feira
    dados = ('Combustíveis\n'
             'Gasóleo simples: 1,978 €/L — PA X (Braga)\n'
             'Última recolha: 08/10/2026 12:34\n\n'
             'Meteorologia: 13–27 °C, Nevoeiro')
    # Todos os números dos dados sobrevivem (recolha incluída — completude).
    redigido = ('Boa tarde! Terça, 13 de outubro. O gasóleo ficou em 1.978 €/L; '
                'última recolha a 08/10/2026 12:34; temperaturas entre 13 e '
                '27 °C.')
    valido, detalhe = redacao.validar_resposta(redigido, dados, data, [], 900)
    assert (valido, detalhe) == (True, None)

    # Número novo (28) continua a cair no determinístico.
    valido, detalhe = redacao.validar_resposta(
        'Amanhã faz 28 °C.', dados, data, [], 900)
    assert valido is False
    assert 'número inventado' in detalhe


def test_completude_numeros_meteorologia_nao_pode_desaparecer():
    """O LLM não pode largar secções: os números dos dados têm de ficar."""
    data = date(2026, 10, 13)
    dados = ('Meteorologia: 13–27 °C, Nevoeiro\n\n'
             'Amanhã\n14:00 — Reunião X')
    # Só a reunião — a meteorologia (13, 27) desapareceu.
    valido, detalhe = redacao.validar_resposta(
        'Bom dia! Amanhã às 14:00 tens Reunião X.', dados, data,
        ['Reunião X'], 900)
    assert valido is False
    assert detalhe.startswith('número em falta')


def test_completude_formas_alternativas_contam():
    """«8 de outubro» ≡ «08/10» e «14h» ≡ «14:00» na completude."""
    data = date(2026, 10, 13)
    dados = ('Tarefas\nEm atraso (08/10): Ligar ao banco\n\n'
             'Amanhã\n14:00 — Reunião X')
    redigido = ('Bom dia! A Reunião X é às 14h; o prazo era 8 de outubro: '
                'Ligar ao banco.')
    valido, detalhe = redacao.validar_resposta(
        redigido, dados, data, ['Ligar ao banco', 'Reunião X'], 900)
    assert (valido, detalhe) == (True, None)


def test_data_do_resumo_aceita_dia_fora_dos_dados(contexto):
    """«sexta-feira, 9 de outubro» é admitido mesmo sem estar nos dados."""
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm(
                             f'Olá, sexta-feira, 9 de outubro! {dados}')):
        resultado = gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    assert resultado['origem'] == 'modelo-teste'


def test_resumo_sem_seccoes_nao_chama_llm(contexto):
    app, user_id = contexto
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm') as llm:
        resultado = gerar_resumo_diario(
            user_id, date(2026, 10, 7), opcoes=SEM_METEO)  # sem dados
    llm.assert_not_called()
    assert resultado['texto'] == ''
    assert resultado['origem'] == 'deterministico'
    assert resultado['motivo'] == 'sem secções'


def test_texto_llm_escapado_no_envio_telegram(contexto):
    from app.notifications.channels.telegram import TelegramChannel

    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm(f'Olá! {dados}')):
        resultado = gerar_resumo_diario(user_id, HOJE, opcoes=SEM_METEO)
    assert resultado['origem'] == 'modelo-teste'

    class Resposta:
        status_code = 200

    class Utilizador:
        telegram_chat_id = '12345'

    with patch('app.notifications.channels.telegram.requests.post',
               return_value=Resposta()) as pedido:
        enviado = TelegramChannel('token').enviar(
            Utilizador(), 'Resumo Diário', resultado['texto'], parse_mode='HTML')
    assert enviado is True
    payload = pedido.call_args.kwargs['json']
    assert payload['parse_mode'] == 'HTML'
    assert '&lt;A&amp;B&gt;' in payload['text']  # <A&B> escapado pelo canal
    assert '*teste*' in payload['text']


def test_origem_llm_indicada_na_simulacao_e_no_log(contexto, capsys, caplog):
    app, user_id = contexto
    dados = _texto_deterministico(app, user_id)
    caplog.set_level(logging.INFO)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '1'}), \
            patch.object(services.meteorologia_services, 'obter_previsao',
                         return_value={'diaria': []}), \
            patch.object(redacao, 'chamar_llm',
                         return_value=_resposta_llm(f'Olá! {dados}')), \
            patch.object(services.notification_service, 'send') as enviar:
        services.enviar_resumos_diarios(HOJE, simular=True)
    saida = capsys.readouterr().out
    assert '[fase4] (origem: modelo-teste)' in saida
    assert 'modelo-teste' in caplog.text
    assert 'Texto redigido por LLM' in caplog.text
    enviar.assert_not_called()


def test_origem_deterministica_indicada_na_simulacao_e_no_log(
        contexto, capsys, caplog):
    app, user_id = contexto
    caplog.set_level(logging.INFO)
    with app.app_context(), \
            patch.dict(os.environ, {'RESUMO_LLM_ATIVO': '0'}), \
            patch.object(services.meteorologia_services, 'obter_previsao',
                         return_value={'diaria': []}), \
            patch.object(redacao, 'chamar_llm') as llm, \
            patch.object(services.notification_service, 'send') as enviar:
        services.enviar_resumos_diarios(HOJE, simular=True)
    llm.assert_not_called()
    saida = capsys.readouterr().out
    assert '[fase4] (origem: determinístico — desligado)' in saida
    assert 'determinístico (desligado)' in caplog.text
    enviar.assert_not_called()
