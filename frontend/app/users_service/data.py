"""
In-memory "database" for the Users service.

In a real microservice split this would be the Users service's own DB
(e.g. a small SQLite/Postgres instance it alone owns) — see
schema_users_service.sql. Other services (like books_service) never touch
this list directly; they go through app.shared.auth, which is the stand-in
for a call to this service's API.
"""

# role: "admin" can see org-wide analytics + manage users.
#       "user" only sees their own dashboard + can add sell entries.
USERS = [
    {"username": "admin", "name": "Admin",          "role": "admin", "active": True},
    {"username": "arjun", "name": "Arjun Das",       "role": "user",  "active": True},
    {"username": "priya", "name": "Priya Devi",      "role": "user",  "active": True},
    {"username": "rahul", "name": "Rahul Krishna",   "role": "user",  "active": True},
    {"username": "sita",  "name": "Sita Rani",       "role": "user",  "active": False},
]


def next_username_available(username: str) -> bool:
    return not any(u["username"] == username for u in USERS)


def find_user(username: str):
    return next((u for u in USERS if u["username"] == username), None)
