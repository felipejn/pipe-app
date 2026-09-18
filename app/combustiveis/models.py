from datetime import datetime
from app import db


class Posto(db.Model):
    __tablename__ = 'combustiveis_postos'
    id = db.Column(db.Integer, primary_key=True)  # mesmo id da DGEG
    nome = db.Column(db.String(200), nullable=False)
    marca = db.Column(db.String(100))
    tipo_posto = db.Column(db.String(50))
    morada = db.Column(db.String(300))
    localidade = db.Column(db.String(150))
    cod_postal = db.Column(db.String(20))
    concelho = db.Column(db.String(100), nullable=False, index=True)
    # Arquivamento automático: quando a API Aberta reatribui o `id` de uma
    # estação (ex.: "E.S. FERREIROS REPSOL" substituída por "Posto Ferreiros-
    # ESO305 REPSOL" com id diferente), o posto antigo fica "congelado" na BD
    # com a última data em que foi visto. Em vez de ficar visível para sempre
    # com dados desactualizados, é marcado como inactivo — mas o histórico
    # associado é preservado.
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    # Nº de recolhas consecutivas em que este posto não apareceu na resposta
    # da API Aberta. Ao atingir LIMIAR_CICLOS_AUSENTE (services.py) o posto
    # passa a ativo=False; volta a 0 assim que o posto reaparece.
    ciclos_ausente = db.Column(db.Integer, nullable=False, default=0)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    precos = db.relationship('PrecoHistorico', backref='posto', lazy='dynamic')


class PrecoHistorico(db.Model):
    __tablename__ = 'combustiveis_precos_historico'
    id = db.Column(db.Integer, primary_key=True)
    posto_id = db.Column(db.Integer, db.ForeignKey('combustiveis_postos.id'), nullable=False, index=True)
    tipo_combustivel = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    data_atualizacao_dgeg = db.Column(db.String(50))
    data_recolha = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class UtilizadorConcelho(db.Model):
    __tablename__ = 'combustiveis_utilizador_concelho'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)
    concelho = db.Column(db.String(100), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'concelho', name='uq_user_concelho'),)


class UtilizadorCombustivel(db.Model):
    __tablename__ = 'combustiveis_utilizador_combustivel'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('utilizadores.id'), nullable=False)
    tipo_combustivel = db.Column(db.String(100), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'tipo_combustivel', name='uq_user_combustivel'),)


class EstadoAtualizacaoCombustiveis(db.Model):
    __tablename__ = 'combustiveis_estado_atualizacao'
    id = db.Column(db.Integer, primary_key=True)
    ultima_atualizacao = db.Column(db.DateTime)
    ultima_execucao_sucesso = db.Column(db.Boolean, default=True)
    mensagem_erro = db.Column(db.Text)