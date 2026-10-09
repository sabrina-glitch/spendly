import re
from pathlib import Path

import pytest

DEMO_NAME = "Demo User"
PROFILE_CSS = Path(__file__).resolve().parent.parent / "static" / "css" / "profile.css"


@pytest.fixture(autouse=True)
def seeded(temp_db):
    """The profile page reads real data, so the demo user (id 1) must exist."""
    temp_db.seed_db()


def login_as(client, user_id=1, name=DEMO_NAME):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = name


def get_profile_html(client, user_id=1, name=DEMO_NAME):
    login_as(client, user_id=user_id, name=name)
    resp = client.get("/profile")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


# ------------------------------------------------------------------ #
# Access control                                                      #
# ------------------------------------------------------------------ #

def test_profile_redirects_when_signed_out(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")

    resp = client.get("/profile", follow_redirects=True)
    assert resp.request.path == "/login"


# ------------------------------------------------------------------ #
# User info card                                                      #
# ------------------------------------------------------------------ #

def test_profile_renders_for_signed_in_user(client):
    html = get_profile_html(client)
    assert DEMO_NAME in html
    assert ">DU<" in html
    assert "Member since" in html
    assert "demo@spendly.com" in html


def test_profile_uses_database_name(client, temp_db):
    user_id = temp_db.create_user("Alice Smith", "alice@example.com", "password123")
    html = get_profile_html(client, user_id=user_id, name="Stale Session Name")
    assert 'id="profile-name" class="profile-name">Alice Smith<' in html
    assert ">AS<" in html


def test_profile_escapes_user_name(client, temp_db):
    user_id = temp_db.create_user("<b>x</b>", "x@example.com", "password123")
    html = get_profile_html(client, user_id=user_id, name="<b>x</b>")
    assert "&lt;b&gt;x&lt;/b&gt;" in html
    assert "<b>x</b>" not in html


# ------------------------------------------------------------------ #
# Sections                                                            #
# ------------------------------------------------------------------ #

def test_profile_section_headings(client):
    html = get_profile_html(client)
    assert 'id="profile-name"' in html
    assert "Summary" in html
    assert "Recent transactions" in html
    assert "Spending by category" in html


def test_profile_stat_cards(client):
    html = get_profile_html(client)
    for label in ("Total spent", "Transactions", "Top category"):
        assert label in html
    assert "₹331.84" in html
    assert "Bills" in html


def test_profile_renders_rupee_amounts(client):
    html = get_profile_html(client)
    assert "₹120.75" in html  # Bills
    assert "₹38.40" in html   # Groceries


def test_profile_missing_description_shows_dash(client):
    html = get_profile_html(client)
    tbody = html.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    assert "—" in tbody


def test_profile_breakdown_sorted_with_bars(client):
    html = get_profile_html(client)
    breakdown = html.split('class="cat-list"', 1)[1]
    assert breakdown.index("Bills") < breakdown.index("Other")
    assert 'style="width: 36%"' in html


def test_profile_empty_states(client, temp_db):
    user_id = temp_db.create_user("New User", "new@example.com", "password123")
    html = get_profile_html(client, user_id=user_id, name="New User")
    assert "₹0.00" in html
    assert "None recorded yet" in html
    assert "No expenses yet." in html
    assert "No spending to break down yet." in html


# ------------------------------------------------------------------ #
# Styles and navbar                                                   #
# ------------------------------------------------------------------ #

def test_profile_css_only_on_profile_page(client):
    html = get_profile_html(client)
    assert "css/profile.css" in html
    assert "<style" not in html
    assert "css/profile.css" not in client.get("/").get_data(as_text=True)


def test_navbar_links_to_profile(client):
    signed_out = client.get("/").get_data(as_text=True)
    assert 'href="/profile"' not in signed_out

    login_as(client)
    html = client.get("/").get_data(as_text=True)
    assert 'href="/profile"' in html
    assert 'class="nav-user">Demo User<' in html


def test_profile_css_has_no_hex_colours():
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", PROFILE_CSS.read_text(encoding="utf-8"))
