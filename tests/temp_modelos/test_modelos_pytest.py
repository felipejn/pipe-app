"""Pytest temporario — valida que resposta nao e vazia e mede tempo.
PT-PT. Nenhum ficheiro existente alterado."""
import os
import pytest
from tests.temp_modelos.test_comparacao_modelos import MODELOS, executar_modelo, PROMPT

@pytest.mark.skipif(not os.environ.get('OPENROUTER_API_KEY'), reason="OPENROUTER_API_KEY ausente")
def test_modelos_respondem():
    resultados = [executar_modelo(m) for m in MODELOS[:2]]  # amostra 2 para nao sobrecarregar
    for r in resultados:
        assert r.get("erro") is None, f"{r['modelo']}: erro={r['erro']}"
        assert r.get("resposta") and len(r["resposta"]) > 5, f"{r['modelo']}: resposta muito curta"
        assert r.get("tempo") and r["tempo"] < 30, f"{r['modelo']}: muito lento (>30s)"