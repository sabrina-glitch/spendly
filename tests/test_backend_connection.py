import pytest

DEMO_EMAIL = "demo@spendly.com"


@pytest.fixture
def seeded_user(temp_db):
    """Seed the demo user and its sample expenses; return the demo user's id."""
    temp_db.seed_db()
    return temp_db.get_user_by_email(DEMO_EMAIL)["id"]


@pytest.fixture
def empty_user(temp_db):
    """A registered user with no expenses; return its id."""
    return temp_db.create_user("Empty User", "empty@example.com", "password123")


def add_expense(db, user_id, amount, category, date, description=None):
    conn = db.get_db()
    try:
        with conn:
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, date, description),
            )
    finally:
        conn.close()


def login_as(client, user_id, name="Demo User"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = name


# ------------------------------------------------------------------ #
# get_user_by_id                                                      #
# ------------------------------------------------------------------ #

def test_get_user_by_id_returns_profile_fields(temp_db, seeded_user):
    user = temp_db.get_user_by_id(seeded_user)
    assert user["name"] == "Demo User"
    assert user["email"] == DEMO_EMAIL
    month, year = user["member_since"].split()
    assert month in temp_db.MONTH_NAMES
    assert year.isdigit() and len(year) == 4
    assert "password_hash" not in user


def test_get_user_by_id_unknown_returns_none(temp_db):
    assert temp_db.get_user_by_id(999) is None


# ------------------------------------------------------------------ #
# [1] Transaction history                                             #
# ------------------------------------------------------------------ #

def test_recent_transactions_seeded_user(temp_db, seeded_user):
    rows = temp_db.get_recent_transactions(seeded_user)
    assert len(rows) == 8
    for row in rows:
        assert set(row.keys()) == {"date", "description", "category", "amount"}
    dates = [row["date"] for row in rows]
    assert dates == sorted(dates, reverse=True)
    assert sum(1 for row in rows if row["description"] is None) == 1


def test_recent_transactions_limit_respected(temp_db, seeded_user):
    full = temp_db.get_recent_transactions(seeded_user)
    limited = temp_db.get_recent_transactions(seeded_user, limit=3)
    assert len(limited) == 3
    assert limited == full[:3]


def test_recent_transactions_same_date_newest_insert_first(temp_db, empty_user):
    add_expense(temp_db, empty_user, 10.0, "Food", "2026-01-05", "A")
    add_expense(temp_db, empty_user, 20.0, "Food", "2026-01-05", "B")
    rows = temp_db.get_recent_transactions(empty_user)
    assert [row["description"] for row in rows] == ["B", "A"]


def test_recent_transactions_empty_user(temp_db, empty_user):
    assert temp_db.get_recent_transactions(empty_user) == []


def test_recent_transactions_isolated_per_user(temp_db, seeded_user, empty_user):
    add_expense(temp_db, empty_user, 99.99, "Other", "2026-01-05", "Not demo's")
    seeded_rows = temp_db.get_recent_transactions(seeded_user)
    assert all(row["description"] != "Not demo's" for row in seeded_rows)
    empty_rows = temp_db.get_recent_transactions(empty_user)
    assert len(empty_rows) == 1
    assert empty_rows[0]["description"] == "Not demo's"


# ------------------------------------------------------------------ #
# [2] Summary stats                                                   #
# ------------------------------------------------------------------ #

def test_summary_stats_seeded_user(temp_db, seeded_user):
    stats = temp_db.get_summary_stats(seeded_user)
    expected_total = round(sum(e[0] for e in temp_db.SAMPLE_EXPENSES), 2)
    assert stats["total_spent"] == pytest.approx(expected_total)
    assert stats["total_spent"] == 331.84
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_summary_stats_empty_user(temp_db, empty_user):
    stats = temp_db.get_summary_stats(empty_user)
    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}


def test_summary_stats_total_is_rounded(temp_db, empty_user):
    add_expense(temp_db, empty_user, 0.1, "Food", "2026-01-01")
    add_expense(temp_db, empty_user, 0.2, "Food", "2026-01-02")
    assert temp_db.get_summary_stats(empty_user)["total_spent"] == 0.3


def test_summary_stats_top_category_tie_breaks_alphabetically(temp_db, empty_user):
    add_expense(temp_db, empty_user, 10.00, "Food", "2026-01-01")
    add_expense(temp_db, empty_user, 10.00, "Bills", "2026-01-02")
    assert temp_db.get_summary_stats(empty_user)["top_category"] == "Bills"


def test_summary_stats_isolated_per_user(temp_db, seeded_user, empty_user):
    before = temp_db.get_summary_stats(seeded_user)
    add_expense(temp_db, empty_user, 999.99, "Shopping", "2026-01-01")
    assert temp_db.get_summary_stats(seeded_user) == before


# ------------------------------------------------------------------ #
# [3] Category breakdown                                              #
# ------------------------------------------------------------------ #

def test_category_breakdown_seeded_user(temp_db, seeded_user):
    breakdown = temp_db.get_category_breakdown(seeded_user)
    assert len(breakdown) == 7
    assert sorted(c["name"] for c in breakdown) == sorted(temp_db.CATEGORIES)
    amounts = [c["amount"] for c in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    assert breakdown[0]["name"] == "Bills"
    assert breakdown[0]["amount"] == 120.75
    assert breakdown[0]["pct"] == 36
    food = next(c for c in breakdown if c["name"] == "Food")
    assert food["amount"] == 50.90


def test_category_breakdown_pcts_are_ints_summing_to_100(temp_db, seeded_user):
    breakdown = temp_db.get_category_breakdown(seeded_user)
    pcts = [c["pct"] for c in breakdown]
    assert all(isinstance(p, int) for p in pcts)
    assert sum(pcts) == 100
    assert pcts == [36, 19, 15, 14, 9, 5, 2]


def test_category_breakdown_remainder_goes_to_largest(temp_db, empty_user):
    for category in ("Food", "Health", "Other"):
        add_expense(temp_db, empty_user, 1.00, category, "2026-01-01")
    breakdown = temp_db.get_category_breakdown(empty_user)
    assert [c["pct"] for c in breakdown] == [34, 33, 33]
    assert sum(c["pct"] for c in breakdown) == 100
    assert breakdown[0]["name"] == "Food"


def test_category_breakdown_empty_user(temp_db, empty_user):
    assert temp_db.get_category_breakdown(empty_user) == []


def test_category_breakdown_isolated_per_user(temp_db, seeded_user, empty_user):
    add_expense(temp_db, empty_user, 999.99, "Food", "2026-01-01", "Not mine")
    breakdown = temp_db.get_category_breakdown(seeded_user)
    food = next(c for c in breakdown if c["name"] == "Food")
    assert food["amount"] == 50.90
    assert all(c["amount"] != 999.99 for c in breakdown)
    assert sum(c["pct"] for c in breakdown) == 100


# ------------------------------------------------------------------ #
# GET /profile                                                        #
# ------------------------------------------------------------------ #

def test_profile_route_redirects_when_signed_out(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_profile_route_stale_session_is_cleared(client, temp_db):
    login_as(client, 999)
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_profile_route_seeded_user(client, temp_db, seeded_user):
    login_as(client, seeded_user)
    resp = client.get("/profile")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    assert "Demo User" in html
    assert DEMO_EMAIL in html
    assert "₹331.84" in html
    assert '<p class="stat-value">8</p>' in html
    assert '<p class="stat-value">Bills</p>' in html

    tbody = html.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    dates = [r["date"] for r in temp_db.get_recent_transactions(seeded_user)]
    assert tbody.count("<tr>") == 8
    positions = [tbody.index(f'datetime="{d}"') for d in dict.fromkeys(dates)]
    assert positions == sorted(positions)

    breakdown = html.split('class="cat-list"', 1)[1]
    for category in temp_db.CATEGORIES:
        assert f"cat-bar cat--{category.lower()}" in breakdown
    assert 'style="width: 36%"' in html


def test_profile_route_empty_user(client, empty_user):
    login_as(client, empty_user, name="Empty User")
    html = client.get("/profile").get_data(as_text=True)
    assert "₹0.00" in html
    assert '<p class="stat-value">0</p>' in html
    assert "No expenses yet." in html
    assert "No spending to break down yet." in html
