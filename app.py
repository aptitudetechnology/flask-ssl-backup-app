"""
Flask Application with Modern SQLAlchemy Integration
Updated to use modern Flask-SQLAlchemy patterns with pathlib
"""

from flask import Flask
import logging
from pathlib import Path
from datetime import datetime
import sqlite3

# Assuming config.py provides get_config and app_paths (which is an AppPaths instance)
from config import get_config, app_paths # app_paths here is likely an AppPaths instance from config.py

# Models and utilities
from models import db, User, BackupRecord, CustomerService
# Note: You have DatabaseBackup and GPGBackup imported globally here,
# and also imported within create_app and from utils.
# It's better to import them where they are used (e.g., within create_app or blueprints).
# For now, keeping your imports as is, but noting potential redundancy.
from backup import DatabaseBackup
from backup_gpg import GPGBackup # This is likely a different GPGBackup than utils.gpg_backup

# --- NEW: Import your backup_bp blueprint ---
from blueprints.backup import backup_bp

# --- NEW: Import your core routes registration function ---
# Assuming 'routes.py' now contains 'register_core_routes(app)'
from routes import register_core_routes

# --- Import Utility Functions (the GPGBackup causing the error) ---
from utils.gpg_backup import GPGBackup as UtilityGPGBackup # Alias to avoid conflict


def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    """Format a datetime for Jinja2 templates."""
    if value is None:
        return ''
    try:
        return value.strftime(format)
    except Exception:
        return str(value)


def create_app(config_name=None):
    """Application factory with modern SQLAlchemy and pathlib integration"""

    # 1. Get your custom config object (e.g., DevelopmentConfig instance)
    custom_config_instance = get_config(config_name)

    app = Flask(
        __name__,
        # These use custom_config_instance.paths which is fine
        static_folder=str(custom_config_instance.paths.static_dir),
        template_folder=str(custom_config_instance.paths.templates_dir)
    )

    # 2. Load attributes from your custom config instance into Flask's app.config dictionary
    app.config.update(custom_config_instance.get_flask_config())

    # --- CRITICAL FIX: Ensure AppPaths instance is explicitly in app.config ---
    # Your config.py's get_flask_config() should already put 'APP_PATHS': self.paths
    # but if not, ensure it's here:
    if 'APP_PATHS' not in app.config:
        app.config['APP_PATHS'] = custom_config_instance.paths # Store the AppPaths instance

    # --- Ensure other GPG/Backup specific config are in app.config ---
    # These should also be handled by get_flask_config in config.py
    # but as a fallback or explicit setting:
    app.config['GPG_BINARY_PATH'] = custom_config_instance.GPG_BINARY_PATH
    app.config['GPG_KEYSERVER'] = custom_config_instance.GPG_KEYSERVER
    app.config['LOG_LEVEL'] = custom_config_instance.LOG_LEVEL # Ensure log level is also passed

    # Modern SQLAlchemy configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{app.config["APP_PATHS"].database_file}' # Use app.config['APP_PATHS']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Setup logging (pass app.config to setup_logging if it needs it, or just app)
    setup_logging(app, app.config) # Pass app.config here

    # Initialize database with modern pattern
    db.init_app(app)

    # Create tables within app context
    with app.app_context():
        db.create_all()
        app.logger.info(f"Database initialized at: {app.config['APP_PATHS'].database_file}") # Use app.config['APP_PATHS']

    # Setup security headers (pass app.config here)
    setup_security_headers(app, app.config) # Pass app.config here

    # Initialize backup systems
    # --- CRITICAL FIX: Pass app.config to your utility classes ---
    # Assuming 'DatabaseBackup' and 'GPGBackup' (from backup.py/backup_gpg.py) also need app.config
    backup_manager = DatabaseBackup(app.config)
    gpg_backup_from_backup_gpg = GPGBackup(app.config) # Renamed to avoid confusion

    # This is the one that caused the error, from utils.gpg_backup.py
    # Pass app.config to it.
    utility_gpg_backup_instance = UtilityGPGBackup(app.config) # <--- THIS IS THE FIX FOR LINE 78

    # --- NEW: Store managers in app.extensions for easy access in blueprints/routes ---
    app.extensions['backup_manager'] = backup_manager
    app.extensions['gpg_backup'] = gpg_backup_from_backup_gpg # Your original GPGBackup
    app.extensions['utility_gpg_backup'] = utility_gpg_backup_instance # The one from utils
    # app.extensions['db'] = db # You might also store db here if needed, but db.session is usually enough


    # Register custom Jinja2 filters
    app.jinja_env.filters['datetimeformat'] = datetimeformat

    # --- NEW: Register blueprints ---
    app.register_blueprint(backup_bp)

    # --- NEW: Register core routes (from routes.py) ---
    # Call the function that registers your non-blueprint routes
    register_core_routes(app)

    # --- REMOVED: Original register_routes call ---
    # register_routes(app, config, db, backup_manager, gpg_backup)

    return app


def setup_logging(app, config): # Now 'config' here is app.config
    """Setup application logging with pathlib"""
    try:
        # Ensure log directory exists
        # Use app.config['APP_PATHS'] here
        app_paths_instance = config.get('APP_PATHS')
        if not app_paths_instance:
            raise ValueError("APP_PATHS not found in app.config for logging setup.")

        app_paths_instance.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup file handler
        log_file = app_paths_instance.log_dir / 'app.log'

        # Configure logging
        logging.basicConfig(
            # Use .get() for robustness, and convert string to actual logging level
            level=getattr(logging, config.get('LOG_LEVEL', 'INFO')),
            format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
            handlers=[
                logging.FileHandler(str(log_file)),
                logging.StreamHandler()
            ]
        )

        app.logger.info(f"Logging initialized - Log file: {log_file}")

    except Exception as e:
        print(f"Failed to setup logging: {str(e)}")


def setup_security_headers(app, config): # Now 'config' here is app.config
    """Setup security headers"""

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Use .get() for config values
        if config.get('FORCE_HTTPS'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response


if __name__ == '__main__':
    app = create_app()
    # When running directly, access config from app.config
    current_app_config = app.config # Get the fully configured app.config

    # SSL configuration
    ssl_context = None
    # Use .get() for config values and APP_PATHS
    if current_app_config.get('SSL_ENABLED'):
        app_paths_instance = current_app_config.get('APP_PATHS')
        if not app_paths_instance:
            print("ERROR: APP_PATHS not found in app.config for SSL setup.")
        else:
            cert_file = app_paths_instance.ssl_dir / 'cert.pem'
            key_file = app_paths_instance.ssl_dir / 'key.pem'

            print(f"DEBUG: SSL_ENABLED is True in config.")
            print(f"DEBUG: Checking for SSL cert at: {cert_file}")
            print(f"DEBUG: Checking for SSL key at: {key_file}")

            if cert_file.exists() and key_file.exists():
                ssl_context = (str(cert_file), str(key_file))
                app.logger.info("SSL enabled with certificates")
                print(f"DEBUG: SSL context set with: {ssl_context}")
            else:
                app.logger.warning("SSL certificates not found, running without SSL")

    # Run the application
    app.run(
        host=current_app_config.get('HOST', '0.0.0.0'), # Use .get()
        port=current_app_config.get('PORT', 5000),     # Use .get()
        debug=current_app_config.get('DEBUG', False),  # Use .get()
        ssl_context=ssl_context,
        threaded=True
    )