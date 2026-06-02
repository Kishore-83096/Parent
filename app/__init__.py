from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.config import config_by_name


db = SQLAlchemy()
ma = Marshmallow()
jwt = JWTManager()
migrate = Migrate()


def include_object(object_, name, type_, reflected, compare_to):
    # Parent and Messenger share a database. Do not treat Django-owned tables
    # as removed just because they are absent from Parent's SQLAlchemy metadata.
    if type_ == "table" and reflected and compare_to is None:
        return False

    return True


def create_app(config_name=None):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name or "development"])

    CORS(app, origins=app.config["CORS_ORIGINS"] or [])

    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db, include_object=include_object)

    from app.main.api.errors import register_api_error_handlers
    from app.main.api.routes import api_bp
    from app.main.health.routes import health_bp

    register_api_error_handlers(app, jwt)
    app.register_blueprint(api_bp, url_prefix="/parent")
    app.register_blueprint(health_bp)

    @app.get("/")
    def index():
        return {"message": "Hai to the Parent service of Parrot."}

    return app
