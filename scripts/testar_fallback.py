"""Testar os modelos fallback do assistente."""
import os, requests, time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('OPENROUTER_API_KEY')
URL = 'https://openrouter.ai/api/v1/chat/completions'

modelos = [
    'qwen/qwen3.6-plus:free',
    'qwen/qwen3-14b:free',
    'meta-llama/llama-4-maverick:free',
]

for m in modelos:
    try:
        r = requests.post(
            URL,
            headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'},
            json={'model': m, 'messages': [{'role': 'user', 'content': 'Diz apenas: ok'}]},
            timeout=15,
        )
        print(f'{r.status_code} {m}')
        if r.status_code == 200:
            c = r.json().get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f'  -> {c}')
        else:
            print(f'  -> {r.text[:150]}')
    except Exception as e:
        print(f'  Erro: {e}')
    time.sleep(1)
