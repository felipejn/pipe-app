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


def _verificar_schema(engine=None):
    """True se a BD já tem as colunas novas do Posto (ativo/ciclos_ausente).

    Sem estas colunas (BD do PA ainda não passou pelo reset v1.3.2/v1.3.3),
    qualquer query a Posto rebenta — e este script não pode sequer ler os
    postos para detectar duplicados. Nesse caso, orienta ao utilizador para
    correr primeiro o script de reset, em vez de deixar um traceback opaco.
    """
    from sqlalchemy import inspect
    if engine is None:
        engine = db.engine
    insp = inspect(engine)
    try:
        cols = {c['name'] for c in insp.get_columns('combustiveis_postos')}
    except Exception:
        cols = set()
    if 'ativo' not in cols:
        print('AVISO: a BD ainda não tem as colunas novas (ativo/ciclos_ausente).')
        print('Não é possível listar/remover postos. Executa primeiro:')
        print('    python scripts/reset_postos_combustiveis.py')
        print('que recria as tabelas (db.create_all), reinicia o estado de actualização')
        print('e força uma recolha — só depois corre este script.')
        return False
    return True


def main():
    app = create_app()
    with app.app_context():
        if not _verificar_schema():
            return
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