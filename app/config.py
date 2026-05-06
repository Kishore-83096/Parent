import os
from datetime import timedelta

from dotenv import load_dotenv


load_dotenv()


def get_database_url():
    database_url = os.getenv("DATABASE_URL", "sqlite:///parent.db")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    return database_url


def get_engine_options(database_url):
    options = {"pool_pre_ping": True}

    if database_url.startswith("postgresql://"):
        options["connect_args"] = {"sslmode": os.getenv("DB_SSLMODE", "require")}

    return options


def get_allowed_hosts():
    hosts = os.getenv("ALLOWED_HOSTS", "")
    return [host.strip() for host in hosts.split(",") if host.strip()]


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key")
    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_ENGINE_OPTIONS = get_engine_options(SQLALCHEMY_DATABASE_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = get_allowed_hosts()
    CLOUDINARY_PROFILE_FOLDER = os.getenv("CLOUDINARY_PROFILE_FOLDER", "MAIN/Display_pics")
    INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    MESSAGING_JWT_SECRET = os.getenv("MESSAGING_JWT_SECRET", "")
    MESSAGING_JWT_ISSUER = os.getenv("MESSAGING_JWT_ISSUER", "parrot-parent")
    MESSAGING_JWT_AUDIENCE = os.getenv("MESSAGING_JWT_AUDIENCE", "parrot-messenger")
    MESSAGING_TOKEN_TTL_SECONDS = int(os.getenv("MESSAGING_TOKEN_TTL_SECONDS", 300))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
