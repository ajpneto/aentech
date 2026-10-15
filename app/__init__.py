"""
Main application package initialization following best practices.
Uses factory pattern with environment-based configuration.
"""

import os
import sys
from typing import Optional, Union, Dict, Any
from importlib import import_module
from dotenv import load_dotenv

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_moment import Moment


# ============================================================================
# Load environment variables FIRST
# ============================================================================
def _load_environment() -> bool:
    """
    Safely load environment variables from .env file.
    
    Returns:
        bool: True if .env was loaded, False otherwise
    """
    # Try to load from project root
    env_paths = [
        os.path.join(os.path.dirname(__file__), '..', '.env'),
        os.path.join(os.path.dirname(__file__), '.env'),
        os.path.join(os.getcwd(), '.env')
    ]
    
    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
            print(f"Loaded environment from: {env_path}")
            return True
    
    print("Warning: No .env file found. Using system environment variables.")
    return False


# Load environment variables at module import
_load_environment()


# ============================================================================
# Extension instances
# ============================================================================
db = SQLAlchemy(session_options={"autoflush": False})
bootstrap = Bootstrap()
moment = Moment()


# ============================================================================
# Configuration Management
# ============================================================================
class ConfigManager:
    """Manages application configuration with validation."""
    
    @staticmethod
    def load_config(app: Flask, config_object: Optional[Union[str, object]] = None) -> None:
        """
        Load configuration into Flask app with validation.
        
        Args:
            app: Flask application instance
            config_object: Configuration object or string (e.g., 'config.DevelopmentConfig')
        """
        if config_object:
            # User-specified configuration
            app.config.from_object(config_object)
        else:
            # Environment-based configuration
            app_settings = os.environ.get("APP_SETTINGS")
            
            if not app_settings:
                # Fallback to development if not specified
                app_settings = "config.DevelopmentConfig"
                print(f"Warning: APP_SETTINGS not set. Defaulting to: {app_settings}")
            
            try:
                app.config.from_object(app_settings)
                print(f"Loaded configuration from: {app_settings}")
            except (ImportError, AttributeError) as e:
                print(f"Error: Could not load configuration '{app_settings}': {e}")
                print("Falling back to default configuration.")
                # Load minimal safe defaults
                app.config.from_object("config.Config")
        
        # Validate critical configurations
        ConfigManager._validate_config(app)
    
    @staticmethod
    def _validate_config(app: Flask) -> None:
        """Validate critical configuration values."""
        errors = []
        
        # Check for secret key
        if not app.config.get('SECRET_KEY') or app.config['SECRET_KEY'] == 'please-change-this':
            errors.append("SECRET_KEY is not set or is using default value")
        
        # Database URL check (only warn, not error)
        if not app.config.get('SQLALCHEMY_DATABASE_URI'):
            print("Warning: SQLALCHEMY_DATABASE_URI is not configured")
        
        # Debug mode warnings
        if app.config.get('DEBUG') and app.config.get('ENV') == 'production':
            print("WARNING: DEBUG mode is enabled in production!")
        
        # Validate pagination settings
        max_per_page = app.config.get('MAX_PER_PAGE', 100)
        posts_per_page = app.config.get('POSTS_PER_PAGE', 10)
        
        if posts_per_page > max_per_page:
            app.config['POSTS_PER_PAGE'] = max_per_page
            print(f"Adjusted POSTS_PER_PAGE to MAX_PER_PAGE: {max_per_page}")
        
        if errors:
            error_msg = "Configuration validation failed:\n  - " + "\n  - ".join(errors)
            if app.config.get('ENV') == 'production':
                raise RuntimeError(error_msg)
            else:
                print(f"Configuration warnings:\n  - " + "\n  - ".join(errors))


# ============================================================================
# Main Application Class (Factory Pattern)
# ============================================================================
class FlaskApplication:
    """Main application class following Factory Pattern."""
    
    def __init__(self, config_object: Optional[Union[str, object]] = None):
        """
        Initialize the Flask application factory.
        
        Args:
            config_object: Configuration object or string to use
        """
        self.app = None
        
        if config_object:
            self.create_app(config_object)
    
    def create_app(self, config_object: Optional[Union[str, object]] = None) -> Flask:
        """
        Create and configure the Flask application instance.
        
        Args:
            config_object: Configuration object or string
            
        Returns:
            Flask: Configured Flask application instance
        """
        self.app = Flask(__name__)
        
        # Load configuration with validation
        ConfigManager.load_config(self.app, config_object)
        
        # Initialize extensions
        self._initialize_extensions()
        
        # Register blueprints
        self._register_blueprints()
        
        # Initialize database migrations
        Migrate(self.app, db)
        
        # Register shell context
        self._register_shell_context()
        
        # Register error handlers
        self._register_error_handlers()
        
        # Register context processors
        self._register_context_processors()
        
        return self.app
    
    def _initialize_extensions(self) -> None:
        """Initialize all Flask extensions with the application."""
        db.init_app(self.app)
        bootstrap.init_app(self.app)
        moment.init_app(self.app)
    
    def _register_blueprints(self) -> None:
        """Register all application blueprints."""
        blueprint_modules = ('main', 'auth')
        
        for module_name in blueprint_modules:
            try:
                module = import_module(f'app.{module_name}.views')
                if hasattr(module, 'blueprint'):
                    self.app.register_blueprint(module.blueprint)
                    print(f"Registered blueprint: {module.blueprint.name}")
                else:
                    print(f"Warning: Module '{module_name}' has no 'blueprint' attribute")
            except ImportError as e:
                print(f"Warning: Could not import blueprint module '{module_name}': {e}")
            except Exception as e:
                print(f"Error registering blueprint '{module_name}': {e}")
    
    def _register_shell_context(self) -> None:
        """Register shell context objects for Flask shell."""
        try:
            from app.models import User, Post, Comment, Category, Tutorial, TutorialPost
            
            @self.app.shell_context_processor
            def make_shell_context() -> Dict[str, Any]:
                return {
                    'app': self.app,
                    'db': db,
                    'User': User,
                    'Post': Post,
                    'Comment': Comment,
                    'Category': Category,
                    'Tutorial': Tutorial,
                    'TutorialPost': TutorialPost,
                    'config': self.app.config
                }
        except ImportError as e:
            print(f"Warning: Could not import models for shell context: {e}")
    
    def _register_error_handlers(self) -> None:
        """Register error handlers for common HTTP errors."""
        
        @self.app.errorhandler(404)
        def page_not_found(e):
            return self._render_error_template(404, "Page not found"), 404
        
        @self.app.errorhandler(500)
        def internal_server_error(e):
            # Log the error
            if self.app.config.get('DEBUG'):
                print(f"Internal Server Error: {e}")
            return self._render_error_template(500, "Internal server error"), 500
    
    def _render_error_template(self, code: int, message: str):
        """Render error template."""
        from flask import render_template
        try:
            return render_template(f'errors/{code}.html', error=message)
        except:
            return f"<h1>{code} Error</h1><p>{message}</p>"
    
    def _register_context_processors(self) -> None:
        """Register context processors for templates."""
        
        @self.app.context_processor
        def inject_config():
            """Make config available in templates."""
            return dict(config=self.app.config)
        
        @self.app.context_processor
        def inject_utility_functions():
            """Make utility functions available in templates."""
            from datetime import datetime
            return dict(
                now=datetime.utcnow,
                len=len,
                str=str
            )

        @self.app.context_processor
        def inject_seo():
            """Make dynamic SEO metadata available to every template."""
            try:
                from app.seo import build_seo
                return dict(seo=build_seo())
            except Exception as e:  # pragma: no cover - never break rendering for SEO
                print(f"Warning: Could not build SEO context: {e}")
                return dict(seo={})
    
    def run(self, **kwargs) -> None:
        """Run the Flask application."""
        if not self.app:
            self.create_app()
        
        # Set default run parameters based on environment
        run_defaults = {}
        
        if self.app.config.get('DEBUG'):
            run_defaults['debug'] = True
            run_defaults['use_reloader'] = True
        
        if self.app.config.get('ENV') == 'production':
            run_defaults['host'] = '0.0.0.0'
        
        # Merge defaults with provided kwargs
        run_kwargs = {**run_defaults, **kwargs}
        
        self.app.run(**run_kwargs)
    
    def get_app(self) -> Flask:
        """Get the current Flask application instance."""
        if not self.app:
            self.create_app()
        return self.app
    
    def get_db(self):
        """Get the database instance."""
        return db
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Safely get a configuration value."""
        if not self.app:
            self.create_app()
        return self.app.config.get(key, default)


# ============================================================================
# Backward Compatibility Functions
# ============================================================================
def create_app(config_object: Optional[Union[str, object]] = None) -> Flask:
    """
    Factory function for creating the Flask application.
    Maintains backward compatibility with the original interface.
    
    Args:
        config_object: Configuration object or string
        
    Returns:
        Flask: Configured Flask application instance
    """
    # Use the FlaskApplication class internally
    factory = FlaskApplication(config_object)
    return factory.get_app()


def register_extensions(app: Flask) -> None:
    """Register Flask extensions (backward compatibility)."""
    db.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)


def register_blueprints(app: Flask) -> None:
    """Register application blueprints (backward compatibility)."""
    for module_name in ('main', 'auth'):
        try:
            module = import_module('app.{}.views'.format(module_name))
            app.register_blueprint(module.blueprint)
        except ImportError as e:
            print(f"Warning: Could not import blueprint module '{module_name}': {e}")


def register_shell_context(app: Flask) -> None:
    """Register shell context objects (backward compatibility)."""
    try:
        from app.models import User, Post, Comment, Category
        
        def shell_context():
            return {
                'app': app,
                'db': db,
                'User': User,
                'Post': Post,
                'Comment': Comment,
                'Category': Category
            }
        
        app.shell_context_processor(shell_context)
    except ImportError as e:
        print(f"Warning: Could not import models for shell context: {e}")


# ============================================================================
# Global Instances and Convenience Functions
# ============================================================================

# Create a global application instance (for backward compatibility)
flask_app = FlaskApplication()

# Convenience function to get current configuration
def get_config(key: str, default: Any = None) -> Any:
    """
    Get a configuration value from the current app.
    
    Args:
        key: Configuration key
        default: Default value if key doesn't exist
        
    Returns:
        Configuration value or default
    """
    try:
        return current_app.config.get(key, default)
    except RuntimeError:
        # Outside of application context
        return default


# Convenience function for pagination
def get_pagination_defaults() -> Dict[str, int]:
    """
    Get pagination defaults from configuration.
    
    Returns:
        Dict with pagination settings
    """
    try:
        return {
            'posts_per_page': current_app.config.get('POSTS_PER_PAGE', 10),
            'comments_per_page': current_app.config.get('COMMENTS_PER_PAGE', 12),
            'max_per_page': current_app.config.get('MAX_PER_PAGE', 100)
        }
    except RuntimeError:
        # Outside of application context, return defaults
        return {
            'posts_per_page': 10,
            'comments_per_page': 12,
            'max_per_page': 100
        }


# ============================================================================
# Main Entry Point
# ============================================================================
if __name__ == '__main__':
    # Determine configuration from environment
    app_settings = os.environ.get("APP_SETTINGS")
    
    if app_settings:
        print(f"Starting with configuration: {app_settings}")
        app = create_app(app_settings)
    else:
        print("No APP_SETTINGS found. Using default configuration.")
        app = create_app()
    
    # Run the application
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(
        debug=debug_mode,
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", 5000))
    )
