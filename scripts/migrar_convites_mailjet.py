"""
migrar_convites_mailjet.py — Registo do estado de entrega dos emails de convite.

Adiciona à tabela `convites` (SQLite — o `db.create_all()` não faz ALTER TABLE):

    mailjet_message_id  ID da mensagem no Mailjet (permite verificar a entrega)
    email_estado        último estado conhecido (aceite, sent, delivered, ...)
    email_verificado_em quando se consultou o estado pela última vez

Executar UMA VEZ, antes de fazer deploy do novo código:
    python scripts/migrar_convites_mailjet.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from sqlalchemy import inspect, text

from app import create_app, db

# Consola Windows com pipe (ex.: PowerShell/redirecionamento) usa cp1252 e
# rebenta ao imprimir '✓' — forçar UTF-8 (mesmo truque de verificar_mailjet.py)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

app = create_app()

with app.app_context():
    conn = db.engine.connect()
    inspector = inspect(db.engine)
    colunas = [c['name'] for c in inspector.get_columns('convites')]
    print(f'Colunas actuais: {colunas}')

    colunas_novas = (
        ('mailjet_message_id', 'VARCHAR(20)'),
        ('email_estado', 'VARCHAR(20)'),
        ('email_verificado_em', 'DATETIME'),
    )
    for nome, tipo in colunas_novas:
        if nome not in colunas:
            conn.execute(text(f'ALTER TABLE convites ADD COLUMN {nome} {tipo}'))
            conn.commit()
            print(f'✓ Coluna {nome} adicionada.')
        else:
            print(f'— {nome} já existe, ignorado.')

    conn.close()
    print('\nMigração concluída.')