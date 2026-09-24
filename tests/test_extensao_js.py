"""Validação do JavaScript da extensão Chrome (content script + popup).

Corre `tests/extensao_harness.js` com o Node, que carrega os ficheiros reais
da extensão num `vm` com stubs de `chrome`/`document` e verifica onde o content
script captura (e onde NÃO captura) e as funções puras do popup.

Regressão da v1.5.1: a captura pendente aparecia em todos os separadores e o
`content.js` capturava o login do próprio PIPE local (só excluía a produção).
Sem Node instalado o teste é saltado — a suite Python continua a ser a autoridade.
"""
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NODE = shutil.which('node')
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'extensao_harness.js')


@pytest.mark.skipif(NODE is None,
                    reason='Node.js não instalado — harness do JS da extensão saltado')
def test_harness_da_extensao():
    r = subprocess.run(
        [NODE, HARNESS],
        capture_output=True, text=True,
        encoding='utf-8', errors='replace',
        timeout=60,
    )
    assert r.returncode == 0, (
        f'harness do JS falhou:\n--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}'
    )
    assert 'FALHA' not in r.stdout, r.stdout
