"""Account registration, login, and access control."""
from __future__ import annotations

import functools
import re
from datetime import datetime, timezone

from flask import (
    Blueprint,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from teachai import db

bp = Blueprint("auth", __name__)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@bp.before_app_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = db.query(
            "SELECT id, name, email, created_at FROM users WHERE id = ?",
            (user_id,),
            one=True,
        )
        if g.user is None:
            session.clear()


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify(error="Please log in to continue."), 401
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view


@bp.route("/register", methods=("GET", "POST"))
def register():
    if g.user is not None:
        return redirect(url_for("main.workspace"))

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        error = None
        if not 2 <= len(name) <= 60:
            error = "Your name should be between 2 and 60 characters."
        elif not EMAIL_PATTERN.match(email) or len(email) > 254:
            error = "Enter a valid email address."
        elif len(password) < 8:
            error = "Use a password with at least 8 characters."
        elif password != confirm:
            error = "The two passwords do not match."
        elif db.query("SELECT id FROM users WHERE email = ?", (email,), one=True):
            error = "An account with that email already exists."

        if error is None:
            connection = db.get_db()
            cursor = connection.cursor()
            try:
                cursor.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password)),
                )
                user_id = cursor.lastrowid
                group_cursor = cursor.execute(
                    "INSERT INTO study_groups (user_id, name, color, position) VALUES (?, ?, ?, ?)",
                    (user_id, "General", "#5B5BD6", 0),
                )
                group_id = group_cursor.lastrowid
                conversation_cursor = cursor.execute(
                    """
                    INSERT INTO conversations (user_id, group_id, title)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, group_id, "Welcome to TeachAI"),
                )
                conversation_id = conversation_cursor.lastrowid
                cursor.execute(
                    "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                    (
                        conversation_id,
                        "assistant",
                        "Welcome to TeachAI! 👋\n\nI'm your study partner. I can help you "
                        "**understand concepts step by step**, **debug code**, **build study "
                        "plans**, and **keep track of deadlines**.\n\nTry asking:\n\n"
                        "- *Explain photosynthesis like I'm a beginner.*\n"
                        "- *Help me debug this Python error: TypeError...*\n"
                        "- *Remind me to review Chapter 3 tomorrow at 6 PM.*\n\n"
                        "You can type below or use the microphone. Let's make this study "
                        "session count!",
                    ),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

            session.clear()
            session["user_id"] = user_id
            flash(f"Welcome to TeachAI, {name.split()[0]}!", "success")
            return redirect(url_for("main.workspace"))

        flash(error, "error")

    return render_template("register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user is not None:
        return redirect(url_for("main.workspace"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = db.query(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?",
            (email,),
            one=True,
        )
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Incorrect email or password. Please try again.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            flash(f"Welcome back, {user['name'].split()[0]}!", "success")
            return redirect(url_for("main.workspace"))

    return render_template("login.html")


@bp.post("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
