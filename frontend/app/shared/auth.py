"""
Shared auth helpers.

In a true multi-process microservice setup, books_service would call the
Users service's API (e.g. GET /internal/users/<username>) to resolve the
logged-in session into a user record + role, rather than importing a
Python module directly. Since this repo runs both services inside one
Flask process for simplicity, this module is that call boundary — it's
the *only* place books_service reaches into users_service's data.
"""

from functools import wraps
from flask import session, redirect, url_for, flash

from app.users_service.data import find_user


def current_user():
    username = session.get("username")
    if not username:
        return None
    return find_user(username)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("users.index"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("users.index"))
        if user["role"] != "admin":
            flash("That page is only available to admins.")
            return redirect(url_for("books.dashboard"))
        return view(*args, **kwargs)
    return wrapped
