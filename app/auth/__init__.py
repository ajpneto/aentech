# app/auth/__init__.py
from flask import Blueprint

blueprint = Blueprint('auth', __name__)

from . import views
