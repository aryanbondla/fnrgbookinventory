"""
Routes owned by the Users service.

    GET  /                 sign-in page (redirects to Books service's
                            dashboard if already logged in)
    POST /login
    GET  /logout

    GET  /users             admin-only: list + add users
    POST /users
    POST /users/<username>/toggle

    GET  /volunteers          volunteer <-> location assignment page
"""

from flask import render_template, request, redirect, url_for, session, flash

from . import users_bp
from . import data
from app.shared.auth import current_user, admin_required, login_required
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
    Demo auth: any known, active username in data.USERS signs in with any
    non-empty password. Usernames not already registered auto-register as
    a regular ("user") role so the flow is runnable end-to-end without a
    real credential store. Replace with real password verification before
    this goes anywhere real (see README / schema_users_service.sql).
    """
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")

    if not username or not password:
        flash("Please enter both a user name and password.")
        return redirect(url_for("users.index"))

    user = data.find_user(username)
    if user is None:
        user = {"username": username, "name": username.title(), "role": "user", "active": True}
        data.USERS.append(user)

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

        return redirect(url_for("users.user_management"))

    return render_template("user_management.html", users=data.USERS)


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


# --------------------------------------------------------------------- #
# Volunteer <-> location assignment
# --------------------------------------------------------------------- #
@users_bp.route("/volunteers", methods=["GET"])
@login_required
def volunteer_assignment():
    """
    Assigns volunteers (regular "user" role accounts) to locations/events.
    The assignments themselves are managed entirely client-side in JS for
    now (no persistence) — this route just supplies the two lists the page
    needs: who can be assigned, and where.
    """
    volunteers = [u for u in data.USERS if u["role"] == "user"]
    return render_template(
        "volunteer_assignment.html",
        volunteers=volunteers,
        locations=LOCATIONS,
    )