import sqlite3
from datetime import date

import pytest
from werkzeug.security import check_password_hash


def query(db, sql, params=()):
    conn = db.get_db()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def test_tables_exist(temp_db):
    rows = query(temp_db, "SELECT name FROM sqlite_master WHERE type = ?", ("table",))
    assert {"users", "expenses"} <= {row["name"] for row in rows}


def test_init_db_is_idempotent(temp_db):
    temp_db.init_db()
    temp_db.init_db()


def test_foreign_keys_enabled(temp_db):
    assert query(temp_db, "PRAGMA foreign_keys")[0][0] == 1


def test_seed_db_does_not_duplicate(temp_db):
    temp_db.seed_db()
    temp_db.seed_db()
    assert query(temp_db, "SELECT COUNT(*) FROM users")[0][0] == 1
    assert query(temp_db, "SELECT COUNT(*) FROM expenses")[0][0] == 8


def test_seed_expenses_cover_categories_in_current_month(temp_db):
    temp_db.seed_db()
    rows = query(temp_db, "SELECT category, date, amount FROM expenses")
    assert {row["category"] for row in rows} == set(temp_db.CATEGORIES)
    month_prefix = date.today().strftime("%Y-%m-")
    for row in rows:
        assert row["date"].startswith(month_prefix)
        date.fromisoformat(row["date"])
        assert isinstance(row["amount"], float)


def test_demo_user_password_is_hashed(temp_db):
    temp_db.seed_db()
    user = query(temp_db, "SELECT * FROM users WHERE email = ?", ("demo@spendly.com",))[0]
    assert user["name"] == "Demo User"
    assert user["password_hash"] != "demo123"
    assert check_password_hash(user["password_hash"], "demo123")


def test_duplicate_email_rejected(temp_db):
    temp_db.seed_db()
    conn = temp_db.get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Someone", "demo@spendly.com", "hash"),
            )
    finally:
        conn.close()


def test_expense_with_unknown_user_rejected(temp_db):
    conn = temp_db.get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                (9999, 1.0, "Food", "2026-01-01"),
            )
    finally:
        conn.close()


def test_rows_accessible_by_column_name(temp_db):
    temp_db.seed_db()
    row = query(temp_db, "SELECT id, email FROM users")[0]
    assert row["email"] == "demo@spendly.com"
    assert row["id"] == row[0]
