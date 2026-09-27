"""
extract.py
Builds RBZ daily rate PDF URLs and fetches them.

URL pattern (confirmed from the live site):
    https://www.rbz.co.zw/documents/Exchange_Rates/{YEAR}/{MonthName}/RATES_{DD}_{MONTHNAME}_{YEAR}.pdf

e.g. https://www.rbz.co.zw/documents/Exchange_Rates/2026/September/RATES_25_SEPTEMBER_2026.pdf

Note: RBZ only publishes on business days, so a 404 for a given date is
expected (weekend/public holiday) and should be treated as "skipped",
not "failed".
"""

import requests
from datetime import date

BASE_URL = "https://www.rbz.co.zw/documents/Exchange_Rates"
HEADERS = {"User-Agent": "Mozilla/5.0 (RBZ rate pipeline; student project)"}
TIMEOUT = 15


def build_url(d: date) -> str:
    month_name = d.strftime("%B").upper()      # SEPTEMBER
    month_folder = d.strftime("%B")             # September
    day_str = f"{d.day:02d}"
    year_str = str(d.year)
    filename = f"RATES_{day_str}_{month_name}_{year_str}.pdf"
    return f"{BASE_URL}/{year_str}/{month_folder}/{filename}"


def fetch_pdf(d: date):
    """
    Fetch the PDF for a given date.
    Returns (status, content_bytes_or_None, url)
      status: "ok" | "not_found" | "error"
    """
    url = build_url(d)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException as e:
        return "error", None, url

    if resp.status_code == 200 and resp.content:
        return "ok", resp.content, url
    elif resp.status_code == 404:
        return "not_found", None, url
    else:
        return "error", None, url


if __name__ == "__main__":
    # Quick manual check
    today = date.today()
    print("Would fetch:", build_url(today))
