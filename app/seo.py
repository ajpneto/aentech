# app/seo.py
"""
Dynamic SEO engine.

Builds per-request SEO metadata: <title>, meta description/keywords, canonical
URLs, Open Graph and Twitter Card tags, robots directives, pagination
rel=prev/next links and JSON-LD structured data (WebSite, Organization,
BlogPosting, CollectionPage, Course, BreadcrumbList).

Values are provided through ``g.seo`` by the views (see the ``*_seo`` helpers
below) and merged with sensible per-endpoint defaults before being exposed to
templates through the ``inject_seo`` context processor.
"""

import re
from datetime import datetime, timezone

from flask import current_app, g, request, url_for

# ============================================================================
# Text helpers
# ============================================================================
_TAG_RE = re.compile(r'<[^>]+>')
_WS_RE = re.compile(r'\s+')


def strip_html(value):
    """Remove HTML tags/entities and collapse whitespace."""
    if not value:
        return ''
    text = _TAG_RE.sub(' ', str(value))
    text = (text.replace('&nbsp;', ' ')
                .replace('&amp;', '&')
                .replace('&lt;', '<')
                .replace('&gt;', '>')
                .replace('&quot;', '"')
                .replace('&#39;', "'"))
    return _WS_RE.sub(' ', text).strip()


def meta_excerpt(value, length=300):
    """Produce a clean, trimmed description suitable for meta tags."""
    text = strip_html(value)
    if len(text) <= length:
        return text
    truncated = text[: length + 1]
    if ' ' in truncated:
        truncated = truncated.rsplit(' ', 1)[0]
    return truncated.rstrip(' ,.;:-') + '…'


def _iso(value):
    """Serialise a datetime to ISO-8601 (UTC when naive)."""
    if not value:
        return None
    if isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


# ============================================================================
# URL helpers
# ============================================================================
def site_base_url():
    """Base absolute URL of the site (without trailing slash)."""
    configured = current_app.config.get('SEO_SITE_URL')
    if configured:
        return configured.rstrip('/')
    try:
        return request.url_root.rstrip('/')
    except RuntimeError:
        return ''


def absolute_url(path=''):
    """Turn a relative path into an absolute URL."""
    if not path:
        return site_base_url()
    if str(path).startswith(('http://', 'https://')):
        return str(path)
    if not str(path).startswith('/'):
        path = '/' + str(path)
    return site_base_url() + path


def _page_url(endpoint, view_args, args):
    try:
        return url_for(endpoint, _external=True, **(view_args or {}), **args)
    except Exception:
        return absolute_url(request.path)


# ============================================================================
# Endpoint defaults
# ============================================================================
# Endpoints that must never be indexed (admin / auth / utility pages).
NOINDEX_ENDPOINTS = {
    'auth.login', 'auth.logout',
    'main.create_post', 'main.edit_post', 'main.delete_post',
    'main.my_posts', 'main.drafts', 'main.manage_categories',
    'main.delete_category', 'main.manage_tutorials', 'main.create_tutorial',
    'main.edit_tutorial', 'main.delete_tutorial',
}

_STATIC_DEFAULTS = {
    'main.index': {
        'title': 'Ciência & Tecnologia — Simulação Molecular e Quimioinformática',
        'description': (
            'Plataforma AENTECH para disseminação científica: artigos, tutoriais e '
            'ferramentas de computação científica, simulação molecular, química teórica '
            'e quimioinformática.'
        ),
        'keywords': (
            'AENTECH, ciência e tecnologia, computação científica, simulação molecular, '
            'dinâmica molecular, química teórica, quimioinformática, pesquisa STEM'
        ),
    },
    'main.posts_list': {
        'title': 'Últimas Postagens — Artigos de Ciência e Tecnologia',
        'description': (
            'Explore os artigos mais recentes da plataforma AENTECH sobre simulação '
            'molecular, físico-química de fluidos, química teórica e ciências da vida.'
        ),
        'keywords': 'artigos, blog científico, simulação molecular, química computacional',
    },
    'main.chemistry': {
        'title': 'Fundamentos de Química — Teórica e Computacional',
        'description': (
            'Fundamentos de termodinâmica, estrutura eletrônica e mecânica estatística '
            'que conectam a química teórica à simulação atomística e à quimioinformática.'
        ),
        'keywords': 'química teórica, físico-química, estrutura eletrônica, química computacional',
    },
    'main.chemistry_posts': {
        'title': 'Artigos de Química — Teórica e Computacional',
        'description': (
            'Todos os artigos da categoria Química: simulação molecular, propriedades de '
            'transporte, dinâmica molecular e quimioinformática na plataforma AENTECH.'
        ),
        'keywords': 'artigos de química, química computacional, dinâmica molecular',
    },
    'main.survey': {
        'title': 'Pesquisa STEM — Taxonomia das Ciências Químicas',
        'description': (
            'Análise da taxonomia das Ciências Químicas (níveis L1 a L4) e dos fluxos de '
            'trabalho computacionais: transporte em líquidos, metadinâmica de polímeros '
            'e triagem virtual.'
        ),
        'keywords': (
            'pesquisa STEM, taxonomia química, workflows computacionais, PLUMED, GROMACS, RDKit'
        ),
    },
    'main.tutorials_list': {
        'title': 'Tutoriais & Minicursos — Ciência Computacional',
        'description': (
            'Trilhas de aprendizado e minicursos organizados sobre computação científica, '
            'simulação molecular e química computacional.'
        ),
        'keywords': 'tutoriais, minicursos, ciência computacional, aprendizado, AENTECH',
    },
    'main.search': {
        'title': 'Busca',
        'description': 'Pesquise artigos, ferramentas e tópicos de ciência e tecnologia na plataforma AENTECH.',
        'robots': 'noindex, follow',
    },
}


# ============================================================================
# JSON-LD structured data
# ============================================================================
def _publisher():
    config = current_app.config
    return {
        '@type': 'Organization',
        'name': config.get('SEO_SITE_NAME', 'AENTECH'),
        'url': site_base_url(),
        'logo': {
            '@type': 'ImageObject',
            'url': absolute_url(config.get('SEO_LOGO_PATH', '/static/favicon.ico')),
        },
    }


def _organization_json_ld():
    config = current_app.config
    return {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        'name': config.get('SEO_SITE_NAME', 'AENTECH'),
        'url': site_base_url(),
        'logo': absolute_url(config.get('SEO_LOGO_PATH', '/static/favicon.ico')),
    }


def _website_json_ld():
    config = current_app.config
    return {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'name': config.get('SEO_SITE_NAME', 'AENTECH'),
        'url': site_base_url(),
        'description': config.get('SEO_DEFAULT_DESCRIPTION', ''),
        'inLanguage': config.get('SEO_LANGUAGE', 'pt-BR'),
        'publisher': {'@type': 'Organization', 'name': config.get('SEO_SITE_NAME', 'AENTECH')},
        'potentialAction': {
            '@type': 'SearchAction',
            'target': {
                '@type': 'EntryPoint',
                'urlTemplate': site_base_url() + '/search?q={search_term_string}',
            },
            'query-input': 'required name=search_term_string',
        },
    }


def breadcrumb_json_ld(items):
    """``items`` is a list of ``(name, path_or_url)`` tuples."""
    elements = []
    for position, item in enumerate(items, start=1):
        name, url = item
        entry = {'@type': 'ListItem', 'position': position, 'name': name}
        if url:
            entry['item'] = absolute_url(url)
        elements.append(entry)
    return {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': elements,
    }


def _article_json_ld(title, description, url, image, published, modified,
                     author, section=None, keywords=None):
    data = {
        '@context': 'https://schema.org',
        '@type': 'BlogPosting',
        'mainEntityOfPage': {'@type': 'WebPage', '@id': url},
        'headline': strip_html(title)[:110],
        'description': description,
        'image': [image] if image else [],
        'datePublished': _iso(published),
        'dateModified': _iso(modified) or _iso(published),
        'author': {'@type': 'Person', 'name': author or current_app.config.get('SEO_SITE_NAME', 'AENTECH')},
        'publisher': _publisher(),
        'inLanguage': current_app.config.get('SEO_LANGUAGE', 'pt-BR'),
        'url': url,
    }
    if section:
        data['articleSection'] = section
    if keywords:
        data['keywords'] = keywords
    return data


def _collection_json_ld(name, description, url):
    return {
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        'name': name,
        'description': description,
        'url': url,
        'inLanguage': current_app.config.get('SEO_LANGUAGE', 'pt-BR'),
        'isPartOf': {'@type': 'WebSite', 'url': site_base_url()},
    }


# ============================================================================
# Per-page override builders (assigned to g.seo by the views)
# ============================================================================
def post_seo(post):
    """SEO overrides for an individual blog post."""
    config = current_app.config
    categories = list(post.categories)
    section = categories[0].name if categories else None
    keywords = ', '.join(c.name for c in categories) or None
    image = absolute_url(config.get('SEO_DEFAULT_IMAGE'))
    url = absolute_url(url_for('main.post_detail', slug=post.slug))
    description = meta_excerpt(post.excerpt or post.content, 300)
    author = post.author.username if getattr(post, 'author', None) else None

    breadcrumbs = [('Home', '/'), ('Artigos', url_for('main.posts_list')),
                   (post.title, url_for('main.post_detail', slug=post.slug))]

    return {
        'title': post.title,
        'description': description,
        'keywords': keywords,
        'type': 'article',
        'image': image,
        'author': author,
        'section': section,
        'published_time': post.created_at,
        'modified_time': post.updated_at,
        'canonical': url_for('main.post_detail', slug=post.slug),
        'robots': None if post.is_published else 'noindex, nofollow',
        'json_ld': [
            _article_json_ld(post.title, description, url, image,
                             post.created_at, post.updated_at, author, section, keywords),
            breadcrumb_json_ld(breadcrumbs),
        ],
    }


def category_seo(category, pagination=None):
    """SEO overrides for a category listing page."""
    url = url_for('main.category_posts', slug=category.slug)
    description = meta_excerpt(
        category.description
        or 'Artigos da categoria "{}" na plataforma AENTECH.'.format(category.name),
        300,
    )
    return {
        'title': 'Categoria: {}'.format(category.name),
        'description': description,
        'keywords': '{}, artigos, {}'.format(category.name, current_app.config.get('SEO_SITE_NAME', 'AENTECH')),
        'type': 'website',
        'canonical': url,
        'pagination': pagination,
        'json_ld': [
            _collection_json_ld(
                'Categoria: {}'.format(category.name), description, absolute_url(url)
            ),
            breadcrumb_json_ld([('Home', '/'), ('Artigos', url_for('main.posts_list')),
                                (category.name, url)]),
        ],
    }


def tutorial_seo(tutorial, posts=None):
    """SEO overrides for a tutorial detail page."""
    url = url_for('main.tutorial_detail', identifier=tutorial.slug)
    description = meta_excerpt(
        tutorial.description
        or 'Tutorial da plataforma AENTECH com artigos ordenados sobre ciência computacional.',
        300,
    )
    json_ld = [
        {
            '@context': 'https://schema.org',
            '@type': 'Course',
            'name': tutorial.title,
            'description': description,
            'url': absolute_url(url),
            'inLanguage': current_app.config.get('SEO_LANGUAGE', 'pt-BR'),
            'provider': _publisher(),
        },
        breadcrumb_json_ld([('Home', '/'), ('Tutoriais', url_for('main.tutorials_list')),
                            (tutorial.title, url)]),
    ]
    return {
        'title': tutorial.title,
        'description': description,
        'keywords': 'tutorial, minicurso, {}, ciência computacional'.format(tutorial.title),
        'type': 'article',
        'canonical': url,
        'published_time': tutorial.created_at,
        'modified_time': tutorial.updated_at,
        'json_ld': json_ld,
    }


# ============================================================================
# Main builder
# ============================================================================
def _branded_title(title):
    title = (title or '').strip()
    site = current_app.config.get('SEO_SITE_NAME', 'AENTECH')
    if not title:
        return site
    if site.lower() in title.lower():
        return title
    return '{} | {}'.format(title, site)


def build_seo():
    """Assemble the complete SEO context for the current request."""
    config = current_app.config
    site_name = config.get('SEO_SITE_NAME', 'AENTECH')
    endpoint = request.endpoint or ''
    override = getattr(g, 'seo', None) or {}
    static = _STATIC_DEFAULTS.get(endpoint, {})

    # Robots directive
    robots = override.get('robots') or static.get('robots')
    if not robots:
        robots = 'noindex, nofollow' if endpoint in NOINDEX_ENDPOINTS else 'index, follow'

    # Title
    title = _branded_title(override.get('title') or static.get('title'))

    # Description / keywords
    description = override.get('description') or static.get('description') \
        or config.get('SEO_DEFAULT_DESCRIPTION', '')
    description = meta_excerpt(description, 300)
    keywords = override.get('keywords') or static.get('keywords') \
        or config.get('SEO_DEFAULT_KEYWORDS', '')

    # Canonical URL
    canonical = override.get('canonical') or request.path
    canonical = absolute_url(canonical)

    # Social image
    image = absolute_url(override.get('image') or config.get('SEO_DEFAULT_IMAGE'))

    og_type = override.get('type') or static.get('type') or 'website'

    # Pagination rel links
    pagination = override.get('pagination')
    prev_page = next_page = None
    if pagination is not None:
        args = request.args.to_dict()
        if getattr(pagination, 'has_prev', False):
            page_args = dict(args, page=pagination.prev_num)
            prev_page = _page_url(endpoint, request.view_args, page_args)
        if getattr(pagination, 'has_next', False):
            page_args = dict(args, page=pagination.next_num)
            next_page = _page_url(endpoint, request.view_args, page_args)

    # Structured data
    json_ld = [_organization_json_ld()]
    if endpoint == 'main.index':
        json_ld.append(_website_json_ld())
    json_ld.extend(override.get('json_ld') or [])

    return {
        'site_name': site_name,
        'title': title,
        'description': description,
        'keywords': keywords,
        'robots': robots,
        'canonical': canonical,
        'image': image,
        'image_alt': config.get('SEO_SITE_NAME', 'AENTECH'),
        'type': og_type,
        'locale': config.get('SEO_LOCALE', 'pt_BR'),
        'language': config.get('SEO_LANGUAGE', 'pt-BR'),
        'twitter_site': config.get('SEO_TWITTER_HANDLE', ''),
        'theme_color': config.get('SEO_THEME_COLOR', '#4f46e5'),
        'author': override.get('author'),
        'section': override.get('section'),
        'published_time': _iso(override.get('published_time')),
        'modified_time': _iso(override.get('modified_time')),
        'prev_page': prev_page,
        'next_page': next_page,
        'json_ld': json_ld,
    }
