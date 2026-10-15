"""Tests for the application factory, configuration and error handlers."""

from app import db, get_config, get_pagination_defaults
from config import TestingConfig


def test_app_is_created(app):
    assert app is not None
    assert app.config['TESTING'] is True


def test_expected_blueprints_registered(app):
    assert 'main' in app.blueprints
    assert 'auth' in app.blueprints


def test_seo_configuration_defaults(app):
    assert app.config['SEO_SITE_URL'] == 'https://aentech.pythonanywhere.com'
    assert app.config['SEO_SITE_NAME'] == 'AENTECH'
    assert app.config['SEO_DEFAULT_DESCRIPTION']
    assert app.config['SEO_DEFAULT_KEYWORDS']


def test_testing_config_is_isolated():
    assert TestingConfig.TESTING is True
    assert TestingConfig.WTF_CSRF_ENABLED is False
    assert 'test_app.db' in TestingConfig.SQLALCHEMY_DATABASE_URI


def test_unknown_route_returns_404(client):
    response = client.get('/rota-que-nao-existe')
    assert response.status_code == 404


def test_error_page_uses_seo_context(client):
    # The 404 template extends base.html, which relies on the SEO context processor.
    response = client.get('/rota-que-nao-existe')
    body = response.get_data(as_text=True)
    assert '<title>' in body
    assert 'description' in body


def test_get_config_outside_app_context():
    assert get_config('NAO_EXISTE', 'fallback') == 'fallback'


def test_get_pagination_defaults_outside_app_context():
    assert get_pagination_defaults() == {
        'posts_per_page': 10,
        'comments_per_page': 12,
        'max_per_page': 100,
    }


def test_get_config_inside_app_context(app):
    with app.app_context():
        assert get_config('SEO_SITE_NAME') == 'AENTECH'
        assert get_pagination_defaults()['posts_per_page'] == app.config['POSTS_PER_PAGE']
