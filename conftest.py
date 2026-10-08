import pytest

import database.db as db


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the data layer at a fresh temporary database with the schema created."""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    return db


@pytest.fixture
def app(temp_db):
    """The Flask app, imported only after DB_PATH points at the temp database.

    Importing app.py runs init_db()/seed_db(), so never import it at module level here.
    """
    from app import app as flask_app

    flask_app.config.update(TESTING=True)
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
