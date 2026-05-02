from flask import Flask
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

    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    from app.resources.auth import auth_bp
    from app.resources.health import health_bp
    from app.resources.profile import profile_bp

    app.register_blueprint(auth_bp, url_prefix="/parent/auth")
    app.register_blueprint(health_bp)
    app.register_blueprint(profile_bp, url_prefix="/parent/profile")

    @app.get("/")
    def index():
        return {"message": "Hai to the Parent service of Parrot."}

    return app
