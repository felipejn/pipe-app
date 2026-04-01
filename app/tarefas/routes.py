from datetime import datetime, date, timedelta
from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user

from app import db
from app.tarefas import tarefas
from app.tarefas.models import Lista, Tarefa, TagTarefa
from app.tarefas.forms import ListaForm, TarefaForm


# ── Utilitários ────────────────────────────────────────────────────────────────

def _obter_lista_ou_404(lista_id):
    return Lista.query.filter_by(id=lista_id, user_id=current_user.id).first_or_404()


def _obter_tarefa_ou_404(tarefa_id):
    return Tarefa.query.filter_by(id=tarefa_id, user_id=current_user.id).first_or_404()


def _processar_tags(texto_tags):
    tags = []
    if not texto_tags:
        return tags
    nomes = [t.strip().lower() for t in texto_tags.split(',') if t.strip()]
    for nome in nomes:
        tag = TagTarefa.query.filter_by(nome=nome, user_id=current_user.id).first()
        if not tag:
            tag = TagTarefa(nome=nome, user_id=current_user.id)
            db.session.add(tag)
        tags.append(tag)
    return tags


def _estatisticas_utilizador():
    hoje = date.today()
    total      = Tarefa.query.filter_by(user_id=current_user.id).count()
    pendentes  = Tarefa.query.filter_by(user_id=current_user.id, concluida=False).count()
    concluidas = Tarefa.query.filter_by(user_id=current_user.id, concluida=True).count()
    atraso = Tarefa.query.filter(
        Tarefa.user_id == current_user.id,
        Tarefa.concluida == False,       # noqa: E712
        Tarefa.data_limite != None,      # noqa: E711
        Tarefa.data_limite < hoje,
    ).count()
    return dict(total=total, pendentes=pendentes, concluidas=concluidas, atraso=atraso)


# ── Página principal ────────────────────────────────────────────────────────────

@tarefas.route('/')
@login_required
def index():
    listas = Lista.query.filter_by(user_id=current_user.id).order_by(Lista.ordem, Lista.data_criacao).all()

    # "todas" é uma vista especial — não corresponde a uma Lista real
    # Por defeito (sem parâmetro) abre em "todas"
    lista_param = request.args.get('lista', 'todas')
    mostrar_todas = (lista_param == 'todas')

    lista_activa = None
    if not mostrar_todas:
        lista_id = int(lista_param) if lista_param.isdigit() else None
        if lista_id:
            lista_activa = Lista.query.filter_by(id=lista_id, user_id=current_user.id).first()
        if not lista_activa and listas:
            # Fallback para "todas" se o id não for válido
            mostrar_todas = True

    filtro = request.args.get('filtro', 'todas')
    busca  = request.args.get('busca', '').strip()
    hoje   = date.today()

    # Base da query — todas as listas ou lista activa
    if mostrar_todas:
        q = Tarefa.query.filter_by(user_id=current_user.id)
    elif lista_activa:
        q = Tarefa.query.filter_by(lista_id=lista_activa.id, user_id=current_user.id)
    else:
        q = Tarefa.query.filter_by(user_id=current_user.id).filter(False)  # vazio

    # Filtros de período/prioridade
    if filtro == 'hoje':
        q = q.filter(Tarefa.data_limite == hoje, Tarefa.concluida == False)  # noqa
    elif filtro == 'semana':
        fim_semana = hoje + timedelta(days=7)
        q = q.filter(Tarefa.data_limite <= fim_semana, Tarefa.concluida == False)  # noqa
    elif filtro == 'alta':
        q = q.filter_by(prioridade='alta', concluida=False)
    elif filtro == 'concluidas':
        q = q.filter_by(concluida=True)

    # Pesquisa por texto (título) ou tag
    if busca:
        tags_encontradas = TagTarefa.query.filter(
            TagTarefa.user_id == current_user.id,
            TagTarefa.nome.ilike(f'%{busca}%'),
        ).all()
        ids_tags = [t.id for t in tags_encontradas]

        from sqlalchemy import or_
        from app.tarefas.models import tarefa_tags as tabela_assoc
        ids_por_tag = db.session.query(tabela_assoc.c.tarefa_id).filter(
            tabela_assoc.c.tag_id.in_(ids_tags)
        ).subquery() if ids_tags else None

        if ids_por_tag is not None:
            q = q.filter(or_(
                Tarefa.texto.ilike(f'%{busca}%'),
                Tarefa.id.in_(ids_por_tag),
            ))
        else:
            q = q.filter(Tarefa.texto.ilike(f'%{busca}%'))

    # Ordenação: pendentes primeiro, depois por data limite (nulls no fim), depois prioridade
    q = q.order_by(
        Tarefa.concluida.asc(),
        Tarefa.data_limite.asc().nullslast(),
        Tarefa.prioridade.desc(),
    )
    tarefas_lista = q.all()

    form_lista  = ListaForm()
    form_tarefa = TarefaForm()
    stats       = _estatisticas_utilizador()

    return render_template(
        'tarefas/index.html',
        listas=listas,
        lista_activa=lista_activa,
        mostrar_todas=mostrar_todas,
        tarefas_lista=tarefas_lista,
        filtro=filtro,
        busca=busca,
        form_lista=form_lista,
        form_tarefa=form_tarefa,
        stats=stats,
        hoje=hoje,
    )


# ── Listas ─────────────────────────────────────────────────────────────────────

@tarefas.route('/listas/criar', methods=['POST'])
@login_required
def criar_lista():
    form = ListaForm()
    if form.validate_on_submit():
        nova = Lista(
            nome=form.nome.data.strip(),
            icone=form.icone.data,
            user_id=current_user.id,
        )
        db.session.add(nova)
        db.session.commit()
        flash(f'Lista "{nova.nome}" criada.', 'sucesso')
        return redirect(url_for('tarefas.index', lista=nova.id))
    flash('Erro ao criar lista.', 'erro')
    return redirect(url_for('tarefas.index'))


@tarefas.route('/listas/<int:lista_id>/apagar', methods=['POST'])
@login_required
def apagar_lista(lista_id):
    lista = _obter_lista_ou_404(lista_id)
    nome  = lista.nome
    db.session.delete(lista)
    db.session.commit()
    flash(f'Lista "{nome}" e todas as suas tarefas foram apagadas.', 'sucesso')
    return redirect(url_for('tarefas.index'))


# ── Tarefas ────────────────────────────────────────────────────────────────────

@tarefas.route('/criar', methods=['POST'])
@login_required
def criar_tarefa():
    form     = TarefaForm()
    lista_id = request.form.get('lista_id', type=int)

    if not lista_id:
        flash('Selecciona uma lista para adicionar a tarefa.', 'erro')
        return redirect(url_for('tarefas.index'))

    lista = _obter_lista_ou_404(lista_id)

    if form.validate_on_submit():
        nova = Tarefa(
            texto=form.texto.data.strip(),
            prioridade=form.prioridade.data,
            data_limite=form.data_limite.data,
            notas=form.notas.data.strip() if form.notas.data else None,
            lista_id=lista.id,
            user_id=current_user.id,
        )
        nova.tags = _processar_tags(form.tags.data)
        db.session.add(nova)
        db.session.commit()
        flash('Tarefa adicionada.', 'sucesso')
    else:
        flash('Erro ao criar tarefa. Verifica os campos.', 'erro')

    return redirect(url_for('tarefas.index', lista=lista_id))


@tarefas.route('/nova', methods=['GET', 'POST'])
@login_required
def nova_tarefa():
    """Formulário de criação de tarefa com todos os detalhes."""
    lista_id = request.args.get('lista', type=int) or request.form.get('lista_id', type=int)

    if not lista_id:
        flash('Selecciona uma lista primeiro.', 'erro')
        return redirect(url_for('tarefas.index'))

    lista = _obter_lista_ou_404(lista_id)
    form  = TarefaForm()

    if request.method == 'GET':
        form.lista_id.data = str(lista_id)
        # Pré-preencher texto se veio do input rápido via query string
        texto_inicial = request.args.get('texto', '').strip()
        if texto_inicial:
            form.texto.data = texto_inicial

    if form.validate_on_submit():
        nova = Tarefa(
            texto=form.texto.data.strip(),
            prioridade=form.prioridade.data,
            data_limite=form.data_limite.data,
            notas=form.notas.data.strip() if form.notas.data else None,
            lista_id=lista.id,
            user_id=current_user.id,
        )
        nova.tags = _processar_tags(form.tags.data)
        db.session.add(nova)
        db.session.commit()
        flash('Tarefa adicionada.', 'sucesso')
        return redirect(url_for('tarefas.index', lista=lista_id))

    listas       = Lista.query.filter_by(user_id=current_user.id).order_by(Lista.ordem).all()
    tarefa_vazia = Tarefa(lista_id=lista_id)
    return render_template('tarefas/editar.html', form=form, tarefa=tarefa_vazia, listas=listas)


@tarefas.route('/<int:tarefa_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_tarefa(tarefa_id):
    """Formulário de edição de tarefa existente."""
    tarefa = _obter_tarefa_ou_404(tarefa_id)
    form   = TarefaForm(obj=tarefa)

    if request.method == 'GET':
        form.tags.data     = ', '.join(t.nome for t in tarefa.tags)
        form.lista_id.data = str(tarefa.lista_id)

    if form.validate_on_submit():
        novo_lista_id = request.form.get('lista_id', type=int) or tarefa.lista_id
        _obter_lista_ou_404(novo_lista_id)

        tarefa.texto       = form.texto.data.strip()
        tarefa.prioridade  = form.prioridade.data
        tarefa.data_limite = form.data_limite.data
        tarefa.notas       = form.notas.data.strip() if form.notas.data else None
        tarefa.lista_id    = novo_lista_id
        tarefa.tags        = _processar_tags(form.tags.data)
        # Se o prazo mudou, resetar notificação para voltar a avisar
        tarefa.notificada_em = None

        db.session.commit()
        flash('Tarefa actualizada.', 'sucesso')
        return redirect(url_for('tarefas.index', lista=tarefa.lista_id))

    listas = Lista.query.filter_by(user_id=current_user.id).order_by(Lista.ordem).all()
    return render_template('tarefas/editar.html', form=form, tarefa=tarefa, listas=listas)


@tarefas.route('/<int:tarefa_id>/apagar', methods=['POST'])
@login_required
def apagar_tarefa(tarefa_id):
    tarefa   = _obter_tarefa_ou_404(tarefa_id)
    lista_id = tarefa.lista_id
    db.session.delete(tarefa)
    db.session.commit()
    flash('Tarefa apagada.', 'sucesso')
    return redirect(url_for('tarefas.index', lista=lista_id))


@tarefas.route('/<int:tarefa_id>/toggle', methods=['POST'])
@login_required
def toggle_tarefa(tarefa_id):
    """Alterna o estado concluída/pendente — responde sempre em JSON."""
    tarefa = _obter_tarefa_ou_404(tarefa_id)
    tarefa.concluida       = not tarefa.concluida
    tarefa.data_conclusao  = datetime.utcnow() if tarefa.concluida else None
    # Ao concluir, limpar notificação pendente; ao reabrir, resetar
    if tarefa.concluida:
        tarefa.notificada_em = None
    db.session.commit()

    return jsonify(ok=True, concluida=tarefa.concluida, tarefa_id=tarefa_id)


# ── Adição rápida (AJAX) ───────────────────────────────────────────────────────

@tarefas.route('/rapida', methods=['POST'])
@login_required
def adicao_rapida():
    dados    = request.get_json(silent=True) or {}
    texto    = (dados.get('texto') or '').strip()
    lista_id = dados.get('lista_id')

    if not texto:
        return jsonify(ok=False, erro='Texto vazio'), 400
    if not lista_id:
        return jsonify(ok=False, erro='Lista não especificada'), 400

    lista = Lista.query.filter_by(id=lista_id, user_id=current_user.id).first()
    if not lista:
        return jsonify(ok=False, erro='Lista inválida'), 403

    nova = Tarefa(
        texto=texto,
        prioridade='media',
        lista_id=lista.id,
        user_id=current_user.id,
    )
    db.session.add(nova)
    db.session.commit()

    return jsonify(
        ok=True,
        id=nova.id,
        texto=nova.texto,
        prioridade=nova.prioridade,
        data_criacao=nova.data_criacao.strftime('%d/%m/%Y'),
    )
