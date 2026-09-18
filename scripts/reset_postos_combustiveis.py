"""
reset_postos_combustiveis.py — Reinicia por completo os postos e o histórico.

Reinicia por completo as tabelas de postos e histórico de preços, mantendo as
definições do utilizador (concelhos e combustíveis escolhidos). Usar depois de
aplicar as migrações de app/combustiveis/models.py. Correr uma vez local,
depois repetir no PythonAnywhere.

    python scripts/reset_postos_combustiveis.py

O que faz:
- Apaga por completo as tabelas `combustiveis_precos_historico` e
  `combustiveis_postos` (não só as linhas) para que o create_all() a seguir as
  recrie já com as colunas novas (`ativo`, `ciclos_ausente`) sem precisar de
  ALTER TABLE manual.
- Não toca em `combustiveis_utilizador_concelho` nem em
  `combustiveis_utilizador_combustivel` — as preferências mantêm-se.
- Repõe `ultima_atualizacao = None` e força uma recolha imediata
  (`atualizar_precos_se_necessario(forcar=True)`), que volta a repovoar os
  postos e o histórico a partir da API Aberta (api.apiaberta.pt).

NOTA (produção/PA): confirmar que `api.apiaberta.pt` está na whitelist do
PythonAnywhere antes de correr.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

from app import create_app, db
from app.combustiveis import services
from app.combustiveis.models import (
    Posto, PrecoHistorico, EstadoAtualizacaoCombustiveis
)


def mostrar_resumo():
    """Mostra o que ficou gravado na BD (para confirmar a recolha)."""
    ativos = Posto.query.filter(Posto.ativo.is_(True)).count()
    arquivados = Posto.query.filter(Posto.ativo.is_(False)).count()

    print(f'  Postos activos:        {ativos}')
    print(f'  Postos arquivados:     {arquivados}')
    print(f'  Registos de preços:    {PrecoHistorico.query.count()}')

    print('  Postos activos por concelho:')
    for concelho in sorted(services.MUNICIPIOS_INTERESSE):
        n = Posto.query.filter(
            Posto.ativo.is_(True), Posto.concelho == concelho
        ).count()
        print(f'    {concelho:<12} {n}')


def main():
    app = create_app()
    with app.app_context():
        # Apaga por completo as tabelas (não só as linhas) para que o
        # create_all() a seguir as recrie já com as colunas novas
        # (ativo, ciclos_ausente) sem precisar de ALTER TABLE manual.
        # Ordem: primeiro o histórico (tem a foreign key para os postos).
        PrecoHistorico.__table__.drop(db.engine, checkfirst=True)
        Posto.__table__.drop(db.engine, checkfirst=True)
        db.create_all()

        estado = EstadoAtualizacaoCombustiveis.query.get(1)
        if estado:
            estado.ultima_atualizacao = None
            db.session.commit()

        print('Tabelas de postos e histórico recriadas. A repovoar...')

        inicio = time.time()
        resultado = services.atualizar_precos_se_necessario(forcar=True)
        duracao = time.time() - inicio

        print(f'  Executado:             {resultado["executado"]}')
        print(f'  Sucesso:               {resultado["sucesso"]}')
        print(f'  Postos verificados:    {resultado["postos_verificados"]}')
        print(f'  Registos novos:        {resultado["precos_novos"]}')
        print(f'  Postos arquivados:     {resultado["postos_arquivados"]}')
        if resultado['erro']:
            print(f'  Erro:                  {resultado["erro"]}')
        print(f'  Duração:               {duracao:.1f}s')
        print()

        mostrar_resumo()


if __name__ == '__main__':
    main()