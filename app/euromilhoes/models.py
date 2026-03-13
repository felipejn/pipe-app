from app import db
from datetime import datetime

class Jogo(db.Model):
    __tablename__ = 'jogos_euromilhoes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)
    data_registo = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    data_sorteio = db.Column(db.Date, nullable=False)
    numeros = db.Column(db.String(20), nullable=False)   # ex: "5,12,23,34,45"
    estrelas = db.Column(db.String(6), nullable=False)    # ex: "3,11"

    def get_numeros(self):
        return [int(n) for n in self.numeros.split(',')]

    def get_estrelas(self):
        return [int(e) for e in self.estrelas.split(',')]

    def set_numeros(self, lista):
        self.numeros = ','.join(str(n) for n in sorted(lista))

    def set_estrelas(self, lista):
        self.estrelas = ','.join(str(e) for e in sorted(lista))

    def __repr__(self):
        return f'<Jogo {self.id} — {self.data_sorteio}>'
