import os
import calendar
from datetime import date, timedelta

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import (
    create_user,
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Date filter helpers (profile page)                                  #
# ------------------------------------------------------------------ #

INVALID_DATE_ERROR = "Invalid date ignored."
DATE_ORDER_ERROR = "Start date must be on or before end date."
SHORT_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def parse_date_param(value):
    """Return a date for a strict YYYY-MM-DD string, otherwise None."""
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    # Python 3.11+ also accepts "20261001", "2026-W40-4" etc. — require the exact form.
    return parsed if parsed.isoformat() == value else None


def read_date_filter(args):
    """Return (start, end, error) from the query string.

    - no / empty params  -> (None, None, None)
    - valid bounds       -> (start, end, None); either may be None
    - a malformed bound  -> that bound is None, error = INVALID_DATE_ERROR
    - start after end    -> (None, None, DATE_ORDER_ERROR), i.e. no filter
    """
    raw_start = args.get("start_date", "")
    raw_end = args.get("end_date", "")
    start, end = parse_date_param(raw_start), parse_date_param(raw_end)
    if (raw_start and start is None) or (raw_end and end is None):
        return start, end, INVALID_DATE_ERROR
    if start and end and start > end:
        return None, None, DATE_ORDER_ERROR
    return start, end, None


def format_day(d):
    """Format a date as "1 Oct 2026" (strftime's %-d is not portable to Windows)."""
    return f"{d.day} {SHORT_MONTHS[d.month - 1]} {d.year}"


def describe_range(start, end):
    """Return the label for the active range, shown under Total spent."""
    if start and end:
        return f"{format_day(start)} – {format_day(end)}"
    if start:
        return f"From {format_day(start)}"
    if end:
        return f"Until {format_day(end)}"
    return "All recorded expenses"


def months_ago(d, months):
    """Return the same day `months` calendar months earlier, clamped to month end."""
    total = d.year * 12 + (d.month - 1) - months
    year, month = divmod(total, 12)
    month += 1
    return d.replace(year=year, month=month,
                     day=min(d.day, calendar.monthrange(year, month)[1]))


def build_presets(today):
    """Return [(key, label, start)] for the quick ranges; each ends today."""
    return [
        ("this_month", "This month", today.replace(day=1)),
        ("last_30", "Last 30 days", today - timedelta(days=29)),
        ("last_3_months", "Last 3 months", months_ago(today, 3)),
        ("last_6_months", "Last 6 months", months_ago(today, 6)),
    ]


def build_filter_context(start, end, filter_error):
    """Return the filter-bar template values: inputs, presets, label and error."""
    today = date.today()
    presets = build_presets(today)

    # First match wins: on the 30th of a month "This month" and
    # "Last 30 days" cover the same range, so only one pill is active.
    if start is None and end is None:
        active_preset = "all"
    else:
        active_preset = next(
            (key for key, _, preset_start in presets
             if (start, end) == (preset_start, today)),
            None,
        )

    return {
        "start_date": start.isoformat() if start else "",
        "end_date": end.isoformat() if end else "",
        "is_filtered": bool(start or end),
        "range_label": describe_range(start, end),
        "active_preset": active_preset,
        "filter_error": filter_error,
        "today": today.isoformat(),
        "presets": [
            {"key": key, "label": label, "start_date": preset_start.isoformat()}
            for key, label, preset_start in presets
        ],
    }


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


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    start, end, filter_error = read_date_filter(request.args)
    start_iso = start.isoformat() if start else None
    end_iso = end.isoformat() if end else None

    # --- [1] Transaction history ---
    recent_expenses = get_recent_transactions(
        user_id, start_date=start_iso, end_date=end_iso
    )

    # --- [2] Summary stats ---
    stats = get_summary_stats(user_id, start_date=start_iso, end_date=end_iso)

    # --- [3] Category breakdown ---
    category_breakdown = get_category_breakdown(
        user_id, start_date=start_iso, end_date=end_iso
    )

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        recent_expenses=recent_expenses,
        category_breakdown=category_breakdown,
        **build_filter_context(start, end, filter_error),
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
