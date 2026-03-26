"""Adiciona coluna is_admin à tabela utilizadores se não existir."""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'pipe.db')

if not os.path.exists(db_path):
    print(f'Base de dados não encontrada: {db_path}')
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verificar se a coluna já existe
cursor.execute("PRAGMA table_info(utilizadores)")
colunas = [col[1] for col in cursor.fetchall()]

if 'is_admin' not in colunas:
    cursor.execute("ALTER TABLE utilizadores ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    conn.commit()
    print('Coluna is_admin adicionada com sucesso.')
else:
    print('Coluna is_admin já existe.')

conn.close()