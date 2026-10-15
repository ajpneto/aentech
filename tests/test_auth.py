"""Tests for the authentication blueprint (login/logout/session)."""


def test_login_page_renders(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert 'Entrar' in response.get_data(as_text=True)


def test_login_with_username(client, data):
    response = client.post('/login', data={
        'username_or_email': 'admin',
        'password': data['admin_password'],
    })
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session['user_id'] == data['admin_id']


def test_login_with_email(client, data):
    response = client.post('/login', data={
        'username_or_email': data['admin_email'],
        'password': data['admin_password'],
    })
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session['user_id'] == data['admin_id']


def test_login_with_invalid_credentials(client):
    response = client.post('/login', data={
        'username_or_email': 'admin',
        'password': 'senha-incorreta',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'inválidos' in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert 'user_id' not in session


def test_login_honours_safe_next(client, data):
    response = client.post('/login?next=/posts', data={
        'username_or_email': 'admin',
        'password': data['admin_password'],
    })
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/posts')


def test_login_ignores_external_next(client, data):
    response = client.post('/login?next=http://evil.example.com', data={
        'username_or_email': 'admin',
        'password': data['admin_password'],
    })
    assert response.status_code == 302
    assert 'evil.example.com' not in response.headers['Location']


def test_login_redirects_when_already_authenticated(admin_client):
    response = admin_client.get('/login')
    assert response.status_code == 302


def test_logout_clears_session(admin_client):
    response = admin_client.get('/logout')
    assert response.status_code == 302
    with admin_client.session_transaction() as session:
        assert 'user_id' not in session
