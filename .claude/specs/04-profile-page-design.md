# Spec: Profile Page Design

## Overview

This step replaces the `/profile` stub with a designed profile page. Today `GET /profile` returns the plain string "Profile page — coming in Step 4". Step 4 adds `templates/profile.html` and a page-only stylesheet, and limits the route to signed-in users. The page has four parts: a user info card, a row of summary stats, a recent-transactions table and a spending-by-category breakdown. In this step every value on the page is **hardcoded** in the route, so the layout, visual hierarchy and responsive behaviour can be built and reviewed on their own. Step 5 will swap in real database queries without touching the markup. This step comes after login and logout (Step 3) because the page needs a signed-in user, and before the expense pages (Steps 7–9) because those pages will link back here.

## Depends on

- **Step 1 — Database setup** (complete): the `users` and `expenses` schemas and the `CATEGORIES` tuple in `database/db.py`. The hardcoded data must use only these category names.
- **Step 2 — Registration** (complete): flash rendering in `base.html`, and the `temp_db`, `app` and `client` fixtures in `conftest.py`.
- **Step 3 — Login and Logout** (complete): `session["user_id"]`, `session["user_name"]`, the signed-in navbar (`.nav-user`) and the `login_as` test helper pattern.

## Routes

- `GET /profile`: renders `profile.html` with hardcoded profile data. If `session.get("user_id")` is not set, it redirects to `url_for("login")` with a 302 and never renders the page. Access: logged-in.

No other routes are added or changed.

## Database changes

No database changes. All data on this page is hardcoded in this step. Real queries, such as fetching the user by id and summarising their expenses, belong to Step 5.

## Templates

**Create:**
- `templates/profile.html`:
  - Extends `base.html`.
  - Sets `{% block title %}Profile — Spendly{% endblock %}`.
  - Links `profile.css` in `{% block head %}` through `url_for('static', filename='css/profile.css')`.

  Sections, from top to bottom:
  1. **User info card:**
     - An avatar circle with the user's initials, worked out in the template from `user.name`.
     - The name, set in `--font-display`, then the email and "Member since <Month YYYY>".
     - An "Add expense" button linking to `url_for('add_expense')`. It points at the existing stub for now.
  2. **Summary stats:** three stat cards.
     - Total spent: `₹` with 2 decimals.
     - Transactions: a count.
     - Top category.
  3. **Recent transactions:**
     - A table with date, description, a category badge and a right-aligned amount.
     - When the description is `None`, show "—".
     - When the list is empty, show an empty-state row.
  4. **Spending by category:**
     - One row per category with its name, amount and a horizontal bar whose width is that category's share of the total.
     - The bar width is set with inline `style="width: {{ c.pct }}%"`. This is the only inline style allowed, because the width is data, not styling.
  - Every value comes from context variables. No literal numbers, names or amounts appear in the markup, so Step 5 only needs to change the route.

**Modify:**
- `templates/base.html`: when signed in, wrap the navbar user name in a link to `url_for('profile')`, keeping the `nav-user` class and the escaped name. The "Sign out" link stays as it is.

## Files to change

- `app.py`: replace the `/profile` stub.
  - When `session.get("user_id")` is not set, redirect to login.
  - Otherwise render `profile.html` with a hardcoded context:
    - `user`:
      - `name` is `session["user_name"]`, so the page greets whoever is signed in.
      - `email` and `member_since` are placeholders.
    - `stats`: `total_spent`, `transaction_count` and `top_category`.
    - `recent_expenses`: about 5 dicts, each with `date`, `description`, `category` and `amount`. At least one has `description` set to `None`.
    - `category_breakdown`: a list of `{name, amount, pct}` sorted by amount, highest first.
  - Keep the hardcoded data in module-level constants such as `SAMPLE_STATS`, not inline in the `render_template` call.
  - Base the amounts on `SAMPLE_EXPENSES` in `db.py`, which total 331.84, so Step 5's real numbers look the same.
- `templates/base.html`: the navbar link described under Templates.
- `tests/test_registration.py`: remove the `/profile` row from the `test_stub_routes_unchanged` parametrize list. The three expense stub rows stay.
- `CLAUDE.md`:
  - Change the `GET /profile` row to "Implemented — logged-in only; renders `profile.html` with hardcoded data until Step 5".
  - Add `profile.css` to the architecture tree.

## Files to create

- `templates/profile.html`
- `static/css/profile.css`: styles for the profile page only.
  - Cards use `--paper-card`, a 1px `--border` and `--radius-md`.
  - Content sits inside a `--max-width` container.
  - The stats sit in a 3-column grid, and the table and breakdown sit in a 2-column grid. Both collapse to one column at `max-width: 900px`.
  - At `max-width: 600px` the padding tightens and the table scrolls horizontally inside a wrapper.
  - Each category gets its own badge and bar colour, built from existing variables only (`--accent`, `--accent-light`, `--accent-2`, `--accent-2-light`, `--danger`, `--danger-light`, `--ink-muted`, `--border-soft` and so on). Where two categories share a colour, that's fine.
  - Amounts use `font-variant-numeric: tabular-nums`.
- `tests/test_profile.py`: tests for the profile route, listed under Definition of done. Log in with the `client.session_transaction()` pattern used by `login_as` in `tests/test_login.py`.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs.
- Parameterised queries only. This step adds no queries, but any query that does get added must use `?` placeholders and live in `database/db.py`.
- Passwords hashed with werkzeug. This step does not touch the auth or password code.
- Use CSS variables and never hardcode hex values: none in `profile.css`, and no new ones in `style.css` outside `:root`.
- All templates extend `base.html`.
- No `<style>` tags. Page styles go only in `static/css/profile.css`.
- Use `url_for()` for every internal link and redirect.
- No database access in the `/profile` route. It uses hardcoded data only.
- No JavaScript is needed for this page. If any is added, it must be vanilla.
- Do not add a `login_required` decorator. Use an inline session check, as the other routes do.
- Show currency as `₹` with 2 decimals, using Jinja's `"%.2f"|format(...)`.
- Do not change the expense stub routes (Steps 7–9).
- Keep the app on port 5001.

## Definition of done

- [ ] `python app.py` starts on http://127.0.0.1:5001 with no errors.
- [ ] Visiting `/profile` while signed out redirects to `/login`.
- [ ] After signing in as `demo@spendly.com` / `demo123`, `/profile` returns 200 and shows a user card with "Demo User", the initials "DU", an email and "Member since".
- [ ] The page shows three stat cards: Total spent (`₹` with 2 decimals), Transactions and Top category.
- [ ] Recent transactions shows the date, the description (or "—"), a category badge and a right-aligned amount.
- [ ] The category breakdown shows one bar per category. Bar widths are proportional to each share, and the largest category is listed first.
- [ ] The navbar user name links to `/profile`, and "Sign out" still works.
- [ ] At about 375px wide the cards stack into one column and the page has no horizontal scroll.
- [ ] `profile.css` is loaded only on `/profile`, and the page has no `<style>` tags.
- [ ] `profile.css` contains no hex colours.
- [ ] `/expenses/add`, `/expenses/<id>/edit` and `/expenses/<id>/delete` still return their stub strings.
- [ ] `pytest` passes, including the updated `test_registration.py`. The new `tests/test_profile.py` covers:
  - the redirect to `/login` when signed out
  - a 200 response with the user's name when signed in
  - all four section headings present
  - a `₹` amount rendered
  - the navbar profile link when signed in
