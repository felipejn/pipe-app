"""
popular_combustiveis.py — Recolha manual de preços de combustível (API Aberta).

Script AVULSO, reutilizável, para correr manualmente sempre que for preciso
repopular a base de dados com dados frescos da API Aberta:

    python scripts/popular_combustiveis.py

- Chama `services.atualizar_precos_se_necessario(forcar=True)`, que percorre
  os combustíveis de FUEL_SLUGS, filtra para Braga / Vila Verde / Amares e
  grava em Posto + PrecoHistorico.
- É seguro correr várias vezes: os postos existentes são actualizados pelo
  `station_id` e cada execução acrescenta novas linhas ao histórico.
- NÃO faz parte da tarefa agendada (pipe_tasks.py) — lá corre a versão
  automática (`forcar=False`), que só actua às terças-feiras.
- Com `APIABERTA_API_KEY` no .env usa o tier de 300 pedidos/minuto (~25 s);
  sem chave cai no tier anónimo de 30 pedidos/minuto (vários minutos).
- NOTA (produção/PA): confirmar que `api.apiaberta.pt` está na whitelist do
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
from app.combustiveis.models import Posto, PrecoHistorico


def mostrar_resumo():
    """Mostra o que ficou gravado na BD (para confirmar a recolha)."""
    total_postos = Posto.query.count()
    total_precos = PrecoHistorico.query.count()
    print(f'  Postos na BD:          {total_postos}')
    print(f'  Registos de preços:    {total_precos}')

    print('  Postos por concelho:')
    for concelho in sorted(services.MUNICIPIOS_INTERESSE):
        n = Posto.query.filter_by(concelho=concelho).count()
        print(f'    {concelho:<12} {n}')

    print('  Tipos de combustível disponíveis:')
    tipos = (
        db.session.query(PrecoHistorico.tipo_combustivel)
        .distinct().order_by(PrecoHistorico.tipo_combustivel).all()
    )
    for (tipo,) in tipos:
        print(f'    {tipo}')


def main():
    tem_chave = bool(services.API_KEY)
    print('╔══ PIPE — Recolha de combustíveis (API Aberta) ══╗')
    print(f'  Autenticação: {"X-API-Key presente" if tem_chave else "sem chave (tier anónimo, 30 pedidos/min)"}')
    print(f'  Combustíveis: {", ".join(services.FUEL_SLUGS)}')
    print(f'  Concelhos:    {", ".join(sorted(services.MUNICIPIOS_INTERESSE))}')
    print()

    app = create_app()
    with app.app_context():
        inicio = time.time()
        resultado = services.atualizar_precos_se_necessario(forcar=True)
        duracao = time.time() - inicio

        print(f'  Executado:             {resultado["executado"]}')
        print(f'  Sucesso:               {resultado["sucesso"]}')
        print(f'  Postos actualizados:   {resultado["postos_atualizados"]}')
        if resultado['erro']:
            print(f'  Erro:                  {resultado["erro"]}')
        print(f'  Duração:               {duracao:.1f}s')
        print()

        mostrar_resumo()

    print('╚══ Fim ══╝')


if __name__ == '__main__':
    main()
