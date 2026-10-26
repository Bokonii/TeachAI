"""Page routes for the TeachAI workspace and settings."""
from __future__ import annotations

from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from teachai import ai, db
from teachai.auth import login_required

bp = Blueprint("main", __name__)


@bp.get("/")
@login_required
def workspace():
    settings = ai.get_user_ai_settings(g.user["id"])
    return render_template(
        "workspace.html",
        ai_configured=settings.configured,
        ai_model=settings.model,
    )


@bp.route("/settings", methods=("GET", "POST"))
@login_required
def settings():
    user_id = g.user["id"]
    current = ai.get_user_ai_settings(user_id)

    if request.method == "POST":
        provider = (request.form.get("provider") or "custom").strip().lower()
        if provider not in ai.PROVIDERS:
            provider = "custom"
        base_url = (request.form.get("base_url") or "").strip().rstrip("/")
        model = (request.form.get("model") or "").strip()
        api_key = (request.form.get("api_key") or "").strip()
        remove_key = request.form.get("remove_key") == "1"

        error = None
        if base_url and not (base_url.startswith("https://") or base_url.startswith("http://")):
            error = "The base URL must begin with http:// or https://."
        elif len(base_url) > 500:
            error = "That base URL is too long."
        elif len(model) > 200:
            error = "That model name is too long."
        elif provider != "ollama" and not (api_key or current.api_key) and base_url and model:
            # Allow saving the endpoint without a key, but make the result clear.
            pass

        if error:
            flash(error, "error")
        else:
            if remove_key:
                api_key = ""
            elif not api_key:
                api_key = current.api_key
            ai.save_user_ai_settings(user_id, provider, base_url, model, api_key)
            if provider == "ollama":
                flash("AI settings saved. Make sure Ollama is running locally.", "success")
            elif api_key and base_url and model:
                flash("AI settings saved. Your assistant is ready to use.", "success")
            else:
                flash(
                    "Settings saved. Add an API key to connect the cloud assistant, "
                    "or use TeachAI's built-in demo mode.",
                    "success",
                )
            return redirect(url_for("main.settings"))

    settings = ai.get_user_ai_settings(user_id)
    conversation_count = db.query(
        "SELECT COUNT(*) AS total FROM conversations WHERE user_id = ?",
        (user_id,),
        one=True,
    )["total"]
    reminder_count = db.query(
        "SELECT COUNT(*) AS total FROM reminders WHERE user_id = ?",
        (user_id,),
        one=True,
    )["total"]
    return render_template(
        "settings.html",
        settings=settings,
        providers=ai.PROVIDERS,
        conversation_count=conversation_count,
        reminder_count=reminder_count,
    )


@bp.get("/health")
def health():
    return {"status": "ok", "app": "TeachAI"}
