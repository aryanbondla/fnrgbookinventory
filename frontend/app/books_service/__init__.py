"""
Books service — owns the catalog, sales ledger, inventory, and analytics.

Registered under Blueprint name "books" (so url_for('books.xxx')). Only
talks to the Users service through app.shared.auth (current_user /
login_required / admin_required) — never touches users_service.data
directly, mirroring a real service-to-service boundary.
"""

from flask import Blueprint

books_bp = Blueprint("books", __name__)

from . import routes  # noqa: E402,F401  (registers routes on import)
