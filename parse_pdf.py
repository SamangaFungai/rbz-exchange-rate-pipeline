"""
parse_pdf.py
Parses a single RBZ daily "RATES_DD_MONTH_YYYY.pdf" into structured rows.

The PDF is a single-page text table (no OCR needed) shaped like:

    CURRENCY INDICES BID ASK MID RATE BID RATE ASK RATE MID RATE
    ZWG ZWG ZWG
    INTERBANK RATE
    USD 1 1 1.0000 25.9637 27.2951 26.6294
    ZAR 16.4026 16.4065 16.40455 0.6009 0.6319 0.6164
    GBP * 1.3218 1.3221 1.32195 34.3188 36.0868 35.2028
    ...
    Friday, 25 September 2026

Each data row has: CURRENCY [*] IDX_BID IDX_ASK IDX_MID ZWG_BID ZWG_ASK ZWG_MID
"""

import re
from datetime import datetime
import pdfplumber
import io

# Matches a currency code (letters/digits/slash), an optional trailing
# asterisk (RBZ marks some currencies this way), then exactly 6 numbers
# (numbers may contain commas as thousand separators).
ROW_RE = re.compile(
    r"^(?P<currency>[A-Z0-9/]+)\s*\*?\s+"
    r"(?P<nums>[\d,.\s]+)$"
)

NUMBER_RE = re.compile(r"[\d,]+\.\d+|\d+")

# RBZ has used at least two footer date formats across different months:
#   "Friday, 25 September 2026"      (day, then month)
#   "Wednesday, August 19, 2026"     (month, then day, extra comma)
# Both are tried, in order, since only one will match any given file.
DATE_PATTERNS = [
    # Day first: "Friday, 25 September 2026"
    (
        re.compile(r"[A-Za-z]+,\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})"),
        "%d %B %Y",
        lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}",
    ),
    # Month first: "Wednesday, August 19, 2026"
    (
        re.compile(r"[A-Za-z]+,\s+([A-Za-z]+)\s+(\d{1,2}),\s+(\d{4})"),
        "%B %d %Y",
        lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}",
    ),
]


def _parse_numbers(num_blob):
    """Extract up to 6 float values from a whitespace/comma-separated blob."""
    raw = NUMBER_RE.findall(num_blob)
    return [float(n.replace(",", "")) for n in raw]


def parse_date(text):
    """
    Find the footer date line and return an ISO date string.
    Tries each known RBZ date format in turn (see DATE_PATTERNS above),
    since the format has changed between months in the past.
    """
    for pattern, strptime_fmt, build_str in DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            dt = datetime.strptime(build_str(m), strptime_fmt)
            return dt.strftime("%Y-%m-%d")
    return None


def parse_rates(text):
    """
    Parse the full extracted PDF text into a list of row dicts:
        {currency, idx_bid, idx_ask, idx_mid, zwg_bid, zwg_ask, zwg_mid}
    Skips header/footer lines that don't match the row pattern.
    """
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = ROW_RE.match(line)
        if not match:
            continue
        currency = match.group("currency")
        # Skip obvious header tokens that happen to look like currency codes
        if currency in {"CURRENCY", "INDICES", "BID", "ASK", "MID", "RATE", "INTERBANK"}:
            continue
        nums = _parse_numbers(match.group("nums"))
        if len(nums) != 6:
            # Malformed / unexpected row shape — skip rather than guess
            continue
        idx_bid, idx_ask, idx_mid, zwg_bid, zwg_ask, zwg_mid = nums
        rows.append(
            {
                "currency": currency,
                "idx_bid": idx_bid,
                "idx_ask": idx_ask,
                "idx_mid": idx_mid,
                "zwg_bid": zwg_bid,
                "zwg_ask": zwg_ask,
                "zwg_mid": zwg_mid,
            }
        )
    return rows


def parse_pdf_bytes(pdf_bytes):
    """
    Given raw PDF bytes, return (date_str, rows).
    Raises ValueError if the date or rows can't be found (signals a
    format change worth investigating rather than silently failing).
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    date_str = parse_date(text)
    rows = parse_rates(text)

    if not date_str:
        raise ValueError("Could not find a date line in the PDF text.")
    if not rows:
        raise ValueError("Could not parse any currency rows from the PDF text.")

    return date_str, rows


if __name__ == "__main__":
    # Quick manual test using a saved sample PDF, if present.
    import sys

    if len(sys.argv) != 2:
        print("Usage: python parse_pdf.py <path-to-pdf>")
        sys.exit(1)

    with open(sys.argv[1], "rb") as f:
        date_str, rows = parse_pdf_bytes(f.read())

    print(f"Date: {date_str}")
    print(f"Parsed {len(rows)} currency rows")
    for r in rows[:5]:
        print(r)
