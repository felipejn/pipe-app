import base64
import time
from datetime import datetime
from flask import render_template, request, jsonify, session, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import generate_csrf
from app import db
from app.passwords import bp
from app.passwords.generator import gerar_password, gerar_passphrase, gerar_pin
from app.passwords.models import CofreConfig, CofrePassword, extrair_dominio
from app.passwords.crypto import (
    gerar_salt, derivar_chave, hash_password_mestre,
    verificar_password_mestre, cifrar, decifrar,
    bytes_para_b64
)


def _kdf_iterations():
    """Iterações PBKDF2 configuradas (COFRE_KDF_ITERATIONS)."""
    return current_app.config.get('COFRE_KDF_ITERATIONS', 600000)


def _obter_chave_cofre():
    """Devolve a chave do cofre da sessão server-side ou None se bloqueado/expirado.

    A expiração bloqueia APENAS o cofre: usa-se `session.pop` das chaves do
    cofre e nunca `session.clear()`, que apagaria também o `_user_id` do
    Flask-Login e deslogava o utilizador a meio do trabalho.
    """
    chave_b64 = session.get('cofre_chave')
    chave_ts = session.get('cofre_chave_ts')
    if not chave_b64 or not chave_ts:
        return None
    timeout = current_app.config.get('COFRE_SESSION_TIMEOUT', 900)
    if time.time() - chave_ts > timeout:
        session.pop('cofre_chave', None)
        session.pop('cofre_chave_ts', None)
        return None
    try:
        return base64.b64decode(chave_b64)
    except Exception:
        return None


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


# ─── Estado do cofre ────────────────────────────────────────────────────────

@bp.route('/api/cofre/estado', methods=['GET'])
@login_required
def api_estado():
    cofre = CofreConfig.query.filter_by(user_id=current_user.id).first()
    chave = _obter_chave_cofre()
    return jsonify({
        'activado': cofre is not None and cofre.ativo,
        'desbloqueado': chave is not None,
    })


# ─── Activar cofre ──────────────────────────────────────────────────────────

@bp.route('/api/cofre/activar', methods=['POST'])
@login_required
def api_activar():
    dados = request.get_json(force=True)
    password = dados.get('password', '')
    confirmacao = dados.get('confirmacao', '')

    if len(password) < 8:
        return jsonify({'erro': 'A password mestra deve ter pelo menos 8 caracteres.'}), 400
    if password != confirmacao:
        return jsonify({'erro': 'As passwords não coincidem.'}), 400

    iterations = _kdf_iterations()
    salt = gerar_salt()
    chave = derivar_chave(password, salt, iterations)
    pw_hash = hash_password_mestre(password)

    cofre = CofreConfig(
        user_id=current_user.id,
        master_pw_hash=pw_hash,
        salt=salt,
        kdf_iterations=iterations,
        ativo=True,
    )
    db.session.add(cofre)
    db.session.commit()

    session['cofre_chave'] = bytes_para_b64(chave)
    session['cofre_chave_ts'] = time.time()

    return jsonify({'mensagem': 'Cofre activado com sucesso.'})


# ─── Desbloquear cofre ──────────────────────────────────────────────────────

@bp.route('/api/cofre/desbloquear', methods=['POST'])
@login_required
def api_desbloquear():
    dados = request.get_json(force=True)
    password = dados.get('password', '')

    cofre = CofreConfig.query.filter_by(user_id=current_user.id).first()
    if not cofre or not cofre.ativo:
        return jsonify({'erro': 'Cofre não activado.'}), 404

    if not verificar_password_mestre(password, cofre.master_pw_hash):
        return jsonify({'erro': 'Password mestra incorreta.'}), 401

    # `or _kdf_iterations()`: cofres antigos podem ter kdf_iterations NULL
    chave = derivar_chave(password, cofre.salt, cofre.kdf_iterations or _kdf_iterations())
    session['cofre_chave'] = bytes_para_b64(chave)
    session['cofre_chave_ts'] = time.time()

    return jsonify({'mensagem': 'Cofre desbloqueado.'})


# ─── Bloquear cofre ─────────────────────────────────────────────────────────

@bp.route('/api/cofre/bloquear', methods=['POST'])
@login_required
def api_bloquear():
    session.pop('cofre_chave', None)
    session.pop('cofre_chave_ts', None)
    return jsonify({'mensagem': 'Cofre bloqueado.'})


# ─── Alterar password mestra ────────────────────────────────────────────────

@bp.route('/api/cofre/alterar-password', methods=['POST'])
@login_required
def api_alterar_password():
    dados = request.get_json(force=True)
    password_actual = dados.get('password_actual', '')
    nova_password = dados.get('nova_password', '')
    confirmacao = dados.get('confirmacao', '')

    if len(nova_password) < 8:
        return jsonify({'erro': 'A nova password deve ter pelo menos 8 caracteres.'}), 400
    if nova_password != confirmacao:
        return jsonify({'erro': 'As passwords não coincidem.'}), 400

    cofre = CofreConfig.query.filter_by(user_id=current_user.id).first()
    if not cofre or not cofre.ativo:
        return jsonify({'erro': 'Cofre não activado.'}), 404

    if not verificar_password_mestre(password_actual, cofre.master_pw_hash):
        return jsonify({'erro': 'Password actual incorreta.'}), 401

    iterations = _kdf_iterations()
    nova_salt = gerar_salt()
    nova_chave = derivar_chave(nova_password, nova_salt, iterations)
    nova_hash = hash_password_mestre(nova_password)

    # Transacção atómica: decifrar tudo com chave antiga, re-cifrar com nova
    chave_antiga = derivar_chave(
        password_actual, cofre.salt, cofre.kdf_iterations or iterations
    )

    entradas = CofrePassword.query.filter_by(user_id=current_user.id).all()
    try:
        for entrada in entradas:
            texto_plano = decifrar(chave_antiga, bytes(entrada.password_cifrada), bytes(entrada.iv), bytes(entrada.tag))
            ct, iv, tag = cifrar(nova_chave, texto_plano)
            entrada.password_cifrada = ct
            entrada.iv = iv
            entrada.tag = tag

        cofre.master_pw_hash = nova_hash
        cofre.salt = nova_salt
        cofre.kdf_iterations = iterations
        db.session.commit()

        # Actualizar chave na sessão
        session['cofre_chave'] = bytes_para_b64(nova_chave)
        session['cofre_chave_ts'] = time.time()

        return jsonify({'mensagem': 'Password mestra alterada com sucesso.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao alterar password: {str(e)}'}), 500


# ─── Listar entradas ────────────────────────────────────────────────────────

@bp.route('/api/cofre/entradas', methods=['GET'])
@login_required
def api_listar_entradas():
    chave = _obter_chave_cofre()
    if not chave:
        return jsonify({'erro': 'Cofre bloqueado. Desbloqueie primeiro.'}), 401

    url_param = request.args.get('url')
    dominio_filtro = extrair_dominio(url_param) if url_param else None

    query = CofrePassword.query.filter_by(user_id=current_user.id)
    if dominio_filtro:
        query = query.filter_by(dominio=dominio_filtro)
    entradas = query.all()

    resultado = [e.para_dict(chave) for e in entradas]
    return jsonify(resultado)


# ─── Criar entrada ──────────────────────────────────────────────────────────

@bp.route('/api/cofre/entradas', methods=['POST'])
@login_required
def api_criar_entrada():
    chave = _obter_chave_cofre()
    if not chave:
        return jsonify({'erro': 'Cofre bloqueado.'}), 401

    dados = request.get_json(force=True)
    titulo = dados.get('titulo', '')
    url = dados.get('url', '')
    username = dados.get('username', '')
    password = dados.get('password', '')
    notas = dados.get('notas', '')
    favorito = dados.get('favorito', False)

    dominio = extrair_dominio(url)

    # Verificar duplicado (dominio + username)
    existente = CofrePassword.query.filter_by(
        user_id=current_user.id, dominio=dominio, username=username
    ).first()
    if existente:
        # O `id` vai na resposta para a extensão poder oferecer "actualizar a
        # entrada existente" em vez de falhar sem alternativa (era o que
        # acontecia: o popup só mostrava o erro e a captura ficava pendente).
        return jsonify({
            'erro': 'Já existe uma entrada com o mesmo domínio e username.',
            'id': existente.id,
            'dominio': existente.dominio,
            'username': existente.username,
        }), 409

    ct, iv, tag = cifrar(chave, password)
    entrada = CofrePassword(
        user_id=current_user.id,
        titulo=titulo,
        url=url,
        dominio=dominio,
        username=username,
        password_cifrada=ct,
        iv=iv,
        tag=tag,
        notas=notas,
        favorito=favorito,
    )
    db.session.add(entrada)
    db.session.commit()

    return jsonify({'mensagem': 'Entrada criada.', 'id': entrada.id})


# ─── Editar entrada ─────────────────────────────────────────────────────────

@bp.route('/api/cofre/entradas/<int:id>', methods=['PUT'])
@login_required
def api_editar_entrada(id):
    chave = _obter_chave_cofre()
    if not chave:
        return jsonify({'erro': 'Cofre bloqueado.'}), 401

    entrada = CofrePassword.query.filter_by(id=id, user_id=current_user.id).first()
    if not entrada:
        return jsonify({'erro': 'Entrada não encontrada.'}), 404

    dados = request.get_json(force=True)
    entrada.titulo = dados.get('titulo', entrada.titulo)
    entrada.url = dados.get('url', entrada.url)
    # O domínio é sempre derivado da URL (única fonte de verdade) — sem isto,
    # editar a URL deixava o domínio antigo e o lookup da extensão falhava.
    entrada.dominio = extrair_dominio(entrada.url)
    entrada.username = dados.get('username', entrada.username)
    entrada.notas = dados.get('notas', entrada.notas)
    entrada.favorito = dados.get('favorito', entrada.favorito)

    if 'password' in dados and dados['password']:
        ct, iv, tag = cifrar(chave, dados['password'])
        entrada.password_cifrada = ct
        entrada.iv = iv
        entrada.tag = tag

    entrada.data_atualizacao = datetime.utcnow()
    db.session.commit()

    return jsonify({'mensagem': 'Entrada actualizada.'})


# ─── Apagar entrada ─────────────────────────────────────────────────────────

@bp.route('/api/cofre/entradas/<int:id>', methods=['DELETE'])
@login_required
def api_apagar_entrada(id):
    entrada = CofrePassword.query.filter_by(id=id, user_id=current_user.id).first()
    if not entrada:
        return jsonify({'erro': 'Entrada não encontrada.'}), 404

    db.session.delete(entrada)
    db.session.commit()

    return jsonify({'mensagem': 'Entrada apagada.'})


# ─── Importar CSV ───────────────────────────────────────────────────────────

@bp.route('/api/cofre/importar-csv', methods=['POST'])
@login_required
def api_importar_csv():
    chave = _obter_chave_cofre()
    if not chave:
        return jsonify({'erro': 'Cofre bloqueado.'}), 401

    ficheiro = request.files.get('ficheiro')
    if not ficheiro:
        return jsonify({'erro': 'Nenhum ficheiro fornecido.'}), 400

    import csv
    import io

    stream = io.StringIO(ficheiro.read().decode('utf-8'))
    reader = csv.DictReader(stream)

    importadas = 0
    duplicadas = 0
    erros = []

    for linha in reader:
        try:
            url = linha.get('url', '')
            username = linha.get('username', '')
            password = linha.get('password', '')
            titulo = linha.get('name', '')

            dominio = extrair_dominio(url)

            # Verificar duplicado
            existente = CofrePassword.query.filter_by(
                user_id=current_user.id, dominio=dominio, username=username
            ).first()
            if existente:
                duplicadas += 1
                continue

            ct, iv, tag = cifrar(chave, password)
            entrada = CofrePassword(
                user_id=current_user.id,
                titulo=titulo,
                url=url,
                dominio=dominio,
                username=username,
                password_cifrada=ct,
                iv=iv,
                tag=tag,
            )
            db.session.add(entrada)
            importadas += 1
        except Exception as e:
            erros.append(str(e))

    db.session.commit()
    return jsonify({'importadas': importadas, 'duplicadas': duplicadas, 'erros': erros})


# ─── CSRF Token para a extensão e para o JS do cofre ────────────────────────

@bp.route('/api/csrf-token', methods=['GET'])
@login_required
def api_csrf_token():
    """Devolve o token CSRF da sessão actual, já assinado pelo Flask-WTF.

    IMPORTANTE: não usar `session['csrf_token']` — a sessão guarda o valor
    *cru* (hex digest) e o valor que o Flask-WTF valida no header
    `X-CSRFToken` é a versão *assinada* devolvida por `generate_csrf()`.
    Devolver o valor cru (ou '' no primeiro pedido da sessão) faz todos os
    POSTs falharem com "The CSRF token is missing/invalid".
    """
    return jsonify({'csrfToken': generate_csrf()})
