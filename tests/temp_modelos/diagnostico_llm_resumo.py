"""Diagnóstico do Resumo Diário com LLM REAL (OpenRouter).

Reproduz localmente, sem BD, os cenários do plano v1.8.3 para perceber
porque é que o texto do LLM «não está a funcionar bem» em produção:

  A) input só-com-evento  → tende a largar metalinguagem de ausência
     («não há dados meteorológicos fornecidos»), por causa da regra v1.8.2
     «Não omitas nada… têm todos de aparecer» ser incondicional.
  B) input completo (evento + meteorologia + tarefa + combustível) → fluxo normal.
  C) input com números/decimal PT-PT → exercita a validação de completude.

A função `redacao.redigir()` é pura: recebe o texto determinístico e devolve
(texto, origem, motivo). `origem`='llm' → passou na validação;
'origem'='deterministico' → caiu no fallback e `motivo` diz porquê.

Requer OPENROUTER_API_KEY no .env do projecto (não altera o .env).
PT-PT. Nenhum ficheiro existente alterado.
"""
import os
import sys
import time

# Caminho do projecto no sys.path + carregar .env (chave OpenRouter).
_PROJETO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _PROJETO)
from dotenv import load_dotenv

load_dotenv(os.path.join(_PROJETO, '.env'))

# Forçar UTF-8 na consola do Windows (acentos/ce-cedilhado/€).
try:
    sys.stdout.reconfigure(encoding='utf-8')
except (AttributeError, ValueError):
    pass

# Ligar o LLM explicitamente (o conftest desliga-o por omissão, mas este
# script corre fora do pytest; ainda assim garantimos o interruptor).
os.environ['RESUMO_LLM_ATIVO'] = '1'

from datetime import date

from app.resumo_diario import redacao

# Data do exemplo do plano v1.8.3 (segunda-feira → há combustíveis na 2ª).
DATA = date(2026, 10, 12)

CENARIOS = [
    (
        'A) só-com-evento (caso problemático do plano)',
        'Hoje: Reunião - Filipa Quintas (14:00).',
        ['Reunião - Filipa Quintas'],
    ),
    (
        'B) completo (evento + meteorologia + tarefa + combustível)',
        'Meteorologia: 13 a 23 °C, céu limpo.\n\n'
        'Hoje: Reunião - Filipa Quintas (14:00).\n\n'
        'Tarefas\nVencem hoje: Comprar pão.\n\n'
        'Combustíveis\nGasolina: 1,789 €/L — Galp (Braga)\n'
        'Última recolha: 12/10/2026 08:15',
        ['Reunião - Filipa Quintas', 'Comprar pão'],
    ),
    (
        'C) só-meteorologia (números a sobreviver)',
        'Meteorologia: 13 a 23 °C, 20% de precipitação.',
        [],
    ),
]


def _safe(texto):
    """Garante que a impressão nunca rebenta por chars estranhos na consola."""
    return (texto or '').encode('utf-8', errors='replace').decode('utf-8')


def correr_cenario(nome, dados, titulos):
    print('=' * 72)
    print(f'CENÁRIO {nome}')
    print('-' * 72)
    print('DADOS de entrada (determinístico):')
    for linha in dados.splitlines():
        print(f'    {linha}')
    print('-' * 72)

    # 1) Resposta CRUA do LLM (sem validação) — o que o modelo realmente devolve.
    from app.assistente.cliente import chamar_llm
    inicio = time.time()
    crua = None
    erro = None
    try:
        resposta = chamar_llm(
            [
                {'role': 'system',
                 'content': redacao.MENSAGEM_SISTEMA.format(limite=900)},
                {'role': 'user', 'content': f'Dados do resumo:\n{dados}'},
            ],
            prazo_total=redacao._orcamento('task'),
        )
        crua = resposta['choices'][0]['message']['content']
    except Exception as exc:  # noqa: BLE001
        erro = exc
    durou = time.time() - inicio

    print(f'RESPOSTA CRUA do LLM (duração: {durou:.2f}s):')
    if erro is not None:
        print(f'    [ERRO] {type(erro).__name__}: {str(erro)[:200]}')
    else:
        for linha in (crua or '').splitlines():
            print(f'    | {linha}')
    print('-' * 72)

    # 2) Resultado da validação v1.8.2 sobre essa resposta crua.
    titulos_exigidos = [
        t for t in titulos if t and str(t).strip()
        and str(t).casefold() in dados.casefold()]
    valido, detalhe = redacao.validar_resposta(
        crua, dados, DATA, titulos_exigidos, 900)
    print(f'VALIDAÇÃO v1.8.2: {"PASSA" if valido else "FALHA → " + str(detalhe)}')

    # 3) Fluxo real (redigir) — para confirmar a origem/motivo finais.
    texto, origem, motivo = redacao.redigir(
        dados, DATA, modo='task', titulos=titulos, limite=900)
    rotulo = 'LLM' if origem == 'llm' else f'determinístico — {motivo}'
    print(f'ORIGEM final (redigir): {rotulo}')
    print()

    # Sinaliza metalinguagem de ausência no texto final (o bug do plano).
    texto_min = (texto or '').casefold()
    suspeitas = [
        p for p in ('não há', 'sem dados', 'não foi fornecido',
                    'não fornecid', 'não tens', 'secção', 'seção', 'tópico')
        if p in texto_min
    ]
    if suspeitas:
        print(f'  >> METALINGUAGEM no texto final: {suspeitas}')
    print()



def main():
    if not (os.environ.get('OPENROUTER_API_KEY') or '').strip():
        print('ERRO: OPENROUTER_API_KEY ausente. Configura o .env.')
        return 1
    print('Diagnóstico do Resumo Diário com LLM real '
          f'(modelo: {os.environ.get("OPENROUTER_MODEL", "por omissão")})\n')

    # Um cenário por execução (cada um faz 2 chamadas ao LLM; evita timeouts).
    # Sem argumento corre todos. Com argumento (0,1,2) corre só esse índice.
    indices = range(len(CENARIOS))
    if len(sys.argv) > 1 and sys.argv[1].strip().isdigit():
        indices = [int(sys.argv[1])]
    for i in indices:
        nome, dados, titulos = CENARIOS[i]
        correr_cenario(nome, dados, titulos)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
