"""TeachAI application factory."""
from __future__ import annotations

import hmac
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

from teachai import db


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", ""),
        DATABASE=os.environ.get(
            "TEACHAI_DATABASE", str(instance_path / "teachai.sqlite3")
        ),
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_NAME="teachai_session",
        PERMANENT_SESSION_LIFETIME=timedelta(days=14),
        CSRF_ENABLED=True,
        AI_TIMEOUT=60,
    )

    if test_config:
        app.config.update(test_config)

    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = _load_or_create_secret(instance_path)

    db.init_app(app)
    with app.app_context():
        db.init_db()

    from teachai import api, auth, main

    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp)

    _configure_csrf(app)
    _configure_headers(app)

    @app.errorhandler(400)
    def bad_request(error):
        message = getattr(error, "description", None) or "The request could not be processed."
        if request.path.startswith("/api/"):
            return jsonify(error=message), 400
        return render_template("error.html", code=400, message=message), 400

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify(error="Not found."), 404
        return render_template("error.html", code=404, message="That page was not found."), 404

    @app.errorhandler(500)
    def server_error(_error):
        if request.path.startswith("/api/"):
            return jsonify(error="Something went wrong on the server. Please try again."), 500
        return (
            render_template(
                "error.html",
                code=500,
                message="Something went wrong. Please go back and try again.",
            ),
            500,
        )

    return app


def _load_or_create_secret(instance_path: Path) -> str:
    secret_file = instance_path / "secret_key"
    if secret_file.exists():
        return secret_file.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    secret_file.write_text(key, encoding="utf-8")
    return key


def _configure_csrf(app: Flask) -> None:
    def csrf_token() -> str:
        token = session.get("_csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["_csrf_token"] = token
        return token

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_from_csrf():
        if not app.config.get("CSRF_ENABLED", True):
            return None
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return None
        if request.endpoint == "static":
            return None
        expected = session.get("_csrf_token")
        supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
        if not expected or not supplied or not hmac.compare_digest(expected, supplied):
            if request.path.startswith("/api/"):
                return jsonify(error="Your session token expired. Refresh the page."), 400
            return (
                render_template(
                    "error.html",
                    code=400,
                    message="Your session token expired. Go back and refresh the page.",
                ),
                400,
            )
        return None


def _configure_headers(app: Flask) -> None:
    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "media-src 'self' blob:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'",
        )
        if request.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response
