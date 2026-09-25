#!/usr/bin/env python
"""Verifica no Mailjet se os emails do PIPE foram realmente enviados/entregues.

Lista as últimas mensagens da conta Mailjet (GET /v3/REST/message), resolve o
destinatário (GET /v3/REST/contact/{ContactID}) e mostra o histórico de eventos
(GET /v3/REST/messagehistory/{ID}) — p.ex. `sent`, `delivered`, `opened`,
`bounced`, `softbounced`, `failed`, `blocked`. Um email pode ser aceite pela
API (200) e mesmo assim falhar depois; esta ferramenta mostra o resultado real.

Credenciais lidas do .env (MAILJET_API_KEY / MAILJET_API_SECRET).

Uso:
    python scripts/verificar_mailjet.py                  # últimas 10 mensagens
    python scripts/verificar_mailjet.py --destinatario x@y.com
    python scripts/verificar_mailjet.py --limite 25
    python scripts/verificar_mailjet.py --apenas-hoje
    python scripts/verificar_mailjet.py --ligar-convites # atribui IDs aos convites sem ID
"""
import argparse
import base64
import datetime
import os
import sys

import requests
from dotenv import load_dotenv

# Caminho do projecto no sys.path (para o --ligar-convites importar a app)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

BASE = 'https://api.mailjet.com/v3'
TIMEOUT = 20


def _auth():
    load_dotenv()
    key = os.getenv('MAILJET_API_KEY', '').strip()
    secret = os.getenv('MAILJET_API_SECRET', '').strip()
    if not key or not secret:
        sys.exit('MAILJET_API_KEY / MAILJET_API_SECRET em falta no .env')
    token = base64.b64encode(f'{key}:{secret}'.encode()).decode()
    return {'Authorization': f'Basic {token}'}


def _tempo(ts):
    """Unix timestamp ou string ISO → 'dd/mm/aaaa hh:mm:ss'."""
    try:
        return datetime.datetime.fromtimestamp(int(ts)).strftime('%d/%m/%Y %H:%M:%S')
    except (TypeError, ValueError, OSError):
        return str(ts or '?')


def _email_do_contacto(headers, contact_id):
    """ContactID da mensagem → email do destinatário (None se falhar)."""
    if not contact_id:
        return None
    try:
        r = requests.get(f'{BASE}/REST/contact/{contact_id}',
                         headers=headers, timeout=TIMEOUT)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    dados = r.json().get('Data') or []
    return dados[0].get('Email') if dados else None


def listar_mensagens(headers, limite, apenas_hoje=False):
    # A lista vem por ordem crescente (mais antigas primeiro) — busca com folga,
    # ordena do mais recente para o mais antigo e só depois corta em `limite`.
    r = requests.get(f'{BASE}/REST/message', headers=headers,
                     params={'Limit': max(limite, 100)}, timeout=TIMEOUT)
    if r.status_code != 200:
        sys.exit(f'GET /message falhou: {r.status_code} {r.text[:300]}')
    mensagens = r.json().get('Data', [])
    if apenas_hoje:
        hoje = datetime.date.today().isoformat()
        mensagens = [m for m in mensagens
                     if str(m.get('ArrivedAt', '')).startswith(hoje)]
    mensagens.sort(key=lambda m: str(m.get('ArrivedAt', '')), reverse=True)
    return mensagens[:limite]


def historico(headers, message_id):
    r = requests.get(f'{BASE}/REST/messagehistory/{message_id}',
                     headers=headers, timeout=TIMEOUT)
    if r.status_code != 200:
        return None, f'HTTP {r.status_code}'
    eventos = r.json().get('Data', [])
    eventos.sort(key=lambda e: int(e.get('EventAt') or 0))
    return eventos, None


def _para_utc(iso):
    """'2026-09-25T08:28:14Z' → datetime UTC naive (ou None)."""
    try:
        return datetime.datetime.strptime(iso, '%Y-%m-%dT%H:%M:%SZ')
    except (TypeError, ValueError):
        return None


def ligar_convites(headers):
    """Atribui `mailjet_message_id` aos convites locais ainda sem ID.

    O ID só passou a ser guardado a partir da v1.5.2; convites antigos são
    ligados por email + proximidade temporal (mensagem do mesmo destinatário
    enviada até 2h após a criação do convite). Requer as colunas novas da BD
    (correr antes: `python scripts/migrar_convites_mailjet.py`).
    """
    from app import create_app, db
    from app.auth.models import Convite

    todos = listar_mensagens(headers, 200)
    app = create_app()
    with app.app_context():
        ligados = 0
        for c in Convite.query.filter(Convite.mailjet_message_id.is_(None)).all():
            candidatas = [m for m in todos
                          if (_email_do_contacto(headers, m.get('ContactID')) or '')
                          .lower() == c.email.lower()]
            melhor, melhor_delta = None, None
            for m in candidatas:
                quando = _para_utc(m.get('ArrivedAt'))
                if quando is None or c.criado_em is None:
                    continue
                delta = abs((quando - c.criado_em).total_seconds())
                if delta <= 7200 and (melhor_delta is None or delta < melhor_delta):
                    melhor, melhor_delta = m, delta
            if melhor:
                c.mailjet_message_id = str(melhor.get('ID'))
                c.email_estado = melhor.get('Status') or 'aceite'
                ligados += 1
                print(f'✓ convite #{c.id} ({c.email}) → mensagem {c.mailjet_message_id}'
                      f' [{c.email_estado}]')
        db.session.commit()
        print(f'{ligados} convite(s) ligado(s) a mensagens do Mailjet.')


def main():
    parser = argparse.ArgumentParser(description='Estado real dos emails no Mailjet')
    parser.add_argument('--limite', type=int, default=10,
                        help='número de mensagens a analisar (default: 10)')
    parser.add_argument('--destinatario', default=None,
                        help='apenas mensagens para este email')
    parser.add_argument('--apenas-hoje', action='store_true',
                        help='apenas mensagens de hoje')
    parser.add_argument('--ligar-convites', action='store_true',
                        help='atribui mailjet_message_id aos convites locais sem ID')
    args = parser.parse_args()

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    headers = _auth()
    mensagens = listar_mensagens(headers, args.limite, args.apenas_hoje)
    if args.destinatario:
        alvo = args.destinatario.lower()
        mensagens = [m for m in mensagens
                     if (_email_do_contacto(headers, m.get('ContactID')) or '')
                     .lower() == alvo]

    if not mensagens:
        print('Nenhuma mensagem encontrada.')
        return

    print(f'{len(mensagens)} mensagem(ns) encontrada(s):\n')
    for m in mensagens:
        mid = m.get('ID')
        para = _email_do_contacto(headers, m.get('ContactID')) or '?'
        print(f'ID {mid} · {m.get("ArrivedAt", "?")} (recebida pelo Mailjet)')
        print(f'   Para:      {para}')
        print(f'   Estado:    {m.get("Status", "?")}'
              f' · spam score {m.get("SpamassassinScore", "?")}')
        eventos, erro = historico(headers, mid)
        if erro:
            print(f'   Eventos:   indisponíveis ({erro})')
        elif not eventos:
            print('   Eventos:   nenhum registado')
        else:
            print('   Eventos:')
            for e in eventos:
                print(f'     - {_tempo(e.get("EventAt"))}  {e.get("EventType")}')
        print()

    print('Legenda: "sent" = o Mailjet entregou ao servidor do destinatário;')
    print('"delivered"/"opened" = confirmação; "bounced"/"failed" = falha;')
    print('sem "delivered" não há confirmação de caixa de entrada — pode estar em spam.')

    if args.ligar_convites:
        print()
        ligar_convites(headers)


if __name__ == '__main__':
    main()
