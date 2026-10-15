"""Tests for the public views (index, posts, chemistry, survey, tutorials, search)."""

from app.models import Comment


def test_index_shows_published_and_hides_draft(client, data):
    response = client.get('/')
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert data['post_title'] in body
    assert 'Rascunho Interno' not in body


def test_posts_list(client, data):
    response = client.get('/posts')
    assert response.status_code == 200
    assert data['post_title'] in response.get_data(as_text=True)


def test_post_detail_renders_content_and_comments(client, data):
    response = client.get(f"/post/{data['post_slug']}")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert data['post_title'] in body
    assert 'dinâmica molecular' in body
    assert 'Ótimo artigo!' in body


def test_post_detail_unknown_slug_returns_404(client):
    assert client.get('/post/nao-existe').status_code == 404


def test_comment_submission_creates_record(app, client, data):
    response = client.post(f"/post/{data['post_slug']}", data={
        'content': 'Comentário de teste automatizado',
    })
    assert response.status_code == 302
    with app.app_context():
        assert Comment.query.filter_by(
            content='Comentário de teste automatizado').count() == 1


def test_comment_requires_content(app, client, data):
    response = client.post(f"/post/{data['post_slug']}", data={'content': ''})
    assert response.status_code == 200
    with app.app_context():
        assert Comment.query.filter_by(content='').count() == 0


def test_comment_uses_logged_in_user(app, admin_client, data):
    response = admin_client.post(f"/post/{data['post_slug']}", data={
        'content': 'Comentário do administrador',
    })
    assert response.status_code == 302
    with app.app_context():
        comment = Comment.query.filter_by(content='Comentário do administrador').first()
        assert comment is not None
        assert comment.user_id == data['admin_id']


def test_category_page(client, data):
    response = client.get(f"/category/{data['category_slug']}")
    assert response.status_code == 200
    assert data['post_title'] in response.get_data(as_text=True)


def test_category_unknown_returns_404(client):
    assert client.get('/category/inexistente').status_code == 404


def test_chemistry_pages(client):
    assert client.get('/chemistry').status_code == 200
    assert client.get('/chemistry/posts').status_code == 200


def test_survey_page(client):
    response = client.get('/survey')
    assert response.status_code == 200
    assert 'STEM' in response.get_data(as_text=True)


def test_tutorials_list(client, data):
    response = client.get('/tutoriais')
    assert response.status_code == 200
    assert 'Trilha de Química Computacional' in response.get_data(as_text=True)


def test_tutorial_detail_by_slug(client, data):
    response = client.get(f"/tutoriais/{data['tutorial_slug']}")
    assert response.status_code == 200
    assert data['post_title'] in response.get_data(as_text=True)


def test_tutorial_detail_by_id(client, data):
    response = client.get(f"/tutoriais/{data['tutorial_id']}")
    assert response.status_code == 200


def test_search_returns_matching_post(client, data):
    response = client.get('/search', query_string={'q': 'GROMACS'})
    assert response.status_code == 200
    assert data['post_title'] in response.get_data(as_text=True)


def test_search_without_matches(client):
    response = client.get('/search', query_string={'q': 'zzzzzzzz'})
    assert response.status_code == 200
