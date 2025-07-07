"""
Configuration management for Dubstep Discovery Agent - Flask Web Version
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Flask application configuration."""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///dubstep_discovery_web.db'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # API Keys
    SOUNDCLOUD_CLIENT_ID = os.environ.get('SOUNDCLOUD_CLIENT_ID', '')
    REDDIT_CLIENT_ID = os.environ.get('REDDIT_CLIENT_ID', '')
    REDDIT_SECRET = os.environ.get('REDDIT_SECRET', '')
    REDDIT_USER_AGENT = os.environ.get('REDDIT_USER_AGENT', 'DubstepDiscoveryBot/1.0')
    YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
    SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', '')
    SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', '')
    APPLE_MUSIC_TOKEN = os.environ.get('APPLE_MUSIC_TOKEN', '')
    
    # Email Configuration
    EMAIL_SENDER_ADDRESS = os.environ.get('EMAIL_SENDER_ADDRESS', '')
    SMTP_SERVER = os.environ.get('SMTP_SERVER', '')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    
    # Security
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY', '')
    RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY', '')
    
    # Rate Limiting
    VOTES_PER_IP_PER_HOUR = int(os.environ.get('VOTES_PER_IP_PER_HOUR', 10))
    VOTES_PER_USER_PER_DAY = int(os.environ.get('VOTES_PER_USER_PER_DAY', 50))
    
    # Anti-Fraud
    MIN_ACCOUNT_AGE_DAYS = int(os.environ.get('MIN_ACCOUNT_AGE_DAYS', 7))
    TRUST_SCORE_THRESHOLD = float(os.environ.get('TRUST_SCORE_THRESHOLD', 0.7))
    FRAUD_DETECTION_ENABLED = os.environ.get('FRAUD_DETECTION_ENABLED', 'True').lower() == 'true'
    
    # Output Configuration
    OUTPUT_DIR = os.environ.get('OUTPUT_DIR', './output')
    CHART_SIZE = int(os.environ.get('CHART_SIZE', 50))
    UPDATE_FREQUENCY_HOURS = int(os.environ.get('UPDATE_FREQUENCY_HOURS', 24))
    
    # Flask-specific
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = False
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
    
    # Session Configuration
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', './uploads')
    
    @staticmethod
    def validate_required_settings():
        """Validate that required settings are present."""
        missing = []
        
        # Check for critical settings
        if not Config.SECRET_KEY or Config.SECRET_KEY == 'dev-secret-key-change-in-production':
            missing.append("SECRET_KEY (using development key)")
        
        # API keys are optional for basic functionality
        optional_missing = []
        
        if not Config.SOUNDCLOUD_CLIENT_ID:
            optional_missing.append("SOUNDCLOUD_CLIENT_ID")
        if not Config.REDDIT_CLIENT_ID:
            optional_missing.append("REDDIT_CLIENT_ID")
        if not Config.REDDIT_SECRET:
            optional_missing.append("REDDIT_SECRET")
        if not Config.YOUTUBE_API_KEY:
            optional_missing.append("YOUTUBE_API_KEY")
        if not Config.SPOTIFY_CLIENT_ID:
            optional_missing.append("SPOTIFY_CLIENT_ID")
        if not Config.SPOTIFY_CLIENT_SECRET:
            optional_missing.append("SPOTIFY_CLIENT_SECRET")
        
        return {
            'critical': missing,
            'optional': optional_missing
        }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///dev_dubstep_discovery.db'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    
    # Production database should be PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:pass@localhost/dubstep_discovery'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test-secret-key'
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
