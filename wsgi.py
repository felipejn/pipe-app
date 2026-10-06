import sys
import os

# Ajustar o path para o PythonAnywhere
# Preenchido com o path real do projecto no PA (ver scripts/pipe_tasks.py).
PROJECTO_DIR = '/home/felipejn/pipe-app'
if PROJECTO_DIR not in sys.path:
    sys.path.insert(0, PROJECTO_DIR)

os.environ['FLASK_ENV'] = 'production'

from app import create_app
application = create_app('production')
