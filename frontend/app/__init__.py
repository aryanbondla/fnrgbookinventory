"""
Application factory for FNRG Preaching.

Wires together two service-style blueprints:
  - users_service  (auth + user management)   -> url_for('users.xxx')
  - books_service   (catalog/sales/analytics)   -> url_for('books.xxx')

They only talk to each other through app.shared.auth, so each package
could be pulled out into its own deployable Flask app later with minimal
rework (see README).
"""

from flask import Flask


def create_app():
    app = Flask(__name__)

    # Replace with something secret & pulled from the environment in production.
    app.config["SECRET_KEY"] = "dev-secret-key-change-me"

    from .users_service import users_bp
    from .books_service import books_bp

    app.register_blueprint(users_bp)
    app.register_blueprint(books_bp)

    # Registered on the app (not a single blueprint) so `current_user` is
    # available in every template, regardless of which service's route
    # rendered it. A per-blueprint context_processor only applies to
    # templates rendered by that blueprint's own views — which is what
    # caused Analytics/User Management to vanish from the sidebar when
    # rendered from books_service routes.
    from app.shared.auth import current_user

    @app.context_processor
    def inject_user():
        return {"current_user": current_user()}

    return app
