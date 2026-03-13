from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.auth.models import User

class LoginForm(FlaskForm):
    username = StringField('Utilizador', validators=[DataRequired()])
    password = PasswordField('Palavra-passe', validators=[DataRequired()])
    lembrar = BooleanField('Lembrar sessão')
    submeter = SubmitField('Entrar')

class RegistoForm(FlaskForm):
    username = StringField('Utilizador', validators=[
        DataRequired(), Length(min=3, max=64)
    ])
    email = StringField('Email', validators=[
        DataRequired(), Email(), Length(max=120)
    ])
    password = PasswordField('Palavra-passe', validators=[
        DataRequired(), Length(min=8, message='Mínimo 8 caracteres')
    ])
    password2 = PasswordField('Confirmar palavra-passe', validators=[
        DataRequired(), EqualTo('password', message='As palavras-passe não coincidem')
    ])
    submeter = SubmitField('Criar conta')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Este nome de utilizador já existe.')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Este email já está registado.')
