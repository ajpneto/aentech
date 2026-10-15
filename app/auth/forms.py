# app/auth/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    username_or_email = StringField('Email ou Nome de Usuário', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Manter-me conectado')
    submit = SubmitField('Entrar')
