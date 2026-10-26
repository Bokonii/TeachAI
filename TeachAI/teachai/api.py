"""JSON API for the TeachAI workspace."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request

from teachai import ai, assistant, db, local_tutor

bp = Blueprint("api", __name__, url_prefix="/api")

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def payload() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def fail(message: str, status: int = 400):
    return jsonify(error=message), status


def get_owned_conversation(conversation_id: int, user_id: int):
    return db.query(
        """
        SELECT c.*, sg.name AS group_name, sg.color AS group_color
        FROM conversations c
        LEFT JOIN study_groups sg ON sg.id = c.group_id
        WHERE c.id = ? AND c.user_id = ?
        """,
        (conversation_id, user_id),
        one=True,
    )


def conversation_json(row) -> dict:
    return {
        "id": row["id"],
        "group_id": row["group_id"],
        "group_name": row["group_name"] if "group_name" in row.keys() else None,
        "group_color": row["group_color"] if "group_color" in row.keys() else None,
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "preview": row["preview"] if "preview" in row.keys() else "",
    }


def message_json(row) -> dict:
    return {
        "id": row["id"],
        "role": row["role"],
        "content": row["content"],
        "created_at": row["created_at"],
    }


def reminder_json(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "notes": row["notes"],
        "due_at": row["due_at"],
        "completed": bool(row["completed"]),
        "created_at": row["created_at"],
        "completed_at": row["completed_at"],
    }


def make_title(text: str) -> str:
    cleaned = re.sub(r"[#*_`>]+", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return "New conversation"
    words = cleaned.split()
    title = " ".join(words[:8])
    if len(words) > 8:
        title += "…"
    return title[:70]


def all_reminders(user_id: int) -> list:
    return db.query(
        """
        SELECT * FROM reminders
        WHERE user_id = ?
        ORDER BY completed ASC, due_at ASC, id ASC
        """,
        (user_id,),
    )


def pending_reminders(user_id: int) -> list:
    return db.query(
        """
        SELECT * FROM reminders
        WHERE user_id = ? AND completed = 0
        ORDER BY due_at ASC, id ASC
        """,
        (user_id,),
    )


@bp.before_request
def require_login():
    if g.user is None:
        return jsonify(error="Please log in to continue."), 401
    return None


@bp.get("/bootstrap")
def bootstrap():
    user_id = g.user["id"]
    groups = db.query(
        "SELECT * FROM study_groups WHERE user_id = ? ORDER BY position ASC, id ASC",
        (user_id,),
    )
    conversations = db.query(
        """
        SELECT c.*,
               (SELECT content FROM messages m
                WHERE m.conversation_id = c.id
                ORDER BY m.id DESC LIMIT 1) AS preview
        FROM conversations c
        WHERE c.user_id = ?
        ORDER BY c.updated_at DESC, c.id DESC
        """,
        (user_id,),
    )
    reminders = all_reminders(user_id)
    settings = ai.get_user_ai_settings(user_id)

    return jsonify(
        user={
            "id": g.user["id"],
            "name": g.user["name"],
            "email": g.user["email"],
            "created_at": g.user["created_at"],
        },
        groups=[
            {"id": row["id"], "name": row["name"], "color": row["color"]} for row in groups
        ],
        conversations=[
            {
                "id": row["id"],
                "group_id": row["group_id"],
                "title": row["title"],
                "preview": (row["preview"] or "")[:120],
                "updated_at": row["updated_at"],
                "created_at": row["created_at"],
            }
            for row in conversations
        ],
        reminders=[reminder_json(row) for row in reminders],
        ai={
            "configured": settings.configured,
            "provider": settings.provider,
            "model": settings.model,
        },
    )


# ---------------------------------------------------------------------------
# Study groups
# ---------------------------------------------------------------------------


@bp.post("/groups")
def create_group():
    data = payload()
    name = (data.get("name") or "").strip()
    color = (data.get("color") or "#5B5BD6").strip()
    if not 1 <= len(name) <= 40:
        return fail("Group names must be between 1 and 40 characters.")
    if not HEX_COLOR.match(color):
        color = "#5B5BD6"

    count = db.query(
        "SELECT COUNT(*) AS total FROM study_groups WHERE user_id = ?",
        (g.user["id"],),
        one=True,
    )["total"]
    if count >= 20:
        return fail("You can have up to 20 study groups.", 409)

    try:
        group_id = db.execute(
            """
            INSERT INTO study_groups (user_id, name, color, position)
            VALUES (?, ?, ?, ?)
            """,
            (g.user["id"], name, color, count),
        )
    except sqlite3.IntegrityError:
        return fail("A group with that name already exists.", 409)

    row = db.query("SELECT * FROM study_groups WHERE id = ?", (group_id,), one=True)
    return jsonify(
        group={"id": row["id"], "name": row["name"], "color": row["color"]}
    ), 201


@bp.patch("/groups/<int:group_id>")
def update_group(group_id: int):
    group = db.query(
        "SELECT * FROM study_groups WHERE id = ? AND user_id = ?",
        (group_id, g.user["id"]),
        one=True,
    )
    if group is None:
        return fail("Study group not found.", 404)

    data = payload()
    name = (data.get("name", group["name"]) or "").strip()
    color = (data.get("color", group["color"]) or group["color"]).strip()
    if not 1 <= len(name) <= 40:
        return fail("Group names must be between 1 and 40 characters.")
    if not HEX_COLOR.match(color):
        color = group["color"]

    try:
        db.execute(
            "UPDATE study_groups SET name = ?, color = ? WHERE id = ?",
            (name, color, group_id),
        )
    except sqlite3.IntegrityError:
        return fail("A group with that name already exists.", 409)

    return jsonify(group={"id": group_id, "name": name, "color": color})


@bp.delete("/groups/<int:group_id>")
def delete_group(group_id: int):
    group = db.query(
        "SELECT id FROM study_groups WHERE id = ? AND user_id = ?",
        (group_id, g.user["id"]),
        one=True,
    )
    if group is None:
        return fail("Study group not found.", 404)
    db.execute("DELETE FROM study_groups WHERE id = ?", (group_id,))
    return jsonify(ok=True)


# ---------------------------------------------------------------------------
# Conversations and messages
# ---------------------------------------------------------------------------


@bp.post("/conversations")
def create_conversation():
    data = payload()
    group_id = data.get("group_id")
    if group_id is not None:
        group = db.query(
            "SELECT id FROM study_groups WHERE id = ? AND user_id = ?",
            (group_id, g.user["id"]),
            one=True,
        )
        if group is None:
            return fail("Study group not found.", 404)

    title = (data.get("title") or "New conversation").strip()[:70]
    conversation_id = db.execute(
        """
        INSERT INTO conversations (user_id, group_id, title)
        VALUES (?, ?, ?)
        """,
        (g.user["id"], group_id, title),
    )
    row = get_owned_conversation(conversation_id, g.user["id"])
    return jsonify(conversation=conversation_json(row), messages=[]), 201


@bp.get("/conversations/<int:conversation_id>")
def get_conversation(conversation_id: int):
    conversation = get_owned_conversation(conversation_id, g.user["id"])
    if conversation is None:
        return fail("Conversation not found.", 404)
    messages = db.query(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,),
    )
    return jsonify(
        conversation=conversation_json(conversation),
        messages=[message_json(row) for row in messages],
    )


@bp.patch("/conversations/<int:conversation_id>")
def update_conversation(conversation_id: int):
    conversation = get_owned_conversation(conversation_id, g.user["id"])
    if conversation is None:
        return fail("Conversation not found.", 404)

    data = payload()
    title = (data.get("title", conversation["title"]) or "").strip()[:70]
    if not title:
        title = conversation["title"]

    group_id = conversation["group_id"]
    if "group_id" in data:
        group_id = data["group_id"]
        if group_id is not None:
            group = db.query(
                "SELECT id FROM study_groups WHERE id = ? AND user_id = ?",
                (group_id, g.user["id"]),
                one=True,
            )
            if group is None:
                return fail("Study group not found.", 404)

    db.execute(
        "UPDATE conversations SET title = ?, group_id = ?, updated_at = ? WHERE id = ?",
        (title, group_id, utc_now(), conversation_id),
    )
    row = get_owned_conversation(conversation_id, g.user["id"])
    return jsonify(conversation=conversation_json(row))


@bp.delete("/conversations/<int:conversation_id>")
def delete_conversation(conversation_id: int):
    conversation = get_owned_conversation(conversation_id, g.user["id"])
    if conversation is None:
        return fail("Conversation not found.", 404)
    db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    return jsonify(ok=True)


@bp.post("/conversations/<int:conversation_id>/chat")
def chat(conversation_id: int):
    conversation = get_owned_conversation(conversation_id, g.user["id"])
    if conversation is None:
        return fail("Conversation not found.", 404)

    data = payload()
    text = (data.get("message") or "").strip()
    if not text:
        return fail("Write a message first.")
    if len(text) > 6000:
        return fail("That message is too long. Keep it under 6,000 characters.")

    now = datetime.now()
    db.execute(
        """
        INSERT INTO messages (conversation_id, role, content)
        VALUES (?, 'user', ?)
        """,
        (conversation_id, text),
    )

    prior_user_messages = db.query(
        """
        SELECT COUNT(*) AS total FROM messages
        WHERE conversation_id = ? AND role = 'user'
        """,
        (conversation_id,),
        one=True,
    )["total"]
    if prior_user_messages <= 1:
        db.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (make_title(text), utc_now(), conversation_id),
        )
    else:
        db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (utc_now(), conversation_id),
        )

    intent = assistant.analyze_message(text, now)
    reminder = None
    warning = None
    source = "system"

    if intent and intent.action == "list":
        pending = pending_reminders(g.user["id"])
        reply = assistant.format_reminder_list(pending, now)
    elif intent and intent.action == "create":
        if intent.due is None:
            reply = assistant.reminder_needs_time_reply(intent.title)
        elif intent.due < now.replace(second=0, microsecond=0):
            reply = (
                "That date and time is already in the past. Tell me a future time, "
                "for example: *Remind me to review tomorrow at 6 PM*."
            )
        else:
            due_text = intent.due.strftime("%Y-%m-%dT%H:%M")
            reminder_id = db.execute(
                """
                INSERT INTO reminders (user_id, title, notes, due_at)
                VALUES (?, ?, '', ?)
                """,
                (g.user["id"], intent.title[:200], due_text),
            )
            reminder = reminder_json(
                db.query("SELECT * FROM reminders WHERE id = ?", (reminder_id,), one=True)
            )
            reply = assistant.reminder_created_reply(intent.title, intent.due, now)
    else:
        settings = ai.get_user_ai_settings(g.user["id"])
        history_rows = db.query(
            """
            SELECT role, content FROM messages
            WHERE conversation_id = ?
            ORDER BY id DESC LIMIT 18
            """,
            (conversation_id,),
        )
        history = [
            {"role": row["role"], "content": row["content"][:12000]}
            for row in reversed(history_rows)
        ]
        if settings.configured:
            system_prompt = ai.build_system_prompt(
                g.user["name"], pending_reminders(g.user["id"]), now
            )
            try:
                reply = ai.chat_completion(settings, history, system_prompt)
                source = "cloud"
            except ai.AIError as error:
                warning = str(error)
                if settings.provider == "ollama":
                    reply = (
                        "I couldn't get a response from your configured Ollama model.\n\n"
                        f"**Details:** {warning}\n\n"
                        "Check that Ollama is running and that the model name in Settings "
                        "matches an installed model. You can verify it with "
                        "`ollama list`, then try **Test connection** in Settings."
                    )
                else:
                    reply = (
                        "I couldn't get a response from your configured AI provider.\n\n"
                        f"**Details:** {warning}\n\n"
                        "Check the provider's status, base URL, model, and API key in Settings, "
                        "then try **Test connection**."
                    )
                source = "error"
        else:
            reply = local_tutor.local_reply(
                text, g.user["name"], all_reminders(g.user["id"]), now
            )
            source = "local"

    assistant_id = db.execute(
        """
        INSERT INTO messages (conversation_id, role, content)
        VALUES (?, 'assistant', ?)
        """,
        (conversation_id, reply),
    )
    db.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (utc_now(), conversation_id),
    )

    user_message = db.query(
        """
        SELECT * FROM messages
        WHERE conversation_id = ? AND role = 'user'
        ORDER BY id DESC LIMIT 1
        """,
        (conversation_id,),
        one=True,
    )
    assistant_message = db.query(
        "SELECT * FROM messages WHERE id = ?", (assistant_id,), one=True
    )
    updated = get_owned_conversation(conversation_id, g.user["id"])

    return jsonify(
        conversation=conversation_json(updated),
        user_message=message_json(user_message),
        assistant_message=message_json(assistant_message),
        reminder=reminder,
        reminders=[reminder_json(row) for row in all_reminders(g.user["id"])],
        source=source,
        warning=warning,
    )


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------


@bp.get("/reminders")
def list_reminders():
    return jsonify(
        reminders=[reminder_json(row) for row in all_reminders(g.user["id"])]
    )


@bp.post("/reminders")
def create_reminder():
    data = payload()
    title = (data.get("title") or "").strip()
    notes = (data.get("notes") or "").strip()
    due_at_raw = (data.get("due_at") or "").strip()

    if not 1 <= len(title) <= 200:
        return fail("A reminder needs a title (up to 200 characters).")
    if len(notes) > 2000:
        return fail("Notes are too long (maximum 2,000 characters).")
    try:
        due_at = _normalize_due(due_at_raw)
    except ValueError:
        return fail("Choose a valid reminder date and time.")

    reminder_id = db.execute(
        """
        INSERT INTO reminders (user_id, title, notes, due_at)
        VALUES (?, ?, ?, ?)
        """,
        (g.user["id"], title, notes, due_at),
    )
    row = db.query("SELECT * FROM reminders WHERE id = ?", (reminder_id,), one=True)
    return jsonify(reminder=reminder_json(row)), 201


@bp.patch("/reminders/<int:reminder_id>")
def update_reminder(reminder_id: int):
    reminder = db.query(
        "SELECT * FROM reminders WHERE id = ? AND user_id = ?",
        (reminder_id, g.user["id"]),
        one=True,
    )
    if reminder is None:
        return fail("Reminder not found.", 404)

    data = payload()
    title = (data.get("title", reminder["title"]) or "").strip()
    notes = (data.get("notes", reminder["notes"]) or "").strip()
    if not 1 <= len(title) <= 200:
        return fail("A reminder needs a title (up to 200 characters).")
    if len(notes) > 2000:
        return fail("Notes are too long (maximum 2,000 characters).")

    due_at = reminder["due_at"]
    if "due_at" in data:
        try:
            due_at = _normalize_due(str(data.get("due_at") or ""))
        except ValueError:
            return fail("Choose a valid reminder date and time.")

    completed = reminder["completed"]
    completed_at = reminder["completed_at"]
    if "completed" in data:
        completed = 1 if data.get("completed") else 0
        completed_at = utc_now() if completed else None

    db.execute(
        """
        UPDATE reminders
        SET title = ?, notes = ?, due_at = ?, completed = ?, completed_at = ?
        WHERE id = ?
        """,
        (title, notes, due_at, completed, completed_at, reminder_id),
    )
    row = db.query("SELECT * FROM reminders WHERE id = ?", (reminder_id,), one=True)
    return jsonify(reminder=reminder_json(row))


@bp.delete("/reminders/<int:reminder_id>")
def delete_reminder(reminder_id: int):
    reminder = db.query(
        "SELECT id FROM reminders WHERE id = ? AND user_id = ?",
        (reminder_id, g.user["id"]),
        one=True,
    )
    if reminder is None:
        return fail("Reminder not found.", 404)
    db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    return jsonify(ok=True)


def _normalize_due(raw: str) -> str:
    if not raw:
        raise ValueError("missing due date")
    try:
        value = datetime.fromisoformat(raw.replace("Z", ""))
    except ValueError as error:
        raise ValueError("invalid due date") from error
    if not 2000 <= value.year <= 2100:
        raise ValueError("date out of range")
    return value.strftime("%Y-%m-%dT%H:%M")


# ---------------------------------------------------------------------------
# AI connection test
# ---------------------------------------------------------------------------


@bp.post("/settings/ai/test")
def test_ai():
    settings = ai.get_user_ai_settings(g.user["id"])
    if not settings.configured:
        return fail("Save your AI provider, base URL, model, and key first.", 400)
    try:
        reply = ai.test_connection(settings)
    except ai.AIError as error:
        return fail(str(error), 502)
    return jsonify(ok=True, reply=reply[:300])
