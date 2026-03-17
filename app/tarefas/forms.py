from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, Optional


ICONES_LISTA = [
    ('📋', '📋 Geral'),
    ('💼', '💼 Trabalho'),
    ('🏠', '🏠 Casa'),
    ('🛒', '🛒 Compras'),
    ('🎓', '🎓 Aprendizagem'),
    ('💪', '💪 Saúde'),
    ('✈️', '✈️ Viagens'),
    ('💡', '💡 Ideias'),
    ('🎯', '🎯 Objectivos'),
    ('⭐', '⭐ Favoritos'),
]


class ListaForm(FlaskForm):
    nome  = StringField('Nome', validators=[DataRequired(), Length(max=64)])
    icone = SelectField('Ícone', choices=ICONES_LISTA, default='📋')


class TarefaForm(FlaskForm):
    texto      = StringField('Tarefa', validators=[DataRequired(), Length(max=512)])
    prioridade = SelectField('Prioridade', choices=[
        ('alta',  'Alta'),
        ('media', 'Média'),
        ('baixa', 'Baixa'),
    ], default='media')
    data_limite = DateField('Data limite', validators=[Optional()], format='%Y-%m-%d')
    notas       = TextAreaField('Notas', validators=[Optional(), Length(max=1000)])
    tags        = StringField('Etiquetas (separadas por vírgula)', validators=[Optional(), Length(max=256)])
    lista_id    = HiddenField('Lista')
