from datetime import datetime
from app import db


# Tabela de associação Tarefa ↔ Tag (many-to-many)
tarefa_tags = db.Table(
    'tarefa_tags',
    db.Column('tarefa_id', db.Integer, db.ForeignKey('tarefas.id'), primary_key=True),
    db.Column('tag_id',    db.Integer, db.ForeignKey('tags_tarefa.id'), primary_key=True),
)


class Lista(db.Model):
    """Lista personalizada de tarefas de um utilizador."""
    __tablename__ = 'listas'

    id           = db.Column(db.Integer, primary_key=True)
    nome         = db.Column(db.String(64), nullable=False)
    icone        = db.Column(db.String(8), default='📋')
    user_id      = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    ordem        = db.Column(db.Integer, default=0)

    tarefas = db.relationship(
        'Tarefa',
        backref='lista',
        lazy='dynamic',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<Lista {self.nome}>'

    def total(self):
        return self.tarefas.count()

    def pendentes(self):
        return self.tarefas.filter_by(concluida=False).count()


class Tarefa(db.Model):
    """Tarefa individual associada a uma lista e a um utilizador."""
    __tablename__ = 'tarefas'

    PRIORIDADES = ('baixa', 'media', 'alta')

    id             = db.Column(db.Integer, primary_key=True)
    texto          = db.Column(db.String(512), nullable=False)
    concluida      = db.Column(db.Boolean, default=False)
    prioridade     = db.Column(db.String(8), default='media')    # baixa / media / alta
    data_limite    = db.Column(db.Date, nullable=True)
    notas          = db.Column(db.Text, nullable=True)
    data_criacao   = db.Column(db.DateTime, default=datetime.utcnow)
    data_conclusao = db.Column(db.DateTime, nullable=True)

    # Data em que foi enviada a última notificação de atraso.
    # NULL = nunca notificada. Se notificada_em < hoje → volta a notificar.
    # Isto garante notificações diárias enquanto a tarefa continuar em atraso.
    notificada_em  = db.Column(db.Date, nullable=True)

    lista_id = db.Column(db.Integer, db.ForeignKey('listas.id'), nullable=False)
    user_id  = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)

    tags = db.relationship('TagTarefa', secondary=tarefa_tags, backref='tarefas', lazy='joined')

    def __repr__(self):
        return f'<Tarefa {self.texto[:30]}>'

    def em_atraso(self):
        """Verdadeiro se a tarefa está pendente e passou a data limite."""
        if self.concluida or not self.data_limite:
            return False
        return datetime.utcnow().date() > self.data_limite

    def notificada_hoje(self):
        """Verdadeiro se já foi enviada notificação de atraso hoje."""
        from datetime import date
        return self.notificada_em == date.today()

    def cor_prioridade(self):
        return {'alta': 'erro', 'media': 'aviso', 'baixa': 'sucesso'}.get(self.prioridade, 'aviso')


class TagTarefa(db.Model):
    """Etiqueta reutilizável por utilizador."""
    __tablename__ = 'tags_tarefa'

    id      = db.Column(db.Integer, primary_key=True)
    nome    = db.Column(db.String(32), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('nome', 'user_id', name='uq_tag_user'),
    )

    def __repr__(self):
        return f'<TagTarefa {self.nome}>'
