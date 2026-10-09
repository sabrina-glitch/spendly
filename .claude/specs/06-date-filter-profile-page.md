# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date-range filter to the profile page. At the moment `/profile`
shows the logged-in user's figures for all time. A filter bar above the summary
stats lets the user narrow the summary stats, recent transactions and category
breakdown to a chosen period. There are quick presets (This month, Last 30
days, Last 3 months, Last 6 months, All time) and a custom start/end date form. The filter is passed as GET
query parameters (`?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`), so a filtered
view can be bookmarked and needs no new route or schema change. Step 5 put
live data on the page; this step makes that data explorable before
add/edit/delete arrive in Steps 7–9.

## Depends on
- Step 1: Database setup (`expenses.date` stored as ISO `YYYY-MM-DD` text)
- Step 3: Login / Logout (`session["user_id"]`)
- Step 4: Profile page UI (`templates/profile.html`, `static/css/profile.css`)
- Step 5: Backend routes for profile page (`get_recent_transactions`,
  `get_summary_stats`, `get_category_breakdown` in `database/db.py`)

## Routes
No new routes. The existing `GET /profile` route is modified:

- `GET /profile` – logged-in – now accepts optional query params
  `start_date` and `end_date` (both `YYYY-MM-DD`, both inclusive)

Query-param behaviour:
- Neither param present → all time (same output as Step 5)
- Only `start_date` → everything on or after that date
- Only `end_date` → everything on or before that date
- A param that is empty or not a valid `YYYY-MM-DD` date is ignored
  (treated as absent). The page still renders with 200 and shows the
  inline message "Invalid date ignored."
- `start_date` later than `end_date` → no filter is applied, the page
  renders with 200, and it shows the inline message "Start date must be on or
  before end date."
- Unauthenticated access still redirects to `/login` (unchanged)

## Database changes
No database changes. `expenses.date` is already `TEXT NOT NULL` in ISO
format, so string comparison (`date >= ?` / `date <= ?`) is correct for range
filtering.

The existing query helpers in `database/db.py` gain optional keyword
arguments. Defaults keep the Step 5 behaviour, so existing callers and tests
still work:
- `get_recent_transactions(user_id, limit=10, start_date=None, end_date=None)`
- `get_summary_stats(user_id, start_date=None, end_date=None)`
- `get_category_breakdown(user_id, start_date=None, end_date=None)`

Each helper adds `AND date >= ?` and/or `AND date <= ?` only when that bound
is not `None`. Values are always bound as parameters. The WHERE fragment may
be built from fixed string literals only, never from user input. A small
private helper such as `_date_range_clause(start_date, end_date)` returning
`(sql_fragment, params)` is acceptable, which avoids repeating the logic
three times.

## Templates
- **Create**: none
- **Modify**: `templates/profile.html`
  - Add a filter bar section between `.profile-top` and `.profile-grid`
    containing:
    - Preset links built with `url_for('profile', ...)`: "This month"
      (1st of the current month → today), "Last 30 days" (today − 29 days →
      today), "Last 3 months" / "Last 6 months" (same day 3 / 6 calendar
      months ago, clamped to the month's last day → today) and "All time"
      (no params). The active preset gets an
      `is-active` class and `aria-current="true"`.
    - A `<form method="get" action="{{ url_for('profile') }}">` with two
      `<input type="date">` fields named `start_date` and `end_date`
      (pre-filled with the current valid values), an "Apply" submit button
      and a "Clear" link to `url_for('profile')`.
    - The inline error message, when one is present (`role="alert"`).
  - Total spent hint: show "All recorded expenses" when unfiltered, otherwise
    the active range, e.g. "1 Oct 2026 – 9 Oct 2026". Open-ended ranges read
    "From 1 Oct 2026" or "Until 9 Oct 2026".
  - Recent transactions empty state: when a filter is active and returns
    nothing, show "No expenses in this period." instead of
    "No expenses yet."
  - Category breakdown empty state: when filtered, show
    "No spending in this period."

## Files to change
- `app.py` – `profile()` reads `request.args`, validates the dates, passes
  `start_date`/`end_date` to the three helpers and passes the filter state
  (`start_date`, `end_date`, `active_preset`, `filter_error`, preset date
  values) to the template. Date parsing/validation lives in a small
  module-level helper in `app.py` (e.g. `parse_date_param(value)` returning
  a `date` or `None`), so the route stays readable. It must not touch the DB.
- `database/db.py` – add optional `start_date` / `end_date` params to the
  three profile query helpers
- `templates/profile.html` – filter bar, range-aware hints and empty states
- `static/css/profile.css` – filter bar styles (preset pills, date inputs,
  error message), responsive down to mobile width

## Files to create
- `tests/test_date_filter.py` – unit and route tests (below)

## New dependencies
No new dependencies. Use the standard library's `datetime.date` /
`date.fromisoformat` for parsing.

## Rules for implementation
- No SQLAlchemy or ORMs – raw `sqlite3` via `get_db()` only
- Parameterised queries only – date bounds go through `?` placeholders,
  never f-strings or `%` formatting into SQL
- Passwords hashed with werkzeug (no auth changes in this step; do not
  regress existing hashing)
- Use CSS variables – never hardcode hex values in `profile.css`
- All templates extend `base.html`
- No inline `<style>` tags or new `style=""` attributes (the existing
  category bar width is the only exception)
- Every link and form action uses `url_for()` – no hardcoded `/profile?...`
- No JavaScript is required. The form works with plain GET submission. If
  any JS is added, it must be vanilla and live in `static/js/main.js`.
- Currency stays ₹
- DB helpers must close their connection before returning
- Validate dates with `date.fromisoformat` and pass them to the DB as
  ISO strings (`date.isoformat()`), never as the raw request value
- `pct` values in a filtered category breakdown must still sum to 100
- A filtered range with no expenses returns zeros/empty lists, not errors
- Do not implement stub routes for Steps 7–9

## Tests to write
File: `tests/test_date_filter.py`. Use a temp DB via monkeypatching
`database.db.DB_PATH`, and insert expenses with fixed dates (e.g.
2026-01-05, 2026-01-20, 2026-02-10, 2026-03-15) so the results don't depend
on today's date.

### Unit tests
| Function | Input | Expected |
|---|---|---|
| `get_summary_stats` | no bounds | same as all-time total/count |
| `get_summary_stats` | start + end covering Jan only | Jan total and count only |
| `get_summary_stats` | bounds equal to an expense's date | that expense included (inclusive) |
| `get_summary_stats` | range with no expenses | `total_spent` 0, `transaction_count` 0, `top_category` "—" |
| `get_recent_transactions` | only `start_date` | only expenses on/after it, newest-first |
| `get_recent_transactions` | only `end_date` | only expenses on/before it |
| `get_category_breakdown` | range | only categories in range; `pct` ints sum to 100 |
| `get_category_breakdown` | empty range | `[]` |
| all three | another user's expenses in range | never included |

### Route tests
- `GET /profile?start_date=...&end_date=...` unauthenticated → 302 to `/login`
- Authenticated, no params → 200, totals match all-time
- Authenticated, valid Jan range → 200, shows only the Jan total and Jan rows
- `start_date=not-a-date` → 200, "Invalid date ignored." shown, all-time totals
- `start_date` > `end_date` → 200, the ordering error is shown, all-time totals
- Valid range with no expenses → 200, "No expenses in this period." shown
- Date inputs are pre-filled with the submitted valid values
- "All time" preset link has no query string; "This month" link carries
  `start_date` set to the 1st of the current month

## Definition of done
- [ ] Visiting `/profile` with no query string shows the same figures as before (seed user: ₹331.84, 8 transactions, top category Bills)
- [ ] A filter bar with "This month", "Last 30 days", "Last 3 months", "Last 6 months" and "All time" presets plus start/end date inputs appears between the header/stats row and the transactions/categories grid
- [ ] Choosing a start and end date and clicking Apply reloads `/profile?start_date=…&end_date=…`, and all three sections (stats, transactions, breakdown) reflect only that range
- [ ] Filtering the seed user to the 1st–10th of the current month shows 3 transactions totalling ₹178.25
- [ ] Both bounds are inclusive: a range starting and ending on one expense's date shows exactly that expense
- [ ] The active preset is visually highlighted, and the date inputs keep the submitted values after reload
- [ ] The Total spent hint shows the active date range when filtered
- [ ] A range with no expenses shows ₹0.00, 0 transactions, "No expenses in this period." and "No spending in this period." with no server error
- [ ] `?start_date=garbage` renders 200 with "Invalid date ignored." and all-time data
- [ ] `start_date` after `end_date` renders 200 with "Start date must be on or before end date." and all-time data
- [ ] Category percentages still add up to 100% when filtered
- [ ] The filter bar is usable at mobile width with no horizontal scroll
- [ ] `pytest` passes, including the existing Step 5 tests
