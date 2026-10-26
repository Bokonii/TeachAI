"""Optional demo data for a quick classroom presentation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from teachai import db


def seed_demo() -> bool:
    if db.query(
        "SELECT id FROM users WHERE email = ?", ("demo@teachai.local",), one=True
    ):
        return False

    now = datetime.now()
    utc_now = datetime.now(timezone.utc)
    connection = db.get_db()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo Student", "demo@teachai.local", generate_password_hash("teachai123")),
    )
    user_id = cursor.lastrowid

    groups = [
        ("General", "#5B5BD6"),
        ("Mathematics", "#D97706"),
        ("Computer Science", "#0F766E"),
        ("Research", "#BE185D"),
    ]
    group_ids = {}
    for position, (name, color) in enumerate(groups):
        group_cursor = cursor.execute(
            """
            INSERT INTO study_groups (user_id, name, color, position)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, name, color, position),
        )
        group_ids[name] = group_cursor.lastrowid

    conversations = [
        (
            "Computer Science",
            "Debugging my Python loop",
            [
                (
                    "user",
                    "My Python code says `TypeError: can only concatenate str (not \"int\") "
                    "to str` when I do `print(\"Score: \" + score)`. What is wrong?",
                ),
                (
                    "assistant",
                    "### The core idea\n\nPython will not automatically turn `score` into text. "
                    "The `+` operator joins two strings, but `score` is probably an integer.\n\n"
                    "### Fix\n\n```python\nscore = 95\nprint(\"Score: \" + str(score))   # convert first\n"
                    "# or use an f-string (recommended):\nprint(f\"Score: {score}\")\n```\n\n"
                    "### Quick check\n\nWhat would `print(\"Total: \" + 10)` do, and how would you fix it?",
                ),
            ],
        ),
        (
            "Mathematics",
            "Understanding derivatives",
            [
                (
                    "user",
                    "Can you explain derivatives like I'm a beginner?",
                ),
                (
                    "assistant",
                    "### The core idea\n\nA derivative measures **how fast something changes** at one "
                    "exact moment. If a car's position is `s(t)`, its derivative `s'(t)` is the speed at "
                    "time `t`.\n\n### A small example\n\nFor `f(x) = x²`, use the power rule: bring the "
                    "exponent down, then subtract one.\n\n```text\nf(x)  = x²\nf'(x) = 2x\n```\n\n"
                    "At `x = 3`, the slope is `2(3) = 6`.\n\n### Your turn\n\nWhat is the derivative of "
                    "`f(x) = x³` at `x = 2`?",
                ),
            ],
        ),
        (
            "Research",
            "Outline for my capstone paper",
            [
                (
                    "user",
                    "Help me outline Chapter 2 of my research paper about AI study assistants.",
                ),
                (
                    "assistant",
                    "### Chapter 2: Review of Related Literature\n\n"
                    "1. **AI in education** — history, current uses, and adoption trends.\n"
                    "2. **Intelligent tutoring systems** — how adaptive feedback supports learning.\n"
                    "3. **Student productivity tools** — reminders, calendars, and study planning.\n"
                    "4. **Usability and trust** — why students accept or reject AI assistants.\n"
                    "5. **Synthesis** — the gap your TeachAI project addresses.\n\n"
                    "**Writing tip:** organize each section by theme, not by author. End every paragraph "
                    "with how the idea connects to your study.",
                ),
            ],
        ),
        (
            "General",
            "Welcome to TeachAI",
            [
                (
                    "assistant",
                    "Welcome to TeachAI! 👋 I'm your study partner. Ask me to explain a concept, debug "
                    "code, build a study plan, or manage your reminders.\n\nTry: *Remind me to review "
                    "Chapter 3 tomorrow at 6 PM.*",
                ),
            ],
        ),
    ]

    for offset, (group_name, title, messages) in enumerate(conversations):
        stamp = utc_now - timedelta(hours=offset + 1)
        conversation_cursor = cursor.execute(
            """
            INSERT INTO conversations (user_id, group_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                group_ids[group_name],
                title,
                stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        conversation_id = conversation_cursor.lastrowid
        for role, content in messages:
            cursor.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content),
            )

    reminders = [
        ("Review calculus notes", "Derivatives and limits, Chapter 3", now + timedelta(hours=3)),
        ("Submit CS project proposal", "Upload the PDF to the class portal", now + timedelta(days=1, hours=2)),
        ("Research chapter 2 draft", "Finish the synthesis section", now + timedelta(days=3, hours=4)),
        ("Team meeting", "Discuss the UI with the group", now - timedelta(hours=2)),
    ]
    for title, notes, due in reminders:
        cursor.execute(
            """
            INSERT INTO reminders (user_id, title, notes, due_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, title, notes, due.strftime("%Y-%m-%dT%H:%M")),
        )

    connection.commit()
    return True
