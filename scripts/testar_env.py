"""Testar a chave do .env no modelo corrente."""
import os, requests
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('OPENROUTER_API_KEY')
model = os.getenv('OPENROUTER_MODEL')
print(f'KEY: {key[:15]}...')
print(f'MODEL: {model}')
r = requests.post(
    'https://openrouter.ai/api/v1/chat/completions',
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    json={'model': model, 'messages': [{'role': 'user', 'content': 'ola em pt-pt'}]},
    timeout=30,
)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    c = r.json().get('choices', [{}])[0].get('message', {}).get('content', '')
    print(f'Resposta: {c}')
else:
    print(f'Erro: {r.text[:200]}')
