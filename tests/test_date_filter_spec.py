"""Step 6 — date-range filter on /profile, written from the spec
(.claude/specs/06-date-filter-profile-page.md).

Complements tests/test_date_filter.py; it does not duplicate its cases.
"""
import html as html_lib
import re
from datetime import date, timedelta

import pytest


# Fixed-date fixture data (spec "Tests to write"):
#   2026-01-05  Food       10.00
#   2026-01-20  Transport  20.50
#   2026-02-10  Bills      30.00
#   2026-03-15  Food       40.25
# All time: 100.75 over 4 transactions.


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


def login_as(client, user_id, name="Spec User"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = name


def get_html(client, query=""):
    response = client.get("/profile" + query)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def stat_values(page):
    """[total spent, transaction count, top category] from the stat cards."""
    return re.findall(r'<p class="stat-value">(.*?)</p>', page)


def row_dates(page):
    body = page.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    return re.findall(r'<time datetime="([^"]+)"', body)


def category_names(page):
    return re.findall(r'class="cat-dot cat--[^"]*" aria-hidden="true"></span>\s*([^<\s]+)', page)


def category_pcts(page):
    return [int(p) for p in re.findall(r'<span class="cat-pct">(\d+)%</span>', page)]


def input_value(page, name):
    match = re.search(r'<input[^>]*name="%s"[^>]*>' % name, page)
    assert match, f"no input named {name}"
    value = re.search(r'value="([^"]*)"', match.group(0))
    return value.group(1) if value else ""


def preset_tag(page, label):
    match = re.search(r'(<a\s[^>]*>)\s*%s\s*</a>' % re.escape(label), page)
    assert match, f"no preset link labelled {label!r}"
    return match.group(1)


def preset_href(page, label):
    return html_lib.unescape(re.search(r'href="([^"]*)"', preset_tag(page, label)).group(1))


@pytest.fixture
def user_id(temp_db):
    uid = temp_db.create_user("Spec User", "spec@example.com", "password123")
    add_expense(temp_db, uid, 10.00, "Food", "2026-01-05", "Jan lunch")
    add_expense(temp_db, uid, 20.50, "Transport", "2026-01-20", "Jan taxi")
    add_expense(temp_db, uid, 30.00, "Bills", "2026-02-10", "Feb bill")
    add_expense(temp_db, uid, 40.25, "Food", "2026-03-15", "Mar dinner")
    return uid


@pytest.fixture
def other_user(temp_db, user_id):
    uid = temp_db.create_user("Other User", "other@example.com", "password123")
    add_expense(temp_db, uid, 999.00, "Shopping", "2026-01-10", "Not yours")
    add_expense(temp_db, uid, 555.00, "Health", "2025-06-01", "Other user 2025")
    return uid


@pytest.fixture
def logged_in(client, user_id):
    login_as(client, user_id)
    return client


# ------------------------------------------------------------------ #
# Unit tests — DB helpers                                             #
# ------------------------------------------------------------------ #

def test_summary_stats_start_date_only_counts_on_or_after(temp_db, user_id):
    stats = temp_db.get_summary_stats(user_id, start_date="2026-02-10")
    assert stats["total_spent"] == pytest.approx(70.25)
    assert stats["transaction_count"] == 2


def test_summary_stats_end_date_only_counts_on_or_before(temp_db, user_id):
    stats = temp_db.get_summary_stats(user_id, end_date="2026-01-20")
    assert stats["total_spent"] == pytest.approx(30.5)
    assert stats["transaction_count"] == 2


def test_summary_stats_end_date_day_before_expense_excludes_it(temp_db, user_id):
    stats = temp_db.get_summary_stats(user_id, "2026-01-01", "2026-01-19")
    assert stats["transaction_count"] == 1
    assert stats["total_spent"] == pytest.approx(10.0)


def test_summary_stats_top_category_reflects_range(temp_db, user_id):
    assert temp_db.get_summary_stats(user_id, "2026-02-01", "2026-02-28")["top_category"] == "Bills"
    assert temp_db.get_summary_stats(user_id, start_date="2026-03-01")["top_category"] == "Food"


def test_recent_transactions_start_and_end_newest_first(temp_db, user_id):
    rows = temp_db.get_recent_transactions(user_id, start_date="2026-01-05", end_date="2026-02-10")
    assert [r["date"] for r in rows] == ["2026-02-10", "2026-01-20", "2026-01-05"]


def test_recent_transactions_single_day_is_inclusive(temp_db, user_id):
    rows = temp_db.get_recent_transactions(user_id, start_date="2026-03-15", end_date="2026-03-15")
    assert [r["date"] for r in rows] == ["2026-03-15"]


def test_recent_transactions_empty_range_returns_empty_list(temp_db, user_id):
    assert list(temp_db.get_recent_transactions(user_id, start_date="2027-01-01")) == []


def test_recent_transactions_no_bounds_matches_step5_default(temp_db, user_id):
    default = [r["date"] for r in temp_db.get_recent_transactions(user_id)]
    explicit = [r["date"] for r in temp_db.get_recent_transactions(
        user_id, limit=10, start_date=None, end_date=None)]
    assert default == explicit == ["2026-03-15", "2026-02-10", "2026-01-20", "2026-01-05"]


def test_category_breakdown_excludes_categories_outside_range(temp_db, user_id):
    names = [c["name"] for c in temp_db.get_category_breakdown(user_id, start_date="2026-02-01")]
    assert sorted(names) == ["Bills", "Food"]
    assert "Transport" not in names


def test_category_breakdown_end_only_pct_sums_to_100(temp_db, user_id):
    breakdown = temp_db.get_category_breakdown(user_id, end_date="2026-02-10")
    assert sorted(c["name"] for c in breakdown) == ["Bills", "Food", "Transport"]
    assert all(isinstance(c["pct"], int) for c in breakdown)
    assert sum(c["pct"] for c in breakdown) == 100


def test_category_breakdown_amounts_reflect_range(temp_db, user_id):
    breakdown = temp_db.get_category_breakdown(user_id, start_date="2026-03-01")
    assert len(breakdown) == 1
    assert breakdown[0]["name"] == "Food"
    assert breakdown[0]["amount"] == pytest.approx(40.25)
    assert breakdown[0]["pct"] == 100


def test_all_helpers_ignore_other_users_expenses_when_user_has_none_in_range(
        temp_db, user_id, other_user):
    # Only the other user has an expense in 2025.
    rng = ("2025-01-01", "2025-12-31")
    stats = temp_db.get_summary_stats(user_id, *rng)
    assert stats["total_spent"] == 0
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"
    assert list(temp_db.get_recent_transactions(user_id, start_date=rng[0], end_date=rng[1])) == []
    assert temp_db.get_category_breakdown(user_id, *rng) == []


def test_recent_transactions_excludes_other_users_rows_in_range(temp_db, user_id, other_user):
    rows = temp_db.get_recent_transactions(user_id, start_date="2026-01-01", end_date="2026-01-31")
    assert [r["date"] for r in rows] == ["2026-01-20", "2026-01-05"]


# ------------------------------------------------------------------ #
# Access control                                                      #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated_with_invalid_params_redirects_to_login(client, temp_db):
    response = client.get("/profile?start_date=garbage&end_date=2026-01-01")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_unauthenticated_filtered_follows_to_login(client, temp_db):
    response = client.get("/profile?start_date=2026-01-01&end_date=2026-01-31",
                          follow_redirects=True)
    assert response.request.path == "/login"


def test_profile_filtered_route_excludes_other_users_expenses(logged_in, other_user):
    page = get_html(logged_in, "?start_date=2026-01-01&end_date=2026-01-31")
    assert stat_values(page)[:2] == ["₹30.50", "2"]
    assert "Not yours" not in page
    assert "₹999.00" not in page
    assert "Shopping" not in category_names(page)


# ------------------------------------------------------------------ #
# Route — query-param behaviour                                       #
# ------------------------------------------------------------------ #

def test_profile_no_params_seed_user_matches_step5_figures(client, temp_db):
    temp_db.seed_db()
    seed_id = temp_db.get_user_by_email("demo@spendly.com")["id"]
    login_as(client, seed_id, "Demo User")
    page = get_html(client)
    assert stat_values(page) == ["₹331.84", "8", "Bills"]
    assert "All recorded expenses" in page


def test_profile_start_date_only_filters_all_sections(logged_in):
    page = get_html(logged_in, "?start_date=2026-02-10")
    assert stat_values(page) == ["₹70.25", "2", "Food"]
    assert row_dates(page) == ["2026-03-15", "2026-02-10"]
    assert sorted(category_names(page)) == ["Bills", "Food"]


def test_profile_end_date_only_filters_all_sections(logged_in):
    page = get_html(logged_in, "?end_date=2026-01-20")
    assert stat_values(page) == ["₹30.50", "2", "Transport"]
    assert row_dates(page) == ["2026-01-20", "2026-01-05"]
    assert sorted(category_names(page)) == ["Food", "Transport"]


def test_profile_january_range_filters_category_breakdown(logged_in):
    page = get_html(logged_in, "?start_date=2026-01-01&end_date=2026-01-31")
    assert sorted(category_names(page)) == ["Food", "Transport"]
    assert "Bills" not in category_names(page)
    assert stat_values(page)[2] == "Transport"


def test_profile_filtered_category_pcts_sum_to_100(logged_in, temp_db, user_id):
    for category in ("Health", "Other", "Shopping"):
        add_expense(temp_db, user_id, 10.00, category, "2026-05-01")
    page = get_html(logged_in, "?start_date=2026-05-01&end_date=2026-05-01")
    pcts = category_pcts(page)
    assert len(pcts) == 3
    assert sum(pcts) == 100


def test_profile_single_day_range_shows_exactly_that_expense(logged_in):
    page = get_html(logged_in, "?start_date=2026-02-10&end_date=2026-02-10")
    assert stat_values(page) == ["₹30.00", "1", "Bills"]
    assert row_dates(page) == ["2026-02-10"]
    assert "Start date must be on or before end date." not in page


def test_profile_invalid_end_date_ignored_and_message_shown(logged_in):
    page = get_html(logged_in, "?end_date=garbage")
    assert "Invalid date ignored." in page
    assert stat_values(page)[:2] == ["₹100.75", "4"]


def test_profile_invalid_end_with_valid_start_applies_start_only(logged_in):
    page = get_html(logged_in, "?start_date=2026-02-01&end_date=garbage")
    assert "Invalid date ignored." in page
    assert stat_values(page)[:2] == ["₹70.25", "2"]
    assert row_dates(page) == ["2026-03-15", "2026-02-10"]


def test_profile_invalid_start_with_valid_end_applies_end_only(logged_in):
    page = get_html(logged_in, "?start_date=31-01-2026&end_date=2026-01-31")
    assert "Invalid date ignored." in page
    assert stat_values(page)[:2] == ["₹30.50", "2"]


@pytest.mark.parametrize("bad", ["2026-1-5", "2026-13-01", "2026-02-29",
                                 "2026-01-01' OR '1'='1", "garbage"])
def test_profile_malformed_start_date_falls_back_to_all_time(logged_in, bad):
    response = logged_in.get("/profile", query_string={"start_date": bad})
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Invalid date ignored." in page
    assert stat_values(page)[:2] == ["₹100.75", "4"]
    assert "All recorded expenses" in page


def test_profile_leap_day_is_a_valid_date(logged_in, temp_db, user_id):
    add_expense(temp_db, user_id, 5.00, "Other", "2028-02-29")
    page = get_html(logged_in, "?start_date=2028-02-29&end_date=2028-02-29")
    assert "Invalid date ignored." not in page
    assert stat_values(page)[:2] == ["₹5.00", "1"]


def test_profile_invalid_date_message_has_alert_role(logged_in):
    page = get_html(logged_in, "?start_date=garbage")
    assert re.search(r'role="alert"[^>]*>\s*Invalid date ignored\.', page)


def test_profile_invalid_date_input_not_prefilled_with_raw_value(logged_in):
    page = get_html(logged_in, "?start_date=garbage&end_date=2026-01-31")
    assert input_value(page, "start_date") == ""
    assert input_value(page, "end_date") == "2026-01-31"
    assert "garbage" not in page


def test_profile_empty_start_with_valid_end_applies_end_silently(logged_in):
    page = get_html(logged_in, "?start_date=&end_date=2026-01-20")
    assert "Invalid date ignored." not in page
    assert stat_values(page)[:2] == ["₹30.50", "2"]


def test_profile_empty_end_with_valid_start_applies_start_silently(logged_in):
    page = get_html(logged_in, "?start_date=2026-02-10&end_date=")
    assert "Invalid date ignored." not in page
    assert stat_values(page)[:2] == ["₹70.25", "2"]


def test_profile_reversed_range_shows_alert_and_empty_inputs(logged_in):
    page = get_html(logged_in, "?start_date=2026-03-01&end_date=2026-01-01")
    assert re.search(r'role="alert"[^>]*>\s*Start date must be on or before end date\.', page)
    assert input_value(page, "start_date") == ""
    assert input_value(page, "end_date") == ""


def test_profile_reversed_range_applies_no_filter_to_any_section(logged_in):
    page = get_html(logged_in, "?start_date=2026-03-01&end_date=2026-01-01")
    assert stat_values(page) == ["₹100.75", "4", "Food"]
    assert len(row_dates(page)) == 4
    assert sorted(category_names(page)) == ["Bills", "Food", "Transport"]
    assert "All recorded expenses" in page
    assert "Invalid date ignored." not in page


def test_profile_reversed_by_one_day_is_rejected(logged_in):
    page = get_html(logged_in, "?start_date=2026-02-11&end_date=2026-02-10")
    assert "Start date must be on or before end date." in page
    assert stat_values(page)[:2] == ["₹100.75", "4"]


def test_profile_valid_range_shows_no_error_message(logged_in):
    page = get_html(logged_in, "?start_date=2026-01-01&end_date=2026-01-31")
    assert "Invalid date ignored." not in page
    assert "Start date must be on or before end date." not in page
    assert 'role="alert"' not in page


# ------------------------------------------------------------------ #
# Template — filter bar                                               #
# ------------------------------------------------------------------ #

def test_filter_bar_sits_between_top_row_and_grid(logged_in):
    page = get_html(logged_in)
    top = page.index('class="profile-top"')
    form = page.index('<form class="filter-form"')
    grid = page.index('class="profile-grid"')
    assert top < form < grid
    for label in ("This month", "Last 30 days", "All time"):
        assert top < page.index(preset_tag(page, label)) < grid


def test_filter_form_is_get_to_profile_with_date_inputs(logged_in):
    page = get_html(logged_in)
    form = re.search(r'<form[^>]*class="filter-form"[^>]*>.*?</form>', page, re.S).group(0)
    assert 'method="get"' in form
    assert 'action="/profile"' in form
    assert re.search(r'<input type="date"[^>]*name="start_date"', form)
    assert re.search(r'<input type="date"[^>]*name="end_date"', form)
    assert re.search(r'<button type="submit"[^>]*>\s*Apply\s*</button>', form)
    assert re.search(r'<a href="/profile"[^>]*>\s*Clear\s*</a>', form)


def test_filter_inputs_empty_when_unfiltered(logged_in):
    page = get_html(logged_in)
    assert input_value(page, "start_date") == ""
    assert input_value(page, "end_date") == ""


def test_filter_start_only_prefills_start_and_leaves_end_empty(logged_in):
    page = get_html(logged_in, "?start_date=2026-02-10")
    assert input_value(page, "start_date") == "2026-02-10"
    assert input_value(page, "end_date") == ""


def test_this_month_preset_href_is_first_of_month_to_today(logged_in):
    today = date.today()
    href = preset_href(get_html(logged_in), "This month")
    assert href.startswith("/profile?")
    assert f"start_date={today.replace(day=1).isoformat()}" in href
    assert f"end_date={today.isoformat()}" in href


def test_last_30_days_preset_href_is_today_minus_29_to_today(logged_in):
    today = date.today()
    href = preset_href(get_html(logged_in), "Last 30 days")
    assert f"start_date={(today - timedelta(days=29)).isoformat()}" in href
    assert f"end_date={today.isoformat()}" in href


def test_all_time_preset_href_has_no_query_string(logged_in):
    assert preset_href(get_html(logged_in, "?end_date=2026-01-31"), "All time") == "/profile"


def test_active_all_time_preset_has_is_active_class(logged_in):
    page = get_html(logged_in)
    assert "is-active" in preset_tag(page, "All time")
    assert 'aria-current="true"' in preset_tag(page, "All time")
    assert "is-active" not in preset_tag(page, "This month")
    assert "is-active" not in preset_tag(page, "Last 30 days")


def test_active_this_month_preset_has_is_active_class(logged_in):
    today = date.today()
    page = get_html(logged_in, f"?start_date={today.replace(day=1).isoformat()}"
                               f"&end_date={today.isoformat()}")
    assert "is-active" in preset_tag(page, "This month")
    assert "is-active" not in preset_tag(page, "All time")


def test_custom_range_has_no_active_preset_class(logged_in):
    page = get_html(logged_in, "?start_date=2026-01-01&end_date=2026-01-31")
    for label in ("This month", "Last 30 days", "All time"):
        assert "is-active" not in preset_tag(page, label)


# ------------------------------------------------------------------ #
# Template — range hint and empty states                              #
# ------------------------------------------------------------------ #

def test_total_hint_uses_spec_example_format(logged_in):
    page = get_html(logged_in, "?start_date=2026-10-01&end_date=2026-10-09")
    assert "1 Oct 2026 – 9 Oct 2026" in page
    assert "All recorded expenses" not in page


def test_total_hint_open_ended_day_not_zero_padded(logged_in):
    assert "From 5 Jan 2026" in get_html(logged_in, "?start_date=2026-01-05")
    assert "Until 9 Oct 2026" in get_html(logged_in, "?end_date=2026-10-09")


def test_empty_range_shows_zero_count_and_dash_top_category(logged_in):
    page = get_html(logged_in, "?start_date=2027-01-01&end_date=2027-12-31")
    assert stat_values(page) == ["₹0.00", "0", "—"]
    assert row_dates(page) == []


def test_unfiltered_user_without_expenses_keeps_step5_empty_states(client, temp_db):
    uid = temp_db.create_user("Empty User", "empty@example.com", "password123")
    login_as(client, uid, "Empty User")
    page = get_html(client)
    assert "No expenses yet." in page
    assert "No expenses in this period." not in page
    assert "No spending in this period." not in page
    assert stat_values(page)[:2] == ["₹0.00", "0"]


def test_filtered_user_without_expenses_shows_period_empty_states(client, temp_db):
    uid = temp_db.create_user("Empty User", "empty@example.com", "password123")
    login_as(client, uid, "Empty User")
    page = get_html(client, "?start_date=2026-01-01")
    assert "No expenses in this period." in page
    assert "No spending in this period." in page
    assert "No expenses yet." not in page
