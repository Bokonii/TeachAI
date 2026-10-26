"""Offline demo tutor used when no cloud AI key is configured.

This is deliberately a teaching scaffold rather than a pretend language model:
it still handles greetings, study-plan requests, common Python errors, and
schedule-aware coaching, but cloud AI should be connected for open-ended work.
"""
from __future__ import annotations

import re
from datetime import datetime

ERROR_HELP = {
    "SyntaxError": (
        "Python could not parse the code.",
        "Look at the line just before the reported line, check for a missing colon, "
        "unclosed bracket, or a stray quote.",
    ),
    "IndentationError": (
        "The indentation does not form a valid Python block.",
        "Select the affected lines and use your editor's consistent indentation. "
        "Do not mix tabs and spaces.",
    ),
    "NameError": (
        "Python is using a name that has not been defined yet.",
        "Check the spelling, define the variable before using it, and confirm the "
        "scope (a local variable inside a function is not visible outside it).",
    ),
    "TypeError": (
        "A value has the wrong type for that operation.",
        "Print the values and their types just before the failing line. For example, "
        "you may be adding a string to an integer or calling a function with the wrong number of arguments.",
    ),
    "ValueError": (
        "The type is right, but the value is not acceptable.",
        "Check the value passed to int(), float(), or another function. Handle bad "
        "input with try/except or validate it first.",
    ),
    "IndexError": (
        "The code asked for a list position that does not exist.",
        "Remember that list indexes start at 0. Print len(my_list) and check the index "
        "before accessing it.",
    ),
    "KeyError": (
        "A dictionary key was not found.",
        "Print the dictionary keys or use dictionary.get(key, default) when a key "
        "might be missing.",
    ),
    "ZeroDivisionError": (
        "A number was divided by zero.",
        "Check the denominator before dividing and show a helpful message when it is zero.",
    ),
    "ModuleNotFoundError": (
        "Python cannot find an installed module.",
        "Check the spelling, then install it in the same environment VS Code uses, "
        "for example: pip install package-name.",
    ),
    "AttributeError": (
        "An object does not have the attribute or method being called.",
        "Print type(object) to confirm what you are working with, then check the "
        "method name and whether the value is None.",
    ),
}


def local_reply(text: str, user_name: str, reminders: list, now: datetime | None = None) -> str:
    now = now or datetime.now()
    lower = text.lower().strip()

    if re.match(r"^(hi|hello|hey|good (morning|afternoon|evening))\b", lower):
        return (
            f"Hi {user_name.split()[0]}! 👋 I'm in **demo mode** right now, so I can help "
            "with study structure, reminders, and common code errors.\n\n"
            "For full step-by-step explanations of any topic, connect a free/paid AI key "
            "in **Settings**. In the meantime, try:\n\n"
            "- *Remind me to review Chapter 3 tomorrow at 6 PM*\n"
            "- *Give me a 3-day study plan for my math exam*\n"
            "- *Explain my TypeError: can only concatenate str*\n\n"
            "What are you studying today?"
        )

    error_name = next((name for name in ERROR_HELP if name in text), None)
    if error_name or "traceback" in lower or "debug" in lower:
        if error_name:
            meaning, fix = ERROR_HELP[error_name]
            return (
                f"### Debugging `{error_name}`\n\n"
                f"**What it means:** {meaning}\n\n"
                f"**How to fix it:** {fix}\n\n"
                "**Try this debugging loop:**\n\n"
                "1. Read the last line of the traceback first — that names the error.\n"
                "2. Find the line number in **your** file (not the library code).\n"
                "3. Print the values used on that line.\n"
                "4. Change one thing, run again, and compare the result.\n\n"
                "Paste the full traceback and the smallest version of your code here, "
                "and I can walk through it with you."
            )
        return (
            "### Let's debug it systematically\n\n"
            "1. **Read the traceback from the bottom up.** The last line names the exception; "
            "the line above it points to your code.\n"
            "2. **Check inputs.** Print the variables involved right before the failing line.\n"
            "3. **Reduce the problem.** Comment out unrelated code until the smallest failing "
            "example remains.\n"
            "4. **Check assumptions.** Are the types, indexes, and dictionary keys what you expect?\n\n"
            "Paste the traceback and the relevant code. If you connect a cloud AI key in "
            "**Settings**, I can analyze the full context and suggest a corrected version."
        )

    if "study plan" in lower or "study schedule" in lower:
        return _study_plan(reminders, now)

    if "quiz" in lower or "practice question" in lower or "flashcard" in lower:
        return (
            "### A quick practice loop\n\n"
            "1. Close your notes and write everything you remember for 3 minutes.\n"
            "2. Compare with your notes using a different color.\n"
            "3. Turn each gap into a question, not a highlight.\n"
            "4. Re-test those questions after 10 minutes, then tomorrow.\n\n"
            "Connect a cloud AI key in **Settings** to generate practice questions for a "
            "specific topic in your own words."
        )

    if "summar" in lower:
        return (
            "### Summarize without losing the meaning\n\n"
            "Paste the source text or your notes. A useful summary should:\n\n"
            "1. State the main idea in one sentence.\n"
            "2. Keep only the evidence or steps needed to support it.\n"
            "3. Use your own words — copying is not summarizing.\n"
            "4. End with one question you still need to answer.\n\n"
            "For an automatic summary of long material, connect a cloud AI key in **Settings**."
        )

    topic_match = re.search(
        r"(?:explain|what is|what are|how does|how do|help me understand)\s+(.+)",
        text,
        re.IGNORECASE,
    )
    if topic_match:
        topic = topic_match.group(1).strip(" ?.!")
        return (
            f"### A study framework for **{topic}**\n\n"
            "I'm currently in **demo mode**, so I can't reliably generate a full explanation "
            "of this topic yet. Use this framework while you gather the facts:\n\n"
            f"1. **Define it:** Write what *{topic}* means in one sentence, without notes.\n"
            "2. **Break it down:** List the 2–3 parts, stages, or rules involved.\n"
            "3. **Make an example:** Create a concrete example from your own life or course.\n"
            "4. **Find the edge case:** What is one situation where the idea does *not* apply?\n"
            "5. **Teach it back:** Explain it aloud in 60 seconds, then check your notes.\n\n"
            "To get a real step-by-step explanation, add an AI provider key in **Settings**. "
            "Gemini, OpenAI, Groq, OpenRouter, and local Ollama are supported."
        )

    return (
        "I'm running in **demo mode**, so my open-ended tutoring is limited. "
        "I can still help you:\n\n"
        "- Create and list reminders by typing, for example: *Remind me to review Chapter 3 tomorrow at 6 PM*\n"
        "- Organize conversations into subject groups\n"
        "- Build a study plan\n"
        "- Walk through common Python errors\n\n"
        "For full explanations, code debugging with context, and practice questions, "
        "connect a cloud AI key in **Settings**."
    )


def _study_plan(reminders: list, now: datetime) -> str:
    pending = [item for item in reminders if not item["completed"]][:4]
    lines = [
        "### A practical 3-day study plan",
        "",
        "**Day 1 — Map the material**",
        "- List the chapters/topics and mark each as *confident*, *shaky*, or *unknown*.",
        "- Study only the shaky/unknown topics for 25 minutes, then take a 5-minute break.",
        "",
        "**Day 2 — Retrieve and practice**",
        "- Close your notes and write what you remember.",
        "- Do practice problems, then review only the mistakes.",
        "",
        "**Day 3 — Simulate the exam**",
        "- Take a timed practice test with no notes.",
        "- Re-teach the two weakest ideas aloud.",
        "",
        "**Today's focus:** start with 25 minutes on your hardest topic. One focused block "
        "beats three hours of passive rereading.",
    ]
    if pending:
        lines.extend(["", "**Your existing deadlines:**"])
        for reminder in pending:
            try:
                due = datetime.fromisoformat(reminder["due_at"])
                due_label = due.strftime("%a, %b %d at %I:%M %p").replace(" 0", " ")
            except ValueError:
                due_label = reminder["due_at"]
            lines.append(f"- {reminder['title']} — {due_label}")
    return "\n".join(lines)
