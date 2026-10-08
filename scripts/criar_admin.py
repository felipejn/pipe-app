"""
Script utilitário para criar o primeiro utilizador administrador.
Correr uma vez após o primeiro deploy:
    python scripts/criar_admin.py

Após criar o utilizador (ou detetar que já existe), aplica seed de:
- listas predefinidas de tarefas
- concelhos de combustível (Braga, Vila Verde, Amares)
- recolha inicial de postos (API Aberta, se tabela vazia e houver chave)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.auth.models import User
from app.tarefas.seed import semear_listas_predefinidas
from app.combustiveis.seed import semear_concelhos_predefinidos
from app.combustiveis import services
from app.combustiveis.models import Posto


def criar_admin():
    app = create_app('development')
    with app.app_context():
        username = input('Username: ').strip()
        email = input('Email: ').strip()
        password = input('Palavra-passe: ').strip()

        user = User.query.filter_by(username=username).first()
        if user:
            print(f'Utilizador "{username}" já existe. A aplicar seed...')
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            user.is_admin = True
            db.session.add(user)
            db.session.flush()
            semear_listas_predefinidas(user.id)
            semear_concelhos_predefinidos(user.id)

            postos_recolhidos = 0
            motivo_nao_recolha = None
            if not services.API_KEY:
                motivo_nao_recolha = 'APIABERTA_API_KEY não definida no .env'
            elif Posto.query.count() == 0:
                try:
                    resultado = services.atualizar_precos_se_necessario(forcar=True)
                    if resultado['sucesso']:
                        postos_recolhidos = resultado['precos_novos']
                    else:
                        motivo_nao_recolha = resultado['erro']
                except Exception as e:
                    motivo_nao_recolha = str(e)
            else:
                motivo_nao_recolha = 'já existem postos na BD'

            db.session.commit()
            print(f'Utilizador "{username}" criado com sucesso (admin).')
            print(f'  Listas predefinidas: 4')
            print(f'  Concelhos configurados: 3 (Braga, Vila Verde, Amares)')
            if postos_recolhidos:
                print(f'  Postos recolhidos: {postos_recolhidos}')
            else:
                print(f'  Recolha de postos não executada: {motivo_nao_recolha}')
            return

        semear_listas_predefinidas(user.id)
        semear_concelhos_predefinidos(user.id)

        postos_recolhidos = 0
        motivo_nao_recolha = None
        if not services.API_KEY:
            motivo_nao_recolha = 'APIABERTA_API_KEY não definida no .env'
        elif Posto.query.count() == 0:
            try:
                resultado = services.atualizar_precos_se_necessario(forcar=True)
                if resultado['sucesso']:
                    postos_recolhidos = resultado['precos_novos']
                else:
                    motivo_nao_recolha = resultado['erro']
            except Exception as e:
                motivo_nao_recolha = str(e)
        else:
            motivo_nao_recolha = 'já existem postos na BD'

        db.session.commit()
        print(f'Seed aplicado ao utilizador "{username}".')
        print(f'  Listas predefinidas: 4')
        print(f'  Concelhos configurados: 3 (Braga, Vila Verde, Amares)')
        if postos_recolhidos:
            print(f'  Postos recolhidos: {postos_recolhidos}')
        else:
            print(f'  Recolha de postos não executada: {motivo_nao_recolha}')


if __name__ == '__main__':
    criar_admin()
