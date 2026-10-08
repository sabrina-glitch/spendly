import re
import sys
from pathlib import Path

import pytest

DEMO_NAME = "Demo User"
PROFILE_CSS = Path(__file__).resolve().parent.parent / "static" / "css" / "profile.css"


def login_as(client, user_id=1, name=DEMO_NAME):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = name


def get_profile_html(client, name=DEMO_NAME):
    login_as(client, name=name)
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


def test_profile_uses_session_name(client):
    html = get_profile_html(client, name="Alice Smith")
    assert "Alice Smith" in html
    assert ">AS<" in html


def test_profile_escapes_user_name(client):
    html = get_profile_html(client, name="<b>x</b>")
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
    assert "₹120.75" in html  # breakdown
    assert "₹38.40" in html   # recent transactions


def test_profile_missing_description_shows_dash(client):
    html = get_profile_html(client)
    tbody = html.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    assert "—" in tbody


def test_profile_breakdown_sorted_with_bars(client):
    html = get_profile_html(client)
    breakdown = html.split('class="cat-list"', 1)[1]
    assert breakdown.index("Bills") < breakdown.index("Other")
    assert 'style="width: 36.4%"' in html


def test_profile_empty_states(client, monkeypatch):
    app_module = sys.modules["app"]
    monkeypatch.setattr(app_module, "SAMPLE_RECENT_EXPENSES", [])
    monkeypatch.setattr(app_module, "SAMPLE_CATEGORY_BREAKDOWN", [])
    html = get_profile_html(client)
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


# ------------------------------------------------------------------ #
# Hardcoded data matches the seed                                     #
# ------------------------------------------------------------------ #

def test_sample_data_matches_seed(app):
    from database.db import CATEGORIES, SAMPLE_EXPENSES

    app_module = sys.modules["app"]
    stats = app_module.SAMPLE_STATS
    breakdown = app_module.SAMPLE_CATEGORY_BREAKDOWN
    total = round(sum(row[0] for row in SAMPLE_EXPENSES), 2)

    assert stats["total_spent"] == pytest.approx(total)
    assert stats["transaction_count"] == len(SAMPLE_EXPENSES)
    assert sum(c["amount"] for c in breakdown) == pytest.approx(total)
    assert [c["amount"] for c in breakdown] == sorted(
        (c["amount"] for c in breakdown), reverse=True
    )
    assert stats["top_category"] == breakdown[0]["name"]
    assert all(c["name"] in CATEGORIES for c in breakdown)
    assert all(e["category"] in CATEGORIES for e in app_module.SAMPLE_RECENT_EXPENSES)
