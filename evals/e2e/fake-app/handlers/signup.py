"""Synthetic Flask signup handler -- Fhorja E2E walkthrough fixture.

This module ships with INTENTIONAL issues so the Fhorja walkthrough has real
material for impact-analysis, implement-approved-slice (Slices 1 + 2), and
repo-consistency-sweep (bug-class globs match `handlers/**` so missing-test
+ missing-validation findings fire on this path). Do NOT treat this code as
a real engineering reference -- it exists to be modified.

Known intentional issues at fixture creation (the walkthrough's slices fix
Slice 1 + Slice 2; the sweep catches the missing test for Slice 1):
- /signup accepts empty email strings (Slice 1 target)
- /signup accepts malformed email addresses (Slice 2 target)
- No tests anywhere (the sweep flags this on Slice 1 inline-close)
- No structured error body (D-1 will lock the shape: {error, code})
"""

from flask import Blueprint, jsonify, request

signup_bp = Blueprint("signup", __name__)

# In-memory user store. Resets on process restart. Not a real database.
USERS = {}


@signup_bp.route("/signup", methods=["POST"])
def signup():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email", "")
    password = payload.get("password", "")

    # INTENTIONAL: no email validation at all. Empty + malformed both pass.
    if email in USERS:
        return jsonify({"error": "already registered"}), 409

    USERS[email] = {"password": password}
    return jsonify({"ok": True, "email": email}), 201
