"""
In-memory "database" for the Users service.

In a real microservice split this would be the Users service's own DB
(e.g. a small SQLite/Postgres instance it alone owns) — see
schema_users_service.sql. Other services (like books_service) never touch
this list directly; they go through app.shared.auth, which is the stand-in
for a call to this service's API.
"""

from werkzeug.security import generate_password_hash, check_password_hash

# Valid roles a user account can hold.
#   "admin"      — org-wide analytics + full user management
#   "commander"  — oversees volunteers/locations, elevated access
#   "volunteer"  — own dashboard + sell entries only
ROLES = ["admin", "volunteer", "commander"]

USERS = [
    {"username": "admin", "name": "Admin",          "mobile": "9999900000", "password_hash": generate_password_hash("admin123"),     "role": "admin",     "active": True},
    {"username": "arjun", "name": "Arjun Das",       "mobile": "9876500001", "password_hash": generate_password_hash("volunteer123"), "role": "volunteer", "active": True},
    {"username": "priya", "name": "Priya Devi",      "mobile": "9876500002", "password_hash": generate_password_hash("volunteer123"), "role": "volunteer", "active": True},
    {"username": "rahul", "name": "Rahul Krishna",   "mobile": "9876500003", "password_hash": generate_password_hash("commander123"), "role": "commander", "active": True},
    {"username": "sita",  "name": "Sita Rani",       "mobile": "9876500004", "password_hash": generate_password_hash("volunteer123"), "role": "volunteer", "active": False},
]


def next_username_available(username: str) -> bool:
    return not any(u["username"] == username for u in USERS)


def find_user(username: str):
    return next((u for u in USERS if u["username"] == username), None)


def add_user(name: str, mobile: str, username: str, password: str, role: str):
    user = {
        "username": username,
        "name": name,
        "mobile": mobile,
        "password_hash": generate_password_hash(password),
        "role": role if role in ROLES else "volunteer",
        "active": True,
    }
    USERS.append(user)
    return user


def delete_user(username: str) -> bool:
    user = find_user(username)
    if user is None:
        return False
    USERS.remove(user)
    return True


def set_password(username: str, new_password: str) -> bool:
    user = find_user(username)
    if user is None:
        return False
    user["password_hash"] = generate_password_hash(new_password)
    return True


def set_role(username: str, new_role: str) -> bool:
    user = find_user(username)
    if user is None or new_role not in ROLES:
        return False
    user["role"] = new_role
    return True


def verify_password(user: dict, password: str) -> bool:
    stored = user.get("password_hash")
    if not stored:
        return False
    return check_password_hash(stored, password)
