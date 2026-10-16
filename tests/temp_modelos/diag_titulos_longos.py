"""Diagnóstico pontual: títulos LONGOS e descritivos (tarefas em atraso).

Reproduz o caso reportado na pré-visualização local: o LLM condensa títulos
longos e a validação «todas as palavras-chave» rejeita por `título em falta`.

Mostra a resposta crua do LLM e, por título, que palavras-chave faltaram —
para calibrar a regra de validação. PT-PT. Nenhum ficheiro existente alterado.
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

from app.assistente.cliente import chamar_llm
from app.resumo_diario import redacao

DATA = date(2026, 10, 12)  # segunda-feira (caso reportado: LLM dizia "sexta")

# Texto determinístico EXACTO da pré-visualização reportada.
DADOS = (
    'Meteorologia: 14–23 °C, Nevoeiro\n'
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
    if not (os.environ.get('OPENROUTER_API_KEY') or '').strip():
        print('ERRO: OPENROUTER_API_KEY ausente.')
        return 1

    inicio = time.time()
    try:
        resposta = chamar_llm(
            [
                {'role': 'system',
                 'content': redacao.MENSAGEM_SISTEMA.format(limite=900)},
                {'role': 'user', 'content': f'Dados do resumo:\n{DADOS}'},
            ],
            prazo_total=redacao._orcamento('task'),
        )
        crua = resposta['choices'][0]['message']['content']
    except Exception as exc:  # noqa: BLE001
        print(f'[ERRO] {type(exc).__name__}: {str(exc)[:200]}')
        return 1
    durou = time.time() - inicio

    print(f'=== RESPOSTA CRUA do LLM (duração: {durou:.2f}s) ===')
    print(crua)
    print('\n=== VALIDAÇÃO ===')
    valido, detalhe = redacao.validar_resposta(crua, DADOS, DATA, TITULOS, 900)
    print(f'Resultado: {"PASSA" if valido else "FALHA → " + str(detalhe)}')

    print('\n=== PALAVRAS-CHAVE POR TÍTULO (o que falta no texto) ===')
    texto_min = crua.casefold()
    for titulo in TITULOS:
        chaves = [p.casefold() for p in redacao._palavras_chave(titulo)]
        presentes = [c for c in chaves if c in texto_min]
        faltam = [c for c in chaves if c not in texto_min]
        print(f'\n«{titulo}»')
        print(f'  chaves ({len(chaves)}): {chaves}')
        print(f'  presentes ({len(presentes)}): {presentes}')
        print(f'  EM FALTA ({len(faltam)}): {faltam}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
