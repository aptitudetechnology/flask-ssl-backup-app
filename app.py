"""
Flask Application with Modern SQLAlchemy Integration
Updated to use modern Flask-SQLAlchemy patterns with pathlib
"""

from flask import Flask
import logging
from pathlib import Path
from datetime import datetime
import sqlite3

from config import get_config, app_paths
from models import db, User, BackupRecord, CustomerService
from backup import DatabaseBackup
from backup_gpg import GPGBackup

# --- NEW: Import your backup_bp blueprint ---
from blueprints.backup_bp import backup_bp

# --- NEW: Import your core routes registration function ---
# Assuming 'routes.py' now contains 'register_core_routes(app)'
from routes import register_core_routes


def create_app(config_name=None):
    """Application factory with modern SQLAlchemy and pathlib integration"""

    config = get_config(config_name)

    app = Flask(
        __name__,
        static_folder=str(config.paths.static_dir),
        template_folder=str(config.paths.templates_dir)
    )

    # Configure Flask app
    app.config.update(config.get_flask_config())
    # --- NEW: Store config in app.config for easy access ---
    app.config['APP_CONFIG'] = config 


    # Modern SQLAlchemy configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{config.paths.database_file}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Setup logging
    setup_logging(app, config)

    # Initialize database with modern pattern
    db.init_app(app)

    # Create tables within app context
    with app.app_context():
        db.create_all()
        app.logger.info(f"Database initialized at: {config.paths.database_file}")

    # Setup security headers
    setup_security_headers(app, config)

    # Initialize backup systems
    backup_manager = DatabaseBackup(config)
    # Ensure gpg_backup is always an instance, even if recipient email is None,
    # so we don't get NoneType errors when calling its methods.
    # The methods themselves should handle the absence of a recipient email if needed.
    gpg_backup = GPGBackup(config) 

    # --- NEW: Store managers in app.extensions for easy access in blueprints/routes ---
    app.extensions['backup_manager'] = backup_manager
    app.extensions['gpg_backup'] = gpg_backup
    # app.extensions['db'] = db # You might also store db here if needed, but db.session is usually enough

    # --- NEW: Register blueprints ---
    app.register_blueprint(backup_bp)

    # --- NEW: Register core routes (from routes.py) ---
    # Call the function that registers your non-blueprint routes
    register_core_routes(app) 

    # --- REMOVED: Original register_routes call ---
    # register_routes(app, config, db, backup_manager, gpg_backup)

    return app


def setup_logging(app, config):
    """Setup application logging with pathlib"""
    try:
        # Ensure log directory exists
        config.paths.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup file handler
        log_file = config.paths.log_dir / 'app.log'

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL),
            format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
            handlers=[
                logging.FileHandler(str(log_file)),
                logging.StreamHandler()
            ]
        )

        app.logger.info(f"Logging initialized - Log file: {log_file}")

    except Exception as e:
        print(f"Failed to setup logging: {str(e)}")


def setup_security_headers(app, config):
    """Setup security headers"""

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'

        if config.FORCE_HTTPS:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response


if __name__ == '__main__':
    app = create_app()
    config = get_config() # Re-get config for standalone run, or pass from create_app if preferred

    # SSL configuration
    ssl_context = None
    if config.SSL_ENABLED:
        cert_file = config.paths.ssl_dir / 'cert.pem'
        key_file = config.paths.ssl_dir / 'key.pem'

        if cert_file.exists() and key_file.exists():
            ssl_context = (str(cert_file), str(key_file))
            app.logger.info("SSL enabled with certificates")
        else:
            app.logger.warning("SSL certificates not found, running without SSL")

    # Run the application
    app.run(
        #host=config.HOST,
        host='0.0.0.0',
        port=config.PORT,
        debug=config.DEBUG,
        ssl_context=ssl_context,
        threaded=True
    )