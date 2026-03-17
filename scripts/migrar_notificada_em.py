"""
migrar_notificada_em.py — Migração da BD do módulo Tarefas.

Substitui o campo booleano `notificada` pelo campo de data `notificada_em`.
Preserva o estado actual: tarefas marcadas como notificadas ficam com
notificada_em = ontem (para voltarem a ser notificadas na próxima execução).

Executar UMA VEZ, antes de fazer deploy do novo código:
    python scripts/migrar_notificada_em.py
"""

import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from app import create_app, db

app = create_app()

with app.app_context():
    conn = db.engine.connect()

    # Verificar colunas actuais
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    colunas   = [c['name'] for c in inspector.get_columns('tarefas')]

    print(f'Colunas actuais: {colunas}')

    # 1 — Adicionar notificada_em (DATE, nullable)
    if 'notificada_em' not in colunas:
        conn.execute(text('ALTER TABLE tarefas ADD COLUMN notificada_em DATE'))
        conn.commit()
        print('✓ Coluna notificada_em adicionada.')
    else:
        print('— notificada_em já existe, ignorado.')

    # 2 — Migrar dados: se notificada=1, definir notificada_em = ontem
    #     (ontem para que amanhã volte a notificar caso ainda esteja em atraso)
    if 'notificada' in colunas:
        ontem = (date.today() - timedelta(days=1)).isoformat()
        resultado = conn.execute(
            text(f"UPDATE tarefas SET notificada_em = '{ontem}' WHERE notificada = 1 AND notificada_em IS NULL")
        )
        conn.commit()
        print(f'✓ {resultado.rowcount} tarefa(s) migrada(s) com notificada_em = {ontem}.')

        # 3 — Remover coluna antiga (SQLite não suporta DROP COLUMN antes da versão 3.35)
        #     Verificar versão do SQLite antes de tentar
        import sqlite3
        versao = tuple(int(x) for x in sqlite3.sqlite_version.split('.'))
        if versao >= (3, 35, 0):
            conn.execute(text('ALTER TABLE tarefas DROP COLUMN notificada'))
            conn.commit()
            print('✓ Coluna notificada removida.')
        else:
            print(f'! SQLite {sqlite3.sqlite_version} — DROP COLUMN não suportado.')
            print('  A coluna notificada fica na BD mas é ignorada pelo código.')
            print('  Podes removê-la manualmente ou deixar ficar (não causa erros).')
    else:
        print('— Coluna notificada não existe, nada a migrar.')

    conn.close()
    print('\nMigração concluída.')
