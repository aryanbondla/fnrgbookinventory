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


def filter_sales(sales, date_from=None, date_to=None, seller=None, location=None):
    rows = sales
    if date_from:
        rows = [r for r in rows if r["date"] >= date_from]
    if date_to:
        rows = [r for r in rows if r["date"] <= date_to]
    if seller and seller != "all":
        rows = [r for r in rows if r["seller"] == seller]
    if location and location != "all":
        rows = [r for r in rows if r["location"] == location]
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
    by_day = defaultdict(lambda: {"revenue": 0, "cost": 0, "profit": 0})
    for r in rows:
        d = by_day[r["date"]]
        d["revenue"] += revenue_of(r)
        d["cost"] += cost_of(r)
        d["profit"] += profit_of(r)
    days = sorted(by_day.keys())
    return {
        "labels": days,
        "revenue": [by_day[d]["revenue"] for d in days],
        "cost": [by_day[d]["cost"] for d in days],
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


def sales_by_location(rows):
    by_loc = defaultdict(lambda: {"revenue": 0, "profit": 0, "qty": 0, "orders": 0})
    for r in rows:
        loc = by_loc[r.get("location") or "Unspecified"]
        loc["revenue"] += revenue_of(r)
        loc["profit"] += profit_of(r)
        loc["qty"] += r["qty"]
        loc["orders"] += 1
    items = sorted(by_loc.items(), key=lambda kv: kv[1]["revenue"], reverse=True)
    return [{"location": k, **v} for k, v in items]


def sales_by_language(rows):
    by_lang = defaultdict(int)
    for r in rows:
        by_lang[r.get("language") or "Unspecified"] += r["qty"]
    items = sorted(by_lang.items(), key=lambda kv: kv[1], reverse=True)
    return {"labels": [k for k, _ in items], "values": [v for _, v in items]}


def top_books(rows, limit=5):
    by_title = defaultdict(lambda: {"qty": 0, "profit": 0})
    for r in rows:
        t = by_title[r["title"]]
        t["qty"] += r["qty"]
        t["profit"] += profit_of(r)
    items = sorted(by_title.items(), key=lambda kv: kv[1]["qty"], reverse=True)
    if limit is not None:
        items = items[:limit]
    return [{"title": k, **v} for k, v in items]


def last_n_days_range(n=30):
    end = date.today()
    start = end - timedelta(days=n - 1)
    return start.isoformat(), end.isoformat()


def inventory_snapshot(sales, initial_stock, books, purchases=None, perf_sales=None):
    """
    Returns per-book stock remaining — initial stock plus everything ever
    received via Inward Stock, minus everything ever sold, regardless of
    any date/seller/event filter (this reflects the physical shelf, not a
    filtered report) — plus category, sorted with the lowest-stock books
    first so shortages are easy to spot.

    `sales` (always the full, all-time ledger) drives the stock columns.
    `perf_sales` — the currently-filtered rows (by date/user/event), or
    `sales` again if no filter was passed — drives the avg cost/sell
    price and profit-or-loss columns, so those reflect whatever window
    the person has selected while "Stock in Hand" stays an accurate,
    unfiltered physical count.
    """
    perf_sales = sales if perf_sales is None else perf_sales

    sold_by_title = defaultdict(int)
    for r in sales:
        sold_by_title[r["title"]] += r["qty"]

    perf_qty_by_title = defaultdict(int)
    cost_by_title = defaultdict(float)
    revenue_by_title = defaultdict(float)
    for r in perf_sales:
        perf_qty_by_title[r["title"]] += r["qty"]
        cost_by_title[r["title"]] += cost_of(r)
        revenue_by_title[r["title"]] += revenue_of(r)

    received_by_title = defaultdict(int)
    for p in (purchases or []):
        received_by_title[p["title"]] += p["qty"]

    rows = []
    for title, category in books:
        stock = initial_stock.get(title, 0)
        received = received_by_title.get(title, 0)
        sold = sold_by_title.get(title, 0)
        available = stock + received - sold

        perf_qty = perf_qty_by_title.get(title, 0)
        total_cost = cost_by_title.get(title, 0.0)
        total_revenue = revenue_by_title.get(title, 0.0)
        profit_or_loss = total_revenue - total_cost
        avg_cost = (total_cost / perf_qty) if perf_qty else 0.0
        avg_sell = (total_revenue / perf_qty) if perf_qty else 0.0
        pl_pct = (profit_or_loss / total_cost * 100) if total_cost else 0.0

        rows.append({
            "title": title,
            "category": category,
            "initial_stock": stock,
            "received": received,
            "sold": sold,
            "available": available,
            "avg_cost": avg_cost,
            "avg_sell": avg_sell,
            "profit_or_loss": profit_or_loss,
            "pl_pct": pl_pct,
        })
    rows.sort(key=lambda r: r["available"])
    return rows