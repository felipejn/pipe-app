"""Testes de regressão para a renderização JavaScript do Calendário."""
import shutil
import subprocess
from pathlib import Path

import pytest


NODE = shutil.which('node')
HARNESS = Path(__file__).with_name('calendario_harness.js')


@pytest.mark.skipif(NODE is None, reason='Node.js não instalado — teste JavaScript saltado')
def test_segmentos_eventos_multidia_no_calendario():
    resultado = subprocess.run(
        [NODE, str(HARNESS)],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=30,
    )
    assert resultado.returncode == 0, (
        f'Harness do Calendário falhou:\n{resultado.stdout}\n{resultado.stderr}'
    )
