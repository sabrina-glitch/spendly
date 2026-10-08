import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "spendly.db")

CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL NOT NULL,
    category    TEXT NOT NULL,
    date        TEXT NOT NULL,
    description TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""

# (amount, category, day of current month, description)
SAMPLE_EXPENSES = (
    (12.50, "Food", 2, "Lunch at cafe"),
    (45.00, "Transport", 5, "Metro card top-up"),
    (120.75, "Bills", 8, "Electricity bill"),
    (30.00, "Health", 11, "Pharmacy"),
    (15.99, "Entertainment", 14, "Movie ticket"),
    (64.20, "Shopping", 18, "New shoes"),
    (38.40, "Food", 22, "Groceries"),
    (5.00, "Other", 26, None),
)


def get_db():
    """Return a connection with dict-like rows and foreign keys enforced.

    Callers must close it — `with conn:` only commits, it does not close.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables. Safe to call repeatedly."""
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    """Insert a demo user and sample expenses, only if no users exist yet."""
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        month_start = date.today().replace(day=1)
        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
            )
            user_id = cursor.lastrowid
            conn.executemany(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (user_id, amount, category,
                     month_start.replace(day=day).isoformat(), description)
                    for amount, category, day, description in SAMPLE_EXPENSES
                ],
            )
    finally:
        conn.close()


def get_user_by_email(email):
    """Return the user row for `email`, or None. Callers normalise the email."""
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


def create_user(name, email, password):
    """Insert a user with a hashed password and return its id.

    Returns None if the email is already registered.
    """
    password_hash = generate_password_hash(password)
    conn = get_db()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, password_hash),
            )
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()
