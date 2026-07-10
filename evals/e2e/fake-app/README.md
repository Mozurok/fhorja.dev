# wos-e2e-fake-app

Synthetic Flask signup app used as the product repo for the Fhorja E2E walkthrough at `evals/e2e/walkthrough.md`.

Not a real reference. Do NOT use this code as a starting point for anything other than the walkthrough.

## Layout

```
fake-app/
  app.py                # Flask app wiring (entrypoint; create_app + /health)
  handlers/
    __init__.py
    signup.py           # /signup endpoint with INTENTIONAL issues (the slices fix these)
  requirements.txt
```

The `/signup` handler lives at `handlers/signup.py` so the `wos/bug-classes/` library's file-pattern globs (which target `handlers/**`, `api/**`, etc.) match this path and the sweep fires its expected findings.

## Run locally (optional manual verification)

```bash
pip install -r requirements.txt
python app.py
# Then in another terminal:
curl -X POST http://localhost:5001/signup \
  -H 'Content-Type: application/json' \
  -d '{"email": "", "password": "x"}'
# Returns 201 today (intentional bug; the walkthrough's Slice 1 fixes this).
```

Note: port 5001 (not 5000) to avoid macOS Monterey+ AirPlay Receiver collision.

## Known intentional issues

See the docstring at the top of `handlers/signup.py`. The walkthrough's slices fix these one at a time so the Fhorja commands have real diffs to analyze.
