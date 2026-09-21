"""Smoke test local da ferramenta get_combustiveis do Assistente IA.

Corre a ferramenta directamente contra a BD real (sem chamar a OpenRouter),
para validar filtros, erros e formato da resposta.

Uso:
    python scripts/smoke_combustiveis.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

# A consola do Windows pode não suportar UTF-8 (setas, acentos) — força-o.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app import create_app
from app.assistente.ferramentas import executar_ferramenta

USER_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 1

CASOS = [
    ('mais barato (sem filtros)', {'apenas_mais_barato': True}),
    ('gasóleo simples, limite 3', {'tipo_combustivel': 'gasoleo simples', 'limite': 3}),
    ('concelho inexistente', {'concelho': 'Lisboa'}),
    ('combustível inexistente', {'tipo_combustivel': 'Hidrogénio'}),
    ('limite inválido', {'limite': 'abc'}),
    ('todos (alias)', {'tipo_combustivel': 'Todos', 'limite': 2}),
]

app = create_app()

with app.app_context():
    for nome, argumentos in CASOS:
        print(f'\n{"=" * 68}\n>> {nome}  arguamentos={argumentos}')
        resultado = executar_ferramenta('get_combustiveis', argumentos, USER_ID, modo='leitura')
        texto = json.dumps(resultado, ensure_ascii=False, indent=1)
        print(texto[:1400])

    print(f'\n{"=" * 68}\n>> get_resumo_geral (só chaves de combustíveis)')
    resumo = executar_ferramenta('get_resumo_geral', {}, USER_ID, modo='leitura')
    if isinstance(resumo, dict):
        for chave, valor in resumo.items():
            if chave.startswith('combustiveis'):
                print(f'  {chave}: {json.dumps(valor, ensure_ascii=False)}')
