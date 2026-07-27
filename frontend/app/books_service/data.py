"""
In-memory "database" for the Books service.

Owns everything about the catalog and the sales/distribution ledger — see
schema_books_service.sql. This is deliberately kept separate from
users_service.data: the Books service only ever knows a *username* string
for who sold something, never the Users service's internal record. That
mirrors how two real microservices would only share an identifier, not a
shared table.
"""

import random
from datetime import date, timedelta

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

# Common places books are purchased from — seeds the "Source Purchased
# From" suggestions on the Inward Stock page. Any new source typed in
# there shows up in the list too (see inward_stock() route), same idea
# as CATEGORIES growing when a new book category is added.
SOURCES = [
    "BBT Chennai Press",
    "BBT Mumbai Press",
    "Local Printer - Hyderabad",
    "Donation",
]

# Language of the specific copy sold (a title may be stocked in several
# languages) and where the sale/distribution happened. Kept as short fixed
# lists (not separate DB tables) — see schema_books_service.sql for how
# these become compact single-byte codes instead of extra tables.
LANGUAGES = ["English", "Hindi", "Telugu", "Bengali", "Tamil", "Sanskrit", "Gujarati"]

LOCATIONS = [
    "Hyderabad Temple",
    "Secunderabad Book Table",
    "Airport Stall",
    "Street Sankirtan - Banjara Hills",
    "College Fest - JNTU",
    "Ratha Yatra Festival",
    "Home Program - Madhapur",
]

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
    # Import kept local so this module has no hard dependency on
    # users_service — sellers here are just username strings, matching
    # how a real cross-service reference would look.
    sellers = ["arjun", "priya", "rahul"]
    rng = random.Random(seed)
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
            "language": rng.choice(LANGUAGES),
            "location": rng.choice(LOCATIONS),
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


SALES = _generate_sales()


def next_sale_id():
    return (max((r["id"] for r in SALES), default=0)) + 1


# --- Inward stock (purchases) ---------------------------------------------
# Every book received into stock after the initial baseline (INITIAL_STOCK)
# is logged here — a purchase from the printer, a reprint, a donation, etc.
# inventory_snapshot() adds these on top of INITIAL_STOCK and subtracts
# SALES to get what's currently available. Newest first, same convention
# as SALES.
PURCHASES = [
    {
        "id": 1,
        "date": "2026-07-20",
        "title": "Bhagavad Gita As It Is",
        "short_title": "BG",
        "category": "Philosophy",
        "language": "English",
        "source": "BBT Chennai Press",
        "qty": 50,
        "cost_price": 95,
        "recorded_by": "admin",
    },
    {
        "id": 2,
        "date": "2026-07-15",
        "title": "Srimad Bhagavatam Canto 1",
        "short_title": "SB1",
        "category": "Scripture",
        "language": "Hindi",
        "source": "Local Printer - Hyderabad",
        "qty": 25,
        "cost_price": 110,
        "recorded_by": "admin",
    },
]


def next_purchase_id():
    return (max((p["id"] for p in PURCHASES), default=0)) + 1