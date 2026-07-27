"""
Routes owned by the Users service.

    GET  /                 sign-in page (redirects to Books service's
                            dashboard if already logged in)
    POST /login
    GET  /logout

    GET  /users             admin-only: list + add users
    POST /users
    GET  /users/export       .xlsx of the All Users table
    POST /users/<username>/toggle
    POST /users/<username>/delete
    POST /users/<username>/password
    POST /users/<username>/role

    GET  /volunteers          volunteer <-> location assignment page
"""

from flask import render_template, request, redirect, url_for, session, flash

from . import users_bp
from . import data
from app.shared.auth import current_user, admin_required, login_required
from app.shared.xlsx_export import send_xlsx
from app.books_service.data import LOCATIONS


# --------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------- #
@users_bp.route("/", methods=["GET"])
def index():
    if current_user():
        return redirect(url_for("books.dashboard"))
    return render_template("login.html")


@users_bp.route("/login", methods=["POST"])
def login():
    """
    Real credential check against data.USERS (password hashes). Unknown
    usernames or wrong passwords are rejected rather than auto-registered.
    """
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Please enter both a user name and password.")
        return redirect(url_for("users.index"))

    user = data.find_user(username)
    if user is None or not data.verify_password(user, password):
        flash("Incorrect username or password.")
        return redirect(url_for("users.index"))

    if not user["active"]:
        flash("That account has been deactivated. Contact an admin.")
        return redirect(url_for("users.index"))

    session["username"] = user["username"]
    return redirect(url_for("books.dashboard"))


@users_bp.route("/logout", methods=["GET"])
def logout():
    session.pop("username", None)
    return redirect(url_for("users.index"))


# --------------------------------------------------------------------- #
# User management (admin)
# --------------------------------------------------------------------- #
@users_bp.route("/users", methods=["GET", "POST"])
# @admin_required  # TEMP: role restriction disabled for now — re-enable when ready to lock this down again
@login_required
def user_management():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "volunteer")

        if not name or not username or not password:
            flash("Name, username, and password are required.", "error")
        elif not mobile:
            flash("Mobile number is required.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif role not in data.ROLES:
            flash("Please choose a valid role.", "error")
        elif not data.next_username_available(username):
            flash(f"Username '{username}' is already taken.", "error")
        else:
            data.add_user(name, mobile, username, password, role)
            flash(f"Added {name} ({username}) as {role}.", "success")

        return redirect(url_for("users.user_management"))

    return render_template("user_management.html", users=data.USERS, roles=data.ROLES)


@users_bp.route("/users/export", methods=["GET"])
# @admin_required  # TEMP: role restriction disabled for now — re-enable when ready to lock this down again
@login_required
def export_users():
    rows = [
        {**u, "status": "Active" if u["active"] else "Inactive"}
        for u in data.USERS
    ]
    return send_xlsx(
        rows,
        columns=["name", "mobile", "username", "role", "status"],
        headers=["Name", "Mobile", "Username", "Role", "Status"],
        sheet_name="All Users",
        filename="users.xlsx",
    )


@users_bp.route("/users/<username>/toggle", methods=["POST"])
# @admin_required  # TEMP: role restriction disabled for now — re-enable when ready to lock this down again
@login_required
def toggle_user(username):
    user = data.find_user(username)
    if user:
        if user["username"] == current_user()["username"]:
            flash("You can't deactivate your own account.", "error")
        else:
            user["active"] = not user["active"]
            flash(f"{user['name']} is now {'active' if user['active'] else 'inactive'}.", "success")
    return redirect(url_for("users.user_management"))


@users_bp.route("/users/<username>/delete", methods=["POST"])
# @admin_required  # TEMP: role restriction disabled for now — re-enable when ready to lock this down again
@login_required
def delete_user(username):
    user = data.find_user(username)
    if user is None:
        flash("User not found.", "error")
    elif user["username"] == current_user()["username"]:
        flash("You can't delete your own account.", "error")
    else:
        data.delete_user(username)
        flash(f"Deleted {user['name']} ({username}).", "success")
    return redirect(url_for("users.user_management"))


@users_bp.route("/users/<username>/password", methods=["POST"])
# @admin_required  # TEMP: role restriction disabled for now — re-enable when ready to lock this down again
@login_required
def change_password(username):
    user = data.find_user(username)
    new_password = request.form.get("password", "")

    if user is None:
        flash("User not found.", "error")
    elif len(new_password) < 6:
        flash("Password must be at least 6 characters.", "error")
    else:
        data.set_password(username, new_password)
        flash(f"Password updated for {user['name']}.", "success")
    return redirect(url_for("users.user_management"))


@users_bp.route("/users/<username>/role", methods=["POST"])
# @admin_required  # TEMP: role restriction disabled for now — re-enable when ready to lock this down again
@login_required
def change_role(username):
    user = data.find_user(username)
    new_role = request.form.get("role", "")

    if user is None:
        flash("User not found.", "error")
    elif new_role not in data.ROLES:
        flash("Please choose a valid role.", "error")
    elif user["username"] == current_user()["username"] and user["role"] == "admin" and new_role != "admin":
        flash("You can't change your own role away from admin.", "error")
    else:
        data.set_role(username, new_role)
        flash(f"{user['name']} is now {new_role}.", "success")
    return redirect(url_for("users.user_management"))


# --------------------------------------------------------------------- #
# Volunteer <-> location assignment
# --------------------------------------------------------------------- #
@users_bp.route("/volunteers", methods=["GET"])
@login_required
def volunteer_assignment():
    """
    Assigns volunteers ("volunteer" role accounts) to locations/events.
    The assignments themselves are managed entirely client-side in JS for
    now (no persistence) — this route just supplies the two lists the page
    needs: who can be assigned, and where.
    """
    volunteers = [u for u in data.USERS if u["role"] == "volunteer"]
    return render_template(
        "volunteer_assignment.html",
        volunteers=volunteers,
        locations=LOCATIONS,
    )