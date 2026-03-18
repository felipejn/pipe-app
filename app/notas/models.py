from datetime import datetime
from app import db


# Tabela de associação Nota ↔ EtiquetaNota (many-to-many)
nota_etiquetas = db.Table(
    'nota_etiquetas',
    db.Column('nota_id',      db.Integer, db.ForeignKey('notas.id'),          primary_key=True),
    db.Column('etiqueta_id',  db.Integer, db.ForeignKey('etiquetas_nota.id'), primary_key=True),
)


class Nota(db.Model):
    """Nota pessoal de um utilizador — texto livre ou checklist."""
    __tablename__ = 'notas'

    # Tipos de conteúdo suportados
    TIPO_TEXTO     = 'texto'
    TIPO_CHECKLIST = 'checklist'
    TIPOS          = (TIPO_TEXTO, TIPO_CHECKLIST)

    # Cores de fundo disponíveis (nome semântico → valor CSS)
    CORES = {
        'padrao':   None,
        'vermelho': '#2d1515',
        'laranja':  '#2d1e10',
        'amarelo':  '#2a2210',
        'verde':    '#112a1a',
        'azul':     '#101e2d',
        'roxo':     '#1e1030',
        'cinzento': '#1e2028',
    }

    id           = db.Column(db.Integer, primary_key=True)
    titulo       = db.Column(db.String(256), nullable=True)      # opcional, como no Keep
    corpo        = db.Column(db.Text, nullable=True)             # texto livre (tipo=texto)
    tipo         = db.Column(db.String(16), default=TIPO_TEXTO)  # texto | checklist
    cor          = db.Column(db.String(16), default='padrao')    # chave de CORES
    fixada       = db.Column(db.Boolean, default=False)          # pin no topo
    arquivada    = db.Column(db.Boolean, default=False)          # arquivo (não apaga)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_edicao  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)

    itens      = db.relationship('ItemChecklist', backref='nota', lazy='dynamic',
                                 cascade='all, delete-orphan', order_by='ItemChecklist.ordem')
    etiquetas  = db.relationship('EtiquetaNota', secondary=nota_etiquetas,
                                 backref='notas', lazy='joined')

    def __repr__(self):
        return f'<Nota {self.id} — {(self.titulo or "sem título")[:30]}>'

    def cor_css(self):
        """Devolve o valor CSS da cor de fundo, ou None se for a cor padrão."""
        return self.CORES.get(self.cor)

    def resumo(self, max_chars=120):
        """Texto de pré-visualização para o cartão da grelha."""
        if self.tipo == self.TIPO_CHECKLIST:
            total    = self.itens.count()
            feitos   = self.itens.filter_by(feito=True).count()
            return f'{feitos}/{total} itens concluídos'
        if self.corpo:
            texto = self.corpo.strip()
            return texto[:max_chars] + ('…' if len(texto) > max_chars else '')
        return ''

    def vazia(self):
        """Verdadeiro se a nota não tem título nem conteúdo útil."""
        if self.titulo and self.titulo.strip():
            return False
        if self.tipo == self.TIPO_TEXTO and self.corpo and self.corpo.strip():
            return False
        if self.tipo == self.TIPO_CHECKLIST and self.itens.count() > 0:
            return False
        return True


class ItemChecklist(db.Model):
    """Item individual de uma nota do tipo checklist."""
    __tablename__ = 'itens_checklist'

    id      = db.Column(db.Integer, primary_key=True)
    texto   = db.Column(db.String(512), nullable=False)
    feito   = db.Column(db.Boolean, default=False)
    ordem   = db.Column(db.Integer, default=0)
    nota_id = db.Column(db.Integer, db.ForeignKey('notas.id'), nullable=False)

    def __repr__(self):
        return f'<Item {"✓" if self.feito else "○"} {self.texto[:30]}>'


class EtiquetaNota(db.Model):
    """Etiqueta reutilizável para notas, por utilizador."""
    __tablename__ = 'etiquetas_nota'

    id      = db.Column(db.Integer, primary_key=True)
    nome    = db.Column(db.String(32), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('nome', 'user_id', name='uq_etiqueta_nota_user'),
    )

    def __repr__(self):
        return f'<EtiquetaNota {self.nome}>'
