from app import db

class UserModulo(db.Model):
    __tablename__ = 'user_modulos'
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), primary_key=True)
    modulo_slug = db.Column(db.String(32), primary_key=True)
    ativo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'UserModulo(user_id={self.user_id}, modulo_slug={self.modulo_slug}, ativo={self.ativo})'


def get_modulos_ativos(user_id):
    """Devolve lista de slugs de módulos activos para o utilizador."""
    modulos = UserModulo.query.filter_by(user_id=user_id, ativo=True).all()
    return [m.modulo_slug for m in modulos]