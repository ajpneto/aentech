"""Unit tests for the pure helper functions in app/seo.py."""

from app.seo import (
    strip_html, meta_excerpt, absolute_url, site_base_url, breadcrumb_json_ld,
)


def test_strip_html_removes_tags_and_entities():
    assert strip_html('<p>Olá&nbsp;<b>mundo</b></p>') == 'Olá mundo'


def test_strip_html_handles_empty_values():
    assert strip_html(None) == ''
    assert strip_html('') == ''


def test_meta_excerpt_keeps_short_text():
    assert meta_excerpt('Texto curto') == 'Texto curto'


def test_meta_excerpt_truncates_long_text():
    result = meta_excerpt('palavra ' * 100, 50)
    assert result.endswith('…')
    assert len(result) <= 52


def test_absolute_url_in_request_context(app):
    with app.test_request_context('/'):
        assert absolute_url('/posts') == 'https://aentech.pythonanywhere.com/posts'
        assert absolute_url('posts') == 'https://aentech.pythonanywhere.com/posts'
        assert absolute_url('http://exemplo.com/x') == 'http://exemplo.com/x'
        assert site_base_url() == 'https://aentech.pythonanywhere.com'


def test_breadcrumb_json_ld_structure(app):
    with app.test_request_context('/'):
        data = breadcrumb_json_ld([('Home', '/'), ('Artigos', '/posts')])
    assert data['@type'] == 'BreadcrumbList'
    assert [item['position'] for item in data['itemListElement']] == [1, 2]
    assert data['itemListElement'][0]['item'] == 'https://aentech.pythonanywhere.com/'
