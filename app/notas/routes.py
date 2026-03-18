from datetime import datetime
from flask import render_template, redirect, url_for, request, jsonify, abort
from flask_login import login_required, current_user
from app import db
from app.notas import notas
from app.notas.models import Nota, ItemChecklist, EtiquetaNota


# ---------------------------------------------------------------------------
# Página principal — grelha de notas
# ---------------------------------------------------------------------------

@notas.route('/')
@login_required
def index():
    busca    = request.args.get('busca', '').strip()
    etiqueta = request.args.get('etiqueta', '').strip()
    arquivo  = request.args.get('arquivo', '0') == '1'

    q = Nota.query.filter_by(user_id=current_user.id, arquivada=arquivo)

    if busca:
        q = q.filter(
            db.or_(
                Nota.titulo.ilike(f'%{busca}%'),
                Nota.corpo.ilike(f'%{busca}%'),
            )
        )

    if etiqueta:
        q = q.join(Nota.etiquetas).filter(EtiquetaNota.nome == etiqueta)

    notas_lista = q.order_by(Nota.fixada.desc(), Nota.data_edicao.desc()).all()

    fixadas   = [n for n in notas_lista if n.fixada]  if not arquivo else []
    restantes = [n for n in notas_lista if not n.fixada] if not arquivo else notas_lista

    etiquetas_user = EtiquetaNota.query.filter_by(user_id=current_user.id)\
                                       .order_by(EtiquetaNota.nome).all()

    return render_template(
        'notas/index.html',
        fixadas=fixadas,
        restantes=restantes,
        etiquetas=etiquetas_user,
        busca=busca,
        etiqueta_activa=etiqueta,
        arquivo=arquivo,
    )


# ---------------------------------------------------------------------------
# Criar nota (inline via AJAX)
# ---------------------------------------------------------------------------

@notas.route('/criar', methods=['POST'])
@login_required
def criar():
    dados = request.get_json(silent=True) or {}

    tipo   = dados.get('tipo', Nota.TIPO_TEXTO)
    titulo = (dados.get('titulo') or '').strip()
    corpo  = (dados.get('corpo')  or '').strip()
    itens  = dados.get('itens', [])
    cor    = dados.get('cor', 'padrao')

    if tipo not in Nota.TIPOS:
        tipo = Nota.TIPO_TEXTO
    if cor not in Nota.CORES:
        cor = 'padrao'

    nota = Nota(
        titulo=titulo or None,
        corpo=corpo or None,
        tipo=tipo,
        cor=cor,
        user_id=current_user.id,
    )
    db.session.add(nota)
    db.session.flush()

    if tipo == Nota.TIPO_CHECKLIST:
        for i, texto_item in enumerate(itens):
            texto_item = texto_item.strip()
            if texto_item:
                db.session.add(ItemChecklist(texto=texto_item, ordem=i, nota_id=nota.id))

    db.session.commit()
    return jsonify({'ok': True, 'id': nota.id, 'cor': nota.cor})


# ---------------------------------------------------------------------------
# Ver / editar nota (página completa)
# ---------------------------------------------------------------------------

@notas.route('/<int:nota_id>', methods=['GET', 'POST'])
@login_required
def editar(nota_id):
    nota = Nota.query.filter_by(id=nota_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        nota.titulo = request.form.get('titulo', '').strip() or None
        nota.corpo  = request.form.get('corpo',  '').strip() or None
        nota.cor    = request.form.get('cor', 'padrao')
        nota.data_edicao = datetime.utcnow()

        nomes_etiquetas = [e.strip().lower() for e in
                           request.form.get('etiquetas', '').split(',') if e.strip()]
        novas_etiquetas = []
        for nome in nomes_etiquetas:
            et = EtiquetaNota.query.filter_by(nome=nome, user_id=current_user.id).first()
            if not et:
                et = EtiquetaNota(nome=nome, user_id=current_user.id)
                db.session.add(et)
            novas_etiquetas.append(et)
        nota.etiquetas = novas_etiquetas

        if nota.tipo == Nota.TIPO_CHECKLIST:
            ItemChecklist.query.filter_by(nota_id=nota.id).delete()
            textos = request.form.getlist('item_texto[]')
            feitos = request.form.getlist('item_feito[]')
            feitos_set = set(feitos)
            for i, texto in enumerate(textos):
                texto = texto.strip()
                if texto:
                    db.session.add(ItemChecklist(
                        texto=texto,
                        feito=(str(i) in feitos_set),
                        ordem=i,
                        nota_id=nota.id,
                    ))

        db.session.commit()
        return redirect(url_for('notas.index'))

    etiquetas_user = EtiquetaNota.query.filter_by(user_id=current_user.id)\
                                       .order_by(EtiquetaNota.nome).all()
    return render_template('notas/editar.html', nota=nota, etiquetas_todas=etiquetas_user,
                           cores=Nota.CORES)


# ---------------------------------------------------------------------------
# Acções rápidas via AJAX
# ---------------------------------------------------------------------------

@notas.route('/<int:nota_id>/accao', methods=['POST'])
@login_required
def accao(nota_id):
    nota = Nota.query.filter_by(id=nota_id, user_id=current_user.id).first_or_404()
    dados = request.get_json(silent=True) or {}
    accao = dados.get('accao')

    if accao == 'fixar':
        nota.fixada = not nota.fixada
    elif accao == 'arquivar':
        nota.arquivada = not nota.arquivada
        nota.fixada    = False
    elif accao == 'cor':
        cor = dados.get('cor', 'padrao')
        if cor in Nota.CORES:
            nota.cor = cor
    elif accao == 'toggle_item':
        item_id = dados.get('item_id')
        item = ItemChecklist.query.filter_by(id=item_id, nota_id=nota.id).first_or_404()
        item.feito = not item.feito
    else:
        abort(400)

    nota.data_edicao = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'fixada': nota.fixada, 'arquivada': nota.arquivada})


# ---------------------------------------------------------------------------
# Apagar nota
# ---------------------------------------------------------------------------

@notas.route('/<int:nota_id>/apagar', methods=['POST'])
@login_required
def apagar(nota_id):
    nota = Nota.query.filter_by(id=nota_id, user_id=current_user.id).first_or_404()
    db.session.delete(nota)
    db.session.commit()
    return jsonify({'ok': True})
