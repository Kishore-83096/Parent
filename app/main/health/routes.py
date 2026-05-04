from flask import Blueprint, render_template

from app.main.health.services import check_database_connection, get_database_tables


health_bp = Blueprint("health", __name__, template_folder="templates")


@health_bp.get("/health")
def health_check():
    return {"status": "ok"}


@health_bp.get("/db/health")
def database_health_check():
    return check_database_connection()


@health_bp.get("/db/schema")
def database_schema():
    tables = get_database_tables()
    return render_template("db_schema.html", tables=tables)
