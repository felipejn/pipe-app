"""
Script utilitário para criar o primeiro utilizador administrador.
Correr uma vez após o primeiro deploy:
    python scripts/criar_admin.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.auth.models import User

def criar_admin():
    app = create_app('development')
    with app.app_context():
        username = input('Username: ').strip()
        email = input('Email: ').strip()
        password = input('Palavra-passe: ').strip()

        if User.query.filter_by(username=username).first():
            print(f'Erro: utilizador "{username}" já existe.')
            return

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print(f'Utilizador "{username}" criado com sucesso.')

if __name__ == '__main__':
    criar_admin()
