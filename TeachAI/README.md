# TeachAI

An interactive, 24/7 AI study partner built with Flask, SQLite, and vanilla JavaScript. TeachAI helps students understand complex concepts through step by step explanations, organize conversations into study groups, manage a calendar of reminders, use voice input, and connect to any OpenAI-compatible AI provider.

## Features

- **Account login system** — register/login with hashed passwords; data stays per user.
- **Recent chat history** — resume past conversations from the sidebar.
- **Group tab system** — organize conversations into subjects/projects (General, Math, CS, etc.).
- **Voice interaction** — ask questions with speech (browser speech recognition).
- **Smart virtual assistant** — natural language study help; falls back to a built-in tutor when no AI key is set.
- **Reminder and schedule calendar** — add/edit/complete/delete reminders with a month view and due alerts.
- **Chat + reminder integration** — create reminders by typing/voice (e.g., "Remind me to review Chapter 3 tomorrow at 6 PM"); ask for upcoming reminders.

## Quick start (VS Code)

1. **Open the project**
   - Open the `TeachAI` folder in Visual Studio Code.

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate and install dependencies**
   - Windows (PowerShell)
   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   - macOS/Linux
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   flask --app app:init_db
   ```

   Or optionally add a demo account:
   ```bash
   flask --app app:seed_demo
   ```
   Login with `demo@teachai.local` / `teachai123`.

5. **Run the app**
   ```bash
   python app.py
   ```
   Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Connecting an AI provider (optional)

1. Go to **Settings** in the app.
2. Choose a provider (Google Gemini, OpenAI, Groq, OpenRouter, Ollama, or Custom).
3. Fill in the base URL, model, and API key (Ollama doesn't need a key).
4. Click **Test connection** to verify, then **Save settings**.

## Project structure

```
TeachAI/
├── app.py
├── requirements.txt
├── teachai/
│   ├── __init__.py
│   ├── ai.py
│   ├── api.py
│   ├── assistant.py
│   ├── auth.py
│   ├── db.py
│   ├── local_tutor.py
│   ├── main.py
│   ├── schema.sql
│   ├── seed.py
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/{common.js, workspace.js, settings.js}
│   └── templates/
│       ├── base.html
│       ├── login.html
│       ├── register.html
│       ├── workspace.html
│       ├── settings.html
│       └── error.html
└── instance/
    └── teachai.sqlite3 (created on first run)
```

## Notes

- Voice input uses the Web Speech API (Chrome/Edge recommended).
- All reminders are stored locally with due dates/times.
- If the cloud provider fails, TeachAI falls back to the built-in demo tutor gracefully.
- For a clean run, delete `instance/teachai.sqlite3` and re-run `flask --app app:init_db`.

## Credits

Created as a finals project for **Application Development and Emerging Technologies**.
