"""Tests for the ORM models (User, Role, Post, Category, Comment, Tutorial)."""

import pytest

from app import db
from app.models import (
    Role, User, Post, Category, Comment, Tutorial, TutorialPost, Permission,
)


def test_insert_roles_is_idempotent(app):
    with app.app_context():
        Role.insert_roles()
        Role.insert_roles()
        assert Role.query.filter_by(name='User').count() == 1
        assert Role.query.filter_by(name='Administrator').count() == 1


def test_role_default_flags(app):
    with app.app_context():
        user_role = Role.query.filter_by(name='User').first()
        admin_role = Role.query.filter_by(name='Administrator').first()
        assert user_role.default is True
        assert admin_role.default is False
        assert admin_role.permissions == 0xff


def test_password_hashing_and_verification(app):
    with app.app_context():
        joe = User.query.filter_by(username='joe').first()
        assert joe.password_hash != 'joe123'
        assert joe.verify_password('joe123') is True
        assert joe.verify_password('senha-errada') is False


def test_password_is_not_readable(app):
    with app.app_context():
        joe = User.query.filter_by(username='joe').first()
        with pytest.raises(AttributeError):
            _ = joe.password


def test_administrator_permissions(app):
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        joe = User.query.filter_by(username='joe').first()
        assert admin.is_administrator() is True
        assert admin.can(Permission.ADMINISTER) is True
        assert joe.is_administrator() is False
        assert joe.can(Permission.COMMENT) is True


def test_post_category_relationship(app):
    with app.app_context():
        post = Post.query.filter_by(slug='simulacao-gromacs').first()
        assert post.categories.count() == 1
        assert post.categories.first().slug == 'quimica'

        category = Category.query.filter_by(slug='quimica').first()
        assert category.posts.count() == 1


def test_post_author_relationship(app):
    with app.app_context():
        post = Post.query.filter_by(slug='simulacao-gromacs').first()
        assert post.author.username == 'admin'


def test_comment_relationship(app):
    with app.app_context():
        post = Post.query.filter_by(slug='simulacao-gromacs').first()
        assert post.comments.count() == 1
        comment = post.comments.first()
        assert comment.content == 'Ótimo artigo!'
        assert comment.author.username == 'joe'


def test_deleting_post_cascades_to_comments(app):
    with app.app_context():
        post = Post.query.filter_by(slug='simulacao-gromacs').first()
        post_id = post.id
        db.session.delete(post)
        db.session.commit()
        assert Comment.query.filter_by(post_id=post_id).count() == 0


def test_tutorial_ordered_posts(app):
    with app.app_context():
        tutorial = Tutorial.query.filter_by(slug='trilha-quimica').first()
        admin = User.query.filter_by(username='admin').first()
        extra = Post(title='Avançado', slug='avancado', content='x', user_id=admin.id)
        db.session.add(extra)
        db.session.flush()
        # Insert an item that must be ordered before the seed item (order 1).
        db.session.add(TutorialPost(tutorial_id=tutorial.id, post_id=extra.id, order=0))
        db.session.commit()

        slug_order = [p.slug for p in tutorial.ordered_posts]
        assert slug_order == ['avancado', 'simulacao-gromacs']


def test_deleting_tutorial_removes_associations(app):
    with app.app_context():
        tutorial = Tutorial.query.filter_by(slug='trilha-quimica').first()
        tutorial_id = tutorial.id
        db.session.delete(tutorial)
        db.session.commit()
        assert TutorialPost.query.filter_by(tutorial_id=tutorial_id).count() == 0
