"""
Application configuration management.
Simplified for local personal blog use.
"""

import os
import tempfile
from datetime import timedelta

class Config:
    """Base configuration class."""
    
    # Flask Core
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-personal-blog'
    DEBUG = False
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(__file__), 'instance', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Pagination
    POSTS_PER_PAGE = 10
    COMMENTS_PER_PAGE = 12
    MAX_PER_PAGE = 100

    # SEO (Dynamic)
    SEO_SITE_NAME = 'AENTECH'
    SEO_SITE_URL = os.environ.get('SEO_SITE_URL') or 'https://aentech.pythonanywhere.com'
    SEO_DEFAULT_DESCRIPTION = (
        'Plataforma AENTECH — Ciência & Tecnologia: artigos, tutoriais e ferramentas '
        'de computação científica, simulação molecular, química teórica e quimioinformática.'
    )
    SEO_DEFAULT_KEYWORDS = (
        'AENTECH, ciência e tecnologia, computação científica, simulação molecular, '
        'dinâmica molecular, GROMACS, química teórica, quimioinformática, RDKit, '
        'físico-química, machine learning, pesquisa STEM'
    )
    SEO_DEFAULT_IMAGE = '/static/images/dos-pdos.jpeg'
    SEO_LOGO_PATH = '/static/favicon.ico'
    SEO_LOCALE = 'pt_BR'
    SEO_LANGUAGE = 'pt-BR'
    SEO_TWITTER_HANDLE = os.environ.get('SEO_TWITTER_HANDLE') or '@aentech'
    SEO_THEME_COLOR = '#4f46e5'

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'instance', 'dev_app.db')

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration: isolated temp DB and CSRF disabled."""
    TESTING = True
    DEBUG = False
    SECRET_KEY = 'testing-secret-key'
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(
        tempfile.mkdtemp(prefix='aentech-test-'), 'test_app.db'
    )

# Configuration mapping
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
