"""Cópia de segurança da base de dados SQLite do PIPE.

Uso:
    python scripts/backup_bd.py

Copia `instance/pipe.db` para `instance/backups/pipe-AAAAMMDD-HHMMSS.db` e
mantém apenas as últimas 10 cópias. Correr antes de operações de risco
(scripts que apagam tabelas, migrações manuais) e, opcionalmente, num cron do
PythonAnywhere.

Nota: a cópia é feita com a aplicação potencialmente a correr; como o SQLite
está em journal_mode `delete` (sem WAL) e as transacções são curtas, é
suficiente para cópias de segurança de desenvolvimento/PA.
"""
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BASE_DIR

MAX_COPIAS = 10


def backup():
    origem = os.path.join(BASE_DIR, 'instance', 'pipe.db')
    if not os.path.exists(origem):
        print(f'Nada a copiar: {origem} não existe.')
        return 1

    destino_dir = os.path.join(BASE_DIR, 'instance', 'backups')
    os.makedirs(destino_dir, exist_ok=True)

    nome = 'pipe-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.db'
    destino = os.path.join(destino_dir, nome)
    shutil.copy2(origem, destino)
    print(f'Cópia criada: {destino} ({os.path.getsize(destino)} bytes)')

    # Nomes com timestamp ordenam cronologicamente — apaga as mais antigas
    copias = sorted(
        f for f in os.listdir(destino_dir)
        if f.startswith('pipe-') and f.endswith('.db')
    )
    for antiga in copias[:-MAX_COPIAS]:
        os.remove(os.path.join(destino_dir, antiga))
        print(f'Cópia antiga removida: {antiga}')

    return 0


if __name__ == '__main__':
    sys.exit(backup())
