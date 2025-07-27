"""
Configuration module with pathlib integration
Handles all application settings
"""

import os
from pathlib import Path
from datetime import timedelta
from typing import Optional, Dict, Any

from paths import AppPaths  # ✅ Use external AppPaths


class Config:
    """Base configuration class with pathlib integration."""

    def __init__(self):
        """Initialize configuration with path manager"""
        self.paths = AppPaths()

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database settings
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            return db_url
        return f'sqlite:///{self.paths.database_file}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SSL settings
    @property
    def SSL_CERT_PATH(self):
        return str(self.paths.ssl_cert_file)

    @property
    def SSL_KEY_PATH(self):
        return str(self.paths.ssl_key_file)

    SSL_ENABLED = os.environ.get('SSL_ENABLED', 'True').lower() == 'true'

    # Backup settings
    @property
    def BACKUP_DIR(self):
        return str(self.paths.backup_dir)

    MAX_BACKUP_AGE_DAYS = int(os.environ.get('MAX_BACKUP_AGE_DAYS', '30'))
    AUTO_BACKUP_ENABLED = os.environ.get('AUTO_BACKUP_ENABLED', 'True').lower() == 'true'
    BACKUP_SCHEDULE_HOURS = int(os.environ.get('BACKUP_SCHEDULE_HOURS', '24'))

    # GPG settings
    @property
    def GPG_HOME_DIR(self):
        return str(self.paths.gpg_home_dir)

    GPG_KEYSERVER = os.environ.get('GPG_KEYSERVER') or 'keyserver.ubuntu.com'
    GPG_BACKUP_ENABLED = os.environ.get('GPG_BACKUP_ENABLED', 'False').lower() == 'true'
    GPG_RECIPIENT_EMAIL = os.environ.get('GPG_RECIPIENT_EMAIL')

    # Logging settings
    @property
    def LOG_DIR(self):
        return str(self.paths.log_dir)

    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'

    @property
    def LOG_FILE(self):
        return str(self.paths.log_file)

    # Application settings
    HOST = os.environ.get('HOST') or '127.0.0.1'
    PORT = int(os.environ.get('PORT', '5000'))
    DEBUG = False
    TESTING = False
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'False').lower() == 'true'

    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get('SESSION_LIFETIME_HOURS', '2')))

    def init_app(self, app):
        """Initialize application with configuration."""
        self.paths._ensure_directories()
        validation_results = self.paths.validate_paths()
        for path_name, is_valid in validation_results.items():
            if not is_valid and not path_name.endswith('_exists'):
                print(f"Warning: {path_name} validation failed")
        app.config.update(self.get_flask_config())

    def get_flask_config(self) -> Dict[str, Any]:
        """Get Flask-compatible configuration dictionary"""
        return {
            'SECRET_KEY': self.SECRET_KEY,
            'SQLALCHEMY_DATABASE_URI': self.SQLALCHEMY_DATABASE_URI,
            'SQLALCHEMY_TRACK_MODIFICATIONS': self.SQLALCHEMY_TRACK_MODIFICATIONS,
            'PERMANENT_SESSION_LIFETIME': self.PERMANENT_SESSION_LIFETIME,
            'DEBUG': self.DEBUG,
            'TESTING': self.TESTING
        }


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SSL_ENABLED = True
    GPG_BACKUP_ENABLED = True
    FORCE_HTTPS = True

    def __init__(self):
        super().__init__()
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY must be set in production")


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    WTF_CSRF_ENABLED = False

    def __init__(self):
        super().__init__()
        self._test_db_uri = 'sqlite:///:memory:'

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return self._test_db_uri


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: Optional[str] = None) -> Config:
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    config_class = config.get(config_name, config['default'])
    return config_class()


# Global path manager instance for convenience
app_paths = AppPaths()


# Utility functions
def init_app(app):
    config_instance = get_config()
    config_instance.init_app(app)


def get_backup_dir() -> Path:
    return app_paths.backup_dir


def get_log_dir() -> Path:
    return app_paths.log_dir


def get_ssl_paths() -> tuple[Path, Path]:
    return app_paths.ssl_cert_file, app_paths.ssl_key_file


if __name__ == "__main__":
    print("Testing configuration...")

    config_instance = get_config('development')
    print(f"Database URI: {config_instance.SQLALCHEMY_DATABASE_URI}")
    print(f"SSL Cert: {config_instance.SSL_CERT_PATH}")
    print(f"Backup Dir: {config_instance.BACKUP_DIR}")
    print(f"Log File: {config_instance.LOG_FILE}")

    validation = config_instance.paths.validate_paths()
    print(f"Path validation: {validation}")
    print("Directories created successfully!")
