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
EXTENSOES_VALIDAS = {'.heic'}
MIMETYPES_VALIDOS = {'image/heic', 'image/heif'}


def validar_ficheiro(file):
    """Valida extensão, mimetype e tamanho de um ficheiro HEIC."""
    erros = []

    # Validar nome/extensão
    nome = file.filename.lower() if file.filename else ''
    if not any(nome.endswith(ext) for ext in EXTENSOES_VALIDAS):
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
    # Ler conteúdo do ficheiro
    conteudo = file.read()

    # Abrir com Pillow (gracias ao pillow_heif opener)
    imagem = Image.open(io.BytesIO(conteudo))

    # Converter para RGB (HEIC pode ter espaços de cor diferentes)
    imagem_rgb = imagem.convert('RGB')

    # Guardar como JPEG em memória
    output = io.BytesIO()
    imagem_rgb.save(output, format='JPEG', quality=85)
    output.seek(0)

    return output


def obter_nome_jpg(nome_original):
    """Converte nome.heic para nome.jpg."""
    if nome_original and nome_original.lower().endswith('.heic'):
        return nome_original[:-5] + '.jpg'
    return nome_original + '.jpg'


@bp.route('/')
@login_required
def index():
    """Página principal do módulo Conversões."""
    # Obter últimas 10 conversões do utilizador
    historico = Conversao.query.filter_by(user_id=current_user.id) \
        .order_by(Conversao.convertido_em.desc()) \
        .limit(10).all()

    return render_template('conversoes/index.html', historico=historico)


@bp.route('/api/converter', methods=['POST'])
@login_required
def api_converter():
    """API para converter ficheiros HEIC para JPG."""
    # Verificar se há ficheiros no request
    if 'ficheiros' not in request.files:
        return jsonify({'erro': 'Nenhum ficheiro enviado'}), 400

    ficheiros = request.files.getlist('ficheiros')

    # Verificar se há ficheiros selecionados
    if not ficheiros or all(f.filename == '' for f in ficheiros):
        return jsonify({'erro': 'Nenhum ficheiro selecionado'}), 400

    # Verificar limite de ficheiros
    if len(ficheiros) > MAX_FICHEIROS:
        return jsonify({'erro': f'Máximo de {MAX_FICHEIROS} ficheiros por conversão'}), 400

    # Validar cada ficheiro
    todos_erros = []
    for ficheiro in ficheiros:
        erros = validar_ficheiro(ficheiro)
        todos_erros.extend(erros)

    if todos_erros:
        return jsonify({'erro': 'Ficheiros inválidos', 'detalhes': todos_erros}), 400

    # Converter ficheiros
    ficheiros_convertidos = []
    tamanho_total = 0

    try:
        for ficheiro in ficheiros:
            # Reset stream para início antes de converter
            ficheiro.seek(0)

            jpg_bytes = converter_heic_para_jpg(ficheiro)
            nome_jpg = obter_nome_jpg(ficheiro.filename)

            ficheiros_convertidos.append({
                'nome': nome_jpg,
                'dados': jpg_bytes
            })

            # Calcular tamanho total
            tamanho_total += len(jpg_bytes.getvalue())
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
        # 1 ficheiro → enviar JPG directo
        ficheiro = ficheiros_convertidos[0]
        return send_file(
            ficheiro['dados'],
            mimetype='image/jpeg',
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
        nome_zip = f'conversao_heic_{timestamp}.zip'

        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=nome_zip
        )