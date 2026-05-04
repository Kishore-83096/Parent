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


def create_app(config_name=None):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name or "development"])

    CORS(app, origins=app.config["CORS_ORIGINS"] or [])

    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

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
