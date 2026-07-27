"""
Aggregation helpers for turning the flat SALES list into dashboard /
analytics-ready numbers. Kept framework-agnostic (plain dicts/lists) so it's
easy to swap in real DB queries later.
"""

from collections import defaultdict
from datetime import date, timedelta


def profit_of(row):
    return (row["sell_price"] - row["cost_price"]) * row["qty"]


def revenue_of(row):
    return row["sell_price"] * row["qty"]


def cost_of(row):
    return row["cost_price"] * row["qty"]


def filter_sales(sales, date_from=None, date_to=None, seller=None):
    rows = sales
    if date_from:
        rows = [r for r in rows if r["date"] >= date_from]
    if date_to:
        rows = [r for r in rows if r["date"] <= date_to]
    if seller and seller != "all":
        rows = [r for r in rows if r["seller"] == seller]
    return rows


def summary(rows):
    total_qty = sum(r["qty"] for r in rows)
    total_revenue = sum(revenue_of(r) for r in rows)
    total_cost = sum(cost_of(r) for r in rows)
    total_profit = total_revenue - total_cost
    loss_rows = [r for r in rows if profit_of(r) < 0]
    total_loss = -sum(profit_of(r) for r in loss_rows)
    return {
        "orders": len(rows),
        "qty": total_qty,
        "revenue": total_revenue,
        "cost": total_cost,
        "profit": total_profit,
        "loss": total_loss,
    }


def revenue_profit_by_day(rows):
    by_day = defaultdict(lambda: {"revenue": 0, "profit": 0})
    for r in rows:
        d = by_day[r["date"]]
        d["revenue"] += revenue_of(r)
        d["profit"] += profit_of(r)
    days = sorted(by_day.keys())
    return {
        "labels": days,
        "revenue": [by_day[d]["revenue"] for d in days],
        "profit": [by_day[d]["profit"] for d in days],
    }


def profit_by_category(rows):
    by_cat = defaultdict(int)
    for r in rows:
        by_cat[r["category"]] += profit_of(r)
    items = sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True)
    return {"labels": [k for k, _ in items], "values": [v for _, v in items]}


def qty_by_category(rows):
    by_cat = defaultdict(int)
    for r in rows:
        by_cat[r["category"]] += r["qty"]
    items = sorted(by_cat.items(), key=lambda kv: kv[1], reverse=True)
    return {"labels": [k for k, _ in items], "values": [v for _, v in items]}


def leaderboard_by_seller(rows):
    by_seller = defaultdict(lambda: {"revenue": 0, "profit": 0, "qty": 0})
    for r in rows:
        s = by_seller[r["seller"]]
        s["revenue"] += revenue_of(r)
        s["profit"] += profit_of(r)
        s["qty"] += r["qty"]
    items = sorted(by_seller.items(), key=lambda kv: kv[1]["revenue"], reverse=True)
    return [{"seller": k, **v} for k, v in items]


def top_books(rows, limit=5):
    by_title = defaultdict(lambda: {"qty": 0, "profit": 0})
    for r in rows:
        t = by_title[r["title"]]
        t["qty"] += r["qty"]
        t["profit"] += profit_of(r)
    items = sorted(by_title.items(), key=lambda kv: kv[1]["qty"], reverse=True)[:limit]
    return [{"title": k, **v} for k, v in items]


def last_n_days_range(n=30):
    end = date.today()
    start = end - timedelta(days=n - 1)
    return start.isoformat(), end.isoformat()


def inventory_snapshot(sales, initial_stock, books):
    """
    Returns per-book stock remaining (initial stock minus everything ever
    sold, regardless of any date/seller filter — this reflects the
    physical shelf, not a filtered report) plus category, sorted with the
    lowest-stock books first so shortages are easy to spot.
    """
    sold_by_title = defaultdict(int)
    for r in sales:
        sold_by_title[r["title"]] += r["qty"]

    rows = []
    for title, category in books:
        stock = initial_stock.get(title, 0)
        sold = sold_by_title.get(title, 0)
        available = stock - sold
        rows.append({
            "title": title,
            "category": category,
            "initial_stock": stock,
            "sold": sold,
            "available": available,
        })
    rows.sort(key=lambda r: r["available"])
    return rows
