from flask import jsonify
from flask_jwt_extended.exceptions import JWTExtendedException
from marshmallow import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException


def register_api_error_handlers(app, jwt):
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify({"message": "Validation failed.", "errors": error.messages}), 400

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        app.logger.exception("Database error", exc_info=error)
        return jsonify({"message": "A database error occurred."}), 500

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        response = error.get_response()
        response.data = jsonify({"message": error.description}).data
        response.content_type = "application/json"
        return response

    @app.errorhandler(JWTExtendedException)
    def handle_jwt_error(error):
        return jsonify({"message": str(error)}), 401

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception("Unhandled error", exc_info=error)
        return jsonify({"message": "An unexpected error occurred."}), 500

    @jwt.unauthorized_loader
    def handle_missing_token(reason):
        return jsonify({"message": reason}), 401

    @jwt.invalid_token_loader
    def handle_invalid_token(reason):
        return jsonify({"message": reason}), 422

    @jwt.expired_token_loader
    def handle_expired_token(jwt_header, jwt_payload):
        return jsonify({"message": "Session has expired. Please login again."}), 401

    @jwt.needs_fresh_token_loader
    def handle_fresh_token_required(jwt_header, jwt_payload):
        return jsonify({"message": "Fresh token required."}), 401

    @jwt.revoked_token_loader
    def handle_revoked_token(jwt_header, jwt_payload):
        return jsonify({"message": "Token has been revoked."}), 401
