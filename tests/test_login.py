import pytest

WELCOME_MESSAGE = "Welcome back, Demo User!"
SIGNED_OUT_MESSAGE = "You have been signed out."
LOGIN_ERROR = "Invalid email or password."

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo123"


@pytest.fixture
def demo_user(temp_db):
    """Seed the demo user — app.py only seeds on its first import, not per test."""
    temp_db.seed_db()
    return temp_db.get_user_by_email(DEMO_EMAIL)


def post_login(client, email=DEMO_EMAIL, password=DEMO_PASSWORD, **kwargs):
    return client.post(
        "/login", data={"email": email, "password": password}, **kwargs
    )


def post_register(client, name, email, password):
    return client.post("/register", data={
        "name": name,
        "email": email,
        "password": password,
        "confirm_password": password,
    })


def login_as(client, user_id=1, name="Demo User"):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_name"] = name


# ------------------------------------------------------------------ #
# GET /login                                                          #
# ------------------------------------------------------------------ #

def test_get_login_renders_form(client):
    resp = client.get("/login")

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'action="/login"' in html
    assert 'value=""' in html


def test_get_login_redirects_when_signed_in(client):
    login_as(client)

    resp = client.get("/login")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


@pytest.mark.parametrize("method", ["get", "post"])
def test_register_redirects_when_signed_in(client, temp_db, method):
    login_as(client)

    resp = getattr(client, method)("/register", data={
        "name": "Alice",
        "email": "alice@example.com",
        "password": "password123",
        "confirm_password": "password123",
    })

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")
    assert temp_db.get_user_by_email("alice@example.com") is None


# ------------------------------------------------------------------ #
# POST /login — success                                              #
# ------------------------------------------------------------------ #

def test_login_success_sets_session(client, demo_user):
    resp = post_login(client)

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert sess["user_id"] == demo_user["id"]
        assert sess["user_name"] == "Demo User"
        assert "email" not in sess
        assert "password_hash" not in sess


def test_login_success_flash_shown_once(client, demo_user):
    resp = post_login(client, follow_redirects=True)

    assert resp.request.path == "/"
    assert WELCOME_MESSAGE in resp.get_data(as_text=True)
    assert WELCOME_MESSAGE not in client.get("/").get_data(as_text=True)


@pytest.mark.parametrize("email", [" DEMO@Spendly.com ", "Demo@SPENDLY.com"])
def test_login_normalises_email(client, demo_user, email):
    resp = post_login(client, email=email)

    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user_id"] == demo_user["id"]


def test_registered_user_can_login(client, temp_db):
    post_register(client, "Alice", "alice@example.com", "password123")

    resp = post_login(client, email="alice@example.com", password="password123")

    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["user_name"] == "Alice"


# ------------------------------------------------------------------ #
# POST /login — failures                                              #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "email, password, expected_email",
    [
        (DEMO_EMAIL, "wrong-password", DEMO_EMAIL),
        ("nobody@example.com", DEMO_PASSWORD, "nobody@example.com"),
        ("", DEMO_PASSWORD, ""),
        (DEMO_EMAIL, "", DEMO_EMAIL),
        ("", "", ""),
        ("   ", DEMO_PASSWORD, ""),
    ],
)
def test_login_failures_show_generic_error(
    client, demo_user, email, password, expected_email
):
    resp = post_login(client, email=email, password=password)

    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert LOGIN_ERROR in html
    assert f'value="{expected_email}"' in html
    if password:
        assert password not in html
    with client.session_transaction() as sess:
        assert "user_id" not in sess


# ------------------------------------------------------------------ #
# /logout                                                             #
# ------------------------------------------------------------------ #

def test_logout_clears_session(client):
    login_as(client)

    resp = client.get("/logout")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "user_name" not in sess


def test_logout_shows_flash(client):
    login_as(client)

    resp = client.get("/logout", follow_redirects=True)

    assert resp.request.path == "/"
    assert SIGNED_OUT_MESSAGE in resp.get_data(as_text=True)


def test_logout_when_signed_out(client):
    resp = client.get("/logout")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


# ------------------------------------------------------------------ #
# Navbar                                                              #
# ------------------------------------------------------------------ #

def test_navbar_signed_out(client):
    html = client.get("/").get_data(as_text=True)

    assert 'href="/login"' in html
    assert "Get started" in html
    assert "Sign out" not in html
    assert 'class="nav-user"' not in html


def test_navbar_signed_in(client):
    login_as(client)

    html = client.get("/").get_data(as_text=True)

    assert 'class="nav-user">Demo User<' in html
    assert 'href="/logout"' in html
    assert "Sign out" in html
    assert 'href="/login"' not in html


def test_navbar_escapes_user_name(client):
    login_as(client, name="<b>x</b>")

    html = client.get("/").get_data(as_text=True)

    assert "&lt;b&gt;x&lt;/b&gt;" in html
    assert "<b>x</b>" not in html
