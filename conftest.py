import pytest

import database.db as db


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the data layer at a fresh temporary database with the schema created."""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    return db
