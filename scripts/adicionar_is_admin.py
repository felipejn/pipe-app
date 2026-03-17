# scripts/adicionar_is_admin.py
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'instance', 'pipe.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Adicionar coluna sem recriar a tabela
cursor.execute("ALTER TABLE utilizadores ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL")
conn.commit()
conn.close()

print("Coluna is_admin adicionada com sucesso.")