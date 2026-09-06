import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_url() -> str:
    """
    Render/Heroku both provide DATABASE_URL, but older Heroku URLs use the
    'postgres://' scheme which SQLAlchemy 1.4+/psycopg2 no longer accepts.
    Normalize it, and fall back to a local SQLite file for dev.
    """
    url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'sparefixer.db')}")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MIN", 60)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.environ.get("JWT_REFRESH_TOKEN_EXPIRES_DAYS", 30)))
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_TYPE = "Bearer"

    CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]

    RECOGNITION_PROVIDER = os.environ.get("RECOGNITION_PROVIDER", "mock")
    RECOGNITION_API_KEY = os.environ.get("RECOGNITION_API_KEY", "")

    PAYMENT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "stripe")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
    RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

    CURRENCY = os.environ.get("CURRENCY", "INR")
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

    JSON_SORT_KEYS = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return CONFIG_MAP.get(env, DevelopmentConfig)
