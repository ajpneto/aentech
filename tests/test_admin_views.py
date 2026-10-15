"""Tests for the admin views: CRUD operations and access control."""

from app import db
from app.models import Post, Category, Tutorial


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
def test_create_requires_login(client):
    response = client.get('/create')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_non_admin_is_denied(user_client):
    response = user_client.get('/create')
    assert response.status_code == 302
    assert '/login' not in response.headers['Location']


def test_admin_can_open_create_form(admin_client):
    assert admin_client.get('/create').status_code == 200


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------
def test_admin_creates_post(app, admin_client, data):
    response = admin_client.post('/create', data={
        'title': 'Artigo Novo de Teste',
        'content': 'Corpo do artigo novo.',
        'excerpt': 'Resumo do artigo.',
        'categories': [str(data['category_id'])],
        'is_published': 'y',
    })
    assert response.status_code == 302
    with app.app_context():
        post = Post.query.filter_by(slug='artigo-novo-de-teste').first()
        assert post is not None
        assert post.is_published is True
        assert post.categories.count() == 1


def test_create_post_rejects_duplicate_slug(admin_client, data):
    response = admin_client.post('/create', data={
        'title': 'Título Repetido',
        'slug': data['post_slug'],
        'content': 'Corpo qualquer.',
        'is_published': 'y',
    })
    assert response.status_code == 200
    assert 'já está em uso' in response.get_data(as_text=True)


def test_admin_edits_post(app, admin_client, data):
    response = admin_client.post(f"/post/{data['post_id']}/edit", data={
        'title': 'Título Atualizado',
        'slug': data['post_slug'],
        'content': 'Conteúdo atualizado.',
        'is_published': 'y',
        'categories': [str(data['category_id'])],
    })
    assert response.status_code == 302
    with app.app_context():
        post = db.session.get(Post, data['post_id'])
        assert post.title == 'Título Atualizado'


def test_admin_deletes_post(app, admin_client, data):
    response = admin_client.post(f"/post/{data['draft_id']}/delete")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Post, data['draft_id']) is None


def test_drafts_page_lists_unpublished(admin_client):
    response = admin_client.get('/drafts')
    assert response.status_code == 200
    assert 'Rascunho Interno' in response.get_data(as_text=True)


def test_my_posts_page(admin_client, data):
    response = admin_client.get('/my-posts')
    assert response.status_code == 200
    assert data['post_title'] in response.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
def test_admin_creates_category(app, admin_client):
    response = admin_client.post('/categories', data={
        'name': 'Biologia',
        'slug': 'biologia',
        'description': 'Ciências biológicas.',
    })
    assert response.status_code == 302
    with app.app_context():
        assert Category.query.filter_by(slug='biologia').first() is not None


def test_admin_deletes_category(app, admin_client, data):
    response = admin_client.post(f"/category/{data['category_id']}/delete")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Category, data['category_id']) is None


# ---------------------------------------------------------------------------
# Tutorials
# ---------------------------------------------------------------------------
def test_manage_tutorials_page(admin_client):
    assert admin_client.get('/admin/tutoriais').status_code == 200


def test_admin_creates_tutorial(app, admin_client, data):
    response = admin_client.post('/tutoriais/novo', data={
        'title': 'Novo Tutorial',
        'description': 'Descrição do tutorial.',
        'selected_posts': [str(data['post_id'])],
    })
    assert response.status_code == 302
    with app.app_context():
        tutorial = Tutorial.query.filter_by(slug='novo-tutorial').first()
        assert tutorial is not None
        assert len(tutorial.ordered_posts) == 1


def test_admin_edits_tutorial(app, admin_client, data):
    response = admin_client.post(f"/tutoriais/{data['tutorial_id']}/editar", data={
        'title': 'Trilha Editada',
        'slug': data['tutorial_slug'],
        'description': 'Nova descrição.',
        'selected_posts': [str(data['post_id'])],
    })
    assert response.status_code == 302
    with app.app_context():
        tutorial = db.session.get(Tutorial, data['tutorial_id'])
        assert tutorial.title == 'Trilha Editada'


def test_admin_deletes_tutorial(app, admin_client, data):
    response = admin_client.post(f"/tutoriais/{data['tutorial_id']}/excluir")
    assert response.status_code == 302
    with app.app_context():
        assert db.session.get(Tutorial, data['tutorial_id']) is None
