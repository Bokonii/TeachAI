"""Tests for the natural-language reminder parser."""
from datetime import datetime

from teachai import assistant


def test_remind_tomorrow_at_time():
    now = datetime(2026, 10, 24, 14, 0)
    intent = assistant.analyze_message("Remind me to review Chapter 3 tomorrow at 6 PM", now)
    assert intent is not None
    assert intent.action == "create"
    assert intent.title == "review Chapter 3"
    assert intent.due == datetime(2026, 10, 25, 18, 0)


def test_add_reminder_format():
    now = datetime(2026, 10, 24, 14, 0)
    intent = assistant.analyze_message("Add a reminder to submit the project on Friday at 9 AM", now)
    assert intent is not None
    assert intent.action == "create"
    assert "submit the project" in intent.title
    assert intent.due is not None


def test_polite_request_to_set_reminder():
    now = datetime(2026, 10, 24, 14, 0)
    intent = assistant.analyze_message(
        "Can you set me a reminder to study tomorrow at 6 PM?", now
    )
    assert intent is not None
    assert intent.action == "create"
    assert intent.title == "study"
    assert intent.due == datetime(2026, 10, 25, 18, 0)


def test_in_minutes():
    now = datetime(2026, 10, 24, 14, 0)
    intent = assistant.analyze_message("Remind me to take a break in 30 minutes", now)
    assert intent is not None
    assert intent.action == "create"
    assert intent.due == datetime(2026, 10, 24, 14, 30)
    assert "break" in intent.title


def test_list_reminders():
    now = datetime(2026, 10, 24, 14, 0)
    intent = assistant.analyze_message("Show me my reminders for this week", now)
    assert intent is not None
    assert intent.action == "list"


def test_needs_time_when_missing():
    now = datetime(2026, 10, 24, 14, 0)
    intent = assistant.analyze_message("Remind me to do my research", now)
    assert intent is not None
    assert intent.action == "create"
    assert intent.due is None


def test_format_due():
    now = datetime(2026, 10, 24, 14, 0)
    assert assistant.format_due(datetime(2026, 10, 24, 18, 0), now) == "Today at 6:00 PM"
    assert assistant.format_due(datetime(2026, 10, 25, 9, 30), now) == "Tomorrow at 9:30 AM"
