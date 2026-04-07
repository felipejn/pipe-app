"""Script de teste local para o Assistente PIPE.

Requisitos:
- .env com OPENROUTER_API_KEY configurada
- Utilizador com id=1 deve existir na BD

Uso:
    python scripts/testar_assistente.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.assistente.contexto import processar_mensagem_assistente

app = create_app()

testes = [
    "Olá, o que podes fazer?",
    "Tenho tarefas em atraso?",
    "Dá-me um resumo geral",
]

with app.app_context():
    historico = []

    for mensagem in testes:
        print(f"\n{'=' * 60}")
        print(f">> {mensagem}")
        resposta, historico = processar_mensagem_assistente(
            mensagem, user_id=1, historico=historico
        )
        print(f"<< {resposta}")
        print(f"(histórico: {len(historico)} mensagens)")
