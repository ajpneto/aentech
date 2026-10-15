"""Tests for the dynamic SEO engine: meta tags, Open Graph, JSON-LD, sitemap."""

import json
import re
import xml.etree.ElementTree as ET

SITE_URL = 'https://aentech.pythonanywhere.com'
SITEMAP_NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _meta(html, name):
    match = re.search(r'<meta name="%s" content="(.*?)">' % name, html)
    return match.group(1) if match else None


def _prop(html, prop):
    match = re.search(r'<meta property="%s" content="(.*?)">' % prop, html)
    return match.group(1) if match else None


def _canonical(html):
    match = re.search(r'<link rel="canonical" href="(.*?)">', html)
    return match.group(1) if match else None


def _title(html):
    match = re.search(r'<title>(.*?)</title>', html, re.S)
    return match.group(1).strip() if match else None


def _json_ld(html):
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return [json.loads(block) for block in blocks]


# ---------------------------------------------------------------------------
# Core meta tags
# ---------------------------------------------------------------------------
def test_home_title_description_and_canonical(client):
    html = client.get('/').get_data(as_text=True)
    assert 'AENTECH' in _title(html)
    assert _meta(html, 'description')
    assert _canonical(html) == SITE_URL + '/'
    assert _meta(html, 'robots') == 'index, follow'


def test_home_open_graph_and_twitter(client):
    html = client.get('/').get_data(as_text=True)
    assert _prop(html, 'og:type') == 'website'
    assert _prop(html, 'og:title')
    assert _prop(html, 'og:url') == SITE_URL + '/'
    assert _prop(html, 'og:image')
    assert 'twitter:card' in html


def test_home_structured_data(client):
    types = {block['@type'] for block in _json_ld(client.get('/').get_data(as_text=True))}
    assert {'Organization', 'WebSite'} <= types


def test_post_page_is_article(client, data):
    html = client.get(f"/post/{data['post_slug']}").get_data(as_text=True)
    assert _prop(html, 'og:type') == 'article'
    assert _canonical(html) == f"{SITE_URL}/post/{data['post_slug']}"
    types = {block['@type'] for block in _json_ld(html)}
    assert {'Organization', 'BlogPosting', 'BreadcrumbList'} <= types


def test_draft_post_is_noindex(client, data):
    html = client.get(f"/post/{data['draft_slug']}").get_data(as_text=True)
    assert 'noindex' in _meta(html, 'robots')


def test_search_page_is_noindex_follow(client):
    html = client.get('/search', query_string={'q': 'x'}).get_data(as_text=True)
    assert _meta(html, 'robots') == 'noindex, follow'


def test_admin_page_is_noindex(admin_client):
    html = admin_client.get('/create').get_data(as_text=True)
    assert 'noindex' in _meta(html, 'robots')


def test_category_page_structured_data(client, data):
    html = client.get(f"/category/{data['category_slug']}").get_data(as_text=True)
    types = {block['@type'] for block in _json_ld(html)}
    assert 'CollectionPage' in types
    assert _canonical(html) == f"{SITE_URL}/category/{data['category_slug']}"


def test_tutorial_page_structured_data(client, data):
    html = client.get(f"/tutoriais/{data['tutorial_slug']}").get_data(as_text=True)
    types = {block['@type'] for block in _json_ld(html)}
    assert 'Course' in types


def test_every_public_page_has_valid_json_ld(client, data):
    paths = [
        '/', '/posts', '/chemistry', '/chemistry/posts', '/survey', '/tutoriais',
        f"/post/{data['post_slug']}",
        f"/category/{data['category_slug']}",
        f"/tutoriais/{data['tutorial_slug']}",
    ]
    for path in paths:
        blocks = _json_ld(client.get(path).get_data(as_text=True))
        assert blocks, f"no JSON-LD found on {path}"
        for block in blocks:
            assert '@context' in block


# ---------------------------------------------------------------------------
# Crawling endpoints
# ---------------------------------------------------------------------------
def test_sitemap_is_valid_xml(client):
    response = client.get('/sitemap.xml')
    assert response.status_code == 200
    assert response.headers['Content-Type'].startswith('application/xml')
    root = ET.fromstring(response.get_data(as_text=True))
    assert root.tag == f'{SITEMAP_NS}urlset'
    assert len(root.findall(f'{SITEMAP_NS}url')) > 0


def test_sitemap_uses_configured_site_url(client):
    xml = client.get('/sitemap.xml').get_data(as_text=True)
    assert 'localhost' not in xml
    assert SITE_URL + '/' in xml


def test_sitemap_includes_categories_and_tutorials(client, data):
    xml = client.get('/sitemap.xml').get_data(as_text=True)
    assert f"/category/{data['category_slug']}" in xml
    assert f"/tutoriais/{data['tutorial_slug']}" in xml


def test_sitemap_includes_published_but_not_draft(client, data):
    xml = client.get('/sitemap.xml').get_data(as_text=True)
    assert f"{SITE_URL}/post/{data['post_slug']}" in xml
    assert data['draft_slug'] not in xml


def test_robots_txt(client):
    response = client.get('/robots.txt')
    assert response.status_code == 200
    assert response.headers['Content-Type'].startswith('text/plain')
    body = response.get_data(as_text=True)
    assert 'User-agent: *' in body
    assert 'Disallow: /search' in body
    assert f'Sitemap: {SITE_URL}/sitemap.xml' in body
