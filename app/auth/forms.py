from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from app import db
from app.auth.models import User


class LoginForm(FlaskForm):
    email = StringField('Email', filters=[lambda valor: valor.strip().lower() if valor else valor],
                        validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Palavra-passe', validators=[DataRequired()])
    lembrar = BooleanField('Lembrar sessão')
    submeter = SubmitField('Entrar')


class RegistoForm(FlaskForm):
    nome = StringField('Nome próprio', validators=[DataRequired(), Length(max=80)])
    apelido = StringField('Apelido', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', filters=[lambda valor: valor.strip().lower() if valor else valor], validators=[
        DataRequired(), Email(), Length(max=120)
    ])
    password = PasswordField('Palavra-passe', validators=[
        DataRequired(), Length(min=8, message='Mínimo 8 caracteres')
    ])
    password2 = PasswordField('Confirmar palavra-passe', validators=[
        DataRequired(), EqualTo('password', message='As palavras-passe não coincidem')
    ])
    submeter = SubmitField('Criar conta')

    def validate_email(self, field):
        if User.query.filter(db.func.lower(User.email) == field.data.strip().lower()).first():
            raise ValidationError('Este email já está registado.')


class DadosPessoaisForm(FlaskForm):
    nome = StringField('Nome próprio', validators=[DataRequired(), Length(max=80)])
    apelido = StringField('Apelido', validators=[DataRequired(), Length(max=80)])
    submeter = SubmitField('Guardar dados')


class AlterarPasswordForm(FlaskForm):
    password_actual = PasswordField('Palavra-passe actual', validators=[DataRequired()])
    password_nova = PasswordField('Nova palavra-passe', validators=[
        DataRequired(), Length(min=8, message='Mínimo 8 caracteres')
    ])
    password_nova2 = PasswordField('Confirmar nova palavra-passe', validators=[
        DataRequired(), EqualTo('password_nova', message='As palavras-passe não coincidem')
    ])
    submeter = SubmitField('Alterar palavra-passe')


class VerificarCodigoForm(FlaskForm):
    codigo = StringField('Código de verificação', validators=[
        DataRequired(), Length(min=6, max=6, message='O código tem 6 dígitos')
    ])
    submeter = SubmitField('Verificar')


class ConfigurarDoisFAForm(FlaskForm):
    # Telegram
    dois_fa_activo = BooleanField('Activar via Telegram')
    dois_fa_chat_id = StringField('Chat ID do Telegram', validators=[
        Optional(), Length(max=64)
    ])
    submeter_telegram = SubmitField('Guardar Telegram')

    # Email
    dois_fa_email_activo = BooleanField('Activar via Email')
    submeter_email = SubmitField('Guardar Email')


class PedirResetForm(FlaskForm):
    """Formulário para pedir recuperação de password por email."""
    email = StringField('Email', filters=[lambda valor: valor.strip().lower() if valor else valor],
                        validators=[DataRequired(), Email()])
    submeter = SubmitField('Enviar link de recuperação')


class ResetPasswordForm(FlaskForm):
    """Formulário para definir nova password via token de recuperação."""
    password_nova = PasswordField('Nova palavra-passe', validators=[
        DataRequired(), Length(min=8, message='Mínimo 8 caracteres')
    ])
    password_nova2 = PasswordField('Confirmar nova palavra-passe', validators=[
        DataRequired(), EqualTo('password_nova', message='As palavras-passe não coincidem')
    ])
    submeter = SubmitField('Guardar nova palavra-passe')


class ConfirmarTOTPForm(FlaskForm):
    """Formulário para confirmar a configuração do TOTP com um código do autenticador."""
    codigo = StringField('Código do autenticador', validators=[
        DataRequired(), Length(min=6, max=6, message='O código tem 6 dígitos')
    ])
    submeter = SubmitField('Activar autenticador')
