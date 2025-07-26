import os
from datetime import timedelta

class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///customers.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SSL settings
    SSL_CERT_PATH = os.environ.get('SSL_CERT_PATH') or 'certs/cert.pem'
    SSL_KEY_PATH = os.environ.get('SSL_KEY_PATH') or 'certs/key.pem'
    SSL_ENABLED = os.environ.get('SSL_ENABLED', 'True').lower() == 'true'
    
    # Backup settings
    BACKUP_DIR = os.environ.get('BACKUP_DIR') or 'backups'
    MAX_BACKUP_AGE_DAYS = int(os.environ.get('MAX_BACKUP_AGE_DAYS', '30'))
    AUTO_BACKUP_ENABLED = os.environ.get('AUTO_BACKUP_ENABLED', 'True').lower() == 'true'
    BACKUP_SCHEDULE_HOURS = int(os.environ.get('BACKUP_SCHEDULE_HOURS', '24'))
    
    # GPG settings
    GPG_HOME_DIR = os.environ.get('GPG_HOME_DIR') or os.path.expanduser('~/.gnupg')
    GPG_KEYSERVER = os.environ.get('GPG_KEYSERVER') or 'keyserver.ubuntu.com'
    GPG_BACKUP_ENABLED = os.environ.get('GPG_BACKUP_ENABLED', 'False').lower() == 'true'
    
    # Logging settings
    LOG_DIR = os.environ.get('LOG_DIR') or 'logs'
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.path.join(LOG_DIR, 'app.log')
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get('SESSION_LIFETIME_HOURS', '2')))
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration."""
        # Create directories if they don't exist
        for dir_path in [Config.BACKUP_DIR, Config.LOG_DIR]:
            os.makedirs(dir_path, exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Override with more secure defaults for production
    SSL_ENABLED = True
    GPG_BACKUP_ENABLED = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
