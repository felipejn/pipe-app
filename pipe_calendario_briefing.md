# Módulo Calendário — Plano de Implementação v1

## Âmbito da v1

### Incluído
- Vista Mensal (grelha 7×N, estilo Google Calendar)
- Vista Agenda (lista cronológica de eventos futuros)
- Modal único para criar e editar eventos
- Paleta de 11 cores com selector visual no modal
- Notificações de eventos do dia seguinte (via `pipe_tasks.py`)
- Integração na Loja de Módulos

### Adiado para versões futuras
- Vista Semanal
- Drag & drop para mover eventos (mover pelo modal de edição)
- Eventos recorrentes (DAILY, WEEKLY, MONTHLY, CUSTOM)
- Integração com o Assistente IA (`get_eventos`)
- Integração Google Calendar API (OAuth 2.0 por utilizador)

---

## Decisões técnicas

- **Fusos horários**: sem conversão UTC explícita na v1 — tudo tratado como hora local. O utilizador está em Lisboa, o comportamento é consistente desde que não se misturem timezones. Revisitar se surgir necessidade real.
- **Frontend**: vanilla JS inline no template — padrão PIPE. Sem bibliotecas externas.
- **Design**: reutiliza o design system existente (`pipe.css`). Acrescentar apenas as 11 variáveis de cor dos eventos (~20 linhas de CSS).
- **`forms.py`**: não criado — as rotas usam `request.get_json()`, padrão PIPE.

---

## Ficheiros a criar

### `app/calendario/__init__.py`
```python
from flask import Blueprint

calendario_bp = Blueprint('calendario', __name__)

from app.calendario import routes
```
> Nota: `template_folder` omitido — os templates em `app/templates/calendario/` são resolvidos automaticamente pelo Jinja2, padrão dos outros blueprints do PIPE.

---

### `app/calendario/models.py`
```python
from app.extensions import db
from datetime import datetime

class Evento(db.Model):
    __tablename__ = 'evento'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    titulo        = db.Column(db.String(200), nullable=False)
    descricao     = db.Column(db.Text, nullable=True)
    localizacao   = db.Column(db.String(300), nullable=True)
    data_inicio   = db.Column(db.DateTime, nullable=False)
    data_fim      = db.Column(db.DateTime, nullable=False)
    dia_inteiro   = db.Column(db.Boolean, default=False)
    cor           = db.Column(db.String(20), default='tomate')
    notificar     = db.Column(db.Boolean, default=True)
    notificado_em = db.Column(db.Date, nullable=True)
    criado_em     = db.Column(db.DateTime, default=datetime.utcnow)

    # Paleta de cores disponíveis:
    # tomate, flamingo, tangerina, banana, salvia, basil, peacock, mirtilo, lavanda, uva, grafite
```

---

### `app/calendario/routes.py`
```python
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.calendario import calendario_bp
from app.calendario.models import Evento
from app.extensions import db
from datetime import datetime

@calendario_bp.route('/')
@login_required
def index():
    return render_template('calendario/index.html')

@calendario_bp.route('/api/eventos')
@login_required
def api_eventos():
    inicio = request.args.get('inicio')
    fim    = request.args.get('fim')
    eventos = Evento.query.filter(
        Evento.user_id     == current_user.id,
        Evento.data_inicio <  datetime.fromisoformat(fim),    # corrigido: eventos que começam antes do fim
        Evento.data_fim    >  datetime.fromisoformat(inicio)  # corrigido: e terminam depois do início
    ).all()
    return jsonify([{
        'id':          e.id,
        'titulo':      e.titulo,
        'descricao':   e.descricao,
        'localizacao': e.localizacao,
        'data_inicio': e.data_inicio.isoformat(),
        'data_fim':    e.data_fim.isoformat(),
        'dia_inteiro': e.dia_inteiro,
        'cor':         e.cor,
        'notificar':   e.notificar
    } for e in eventos])

@calendario_bp.route('/api/eventos', methods=['POST'])
@login_required
def api_criar_evento():
    dados = request.get_json()
    # Validação: data_fim >= data_inicio
    inicio = datetime.fromisoformat(dados['data_inicio'])
    fim    = datetime.fromisoformat(dados['data_fim'])
    if fim < inicio:
        return jsonify({'erro': 'A data de fim não pode ser anterior à data de início.'}), 400
    evento = Evento(
        user_id     = current_user.id,
        titulo      = dados['titulo'],
        descricao   = dados.get('descricao'),
        localizacao = dados.get('localizacao'),
        data_inicio = inicio,
        data_fim    = fim,
        dia_inteiro = dados.get('dia_inteiro', False),
        cor         = dados.get('cor', 'tomate'),
        notificar   = dados.get('notificar', True)
    )
    db.session.add(evento)
    db.session.commit()
    return jsonify({'id': evento.id}), 201

@calendario_bp.route('/api/eventos/<int:id>', methods=['PUT'])
@login_required
def api_editar_evento(id):
    evento = Evento.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    dados  = request.get_json()
    inicio = datetime.fromisoformat(dados['data_inicio'])
    fim    = datetime.fromisoformat(dados['data_fim'])
    if fim < inicio:
        return jsonify({'erro': 'A data de fim não pode ser anterior à data de início.'}), 400
    evento.titulo      = dados.get('titulo', evento.titulo)
    evento.descricao   = dados.get('descricao', evento.descricao)
    evento.localizacao = dados.get('localizacao', evento.localizacao)
    evento.data_inicio = inicio
    evento.data_fim    = fim
    evento.dia_inteiro = dados.get('dia_inteiro', evento.dia_inteiro)
    evento.cor         = dados.get('cor', evento.cor)
    evento.notificar   = dados.get('notificar', evento.notificar)
    evento.notificado_em = None  # reset ao editar datas
    db.session.commit()
    return jsonify({'ok': True})

@calendario_bp.route('/api/eventos/<int:id>', methods=['DELETE'])
@login_required
def api_apagar_evento(id):
    evento = Evento.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(evento)
    db.session.commit()
    return jsonify({'ok': True})
```
> Nota: rota `/mover` removida da v1 — mover evento é feito pelo modal de edição.

---

## Alterações em ficheiros existentes

### `app/__init__.py`
```python
# Adicionar junto aos outros blueprints
from app.calendario import calendario_bp
app.register_blueprint(calendario_bp, url_prefix='/calendario')

# Garantir import do modelo antes de db.create_all()
from app.calendario.models import Evento
```

### `app/modulos/config.py`
```python
# Adicionar à lista MODULOS_DISPONIVEIS
{
    'slug':        'calendario',
    'nome':        'Calendário',
    'icone':       '📅',
    'url_endpoint': 'calendario.index',
    'descricao':   'Agenda pessoal com vistas mensal e de agenda.'
},
```

### `app/static/css/pipe.css`
```css
/* Cores de eventos do Calendário */
.evento-tomate    { background-color: #d32f2f; color: #fff; }
.evento-flamingo  { background-color: #e91e63; color: #fff; }
.evento-tangerina { background-color: #f4511e; color: #fff; }
.evento-banana    { background-color: #f6bf26; color: #1a1a1a; }
.evento-salvia    { background-color: #33b679; color: #fff; }
.evento-basil     { background-color: #0b8043; color: #fff; }
.evento-peacock   { background-color: #039be5; color: #fff; }
.evento-mirtilo   { background-color: #3f51b5; color: #fff; }
.evento-lavanda   { background-color: #7986cb; color: #fff; }
.evento-uva       { background-color: #8e24aa; color: #fff; }
.evento-grafite   { background-color: #616161; color: #fff; }
```

### `scripts/pipe_tasks.py`
```python
def tarefa_calendario_hoje():
    """Notifica eventos do dia seguinte às 08:00."""
    from app.calendario.models import Evento
    from app.notifications.service import notification_service
    from app.auth.models import User
    from datetime import date, timedelta

    amanha = date.today() + timedelta(days=1)
    eventos = Evento.query.filter(
        Evento.notificar   == True,
        db.func.date(Evento.data_inicio) == amanha,
        Evento.notificado_em != amanha
    ).all()

    for evento in eventos:
        user = User.query.get(evento.user_id)
        if not user:
            continue
        notification_service.send(
            user    = user,
            type    = 'evento',
            subject = f'Evento amanhã: {evento.titulo}',
            body    = (
                f"📅 {evento.titulo}\n"
                f"🕐 {evento.data_inicio.strftime('%H:%M')} — {evento.data_fim.strftime('%H:%M')}\n"
                + (f"📍 {evento.localizacao}" if evento.localizacao else "")
            ),
            data = {}
        )
        evento.notificado_em = amanha

    db.session.commit()

# Adicionar chamada no bloco principal:
# tarefa_calendario_hoje()
```
> Nota: `notification_service.send()` recebe `user` (objeto User), não `user_id`. Confirmar assinatura em `app/notifications/service.py` antes de implementar.

---

## Templates a criar

### `app/templates/calendario/index.html`
- Herda `base.html`
- Duas vistas: **Mensal** | **Agenda** (tabs no topo)
- **Vista Mensal**: grelha 7 colunas × N semanas, estilo Google Calendar
  - Cabeçalho com dias da semana (Dom–Sáb ou Seg–Dom, a decidir)
  - Navegação Mês anterior / Mês seguinte / Hoje
  - Eventos renderizados como píldoras coloridas (`span` com classe `evento-<cor>`)
  - Eventos com mais de 1 dia mostram píldora contínua entre células
  - Clique em slot vazio → abre modal de criação com data pré-preenchida
  - Clique em evento → abre modal de edição
  - Dia atual destacado (acento âmbar do PIPE)
- **Vista Agenda**: lista cronológica a partir de hoje
  - Agrupada por data
  - Cada evento: hora início–fim, cor, título, localização (se existir)
  - Botão de editar e apagar por evento
- **Modal único** (criar e editar):
  - Campos: título, descrição, localização, data início, data fim, dia inteiro (toggle), notificar (toggle)
  - Selector de cor: 11 círculos coloridos clicáveis
  - Botões: Guardar / Apagar (só em edição) / Cancelar
- Frontend vanilla JS inline — padrão PIPE
- CSRF: `X-CSRFToken` no header de todos os fetch, padrão PIPE

---

## Rate limiting (a adicionar em `routes.py`)

```python
from app.extensions import limiter

# Aplicar nas rotas de escrita
@limiter.limit("60/minute")   # api_eventos (GET) — leitura frequente ao navegar
@limiter.limit("30/minute")   # api_criar_evento, api_editar_evento, api_apagar_evento
```

---

## Migração de base de dados

```bash
# No PythonAnywhere, após deploy:
python -c "from app import create_app; from app.extensions import db; from app.calendario.models import Evento; app = create_app(); app.app_context().push(); db.create_all()"
```

---

## Sequência de implementação sugerida

1. Backend: `__init__.py`, `models.py`, `routes.py`
2. Registo do blueprint em `app/__init__.py`
3. Entrada em `app/modulos/config.py`
4. Cores em `pipe.css`
5. Template `calendario/index.html` — vista Agenda primeiro (mais simples), depois vista Mensal
6. Tarefa agendada em `pipe_tasks.py`
7. Teste local → deploy → migração BD no PA
