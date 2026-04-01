from flask import render_template, request, jsonify
from flask_login import login_required
from app.passwords import bp
from app.passwords.generator import gerar_password, gerar_passphrase, gerar_pin


@bp.route('/')
@login_required
def index():
    return render_template('passwords/index.html')


@bp.route('/api/gerar', methods=['POST'])
@login_required
def api_gerar():
    dados = request.get_json(force=True)
    modo = dados.get('modo', 'password')

    if modo == 'passphrase':
        num_palavras = max(3, min(10, int(dados.get('num_palavras', 4))))
        resultado = gerar_passphrase(num_palavras)
    elif modo == 'pin':
        comprimento = max(4, min(12, int(dados.get('comprimento', 6))))
        resultado = gerar_pin(comprimento)
    else:
        comprimento = max(8, min(64, int(dados.get('comprimento', 18))))
        resultado = gerar_password(
            comprimento=comprimento,
            maiusculas=bool(dados.get('maiusculas', True)),
            minusculas=bool(dados.get('minusculas', True)),
            numeros=bool(dados.get('numeros', True)),
            simbolos=bool(dados.get('simbolos', True)),
            excluir_ambiguos=bool(dados.get('excluir_ambiguos', False)),
        )

    return jsonify(resultado)
