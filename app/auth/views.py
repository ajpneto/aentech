# app/auth/views.py
from flask import render_template, redirect, request, url_for, flash, session, g
from app import db
from app.models import User
from . import blueprint
from .forms import LoginForm

@blueprint.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.current_user = None
    else:
        g.current_user = User.query.get(user_id)

@blueprint.app_context_processor
def inject_current_user():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        return dict(current_user=user)
    return dict(current_user=None)

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if g.current_user is not None:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter(
            (User.email == form.username_or_email.data) | 
            (User.username == form.username_or_email.data)
        ).first()
        
        if user is not None and user.verify_password(form.password.data):
            session.clear()
            session['user_id'] = user.id
            if form.remember_me.data:
                session.permanent = True
            flash('Login realizado com sucesso!', 'success')
            next_page = request.args.get('next')
            # Security check for next page redirects
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
            return redirect(next_page)
            
        flash('Nome de usuário ou senha inválidos.', 'danger')
        
    return render_template('auth/login.html', form=form)

@blueprint.route('/logout')
def logout():
    session.clear()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('main.index'))
