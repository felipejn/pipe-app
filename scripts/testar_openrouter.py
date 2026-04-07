import os, requests, time
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('OPENROUTER_API_KEY')
URL = "https://openrouter.ai/api/v1/chat/completions"

modelos = [
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-3-27b-it:free",
    "google/gemma-3-12b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]

for modelo in modelos:
    try:
        r = requests.post(URL,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": modelo, "messages": [{"role": "user", "content": "Diz apenas: ok"}], "max_tokens": 10},
            timeout=15
        )
        conteudo = r.json().get('choices', [{}])[0].get('message', {}).get('content', r.text[:80])
        print(f"{r.status_code} {modelo}: {conteudo}")
    except Exception as e:
        print(f"ERRO {modelo}: {e}")
    time.sleep(1)
