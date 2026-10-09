import os
import sqlite3
from datetime import date, datetime

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


# ------------------------------------------------------------------ #
# Profile page queries                                                #
# ------------------------------------------------------------------ #

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def get_user_by_id(user_id):
    """Return {name, email, member_since} for the user, or None if missing."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    member_since = ""
    if row["created_at"]:
        try:
            joined = datetime.strptime(row["created_at"][:10], "%Y-%m-%d")
            member_since = f"{MONTH_NAMES[joined.month - 1]} {joined.year}"
        except ValueError:
            pass

    return {"name": row["name"], "email": row["email"], "member_since": member_since}


def _date_range_clause(start_date, end_date):
    """Return (sql, params) narrowing `expenses.date` to inclusive ISO bounds.

    Only the fixed literals below are concatenated into SQL; the bounds
    themselves are always bound as `?` parameters. A None bound is skipped.
    """
    sql, params = "", []
    if start_date is not None:
        sql += " AND date >= ?"
        params.append(start_date)
    if end_date is not None:
        sql += " AND date <= ?"
        params.append(end_date)
    return sql, params


# --- [1] Transaction history --- #

def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    """Return the user's newest expenses as dicts: date, description, category, amount.

    `start_date` / `end_date` are optional inclusive ISO (YYYY-MM-DD) bounds.
    """
    range_sql, range_params = _date_range_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ?"
            + range_sql
            + " ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, *range_params, limit),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "date": r["date"],
            "description": r["description"],
            "category": r["category"],
            "amount": round(r["amount"], 2),
        }
        for r in rows
    ]


# --- [2] Summary stats --- #

def get_summary_stats(user_id, start_date=None, end_date=None):
    """Return {total_spent, transaction_count, top_category} for the user.

    `start_date` / `end_date` are optional inclusive ISO (YYYY-MM-DD) bounds.
    """
    range_sql, range_params = _date_range_clause(start_date, end_date)
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS n "
            "FROM expenses WHERE user_id = ?"
            + range_sql,
            (user_id, *range_params),
        ).fetchone()
        top_row = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ?"
            + range_sql
            + " GROUP BY category"
            " ORDER BY ROUND(SUM(amount), 2) DESC, category ASC LIMIT 1",
            (user_id, *range_params),
        ).fetchone()
    finally:
        conn.close()
    return {
        "total_spent": round(totals["total"], 2),
        "transaction_count": totals["n"],
        "top_category": top_row["category"] if top_row else "—",
    }


# --- [3] Category breakdown --- #

def get_category_breakdown(user_id, start_date=None, end_date=None):
    """Return [{name, amount, pct}] sorted by amount desc; integer pcts sum to 100.

    `start_date` / `end_date` are optional inclusive ISO (YYYY-MM-DD) bounds.
    """
    range_sql, range_params = _date_range_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, ROUND(SUM(amount), 2) AS total FROM expenses "
            "WHERE user_id = ?"
            + range_sql
            + " GROUP BY category"
            " ORDER BY ROUND(SUM(amount), 2) DESC, category ASC",
            (user_id, *range_params),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    amounts = [round(r["total"], 2) for r in rows]
    grand = sum(amounts)
    if grand <= 0:
        return [
            {"name": r["category"], "amount": a, "pct": 0}
            for r, a in zip(rows, amounts)
        ]

    pcts = [round(a / grand * 100) for a in amounts]
    pcts[0] += 100 - sum(pcts)
    return [
        {"name": r["category"], "amount": a, "pct": p}
        for r, a, p in zip(rows, amounts, pcts)
    ]
