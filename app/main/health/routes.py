from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from app.main.health.services import (
    check_database_connection,
    cleanup_expired_messenger_stories,
    get_database_tables,
)


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


@health_bp.post("/db/schema/stories/cleanup-expired")
def cleanup_expired_story_data():
    if not current_app.config.get("ENABLE_DB_SCHEMA_ROUTE") or not _is_local_request():
        abort(404)

    cleanup_response, response_status = cleanup_expired_messenger_stories()
    if cleanup_response.get("ok"):
        result = cleanup_response.get("messenger", {}).get("result", {})
        flash(
            (
                f'Expired story cleanup completed: {result.get("expired_stories", 0)} '
                f'stories marked expired and {result.get("media_cleaned", 0)} '
                'media items cleaned.'
            ),
            "success",
        )
    else:
        messenger_response = cleanup_response.get("messenger", {})
        flash(
            (
                messenger_response.get("message")
                or cleanup_response.get("message")
                or f"Expired story cleanup failed with status {response_status}."
            ),
            "error",
        )

    return redirect(url_for("health.database_schema"))
