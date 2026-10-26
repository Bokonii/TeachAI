import pytest

from teachai import ai, create_app, db


@pytest.fixture
def authenticated_chat_client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "CSRF_ENABLED": False,
            "DATABASE": str(tmp_path / "test.sqlite3"),
            "SECRET_KEY": "test-secret",
        }
    )
    with app.app_context():
        user_id = db.execute(
            """
            INSERT INTO users (name, email, password_hash)
            VALUES ('Test Student', 'student@example.test', 'unused')
            """
        )
        conversation_id = db.execute(
            "INSERT INTO conversations (user_id, title) VALUES (?, 'Test chat')",
            (user_id,),
        )
        ai.save_user_ai_settings(
            user_id, "ollama", "http://localhost:11434/v1", "llama3.2", ""
        )

    client = app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = user_id
    return client, conversation_id


def test_ollama_timeout_is_reported_without_demo_fallback(
    authenticated_chat_client, monkeypatch
):
    client, conversation_id = authenticated_chat_client

    def timeout(*_args, **_kwargs):
        raise ai.AIError("The AI provider did not respond within 60 seconds.")

    monkeypatch.setattr(ai, "chat_completion", timeout)
    response = client.post(
        f"/api/conversations/{conversation_id}/chat",
        json={"message": "Explain photosynthesis."},
    )

    assert response.status_code == 200
    result = response.get_json()
    assert result["source"] == "error"
    assert "configured Ollama model" in result["assistant_message"]["content"]
    assert "did not respond within 60 seconds" in result["warning"]
    assert "Demo mode" not in result["assistant_message"]["content"]


def test_polite_reminder_request_creates_reminder_without_calling_ai(
    authenticated_chat_client, monkeypatch
):
    client, conversation_id = authenticated_chat_client

    def unexpected_ai_call(*_args, **_kwargs):
        raise AssertionError("Reminder commands should be handled before calling AI")

    monkeypatch.setattr(ai, "chat_completion", unexpected_ai_call)
    response = client.post(
        f"/api/conversations/{conversation_id}/chat",
        json={"message": "Can you set me a reminder to study tomorrow at 6 PM?"},
    )

    assert response.status_code == 200
    result = response.get_json()
    assert result["source"] == "system"
    assert result["reminder"]["title"] == "study"
    assert result["reminder"]["due_at"].endswith("T18:00")


def test_ai_timeout_has_specific_error(monkeypatch):
    settings = ai.AISettings(
        provider="ollama",
        base_url="http://localhost:11434/v1",
        model="llama3.2",
    )

    def timeout(*_args, **_kwargs):
        raise TimeoutError

    monkeypatch.setattr(ai.urllib.request, "urlopen", timeout)

    with pytest.raises(ai.AIError, match="did not respond within 60 seconds"):
        ai.chat_completion(settings, [{"role": "user", "content": "Hello"}], "System")
