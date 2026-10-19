from datetime import datetime

from app import db


class PartilhaRecurso(db.Model):
    """Representa uma partilha de um recurso (tarefa, nota ou evento) entre utilizadores.

    O dono (utilizador que criou o recurso) partilha com outro utilizador registado,
    identificado pelo email no momento da criação. O utilizador alvo pode aceitar ou
    rejeitar a partilha. Enquanto o estado nao e 'aceite', o utilizador alvo nao acede
    ao recurso.
    """
    __tablename__ = 'partilha_recurso'

    id = db.Column(db.Integer, primary_key=True)
    tipo_recurso = db.Column(db.String(32), nullable=False)
    recurso_id = db.Column(db.Integer, nullable=False)
    dono_id = db.Column(
        db.Integer, db.ForeignKey('utilizadores.id', ondelete='CASCADE'),
        nullable=False,
    )
    utilizador_id = db.Column(
        db.Integer, db.ForeignKey('utilizadores.id', ondelete='CASCADE'),
        nullable=False,
    )
    nivel = db.Column(db.String(16), nullable=False, default='leitura')
    estado = db.Column(db.String(16), nullable=False, default='pendente')
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    actualizado_em = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        db.UniqueConstraint(
            'tipo_recurso', 'recurso_id', 'utilizador_id',
            name='uq_partilha_recurso_utilizador',
        ),
        db.CheckConstraint(
            "nivel IN ('leitura','edicao')", name='ck_partilha_nivel',
        ),
        db.CheckConstraint(
            "estado IN ('pendente','aceite','rejeitado')",
            name='ck_partilha_estado',
        ),
        db.CheckConstraint(
            'dono_id != utilizador_id', name='ck_partilha_nao_self',
        ),
    )

    dono = db.relationship(
        'User', foreign_keys=[dono_id], backref='partilhas_criadas',
    )
    utilizador = db.relationship(
        'User', foreign_keys=[utilizador_id], backref='partilhas_recebidas',
    )

    def __repr__(self):
        return (
            f'<PartilhaRecurso {self.tipo_recurso}:{self.recurso_id} '
            f'para {self.utilizador_id} ({self.nivel}, {self.estado})>'
        )
