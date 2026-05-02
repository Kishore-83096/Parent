import os

from app import create_app


config_name = os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "production"
app = create_app(config_name)

