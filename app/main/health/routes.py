from flask import Blueprint, abort, current_app, render_template, request

from app.main.health.services import check_database_connection, get_database_tables


health_bp = Blueprint("health", __name__, template_folder="templates")


def _is_local_request():
    remote_addr = request.remote_addr or ""
    host = (request.host or "").lower()
    host_name = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
    local_remote = (
        remote_addr == "::1"
        or remote_addr.startswith("127.")
        or remote_addr.startswith("::ffff:127.")
    )
    local_host = (
        host.startswith("[::1]")
        or host_name == "localhost"
        or host_name.startswith("127.")
    )
    return local_remote and local_host


@health_bp.get("/health")
def health_check():
    return {"status": "ok"}


@health_bp.get("/db/health")
def database_health_check():
    return check_database_connection()


@health_bp.get("/db/schema")
def database_schema():
    if not current_app.config.get("ENABLE_DB_SCHEMA_ROUTE") or not _is_local_request():
        abort(404)

    tables = get_database_tables()
    return render_template("db_schema.html", tables=tables)
