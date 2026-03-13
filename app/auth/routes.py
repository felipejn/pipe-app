from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from app import db
from app.auth import auth
from app.auth.forms import LoginForm, RegistoForm
from app.auth.models import User

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.activo and user.check_password(form.password.data):
            login_user(user, remember=form.lembrar.data)
            user.ultimo_login = datetime.utcnow()
            db.session.commit()
            proximo = request.args.get('next')
            return redirect(proximo or url_for('dashboard'))
        flash('Utilizador ou palavra-passe incorrectos.', 'erro')

    return render_template('auth/login.html', form=form)

@auth.route('/registo', methods=['GET', 'POST'])
def registo():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistoForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Conta criada com sucesso. Podes iniciar sessão.', 'sucesso')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão terminada.', 'info')
    return redirect(url_for('auth.login'))
