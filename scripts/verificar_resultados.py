"""
Scheduled task — verificar resultados Euromilhões e enviar notificações.

Corre 1x por dia no PythonAnywhere.
Só actua às terças-feiras e sextas-feiras (dias de sorteio).

Configurar no PA em:
  Dashboard → Tasks → Add a new scheduled task
  Comando: python /home/<username>/pipe-app/scripts/verificar_resultados.py
  Hora: 23:00 (garante que o sorteio já foi publicado na API)
"""

import sys
import os
from datetime import date

# Adiciona a raiz do projecto ao path para os imports Flask funcionarem
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.auth.models import User
from app.euromilhoes.models import Jogo
from app.euromilhoes import api as euro_api
from app.notifications import notification_service
from app.notifications.models import UserNotificationPreferences


def formatar_numeros(numeros, estrelas):
    """Formata números e estrelas para apresentação na mensagem."""
    nums = '  '.join(str(n).zfill(2) for n in numeros)
    ests = '  '.join(str(e).zfill(2) for e in estrelas)
    return nums, ests


def formatar_premio(premio):
    """Formata valor do prémio em euros."""
    if premio == 0:
        return '0 €'
    if premio >= 1_000_000:
        return f'{premio / 1_000_000:.1f}M €'
    if premio >= 1_000:
        return f'{premio / 1_000:.0f}K €'
    return f'{premio} €'


def construir_mensagem(sorteio, resultados_jogos):
    """Constrói o corpo da mensagem de notificação."""
    data_str = sorteio['date']
    nums_sorteio = '  '.join(str(n).zfill(2) for n in sorteio.get('numbers', []))
    ests_sorteio = '  '.join(str(e).zfill(2) for e in sorteio.get('stars', []))

    linhas = [
        f'Sorteio de {data_str}',
        f'Números: {nums_sorteio}',
        f'Estrelas: {ests_sorteio}',
        '',
    ]

    total_ganho = 0

    for res in resultados_jogos:
        nums_jogo, ests_jogo = formatar_numeros(
            res['numeros'], res['estrelas']
        )
        n_ac = res['n_acertos']
        e_ac = res['e_acertos']
        premio = res['premio']
        total_ganho += premio

        linhas.append(f'Jogo: {nums_jogo}  ★ {ests_jogo}')
        linhas.append(f'Acertos: {n_ac} números  {e_ac} estrelas  — {formatar_premio(premio)}')
        linhas.append('')

    if total_ganho > 0:
        linhas.append(f'Total ganho: {formatar_premio(total_ganho)}')
    else:
        linhas.append('Desta vez não foi. Boa sorte no próximo sorteio!')

    return '\n'.join(linhas)


def verificar_e_notificar():
    hoje = date.today()

    # Só actua em dias de sorteio (terça=1, sexta=4)
    if hoje.weekday() not in (1, 4):
        print(f'[{hoje}] Não é dia de sorteio. A sair.')
        return

    print(f'[{hoje}] Dia de sorteio — a verificar resultados...')

    # Obter sorteios da API
    try:
        todos = euro_api.obter_todos_sorteios()
    except Exception as e:
        print(f'Erro ao contactar a API: {e}')
        return

    if not todos:
        print('API não devolveu sorteios.')
        return

    # Procurar sorteio de hoje
    hoje_str = hoje.strftime('%Y-%m-%d')
    sorteio_hoje = next((s for s in todos if s['date'] == hoje_str), None)

    if not sorteio_hoje:
        print(f'Sorteio de {hoje_str} ainda não disponível na API.')
        return

    print(f'Sorteio encontrado: {sorteio_hoje["numbers"]} | {sorteio_hoje["stars"]}')

    # Obter todos os utilizadores com jogos para hoje
    utilizadores = User.query.filter_by(activo=True).all()
    notificados = 0

    for utilizador in utilizadores:
        # Verificar se tem notificações activas
        prefs = utilizador.notificacao_prefs
        if not prefs:
            continue
        if not prefs.notificar_resultados:
            continue
        if not prefs.telegram_activo and not prefs.email_activo:
            continue

        # Jogos deste utilizador para hoje
        jogos = Jogo.query.filter_by(
            user_id=utilizador.id,
            data_sorteio=hoje,
        ).all()

        if not jogos:
            continue

        # Calcular acertos para cada jogo
        resultados_jogos = []
        for jogo in jogos:
            n_ac, e_ac, premio = euro_api.verificar_acertos(
                jogo.get_numeros(),
                jogo.get_estrelas(),
                sorteio_hoje,
            )
            resultados_jogos.append({
                'numeros': jogo.get_numeros(),
                'estrelas': jogo.get_estrelas(),
                'n_acertos': n_ac,
                'e_acertos': e_ac,
                'premio': premio,
            })

        # Construir e enviar notificação
        corpo = construir_mensagem(sorteio_hoje, resultados_jogos)
        resultado = notification_service.send(
            user=utilizador,
            type='resultado_euromilhoes',
            subject=f'Resultados Euromilhões — {hoje_str}',
            body=corpo,
        )

        print(f'  {utilizador.username}: telegram={resultado.get("telegram")}  email={resultado.get("email")}')
        notificados += 1

    print(f'Concluído. {notificados} utilizador(es) notificado(s).')


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_e_notificar()
