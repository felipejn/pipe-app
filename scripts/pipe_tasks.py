"""
pipe_tasks.py — Única scheduled task do PIPE no PythonAnywhere.

Corre 1x por dia. Cada módulo é independente — um erro não interrompe os restantes.

Configuração no PA:
  Comando: python /home/felipejn/pipe-app/scripts/pipe_tasks.py
  Hora:    07:00

Módulos activos:
  Euromilhões — verifica resultados às terças e sextas
  Combustíveis → Resumo Diário → Tarefas → Calendário
"""

import sys
import os
import argparse
import logging
from datetime import date, datetime, timedelta

# Consola Windows (cp1252) não suporta os caracteres de caixa ═/╔/╗/╚/╝
# nem emojis — força UTF-8 com substituição segura para não rebentar.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 1 — Euromilhões
# ══════════════════════════════════════════════════════════════════════════════

def tarefa_euromilhoes(hoje):
    if hoje.weekday() not in (1, 4):
        print(f'  [Euromilhões] Não é dia de sorteio — ignorado.')
        return

    print(f'  [Euromilhões] Dia de sorteio — a verificar...')

    from app.auth.models import User
    from app.euromilhoes.models import Jogo
    from app.euromilhoes import api as euro_api
    from app.notifications import notification_service

    def formatar_premio(p):
        if p == 0:         return '0 €'
        if p >= 1_000_000: return f'{p / 1_000_000:.1f}M €'
        if p >= 1_000:     return f'{p / 1_000:.0f}K €'
        return f'{p} €'

    def construir_mensagem(sorteio, resultados):
        nums  = '  '.join(str(n).zfill(2) for n in sorteio.get('numbers', []))
        ests  = '  '.join(str(e).zfill(2) for e in sorteio.get('stars', []))
        linhas = [f'Sorteio de {sorteio["date"]}', f'Números: {nums}', f'Estrelas: {ests}', '']
        total = 0
        for r in resultados:
            n_fmt = '  '.join(str(n).zfill(2) for n in r['numeros'])
            e_fmt = '  '.join(str(e).zfill(2) for e in r['estrelas'])
            linhas += [f'Jogo: {n_fmt}  ★ {e_fmt}',
                       f'Acertos: {r["n_ac"]} números  {r["e_ac"]} estrelas  — {formatar_premio(r["premio"])}', '']
            total += r['premio']
        linhas.append(f'Total ganho: {formatar_premio(total)}' if total > 0
                      else 'Desta vez não foi. Boa sorte no próximo sorteio!')
        return '\n'.join(linhas)

    try:
        todos = euro_api.obter_todos_sorteios()
    except Exception as e:
        print(f'  [Euromilhões] Erro na API: {e}')
        return

    hoje_str = hoje.strftime('%Y-%m-%d')
    sorteio  = next((s for s in todos if s['date'] == hoje_str), None)
    if not sorteio:
        print(f'  [Euromilhões] Sorteio de {hoje_str} ainda não disponível.')
        return

    print(f'  [Euromilhões] Sorteio: {sorteio["numbers"]} | {sorteio["stars"]}')
    notificados = 0

    for user in User.query.filter_by(activo=True).all():
        prefs = user.notificacao_prefs
        if not prefs or not prefs.notificar_resultados:
            continue
        if not prefs.telegram_activo and not prefs.email_activo:
            continue

        jogos = Jogo.query.filter_by(user_id=user.id, data_sorteio=hoje).all()
        if not jogos:
            continue

        resultados = []
        for j in jogos:
            n_ac, e_ac, premio = euro_api.verificar_acertos(
                j.get_numeros(), j.get_estrelas(), sorteio)
            resultados.append(dict(numeros=j.get_numeros(), estrelas=j.get_estrelas(),
                                   n_ac=n_ac, e_ac=e_ac, premio=premio))

        corpo = construir_mensagem(sorteio, resultados)
        res   = notification_service.send(
            user=user, type='resultado_euromilhoes',
            subject=f'Resultados Euromilhões — {hoje_str}', body=corpo)
        print(f'  [Euromilhões] {user.username}: telegram={res.get("telegram")}  email={res.get("email")}')
        notificados += 1

    print(f'  [Euromilhões] {notificados} utilizador(es) notificado(s).')


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 2 — Tarefas
# Notificações DIÁRIAS: envia todos os dias enquanto a tarefa estiver em atraso.
# Usa o campo notificada_em (Date) — se for diferente de hoje, volta a notificar.
# ══════════════════════════════════════════════════════════════════════════════

def tarefa_tarefas(hoje, resumo_recebido=None):
    print(f'  [Tarefas] A verificar prazos...')

    from app.tarefas.models import Tarefa
    from app.auth.models import User
    from app.notifications import notification_service

    # Tarefas com prazo para HOJE ou já em atraso, não notificadas ainda hoje
    candidatas = Tarefa.query.filter(
        Tarefa.concluida == False,           # noqa: E712
        Tarefa.data_limite != None,          # noqa: E711
        Tarefa.data_limite <= hoje,          # vence hoje OU prazo ultrapassado
        db.or_(
            Tarefa.notificada_em == None,    # nunca notificada   # noqa: E711
            Tarefa.notificada_em < hoje,     # última notificação foi antes de hoje
        ),
    ).all()

    if not candidatas:
        print(f'  [Tarefas] Sem tarefas para notificar hoje.')
        return

    # Agrupar por utilizador
    por_user = {}
    for t in candidatas:
        por_user.setdefault(t.user_id, []).append(t)

    notificados = 0
    for user_id, lista in por_user.items():
        if resumo_recebido and user_id in resumo_recebido:
            continue
        user = User.query.get(user_id)
        if not user or not user.activo:
            continue

        hoje_lista  = [t for t in lista if t.data_limite == hoje]
        atraso_lista = [t for t in lista if t.data_limite < hoje]

        # Secções da mensagem (cada uma só aparece se tiver itens)
        partes = []
        if hoje_lista:
            itens = '\n'.join(
                f'• {t.texto} (limite: {t.data_limite.strftime("%d/%m/%Y")})'
                for t in hoje_lista
            )
            partes.append(f'⏰ Vencem hoje ({len(hoje_lista)}):\n{itens}')
        if atraso_lista:
            itens = '\n'.join(
                f'• {t.texto} (limite: {t.data_limite.strftime("%d/%m/%Y")}, '
                f'{(hoje - t.data_limite).days} dia(s) de atraso)'
                for t in atraso_lista
            )
            partes.append(f'⚠ Em atraso ({len(atraso_lista)}):\n{itens}')

        n_hoje, n_atraso = len(hoje_lista), len(atraso_lista)
        if n_hoje and n_atraso:
            subject = (f'⏰ {n_hoje} tarefa{"s" if n_hoje > 1 else ""} com prazo hoje '
                       f'e {n_atraso} em atraso no PIPE')
        elif n_hoje:
            subject = f'⏰ {n_hoje} tarefa{"s" if n_hoje > 1 else ""} com prazo hoje no PIPE'
        else:
            subject = f'⚠ {n_atraso} tarefa{"s" if n_atraso > 1 else ""} em atraso no PIPE'

        body = (
            f'Olá {user.username},\n\n'
            + '\n\n'.join(partes)
            + '\n\nAcede ao PIPE para concluir ou actualizar os prazos.'
        )

        try:
            res = notification_service.send(
                user=user, type='tarefa_lembrete',
                subject=subject, body=body,
                data={'total_hoje': n_hoje, 'total_atraso': n_atraso})
        except Exception:
            db.session.rollback()
            logging.exception('[Tarefas] Falha ao notificar %s', user.username)
            continue
        print(f'  [Tarefas] {user.username}: hoje={n_hoje} atraso={n_atraso} '
              f'— telegram={res.get("telegram")}  email={res.get("email")}')

        # Marcar com a data de hoje — amanhã, se ainda faltar, volta a notificar
        try:
            for t in lista:
                t.notificada_em = hoje
            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.exception('[Tarefas] Falha ao registar avisos de %s', user.username)
            continue
        notificados += len(lista)

    print(f'  [Tarefas] {notificados} tarefa(s) notificada(s) em {len(por_user)} utilizador(es).')


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 3 — Combustíveis
# ══════════════════════════════════════════════════════════════════════════════

def tarefa_combustiveis(hoje):
    print(f'  [Combustíveis] A verificar necessidade de atualização...')

    from app.combustiveis import services

    resultado = services.atualizar_precos_se_necessario(forcar=False)

    if not resultado['executado']:
        motivo = ('já actualizado hoje' if hoje.weekday() == 1 else 'hoje não é terça-feira')
        print(f'  [Combustíveis] Actualização automática ignorada — {motivo}.')
        return

    if resultado['sucesso']:
        print(f'  [Combustíveis] {resultado["postos_verificados"]} posto(s) verificado(s), '
              f'{resultado["precos_novos"]} registo(s) novo(s); total na BD: {resultado["postos_na_bd"]}.')
    else:
        print(f'  [Combustíveis] Concluído com erros ({resultado["postos_verificados"]} postos '
              f'verificados): {resultado["erro"]}')


# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 4 — Calendário
# Lembretes de eventos: no dia ANTERIOR («Amanhã») e no PRÓPRIO DIA («Hoje»).
# O campo único notificado_em cobre os dois avisos: no dia D−1 grava D−1; no
# dia D (do evento), como notificado_em < D, volta a notificar e grava D.
# Eventos já iniciados à hora da task (não dia inteiro) são ignorados.
# ══════════════════════════════════════════════════════════════════════════════

def tarefa_calendario(hoje, resumo_recebido=None):
    print(f'  [Calendário] A verificar eventos...')

    from app.calendario.models import Evento
    from app.auth.models import User
    from app.notifications import notification_service

    amanha = hoje + timedelta(days=1)
    agora = datetime.now()

    eventos = Evento.query.filter(
        Evento.notificar == True,                      # noqa: E712
        db.or_(
            Evento.notificado_em == None,              # nunca notificado  # noqa: E711
            Evento.notificado_em < hoje,               # notificado antes de hoje
        ),
        db.or_(
            db.func.date(Evento.data_inicio) == amanha,        # → «Amanhã»
            db.and_(
                db.func.date(Evento.data_inicio) == hoje,      # → «Hoje»
                db.or_(
                    Evento.dia_inteiro == True,                # noqa: E712
                    Evento.data_inicio > agora,                # ainda não começou
                ),
            ),
        ),
    ).order_by(Evento.data_inicio).all()

    if not eventos:
        print(f'  [Calendário] Sem eventos para notificar.')
        return

    # Agrupar por utilizador
    por_user = {}
    for e in eventos:
        por_user.setdefault(e.user_id, []).append(e)

    def _linha(e):
        quando = 'dia inteiro' if e.dia_inteiro else f'às {e.data_inicio.strftime("%H:%M")}'
        local = f' — {e.localizacao}' if e.localizacao else ''
        return f'• {e.titulo} ({quando}){local}'

    notificados = 0
    for user_id, lista in por_user.items():
        if resumo_recebido and user_id in resumo_recebido:
            continue
        user = User.query.get(user_id)
        if not user or not user.activo:
            continue

        amanha_lista = [e for e in lista if e.data_inicio.date() == amanha]
        hoje_lista = [e for e in lista if e.data_inicio.date() == hoje]

        partes = []
        if amanha_lista:
            itens = '\n'.join(_linha(e) for e in amanha_lista)
            partes.append(f'📅 Amanhã ({len(amanha_lista)}):\n{itens}')
        if hoje_lista:
            itens = '\n'.join(_linha(e) for e in hoje_lista)
            partes.append(f'📅 Hoje ({len(hoje_lista)}):\n{itens}')

        n_a, n_h = len(amanha_lista), len(hoje_lista)
        if n_a and n_h:
            subject = f'📅 {n_a} evento{"s" if n_a > 1 else ""} amanhã e {n_h} hoje no PIPE'
        elif n_a:
            subject = f'📅 {n_a} evento{"s" if n_a > 1 else ""} amanhã no PIPE'
        else:
            subject = f'📅 {n_h} evento{"s" if n_h > 1 else ""} hoje no PIPE'

        body = (
            f'Olá {user.username},\n\n'
            + '\n\n'.join(partes)
            + '\n\nAcede ao PIPE ao Calendário para ver os detalhes.'
        )

        try:
            res = notification_service.send(
                user=user, type='evento_lembrete',
                subject=subject, body=body,
                data={'total_amanha': n_a, 'total_hoje': n_h})
        except Exception:
            db.session.rollback()
            logging.exception('[Calendário] Falha ao notificar %s', user.username)
            continue
        print(f'  [Calendário] {user.username}: amanhã={n_a} hoje={n_h} '
              f'— telegram={res.get("telegram")}  email={res.get("email")}')

        # Um único campo cobre os dois avisos — amanhã passa a «hoje» e notifica
        try:
            for e in lista:
                e.notificado_em = hoje
            db.session.commit()
        except Exception:
            db.session.rollback()
            logging.exception('[Calendário] Falha ao registar avisos de %s', user.username)
            continue
        notificados += len(lista)

    print(f'  [Calendário] {notificados} evento(s) notificado(s) em {len(por_user)} utilizador(es).')


# ══════════════════════════════════════════════════════════════════════════════
# ADICIONAR NOVOS MÓDULOS AQUI
# ══════════════════════════════════════════════════════════════════════════════

def executar_tarefas_diarias(hoje, apenas_resumo=False, simular_resumo=False):
    """Executa módulos isoladamente e devolve quem recebeu o resumo hoje."""
    from app.resumo_diario.services import enviar_resumos_diarios
    if apenas_resumo or simular_resumo:
        return enviar_resumos_diarios(hoje, simular=simular_resumo)

    # O sorteio mantém-se fora da sequência de combustíveis/resumo/avisos.
    for tarefa in (tarefa_euromilhoes, tarefa_combustiveis):
        try:
            tarefa(hoje)
        except Exception:
            logging.exception('Falha na tarefa agendada %s',
                              getattr(tarefa, '__name__', repr(tarefa)))
    try:
        recebidos = enviar_resumos_diarios(hoje)
    except Exception:
        logging.exception('Falha na tarefa agendada Resumo Diário')
        recebidos = set()
    for tarefa in (tarefa_tarefas, tarefa_calendario):
        try:
            tarefa(hoje, recebidos)
        except Exception:
            logging.exception('Falha na tarefa agendada %s',
                              getattr(tarefa, '__name__', repr(tarefa)))
    return recebidos

def validar_argumentos(simular_resumo, data):
    """Valida a combinação dos argumentos da linha de comandos.

    A regra de segurança: ``--data`` só é aceite em simulação, nunca num
    envio real, para o resumo não sair com a data errada nem gravar
    ``ultimo_envio`` com ela.

    Args:
        simular_resumo: valor de ``--simular-resumo``.
        data: valor de ``--data`` (string ISO ``AAAA-MM-DD`` ou None).

    Returns:
        datetime.date quando ``--data`` foi indicado; None caso contrário.

    Raises:
        ValueError: ``--data`` sem ``--simular-resumo`` ou data inválida.
    """
    if data and not simular_resumo:
        raise ValueError('--data só é permitido com --simular-resumo '
                         '(nunca num envio real).')
    if not data:
        return None
    try:
        return date.fromisoformat(data)
    except ValueError:
        raise ValueError(
            '--data tem de ser AAAA-MM-DD (ex.: 2026-10-13).') from None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--so-resumo', action='store_true')
    parser.add_argument('--simular-resumo', action='store_true')
    parser.add_argument('--data', default=None,
                        help='Força a data (AAAA-MM-DD) em vez da data local. '
                             'Só é aceite com --simular-resumo.')
    argumentos = parser.parse_args()
    try:
        data_forcada = validar_argumentos(argumentos.simular_resumo,
                                          argumentos.data)
    except ValueError as erro:
        parser.error(str(erro))
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    app = create_app()
    from app.resumo_diario.services import obter_data_local
    hoje = data_forcada or obter_data_local()
    print(f'╔══ PIPE Tasks — {hoje} ══╗')
    with app.app_context():
        executar_tarefas_diarias(hoje, apenas_resumo=argumentos.so_resumo,
                                 simular_resumo=argumentos.simular_resumo)
    print(f'╚══ Fim ══╝')
