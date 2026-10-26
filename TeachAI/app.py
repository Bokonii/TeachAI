"""TeachAI entrypoint for VS Code and `flask run`."""
from __future__ import annotations

import os

from teachai import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=True)
