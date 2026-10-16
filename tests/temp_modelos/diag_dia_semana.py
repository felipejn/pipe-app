"""Verificação multi-execução do dia da semana com LLM real.

Corre o fluxo real (`redacao.redigir`) N vezes para o caso de segunda e
confirma que NUNCA escapa um dia da semana errado: ou o LLM diz «segunda»/nada,
ou cai no determinístico com `dia da semana errado`. PT-PT, untracked.
"""
import os
import sys
import time

_PROJETO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJETO)
from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJETO, '.env'))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass
os.environ['RESUMO_LLM_ATIVO'] = '1'

from datetime import date

from app.resumo_diario import redacao

DATA = date(2026, 10, 12)  # segunda-feira
DADOS = (
    'Meteorologia: 14 a 23 °C, Nevoeiro\n'
    'Tarefas\n'
    'Em atraso (09/10): Revisar o relatório financeiro do trimestre e enviar ao supervisor\n'
    'Em atraso (10/10): Organizar a garagem e separar documentos para reciclagem\n'
    'Em atraso (11/10): Planear o menu da semana e fazer a lista de compras'
)
TITULOS = [
    'Revisar o relatório financeiro do trimestre e enviar ao supervisor',
    'Organizar a garagem e separar documentos para reciclagem',
    'Planear o menu da semana e fazer a lista de compras',
]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    for i in range(1, n + 1):
        inicio = time.time()
        texto, origem, motivo = redacao.redigir(DADOS, DATA, titulos=TITULOS)
        durou = time.time() - inicio
        primeira = (texto.splitlines() or [''])[0][:90]
        print(f'#{i} [{origem}'
              f'{" — " + motivo if motivo else ""}] ({durou:.1f}s): {primeira}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
