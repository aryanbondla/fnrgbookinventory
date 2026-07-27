"""
In-memory dummy data for FNRG Preaching.

Everything here lives in process memory only — restarting the app resets it.
Swap this module out for real database models when you're ready to persist
data (see README for suggested next steps).
"""

import random
from datetime import date, timedelta

# --- Users -------------------------------------------------------------
# role: "admin" can see org-wide analytics + manage users.
#       "user" only sees their own dashboard + can add sell entries.
USERS = [
    {"username": "admin", "name": "Admin",          "role": "admin", "active": True},
    {"username": "arjun", "name": "Arjun Das",       "role": "user",  "active": True},
    {"username": "priya", "name": "Priya Devi",      "role": "user",  "active": True},
    {"username": "rahul", "name": "Rahul Krishna",   "role": "user",  "active": True},
    {"username": "sita",  "name": "Sita Rani",       "role": "user",  "active": False},
]

BOOKS = [
    ("Bhagavad Gita As It Is", "Philosophy"),
    ("Srimad Bhagavatam Canto 1", "Scripture"),
    ("Sri Chaitanya Charitamrita", "Biography"),
    ("Nectar of Devotion", "Philosophy"),
    ("Nectar of Instruction", "Philosophy"),
    ("Krishna Book", "Storytelling"),
    ("Science of Self Realization", "Philosophy"),
    ("Beyond Illusion and Doubt", "Essays"),
    ("Life Comes From Life", "Science"),
    ("Perfect Questions Perfect Answers", "Philosophy"),
    ("The Higher Taste (Cookbook)", "Lifestyle"),
    ("Easy Journey to Other Planets", "Philosophy"),
]

CATEGORIES = sorted({c for _, c in BOOKS})

# --- Inventory -----------------------------------------------------------
# Initial stock received per title (e.g. from the printer / BBT). Books
# sold (from SALES) are subtracted from this at read time to get what's
# currently available — see analytics.inventory_snapshot().
INITIAL_STOCK = {
    "Bhagavad Gita As It Is": 120,
    "Srimad Bhagavatam Canto 1": 60,
    "Sri Chaitanya Charitamrita": 40,
    "Nectar of Devotion": 55,
    "Nectar of Instruction": 70,
    "Krishna Book": 65,
    "Science of Self Realization": 50,
    "Beyond Illusion and Doubt": 35,
    "Life Comes From Life": 30,
    "Perfect Questions Perfect Answers": 45,
    "The Higher Taste (Cookbook)": 40,
    "Easy Journey to Other Planets": 38,
}


def _generate_sales(n=70, days_back=60, seed=42):
    rng = random.Random(seed)
    sellers = [u["username"] for u in USERS if u["role"] == "user"]
    today = date.today()
    rows = []
    for i in range(1, n + 1):
        title, category = rng.choice(BOOKS)
        seller = rng.choice(sellers)
        day = today - timedelta(days=rng.randint(0, days_back))
        qty = rng.randint(1, 6)
        cost_price = rng.choice([60, 80, 100, 120, 150, 180, 220])
        # sell price is usually cost + margin, occasionally sold at a loss
        # (e.g. discounted / damaged stock) so profit & loss both show up.
        margin_pct = rng.choice([-10, -5, 10, 15, 20, 25, 30, 40])
        sell_price = round(cost_price * (1 + margin_pct / 100))
        rows.append({
            "id": i,
            "date": day.isoformat(),
            "title": title,
            "category": category,
            "seller": seller,
            "qty": qty,
            "cost_price": cost_price,
            "sell_price": sell_price,
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


SALES = _generate_sales()


def next_sale_id():
    return (max((r["id"] for r in SALES), default=0)) + 1


def next_username_available(username: str) -> bool:
    return not any(u["username"] == username for u in USERS)
