"""Step 6 — date-range filter on /profile."""
import re
from datetime import date, timedelta

import pytest


def add_expense(db, user_id, amount, category, date_str, description=None):
    conn = db.get_db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, date_str, description),
            )
    finally:
        conn.close()


def login_as(client, user_id, name="Filter User"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = name


def profile_html(client, query=""):
    response = client.get("/profile" + query)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def tbody(html):
    return html.split("<tbody>", 1)[1].split("</tbody>", 1)[0]


@pytest.fixture
def user_id(temp_db):
    uid = temp_db.create_user("Filter User", "filter@example.com", "password123")
    add_expense(temp_db, uid, 10.00, "Food", "2026-01-05", "Jan lunch")
    add_expense(temp_db, uid, 20.50, "Transport", "2026-01-20", "Jan taxi")
    add_expense(temp_db, uid, 30.00, "Bills", "2026-02-10", "Feb bill")
    add_expense(temp_db, uid, 40.25, "Food", "2026-03-15", "Mar dinner")
    return uid


@pytest.fixture
def other_user(temp_db, user_id):
    uid = temp_db.create_user("Other User", "other@example.com", "password123")
    add_expense(temp_db, uid, 999.00, "Shopping", "2026-01-10", "Not yours")
    return uid


@pytest.fixture
def logged_in(client, user_id):
    login_as(client, user_id)
    return client


# ------------------------------------------------------------------ #
# Unit tests — DB helpers                                             #
# ------------------------------------------------------------------ #

def test_summary_no_bounds_is_all_time(temp_db, user_id):
    stats = temp_db.get_summary_stats(user_id)
    assert stats == temp_db.get_summary_stats(user_id, start_date=None, end_date=None)
    assert stats["total_spent"] == 100.75
    assert stats["transaction_count"] == 4


def test_summary_january_only(temp_db, user_id):
    stats = temp_db.get_summary_stats(user_id, "2026-01-01", "2026-01-31")
    assert stats["total_spent"] == 30.5
    assert stats["transaction_count"] == 2
    assert stats["top_category"] == "Transport"


def test_summary_bounds_are_inclusive(temp_db, user_id):
    stats = temp_db.get_summary_stats(user_id, "2026-02-10", "2026-02-10")
    assert stats["transaction_count"] == 1
    assert stats["total_spent"] == 30.0


def test_summary_empty_range(temp_db, user_id):
    stats = temp_db.get_summary_stats(user_id, "2025-01-01", "2025-12-31")
    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


def test_recent_start_only(temp_db, user_id):
    rows = temp_db.get_recent_transactions(user_id, start_date="2026-02-10")
    assert [r["date"] for r in rows] == ["2026-03-15", "2026-02-10"]


def test_recent_end_only(temp_db, user_id):
    rows = temp_db.get_recent_transactions(user_id, end_date="2026-01-20")
    assert [r["date"] for r in rows] == ["2026-01-20", "2026-01-05"]


def test_recent_limit_still_applies(temp_db, user_id):
    rows = temp_db.get_recent_transactions(user_id, limit=1, start_date="2026-01-01")
    assert [r["date"] for r in rows] == ["2026-03-15"]


def test_breakdown_range(temp_db, user_id):
    breakdown = temp_db.get_category_breakdown(user_id, "2026-01-01", "2026-01-31")
    assert [c["name"] for c in breakdown] == ["Transport", "Food"]
    assert sum(c["pct"] for c in breakdown) == 100
    assert all(isinstance(c["pct"], int) for c in breakdown)


def test_breakdown_pct_rounding_sums_to_100(temp_db, user_id):
    for category in ("Health", "Other", "Shopping"):
        add_expense(temp_db, user_id, 10.00, category, "2026-05-01")
    breakdown = temp_db.get_category_breakdown(user_id, "2026-05-01", "2026-05-01")
    assert sorted(c["pct"] for c in breakdown) == [33, 33, 34]


def test_breakdown_empty_range(temp_db, user_id):
    assert temp_db.get_category_breakdown(user_id, "2025-01-01", "2025-12-31") == []


def test_other_users_expenses_excluded(temp_db, user_id, other_user):
    jan = ("2026-01-01", "2026-01-31")
    assert temp_db.get_summary_stats(user_id, *jan)["total_spent"] == 30.5
    rows = temp_db.get_recent_transactions(user_id, start_date=jan[0], end_date=jan[1])
    assert all(r["amount"] != 999.0 for r in rows)
    names = [c["name"] for c in temp_db.get_category_breakdown(user_id, *jan)]
    assert "Shopping" not in names


# ------------------------------------------------------------------ #
# Route tests — GET /profile                                          #
# ------------------------------------------------------------------ #

def test_unauthenticated_filtered_redirects(client, temp_db):
    response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_no_params_shows_all_time(logged_in):
    html = profile_html(logged_in)
    assert "₹100.75" in html
    assert '<p class="stat-value">4</p>' in html
    assert "All recorded expenses" in html
    assert "filter-error" not in html


def test_january_range(logged_in):
    html = profile_html(logged_in, "?start_date=2026-01-01&end_date=2026-01-31")
    assert "₹30.50" in html
    assert '<p class="stat-value">2</p>' in html
    assert "1 Jan 2026 – 31 Jan 2026" in html
    body = tbody(html)
    assert 'datetime="2026-01-05"' in body
    assert 'datetime="2026-01-20"' in body
    assert 'datetime="2026-02-10"' not in body


def test_open_ended_labels(logged_in):
    assert "From 1 Feb 2026" in profile_html(logged_in, "?start_date=2026-02-01")
    assert "Until 31 Jan 2026" in profile_html(logged_in, "?end_date=2026-01-31")


def test_empty_params_are_ignored_silently(logged_in):
    html = profile_html(logged_in, "?start_date=&end_date=")
    assert "₹100.75" in html
    assert "Invalid date ignored." not in html


@pytest.mark.parametrize("bad", ["not-a-date", "20260105", "2026-02-30"])
def test_invalid_date_ignored(logged_in, bad):
    html = profile_html(logged_in, f"?start_date={bad}")
    assert "Invalid date ignored." in html
    assert "₹100.75" in html
    assert '<p class="stat-value">4</p>' in html


def test_reversed_range(logged_in):
    html = profile_html(logged_in, "?start_date=2026-03-01&end_date=2026-01-01")
    assert "Start date must be on or before end date." in html
    assert "₹100.75" in html
    assert '<p class="stat-value">4</p>' in html


def test_empty_range_messages(logged_in):
    html = profile_html(logged_in, "?start_date=2025-01-01&end_date=2025-12-31")
    assert "₹0.00" in html
    assert "No expenses in this period." in html
    assert "No spending in this period." in html
    assert "No expenses yet." not in html
    assert tbody(html).count("<tr") == 1


def test_inputs_prefilled(logged_in):
    html = profile_html(logged_in, "?start_date=2026-01-01&end_date=2026-01-31")
    assert 'name="start_date" class="form-input" value="2026-01-01"' in html
    assert 'name="end_date" class="form-input" value="2026-01-31"' in html


def test_preset_links(logged_in):
    html = profile_html(logged_in)
    today = date.today()
    assert f"start_date={today.replace(day=1).isoformat()}" in html
    assert f"end_date={today.isoformat()}" in html
    assert 'href="/profile"' in html


def test_all_time_preset_has_no_query_string(logged_in):
    html = profile_html(logged_in, "?start_date=2026-01-01")
    assert re.search(r'href="/profile"\s+class="filter-pill[^"]*"[^>]*>All time', html)


def test_last_30_days_preset(logged_in):
    today = date.today()
    start = (today - timedelta(days=29)).isoformat()
    html = profile_html(logged_in)
    assert f"start_date={start}" in html
    if today.day == 30:  # "This month" covers the same range and wins
        return
    html = profile_html(logged_in, f"?start_date={start}&end_date={today.isoformat()}")
    assert html.count('aria-current="true"') == 1
    assert 'aria-current="true">Last 30 days' in html


def test_active_preset_all_time(logged_in):
    html = profile_html(logged_in)
    assert html.count('aria-current="true"') == 1
    assert 'aria-current="true">All time' in html


def test_active_preset_this_month(logged_in):
    today = date.today()
    query = f"?start_date={today.replace(day=1).isoformat()}&end_date={today.isoformat()}"
    html = profile_html(logged_in, query)
    assert html.count('aria-current="true"') == 1
    assert 'aria-current="true">This month' in html


def test_custom_range_marks_no_preset(logged_in):
    html = profile_html(logged_in, "?start_date=2026-01-01&end_date=2026-01-31")
    assert 'aria-current="true"' not in html


def test_seed_user_first_ten_days(client, temp_db):
    temp_db.seed_db()
    seed_id = temp_db.get_user_by_email("demo@spendly.com")["id"]
    login_as(client, seed_id, "Demo User")
    month_start = date.today().replace(day=1)
    query = (f"?start_date={month_start.isoformat()}"
             f"&end_date={month_start.replace(day=10).isoformat()}")
    html = profile_html(client, query)
    assert '<p class="stat-value">3</p>' in html
    assert "₹178.25" in html


# ------------------------------------------------------------------ #
# Month-based presets (Last 3 / Last 6 months)                        #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("today, months, expected", [
    (date(2026, 10, 9), 3, date(2026, 7, 9)),
    (date(2026, 10, 9), 6, date(2026, 4, 9)),
    (date(2026, 2, 15), 3, date(2025, 11, 15)),   # crosses a year boundary
    (date(2026, 8, 31), 6, date(2026, 2, 28)),    # clamps to a shorter month
    (date(2028, 5, 31), 3, date(2028, 2, 29)),    # clamps to a leap day
])
def test_months_ago(app, today, months, expected):
    from app import months_ago
    assert months_ago(today, months) == expected


@pytest.mark.parametrize("label, months", [("Last 3 months", 3), ("Last 6 months", 6)])
def test_month_preset_link_and_active_state(app, logged_in, label, months):
    from app import months_ago
    today = date.today()
    start = months_ago(today, months).isoformat()
    html = profile_html(logged_in)
    link = re.search(r'<a href="([^"]*)"[^>]*>%s</a>' % label, html, re.S)
    assert link, f"no {label} preset"
    assert f"start_date={start}" in link.group(1)
    assert f"end_date={today.isoformat()}" in link.group(1)

    html = profile_html(logged_in, f"?start_date={start}&end_date={today.isoformat()}")
    assert html.count('aria-current="true"') == 1
    assert f'aria-current="true">{label}' in html


def test_preset_order(logged_in):
    html = profile_html(logged_in)
    labels = ["This month", "Last 30 days", "Last 3 months", "Last 6 months", "All time"]
    positions = [html.index(f">{label}</a>") for label in labels]
    assert positions == sorted(positions)


def test_this_month_wins_over_last_30_days_on_the_30th(app, logged_in, monkeypatch):
    import app as app_module

    class FrozenDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 4, 30)

    monkeypatch.setattr(app_module, "date", FrozenDate)
    # On the 30th, today - 29 days is the 1st, so both presets share one range.
    html = profile_html(logged_in, "?start_date=2026-04-01&end_date=2026-04-30")
    assert html.count('aria-current="true"') == 1
    assert 'aria-current="true">This month' in html
