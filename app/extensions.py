from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    # NOTA: key_func com X-Forwarded-For é obrigatório no PythonAnywhere.
    # O PA corre atrás de proxy reverso — sem isto, o REMOTE_ADDR é sempre
    # o IP interno do proxy e o rate limiting bloquearia todos os utilizadores.
    key_func=get_remote_address,
    default_limits=[],
    storage_uri='memory://',
)
