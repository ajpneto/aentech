"""Shared pytest fixtures for the AENTECH platform test suite."""

import pytest

from app import create_app, db
from app.models import Role, User, Post, Category, Comment, Tutorial, TutorialPost


# ============================================================================
# Application & database
# ============================================================================
@pytest.fixture()
def app():
    """Create a fresh application with an isolated database for each test."""
    application = create_app('config.TestingConfig')
    with application.app_context():
        db.drop_all()
        db.create_all()
        _seed_database()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


def _seed_database():
    """Populate the database with deterministic fixtures."""
    Role.insert_roles()

    admin_role = Role.query.filter_by(name='Administrator').first()
    admin = User(username='admin', email='admin@example.com', name='Administrador')
    admin.role = admin_role
    admin.password = 'admin123'

    joe = User(username='joe', email='joe@example.com', name='Joe')
    joe.password = 'joe123'

    db.session.add_all([admin, joe])
    db.session.flush()

    quimica = Category(name='Química', slug='quimica',
                       description='Química teórica e computacional')
    fisica = Category(name='Física', slug='fisica', description='Física aplicada')
    db.session.add_all([quimica, fisica])
    db.session.flush()

    published = Post(
        title='Simulação Molecular com GROMACS',
        slug='simulacao-gromacs',
        content='Conteúdo detalhado sobre dinâmica molecular e GROMACS.',
        excerpt='Introdução à dinâmica molecular com GROMACS.',
        is_published=True,
        user_id=admin.id,
    )
    draft = Post(
        title='Rascunho Interno',
        slug='rascunho-interno',
        content='Rascunho não publicado.',
        excerpt='Rascunho.',
        is_published=False,
        user_id=admin.id,
    )
    db.session.add_all([published, draft])
    db.session.flush()
    published.categories.append(quimica)

    db.session.add(Comment(content='Ótimo artigo!', post_id=published.id, user_id=joe.id))

    tutorial = Tutorial(
        title='Trilha de Química Computacional',
        slug='trilha-quimica',
        description='Sequência de artigos sobre química computacional.',
    )
    db.session.add(tutorial)
    db.session.flush()
    db.session.add(TutorialPost(tutorial_id=tutorial.id, post_id=published.id, order=1))

    db.session.commit()


# ============================================================================
# Data identifiers (avoid detached ORM instances across contexts)
# ============================================================================
@pytest.fixture()
def data(app):
    """Return a dict of ids/slugs for the seeded records."""
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        joe = User.query.filter_by(username='joe').first()
        published = Post.query.filter_by(slug='simulacao-gromacs').first()
        draft = Post.query.filter_by(slug='rascunho-interno').first()
        categoria = Category.query.filter_by(slug='quimica').first()
        tutorial = Tutorial.query.filter_by(slug='trilha-quimica').first()
        return {
            'admin_id': admin.id,
            'admin_email': admin.email,
            'admin_password': 'admin123',
            'user_id': joe.id,
            'user_email': joe.email,
            'user_password': 'joe123',
            'post_id': published.id,
            'post_slug': published.slug,
            'post_title': published.title,
            'draft_id': draft.id,
            'draft_slug': draft.slug,
            'category_id': categoria.id,
            'category_slug': categoria.slug,
            'tutorial_id': tutorial.id,
            'tutorial_slug': tutorial.slug,
        }


# ============================================================================
# HTTP clients
# ============================================================================
@pytest.fixture()
def client(app):
    """Anonymous test client."""
    return app.test_client()


@pytest.fixture()
def admin_client(app, data):
    """Test client authenticated as the administrator."""
    test_client = app.test_client()
    with test_client.session_transaction() as session:
        session['user_id'] = data['admin_id']
    return test_client


@pytest.fixture()
def user_client(app, data):
    """Test client authenticated as a regular (non-admin) user."""
    test_client = app.test_client()
    with test_client.session_transaction() as session:
        session['user_id'] = data['user_id']
    return test_client
