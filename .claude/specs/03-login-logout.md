# Spec: Login and Logout

## Overview

This step makes signing in and out work. `GET /login` already renders `login.html`, but submitting the form currently returns 405, and `/logout` is a stub that returns a plain string. Step 3 adds POST handling for `/login`. The route looks up the user by email, checks the password with werkzeug's `check_password_hash` and stores the user's id and name in Flask's signed `session` cookie. `/logout` clears the session and sends the user back to the landing page. The navbar changes with auth state: signed-out visitors see "Sign in" and "Get started", and signed-in users see their name and "Sign out". This step comes after registration (Step 2) because there are now real accounts to sign in to. It comes before profile (Step 4) and expenses (Steps 7–9) because those pages need to know who the current user is.

## Depends on

- **Step 1 — Database setup** (complete): the `users` table, `get_db()`, `init_db()`, `seed_db()` and the demo user `demo@spendly.com` / `demo123`.
- **Step 2 — Registration** (complete): `get_user_by_email()`, passwords hashed with `generate_password_hash`, `app.secret_key`, flash message rendering in `base.html` and the `app` and `client` fixtures in `conftest.py`.

## Routes

- `GET /login`: renders the sign-in form. This route already exists. If the user is already signed in, redirect to `url_for("landing")` instead. Access: public.
- `POST /login`: normalises the email, checks the credentials, and on success clears and then fills `session`, flashes a welcome message and redirects to `url_for("landing")`. On failure it re-renders `login.html` with a generic error and the submitted email filled back in. Access: public.
- `GET` and `POST /register`: if the user is already signed in, redirect to `url_for("landing")` without rendering the form or creating an account. Otherwise behaviour is unchanged from Step 2. Access: public.
- `GET /logout`: clears `session`, flashes "You have been signed out.", and redirects to `url_for("landing")`. This replaces the Step 3 stub. It is safe to call when the user is not signed in, because it simply redirects. Access: public.

`GET` and `POST /login` are both served by the existing `login` view function using `methods=["GET", "POST"]`. Do not add a separate function.

## Database changes

No database changes. The `users` table already has `email` and `password_hash`, and `get_user_by_email()` already exists in `database/db.py`.

No new DB helpers are needed. Checking the password is not DB logic, so the route calls `get_user_by_email()` and then `check_password_hash()` directly.

## Templates

**Create:** none.

**Modify:**
- `templates/login.html`:
  - Change the form `action="/login"` to `action="{{ url_for('login') }}"`.
  - Pre-fill the email field with `value="{{ email or '' }}"`. Never pre-fill the password.
- `templates/base.html`: make the navbar `.nav-links` depend on auth state.
  - Signed in (`session.get('user_id')`): show the user's name (`session.get('user_name')`) in a `<span class="nav-user">`, then a "Sign out" link to `url_for('logout')` with class `nav-cta`.
  - Signed out: keep the existing "Sign in" and "Get started" links.

## Files to change

- `app.py`:
  - Import `session` from flask and `check_password_hash` from `werkzeug.security`.
  - Make `/login` accept GET and POST and implement the login logic.
  - Replace the `/logout` stub.
- `templates/login.html`: the changes listed under Templates.
- `templates/base.html`: the auth-aware navbar.
- `static/css/style.css`: add a `.nav-user` style (muted ink colour, medium weight) using existing variables only. Make sure the existing mobile rule `.nav-links a:not(.nav-cta) { display: none; }` still leaves "Sign out" visible. It should, because "Sign out" has the `nav-cta` class.
- `CLAUDE.md`: in the routes table, mark `GET /logout` as implemented and record that `/login` now accepts POST.

## Files to create

- `tests/test_login.py`: login and logout route tests (see Definition of done).

## New dependencies

No new dependencies. `werkzeug.security.check_password_hash` ships with Werkzeug, which Flask already installs.

## Rules for implementation

- No SQLAlchemy or ORMs. Use raw `sqlite3` via the helpers in `database/db.py` only.
- Parameterised queries only (`?` placeholders). Never use f-strings or string concatenation in SQL.
- Verify passwords with werkzeug `check_password_hash`. Never compare plain passwords, and never store or log the submitted password.
- Use CSS variables. Never hardcode hex values.
- All templates extend `base.html`.
- No DB access in routes. Use `get_user_by_email()` only, and never open a connection in `app.py`.
- Use `url_for()` for every internal link, form action and redirect.
- Normalise the email with `.strip().lower()` before the lookup, just like registration.
- Use one generic error for every failure: an empty field, an unknown email or a wrong password all show "Invalid email or password." Never reveal whether an email is registered.
- On a successful login:
  1. `session.clear()`, which prevents session fixation.
  2. `session["user_id"] = user["id"]`
  3. `session["user_name"] = user["name"]`
  4. `flash(f"Welcome back, {user['name']}!", "success")`
  5. `redirect(url_for("landing"))` (HTTP 302)
- Logout uses `session.clear()` and then `flash("You have been signed out.", "success")` before the redirect.
- Store only `user_id` and `user_name` in the session. Never store the password hash or the email.
- Do not add a `login_required` decorator and do not protect other routes. That belongs to the steps that build those pages.
- Do not implement or modify the `/profile` or expense stub routes.
- The app stays on port 5001.
- Keep each route single-responsibility: read the form, validate, set the session, then redirect or render.

## Definition of done

- [ ] `python app.py` starts on http://127.0.0.1:5001 with no errors.
- [ ] On `GET /login`, the page source shows a generated form action (`/login`).
- [ ] Signing in as `demo@spendly.com` / `demo123` redirects to `/` with "Welcome back, Demo User!" shown once.
- [ ] After signing in, the navbar shows "Demo User" and "Sign out" instead of "Sign in" and "Get started".
- [ ] Signing in with ` DEMO@Spendly.com ` (mixed case, with spaces) and `demo123` succeeds.
- [ ] A wrong password, an unregistered email or an empty field each re-renders the form with "Invalid email or password.". The email field keeps its value and the password field is empty.
- [ ] A user registered through `/register` can then sign in with their new credentials.
- [ ] Visiting `/login` while signed in redirects to `/`.
- [ ] Visiting or posting to `/register` while signed in redirects to `/` and creates no account.
- [ ] Clicking "Sign out" redirects to `/` and shows "You have been signed out.". The navbar is back to "Sign in" and "Get started", and the session no longer contains `user_id`.
- [ ] Visiting `/logout` while signed out redirects to `/` without an error.
- [ ] `/profile` and the expense routes still return their stub strings.
- [ ] No hex colours were added to `style.css`.
- [ ] `pytest` passes, including the existing `tests/test_db.py` and `tests/test_registration.py`. The new `tests/test_login.py` must cover:
  - a successful login (302 to `/`, `session["user_id"]` and `session["user_name"]` set)
  - email case and whitespace normalisation
  - a wrong password, an unknown email and empty fields, each showing the generic error with no session set
  - `GET /login` redirecting when already signed in
  - logout clearing the session and redirecting to `/`
  - logout when not signed in
  - the navbar showing "Sign out" when signed in and "Sign in" when signed out
