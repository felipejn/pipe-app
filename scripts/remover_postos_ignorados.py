"""
remover_postos_ignorados.py — Remove da BD os postos em services.NOMES_IGNORADOS.

São entradas antigas da DGEG cujo `id` foi reatribuído e que a API Aberta
continua a devolver com preços congelados (duplicados dos postos já existentes
com o id novo, com valores desactualizados que falseiam o "mais barato por
combustível"). A recolha já os descarta na origem (ver services.py); este script
limpa o que ficou gravado antes dessa alteração.

    python scripts/remover_postos_ignorados.py

- A lista de nomes vive em `services.NOMES_IGNORADOS` — não é duplicada aqui.
- Apaga primeiro o histórico (`combustiveis_precos_historico`) e depois o posto,
  porque a foreign key é `nullable=False` e não há cascade configurado.
- É idempotente: correr outra vez não encontra nada para remover.
- Não toca nas preferências do utilizador nem em qualquer outro posto.
- Correr local e repetir no PythonAnywhere depois do deploy.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from app import create_app, db
from app.combustiveis import services
from app.combustiveis.models import Posto, PrecoHistorico


def main():
    app = create_app()
    with app.app_context():
        print('Nomes ignorados (services.NOMES_IGNORADOS):')
        for nome in sorted(services.NOMES_IGNORADOS):
            print(f'  - {nome}')
        print()

        alvos = [p for p in Posto.query.all() if services._nome_ignorado(p.nome)]
        alvos.sort(key=lambda p: p.nome)

        if not alvos:
            print('Nada a remover — nenhum posto corresponde à lista.')
        else:
            for posto in alvos:
                n_precos = PrecoHistorico.query.filter_by(posto_id=posto.id).count()
                PrecoHistorico.query.filter_by(posto_id=posto.id).delete()
                db.session.delete(posto)
                db.session.commit()
                print(f'  Removido: id={posto.id} {posto.nome!r} '
                      f'({posto.concelho}) — {n_precos} registo(s) de preço')

        # Verificação final: nada pode ter ficado para trás.
        restantes = [p.nome for p in Posto.query.all() if services._nome_ignorado(p.nome)]
        if restantes:
            print(f'\n! ATENÇÃO: ainda restam {restantes}')
        else:
            print('\nVerificação final: nenhum dos nomes ignorados permanece na BD.')
        print(f'Postos na BD: {Posto.query.count()} '
              f'({Posto.query.filter(Posto.ativo.is_(True)).count()} activos)')


if __name__ == '__main__':
    main()