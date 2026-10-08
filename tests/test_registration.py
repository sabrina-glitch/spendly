import pytest
from werkzeug.security import check_password_hash

SUCCESS_MESSAGE = "Account created — please sign in."
DUPLICATE_ERROR = "An account with that email already exists."

VALID_FORM = {
    "name": "Alice",
    "email": "alice@example.com",
    "password": "password123",
    "confirm_password": "password123",
}


def count_users(db):
    conn = db.get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()


def post_register(client, **overrides):
    return client.post("/register", data={**VALID_FORM, **overrides})


# ------------------------------------------------------------------ #
# Helpers in database/db.py                                           #
# ------------------------------------------------------------------ #

def test_create_user_returns_id_and_hashes_password(temp_db):
    user_id = temp_db.create_user("Alice", "alice@example.com", "password123")

    assert isinstance(user_id, int)
    row = temp_db.get_user_by_email("alice@example.com")
    assert row["id"] == user_id
    assert row["password_hash"] != "password123"
    assert check_password_hash(row["password_hash"], "password123")


def test_create_user_duplicate_returns_none(temp_db):
    temp_db.create_user("Alice", "alice@example.com", "password123")

    assert temp_db.create_user("Other", "alice@example.com", "different1") is None
    assert count_users(temp_db) == 1


def test_get_user_by_email_unknown_returns_none(temp_db):
    assert temp_db.get_user_by_email("nobody@example.com") is None


def test_get_user_by_email_returns_row(temp_db):
    temp_db.create_user("Alice", "alice@example.com", "password123")

    row = temp_db.get_user_by_email("alice@example.com")
    assert row["name"] == "Alice"
    assert row["email"] == "alice@example.com"


# ------------------------------------------------------------------ #
# GET /register                                                       #
# ------------------------------------------------------------------ #

def test_get_register_renders_form(client):
    resp = client.get("/register")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert 'action="/register"' in html
    assert 'href="/terms"' in html
    assert 'href="/privacy"' in html


# ------------------------------------------------------------------ #
# POST /register — success                                            #
# ------------------------------------------------------------------ #

def test_register_success_redirects_to_login(client, temp_db):
    resp = post_register(client)

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")

    row = temp_db.get_user_by_email("alice@example.com")
    assert row is not None
    assert row["name"] == "Alice"
    assert check_password_hash(row["password_hash"], "password123")

    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_register_success_flash_shown_once(client):
    resp = client.post("/register", data=VALID_FORM, follow_redirects=True)
    html = resp.get_data(as_text=True)

    assert resp.request.path == "/login"
    assert SUCCESS_MESSAGE in html
    assert 'class="flash flash-success"' in html

    assert SUCCESS_MESSAGE not in client.get("/login").get_data(as_text=True)


def test_register_normalises_email_and_name(client, temp_db):
    post_register(client, name="  Alice  ", email="  Test@Example.com ")

    row = temp_db.get_user_by_email("test@example.com")
    assert row is not None
    assert row["name"] == "Alice"


# ------------------------------------------------------------------ #
# POST /register — duplicates                                         #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("email", ["demo@spendly.com", "DEMO@spendly.com"])
def test_register_duplicate_email(client, temp_db, email):
    temp_db.seed_db()
    before = count_users(temp_db)

    resp = post_register(client, email=email)

    assert resp.status_code == 200
    assert DUPLICATE_ERROR in resp.get_data(as_text=True)
    assert count_users(temp_db) == before


def test_register_race_returns_duplicate_error(client, temp_db, monkeypatch):
    monkeypatch.setattr("app.create_user", lambda *args: None)

    resp = post_register(client)

    assert resp.status_code == 200
    assert DUPLICATE_ERROR in resp.get_data(as_text=True)


# ------------------------------------------------------------------ #
# POST /register — validation                                         #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"name": ""}, "Please enter your name."),
        ({"name": "   "}, "Please enter your name."),
        ({"email": ""}, "Please enter a valid email address."),
        ({"email": "bob"}, "Please enter a valid email address."),
        ({"email": "bob@example"}, "Please enter a valid email address."),
        ({"email": "bob.example.com"}, "Please enter a valid email address."),
        ({"password": "1234567"}, "Password must be at least 8 characters."),
        ({"confirm_password": "s3cretpasX"}, "Passwords do not match."),
        ({"confirm_password": ""}, "Passwords do not match."),
    ],
)
def test_register_validation_errors(client, temp_db, overrides, message):
    before = count_users(temp_db)
    form = {
        **VALID_FORM,
        "password": "s3cretpass",
        "confirm_password": "s3cretpass",
        **overrides,
    }

    resp = client.post("/register", data=form)
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert message in html
    assert count_users(temp_db) == before
    if form["name"].strip():
        assert f'value="{form["name"]}"' in html
    if form["email"]:
        assert f'value="{form["email"]}"' in html
    assert form["password"] not in html
    if form["confirm_password"]:
        assert form["confirm_password"] not in html


def test_validation_order_reports_name_first(client):
    resp = client.post(
        "/register", data={"name": "", "email": "bad", "password": "short"}
    )
    html = resp.get_data(as_text=True)

    assert "Please enter your name." in html
    assert "Please enter a valid email address." not in html
    assert "Password must be at least 8 characters." not in html


# ------------------------------------------------------------------ #
# Stub routes stay untouched                                          #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "path, text",
    [
        ("/logout", "coming in Step 3"),
        ("/profile", "coming in Step 4"),
        ("/expenses/add", "coming in Step 7"),
        ("/expenses/1/edit", "coming in Step 8"),
        ("/expenses/1/delete", "coming in Step 9"),
    ],
)
def test_stub_routes_unchanged(client, path, text):
    assert text in client.get(path).get_data(as_text=True)
