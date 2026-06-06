import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Asosiy konfiguratsiya klassi."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sizning-maxfiy-kalitingiz-bu-yerda'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'grammar_test.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'csrf-maxfiy-kalit'


class DevelopmentConfig(Config):
    """Dasturlash muhiti uchun konfiguratsiya."""
    DEBUG = True


class ProductionConfig(Config):
    """Ishlab chiqarish muhiti uchun konfiguratsiya."""
    DEBUG = False


class TestingConfig(Config):
    """Test muhiti uchun konfiguratsiya."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'test.db')
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
