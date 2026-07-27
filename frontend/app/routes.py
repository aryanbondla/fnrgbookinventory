"""
Routes for FNRG Preaching.

Pages (all except login/logout require a session; admin-only pages also
check role):
    GET  /                 sign-in page
    POST /login
    GET  /logout

    GET  /dashboard         personal (or org-wide, for admins) overview
    GET  /sell               book sell-entry form + recent entries
    POST /sell
    GET  /analytics          admin-only profit/loss analytics with filters
    GET  /upload              excel upload form
    POST /upload
    GET  /users                admin-only user management
    POST /users
    POST /users/<username>/toggle
"""

from functools import wraps
from io import BytesIO

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash
)
from openpyxl import load_workbook

from . import dummy_data as data

main_bp = Blueprint("main", __name__)


# --------------------------------------------------------------------- #
# Auth helpers
# --------------------------------------------------------------------- #
def current_user():
    username = session.get("username")
    if not username:
        return None
    return next((u for u in data.USERS if u["username"] == username), None)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("main.index"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("main.index"))
        if user["role"] != "admin":
            flash("That page is only available to admins.")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)
    return wrapped


@main_bp.context_processor
def inject_user():
    return {"current_user": current_user()}


# --------------------------------------------------------------------- #
# Auth routes
# --------------------------------------------------------------------- #
@main_bp.route("/", methods=["GET"])
def index():
    if current_user():
        return redirect(url_for("main.dashboard"))
    return render_template("login.html")


@main_bp.route("/login", methods=["POST"])
def login():
    """
    Demo auth: any known, active username in dummy_data.USERS signs in with
    any non-empty password. Usernames not already in USERS auto-register as
    a regular ("user") role so the flow is runnable end-to-end without a DB.
    Replace with real credential verification before this goes anywhere
    real (see README).
    """
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Please enter both a user name and password.")
        return redirect(url_for("main.index"))

    user = next((u for u in data.USERS if u["username"] == username), None)
    if user is None:
        user = {"username": username, "name": username.title(), "role": "user", "active": True}
        data.USERS.append(user)

    if not user["active"]:
        flash("That account has been deactivated. Contact an admin.")
        return redirect(url_for("main.index"))

    session["username"] = user["username"]
    return redirect(url_for("main.dashboard"))


@main_bp.route("/logout", methods=["GET"])
def logout():
    session.pop("username", None)
    return redirect(url_for("main.index"))


# --------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------- #
@main_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    user = current_user()
    is_admin = user["role"] == "admin"

    date_from, date_to = an.last_n_days_range(30)
    scope_rows = data.SALES if is_admin else an.filter_sales(data.SALES, seller=user["username"])
    recent_rows = an.filter_sales(scope_rows, date_from=date_from, date_to=date_to)

    kpis = an.summary(recent_rows)
    trend = an.revenue_profit_by_day(recent_rows)
    top_cats = an.qty_by_category(recent_rows)
    leaderboard = an.leaderboard_by_seller(scope_rows)[:5] if is_admin else None
    my_top_books = an.top_books(an.filter_sales(data.SALES, seller=user["username"]))

    # Inventory reflects the whole physical stock, so it always uses the
    # full (unfiltered, all-time) sales history — not the 30-day window.
    inventory = an.inventory_snapshot(data.SALES, data.INITIAL_STOCK, data.BOOKS)
    total_available = sum(r["available"] for r in inventory)

    return render_template(
        "home.html",
        is_admin=is_admin,
        kpis=kpis,
        trend=trend,
        top_cats=top_cats,
        leaderboard=leaderboard,
        my_top_books=my_top_books,
        inventory=inventory,
        total_available=total_available,
        window_label="last 30 days",
    )


# --------------------------------------------------------------------- #
# Sell entry
# --------------------------------------------------------------------- #
@main_bp.route("/sell", methods=["GET", "POST"])
@login_required
def sell_entry():
    user = current_user()

    if request.method == "POST":
        try:
            row = {
                "id": data.next_sale_id(),
                "date": request.form.get("date") or "",
                "title": request.form.get("title", "").strip(),
                "category": request.form.get("category", "").strip(),
                "seller": user["username"],
                "qty": int(request.form.get("qty", 0)),
                "cost_price": float(request.form.get("cost_price", 0)),
                "sell_price": float(request.form.get("sell_price", 0)),
            }
            if not row["title"] or not row["date"] or row["qty"] <= 0:
                raise ValueError("missing required fields")
            data.SALES.insert(0, row)
            flash(f"Recorded sale of {row['qty']} x \"{row['title']}\".", "success")
        except (TypeError, ValueError):
            flash("Please fill in every field with valid values.", "error")

        return redirect(url_for("main.sell_entry"))

    my_sales = an.filter_sales(data.SALES, seller=user["username"])[:15]
    return render_template(
        "sell_entry.html",
        book_titles=[t for t, _ in data.BOOKS],
        categories=data.CATEGORIES,
        my_sales=my_sales,
    )


# --------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------- #
EXPECTED_COLUMNS = ["date", "title", "category", "seller", "qty", "cost_price", "sell_price"]


@main_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Choose an .xlsx file first.", "error")
            return redirect(url_for("main.upload"))

        if not file.filename.lower().endswith((".xlsx", ".xlsm")):
            flash("Only .xlsx files are supported right now.", "error")
            return redirect(url_for("main.upload"))

        try:
            wb = load_workbook(filename=BytesIO(file.read()), data_only=True)
            ws = wb.active
            header = [str(c.value).strip().lower() if c.value else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]

            col_index = {}
            for col in EXPECTED_COLUMNS:
                if col not in header:
                    raise ValueError(f"Missing expected column: '{col}'")
                col_index[col] = header.index(col)

            added = 0
            errors = 0
            for row_cells in ws.iter_rows(min_row=2):
                values = [c.value for c in row_cells]
                if all(v in (None, "") for v in values):
                    continue
                try:
                    new_row = {
                        "id": data.next_sale_id(),
                        "date": str(values[col_index["date"]])[:10],
                        "title": str(values[col_index["title"]]).strip(),
                        "category": str(values[col_index["category"]]).strip(),
                        "seller": str(values[col_index["seller"]]).strip().lower(),
                        "qty": int(values[col_index["qty"]]),
                        "cost_price": float(values[col_index["cost_price"]]),
                        "sell_price": float(values[col_index["sell_price"]]),
                    }
                    data.SALES.insert(0, new_row)
                    added += 1
                except (TypeError, ValueError):
                    errors += 1

            if added:
                msg = f"Imported {added} row{'s' if added != 1 else ''} successfully."
                if errors:
                    msg += f" Skipped {errors} row(s) with invalid data."
                flash(msg, "success")
            else:
                flash("No valid rows found in that file.", "error")

        except Exception as exc:
            flash(f"Could not read that file: {exc}", "error")

        return redirect(url_for("main.upload"))

    return render_template("upload.html", expected_columns=EXPECTED_COLUMNS)


@main_bp.route("/upload/sample", methods=["GET"])
@login_required
def upload_sample():
    """Serve a tiny sample workbook so users know the expected format."""
    from openpyxl import Workbook
    from flask import send_file

    wb = Workbook()
    ws = wb.active
    ws.append(EXPECTED_COLUMNS)
    ws.append(["2026-07-01", "Bhagavad Gita As It Is", "Philosophy", "arjun", 3, 100, 130])
    ws.append(["2026-07-02", "Krishna Book", "Storytelling", "priya", 2, 120, 150])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name="sample_sales_upload.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# --------------------------------------------------------------------- #
# User management (admin)
# --------------------------------------------------------------------- #
@main_bp.route("/users", methods=["GET", "POST"])
@admin_required
def user_management():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "user")

        if not username or not name:
            flash("Name and username are required.", "error")
        elif not data.next_username_available(username):
            flash(f"Username '{username}' is already taken.", "error")
        else:
            data.USERS.append({"username": username, "name": name, "role": role, "active": True})
            flash(f"Added {name} ({username}) as {role}.", "success")

        return redirect(url_for("main.user_management"))

    return render_template("user_management.html", users=data.USERS)


@main_bp.route("/users/<username>/toggle", methods=["POST"])
@admin_required
def toggle_user(username):
    user = next((u for u in data.USERS if u["username"] == username), None)
    if user:
        if user["username"] == current_user()["username"]:
            flash("You can't deactivate your own account.", "error")
        else:
            user["active"] = not user["active"]
            flash(f"{user['name']} is now {'active' if user['active'] else 'inactive'}.", "success")
    return redirect(url_for("main.user_management"))
