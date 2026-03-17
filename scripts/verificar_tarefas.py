#!/usr/bin/env python
"""
verificar_tarefas.py — Scheduled task do PythonAnywhere
Corre 1x/dia (sugerido: 08:00) e notifica utilizadores sobre tarefas em atraso.

Configuração no PA:
    python /home/felipejn/pipe-app/scripts/verificar_tarefas.py
"""

import sys
import os
from datetime import date

# Garantir que o projecto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from app import create_app, db
from app.tarefas.models import Tarefa
from app.auth.models import User
from app.notifications import notification_service

app = create_app()

with app.app_context():
    hoje = date.today()

    # Tarefas pendentes, com data limite ultrapassada, ainda não notificadas
    tarefas_atraso = Tarefa.query.filter(
        Tarefa.concluida == False,  # noqa: E712
        Tarefa.data_limite < hoje,
        Tarefa.notificada == False,  # noqa: E712
        Tarefa.data_limite != None,  # noqa: E711
    ).all()

    if not tarefas_atraso:
        print(f"[{hoje}] Sem tarefas em atraso para notificar.")
        sys.exit(0)

    # Agrupar por utilizador
    por_utilizador = {}
    for t in tarefas_atraso:
        por_utilizador.setdefault(t.user_id, []).append(t)

    notificadas = 0
    for user_id, lista_tarefas in por_utilizador.items():
        user = User.query.get(user_id)
        if not user or not user.activo:
            continue

        n = len(lista_tarefas)
        itens = '\n'.join(
            f"• {t.texto} (limite: {t.data_limite.strftime('%d/%m/%Y')})"
            for t in lista_tarefas
        )

        subject = f"⚠ {n} tarefa{'s' if n > 1 else ''} em atraso no PIPE"
        body = (
            f"Olá {user.username},\n\n"
            f"Tens {n} tarefa{'s' if n > 1 else ''} com prazo ultrapassado:\n\n"
            f"{itens}\n\n"
            f"Acede ao PIPE para as concluir ou actualizar."
        )

        resultado = notification_service.send(
            user=user,
            type='tarefa_atraso',
            subject=subject,
            body=body,
            data={'total_atraso': n},
        )
        print(f"[{hoje}] {user.username}: {n} tarefa(s) notificadas → {resultado}")

        # Marcar como notificadas para não repetir
        for t in lista_tarefas:
            t.notificada = True
        db.session.commit()
        notificadas += n

    print(f"[{hoje}] Total notificado: {notificadas} tarefa(s) em {len(por_utilizador)} utilizador(es).")
