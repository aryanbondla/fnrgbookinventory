"""
Routes owned by the Books service.

    GET  /dashboard          personal (or org-wide, for admins) overview
                              + inventory
    GET  /sell                 book sell-entry form + recent entries
    POST /sell
    GET  /analytics              admin-only profit/loss analytics with filters
    GET  /upload                   excel upload form
    POST /upload
    GET  /upload/sample
"""

from io import BytesIO

from flask import render_template, request, redirect, url_for, flash
from openpyxl import load_workbook

from . import books_bp
from . import data
from . import analytics as an
from app.shared.auth import current_user, login_required, admin_required


# --------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------- #
@books_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    user = current_user()
    is_admin = user["role"] == "admin"
    default_from, default_to = an.last_n_days_range(30)

    def section_filters(prefix):
        """
        Reads this section's own (prefixed) query params only, so
        submitting one filter bar never touches another section's
        filter state. Falls back to the 30-day default window / "all"
        when a param is missing, e.g. the first page load.
        """
        date_from = request.args.get(f"{prefix}date_from") or default_from
        date_to = request.args.get(f"{prefix}date_to") or default_to
        # Only admins can look at another seller's numbers — everyone else
        # is always pinned to their own username regardless of the URL.
        seller = (request.args.get(f"{prefix}seller") or "all") if is_admin else user["username"]
        event = request.args.get(f"{prefix}event") or "all"
        return {"date_from": date_from, "date_to": date_to, "seller": seller, "event": event}

    # One independent filter state per section of the page.
    main_f = section_filters("")
    dist_f = section_filters("dist_")
    books_f = section_filters("books_")
    inv_f = section_filters("inv_")
    filters = {"": main_f, "dist_": dist_f, "books_": books_f, "inv_": inv_f}

    scope_rows = data.SALES if is_admin else an.filter_sales(data.SALES, seller=user["username"])

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
        book_titles=[t for t, _ in data.BOOKS],
        categories=data.CATEGORIES,
        languages=data.LANGUAGES,
        locations=data.LOCATIONS,
        my_sales=my_sales,
    )


# --------------------------------------------------------------------- #
# Analytics (admin)
# --------------------------------------------------------------------- #
@books_bp.route("/analytics", methods=["GET"])
# @admin_required  # TEMP: role restriction disabled for now — re-enable when ready to lock this down again
@login_required
def analytics_page():
    default_from, default_to = an.last_n_days_range(60)
    date_from = request.args.get("date_from") or default_from
    date_to = request.args.get("date_to") or default_to
    seller = request.args.get("seller") or "all"
    location = request.args.get("location") or "all"

    rows = an.filter_sales(data.SALES, date_from=date_from, date_to=date_to, seller=seller, location=location)

    kpis = an.summary(rows)
    trend = an.revenue_profit_by_day(rows)
    profit_cat = an.profit_by_category(rows)
    qty_cat = an.qty_by_category(rows)
    leaderboard = an.leaderboard_by_seller(rows)
    top_bks = an.top_books(rows, limit=8)
    by_location = an.sales_by_location(rows)
    by_language = an.sales_by_language(rows)

    # Sellers come from the sales ledger itself (usernames only) rather
    # than importing users_service.data — books_service doesn't need to
    # know anything about a user besides the username string they sold
    # under, same as if this were a real cross-service call.
    sellers = sorted({r["seller"] for r in data.SALES})
    locations = sorted({r["location"] for r in data.SALES if r.get("location")})

    return render_template(
        "analytics.html",
        kpis=kpis,
        trend=trend,
        profit_cat=profit_cat,
        qty_cat=qty_cat,
        leaderboard=leaderboard,
        top_books=top_bks,
        by_location=by_location,
        by_language=by_language,
        sellers=sellers,
        locations=locations,
        date_from=date_from,
        date_to=date_to,
        selected_seller=seller,
        selected_location=location,
    )


# --------------------------------------------------------------------- #
# Upload
# --------------------------------------------------------------------- #
EXPECTED_COLUMNS = ["date", "title", "category", "seller", "qty", "cost_price", "sell_price", "language", "location"]


@books_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Choose an .xlsx file first.", "error")
            return redirect(url_for("books.upload"))

        if not file.filename.lower().endswith((".xlsx", ".xlsm")):
            flash("Only .xlsx files are supported right now.", "error")
            return redirect(url_for("books.upload"))

        try:
            wb = load_workbook(filename=BytesIO(file.read()), data_only=True)
            ws = wb.active
            header = [str(c.value).strip().lower() if c.value else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]

            col_index = {}
            for col in EXPECTED_COLUMNS:
                if col not in header:
                    raise ValueError(f"Missing expected column: '{col}'")
                col_index[col] = header.index(col)

            added = 0
            errors = 0
            for row_cells in ws.iter_rows(min_row=2):
                values = [c.value for c in row_cells]
                if all(v in (None, "") for v in values):
                    continue
                try:
                    new_row = {
                        "id": data.next_sale_id(),
                        "date": str(values[col_index["date"]])[:10],
                        "title": str(values[col_index["title"]]).strip(),
                        "category": str(values[col_index["category"]]).strip(),
                        "seller": str(values[col_index["seller"]]).strip().lower(),
                        "qty": int(values[col_index["qty"]]),
                        "cost_price": float(values[col_index["cost_price"]]),
                        "sell_price": float(values[col_index["sell_price"]]),
                        "language": str(values[col_index["language"]]).strip(),
                        "location": str(values[col_index["location"]]).strip(),
                    }
                    data.SALES.insert(0, new_row)
                    added += 1
                except (TypeError, ValueError):
                    errors += 1

            if added:
                msg = f"Imported {added} row{'s' if added != 1 else ''} successfully."
                if errors:
                    msg += f" Skipped {errors} row(s) with invalid data."
                flash(msg, "success")
            else:
                flash("No valid rows found in that file.", "error")

        except Exception as exc:
            flash(f"Could not read that file: {exc}", "error")

        return redirect(url_for("books.upload"))

    return render_template("upload.html", expected_columns=EXPECTED_COLUMNS)


@books_bp.route("/upload/sample", methods=["GET"])
@login_required
def upload_sample():
    """Serve a tiny sample workbook so users know the expected format."""
    from openpyxl import Workbook
    from flask import send_file

    wb = Workbook()
    ws = wb.active
    ws.append(EXPECTED_COLUMNS)
    ws.append(["2026-07-01", "Bhagavad Gita As It Is", "Philosophy", "arjun", 3, 100, 130, "English", "Hyderabad Temple"])
    ws.append(["2026-07-02", "Krishna Book", "Storytelling", "priya", 2, 120, 150, "Telugu", "College Fest - JNTU"])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name="sample_sales_upload.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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

        known_titles = {t for t, _ in data.BOOKS}
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
            # in the Dashboard inventory and future dropdowns.
            if title not in known_titles:
                data.BOOKS.append((title, category or "Uncategorized"))
                known_titles.add(title)
                if category and category not in data.CATEGORIES:
                    data.CATEGORIES = sorted(set(data.CATEGORIES) | {category})

        if source and source not in data.SOURCES:
            data.SOURCES.append(source)

        if added:
            flash(f"Recorded {added} book{'s' if added != 1 else ''} received into stock.", "success")
        else:
            flash("No valid rows to record — check titles, quantities and required fields.", "error")

        return redirect(url_for("books.inward_stock"))

    book_catalog = [{"title": t, "category": c} for t, c in data.BOOKS]
    sources = sorted(set(data.SOURCES) | {p["source"] for p in data.PURCHASES if p.get("source")})

    return render_template(
        "inward_stock.html",
        book_catalog=book_catalog,
        languages=data.LANGUAGES,
        categories=data.CATEGORIES,
        sources=sources,
        recent_purchases=data.PURCHASES[:20],
    )