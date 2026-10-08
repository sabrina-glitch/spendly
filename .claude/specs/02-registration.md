# Spec: Registration

## Overview

This step makes the existing registration page work. `GET /register` already renders `register.html`, but submitting the form currently returns 405. Step 2 adds POST handling for `/register`. The route validates the submitted name, email and password, hashes the password with werkzeug and stores the new user through a helper in `database/db.py`. On success it redirects to the login page with a success message. Registration comes right after the data layer (Step 1) because every later step needs real user accounts: login and logout (Step 3), profile (Step 4) and expenses (Steps 7–9). This step only creates accounts. It does not log the user in, and it adds no session or auth handling; that belongs to Step 3.

## Depends on

- **Step 1 — Database setup** (complete): the `users` table, `get_db()`, `init_db()`, `seed_db()`, `PRAGMA foreign_keys = ON`.

## Routes

- `GET /register` — render the registration form (already exists, unchanged behaviour) — public
- `POST /register` — validate input, create the user, flash a success message and redirect to `GET /login`. On a validation error, re-render `register.html` with an error message and the submitted name and email filled back in. — public

Both methods are served by the existing `register` view function using `methods=["GET", "POST"]`. Do not add a separate function.

## Database changes

No database changes. The existing `users` table already has `name`, `email` (UNIQUE), `password_hash` and `created_at`.

Add new helper functions to `database/db.py`. These are code changes, not schema changes:

- `get_user_by_email(email)` returns the `sqlite3.Row` for that email, or `None`.
- `create_user(name, email, password)`:
  - hashes `password` with `werkzeug.security.generate_password_hash`
  - inserts the row with a parameterised query
  - returns the new user's `id`
  - returns `None` if the email already exists, by catching `sqlite3.IntegrityError`, so a race between check and insert is still safe
  - always closes the connection

Email is stored case-sensitively by the schema (no `COLLATE NOCASE`). The route must normalise emails with `.strip().lower()` before both lookup and insert. Do not change the schema.

## Templates

**Create:** none.

**Modify:**
- `templates/register.html`:
  - Change the form `action="/register"` to `action="{{ url_for('register') }}"`.
  - Pre-fill submitted values: `value="{{ name or '' }}"` and `value="{{ email or '' }}"`. Never pre-fill the password.
  - Add `minlength="8"` to the password input.
  - Add a "Confirm password" field (`name="confirm_password"`, `type="password"`, `minlength="8"`, `required`) directly below the password field. Never pre-fill it.
- `templates/base.html`:
  - Render flashed messages with `get_flashed_messages(with_categories=true)` in a container above the page content.
  - Each message gets the class `flash flash-<category>`.
  - Replace the hardcoded footer links `/terms` and `/privacy` with `url_for('terms')` and `url_for('privacy')`.

## Files to change

- `app.py`:
  - Import `request`, `redirect`, `url_for` and `flash` from flask.
  - Import `create_user` and `get_user_by_email` from `database.db`.
  - Set `app.secret_key` from `os.environ.get("SECRET_KEY", "dev-secret-change-me")`.
  - Make `/register` accept GET and POST.
- `database/db.py`: add `get_user_by_email()` and `create_user()`.
- `templates/register.html`: the changes listed under Templates.
- `templates/base.html`: flash rendering and the `url_for` footer links.
- `static/css/style.css`:
  - Add `.flash`, `.flash-success` and `.flash-error` styles using existing variables (`--accent`, `--accent-light`, `--danger`, `--danger-light`, `--radius-sm`).
  - Replace the hardcoded `#f5c6c2` border in `.auth-error` with a CSS variable. Add `--danger-border` to `:root` if needed.
- `conftest.py`: add `app` and `client` fixtures.
  - Set `TESTING = True`.
  - Monkeypatch `database.db.DB_PATH` to a tmp file and call `init_db()`.
  - Return `app.test_client()`.

## Files to create

- `tests/test_registration.py`: route and helper tests (see Definition of done).

## New dependencies

No new dependencies. Werkzeug, Flask and pytest-flask are already in `requirements.txt`.

## Rules for implementation

- No SQLAlchemy or ORMs. Use raw `sqlite3` via `get_db()` only.
- Parameterised queries only (`?` placeholders). Never use f-strings or string concatenation in SQL.
- Hash passwords with werkzeug `generate_password_hash`. Never store or log the plain password.
- Use CSS variables. Never hardcode hex values.
- All templates extend `base.html`.
- All DB access lives in `database/db.py`. The route calls helpers only and never opens a connection itself.
- Every `get_db()` connection must be closed (`with conn:` only commits). Use `try/finally`.
- Use `url_for()` for every internal link and redirect. Do not hardcode paths.
- Server-side validation, in this order, with the first failure shown as `error`:
  1. Name is required after strip: "Please enter your name."
  2. Email is required and must contain `@` and a `.` after it: "Please enter a valid email address."
  3. Password must be at least 8 characters: "Password must be at least 8 characters."
  4. Confirm password must exactly match password: "Passwords do not match."
  5. The email must not already be registered: "An account with that email already exists."
- On success: `flash("Account created — please sign in.", "success")` and then `redirect(url_for("login"))` (HTTP 302).
- Do not log the user in and do not touch `session`. That is Step 3.
- Do not implement or modify the `/logout`, `/profile` or expense stub routes.
- The app stays on port 5001.
- Keep the `register` route single-responsibility: read the form, validate, call `create_user`, then redirect or render.

## Definition of done

- [ ] `python app.py` starts on http://127.0.0.1:5001 with no errors.
- [ ] `GET /register` shows the form. Viewing the page source shows the form action is generated (`/register`) and there are no hardcoded links in the footer.
- [ ] Submitting a valid name, email and 8+ character password (with a matching confirm password) redirects to `/login` and shows the "Account created — please sign in." message once. The message is gone after refreshing.
- [ ] The new row exists in `spendly.db`'s `users` table. Its `password_hash` starts with a werkzeug scheme prefix (for example `scrypt:` or `pbkdf2:`) and is not the plain password.
- [ ] Registering `Test@Example.com ` stores `test@example.com`.
- [ ] Registering with an email that already exists (for example `demo@spendly.com`, or `DEMO@spendly.com`) re-renders the form with "An account with that email already exists." and no new row is created.
- [ ] Submitting an empty name, an invalid email, a 7-character password or a confirm password that does not match each shows the matching error. The name and email fields keep their values and both password fields are empty.
- [ ] `/logout`, `/profile` and the expense routes still return their stub strings.
- [ ] No hex colours were added to `style.css`, and the old `#f5c6c2` is gone.
- [ ] `pytest` passes. That includes the existing `tests/test_db.py` and new `tests/test_registration.py` covering:
  - a successful POST (302 to `/login`, row created, password hashed)
  - a duplicate email, including different letter case
  - each validation error
  - `create_user` returning `None` on a duplicate
  - `get_user_by_email` returning `None` for an unknown email
