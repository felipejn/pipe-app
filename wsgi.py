import sys
import os

# Ajustar o path para o PythonAnywhere
# Substituir 'utilizador' pelo teu username no PA
PROJECTO_DIR = '/home/utilizador/pipe'
if PROJECTO_DIR not in sys.path:
    sys.path.insert(0, PROJECTO_DIR)

os.environ['FLASK_ENV'] = 'production'

from app import create_app
application = create_app('production')
