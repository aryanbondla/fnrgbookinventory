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

# Book catalog — each title carries its own shorthand (used on the Inward
# Stock rows / backups so long titles are quick to scan) and category.
# Kept as dicts (rather than the old (title, category) tuples) so the
# shorthand has somewhere to live; see the Master Data page / master_data
# route for where these get added to through the UI.
BOOKS = [
    {"title": "Bhagavad Gita As It Is", "short_title": "BG", "category": "Philosophy"},
    {"title": "Srimad Bhagavatam Canto 1", "short_title": "SB1", "category": "Scripture"},
    {"title": "Sri Chaitanya Charitamrita", "short_title": "CC", "category": "Biography"},
    {"title": "Nectar of Devotion", "short_title": "NOD", "category": "Philosophy"},
    {"title": "Nectar of Instruction", "short_title": "NOI", "category": "Philosophy"},
    {"title": "Krishna Book", "short_title": "KB", "category": "Storytelling"},
    {"title": "Science of Self Realization", "short_title": "SSR", "category": "Philosophy"},
    {"title": "Beyond Illusion and Doubt", "short_title": "BID", "category": "Essays"},
    {"title": "Life Comes From Life", "short_title": "LCFL", "category": "Science"},
    {"title": "Perfect Questions Perfect Answers", "short_title": "PQPA", "category": "Philosophy"},
    {"title": "The Higher Taste (Cookbook)", "short_title": "THT", "category": "Lifestyle"},
    {"title": "Easy Journey to Other Planets", "short_title": "EJOP", "category": "Philosophy"},
]

CATEGORIES = sorted({b["category"] for b in BOOKS})

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

# Named preaching programs / festivals books get distributed at — distinct
# from LOCATIONS (the physical place). Managed from the Master Data page
# alongside categories, languages and locations.
EVENTS = [
    "Janmashtami Festival",
    "Ratha Yatra Festival",
    "Gita Jayanti",
    "College Fest - JNTU",
    "Sunday Feast Program",
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
        book = rng.choice(BOOKS)
        title, category = book["title"], book["category"]
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


# --- Master data helpers --------------------------------------------------
# Small, dependency-free add/lookup helpers backing the Master Data page
# (see books_service/routes.py: master_data()). Each keeps its own list
# de-duplicated and sorted where that list is display-ordered.

def find_book(title):
    title = (title or "").strip()
    return next((b for b in BOOKS if b["title"].lower() == title.lower()), None)


def add_book(title, short_title, category):
    """
    Adds a new title to the catalog. Returns (book, created) — created is
    False if the title already exists (nothing is overwritten in that
    case, so this is safe to call from both the Master Data page and the
    Inward Stock "+ Add New Book" flow without clobbering an existing
    entry). Also grows CATEGORIES if this introduces a new one.
    """
    title = (title or "").strip()
    short_title = (short_title or "").strip()
    category = (category or "").strip() or "Uncategorized"

    existing = find_book(title)
    if existing:
        return existing, False

    book = {"title": title, "short_title": short_title, "category": category}
    BOOKS.append(book)
    add_category(category)
    return book, True


def add_category(name):
    global CATEGORIES
    name = (name or "").strip()
    if not name:
        return False
    if name in CATEGORIES:
        return False
    CATEGORIES = sorted(set(CATEGORIES) | {name})
    return True


def add_language(name):
    name = (name or "").strip()
    if not name or name in LANGUAGES:
        return False
    LANGUAGES.append(name)
    return True


def add_location(name):
    name = (name or "").strip()
    if not name or name in LOCATIONS:
        return False
    LOCATIONS.append(name)
    return True


def add_event(name):
    name = (name or "").strip()
    if not name or name in EVENTS:
        return False
    EVENTS.append(name)
    return True