"""
extract.py
Builds RBZ daily rate PDF URLs and fetches them.

URL pattern (confirmed from the live site):
    https://www.rbz.co.zw/documents/Exchange_Rates/{YEAR}/{MonthName}/RATES_{D}_{MONTHNAME}_{YEAR}.pdf

e.g. https://www.rbz.co.zw/documents/Exchange_Rates/2026/September/RATES_25_SEPTEMBER_2026.pdf

Days 1-9 are NOT zero-padded on RBZ's site, e.g.
    .../2026/September/RATES_3_SEPTEMBER_2026.pdf
so for those days we try the unpadded name first and fall back to the
zero-padded one in case RBZ ever changes it.

Note: RBZ only publishes on business days, so a 404 for a given date is
expected (weekend/public holiday) and should be treated as "skipped",
not "failed".
"""

import requests
from datetime import date

BASE_URL = "https://www.rbz.co.zw/documents/Exchange_Rates"
HEADERS = {"User-Agent": "Mozilla/5.0 (RBZ rate pipeline; student project)"}
TIMEOUT = 15


def build_urls(d: date) -> list:
    """All filename variants to try for a date, most likely first."""
    month_name = d.strftime("%B").upper()      # SEPTEMBER
    month_folder = d.strftime("%B")             # September
    year_str = str(d.year)

    day_variants = [str(d.day)]                 # 3  (what RBZ actually uses)
    if d.day < 10:
        day_variants.append(f"{d.day:02d}")     # 03 (fallback)

    return [
        f"{BASE_URL}/{year_str}/{month_folder}/RATES_{day}_{month_name}_{year_str}.pdf"
        for day in day_variants
    ]


def build_url(d: date) -> str:
    """Primary URL for a date (kept for anything that still calls build_url)."""
    return build_urls(d)[0]


def fetch_pdf(d: date):
    """
    Fetch the PDF for a given date, trying each filename variant.
    Returns (status, content_bytes_or_None, url)
      status: "ok" | "not_found" | "error"
    """
    urls = build_urls(d)
    had_error = False

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        except requests.RequestException:
            had_error = True
            continue

        if resp.status_code == 200 and resp.content:
            return "ok", resp.content, url
        elif resp.status_code == 404:
            continue
        else:
            had_error = True

    return ("error" if had_error else "not_found"), None, urls[0]


if __name__ == "__main__":
    # Quick manual check
    today = date.today()
    print("Would try:", *build_urls(today), sep="\n  ")
