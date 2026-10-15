from flask import Blueprint
from app.models import Category

blueprint = Blueprint('main', __name__)

@blueprint.context_processor
def inject_categories():
    """Make categories available to all templates"""
    return {
        'all_categories': Category.query.order_by(Category.name).all()
    }
