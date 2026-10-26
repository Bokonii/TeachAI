"""Natural-language reminder commands and small assistant utilities.

The parser intentionally supports a focused set of phrases that are easy to
demonstrate in a class: "remind me to ...", "add a reminder ...",
"what are my reminders?", and normal calendar dates/times.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

WEEKDAYS = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

CREATE_PATTERNS = [
    re.compile(
        r"^(?:hey\s+)?(?:teach\s*ai[,:\s]+)?(?:please\s+)?"
        r"(?:can|could|would)\s+you\s+(?:please\s+)?remind\s+me"
        r"(?:\s+(?:to|about|that))?\s*(?P<body>.*)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:hey\s+)?(?:teach\s*ai[,:\s]+)?(?:please\s+)?"
        r"(?:can|could|would)\s+you\s+(?:please\s+)?"
        r"(?:add|create|set|make|schedule)\s+"
        r"(?:(?:me|us)\s+)?(?:a|an|the)?\s*(?:new\s+)?reminder"
        r"(?:\s+(?:to|for|about|that))?\s*(?P<body>.*)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:hey\s+)?(?:teach\s*ai[,:\s]+)?(?:please\s+)?remind\s+me"
        r"(?:\s+(?:to|about|that))?\s*(?P<body>.*)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:please\s+)?(?:add|create|set|make|schedule)\s+"
        r"(?:a|an|the)?\s*(?:new\s+)?reminder"
        r"(?:\s+(?:to|for|about|that))?\s*(?P<body>.*)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:please\s+)?(?:add|put)\s+(?P<body>.+?)\s+"
        r"(?:to|on)\s+my\s+(?:reminders?|calendar|schedule)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:please\s+)?schedule\s+(?P<body>.+)$",
        re.IGNORECASE,
    ),
]

LIST_PATTERN = re.compile(
    r"\b(?:show|list|check|view|see|what(?:'s| is| are)?|anything|anything else)\b"
    r".*\b(?:reminders?|schedule|calendar|tasks?|deadlines?|due|upcoming)\b"
    r"|\b(?:my|upcoming)\s+(?:reminders?|schedule|tasks?|deadlines?)\b"
    r"|\bwhat\s+do\s+i\s+have\s+(?:coming\s+up|due|scheduled)\b"
    r"|\bdo\s+i\s+have\s+anything\s+(?:due|scheduled|coming up)\b",
    re.IGNORECASE,
)


@dataclass
class ReminderIntent:
    action: str
    title: str = ""
    due: datetime | None = None


@dataclass
class _FoundDate:
    value: date
    start: int
    end: int
    suggested_time: time | None = None


@dataclass
class _FoundTime:
    value: time
    start: int
    end: int


def is_schedule_query(text: str) -> bool:
    """Return True for obvious "show my reminders" questions."""
    cleaned = text.strip()
    if not cleaned:
        return False
    if any(pattern.match(cleaned) for pattern in CREATE_PATTERNS):
        return False
    return bool(LIST_PATTERN.search(cleaned))


def analyze_message(text: str, now: datetime | None = None) -> ReminderIntent | None:
    """Classify a user message as a reminder command, or return None."""
    now = now or datetime.now()
    cleaned = text.strip()

    if is_schedule_query(cleaned):
        return ReminderIntent(action="list")

    body = None
    for pattern in CREATE_PATTERNS:
        match = pattern.match(cleaned)
        if match:
            body = match.group("body").strip(" ,.;:-")
            break

    if body is None:
        return None

    if not body:
        return ReminderIntent(action="create", title="", due=None)

    due, spans = extract_due(body, now)
    title = _remove_spans(body, spans)
    title = _clean_title(title)
    return ReminderIntent(action="create", title=title, due=due)


def extract_due(text: str, now: datetime) -> tuple[datetime | None, list[tuple[int, int]]]:
    """Extract a local due date/time and spans that should be removed from the title."""
    spans: list[tuple[int, int]] = []
    found_date: _FoundDate | None = None
    found_time: _FoundTime | None = None

    # Phrases like "in 30 minutes" fully describe the due time.
    relative_delta = re.search(
        r"\bin\s+(\d{1,4})\s*(minutes?|mins?|hours?|hrs?|days?|weeks?)\b",
        text,
        re.IGNORECASE,
    )
    if relative_delta:
        amount = int(relative_delta.group(1))
        unit = relative_delta.group(2).lower()
        if unit.startswith("min"):
            delta = timedelta(minutes=amount)
        elif unit.startswith("h"):
            delta = timedelta(hours=amount)
        elif unit.startswith("w"):
            delta = timedelta(weeks=amount)
        else:
            delta = timedelta(days=amount)
        return now + delta, [(relative_delta.start(), relative_delta.end())]

    # ISO date: 2026-10-24
    iso_match = re.search(r"\b(\d{4}-\d{1,2}-\d{1,2})\b", text)
    if iso_match:
        try:
            found_date = _FoundDate(
                datetime.strptime(iso_match.group(1), "%Y-%m-%d").date(),
                iso_match.start(),
                iso_match.end(),
            )
        except ValueError:
            pass

    # Month name and day: October 24, Oct 24th 2026
    if found_date is None:
        match = re.search(
            r"\b(?:on\s+)?(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
            r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
            r"nov(?:ember)?|dec(?:ember)?)\.?\s+"
            r"(?P<day>\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(?P<year>\d{4}))?\b",
            text,
            re.IGNORECASE,
        )
        if match:
            month = MONTHS[match.group("month").lower().rstrip(".")]
            day = int(match.group("day"))
            year = int(match.group("year")) if match.group("year") else now.year
            try:
                parsed = date(year, month, day)
                if not match.group("year") and parsed < now.date():
                    parsed = date(year + 1, month, day)
                found_date = _FoundDate(parsed, match.start(), match.end())
            except ValueError:
                pass

    # Numeric date: 10/24 or 10/24/2026
    if found_date is None:
        match = re.search(r"\b(?:on\s+)?(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", text)
        if match:
            month, day = int(match.group(1)), int(match.group(2))
            year = int(match.group(3)) if match.group(3) else now.year
            if year < 100:
                year += 2000
            try:
                parsed = date(year, month, day)
                if not match.group(3) and parsed < now.date():
                    parsed = date(year + 1, month, day)
                found_date = _FoundDate(parsed, match.start(), match.end())
            except ValueError:
                pass

    # Relative dates.
    if found_date is None:
        match = re.search(r"\b(?:the\s+)?day\s+after\s+tomorrow\b", text, re.IGNORECASE)
        if match:
            found_date = _FoundDate(now.date() + timedelta(days=2), match.start(), match.end())
    if found_date is None:
        match = re.search(r"\btomorrow\b", text, re.IGNORECASE)
        if match:
            found_date = _FoundDate(now.date() + timedelta(days=1), match.start(), match.end())
    if found_date is None:
        match = re.search(r"\btonight\b", text, re.IGNORECASE)
        if match:
            found_date = _FoundDate(
                now.date(), match.start(), match.end(), suggested_time=time(20, 0)
            )
    if found_date is None:
        match = re.search(r"\btoday\b", text, re.IGNORECASE)
        if match:
            found_date = _FoundDate(now.date(), match.start(), match.end())
    if found_date is None:
        match = re.search(r"\bnext\s+week\b", text, re.IGNORECASE)
        if match:
            found_date = _FoundDate(
                now.date() + timedelta(days=7), match.start(), match.end(),
                suggested_time=time(9, 0),
            )

    # Weekdays: "Friday", "next Friday", "on Monday".
    if found_date is None:
        weekday_names = "|".join(WEEKDAYS)
        match = re.search(
            rf"\b(?P<prefix>next|this|on)?\s*(?P<weekday>{weekday_names})\b",
            text,
            re.IGNORECASE,
        )
        if match:
            target = WEEKDAYS[match.group("weekday").lower()]
            days_ahead = (target - now.weekday()) % 7
            if match.group("prefix") and match.group("prefix").lower() == "next":
                days_ahead = days_ahead or 7
            parsed = now.date() + timedelta(days=days_ahead)
            found_date = _FoundDate(parsed, match.start(), match.end())

    # Time: 7 PM, 7:30pm, 19:00, at 7, noon, midnight.
    match = re.search(
        r"\b(?:at|by|around)\s+(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?\b",
        text,
        re.IGNORECASE,
    )
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        marker = (match.group(3) or "").lower().replace(".", "")
        if marker == "pm" and hour < 12:
            hour += 12
        elif marker == "am" and hour == 12:
            hour = 0
        elif not marker and 1 <= hour <= 7:
            # In study contexts, a bare "at 5" almost always means afternoon.
            hour += 12
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            found_time = _FoundTime(time(hour, minute), match.start(), match.end())

    if found_time is None:
        match = re.search(
            r"\b(\d{1,2})(?::(\d{2}))\s*(a\.?m\.?|p\.?m\.?)\b",
            text,
            re.IGNORECASE,
        )
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            marker = match.group(3).lower().replace(".", "")
            if marker == "pm" and hour < 12:
                hour += 12
            elif marker == "am" and hour == 12:
                hour = 0
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                found_time = _FoundTime(time(hour, minute), match.start(), match.end())

    if found_time is None:
        match = re.search(r"\b(noon|midnight)\b", text, re.IGNORECASE)
        if match:
            value = time(12, 0) if match.group(1).lower() == "noon" else time(0, 0)
            found_time = _FoundTime(value, match.start(), match.end())

    if found_time is None:
        match = re.search(r"\b(morning|afternoon|evening)\b", text, re.IGNORECASE)
        if match:
            hour = {"morning": 9, "afternoon": 14, "evening": 19}[match.group(1).lower()]
            found_time = _FoundTime(time(hour, 0), match.start(), match.end())

    if found_date is None and found_time is None:
        return None, []

    if found_date is not None:
        spans.append((found_date.start, found_date.end))
    if found_time is not None:
        spans.append((found_time.start, found_time.end))

    if found_date is not None:
        chosen_time = (
            found_time.value
            if found_time
            else found_date.suggested_time or time(9, 0)
        )
        due = datetime.combine(found_date.value, chosen_time)
    else:
        due = datetime.combine(now.date(), found_time.value)  # type: ignore[union-attr]
        if due <= now:
            due += timedelta(days=1)

    # A weekday mentioned without a specific time and already past today rolls
    # forward one week.
    if found_date is not None and found_time is None and due < now and not (
        re.search(r"\b(?:today|tonight)\b", text, re.IGNORECASE)
    ):
        due += timedelta(days=7)

    return due, spans


def _remove_spans(text: str, spans: list[tuple[int, int]]) -> str:
    if not spans:
        return text
    result = text
    for start, end in sorted(spans, reverse=True):
        result = result[:start] + " " + result[end:]
    return result


def _clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip(" ,.;:!?-")
    title = re.sub(r"^(?:to|that|about|for|on|at|by)\s+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+(?:on|at|by|for|to)$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" ,.;:!?-")
    return title or "Study reminder"


def format_due(value: datetime, now: datetime | None = None) -> str:
    now = now or datetime.now()
    day = value.date()
    if day == now.date():
        date_part = "Today"
    elif day == now.date() + timedelta(days=1):
        date_part = "Tomorrow"
    else:
        date_part = value.strftime("%a, %b %d")
    time_part = value.strftime("%I:%M %p").lstrip("0")
    return f"{date_part} at {time_part}"


def format_reminder_list(reminders: list, now: datetime | None = None) -> str:
    now = now or datetime.now()
    pending = [item for item in reminders if not item["completed"]]
    if not pending:
        return (
            "You have no upcoming reminders yet. Try saying:\n\n"
            "> Remind me to review Chapter 3 tomorrow at 6 PM"
        )

    lines = ["### Your upcoming reminders", ""]
    for reminder in pending[:8]:
        try:
            due = datetime.fromisoformat(reminder["due_at"])
            due_label = format_due(due, now)
            status = " · **overdue**" if due < now else ""
        except ValueError:
            due_label = reminder["due_at"]
            status = ""
        lines.append(f"- **{reminder['title']}** — {due_label}{status}")
    lines.append("")
    lines.append("Open the calendar panel to edit, complete, or add a reminder.")
    return "\n".join(lines)


def reminder_created_reply(title: str, due: datetime, now: datetime | None = None) -> str:
    return (
        f"Your reminder is set! 🎯\n\n"
        f"**{title}**\n\n"
        f"Due **{format_due(due, now)}**. I've added it to your calendar and upcoming list."
    )


def reminder_needs_time_reply(title: str) -> str:
    label = f"**{title}**" if title and title != "Study reminder" else "that reminder"
    return (
        f"I can add {label}, but I need a date or time. Try:\n\n"
        "> Remind me to review Chapter 3 tomorrow at 6 PM\n\n"
        "You can also use the **Add reminder** button in the calendar panel."
    )
