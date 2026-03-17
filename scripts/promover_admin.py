"""
Promove um utilizador existente a admin.
Usar no primeiro arranque ou em recuperação de acesso.

Uso:
    python scripts/promover_admin.py <username>

Exemplo:
    python scripts/promover_admin.py felipejn
"""

import sys
import os

# Garante que o projecto está no path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app import create_app, db
from app.auth.models import User

def promover(username):
    app = create_app()
    with app.app_context():
        u = User.query.filter_by(username=username).first()
        if not u:
            print(f"Erro: utilizador '{username}' não encontrado.")
            sys.exit(1)
        if u.is_admin:
            print(f"'{username}' já é admin.")
            sys.exit(0)
        u.is_admin = True
        db.session.commit()
        print(f"OK: '{username}' é agora admin.")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Uso: python scripts/promover_admin.py <username>")
        sys.exit(1)
    promover(sys.argv[1])
