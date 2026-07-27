"""
Routes owned by the Books service.

    GET  /dashboard          personal (or org-wide, for admins) overview
                              + inventory
    GET  /dashboard/export/leaderboard    .xlsx of Top Distributors table
    GET  /dashboard/export/top-books      .xlsx of Top Books table
    GET  /dashboard/export/inventory      .xlsx of Book Inventory table
    GET  /sell                 book sell-entry form + recent entries
    POST /sell
    GET  /sell/export                     .xlsx of My Recent Entries table
    GET  /analytics              admin-only profit/loss analytics with filters
    GET  /backup                   last-7-days backup page (one link per day)
    GET  /backup/download/<day>     downloads that single day's .xlsx backup
    GET  /inward-stock                    inward stock form + recent purchases
    POST /inward-stock
    GET  /inward-stock/export             .xlsx of Recent Purchases table
"""

from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash

from . import books_bp
from . import data
from . import analytics as an
from app.shared.auth import current_user, login_required, admin_required
from app.shared.xlsx_export import send_xlsx, send_xlsx_multi


# --------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------- #
def _dashboard_section_filters(prefix, is_admin, user):
    """
    Reads this section's own (prefixed) query params only, so submitting
    one filter bar never touches another section's filter state. Falls
    back to the 30-day default window / "all" when a param is missing,
    e.g. the first page load. Shared by the dashboard page itself and its
    per-table export routes so a download always matches what's on screen.
    """
    default_from, default_to = an.last_n_days_range(30)
    date_from = request.args.get(f"{prefix}date_from") or default_from
    date_to = request.args.get(f"{prefix}date_to") or default_to
    # Only admins can look at another seller's numbers — everyone else
    # is always pinned to their own username regardless of the URL.
    seller = (request.args.get(f"{prefix}seller") or "all") if is_admin else user["username"]
    event = request.args.get(f"{prefix}event") or "all"
    return {"date_from": date_from, "date_to": date_to, "seller": seller, "event": event}


def _dashboard_scope_rows(is_admin, user):
    return data.SALES if is_admin else an.filter_sales(data.SALES, seller=user["username"])


@books_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    user = current_user()
    is_admin = user["role"] == "admin"

    # One independent filter state per section of the page.
    main_f = _dashboard_section_filters("", is_admin, user)
    dist_f = _dashboard_section_filters("dist_", is_admin, user)
    books_f = _dashboard_section_filters("books_", is_admin, user)
    inv_f = _dashboard_section_filters("inv_", is_admin, user)
    filters = {"": main_f, "dist_": dist_f, "books_": books_f, "inv_": inv_f}

    scope_rows = _dashboard_scope_rows(is_admin, user)

    recent_rows = an.filter_sales(
        scope_rows, date_from=main_f["date_from"], date_to=main_f["date_to"],
        seller=main_f["seller"], location=main_f["event"],
    )
    kpis = an.summary(recent_rows)
    trend = an.revenue_profit_by_day(recent_rows)
    top_cats = an.qty_by_category(recent_rows)
    net_pl = kpis["profit"]
    pl_pct = (net_pl / kpis["cost"] * 100) if kpis["cost"] else 0.0

    dist_rows = an.filter_sales(
        scope_rows, date_from=dist_f["date_from"], date_to=dist_f["date_to"],
        seller=dist_f["seller"], location=dist_f["event"],
    )
    leaderboard = an.leaderboard_by_seller(dist_rows) if is_admin else None

    books_rows = an.filter_sales(
        scope_rows, date_from=books_f["date_from"], date_to=books_f["date_to"],
        seller=books_f["seller"], location=books_f["event"],
    )
    my_top_books = an.top_books(books_rows, limit=None)

    inv_rows = an.filter_sales(
        scope_rows, date_from=inv_f["date_from"], date_to=inv_f["date_to"],
        seller=inv_f["seller"], location=inv_f["event"],
    )
    # Stock counts always reflect the whole physical shelf (all-time sales
    # history), but the avg cost/sell/profit-or-loss columns respect the
    # inventory section's own filter bar.
    inventory = an.inventory_snapshot(
        data.SALES, data.INITIAL_STOCK, data.BOOKS, data.PURCHASES, perf_sales=inv_rows
    )
    total_available = sum(r["available"] for r in inventory)

    sellers = sorted({r["seller"] for r in data.SALES})
    events = sorted({r["location"] for r in data.SALES if r.get("location")})

    return render_template(
        "home.html",
        is_admin=is_admin,
        kpis=kpis,
        net_pl=net_pl,
        pl_pct=pl_pct,
        trend=trend,
        top_cats=top_cats,
        leaderboard=leaderboard,
        my_top_books=my_top_books,
        inventory=inventory,
        total_available=total_available,
        window_label=f"{main_f['date_from']} to {main_f['date_to']}",
        filters=filters,
        sellers=sellers,
        events=events,
    )


@books_bp.route("/dashboard/export/leaderboard", methods=["GET"])
@admin_required
def export_leaderboard():
    user = current_user()
    f = _dashboard_section_filters("dist_", True, user)
    scope_rows = _dashboard_scope_rows(True, user)
    rows = an.filter_sales(
        scope_rows, date_from=f["date_from"], date_to=f["date_to"],
        seller=f["seller"], location=f["event"],
    )
    leaderboard = an.leaderboard_by_seller(rows)
    return send_xlsx(
        leaderboard,
        columns=["seller", "revenue", "qty", "profit"],
        headers=["Name", "Amount Collected", "Qty", "Profit"],
        sheet_name="Top Distributors",
        filename=f"top_distributors_{f['date_from']}_to_{f['date_to']}.xlsx",
    )


@books_bp.route("/dashboard/export/top-books", methods=["GET"])
@login_required
def export_top_books():
    user = current_user()
    is_admin = user["role"] == "admin"
    f = _dashboard_section_filters("books_", is_admin, user)
    scope_rows = _dashboard_scope_rows(is_admin, user)
    rows = an.filter_sales(
        scope_rows, date_from=f["date_from"], date_to=f["date_to"],
        seller=f["seller"], location=f["event"],
    )
    top_books = an.top_books(rows, limit=None)
    return send_xlsx(
        top_books,
        columns=["title", "qty"],
        headers=["Title", "Qty Distributed"],
        sheet_name="Top Books",
        filename=f"top_books_{f['date_from']}_to_{f['date_to']}.xlsx",
    )


@books_bp.route("/dashboard/export/inventory", methods=["GET"])
@login_required
def export_inventory():
    user = current_user()
    is_admin = user["role"] == "admin"
    f = _dashboard_section_filters("inv_", is_admin, user)
    scope_rows = _dashboard_scope_rows(is_admin, user)
    inv_rows = an.filter_sales(
        scope_rows, date_from=f["date_from"], date_to=f["date_to"],
        seller=f["seller"], location=f["event"],
    )
    inventory = an.inventory_snapshot(
        data.SALES, data.INITIAL_STOCK, data.BOOKS, data.PURCHASES, perf_sales=inv_rows
    )
    return send_xlsx(
        inventory,
        columns=["title", "available", "avg_cost", "avg_sell", "profit_or_loss", "pl_pct"],
        headers=["Book Name", "Stock in Hand (Available)", "Avg Cost / Book", "Avg Sell / Book", "Profit or Loss", "% Profit/Loss"],
        sheet_name="Book Inventory",
        filename=f"book_inventory_{f['date_from']}_to_{f['date_to']}.xlsx",
    )


# --------------------------------------------------------------------- #
# Sell entry
# --------------------------------------------------------------------- #
@books_bp.route("/sell", methods=["GET", "POST"])
@login_required
def sell_entry():
    user = current_user()

    if request.method == "POST":
        try:
            row = {
                "id": data.next_sale_id(),
                "date": request.form.get("date") or "",
                "title": request.form.get("title", "").strip(),
                "category": request.form.get("category", "").strip(),
                "seller": user["username"],
                "qty": int(request.form.get("qty", 0)),
                "cost_price": float(request.form.get("cost_price", 0)),
                "sell_price": float(request.form.get("sell_price", 0)),
                "language": request.form.get("language", "").strip(),
                "location": request.form.get("location", "").strip(),
            }
            if not row["title"] or not row["date"] or row["qty"] <= 0 or not row["language"] or not row["location"]:
                raise ValueError("missing required fields")
            data.SALES.insert(0, row)
            flash(f"Recorded sale of {row['qty']} x \"{row['title']}\".", "success")
        except (TypeError, ValueError):
            flash("Please fill in every field with valid values.", "error")

        return redirect(url_for("books.sell_entry"))

    my_sales = an.filter_sales(data.SALES, seller=user["username"])[:15]
    return render_template(
        "sell_entry.html",
        book_titles=[b["title"] for b in data.BOOKS],
        categories=data.CATEGORIES,
        languages=data.LANGUAGES,
        locations=data.LOCATIONS,
        my_sales=my_sales,
    )


@books_bp.route("/sell/export", methods=["GET"])
@login_required
def export_sell_entries():
    user = current_user()
    my_sales = an.filter_sales(data.SALES, seller=user["username"])
    return send_xlsx(
        my_sales,
        columns=["date", "title", "location", "location", "qty", "sell_price"],
        headers=["Distribution Date", "Book Name", "Event", "Location", "Qty", "Sell Price"],
        sheet_name="My Recent Entries",
        filename=f"my_sales_{user['username']}.xlsx",
    )


# --------------------------------------------------------------------- #
# Backup — download each of the last 7 days' records as its own Excel file
# --------------------------------------------------------------------- #
BACKUP_DAYS = 7
SALES_BACKUP_COLUMNS = ["date", "title", "category", "seller", "qty", "cost_price", "sell_price", "language", "location"]
PURCHASES_BACKUP_COLUMNS = ["date", "title", "short_title", "category", "language", "source", "qty", "cost_price", "recorded_by"]


def _last_7_days():
    """Today first, going back BACKUP_DAYS - 1 more days (newest first)."""
    today = date.today()
    return [(today - timedelta(days=i)).isoformat() for i in range(BACKUP_DAYS)]


def _day_rows(day: str):
    sales_rows = an.filter_sales(data.SALES, date_from=day, date_to=day)
    purchase_rows = an.filter_sales(data.PURCHASES, date_from=day, date_to=day)
    return sales_rows, purchase_rows


@books_bp.route("/backup", methods=["GET"])
@login_required
def backup():
    days = []
    for day in _last_7_days():
        sales_rows, purchase_rows = _day_rows(day)
        days.append({
            "date": day,
            "has_records": bool(sales_rows or purchase_rows),
        })
    return render_template("backup.html", days=days)


@books_bp.route("/backup/download/<day>", methods=["GET"])
@login_required
def backup_download(day):
    if day not in _last_7_days():
        flash("That backup date is out of range.", "error")
        return redirect(url_for("books.backup"))

    sales_rows, purchase_rows = _day_rows(day)

    return send_xlsx_multi(
        [
            ("Sales", sales_rows, SALES_BACKUP_COLUMNS, None),
            ("Inward Stock", purchase_rows, PURCHASES_BACKUP_COLUMNS, None),
        ],
        filename=f"fnrg_backup_{day}.xlsx",
    )


@books_bp.route("/inward-stock", methods=["GET", "POST"])
@login_required
def inward_stock():
    user = current_user()

    if request.method == "POST":
        purchase_date = request.form.get("purchase_date") or ""
        source = request.form.get("source", "").strip()

        # Rows arrive as parallel arrays (one entry per purchase row) —
        # see the name="...[]" inputs in inward_stock.html.
        titles = request.form.getlist("title[]")
        shorts = request.form.getlist("short[]")
        row_languages = request.form.getlist("language[]")
        row_categories = request.form.getlist("category[]")
        qtys = request.form.getlist("qty[]")
        costs = request.form.getlist("cost[]")

        if not purchase_date or not source:
            flash("Purchase date and source are required.", "error")
            return redirect(url_for("books.inward_stock"))

        added = 0

        for i, raw_title in enumerate(titles):
            title = raw_title.strip()
            if not title:
                continue
            try:
                qty = int(qtys[i])
                cost_price = float(costs[i])
            except (ValueError, IndexError):
                continue
            if qty <= 0:
                continue

            language = row_languages[i] if i < len(row_languages) else ""
            category = row_categories[i] if i < len(row_categories) else ""
            short_title = shorts[i].strip() if i < len(shorts) else ""

            data.PURCHASES.insert(0, {
                "id": data.next_purchase_id(),
                "date": purchase_date,
                "title": title,
                "short_title": short_title,
                "category": category,
                "language": language,
                "source": source,
                "qty": qty,
                "cost_price": cost_price,
                "recorded_by": user["username"] if user else "",
            })
            added += 1

            # A title purchased for the first time (e.g. via "+ Add New
            # Book") becomes part of the real catalog too, so it shows up
            # in the Dashboard inventory, Master Data, and future
            # dropdowns. Existing titles are left untouched.
            data.add_book(title, short_title, category)

        if source and source not in data.SOURCES:
            data.SOURCES.append(source)

        if added:
            flash(f"Recorded {added} book{'s' if added != 1 else ''} received into stock.", "success")
        else:
            flash("No valid rows to record — check titles, quantities and required fields.", "error")

        return redirect(url_for("books.inward_stock"))

    book_catalog = [
        {"title": b["title"], "short_title": b["short_title"], "category": b["category"]}
        for b in data.BOOKS
    ]
    sources = sorted(set(data.SOURCES) | {p["source"] for p in data.PURCHASES if p.get("source")})

    return render_template(
        "inward_stock.html",
        book_catalog=book_catalog,
        languages=data.LANGUAGES,
        categories=data.CATEGORIES,
        sources=sources,
        recent_purchases=data.PURCHASES[:20],
    )


@books_bp.route("/inward-stock/export", methods=["GET"])
@login_required
def export_inward_stock():
    return send_xlsx(
        data.PURCHASES,
        columns=["date", "title", "short_title", "category", "language", "source", "qty", "cost_price"],
        headers=["Purchase Date", "Book Title", "Short Title", "Category", "Language", "Source", "Qty", "Cost/Unit"],
        sheet_name="Recent Purchases",
        filename="inward_stock.xlsx",
    )


# --------------------------------------------------------------------- #
# Master Data — books (with shorthand), categories, languages, locations,
# events. One page that both adds to and shows each of these lists, since
# they're all small reference tables the rest of the app's dropdowns pull
# from (Sell Entry, Inward Stock, Dashboard filters).
# --------------------------------------------------------------------- #
@books_bp.route("/master-data", methods=["GET"])
@login_required
def master_data():
    return render_template(
        "master_data.html",
        books=sorted(data.BOOKS, key=lambda b: b["title"]),
        categories=data.CATEGORIES,
        languages=data.LANGUAGES,
        locations=data.LOCATIONS,
        events=data.EVENTS,
    )


@books_bp.route("/master-data/books", methods=["POST"])
@login_required
def master_data_add_book():
    title = request.form.get("title", "").strip()
    short_title = request.form.get("short_title", "").strip()

    if not title:
        flash("Book title is required.", "error")
    else:
        book, created = data.add_book(title, short_title, "")
        if created:
            flash(f"Added \"{title}\" ({book['short_title'] or 'no shorthand'}) to the catalog.", "success")
        else:
            flash(f"\"{title}\" is already in the catalog.", "error")

    return redirect(url_for("books.master_data"))


@books_bp.route("/master-data/categories", methods=["POST"])
@login_required
def master_data_add_category():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Category name is required.", "error")
    elif data.add_category(name):
        flash(f"Added category \"{name}\".", "success")
    else:
        flash(f"Category \"{name}\" already exists.", "error")
    return redirect(url_for("books.master_data"))


@books_bp.route("/master-data/languages", methods=["POST"])
@login_required
def master_data_add_language():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Language name is required.", "error")
    elif data.add_language(name):
        flash(f"Added language \"{name}\".", "success")
    else:
        flash(f"Language \"{name}\" already exists.", "error")
    return redirect(url_for("books.master_data"))


@books_bp.route("/master-data/locations", methods=["POST"])
@login_required
def master_data_add_location():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Location name is required.", "error")
    elif data.add_location(name):
        flash(f"Added location \"{name}\".", "success")
    else:
        flash(f"Location \"{name}\" already exists.", "error")
    return redirect(url_for("books.master_data"))


@books_bp.route("/master-data/events", methods=["POST"])
@login_required
def master_data_add_event():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Event name is required.", "error")
    elif data.add_event(name):
        flash(f"Added event \"{name}\".", "success")
    else:
        flash(f"Event \"{name}\" already exists.", "error")
    return redirect(url_for("books.master_data"))
