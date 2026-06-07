import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app
from sqlalchemy import text
from sqlalchemy.sql.compiler import IdentifierPreparer

from app import db


SENSITIVE_COLUMNS = {"password_hash", "card_number"}


def cleanup_expired_messenger_stories():
    base_urls = get_messenger_service_urls()
    internal_service_token = current_app.config.get("INTERNAL_SERVICE_TOKEN") or ""
    cleanup_timeout = current_app.config.get(
        "MESSENGER_CLEANUP_TIMEOUT_SECONDS",
        current_app.config["MESSENGER_SERVICE_TIMEOUT_SECONDS"],
    )

    if not base_urls:
        return {"ok": False, "message": "Messenger service URL is not configured."}, 503

    if not internal_service_token:
        return {"ok": False, "message": "Internal service token is not configured."}, 503

    attempted_urls = []

    for base_url in base_urls:
        cleanup_url = f"{base_url.rstrip('/')}/stories/internal/cleanup-expired/"
        attempted_urls.append(cleanup_url)
        cleanup_response, response_status = request_messenger_story_cleanup(
            cleanup_url,
            internal_service_token,
            cleanup_timeout,
        )

        if cleanup_response is not None:
            cleanup_response["messenger_url"] = base_url
            return cleanup_response, response_status

    return {
        "ok": False,
        "message": "Messenger cleanup service is unavailable.",
        "messenger_urls": attempted_urls,
    }, 503


def get_messenger_service_urls():
    service_urls = current_app.config.get("MESSENGER_SERVICE_URLS")
    if not service_urls:
        service_urls = [current_app.config.get("MESSENGER_SERVICE_URL") or ""]
    elif isinstance(service_urls, str):
        service_urls = [service_urls]

    return [str(url).strip().rstrip("/") for url in service_urls if str(url).strip()]


def request_messenger_story_cleanup(cleanup_url, internal_service_token, timeout):
    cleanup_request = Request(
        cleanup_url,
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "X-Internal-Service-Token": internal_service_token,
        },
        method="POST",
    )

    try:
        with urlopen(
            cleanup_request,
            timeout=timeout,
        ) as response:
            response_status = response.status
            response_body = decode_json_response(response.read())
    except HTTPError as error:
        return {
            "ok": False,
            "message": "Messenger cleanup request failed.",
            "messenger": decode_json_response(error.read()),
        }, error.code
    except (URLError, TimeoutError) as error:
        current_app.logger.warning(
            "Messenger cleanup service is unavailable at %s: %s",
            cleanup_url,
            error,
        )
        return None, None

    return {
        "ok": 200 <= response_status < 300,
        "messenger": response_body,
    }, response_status


def decode_json_response(response_body):
    try:
        return json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return {}


def check_database_connection():
    try:
        db.session.execute(text("SELECT 1")).scalar()
    except Exception as error:
        return {"database": "disconnected", "error": str(error)}, 500

    return {"database": "connected"}, 200


def get_database_tables(schema="public"):
    query = text(
        """
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = :schema
        ORDER BY table_name, ordinal_position
        """
    )
    rows = db.session.execute(query, {"schema": schema}).fetchall()
    constraints = get_column_constraints(schema)

    tables = {}
    for row in rows:
        table = tables.setdefault(row.table_name, {"columns": [], "rows": []})
        column_constraints = constraints.get((row.table_name, row.column_name), [])
        if row.is_nullable == "NO":
            column_constraints = ["NOT NULL", *column_constraints]

        table["columns"].append(
            {
                "column": row.column_name,
                "type": row.data_type,
                "nullable": row.is_nullable == "YES",
                "max_length": row.character_maximum_length,
                "constraints": column_constraints,
            }
        )

    load_table_rows(tables)
    return tables


def load_table_rows(tables):
    preparer = IdentifierPreparer(db.engine.dialect)
    for table_name, table in tables.items():
        quoted_table = preparer.quote(table_name)
        result = db.session.execute(text(f"SELECT * FROM {quoted_table}"))

        for data_row in result.mappings():
            table["rows"].append(
                {
                    column: mask_value(column, value)
                    for column, value in data_row.items()
                }
            )


def get_column_constraints(schema="public"):
    query = text(
        """
        SELECT
            tc.table_name,
            kcu.column_name,
            tc.constraint_name,
            tc.constraint_type
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
            AND tc.table_name = kcu.table_name
        WHERE tc.table_schema = :schema
        ORDER BY tc.table_name, kcu.ordinal_position
        """
    )
    rows = db.session.execute(query, {"schema": schema}).fetchall()

    constraints = {}
    for row in rows:
        label = f"{row.constraint_type}: {row.constraint_name}"
        constraints.setdefault((row.table_name, row.column_name), []).append(label)

    return constraints


def mask_value(column, value):
    if value is None:
        return None

    if column in SENSITIVE_COLUMNS and column == "password_hash":
        return "hidden"

    if column in SENSITIVE_COLUMNS and column == "card_number":
        value = str(value)
        return f"**** **** **** {value[-4:]}" if len(value) >= 4 else "****"

    return value
