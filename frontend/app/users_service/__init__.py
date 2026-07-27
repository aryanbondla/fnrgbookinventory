"""
Users service — owns login/logout and user management.

Registered under Blueprint name "users" (so url_for('users.xxx')). In a
real microservice deployment this package could run as its own Flask app
behind its own port/URL, with a small internal API for other services
(like books_service) to resolve a session into a user + role.
"""

from flask import Blueprint

users_bp = Blueprint("users", __name__)

from . import routes  # noqa: E402,F401  (registers routes on import)
