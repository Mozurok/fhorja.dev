"""Synthetic Flask app -- Fhorja E2E walkthrough fixture entrypoint.

This file is the app-wiring stub. The actual /signup handler with the
intentional issues lives in handlers/signup.py so the bug-class globs in
`wos/bug-classes/` (which target `handlers/**`, `api/**`, etc.) match.

Run locally for optional manual verification:
    pip install -r requirements.txt
    python app.py
    curl -X POST http://localhost:5001/signup \\
      -H 'Content-Type: application/json' \\
      -d '{"email": "", "password": "x"}'
    # Returns 201 today (intentional bug; Slice 1 fixes this).
"""

from flask import Flask

from handlers.signup import signup_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(signup_bp)

    @app.route("/health", methods=["GET"])
    def health():
        return {"status": "ok"}, 200

    return app


if __name__ == "__main__":
    # Port 5001 to avoid macOS Monterey+ AirPlay Receiver on :5000.
    create_app().run(debug=True, port=5001)
