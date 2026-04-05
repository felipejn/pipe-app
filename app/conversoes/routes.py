import io
import zipfile
from datetime import datetime, timezone

import pillow_heif
from flask import render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from PIL import Image

from app import db
from app.conversoes import bp
from app.conversoes.models import Conversao

# Registar opener HEIC para Pillow
pillow_heif.register_heif_opener()

# Constantes
MAX_FICHEIROS = 20
MAX_TAMANHO_MB = 10
MAX_TAMANHO_BYTES = MAX_TAMANHO_MB * 1024 * 1024
EXTENSOES_HEIC = {'.heic'}
MIMETYPES_HEIC = {'image/heic', 'image/heif'}
EXTENSOES_IMG = {'.png', '.jpg', '.jpeg'}


def validar_ficheiro(file, tipo):
    """Valida extensão e tamanho de um ficheiro."""
    erros = []

    # Validar nome/extensão
    nome = file.filename.lower() if file.filename else ''
    if tipo == 'ico':
        if not any(nome.endswith(ext) for ext in EXTENSOES_IMG):
            exts = ', '.join(EXTENSOES_IMG)
            erros.append(f'"{file.filename}": extensão não suportada (apenas {exts})')
    else:
        if not any(nome.endswith(ext) for ext in EXTENSOES_HEIC):
            erros.append(f'"{file.filename}": extensão não suportada (apenas .heic)')

    # Validar tamanho sem consumir o stream
    posicao_atual = file.tell()
    file.seek(0, 2)  # Ir para o fim do ficheiro
    tamanho = file.tell()
    file.seek(posicao_atual)  # Voltar à posição original

    if tamanho > MAX_TAMANHO_BYTES:
        tamanho_mb = tamanho / (1024 * 1024)
        erros.append(f'"{file.filename}": {tamanho_mb:.1f}MB (máximo {MAX_TAMANHO_MB}MB)')

    return erros


def converter_heic_para_jpg(file):
    """Converte um ficheiro HEIC para JPG em memória. Retorna BytesIO."""
    conteudo = file.read()
    imagem = Image.open(io.BytesIO(conteudo))
    imagem_rgb = imagem.convert('RGB')
    output = io.BytesIO()
    imagem_rgb.save(output, format='JPEG', quality=85)
    output.seek(0)
    return output


def converter_img_para_ico(file, tamanho=64):
    """Converte PNG/JPG para ICO em memória. Retorna BytesIO."""
    conteudo = file.read()
    imagem = Image.open(io.BytesIO(conteudo))
    imagem = imagem.convert('RGBA')
    imagem_red = imagem.resize((tamanho, tamanho), Image.LANCZOS)
    output = io.BytesIO()
    imagem_red.save(output, format='ICO', sizes=[(tamanho, tamanho)])
    output.seek(0)
    return output


def obter_nome_saida(nome_original, ext_saida):
    """Obtem nome do ficheiro de saída."""
    base = nome_original.rsplit('.', 1)[0] if nome_original and '.' in nome_original else nome_original
    return f'{base}{ext_saida}'


@bp.route('/')
@login_required
def index():
    """Página principal do módulo Conversões."""
    historico = Conversao.query.filter_by(user_id=current_user.id) \
        .order_by(Conversao.convertido_em.desc()) \
        .limit(10).all()
    return render_template('conversoes/index.html', historico=historico)


@bp.route('/api/converter', methods=['POST'])
@login_required
def api_converter():
    """API para converter ficheiros."""
    if 'ficheiros' not in request.files:
        return jsonify({'erro': 'Nenhum ficheiro enviado'}), 400

    ficheiros = request.files.getlist('ficheiros')
    tipo = request.form.get('tipo', 'heic')  # 'heic' ou 'ico'

    ICO_TAMANHOS_VALIDOS = [16, 32, 48, 64, 128, 256]
    try:
        tamanho_ico = int(request.form.get('tamanho', 64))
        if tamanho_ico not in ICO_TAMANHOS_VALIDOS:
            tamanho_ico = 64
    except (ValueError, TypeError):
        tamanho_ico = 64

    # Verificar se há ficheiros selecionados
    if not ficheiros or all(f.filename == '' for f in ficheiros):
        return jsonify({'erro': 'Nenhum ficheiro selecionado'}), 400

    # Verificar limite de ficheiros
    if len(ficheiros) > MAX_FICHEIROS:
        return jsonify({'erro': f'Máximo de {MAX_FICHEIROS} ficheiros por conversão'}), 400

    # Validar cada ficheiro
    todos_erros = []
    for ficheiro in ficheiros:
        erros = validar_ficheiro(ficheiro, tipo)
        todos_erros.extend(erros)

    if todos_erros:
        return jsonify({'erro': 'Ficheiros inválidos', 'detalhes': todos_erros}), 400

    # Converter ficheiros
    ficheiros_convertidos = []
    tamanho_total = 0

    try:
        for ficheiro in ficheiros:
            ficheiro.seek(0)

            if tipo == 'ico':
                bytes_saida = converter_img_para_ico(ficheiro, tamanho_ico)
                nome_saida = obter_nome_saida(ficheiro.filename, '.ico')
            else:
                bytes_saida = converter_heic_para_jpg(ficheiro)
                nome_saida = obter_nome_saida(ficheiro.filename, '.jpg')

            ficheiros_convertidos.append({
                'nome': nome_saida,
                'dados': bytes_saida
            })

            tamanho_total += len(bytes_saida.getvalue())
    except Exception as e:
        return jsonify({'erro': f'Erro na conversão: {str(e)}'}), 500

    # Guardar metadados no histórico
    tamanho_total_kb = tamanho_total // 1024
    conversao = Conversao(
        user_id=current_user.id,
        num_ficheiros=len(ficheiros_convertidos),
        tamanho_total_kb=tamanho_total_kb,
        convertido_em=datetime.now(timezone.utc)
    )
    db.session.add(conversao)
    db.session.commit()

    # Preparar resposta
    if len(ficheiros_convertidos) == 1:
        ficheiro = ficheiros_convertidos[0]
        mimetype_saida = 'image/x-icon' if tipo == 'ico' else 'image/jpeg'
        return send_file(
            ficheiro['dados'],
            mimetype=mimetype_saida,
            as_attachment=True,
            download_name=ficheiro['nome']
        )
    else:
        # 2+ ficheiros → criar ZIP em memória
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for ficheiro in ficheiros_convertidos:
                zip_file.writestr(ficheiro['nome'], ficheiro['dados'].getvalue())

        zip_buffer.seek(0)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefixo = 'conversao_ico' if tipo == 'ico' else 'conversao_heic'
        nome_zip = f'{prefixo}_{timestamp}.zip'

        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=nome_zip
        )
