"""SQLite helpers for TeachAI."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import click
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    """Return one database connection per request."""
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db() -> None:
    """Create all tables when they do not exist yet."""
    connection = get_db()
    schema_path = Path(__file__).with_name("schema.sql")
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    connection.commit()


def query(sql: str, parameters: tuple | list = (), one: bool = False):
    cursor = get_db().execute(sql, parameters)
    rows = cursor.fetchall()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql: str, parameters: tuple | list = ()) -> int:
    connection = get_db()
    cursor = connection.execute(sql, parameters)
    connection.commit()
    return cursor.lastrowid


@click.command("init-db")
def init_db_command() -> None:
    """Create the database tables and exit."""
    init_db()
    click.echo("Initialized the TeachAI database.")


@click.command("seed-demo")
def seed_demo_command() -> None:
    """Create (or refresh) the local demo account."""
    from teachai.seed import seed_demo

    created = seed_demo()
    if created:
        click.echo("Demo account created: demo@teachai.local / teachai123")
    else:
        click.echo("Demo account already exists. Delete instance/teachai.sqlite3 to recreate it.")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_demo_command)
