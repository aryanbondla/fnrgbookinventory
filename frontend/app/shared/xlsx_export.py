"""
Shared helper for exporting a table (list of dicts) to a downloadable
.xlsx file. Used by every "Download XLSX" button across the app so each
route only needs to supply its rows, column order, and a filename.
"""

from io import BytesIO

from flask import send_file
from openpyxl import Workbook


def send_xlsx(rows, columns, sheet_name, filename, headers=None):
    """
    rows:       list of dicts (or dict-like) — one per output row.
    columns:    list of dict keys, in the order they should appear.
    sheet_name: worksheet title (max 31 chars, Excel's own limit).
    filename:   download filename, should end in .xlsx.
    headers:    optional display header labels, same order as `columns`
                (defaults to the column keys themselves).
    """
    return send_xlsx_multi([(sheet_name, rows, columns, headers)], filename)


def send_xlsx_multi(sheets, filename):
    """
    sheets: list of (sheet_name, rows, columns, headers) tuples — headers
            may be None to fall back to the column keys. One worksheet is
            created per tuple, in order.
    filename: download filename, should end in .xlsx.
    """
    wb = Workbook()
    wb.remove(wb.active)

    for sheet_name, rows, columns, headers in sheets:
        ws = wb.create_sheet(sheet_name[:31])
        ws.append(headers or columns)
        for row in rows:
            ws.append([row.get(c, "") for c in columns])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
