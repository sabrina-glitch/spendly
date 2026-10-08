import os

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_user_by_email, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


DUPLICATE_EMAIL_ERROR = "An account with that email already exists."


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    _, at, domain = email.partition("@")
    if not name:
        error = "Please enter your name."
    elif not at or "." not in domain:
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    elif password != confirm_password:
        error = "Passwords do not match."
    elif get_user_by_email(email) is not None:
        error = DUPLICATE_EMAIL_ERROR
    elif create_user(name, email, password) is None:
        error = DUPLICATE_EMAIL_ERROR
    else:
        error = None

    if error:
        return render_template("register.html", error=error, name=name, email=email)

    flash("Account created — please sign in.", "success")
    return redirect(url_for("login"))


LOGIN_ERROR = "Invalid email or password."


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("profile"))
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email) if email and password else None
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error=LOGIN_ERROR, email=email)

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("landing"))


# Hardcoded profile data — Step 5 replaces these with DB queries.
# Derived from SAMPLE_EXPENSES in database/db.py (total 331.84).
SAMPLE_PROFILE = {
    "email": "demo@spendly.com",
    "member_since": "October 2026",
}

SAMPLE_STATS = {
    "total_spent": 331.84,
    "transaction_count": 8,
    "top_category": "Bills",
}

SAMPLE_RECENT_EXPENSES = [
    {"date": "2026-10-26", "description": None, "category": "Other", "amount": 5.00},
    {"date": "2026-10-22", "description": "Groceries", "category": "Food", "amount": 38.40},
    {"date": "2026-10-18", "description": "New shoes", "category": "Shopping", "amount": 64.20},
    {"date": "2026-10-14", "description": "Movie ticket", "category": "Entertainment", "amount": 15.99},
    {"date": "2026-10-11", "description": "Pharmacy", "category": "Health", "amount": 30.00},
]

SAMPLE_CATEGORY_BREAKDOWN = [
    {"name": "Bills", "amount": 120.75, "pct": 36.4},
    {"name": "Shopping", "amount": 64.20, "pct": 19.3},
    {"name": "Food", "amount": 50.90, "pct": 15.3},
    {"name": "Transport", "amount": 45.00, "pct": 13.6},
    {"name": "Health", "amount": 30.00, "pct": 9.0},
    {"name": "Entertainment", "amount": 15.99, "pct": 4.8},
    {"name": "Other", "amount": 5.00, "pct": 1.5},
]


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {"name": session.get("user_name", ""), **SAMPLE_PROFILE}
    return render_template(
        "profile.html",
        user=user,
        stats=SAMPLE_STATS,
        recent_expenses=SAMPLE_RECENT_EXPENSES,
        category_breakdown=SAMPLE_CATEGORY_BREAKDOWN,
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
