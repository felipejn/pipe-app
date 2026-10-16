"""Testes temporarios de comparacao de modelos free OpenRouter.
PT-PT conforme CLAUDE.md. Nenhum ficheiro existente alterado.
Usa prompt real do assistente (leitura) + mede tempo e qualidade.
Requer OPENROUTER_API_KEY no ambiente (nao modifica .env)."""
import os, time, statistics
import requests

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
API_KEY = os.environ.get('OPENROUTER_API_KEY')

# Modelos validos ordenados por qualidade/tempo (melhor ratio primeiro)
MODELOS = [
    'cohere/north-mini-code:free',              # 2.01s, resposta util
    'nvidia/nemotron-3-super-120b-a12b:free',   # 2.06s, resposta contextualizada
    'liquid/lfm-2.5-2.6b:free',                # 4.98s, resposta generica
    'dots-studio/dots-3-note-preview:free',     # 9.65s, resposta contextualizada
    'nvidia/nemotron-3-ultra-550b-a55b:free',   # 0.40s mas resposta vazia
    'poolside/laguna-s-2.1:free',               # 429 rate limit (pode ser temporario)
]

PROMPT = "Quais as tarefas pendentes para hoje? Responde de forma concisa."


def executar_modelo(modelo):
    if not API_KEY:
        return {"modelo": modelo, "erro": "OPENROUTER_API_KEY ausente", "tempo": None, "resposta": None}
    payload = {
        "model": modelo,
        "messages": [{"role": "user", "content": PROMPT}],
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    inicio = time.time()
    try:
        r = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
        r.raise_for_status()
        dados = r.json()
        tempo = time.time() - inicio
        resposta = dados.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"modelo": modelo, "tempo": round(tempo, 2), "resposta": (resposta or "")[:500], "tokens": dados.get("usage", {}).get("total_tokens")}
    except Exception as e:
        return {"modelo": modelo, "erro": str(e)[:200], "tempo": round(time.time() - inicio, 2), "resposta": None}


def _safe(text):
    """Remove chars que nao existem em cp1252 (Windows console)."""
    return text.encode('cp1252', errors='replace').decode('cp1252') if text else ''

def main():
    resultados = [executar_modelo(m) for m in MODELOS]
    print("=== RESULTADOS (PT-PT) ===")
    for res in resultados:
        resp = _safe((res.get('resposta') or '')[:200])
        print(f"\n{res['modelo']}: tempo={res.get('tempo')}s | erro={res.get('erro')} | resposta={resp}")
    tempos = [r["tempo"] for r in resultados if r.get("tempo") and not r.get("erro")]
    if tempos:
        print(f"\nTempo medio: {statistics.mean(tempos):.2f}s | Min: {min(tempos):.2f}s")
    qualidade = sum(1 for r in resultados if r.get("resposta") and len(r["resposta"]) > 10)
    print(f"Qualidade (resposta nao vazia): {qualidade}/{len(MODELOS)}")


if __name__ == "__main__":
    main()