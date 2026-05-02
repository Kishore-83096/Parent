from flask import Blueprint, render_template
from sqlalchemy import text
from sqlalchemy.sql.compiler import IdentifierPreparer

from app import db


health_bp = Blueprint("health", __name__)
SENSITIVE_COLUMNS = {"password_hash", "card_number"}


@health_bp.get("/health")
def health_check():
    return {"status": "ok"}


@health_bp.get("/db/health")
def database_health_check():
    try:
        db.session.execute(text("SELECT 1")).scalar()
    except Exception as error:
        return {"database": "disconnected", "error": str(error)}, 500

    return {"database": "connected"}


@health_bp.get("/db/schema")
def database_schema():
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
    rows = db.session.execute(query, {"schema": "public"}).fetchall()
    constraints = get_column_constraints()

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

    return render_template("db_schema.html", tables=tables)


def get_column_constraints():
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
    rows = db.session.execute(query, {"schema": "public"}).fetchall()

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
