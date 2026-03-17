"""
pipe_tasks.py — Única scheduled task do PIPE no PythonAnywhere.

Corre 1x por dia. Cada módulo é independente — um erro não interrompe os restantes.

Configuração no PA:
  Comando: python /home/felipejn/pipe-app/scripts/pipe_tasks.py
  Hora:    23:00

Módulos activos:
  1. Euromilhões — verifica resultados às terças e sextas
  2. Tarefas     — notifica tarefas em atraso (diariamente, enquanto persistirem)
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from app import create_app, db

app = create_app()


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

def tarefa_tarefas(hoje):
    print(f'  [Tarefas] A verificar prazos...')

    from app.tarefas.models import Tarefa
    from app.auth.models import User
    from app.notifications import notification_service

    # Tarefas em atraso que ainda não foram notificadas HOJE
    em_atraso = Tarefa.query.filter(
        Tarefa.concluida == False,           # noqa: E712
        Tarefa.data_limite != None,          # noqa: E711
        Tarefa.data_limite < hoje,
        db.or_(
            Tarefa.notificada_em == None,    # nunca notificada   # noqa: E711
            Tarefa.notificada_em < hoje,     # última notificação foi antes de hoje
        ),
    ).all()

    if not em_atraso:
        print(f'  [Tarefas] Sem tarefas em atraso para notificar hoje.')
        return

    # Agrupar por utilizador
    por_user = {}
    for t in em_atraso:
        por_user.setdefault(t.user_id, []).append(t)

    notificados = 0
    for user_id, lista in por_user.items():
        user = User.query.get(user_id)
        if not user or not user.activo:
            continue

        n     = len(lista)
        itens = '\n'.join(
            f'• {t.texto} (limite: {t.data_limite.strftime("%d/%m/%Y")}, '
            f'{(hoje - t.data_limite).days} dia(s) de atraso)'
            for t in lista
        )
        subject = f'⚠ {n} tarefa{"s" if n > 1 else ""} em atraso no PIPE'
        body    = (
            f'Olá {user.username},\n\n'
            f'Tens {n} tarefa{"s" if n > 1 else ""} com prazo ultrapassado:\n\n'
            f'{itens}\n\n'
            f'Acede ao PIPE para as concluir ou actualizar o prazo.'
        )

        res = notification_service.send(
            user=user, type='tarefa_atraso',
            subject=subject, body=body, data={'total_atraso': n})
        print(f'  [Tarefas] {user.username}: {n} tarefa(s) — telegram={res.get("telegram")}  email={res.get("email")}')

        # Marcar com a data de hoje — amanhã, se ainda estiverem em atraso, volta a notificar
        for t in lista:
            t.notificada_em = hoje
        db.session.commit()
        notificados += n

    print(f'  [Tarefas] {notificados} tarefa(s) notificada(s) em {len(por_user)} utilizador(es).')


# ══════════════════════════════════════════════════════════════════════════════
# ADICIONAR NOVOS MÓDULOS AQUI
# ══════════════════════════════════════════════════════════════════════════════

TAREFAS = [
    tarefa_euromilhoes,
    tarefa_tarefas,
]

if __name__ == '__main__':
    hoje = date.today()
    print(f'╔══ PIPE Tasks — {hoje} ══╗')
    with app.app_context():
        for tarefa in TAREFAS:
            print(f'┌─ {tarefa.__name__}')
            try:
                tarefa(hoje)
            except Exception as e:
                print(f'  [{tarefa.__name__}] ERRO: {e}')
                import traceback
                traceback.print_exc()
            print(f'└─ concluído')
    print(f'╚══ Fim ══╝')
